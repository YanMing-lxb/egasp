"""egasp 高性能物性内核 — CompiledEGMixture + compile_mixture().

职责：一次沿浓度方向编译 (33, 9, 5) 数据表 → 固定浓度的 (5, 33) 表，
并提供真正的 NumPy 批量 fused evaluator。

本文件仅依赖 numpy + egasp.data + egasp.exceptions，不导入 core / __main__ / rich。
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Final, NamedTuple

import numpy as np

from egasp.data.egasp_data import (
    _FB_RAW_VOL_SORTED,
    _PROPERTY_TABLE,
    CONC_NODES,
    TEMP_NODES,
)
from egasp.exceptions import (
    CompilationError,
    MissingPropertyDataError,
    PropertyOutOfRangeError,
)

# ---------------------------------------------------------------------------
# 模块级常量（避免硬编码）
# ---------------------------------------------------------------------------

_T_MIN: Final[float] = float(TEMP_NODES[0])  # -35.0
_T_MAX: Final[float] = float(TEMP_NODES[-1])  # 125.0
_T_STEP: Final[float] = float(TEMP_NODES[1] - TEMP_NODES[0])  # 5.0

_PROP_IDX_RHO: Final[int] = 0
_PROP_IDX_CP: Final[int] = 1
_PROP_IDX_H: Final[int] = 2
_PROP_IDX_K: Final[int] = 3
_PROP_IDX_MU: Final[int] = 4
_N_PROPS: Final[int] = 5


# ---------------------------------------------------------------------------
# 属性结果容器（标量 / 小批量查询的便捷返回）
# ---------------------------------------------------------------------------


class PropsScalar(NamedTuple):
    rho: float
    cp: float
    h: float
    k: float
    mu: float


# ---------------------------------------------------------------------------
# 主要数据类
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompiledEGMixture:
    """固定浓度乙二醇水溶液的预编译物性表 + 融合求值器。

    使用 :func:`compile_mixture` 构造，重复调用相同浓度会命中 LRU cache。
    """

    conc: float
    table: np.ndarray  # (5, 33) 固定浓度下的五物性温度节点值
    dtable: np.ndarray  # (5, 33) 区间内导数（legacy-linear 下为常数）
    h_nodes: np.ndarray  # (33,) h 表，供 temperature_from_h() 反解
    Tmin: float
    Tmax: float
    validity: bool  # 整个 [Tmin, Tmax] 内五物性均无 NaN
    freezing_point: float | None
    boiling_point: float | None
    mass_fraction: float | None
    volume_fraction: float | None

    # ------------------------------------------------------------------
    # 融合求值（核心 hot path）
    # ------------------------------------------------------------------

    def evaluate(self, T: float | np.ndarray) -> np.ndarray:
        """批量返回五物性 `(5, N)` ndarray；标量输入返回 `(5,)`。

        顺序固定: [rho, cp, h, k, mu]。内部一次 idx/w → 五物性共享。
        超出有效范围 raise PropertyOutOfRangeError。
        """
        T_arr = np.asarray(T, dtype=np.float64)
        is_scalar = T_arr.ndim == 0
        if is_scalar:
            T_arr = T_arr.reshape(1)
        self._check_range(T_arr)
        result = self._fused_eval(T_arr)  # (5, N)
        if is_scalar:
            result = result[:, 0]  # → (5,)
        return result

    def evaluate_into(self, T: np.ndarray, out: np.ndarray) -> None:
        """原地写入预分配的 `(5, N)` ndarray。

        调用方负责分配并保证 out.shape == (5, N)，N = T.size。
        """
        T_arr = np.asarray(T, dtype=np.float64).ravel()
        if out.shape != (_N_PROPS, T_arr.size):
            raise ValueError(
                f"out shape 应为 ({_N_PROPS}, {T_arr.size})，实际 {out.shape}"
            )
        self._check_range(T_arr)
        out[...] = self._fused_eval(T_arr)

    # -- 单属性快捷 -------------------------------------------------------

    def rho(self, T: float | np.ndarray) -> float | np.ndarray:
        return self._single_eval(T, _PROP_IDX_RHO)

    def cp(self, T: float | np.ndarray) -> float | np.ndarray:
        return self._single_eval(T, _PROP_IDX_CP)

    def h(self, T: float | np.ndarray) -> float | np.ndarray:
        return self._single_eval(T, _PROP_IDX_H)

    def k(self, T: float | np.ndarray) -> float | np.ndarray:
        return self._single_eval(T, _PROP_IDX_K)

    def mu(self, T: float | np.ndarray) -> float | np.ndarray:
        return self._single_eval(T, _PROP_IDX_MU)

    def mu_into(self, T: np.ndarray, out: np.ndarray) -> None:
        """壁面粘度专用 fast path — 只计算 mu。"""
        T_arr = np.asarray(T, dtype=np.float64).ravel()
        self._check_range(T_arr)
        idx, w = self._temp_index(T_arr)
        lo = self.table[_PROP_IDX_MU, idx]
        hi = self.table[_PROP_IDX_MU, idx + 1]
        out[...] = lo + (hi - lo) * w

    def h_from_T(self, T: float | np.ndarray) -> float | np.ndarray:
        """h(T) — evaluate 的 h 列别名。"""
        return self.h(T)

    # ------------------------------------------------------------------
    # 焓反解（legacy-linear 模式）
    # ------------------------------------------------------------------

    def temperature_from_h(self, h: float | np.ndarray) -> float | np.ndarray:
        """固定浓度下 h→T 一次反解（线性插值区间 O(log n) 搜索）。

        legacy-linear 模式下与 PHEx 现有二分反解等价，数值误差在 1e-12 量级。
        """
        h_arr = np.asarray(h, dtype=np.float64)
        is_scalar = h_arr.ndim == 0
        h_vals = h_arr[None] if is_scalar else h_arr

        h_nodes = self.h_nodes
        idx = np.searchsorted(h_nodes, h_vals) - 1
        idx = np.clip(idx, 0, len(h_nodes) - 2)
        h_lo = h_nodes[idx]
        h_hi = h_nodes[idx + 1]
        T_lo = TEMP_NODES[idx]
        T_hi = TEMP_NODES[idx + 1]
        w = (h_vals - h_lo) / (h_hi - h_lo)
        result = T_lo + (T_hi - T_lo) * w

        return float(result[0]) if is_scalar else result

    # ------------------------------------------------------------------
    # 导数（legacy-linear 模式下区间内为常数）
    # ------------------------------------------------------------------

    def _dprop_dT(self, T: float | np.ndarray, prop_idx: int) -> float | np.ndarray:
        T_arr = np.asarray(T, dtype=np.float64)
        is_scalar = T_arr.ndim == 0
        if is_scalar:
            T_arr = T_arr.reshape(1)
        self._check_range(T_arr)
        idx, _w = self._temp_index(T_arr)
        deriv = self.dtable[prop_idx, idx]
        return float(deriv[0]) if is_scalar else deriv

    def drho_dT(self, T: float | np.ndarray) -> float | np.ndarray:
        return self._dprop_dT(T, _PROP_IDX_RHO)

    def dcp_dT(self, T: float | np.ndarray) -> float | np.ndarray:
        return self._dprop_dT(T, _PROP_IDX_CP)

    def dh_dT(self, T: float | np.ndarray) -> float | np.ndarray:
        """legacy-linear 模式下，区间内 dh/dT = cp_i（近似）。

        严格来说只在 `integrated_cp` 模式下 dh/dT == cp(T) 逐点成立；
        legacy-linear 区间内 dh/dT 是平均 cp。
        """
        return self._dprop_dT(T, _PROP_IDX_H)

    def dk_dT(self, T: float | np.ndarray) -> float | np.ndarray:
        return self._dprop_dT(T, _PROP_IDX_K)

    def dmu_dT(self, T: float | np.ndarray) -> float | np.ndarray:
        return self._dprop_dT(T, _PROP_IDX_MU)

    # ------------------------------------------------------------------
    # PropertyWorkspace
    # ------------------------------------------------------------------

    def make_workspace(self, n_edges: int) -> PropertyWorkspace:
        """创建持久数组的 PropertyWorkspace — 供固定网络规模求解器复用。"""
        return PropertyWorkspace(
            T=np.empty(n_edges, dtype=np.float64),
            idx=np.empty(n_edges, dtype=np.intp),
            w=np.empty(n_edges, dtype=np.float64),
            rho=np.empty(n_edges, dtype=np.float64),
            cp=np.empty(n_edges, dtype=np.float64),
            h=np.empty(n_edges, dtype=np.float64),
            k=np.empty(n_edges, dtype=np.float64),
            mu=np.empty(n_edges, dtype=np.float64),
        )

    def update_into(self, T: np.ndarray, ws: PropertyWorkspace) -> None:
        """原地更新 workspace 的所有字段。"""
        T_arr = np.asarray(T, dtype=np.float64).ravel()
        self._check_range(T_arr)
        idx, w = self._temp_index(T_arr)
        ws.T[...] = T_arr
        ws.idx[...] = idx
        ws.w[...] = w

        # 五属性 fused 写入 — 同一次 idx/w
        lo = self.table[:, idx]  # (5, N)
        hi = self.table[:, idx + 1]  # (5, N)
        val = lo + (hi - lo) * w[np.newaxis, :]  # (5, N)
        ws.rho[...] = val[_PROP_IDX_RHO]
        ws.cp[...] = val[_PROP_IDX_CP]
        ws.h[...] = val[_PROP_IDX_H]
        ws.k[...] = val[_PROP_IDX_K]
        ws.mu[...] = val[_PROP_IDX_MU]

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _temp_index(self, T_arr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """T (N,) → (idx, w) (N,) — 零 bisect，零 list 依赖。"""
        z = (T_arr - _T_MIN) * (1.0 / _T_STEP)
        idx = np.floor(z).astype(np.intp)
        idx = np.clip(idx, 0, len(TEMP_NODES) - 2)
        w = z - idx
        return idx, w

    def _fused_eval(self, T_arr: np.ndarray) -> np.ndarray:
        """给定 (N,) 温度数组，返回融合的 (5, N) 结果。"""
        idx, w = self._temp_index(T_arr)
        lo = self.table[:, idx]  # (5, N)
        hi = self.table[:, idx + 1]  # (5, N)
        return lo + (hi - lo) * w[np.newaxis, :]  # (5, N)

    def _single_eval(self, T: float | np.ndarray, prop_idx: int) -> float | np.ndarray:
        T_arr = np.asarray(T, dtype=np.float64)
        is_scalar = T_arr.ndim == 0
        if is_scalar:
            T_arr = T_arr.reshape(1)
        self._check_range(T_arr)
        idx, w = self._temp_index(T_arr)
        lo = self.table[prop_idx, idx]
        hi = self.table[prop_idx, idx + 1]
        result = lo + (hi - lo) * w
        return float(result[0]) if is_scalar else result

    def _check_range(self, T_arr: np.ndarray) -> None:
        if T_arr.size == 0:
            return
        lo_viol = np.min(T_arr) if np.any(T_arr < _T_MIN) else None
        hi_viol = np.max(T_arr) if np.any(T_arr > _T_MAX) else None
        if lo_viol is not None or hi_viol is not None:
            viol = lo_viol if lo_viol is not None else hi_viol
            raise PropertyOutOfRangeError(float(viol), _T_MIN, _T_MAX, param="温度")


# ---------------------------------------------------------------------------
# PropertyWorkspace
# ---------------------------------------------------------------------------


@dataclass
class PropertyWorkspace:
    """固定网络规模的持久属性容器 — 避免每轮 new 数组。"""

    T: np.ndarray
    idx: np.ndarray
    w: np.ndarray
    rho: np.ndarray
    cp: np.ndarray
    h: np.ndarray
    k: np.ndarray
    mu: np.ndarray

    def update(self, mixture: CompiledEGMixture, T: np.ndarray) -> None:
        """ws.update(mixture, T) 等价于 mixture.update_into(T, ws)。"""
        mixture.update_into(T, self)


# ---------------------------------------------------------------------------
# compile_mixture() — 模块级 LRU 缓存入口
# ---------------------------------------------------------------------------


_CONC_LO: Final[float] = float(CONC_NODES[0])
_CONC_HI: Final[float] = float(CONC_NODES[-1])


@lru_cache(maxsize=32)
def compile_mixture(concentration: float) -> CompiledEGMixture:
    """一次性沿浓度方向编译固定浓度的物性表，返回 CompiledEGMixture。

    concentration ∈ [0.1, 0.9]（体积浓度）。若 concentration 恰好是数据库节点
    （如 0.5）则直接取对应列，零浓度插值开销。
    """
    # ---- 校验 -----------------------------------------------------------
    if not np.isfinite(concentration):
        raise CompilationError(f"concentration 必须是有限浮点数，得到 {concentration}")
    if not (_CONC_LO - 1e-9 <= concentration <= _CONC_HI + 1e-9):
        raise PropertyOutOfRangeError(
            float(concentration), _CONC_LO, _CONC_HI, param="浓度"
        )

    # ---- 沿浓度方向插值 → (5, 33) table ---------------------------------
    conc_idxs = np.round(np.abs(CONC_NODES - concentration), 6)
    hit = np.where(conc_idxs < 1e-6)[0]
    if len(hit) == 1:
        # 精确命中 — 直接取列 (33, 5) → transpose → (5, 33)
        table = _PROPERTY_TABLE[:, int(hit[0]), :].T.copy()  # (33, 5) → (5, 33)
        conc_used = float(CONC_NODES[int(hit[0])])
    else:
        # 双线性沿浓度方向插值
        lo_i = int(np.searchsorted(CONC_NODES, concentration) - 1)
        lo_i = max(0, min(lo_i, len(CONC_NODES) - 2))
        hi_i = lo_i + 1
        c_lo = float(CONC_NODES[lo_i])
        c_hi = float(CONC_NODES[hi_i])
        if c_hi == c_lo:
            raise CompilationError(f"浓度节点间距为零: {c_lo}, {c_hi}")
        w_c = (concentration - c_lo) / (c_hi - c_lo)
        lo_tab = _PROPERTY_TABLE[:, lo_i, :]  # (33, 5)
        hi_tab = _PROPERTY_TABLE[:, hi_i, :]
        table = (lo_tab + (hi_tab - lo_tab) * w_c).T.copy()  # → (5, 33)
        conc_used = float(concentration)

    # ---- 导数表 ---------------------------------------------------------
    # legacy-linear 下，区间 [T_i, T_{i+1}] 内导数 = (P_{i+1} - P_i) / 5
    # 输出形状 (5, 33) — 末列重复前一列的导数（边界外会被 clip 截断）
    dtable = np.zeros_like(table)
    dtable[:, :-1] = (table[:, 1:] - table[:, :-1]) / _T_STEP
    dtable[:, -1] = dtable[:, -2]

    # ---- h 表副本（反解用）----------------------------------------------
    h_nodes = table[_PROP_IDX_H, :].copy()

    # ---- 有效温度范围 ---------------------------------------------------
    # 检查五物性是否同时有界（非 NaN），取交集
    valid_mask = np.all(~np.isnan(table), axis=0)  # (33,) bool
    if not np.any(valid_mask):
        raise MissingPropertyDataError(
            concentration=conc_used,
            message=f"浓度 {conc_used} 下全部物性均缺失有效数据",
        )
    valid_Ts = TEMP_NODES[valid_mask]
    Tmin = float(valid_Ts[0])
    Tmax = float(valid_Ts[-1])
    validity = bool(np.all(valid_mask))

    # ---- fb 值（冰点/沸点/质量浓度/体积浓度）-----------------------------
    # 按 concentration 是 volume frac 还是 mass frac 来决定插值基准
    volume_fraction = conc_used  # compile_mixture 的 concentration 参数是体积浓度
    mass_fraction = _fb_interp(volume_fraction, axis=1)  # 从体积浓度 → 质量浓度
    freezing_point = _fb_interp(volume_fraction, axis=2)
    boiling_point = _fb_interp(volume_fraction, axis=3)

    return CompiledEGMixture(
        conc=conc_used,
        table=table,
        dtable=dtable,
        h_nodes=h_nodes,
        Tmin=Tmin,
        Tmax=Tmax,
        validity=validity,
        freezing_point=freezing_point,
        boiling_point=boiling_point,
        mass_fraction=mass_fraction,
        volume_fraction=volume_fraction,
    )


# ---------------------------------------------------------------------------
# fb 内部插值 helper
# ---------------------------------------------------------------------------


def _fb_interp(volume_fraction: float, axis: int) -> float | None:
    """从体积浓度插值 fb 表的某个列（mass/volume/freezing/boiling）。

    返回 float 或 None（该列在查询区间缺失数据）。
    """
    # axis 0 = mass, 1 = volume, 2 = freezing, 3 = boiling
    x_col = 1  # fb vol sorted → x 轴是 volume frac
    data = _FB_RAW_VOL_SORTED
    x_lo = float(data[0, x_col])
    x_hi = float(data[-1, x_col])
    if not (x_lo <= volume_fraction <= x_hi):
        return None

    vals = data[:, axis]
    xs = data[:, x_col]
    # 找区间
    idx = int(np.searchsorted(xs, volume_fraction)) - 1
    idx = max(0, min(idx, len(xs) - 2))
    x_lo2 = float(xs[idx])
    x_hi2 = float(xs[idx + 1])
    y_lo = vals[idx]
    y_hi = vals[idx + 1]
    if np.isnan(y_lo) or np.isnan(y_hi):
        return None
    if x_hi2 == x_lo2:
        return float(y_lo)
    w = (volume_fraction - x_lo2) / (x_hi2 - x_lo2)
    return float(y_lo + (y_hi - y_lo) * w)
