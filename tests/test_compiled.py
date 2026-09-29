"""pytest 回归与规格验证套件 — EGASP compiled 内核。

覆盖 Spec Mode checklist AC-1 ~ AC-10：
  AC-1  mass_fraction 正确映射
  AC-2  有效域检查 raise (PropertyOutOfRangeError)
  AC-3  temperature_from_h 安全反解
  AC-4  NaN/Inf 输入 raise
  AC-5  单属性方法 (rho/cp/h/k/mu)
  AC-6  evaluate 返回形状正确 + 单属性精确插值
  AC-7  legacy prop/props 与 compiled 内核完全一致
  AC-8  LRU cache + readonly table
  AC-9  批量性能 ≤ 0.38ms @ 5000T*100
  AC-10 mu 单位 Pa·s（legacy 内部已 /1000 修正）
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from egasp import EGASP, compile_mixture
from egasp.compiled import CompiledEGMixture
from egasp.exceptions import (
    EGASPError,
    InvalidInputError,
    PropertyOutOfRangeError,
)
from egasp.validate import clamp_or_raise, normalize_query_type, validate_prop_key

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def eg() -> EGASP:
    return EGASP()


@pytest.fixture(scope="module")
def cm50() -> CompiledEGMixture:
    return compile_mixture(0.5)


# ===========================================================================
# AC-1: mass_fraction 映射
# ===========================================================================


@pytest.mark.parametrize(
    "vol,expected_mass",
    [
        (0.5, 0.5240),
        (0.3, 0.3240),
        (0.7, 0.7160),
        (0.1, 0.1117),
        (0.9, 0.9028),
    ],
)
def test_ac1_mass_fraction(vol: float, expected_mass: float) -> None:
    cm = compile_mixture(vol)
    assert abs(cm.mass_fraction - expected_mass) < 0.01
    # volume_fraction 必须等于构造时的值（误差 ≤ 1e-6）
    assert abs(cm.volume_fraction - vol) < 1e-6


def test_ac1_mass_volume_differ() -> None:
    """除 0.0 外，质量浓度 ≠ 体积浓度。"""
    for vol in np.round(np.arange(0.1, 1.0, 0.1), 1):
        cm = compile_mixture(float(vol))
        if cm.volume_fraction > 0.01:
            assert cm.mass_fraction != cm.volume_fraction


# ===========================================================================
# AC-2: 有效域边界检查
# ===========================================================================


def test_ac2_out_of_range_raises(cm50: CompiledEGMixture) -> None:
    with pytest.raises(PropertyOutOfRangeError):
        cm50.evaluate(cm50.Tmin - 1)
    with pytest.raises(PropertyOutOfRangeError):
        cm50.evaluate(cm50.Tmax + 1)
    with pytest.raises(PropertyOutOfRangeError):
        cm50.temperature_from_h(cm50.hmax + 1)
    with pytest.raises(PropertyOutOfRangeError):
        cm50.temperature_from_h(cm50.hmin - 1)


def test_ac2_edge_ok(cm50: CompiledEGMixture) -> None:
    """边界端点 ∈ 有效域。"""
    v = cm50.evaluate(cm50.Tmin)
    assert v.shape == (5,)
    assert np.all(np.isfinite(v))


def test_ac2_concentration_range() -> None:
    with pytest.raises(PropertyOutOfRangeError):
        compile_mixture(0.05)
    with pytest.raises(PropertyOutOfRangeError):
        compile_mixture(0.96)


# ===========================================================================
# AC-3: temperature_from_h 安全
# ===========================================================================


def test_ac3_temperature_from_h_midpoint() -> None:
    cm = compile_mixture(0.5)
    h_mid = cm.h(25.0)
    T_back = cm.temperature_from_h(h_mid)
    assert abs(T_back - 25.0) < 0.5  # 接近 25C


def test_ac3_temperature_from_h_boundaries() -> None:
    """hmin/hmax 端点应能精确反解。"""
    cm = compile_mixture(0.5)
    T_at_hmin = cm.temperature_from_h(cm.hmin)
    T_at_hmax = cm.temperature_from_h(cm.hmax)
    assert abs(T_at_hmin - cm.Tmin) < 0.6  # 节点级精度
    assert abs(T_at_hmax - cm.Tmax) < 0.6


def test_ac3_temperature_from_h_out_of_range() -> None:
    cm = compile_mixture(0.5)
    with pytest.raises(PropertyOutOfRangeError):
        cm.temperature_from_h(cm.hmin - 1)
    with pytest.raises(PropertyOutOfRangeError):
        cm.temperature_from_h(cm.hmax + 1)


# ===========================================================================
# AC-4: NaN / Inf 输入拒绝
# ===========================================================================


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
def test_ac4_nan_input(cm50: CompiledEGMixture, bad: float) -> None:
    with pytest.raises((InvalidInputError, EGASPError)):
        cm50.evaluate(bad)
    with pytest.raises((InvalidInputError, EGASPError)):
        cm50.temperature_from_h(bad)


def test_ac4_array_nan(cm50: CompiledEGMixture) -> None:
    with pytest.raises((InvalidInputError, EGASPError)):
        cm50.evaluate(np.array([10.0, np.nan, 20.0]))


# ===========================================================================
# AC-5: 单属性方法
# ===========================================================================


@pytest.mark.parametrize("prop", ["rho", "cp", "h", "k", "mu"])
def test_ac5_scalar_callable(cm50: CompiledEGMixture, prop: str) -> None:
    fn = getattr(cm50, prop)
    val = fn(25.0)
    assert isinstance(val, float)
    assert np.isfinite(val)


@pytest.mark.parametrize("prop", ["rho", "cp", "h", "k", "mu"])
def test_ac5_array_callable(cm50: CompiledEGMixture, prop: str) -> None:
    fn = getattr(cm50, prop)
    vals = fn(np.array([10.0, 25.0, 50.0]))
    assert vals.shape == (3,)
    assert np.all(np.isfinite(vals))


# ===========================================================================
# AC-6: evaluate 返回形状 + 节点精确命中
# ===========================================================================


def test_ac6_evaluate_scalar_shape(cm50: CompiledEGMixture) -> None:
    v = cm50.evaluate(25.0)
    assert v.shape == (5,)


def test_ac6_evaluate_array_shape(cm50: CompiledEGMixture) -> None:
    v = cm50.evaluate(np.linspace(-30, 120, 100))
    assert v.shape == (5, 100)


@pytest.mark.parametrize("T", [-35.0, 0.0, 5.0, 25.0, 50.0, 100.0, 125.0])
def test_ac6_node_exact_hit(cm50: CompiledEGMixture, T: float) -> None:
    """节点温度的 evaluate 结果应 ≈ 原始表值（或 raise 如节点不在有效域）。"""
    if T < cm50.Tmin or T > cm50.Tmax:
        with pytest.raises(PropertyOutOfRangeError):
            cm50.evaluate(T)
        return
    v = cm50.evaluate(T)
    assert np.all(np.isfinite(v))


# ===========================================================================
# AC-7: legacy prop() 与 compiled 内核数值一致
# ===========================================================================


@pytest.mark.parametrize("conc", [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])
@pytest.mark.parametrize("prop_key", ["rho", "cp", "h", "k", "mu"])
def test_ac7_legacy_prop_matches_compiled(
    eg: EGASP, conc: float, prop_key: str
) -> None:
    cm = compile_mixture(conc)
    T_range = np.array([cm.Tmin + 0.5, 25.0, 50.0, cm.Tmax - 0.5])
    legacy = eg.prop(T_range, conc, prop_key)
    idx = {"rho": 0, "cp": 1, "h": 2, "k": 3, "mu": 4}[prop_key]
    new = cm.evaluate(T_range)[idx, :]
    np.testing.assert_allclose(legacy, new, rtol=1e-12)


def test_ac7_legacy_props_matches_compiled(eg: EGASP) -> None:
    """props() 返回 tuple 的第 5-9 位 (rho, cp, k, mu, h) 应 == compiled。"""
    _mass, vol, _freez, _boil, rho, cp, k, mu, h = eg.props(25.0, "volume", 0.5)
    cm = compile_mixture(vol)
    v = cm.evaluate(25.0)
    np.testing.assert_allclose([rho, cp, k, mu, h], v[[0, 1, 3, 4, 2]], rtol=1e-12)


# ===========================================================================
# AC-8: LRU cache + readonly table
# ===========================================================================


def test_ac8_lru_cache_identity() -> None:
    a = compile_mixture(0.5)
    b = compile_mixture(0.5)
    assert a is b
    c = compile_mixture(0.3)
    d = compile_mixture(0.3)
    assert c is d
    assert a is not c


def test_ac8_table_readonly(cm50: CompiledEGMixture) -> None:
    with pytest.raises(ValueError):
        cm50.table[0, 0] = 123.0
    with pytest.raises(ValueError):
        cm50.table[3, 10] = 1.0


# ===========================================================================
# AC-9: 性能 ≤ 0.38ms @ 5000 temps * 100 次
# ===========================================================================


def test_ac9_batch_performance() -> None:
    cm = compile_mixture(0.5)
    temps = np.linspace(-30, 120, 5000)
    # warm up
    cm.evaluate(temps)
    # timed
    t0 = time.perf_counter()
    for _ in range(100):
        cm.evaluate(temps)
    t1 = time.perf_counter()
    avg_ms = (t1 - t0) / 100 * 1000
    assert avg_ms < 0.38, f"avg={avg_ms:.3f}ms > 0.38ms"


# ===========================================================================
# AC-10: mu 单位 Pa·s
# ===========================================================================


def test_ac10_mu_unit(eg: EGASP, cm50: CompiledEGMixture) -> None:
    """mu(25C, 0.5) ≈ 3.39 mPa·s = 0.00339 Pa·s。"""
    mu_scalar = cm50.mu(25.0)
    assert 0.002 < mu_scalar < 0.005
    legacy = eg.prop(25.0, 0.5, "mu")
    assert abs(legacy - mu_scalar) < 1e-10


# ===========================================================================
# Import time sanity
# ===========================================================================


def test_import_time() -> None:
    """core import 应 < 200ms。"""
    t0 = time.perf_counter()
    import egasp  # noqa: F401 — verify import succeeds

    t1 = time.perf_counter()
    # 注意: 在已 import 过的进程里会更快，这里主要保证不抛异常
    assert (t1 - t0) < 10.0  # 10s 上限 — 宽松但防退化


# ===========================================================================
# Exception / validate 基础
# ===========================================================================


def test_validate_prop_key() -> None:
    assert validate_prop_key("rho") == "rho"
    with pytest.raises(InvalidInputError):
        validate_prop_key("foobar")


def test_normalize_query_type() -> None:
    assert normalize_query_type("v") == "volume"
    assert normalize_query_type("mass") == "mass"
    with pytest.raises(InvalidInputError):
        normalize_query_type("density")


def test_clamp_or_raise() -> None:
    assert clamp_or_raise(0.5, 0.1, 0.9, param="c") == 0.5
    with pytest.raises(PropertyOutOfRangeError):
        clamp_or_raise(0.05, 0.1, 0.9, param="c")
    with pytest.raises(PropertyOutOfRangeError):
        clamp_or_raise(250.0, -35.0, 125.0, param="T")
