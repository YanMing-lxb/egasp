"""egasp 核心 — 旧 API 保留 + compiled 内核桥接。

EGASP 类为 CLI / Excel / 脚本的主入口。prop() / props() 内部完全委托
compiled.compile_mixture()；fb_props() 保持 legacy 路径（需要质量↔体积双向查询）。
对外签名（prop / props / fb_props / concentration_type_to_chinese）保持完全兼容。
"""

from __future__ import annotations

import bisect
import logging
from typing import Any, ClassVar

import numpy as np

from egasp.compiled import compile_mixture
from egasp.data.egasp_data import EGP
from egasp.exceptions import (
    EGASPError,
    InvalidInputError,
    MissingPropertyDataError,
    PropertyOutOfRangeError,
)
from egasp.validate import clamp_or_raise, normalize_query_type, validate_prop_key

# ---------------------------------------------------------------------------
# 模块级常量（logging 辅助仍用 — 仅供 _log_missing_data_warning 边界检查）
# ---------------------------------------------------------------------------

_TEMP_NODES_LIST: list[float] = list(range(-35, 126, 5))
_CONC_NODES_LIST: list[float] = [round(0.1 + i * 0.1, 1) for i in range(9)]


# ---------------------------------------------------------------------------
# 底层插值工具（fb_props / logging 辅助共用）
# ---------------------------------------------------------------------------


def _interpolate_linear_static(
    x1: float, y1: float, x2: float, y2: float, x: float
) -> float:
    """纯数学线性插值。"""
    if x1 == x2:
        raise EGASPError(f"插值节点间距为零 x1={x1}, x2={x2}")
    return y1 + (y2 - y1) * (x - x1) / (x2 - x1)


# ---------------------------------------------------------------------------
# EGASP 类 — 旧公共 API 保持不变
# ---------------------------------------------------------------------------


_PROP_IDX_MAP: dict[str, int] = {"rho": 0, "cp": 1, "h": 2, "k": 3, "mu": 4}
_PROP_FN_MAP = {
    "rho": "rho",
    "cp": "cp",
    "h": "h",
    "k": "k",
    "mu": "mu",
}


class EGASP:
    """乙二醇水溶液属性查询主类（CLI / Excel / 脚本通用入口）。

    对外签名与旧版完全兼容：prop() / props() / fb_props() / concentration_type_to_chinese()。
    内部 prop/props 完全委托 compiled.compile_mixture() — 单一计算内核。
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

    # -- prop（compiled 内核委托）--------------------------------------------

    def prop(
        self,
        temp: float | np.ndarray,
        conc: float,
        egp_key: str,
    ) -> float | np.ndarray:
        """旧 API — 按指定属性名查询。

        完全委托 compiled.compile_mixture()，返回值为 float 或 ndarray。
        单位: mu 返回 Pa·s（与 compiled 内核一致）。
        超范围 raise PropertyOutOfRangeError；NaN/Inf raise InvalidInputError。
        """
        egp_key = validate_prop_key(egp_key)
        cm = compile_mixture(float(conc))
        # compiled 的单属性方法已处理 scalar/array 自动分支
        return getattr(cm, _PROP_FN_MAP[egp_key])(temp)

    # -- props（compiled 内核委托，一次 evaluate）---------------------------

    def props(
        self, query_temp: float, query_type: str = "volume", query_value: float = 0.5
    ) -> tuple[Any, ...]:
        """旧 API — 一次性返回所有属性。

        顺序: (mass, volume, freezing, boiling, rho, cp, k, mu, h) — legacy 兼容。
        内部一次 cm.evaluate() 取五属性。
        """
        query_type = normalize_query_type(query_type)
        query_value = clamp_or_raise(query_value, 0.1, 0.9, param="浓度")
        query_temp = clamp_or_raise(query_temp, -35.0, 125.0, param="温度")

        mass, volume, freezing, boiling = self.fb_props(
            query_value, query_type=query_type
        )

        cm = compile_mixture(float(volume))
        result = cm.evaluate(float(query_temp))  # (5,)
        rho = float(result[0])
        cp = float(result[1])
        h = float(result[2])
        k = float(result[3])
        mu = float(result[4])

        return (mass, volume, freezing, boiling, rho, cp, k, mu, h)

    # -- fb_props（legacy 路径 — 需要质量↔体积双向查询）---------------------

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

        self._log_fb_missing_warnings(lo_row, hi_row, query_type)
        return (mass, volume, freezing, boiling)

    # -- 日志辅助 -----------------------------------------------------------

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
