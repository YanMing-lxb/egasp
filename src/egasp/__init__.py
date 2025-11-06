'''
一款用于获取乙二醇水溶液物性参数的工具
可用函数 props()
'''

import sys
from .core import EGASP

# 实例化核心类
eg = EGASP()

# 将指定方法暴露为模块级别的函数
prop = eg.prop
props = eg.props  # 直接暴露 props 函数

if sys.version_info[0] == 3:
    from .__main__ import main  # 显式导出 main() 供 CLI 入口使用
else:
    # Don't import anything.
    pass