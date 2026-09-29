"""输入规范化与校验 — 纯函数，零 logger 依赖。"""

from __future__ import annotations

from typing import Final

from egasp.exceptions import InvalidInputError, PropertyOutOfRangeError

_VALID_TYPES: Final[dict[str, str]] = {
    "volume": "volume",
    "v": "volume",
    "mass": "mass",
    "m": "mass",
}

_PROP_KEY_MAP: Final[dict[str, str]] = {
    "rho": "rho",
    "cp": "cp",
    "h": "h",
    "k": "k",
    "mu": "mu",
}


def normalize_query_type(query_type: str, default: str = "volume") -> str:
    """将 CLI/用户输入的查询类型规范化为 'volume' / 'mass'。

    空字符串或合法别名返回规范化值；非法值 raise InvalidInputError。
    """
    if query_type == "":
        return default
    key = query_type.lower()
    if key not in _VALID_TYPES:
        raise InvalidInputError(
            f"无效查询类型 '{query_type}'，支持的值: volume/v/mass/m"
        )
    return _VALID_TYPES[key]


def validate_prop_key(key: str) -> str:
    """规范化物性 key；非法值 raise InvalidInputError。"""
    if key not in _PROP_KEY_MAP:
        raise InvalidInputError(f"无效物性参数 '{key}'，可选值: rho/cp/h/k/mu")
    return _PROP_KEY_MAP[key]


def clamp_or_raise(
    value: float,
    lo: float,
    hi: float,
    *,
    param: str = "value",
    raise_on_out_of_range: bool = True,
) -> float:
    """检查 value ∈ [lo, hi]，超范围默认 raise PropertyOutOfRangeError。

    raise_on_out_of_range=False 时改为 silent clamp（仅用于极少数 legacy 场景）。
    """
    if value < lo or value > hi:
        if raise_on_out_of_range:
            raise PropertyOutOfRangeError(value, lo, hi, param=param)
        return min(max(value, lo), hi)
    return value
