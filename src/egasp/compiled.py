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
    InvalidInputError,
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
    所有内部 ndarray 在构造完成后均设 writeable=False，防止外部修改污染缓存。
    """

    conc: float
    table: np.ndarray  # (5, 33) 固定浓度下的五物性温度节点值
    dtable: np.ndarray  # (5, 33) 区间内导数（legacy-linear 下为常数）
    h_nodes: np.ndarray  # (33,) h 表，供 temperature_from_h() 反解
    # --- 公共有效域（五物性同时有效）---
    Tmin: float
    Tmax: float
    validity: bool  # 整个 [Tmin, Tmax] 内五物性均无 NaN
    # --- 每属性独立有效温度节点索引 ---
    valid_start_idx: np.ndarray  # (5,) 每属性第一个有效 T 节点索引
    valid_end_idx: np.ndarray  # (5,) 每属性最后一个有效 T 节点索引
    # --- temperature_from_h 专用 ---
    h_valid_idx: np.ndarray  # h 有效的温度节点索引切片
    hmin: float
    hmax: float
    h_mono: bool  # 编译阶段验证：h_valid 是否严格单调递增
    # --- fb 值 ---
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
        超出五物性公共有效域 raise PropertyOutOfRangeError。
        NaN/Inf raise InvalidInputError。
        """
        T_arr = np.asarray(T, dtype=np.float64)
        is_scalar = T_arr.ndim == 0
        if is_scalar:
            T_arr = T_arr.reshape(1)
        self._check_range_common(T_arr)
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
        self._check_range_common(T_arr)
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
        """壁面粘度专用 fast path — 只计算 mu（检查公共域）。"""
        T_arr = np.asarray(T, dtype=np.float64).ravel()
        self._check_range_common(T_arr)
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

        仅在编译阶段已识别的有效 h slice 上搜索；
        超出 [hmin, hmax]  raise PropertyOutOfRangeError；
        h 含 NaN/Inf raise InvalidInputError。
        legacy-linear 模式下与 PHEx 现有二分反解等价，数值误差在 1e-12 量级。
        """
        h_arr = np.asarray(h, dtype=np.float64)
        is_scalar = h_arr.ndim == 0
        h_vals = h_arr[None] if is_scalar else h_arr

        if not np.all(np.isfinite(h_vals)):
            raise InvalidInputError("焓值包含 NaN 或 inf")

        # 严格范围检查 — 不做外推
        lo_viol = np.min(h_vals) < self.hmin
        hi_viol = np.max(h_vals) > self.hmax
        if lo_viol or hi_viol:
            viol = np.min(h_vals) if lo_viol else np.max(h_vals)
            raise PropertyOutOfRangeError(float(viol), self.hmin, self.hmax, param="焓")

        # 用有效 h slice 做 searchsorted（要求单调，编译阶段已验证）
        h_valid_nodes = self.h_nodes[self.h_valid_idx]  # 已切到纯值段
        T_valid_nodes = TEMP_NODES[self.h_valid_idx]
        idx = np.searchsorted(h_valid_nodes, h_vals) - 1
        idx = np.clip(idx, 0, len(h_valid_nodes) - 2)
        h_lo = h_valid_nodes[idx]
        h_hi = h_valid_nodes[idx + 1]
        T_lo = T_valid_nodes[idx]
        T_hi = T_valid_nodes[idx + 1]
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
        self._check_range_prop(T_arr, prop_idx)
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
        self._check_range_common(T_arr)
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
        self._check_range_prop(T_arr, prop_idx)
        idx, w = self._temp_index(T_arr)
        lo = self.table[prop_idx, idx]
        hi = self.table[prop_idx, idx + 1]
        result = lo + (hi - lo) * w
        return float(result[0]) if is_scalar else result

    # ---- 有效域检查 ---------------------------------------------------

    def _check_range_common(self, T_arr: np.ndarray) -> None:
        """五物性公共有效域 + NaN/Inf 检查。"""
        if T_arr.size == 0:
            return
        if not np.all(np.isfinite(T_arr)):
            raise InvalidInputError("温度包含 NaN 或 inf")
        lo_viol = np.min(T_arr) < self.Tmin
        hi_viol = np.max(T_arr) > self.Tmax
        if lo_viol or hi_viol:
            viol = np.min(T_arr) if lo_viol else np.max(T_arr)
            raise PropertyOutOfRangeError(
                float(viol), self.Tmin, self.Tmax, param="温度"
            )

    def _check_range_prop(self, T_arr: np.ndarray, prop_idx: int) -> None:
        """单属性有效域 + NaN/Inf 检查。"""
        if T_arr.size == 0:
            return
        if not np.all(np.isfinite(T_arr)):
            raise InvalidInputError("温度包含 NaN 或 inf")
        lo_node = TEMP_NODES[int(self.valid_start_idx[prop_idx])]
        hi_node = TEMP_NODES[int(self.valid_end_idx[prop_idx])]
        lo_viol = np.min(T_arr) < lo_node
        hi_viol = np.max(T_arr) > hi_node
        if lo_viol or hi_viol:
            viol = np.min(T_arr) if lo_viol else np.max(T_arr)
            raise PropertyOutOfRangeError(float(viol), lo_node, hi_node, param="温度")


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

    # ---- 每属性独立有效温区 ---------------------------------------------
    # 对 table 每行 (每属性)，找 first valid / last valid T 节点索引
    valid_start_idx = np.empty(_N_PROPS, dtype=np.intp)
    valid_end_idx = np.empty(_N_PROPS, dtype=np.intp)
    for p in range(_N_PROPS):
        row = table[p, :]
        valid_mask = ~np.isnan(row)
        if not np.any(valid_mask):
            raise MissingPropertyDataError(
                concentration=conc_used,
                message=f"浓度 {conc_used} 下属性 {p} 无有效数据",
            )
        first = int(np.argmax(valid_mask))
        # np.argmax 找到第一个 True；找最后一个：翻转后 argmax
        last = int(len(row) - 1 - np.argmax(valid_mask[::-1]))
        # 验证中间无 NaN（数据表要求连续有效域）
        if not np.all(valid_mask[first : last + 1]):
            raise CompilationError(
                f"浓度 {conc_used} 属性 {p} 的有效温度区间不连续（中间存在 NaN）"
            )
        valid_start_idx[p] = first
        valid_end_idx[p] = last

    # ---- 公共有效域（五物性同时有效）-------------------------------------
    common_start = int(np.max(valid_start_idx))
    common_end = int(np.min(valid_end_idx))
    Tmin = float(TEMP_NODES[common_start])
    Tmax = float(TEMP_NODES[common_end])
    # validity = 全部 33 节点均有效
    validity = bool(common_start == 0 and common_end == len(TEMP_NODES) - 1)

    # ---- temperature_from_h 专用 ----------------------------------------
    # h 有效 slice（跳过前导/尾随 NaN）
    h_row = h_nodes
    h_valid_mask = ~np.isnan(h_row)
    if not np.any(h_valid_mask):
        raise MissingPropertyDataError(
            concentration=conc_used,
            message=f"浓度 {conc_used} 下焓数据全部缺失",
        )
    h_first = int(np.argmax(h_valid_mask))
    h_last = int(len(h_row) - 1 - np.argmax(h_valid_mask[::-1]))
    h_valid_idx = np.arange(h_first, h_last + 1, dtype=np.intp)
    # 验证 h 在有效区间内严格递增（否则 searchsorted 语义不成立）
    h_valid_vals = h_row[h_valid_idx]
    if len(h_valid_vals) < 2:
        raise CompilationError(f"浓度 {conc_used} 下有效焓节点不足 2 个，无法反解")
    h_mono = bool(np.all(np.diff(h_valid_vals) > 0))
    if not h_mono:
        raise CompilationError(f"浓度 {conc_used} 下焓数据非严格单调递增，无法安全反解")
    hmin = float(h_valid_vals[0])
    hmax = float(h_valid_vals[-1])

    # ---- fb 值（冰点/沸点/质量浓度/体积浓度）-----------------------------
    volume_fraction = conc_used
    mass_fraction = _fb_interp(volume_fraction, axis=0)  # axis=0 = mass
    freezing_point = _fb_interp(volume_fraction, axis=2)
    boiling_point = _fb_interp(volume_fraction, axis=3)

    # ---- 构造 + 设置所有数组为 readonly ----------------------------------
    result = CompiledEGMixture(
        conc=conc_used,
        table=table,
        dtable=dtable,
        h_nodes=h_nodes,
        Tmin=Tmin,
        Tmax=Tmax,
        validity=validity,
        valid_start_idx=valid_start_idx,
        valid_end_idx=valid_end_idx,
        h_valid_idx=h_valid_idx,
        hmin=hmin,
        hmax=hmax,
        h_mono=h_mono,
        freezing_point=freezing_point,
        boiling_point=boiling_point,
        mass_fraction=mass_fraction,
        volume_fraction=volume_fraction,
    )

    # 防止 LRU 缓存对象被外部修改
    for arr in (
        result.table,
        result.dtable,
        result.h_nodes,
        result.valid_start_idx,
        result.valid_end_idx,
        result.h_valid_idx,
    ):
        arr.flags.writeable = False

    return result


# ---------------------------------------------------------------------------
# fb 内部插值 helper
# ---------------------------------------------------------------------------


def _fb_interp(volume_fraction: float, axis: int) -> float | None:
    """从体积浓度插值 fb 表的某个列（mass/volume/freezing/boiling）。

    返回 float 或 None（该列在查询区间缺失数据）。
    支持 exact node hit — 查询值恰为数据库节点时直接返回节点值，
    不被相邻节点 NaN 阻断。
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

    # ---- exact node hit 优先 ----
    hit = np.flatnonzero(np.isclose(xs, volume_fraction))
    if hit.size > 0:
        v = float(vals[int(hit[0])])
        if np.isnan(v):
            return None
        return v

    # ---- 非节点值：searchsorted + 两端有效检查 ----
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
