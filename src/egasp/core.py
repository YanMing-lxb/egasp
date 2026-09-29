"""egasp 核心 — 旧 API 保留 + 新 compiled 内核桥接。

EGASP 类当前仍为 CLI/Excel 的主入口。内部逐步委托给 compiled.compile_mixture，
但对外签名（prop / props / fb_props）保持完全兼容。
"""

from __future__ import annotations

import bisect
import logging
from functools import lru_cache
from typing import Any, ClassVar

import numpy as np

from egasp.data.egasp_data import EGP
from egasp.exceptions import (
    EGASPError,
    InvalidInputError,
    MissingPropertyDataError,
    PropertyOutOfRangeError,
)
from egasp.validate import clamp_or_raise, normalize_query_type, validate_prop_key

# ---------------------------------------------------------------------------
# 模块级数据表（首次访问时从 Python nested list 转成 numpy）
# ---------------------------------------------------------------------------

_TEMP_NODES_LIST: list[float] = list(range(-35, 126, 5))
_CONC_NODES_LIST: list[float] = [round(0.1 + i * 0.1, 1) for i in range(9)]

_rho_array: np.ndarray | None = None
_cp_array: np.ndarray | None = None
_h_array: np.ndarray | None = None
_k_array: np.ndarray | None = None
_mu_array: np.ndarray | None = None
_array_map: dict[str, np.ndarray] | None = None


def _init_class_data() -> None:
    """首次访问时把 EGP dict 转成 numpy float64 数组。"""
    global _rho_array, _cp_array, _h_array, _k_array, _mu_array, _array_map
    if _rho_array is None:
        _rho_array = np.array(EGP["rho"], dtype=np.float64)
        _cp_array = np.array(EGP["cp"], dtype=np.float64)
        _h_array = np.array(EGP["h"], dtype=np.float64)
        _k_array = np.array(EGP["k"], dtype=np.float64)
        _mu_array = np.array(EGP["mu"], dtype=np.float64)
        _array_map = {
            "rho": _rho_array,
            "cp": _cp_array,
            "h": _h_array,
            "k": _k_array,
            "mu": _mu_array,
        }


# ---------------------------------------------------------------------------
# 底层插值工具（给 scalar compatibility path 和 compiled.py 共用）
# ---------------------------------------------------------------------------


def _interpolate_linear_static(
    x1: float, y1: float, x2: float, y2: float, x: float
) -> float:
    """纯数学线性插值。"""
    if x1 == x2:
        raise EGASPError(f"插值节点间距为零 x1={x1}, x2={x2}")
    return y1 + (y2 - y1) * (x - x1) / (x2 - x1)


def _find_nearest_nodes_static(
    nodes: list[float], value: float, *, param: str = "value"
) -> tuple[int, int]:
    """返回 value 在有序节点列表中的 (lower_idx, upper_idx)。

    超范围 raise PropertyOutOfRangeError，节点越界 raise EGASPError。
    """
    lo_node, hi_node = nodes[0], nodes[-1]
    if not (lo_node <= value <= hi_node):
        raise PropertyOutOfRangeError(value, lo_node, hi_node, param=param)
    idx = bisect.bisect_right(nodes, value) - 1
    lower_idx = max(idx, 0)
    upper_idx = min(bisect.bisect_left(nodes, value), len(nodes) - 1)
    return lower_idx, upper_idx


@lru_cache(maxsize=1024)
def _cached_prop_single(temp: float, conc: float, egp_key: str) -> float | None:
    """标量兼容性路径 — 旧 API 逐属性查表。

    LRU cache 命中率低（温度浮点每轮变），仅供 CLI / Excel 小量查询。
    新求解器 hot path 应走 compiled.compile_mixture().evaluate()。
    """
    _init_class_data()
    assert _array_map is not None

    t_lo, t_hi = _find_nearest_nodes_static(_TEMP_NODES_LIST, temp, param="温度")
    c_lo, c_hi = _find_nearest_nodes_static(_CONC_NODES_LIST, conc, param="浓度")

    data_array = _array_map[egp_key]
    v11 = data_array[t_lo, c_lo]
    v12 = data_array[t_lo, c_hi]
    v21 = data_array[t_hi, c_lo]
    v22 = data_array[t_hi, c_hi]

    if np.isnan(v11) or np.isnan(v21) or np.isnan(v12) or np.isnan(v22):
        return None

    t_lo_val = _TEMP_NODES_LIST[t_lo]
    t_hi_val = _TEMP_NODES_LIST[t_hi]
    c_lo_val = _CONC_NODES_LIST[c_lo]
    c_hi_val = _CONC_NODES_LIST[c_hi]

    if t_lo_val == t_hi_val and c_lo_val == c_hi_val:
        result = v11
    elif t_lo_val == t_hi_val:
        result = _interpolate_linear_static(c_lo_val, v11, c_hi_val, v12, conc)
    elif c_lo_val == c_hi_val:
        result = _interpolate_linear_static(t_lo_val, v11, t_hi_val, v21, temp)
    else:
        v1 = _interpolate_linear_static(c_lo_val, v11, c_hi_val, v12, conc)
        v2 = _interpolate_linear_static(c_lo_val, v21, c_hi_val, v22, conc)
        result = _interpolate_linear_static(t_lo_val, v1, t_hi_val, v2, temp)
    return result


