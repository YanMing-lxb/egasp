"""egasp 库级入口 — 轻量，仅导入 numpy/data/core/compiled。

CLI 入口通过 ``python -m egasp`` 触发（即 ``__main__.py``），不在本文件 eager 导入。
这样 ``import egasp`` 的启动时间从 ~1.6s 降到 <100ms。
"""

from egasp.compiled import CompiledEGMixture, PropertyWorkspace, compile_mixture
from egasp.core import EGASP
from egasp.exceptions import (
    CompilationError,
    EGASPError,
    InvalidInputError,
    MissingPropertyDataError,
    PropertyOutOfRangeError,
)

# 模块级兼容单例 — 供 CLI / Excel / 脚本使用
_eg = EGASP()
prop = _eg.prop
props = _eg.props
fb_props = _eg.fb_props
concentration_type_to_chinese = EGASP.concentration_type_to_chinese


def main() -> None:
    """CLI 入口 — lazy import __main__，避免核心 import 路径携带 rich/argparse。"""
    from egasp.__main__ import main as _cli_main

    _cli_main()


__all__ = [
    # 旧 API 兼容
    "EGASP",
    "CompilationError",
    "CompiledEGMixture",
    "EGASPError",
    "InvalidInputError",
    "MissingPropertyDataError",
    "PropertyOutOfRangeError",
    "PropertyWorkspace",
    "compile_mixture",
    "concentration_type_to_chinese",
    "fb_props",
    "main",
    "prop",
    "props",
]
