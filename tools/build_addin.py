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
Date         : 2026-04-04
LastEditTime : 2026-04-05
Github       : https://github.com/YanMing-lxb/
FilePath     : /egasp/tools/build_addin.py
Description  : 纯VBA Excel加载项构建工具 - 创建.xlam文件
 -----------------------------------------------------------------------
"""

import shutil
import subprocess
import os
import sys
from pathlib import Path
from rich.console import Console
from rich.theme import Theme

# 确保 stdout 使用 UTF-8 编码
if sys.stdout.encoding != "UTF-8":
    sys.stdout.reconfigure(encoding="utf-8")

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

# 读取版本信息
def get_version():
    """
    从版本文件获取版本号
    
    Returns
    -------
    str
        版本号字符串
    """
    version_file = project_root / 'src' / 'egasp' / 'version.py'
    if version_file.exists():
        with open(version_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('__version__'):
                    version = line.split('=')[1].strip()
                    # 去除引号
                    if (version.startswith('"') and version.endswith('"')) or (version.startswith("'") and version.endswith("'")):
                        version = version[1:-1]
                    return version
    return '1.0.0'

__version__ = get_version()

# 性能跟踪类
class PerformanceTracker:
    """性能跟踪器"""
    def __init__(self):
        self.records = []
    
    def execute_with_timing(self, func, description):
        """
        执行函数并记录执行时间
        
        Parameters
        ----------
        func : callable
            要执行的函数
        description : str
            操作描述
            
        Returns
        -------
        tuple
            (函数返回值, 执行时间)
        """
        import time
        start_time = time.time()
        result = func()
        end_time = time.time()
        execution_time = end_time - start_time
        return result, execution_time
    
    def add_record(self, execution_time):
        """
        添加性能记录
        
        Parameters
        ----------
        execution_time : float
            执行时间
        """
        self.records.append(execution_time)
    
    def generate_report(self):
        """
        生成性能报告
        """
        if not self.records:
            return
        
        console.rule("[bold]性能报告[/]")
        for i, time_taken in enumerate(self.records, 1):
            console.print(f"操作 {i}: {time_taken:.2f} 秒")
        
        if len(self.records) > 1:
            total_time = sum(self.records)
            avg_time = total_time / len(self.records)
            console.print(f"总时间: {total_time:.2f} 秒")
            console.print(f"平均时间: {avg_time:.2f} 秒")

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

# 构建基础类
class Builder:
    """构建基础类"""
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.version = __version__
    
    def create_output_directory(self):
        """
        创建输出目录
        
        Returns
        -------
        bool
            操作是否成功
        """
        print_step(f"创建输出目录: {self.output_dir}")
        try:
            if self.output_dir.exists():
                shutil.rmtree(self.output_dir)
            
            self.output_dir.mkdir(parents=True, exist_ok=True)
            print_success(f"输出目录已创建: {self.output_dir}")
            return True
        except Exception as e:
            print_error(f"创建输出目录失败: {e}")
            return False

# 纯VBA Excel加载项构建器
class ExcelVBABuilder(Builder):
    """纯VBA Excel加载项构建器"""
    def __init__(self, output_dir):
        super().__init__(output_dir)
        self.excel_addin_dir = project_root / 'excel_addin'
    
    def check_dependencies(self):
        """
        检查VBA Excel加载项依赖项
        
        Returns
        -------
        bool
            依赖项检查是否通过
        """
        print_step("检查VBA Excel加载项依赖项...")
        
        # 检查excel_addin目录是否存在
        if not self.excel_addin_dir.exists():
            print_error(f"Excel Add-in目录不存在: {self.excel_addin_dir}")
            return False
        
        # 检查必要的文件
        required_files = [
            'EGASP.bas'
        ]
        
        for file_name in required_files:
            file_path = self.excel_addin_dir / file_name
            if not file_path.exists():
                print_error(f"缺少必要文件: {file_path}")
                return False
        
        print_success("所有依赖项检查通过")
        return True
    
    def create_xlam_file(self):
        """
        创建.xlam Excel加载项文件
        
        Returns
        -------
        bool
            操作是否成功
        """
        print_step("创建.xlam Excel加载项文件...")
        
        try:
            import win32com.client as win32
            
            # 读取VBA代码
            vba_file = self.excel_addin_dir / 'EGASP.bas'
            with open(vba_file, 'r', encoding='utf-8') as f:
                vba_code = f.read()
            
            # 创建Excel应用程序对象
            excel = win32.Dispatch("Excel.Application")
            excel.Visible = False
            excel.DisplayAlerts = False
            
            try:
                # 创建新工作簿
                workbook = excel.Workbooks.Add()
                
                # 导入VBA模块
                vb_project = workbook.VBProject
                vb_component = vb_project.VBComponents.Add(1)  # 1 = vbext_ct_StdModule
                vb_component.Name = "EGASP"
                
                # 写入VBA代码
                code_module = vb_component.CodeModule
                code_module.AddFromString(vba_code)
                
                # 保存为.xlam文件
                xlam_path = self.output_dir / 'EGASP Addin.xlam'
                workbook.SaveAs(str(xlam_path), FileFormat=55)  # 55 = xlOpenXMLAddIn
                
                print_success(f".xlam文件已创建: {xlam_path}")
                
                return True
                
            finally:
                # 关闭工作簿和Excel
                if 'workbook' in locals():
                    workbook.Close(SaveChanges=False)
                excel.Quit()
                
        except ImportError:
            print_warning("未安装pywin32，无法自动创建.xlam文件")
            print_step("将提供VBA源代码文件和手动创建说明")
            return self.copy_vba_files()
            
        except Exception as e:
            print_error(f"创建.xlam文件失败: {e}")
            import traceback
            traceback.print_exc()
            print_step("将提供VBA源代码文件和手动创建说明")
            return self.copy_vba_files()
    
    def copy_vba_files(self):
        """
        复制VBA源代码文件到输出目录
        
        Returns
        -------
        bool
            操作是否成功
        """
        print_step("复制VBA源代码文件...")
        
        try:
            # 复制VBA模块
            vba_file = self.excel_addin_dir / 'EGASP.bas'
            if vba_file.exists():
                shutil.copy2(vba_file, self.output_dir / 'EGASP.bas')
            
            # 创建README
            self.create_readme()
            
            print_success("VBA文件复制完成")
            return True
            
        except Exception as e:
            print_error(f"复制VBA文件失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def create_readme(self):
        """创建README文件"""
        readme_content = """# EGASP Excel加载项 (纯VBA版)

