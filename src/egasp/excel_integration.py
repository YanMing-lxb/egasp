'''
 =======================================================================
 ····Y88b···d88P················888b·····d888·d8b·······················
 ·····Y88b·d88P·················8888b···d8888·Y8P·······················
 ······Y88o88P··················88888b·d88888···························
 ·······Y888P··8888b···88888b···888Y88888P888·888·88888b·····d88b·······
 ········888······"88b·888·"88b·888·Y888P·888·888·888·"88b·d88P"88b·····
 ········888···d888888·888··888·888··Y8P··888·888·888··888·888··888·····
 ········888··888··888·888··888·888···"···888·888·888··888·Y88b·888·····
 ········888··"Y888888·888··888·888·······888·888·888··888··"Y88888·····
 ································································888·····
 ····························································Y8b·d88P·····
 ·····························································"Y88P"······
 =======================================================================

 -----------------------------------------------------------------------
Author       : 焱铭
Date         : 2026-04-04
Description  : Excel/WPS表格集成模块 - 提供高性能、稳定的表格调用接口
 -----------------------------------------------------------------------
'''

import os
import sys
import json
import logging
import argparse
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime

from egasp.core import EGASP
from egasp.logger_config import setup_logger
from egasp.validate import Validate


# ===========================================================================
# 错误代码定义
# ===========================================================================
class ErrorCode(Enum):
    SUCCESS = 0
    INVALID_PARAMETER = 1001
    INVALID_CONCENTRATION_TYPE = 1002
    INVALID_CONCENTRATION_VALUE = 1003
    INVALID_TEMPERATURE = 1004
    INVALID_PROPERTY = 1005
    DATA_MISSING = 2001
    CALCULATION_ERROR = 2002
    IO_ERROR = 3001
    INTERNAL_ERROR = 9999

# 错误消息映射
ERROR_MESSAGES = {
    ErrorCode.SUCCESS: "操作成功",
    ErrorCode.INVALID_PARAMETER: "参数验证失败，请检查输入值是否正确",
    ErrorCode.INVALID_CONCENTRATION_TYPE: "无效的浓度类型，支持: volume/mass",
    ErrorCode.INVALID_CONCENTRATION_VALUE: "浓度值超出范围，有效范围: 0.1-0.9",
    ErrorCode.INVALID_TEMPERATURE: "温度超出范围，有效范围: -35°C ~ 125°C",
    ErrorCode.INVALID_PROPERTY: "无效的物性参数，支持: rho/cp/k/mu/mass/volume/freezing/boiling",
    ErrorCode.DATA_MISSING: "数据缺失，无法完成计算",
    ErrorCode.CALCULATION_ERROR: "计算错误，请检查输入参数",
    ErrorCode.IO_ERROR: "文件操作错误",
    ErrorCode.INTERNAL_ERROR: "内部错误，请联系开发者"
}

# 错误处理辅助函数
def get_error_message(error_code: ErrorCode, details: str = None) -> str:
    """获取错误消息"""
    base_message = ERROR_MESSAGES.get(error_code, "未知错误")
    if details:
        return f"{base_message}：{details}"
    return base_message


# ===========================================================================
# 数据类定义
# ===========================================================================
@dataclass
class PropertyRequest:
    """物性参数请求"""
    concentration_type: str = 'volume'
    concentration_value: float = 0.5
    temperature: float = 25.0
    property_name: str = 'rho'


@dataclass
class PropertyResult:
    """物性参数结果"""
    success: bool
    error_code: ErrorCode
    error_message: Optional[str] = None
    mass_concentration: Optional[float] = None
    volume_concentration: Optional[float] = None
    freezing_point: Optional[float] = None
    boiling_point: Optional[float] = None
    density: Optional[float] = None
    specific_heat: Optional[float] = None
    thermal_conductivity: Optional[float] = None
    viscosity: Optional[float] = None
    execution_time_ms: float = 0.0


@dataclass
class BatchRequest:
    """批量请求"""
    requests: List[PropertyRequest]
    return_full_data: bool = False


