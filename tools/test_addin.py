#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
 =======================================================================
 ····Y88b···d88P················888b·····d888·d8b·······················
 ·····Y88b·d88P·················8888b···d8888·Y8P·······················
 ······Y88o88P··················88888b·d88888···························
 ·······Y888P··8888b···88888b···888Y88888P888·888·88888b·····d88b·······
 ········888······"88b·888·"88b·888·Y888P·888·888·888·"88b·d88P"88b·····
 ········888···d888888·888··888·888··Y8P··888·888·888··888·888··888·····
 ········888··888··888·888··888·888···"···888·888·888··888·Y88b·888·····
 ········888··"Y888888·888··888·888·······888·888·888··888··"Y88888·····
 ·······························································888·····
 ··························································Y8b·d88P·····
 ···························································"Y88P"······
 =======================================================================

 -----------------------------------------------------------------------
Author       : 焱铭
Date         : 2026-04-05
LastEditTime : 2026-04-05
Github       : https://github.com/YanMing-lxb/
FilePath     : /egasp/tools/test_addin.py
Description  : Excel/WPS 插件测试工具
 -----------------------------------------------------------------------
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from rich.console import Console
from rich.theme import Theme

# 定义自定义主题
custom_theme = Theme({
    "success": "bold green",
    "warning": "bold yellow",
    "error": "bold red",
    "info": "bold blue",
    "status": "bold cyan",
})

# 创建控制台实例
console = Console(theme=custom_theme)

project_root = Path(__file__).parent.parent

# 辅助函数
def print_header(text):
    """打印标题栏"""
    console.rule(f"[bold]{text}[/]")

def print_step(text):
    """打印步骤信息"""
    console.print(f"[*] {text}")

def print_success(text):
    """打印成功信息"""
    console.print(f"[+] {text}", style="success")

def print_error(text):
    """打印错误信息"""
    console.print(f"[-] {text}", style="error")

def print_warning(text):
    """打印警告信息"""
    console.print(f"[!] {text}", style="warning")

# 安全性测试类
class SecurityTester:
    """安全性测试类"""
    
    def test_command_injection(self):
        """测试命令注入漏洞"""
        print_step("测试命令注入漏洞...")
        
        # 测试恶意输入
        test_cases = [
            # 尝试命令注入
            ("volume; echo 'injection'", 0.5, 25, "rho"),
            ("volume && echo 'injection'", 0.5, 25, "rho"),
            ("volume || echo 'injection'", 0.5, 25, "rho"),
            # 尝试路径遍历
            ("../../../../etc/passwd", 0.5, 25, "rho"),
            # 尝试特殊字符
            ("volume'\";'echo injection'", 0.5, 25, "rho"),
        ]
        
        for i, (concentration_type, concentration_value, temperature, property_name) in enumerate(test_cases, 1):
            print_step(f"测试用例 {i}: 尝试注入恶意命令")
            
            # 构建测试命令
            cmd = [
                sys.executable,
                str(project_root / "src" / "egasp" / "cli.py"),
                "--excel",
                "--single",
                f"--type={concentration_type}",
                f"--value={concentration_value}",
                f"--temp={temperature}",
                f"--prop={property_name}",
                "--quiet"
            ]
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=5
                )
                
                # 检查输出是否包含注入的命令结果
                if "injection" in result.stdout or "injection" in result.stderr:
                    print_error(f"测试用例 {i}: 命令注入漏洞存在！")
                else:
                    print_success(f"测试用例 {i}: 命令注入测试通过")
                    
            except Exception as e:
                print_error(f"测试用例 {i}: 测试失败: {e}")
    
    def test_input_validation(self):
        """测试输入验证"""
        print_step("测试输入验证...")
        
        # 测试无效输入
        test_cases = [
            # 无效的浓度类型
            ("invalid_type", 0.5, 25, "rho"),
            # 浓度值超出范围
            ("volume", 0.05, 25, "rho"),
            ("volume", 0.95, 25, "rho"),
            # 温度超出范围
            ("volume", 0.5, -40, "rho"),
            ("volume", 0.5, 130, "rho"),
            # 无效的物性参数
            ("volume", 0.5, 25, "invalid_property"),
        ]
        
        for i, (concentration_type, concentration_value, temperature, property_name) in enumerate(test_cases, 1):
            print_step(f"测试用例 {i}: 验证无效输入处理")
            
            # 构建测试命令
            cmd = [
                sys.executable,
                str(project_root / "src" / "egasp" / "cli.py"),
                "--excel",
                "--single",
                f"--type={concentration_type}",
                f"--value={concentration_value}",
                f"--temp={temperature}",
                f"--prop={property_name}",
                "--quiet"
            ]
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=5
                )
                
                # 检查输出是否包含错误信息
                if "ERROR" in result.stdout or "ERROR" in result.stderr:
                    print_success(f"测试用例 {i}: 输入验证测试通过")
                else:
                    print_error(f"测试用例 {i}: 输入验证失败！")
                    
            except Exception as e:
                print_error(f"测试用例 {i}: 测试失败: {e}")

# 性能测试类
class PerformanceTester:
    """性能测试类"""
    
    def test_calculation_performance(self):
        """测试计算性能"""
        print_step("测试计算性能...")
        
        # 测试参数
        test_count = 100
        total_time = 0
        
        # 测试用例
        test_cases = [
            ("volume", 0.5, 25, "rho"),
            ("volume", 0.6, 30, "cp"),
            ("volume", 0.7, 35, "k"),
            ("volume", 0.8, 40, "mu"),
        ]
        
        for i in range(test_count):
            # 循环使用测试用例
            test_case = test_cases[i % len(test_cases)]
            concentration_type, concentration_value, temperature, property_name = test_case
            
            # 构建测试命令
            cmd = [
                sys.executable,
                str(project_root / "src" / "egasp" / "cli.py"),
                "--excel",
                "--single",
                f"--type={concentration_type}",
                f"--value={concentration_value}",
                f"--temp={temperature}",
                f"--prop={property_name}",
                "--quiet"
            ]
            
            start_time = time.time()
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=5
                )
                end_time = time.time()
                total_time += (end_time - start_time)
                
            except Exception as e:
                print_error(f"测试失败: {e}")
        
        # 计算平均执行时间
        avg_time = total_time / test_count
        print_success(f"执行 {test_count} 次计算的平均时间: {avg_time:.4f} 秒")
        
        # 性能评估
        if avg_time < 0.1:
            print_success("性能优秀: 平均执行时间 < 0.1 秒")
        elif avg_time < 0.5:
            print_success("性能良好: 平均执行时间 < 0.5 秒")
        else:
            print_warning("性能一般: 平均执行时间 > 0.5 秒")
    
    def test_batch_performance(self):
        """测试批量处理性能"""
        print_step
