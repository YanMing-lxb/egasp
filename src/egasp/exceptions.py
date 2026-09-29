"""egasp 库级异常体系。

所有计算内核错误都用下面这些 Exception 子类抛出，不调用 sys.exit()。
CLI 的 main() 捕获 EGASPError 基类并转为友好打印。
"""

from __future__ import annotations

from typing import Any


class EGASPError(Exception):
    """egasp 所有库级异常的基类。"""


class PropertyOutOfRangeError(EGASPError):
    """温度 / 浓度等输入超出数据库有效范围。"""

    def __init__(
        self, value: float, lo: float, hi: float, *, param: str = "value"
    ) -> None:
        self.value = value
        self.lo = lo
        self.hi = hi
        self.param = param
        super().__init__(f"{param} {value} 超出有效范围 [{lo}, {hi}]")


class MissingPropertyDataError(EGASPError):
    """数据库在查询区域存在 NaN / None，插值无法进行。"""

    def __init__(
        self,
        *,
        temperature: float | None = None,
        concentration: float | None = None,
        prop_key: str | None = None,
        message: str | None = None,
    ) -> None:
        self.temperature = temperature
        self.concentration = concentration
        self.prop_key = prop_key
        parts: list[str] = []
        if temperature is not None:
            parts.append(f"温度 {temperature}")
        if concentration is not None:
            parts.append(f"浓度 {concentration}")
        if prop_key is not None:
            parts.append(f"属性 {prop_key}")
        loc = ", ".join(parts) if parts else "查询位置"
        detail = message or f"数据库在 {loc} 存在缺失数据 (NaN)"
        super().__init__(detail)


class InvalidInputError(EGASPError):
    """输入类型或取值非法（例如空字符串、未支持的 mode）。"""

    def __init__(self, message: str, *, value: Any | None = None) -> None:
        self.value = value
        super().__init__(message)


class CompilationError(EGASPError):
    """compile_mixture 编译阶段的内部错误。"""