# ---------------------------------------------------------------------------
# EGASP 类 — 旧公共 API 保持不变
# ---------------------------------------------------------------------------


class EGASP:
    """乙二醇水溶液属性查询主类（CLI / Excel / 脚本通用入口）。

    对外签名与旧版完全兼容：prop() / props() / fb_props() / concentration_type_to_chinese()。
    内部 scalar 查询继续用 _cached_prop_single（legacy path），批量数组建议走
    egasp.compile_mixture().evaluate()。
    """

    _PROP_KEYS: tuple[str, ...] = ("rho", "cp", "h", "k", "mu")

    _PROP_LABEL: ClassVar[dict[str, str]] = {
        "rho": "密度",
        "cp": "比热容",
        "h": "焓",
        "k": "导热系数",
        "mu": "动力粘度",
    }

    _TYPE_LABEL: ClassVar[dict[str, str]] = {
        "volume": "体积浓度",
        "mass": "质量浓度",
    }

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        _init_class_data()
        self.temp_nodes = _TEMP_NODES_LIST
        self.conc_nodes = _CONC_NODES_LIST
        self.rho_array = _rho_array
        self.cp_array = _cp_array
        self.h_array = _h_array
        self.k_array = _k_array
        self.mu_array = _mu_array
        self.array_map = _array_map

    # -- 公开静态工具 -------------------------------------------------------

    @staticmethod
    def concentration_type_to_chinese(concentration_type: str) -> str:
        """'volume'/'v'/'mass'/'m' → 中文标签。"""
        label = EGASP._TYPE_LABEL.get(concentration_type.lower())
        if label is None:
            raise InvalidInputError(
                f"不支持的浓度类型: {concentration_type}，支持的类型有: volume/v, mass/m"
            )
        return label

    # -- prop ---------------------------------------------------------------

    def prop(
        self,
        temp: float | np.ndarray,
        conc: float,
        egp_key: str,
    ) -> float | np.ndarray | None:
        """旧 API — 按指定属性名查询。

        float 输入返回 float 或 None（数据缺失）；ndarray 输入返回同形状 ndarray。
        mu 属性内部已统一用 Pa·s（egasp_data.py 初始化时转换）。
        """
        egp_key = validate_prop_key(egp_key)

        _to_pa_s = egp_key == "mu"  # 原始 mu 数据单位 mPa·s，旧 API 统一返回 Pa·s

        if isinstance(temp, np.ndarray):
            result = np.vectorize(
                lambda t: _cached_prop_single(float(t), float(conc), egp_key),
                otypes=[np.float64],
            )(temp)
            if _to_pa_s:
                result = result / 1000.0
            return result

        # scalar
        try:
            result = _cached_prop_single(float(temp), float(conc), egp_key)
        except PropertyOutOfRangeError as exc:
            # 旧 API 语义：越界 raise
            raise exc from None

        if result is None:
            self._log_missing_data_warning(float(temp), float(conc), egp_key)
            return None
        return result / 1000.0 if _to_pa_s else result

    # -- fb_props -----------------------------------------------------------

    def fb_props(
        self, query: float, query_type: str = "volume"
    ) -> tuple[float | None, float | None, float | None, float | None]:
        """按浓度查询冰点 / 沸点 / 质量浓度 / 体积浓度。"""
        query_type = normalize_query_type(query_type)

        data = EGP.get("fb")
        if data is None:
            raise MissingPropertyDataError(message="数据库无冰点/沸点数据")

        sort_key = 1 if query_type == "volume" else 0
        sorted_data = sorted(data, key=lambda row: row[sort_key])
        sorted_values = np.array(
            [row[sort_key] for row in sorted_data], dtype=np.float64
        )

        if query < float(sorted_values[0]) or query > float(sorted_values[-1]):
            lo, hi = float(sorted_values[0]), float(sorted_values[-1])
            raise PropertyOutOfRangeError(
                float(query), lo, hi, param=f"浓度 ({query_type})"
            )

        idx = bisect.bisect_left(sorted_values, float(query))
        if idx == 0:
            idx = 1
        if idx == len(sorted_data):
            idx = len(sorted_data) - 1

        prev, curr = sorted_data[idx - 1], sorted_data[idx]

        # 同一区间
        lo_row = sorted_data[idx - 1]
        hi_row = sorted_data[idx]

        if query_type == "volume":
            mass = _interp_or_none(prev[1], prev[0], curr[1], curr[0], float(query))
            volume = float(query)
            freezing = _interp_or_none(prev[1], prev[2], curr[1], curr[2], float(query))
            boiling = _interp_or_none(prev[1], prev[3], curr[1], curr[3], float(query))
        else:
            volume = _interp_or_none(prev[0], prev[1], curr[0], curr[1], float(query))
            mass = float(query)
            freezing = _interp_or_none(prev[0], prev[2], curr[0], curr[2], float(query))
            boiling = _interp_or_none(prev[0], prev[3], curr[0], curr[3], float(query))

        # 缺失字段 warning — 仅记日志，不 raise
        self._log_fb_missing_warnings(lo_row, hi_row, query_type)
        return (mass, volume, freezing, boiling)

    # -- props --------------------------------------------------------------

    def props(
        self, query_temp: float, query_type: str = "volume", query_value: float = 0.5
    ) -> tuple[Any, ...]:
        """旧 API — 一次性返回所有属性。"""
        query_type = normalize_query_type(query_type)
        query_value = clamp_or_raise(query_value, 0.1, 0.9, param="浓度")
        query_temp = clamp_or_raise(query_temp, -35.0, 125.0, param="温度")

        mass, volume, freezing, boiling = self.fb_props(
            query_value, query_type=query_type
        )
        rho = self.prop(temp=query_temp, conc=volume, egp_key="rho")
        cp = self.prop(temp=query_temp, conc=volume, egp_key="cp")
        h = self.prop(temp=query_temp, conc=volume, egp_key="h")
        k = self.prop(temp=query_temp, conc=volume, egp_key="k")
        mu = self.prop(temp=query_temp, conc=volume, egp_key="mu")
        return (mass, volume, freezing, boiling, rho, cp, k, mu, h)

    # -- 日志辅助 -----------------------------------------------------------

    def _log_missing_data_warning(self, temp: float, conc: float, egp_key: str) -> None:
        """当四角存在 NaN 时记录 warning。"""
        t_lo, t_hi = _find_nearest_nodes_static(_TEMP_NODES_LIST, temp, param="温度")
        c_lo, c_hi = _find_nearest_nodes_static(_CONC_NODES_LIST, conc, param="浓度")

        prop_label = self._PROP_LABEL.get(egp_key, egp_key)

        assert _array_map is not None
        data_array = _array_map[egp_key]
        if np.isnan(data_array[t_lo, c_lo]) or np.isnan(data_array[t_hi, c_lo]):
            self.logger.warning(
                "数据库在浓度 %s 下温度 %s ~ %s 范围内 %s 数据缺失",
                _CONC_NODES_LIST[c_lo],
                _TEMP_NODES_LIST[t_lo],
                _TEMP_NODES_LIST[t_hi],
                prop_label,
            )
        if np.isnan(data_array[t_lo, c_hi]) or np.isnan(data_array[t_hi, c_hi]):
            self.logger.warning(
                "数据库在浓度 %s 下温度 %s ~ %s 范围内 %s 数据缺失",
                _CONC_NODES_LIST[c_hi],
                _TEMP_NODES_LIST[t_lo],
                _TEMP_NODES_LIST[t_hi],
                prop_label,
            )

    def _log_fb_missing_warnings(
        self, lo_row: tuple[Any, ...], hi_row: tuple[Any, ...], query_type: str
    ) -> None:
        field_names = ["质量浓度", "体积浓度", "冰点", "沸点"]
        for col, name in enumerate(field_names):
            lo_v, hi_v = lo_row[col], hi_row[col]
            if None in (lo_v, hi_v):
                lo_key = 1 if query_type == "volume" else 0
                self.logger.warning(
                    "数据库在%s %s ~ %s 范围内 %s 数据缺失",
                    self.concentration_type_to_chinese(query_type),
                    lo_row[lo_key],
                    hi_row[lo_key],
                    name,
                )


# ---------------------------------------------------------------------------
# fb_props 内部插值的 None-safe helper
# ---------------------------------------------------------------------------


def _interp_or_none(x1: Any, y1: Any, x2: Any, y2: Any, x: float) -> float | None:
    """任何 y 端为 None 时直接返回 None。"""
    if y1 is None or y2 is None:
        return None
    return _interpolate_linear_static(float(x1), float(y1), float(x2), float(y2), x)