## 安装说明

### 前置要求
1. Excel 2010+
2. egasp.exe已添加到环境变量EGASP_BIN中

### 安装方法一：使用.xlam文件（推荐）

如果构建成功生成了`EGASP Addin.xlam`文件：

1. 打开Excel
2. 点击`文件` -> `选项` -> `加载项`
3. 在底部的`管理`下拉框中选择`Excel加载项`，点击`转到`
4. 点击`浏览`，选择`EGASP Addin.xlam`文件
5. 确保`EGASP Addin`已勾选，点击`确定`
6. 重启Excel

### 安装方法二：手动导入VBA模块

如果只有`EGASP.bas`文件：

1. 打开Excel
2. 按下`Alt+F11`打开VBA编辑器
3. 点击`文件` -> `导入文件`
4. 选择`EGASP.bas`文件
5. 保存工作簿为`.xlam`格式（Excel加载项）
6. 按照方法一的步骤加载此.xlam文件

### 使用方法

在Excel单元格中直接使用以下函数：

```excel
=EG_PROPERTY("volume", 0.5, 25, "rho")  ' 通用物性参数查询
=EG_RHO("volume", 0.5, 25)  ' 密度
=EG_CP("volume", 0.5, 25)  ' 比热容
=EG_K("volume", 0.5, 25)  ' 导热系数
=EG_MU("volume", 0.5, 25)  ' 粘度
=EG_TF("volume", 0.5)  ' 冰点
=EG_TB("volume", 0.5)  ' 沸点
=EG_MASS("volume", 0.5, 25)  ' 质量浓度
=EG_VOL("mass", 0.5, 25)  ' 体积浓度
=EG_CLEAR_CACHE()  ' 清除缓存
=EG_CACHE_STATUS()  ' 缓存状态
=EG_INITIALIZE()  ' 初始化检查
```

### 参数说明

- **类型**: 'volume' (体积浓度) 或 'mass' (质量浓度)
- **浓度值**: 0.1 到 0.9 之间
- **温度**: -35°C 到 125°C 之间
- **属性名**: 
  - rho, density: 密度
  - cp, specific_heat: 比热容
  - k, thermal_conductivity: 导热系数
  - mu, viscosity: 粘度
  - freezing, freezing_point: 冰点
  - boiling, boiling_point: 沸点
  - mass, mass_concentration: 质量浓度
  - volume, volume_concentration: 体积浓度

### 注意事项

1. 确保egasp.exe已添加到环境变量EGASP_BIN中
2. 首次使用建议先运行`=EG_INITIALIZE()`函数检查环境
3. 如果遇到问题，请查看Excel的宏安全设置，确保启用了宏
4. 加载项内置了缓存机制，重复计算相同参数会非常快
"""
        
        readme_path = self.output_dir / 'README.md'
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)

# 主构建类
class BuildManager:
    """构建管理器"""
    def __init__(self):
        self.version = __version__
        self.dist_dir = project_root / 'dist'
    
    def build_excel_addin(self):
        """
        构建纯VBA Excel加载项
        
        Returns
        -------
        bool
            操作是否成功
        """
        print_header(f"构建纯VBA Excel加载项 (v{self.version})")
        
        # 构建目录
        addin_dir = self.dist_dir / 'excel_addin'
        
        print_step("开始构建纯VBA Excel加载项...")
        
        # 1. 创建输出目录
        print_step("1. 创建输出目录")
        builder = Builder(addin_dir)
        if not builder.create_output_directory():
            return False
        
        # 2. 检查依赖项
        print_step("2. 检查依赖项")
        excel_builder = ExcelVBABuilder(addin_dir)
        if not excel_builder.check_dependencies():
            return False
        
        # 3. 创建.xlam文件或复制VBA文件
        print_step("3. 构建Excel加载项")
        if not excel_builder.create_xlam_file():
            return False
        
        print_header("纯VBA Excel加载项构建完成！")
        console.print(f"输出目录: {addin_dir}")
        console.print("\n使用说明:")
        console.print("  1. 确保egasp.exe已添加到环境变量EGASP_BIN中")
        console.print("  2. 打开Excel并按照README.md中的说明安装加载项")
        console.print("  3. 在单元格中使用EG_开头的函数")
        return True

def main():
    """主函数"""
    print_header("EGASP 纯VBA Excel加载项构建工具")
    
    tracker = PerformanceTracker()
    
    try:
        manager = BuildManager()
        result, performance = tracker.execute_with_timing(manager.build_excel_addin, "构建纯VBA Excel加载项")
        tracker.add_record(performance)
        
        tracker.generate_report()
        
        return 0 if result else 1
    
    except Exception as e:
        console.rule("[bold red]发生未知异常！[/]")
        console.print_exception(show_locals=True)
        console.print(f"异常类型: {type(e).__name__}")
        console.print(f"异常内容: {str(e)}")
        console.print("请联系开发者并附上以上异常信息以便排查问题", style="warning")
        return 1

if __name__ == '__main__':
    sys.exit(main())