@dataclass
class BatchResult:
    """批量结果"""
    success: bool
    results: List[PropertyResult]
    total_count: int = 0
    success_count: int = 0
    error_count: int = 0
    total_execution_time_ms: float = 0.0


# ===========================================================================
# Excel集成核心类
# ===========================================================================
class ExcelIntegration:
    """Excel/WPS表格集成核心类"""

    # 支持的物性参数映射
    PROPERTY_MAP = {
        'mass': 'mass_concentration',
        'volume': 'volume_concentration',
        'freezing': 'freezing_point',
        'boiling': 'boiling_point',
        'rho': 'density',
        'cp': 'specific_heat',
        'k': 'thermal_conductivity',
        'mu': 'viscosity',
        # 别名支持
        'density': 'density',
        'specific_heat': 'specific_heat',
        'thermal_conductivity': 'thermal_conductivity',
        'viscosity': 'viscosity',
        'freezing_point': 'freezing_point',
        'boiling_point': 'boiling_point',
        'mass_concentration': 'mass_concentration',
        'volume_concentration': 'volume_concentration',
    }

    # 单位映射
    UNIT_MAP = {
        'mass_concentration': '%',
        'volume_concentration': '%',
        'freezing_point': '°C',
        'boiling_point': '°C',
        'density': 'kg/m³',
        'specific_heat': 'J/kg·K',
        'thermal_conductivity': 'W/m·K',
        'viscosity': 'Pa·s',
    }

    def __init__(self, verbose: bool = False, cache_size: int = 1000):
        self.logger = setup_logger(verbose)
        self.egasp = EGASP()
        self.validate = Validate()
        
        # 性能统计
        self._total_calls = 0
        self._total_time_ms = 0.0
        
        # 缓存系统
        self._cache = {}
        self._cache_size = cache_size
        self._cache_hits = 0
        self._cache_misses = 0

    def validate_request(self, request: PropertyRequest) -> Tuple[bool, ErrorCode, Optional[str]]:
        """
        验证请求参数
        
        Returns:
            (is_valid, error_code, error_message)
        """
        try:
            # 验证浓度类型
            conc_type = self.validate.type_value(request.concentration_type)
            if conc_type not in ['volume', 'mass']:
                return False, ErrorCode.INVALID_CONCENTRATION_TYPE, \
                       get_error_message(ErrorCode.INVALID_CONCENTRATION_TYPE, 
                       f"当前值: {request.concentration_type}")

            # 验证浓度值
            if not (0.1 <= request.concentration_value <= 0.9):
                return False, ErrorCode.INVALID_CONCENTRATION_VALUE, \
                       get_error_message(ErrorCode.INVALID_CONCENTRATION_VALUE, 
                       f"当前值: {request.concentration_value}")

            # 验证温度
            if not (-35 <= request.temperature <= 125):
                return False, ErrorCode.INVALID_TEMPERATURE, \
                       get_error_message(ErrorCode.INVALID_TEMPERATURE, 
                       f"当前值: {request.temperature}°C")

            # 验证物性参数
            prop_name = request.property_name.lower()
            if prop_name not in self.PROPERTY_MAP:
                return False, ErrorCode.INVALID_PROPERTY, \
                       get_error_message(ErrorCode.INVALID_PROPERTY, 
                       f"当前值: {request.property_name}")

            return True, ErrorCode.SUCCESS, None

        except Exception as e:
            return False, ErrorCode.INVALID_PARAMETER, \
                   get_error_message(ErrorCode.INVALID_PARAMETER, str(e))

    def calculate_single(self, request: PropertyRequest) -> PropertyResult:
        """计算单个物性参数"""
        import time
        start_time = time.perf_counter()
        
        # 验证请求
        is_valid, error_code, error_msg = self.validate_request(request)
        if not is_valid:
            return PropertyResult(
                success=False,
                error_code=error_code,
                error_message=error_msg,
                execution_time_ms=(time.perf_counter() - start_time) * 1000
            )

        # 检查缓存
        cached_result = self._check_cache(request)
        if cached_result:
            # 更新执行时间
            cached_result.execution_time_ms = (time.perf_counter() - start_time) * 1000
            # 更新统计
            self._total_calls += 1
            self._total_time_ms += cached_result.execution_time_ms
            return cached_result

        try:
            # 执行计算
            mass, volume, freezing, boiling, rho, cp, k, mu = self.egasp.props(
                request.temperature,
                request.concentration_type,
                request.concentration_value
            )

            # 构建结果
            result = PropertyResult(
                success=True,
                error_code=ErrorCode.SUCCESS,
                mass_concentration=mass * 100 if mass is not None else None,
                volume_concentration=volume * 100 if volume is not None else None,
                freezing_point=freezing,
                boiling_point=boiling,
                density=rho,
                specific_heat=cp,
                thermal_conductivity=k,
                viscosity=mu,
                execution_time_ms=(time.perf_counter() - start_time) * 1000
            )

            # 更新缓存
            self._update_cache(request, result)

            # 更新统计
            self._total_calls += 1
            self._total_time_ms += result.execution_time_ms

            return result

        except Exception as e:
            self.logger.exception(f"计算失败: {e}")
            return PropertyResult(
                success=False,
                error_code=ErrorCode.CALCULATION_ERROR,
                error_message=get_error_message(ErrorCode.CALCULATION_ERROR, str(e)),
                execution_time_ms=(time.perf_counter() - start_time) * 1000
            )

    def get_property_value(self, request: PropertyRequest) -> Optional[float]:
        """获取指定的单个物性值（简化接口）"""
        result = self.calculate_single(request)
        if not result.success:
            return None

        prop_key = self.PROPERTY_MAP.get(request.property_name.lower())
        if prop_key is None:
            return None

        return getattr(result, prop_key, None)

    def calculate_batch(self, batch_request: BatchRequest) -> BatchResult:
        """批量计算物性参数"""
        import time
        start_time = time.perf_counter()
        
        results = []
        success_count = 0
        error_count = 0

        for request in batch_request.requests:
            result = self.calculate_single(request)
            results.append(result)
            if result.success:
                success_count += 1
            else:
                error_count += 1

        total_time = (time.perf_counter() - start_time) * 1000

        return BatchResult(
            success=error_count == 0,
            results=results,
            total_count=len(results),
            success_count=success_count,
            error_count=error_count,
            total_execution_time_ms=total_time
        )

    def format_result(self, result: PropertyResult, 
                     include_metadata: bool = False) -> Dict[str, Any]:
        """格式化结果为字典"""
        data = {}
        
        if result.success:
            prop_fields = [
                'mass_concentration', 'volume_concentration',
                'freezing_point', 'boiling_point',
                'density', 'specific_heat',
                'thermal_conductivity', 'viscosity'
            ]
            
            for field in prop_fields:
                value = getattr(result, field, None)
                if value is not None:
                    unit = self.UNIT_MAP.get(field, '')
                    data[field] = {
                        'value': value,
                        'unit': unit
                    }
        else:
            data['error'] = {
                'code': result.error_code.value,
                'message': result.error_message
            }
        
        if include_metadata:
            data['metadata'] = {
                'execution_time_ms': result.execution_time_ms,
                'success': result.success
            }
        
        return data

    def _generate_cache_key(self, request: PropertyRequest) -> str:
        """生成缓存键"""
        return f"{request.concentration_type}:{request.concentration_value:.6f}:{request.temperature:.2f}"

    def _check_cache(self, request: PropertyRequest) -> Optional[PropertyResult]:
        """检查缓存"""
        cache_key = self._generate_cache_key(request)
        if cache_key in self._cache:
            self._cache_hits += 1
            return self._cache[cache_key]
        self._cache_misses += 1
        return None

    def _update_cache(self, request: PropertyRequest, result: PropertyResult):
        """更新缓存"""
        if len(self._cache) >= self._cache_size:
            # 简单的FIFO缓存淘汰策略
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        cache_key = self._generate_cache_key(request)
        self._cache[cache_key] = result

    def clear_cache(self):
        """清除缓存"""
        self._cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0

    def get_statistics(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        avg_time = self._total_time_ms / self._total_calls if self._total_calls > 0 else 0
        cache_hit_rate = self._cache_hits / (self._cache_hits + self._cache_misses) * 100 if (self._cache_hits + self._cache_misses) > 0 else 0
        return {
            'total_calls': self._total_calls,
            'total_time_ms': self._total_time_ms,
            'average_time_ms': avg_time,
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'cache_hit_rate': cache_hit_rate
        }


# ===========================================================================
# Excel调用入口函数
# ===========================================================================
def excel_main():
    """Excel/WPS调用的主入口"""
    parser = argparse.ArgumentParser(
        description='EGASP Excel/WPS集成接口',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 单个属性查询
  egasp --excel --type=volume --value=0.5 --temp=25 --prop=rho
  
  # 完整数据查询（JSON输出）
  egasp --excel --type=volume --value=0.5 --temp=25 --full
  
  # 批量查询（JSON输入）
  egasp --excel --batch --input=requests.json --output=results.json
  
  # 静默模式（只输出结果值）
  egasp --excel --type=volume --value=0.5 --temp=25 --prop=rho --quiet
        """
    )

    # 模式选择
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--single', action='store_true', help='单属性查询模式（默认）')
    mode_group.add_argument('--full', action='store_true', help='完整数据查询模式')
    mode_group.add_argument('--batch', action='store_true', help='批量查询模式')

    # 单属性/完整数据参数
    parser.add_argument('--type', type=str, default='volume', 
                       help='浓度类型 (volume/mass), 默认: volume')
    parser.add_argument('--value', type=float, default=0.5,
                       help='浓度值 (0.1-0.9), 默认: 0.5')
    parser.add_argument('--temp', type=float, required=False,
                       help='温度值 (-35 ~ 125°C)')
    parser.add_argument('--prop', type=str, default='rho',
                       help='物性参数 (rho/cp/k/mu/mass/volume/freezing/boiling), 默认: rho')

    # 批量模式参数
    parser.add_argument('--input', type=str, help='批量输入JSON文件路径')
    parser.add_argument('--output', type=str, help='批量输出JSON文件路径')

    # 输出控制
    parser.add_argument('--quiet', '-q', action='store_true', help='静默模式，只输出结果值')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出模式')
    parser.add_argument('--json', action='store_true', help='以JSON格式输出')

    args = parser.parse_args()

    # 初始化
    integration = ExcelIntegration(verbose=args.verbose)
    logger = integration.logger

    try:
        if args.batch:
            # 批量模式
            _handle_batch_mode(integration, args)
        elif args.full:
            # 完整数据模式
            _handle_full_mode(integration, args)
        else:
            # 单属性模式
            _handle_single_mode(integration, args)

    except Exception as e:
        logger.exception(f"执行失败: {e}")
        if not args.quiet:
            print(f"ERROR: {str(e)}", file=sys.stderr)
        sys.exit(1)


def _handle_single_mode(integration: ExcelIntegration, args):
    """处理单属性查询模式"""
    if args.temp is None:
        print("错误: 单属性模式必须指定 --temp 参数", file=sys.stderr)
        sys.exit(1)

    request = PropertyRequest(
        concentration_type=args.type,
        concentration_value=args.value,
        temperature=args.temp,
        property_name=args.prop
    )

    result = integration.calculate_single(request)

    if args.json:
        output = {
            'success': result.success,
            'error_code': result.error_code.value if result.error_code else None,
            'error_message': result.error_message,
            'value': integration.get_property_value(request),
            'execution_time_ms': result.execution_time_ms
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        if result.success:
            value = integration.get_property_value(request)
            if args.quiet:
                print(value)
            else:
                prop_key = integration.PROPERTY_MAP.get(request.property_name.lower(), request.property_name)
                unit = integration.UNIT_MAP.get(prop_key, '')
                print(f"{value} {unit}".strip())
        else:
            if args.quiet:
                print(f"#ERROR: {result.error_message}")
            else:
                print(f"错误 [{result.error_code.value}]: {result.error_message}", file=sys.stderr)
            # 不要退出，返回错误信息让调用方处理
            print(f"#ERROR: {result.error_message}")


def _handle_full_mode(integration: ExcelIntegration, args):
    """处理完整数据查询模式"""
    if args.temp is None:
        print("错误: 完整数据模式必须指定 --temp 参数", file=sys.stderr)
        sys.exit(1)

    request = PropertyRequest(
        concentration_type=args.type,
        concentration_value=args.value,
        temperature=args.temp,
        property_name='rho'  # 占位，实际会计算所有属性
    )

    result = integration.calculate_single(request)
    formatted = integration.format_result(result, include_metadata=True)
    
    if args.quiet:
        # 静默模式输出所有值，制表符分隔
        values = []
        for field in ['mass_concentration', 'volume_concentration', 'freezing_point', 
                     'boiling_point', 'density', 'specific_heat', 
                     'thermal_conductivity', 'viscosity']:
            val = formatted.get(field, {}).get('value', '#N/A')
            values.append(str(val))
        print('\t'.join(values))
    else:
        print(json.dumps(formatted, ensure_ascii=False, indent=2))


def _handle_batch_mode(integration: ExcelIntegration, args):
    """处理批量查询模式"""
    if not args.input:
        print("错误: 批量模式必须指定 --input 参数", file=sys.stderr)
        sys.exit(1)

    # 读取输入
    with open(args.input, 'r', encoding='utf-8') as f:
        input_data = json.load(f)

    # 构建批量请求
    requests = []
    for item in input_data:
        req = PropertyRequest(
            concentration_type=item.get('type', 'volume'),
            concentration_value=float(item.get('value', 0.5)),
            temperature=float(item.get('temp', 25.0)),
            property_name=item.get('prop', 'rho')
        )
        requests.append(req)

    batch_request = BatchRequest(requests=requests, return_full_data=True)
    batch_result = integration.calculate_batch(batch_request)

    # 构建输出
    output = {
        'success': batch_result.success,
        'total_count': batch_result.total_count,
        'success_count': batch_result.success_count,
        'error_count': batch_result.error_count,
        'total_execution_time_ms': batch_result.total_execution_time_ms,
        'results': []
    }

    for result in batch_result.results:
        output['results'].append(integration.format_result(result, include_metadata=True))

    # 写入输出或打印
    output_str = json.dumps(output, ensure_ascii=False, indent=2)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output_str)
        if not args.quiet:
            print(f"批量计算完成，结果已写入: {args.output}")
    else:
        print(output_str)


# ===========================================================================
# 便捷函数 - 直接从Python调用
# ===========================================================================
def get_property(concentration_type: str, concentration_value: float, 
                temperature: float, property_name: str) -> Optional[float]:
    """
    便捷函数：获取单个物性参数值
    
    Args:
        concentration_type: 浓度类型 ('volume' 或 'mass')
        concentration_value: 浓度值 (0.1-0.9)
        temperature: 温度值 (-35 ~ 125°C)
        property_name: 物性参数名称
    
    Returns:
        物性参数值，失败返回None
    """
    integration = ExcelIntegration()
    request = PropertyRequest(
        concentration_type=concentration_type,
        concentration_value=concentration_value,
        temperature=temperature,
        property_name=property_name
    )
    return integration.get_property_value(request)


def get_all_properties(concentration_type: str, concentration_value: float, 
                      temperature: float) -> Optional[Dict[str, Any]]:
    """
    便捷函数：获取所有物性参数
    
    Args:
        concentration_type: 浓度类型 ('volume' 或 'mass')
        concentration_value: 浓度值 (0.1-0.9)
        temperature: 温度值 (-35 ~ 125°C)
    
    Returns:
        包含所有物性参数的字典，失败返回None
    """
    integration = ExcelIntegration()
    request = PropertyRequest(
        concentration_type=concentration_type,
        concentration_value=concentration_value,
        temperature=temperature,
        property_name='rho'
    )
    result = integration.calculate_single(request)
    if result.success:
        return integration.format_result(result)
    return None


if __name__ == '__main__':
    excel_main()
