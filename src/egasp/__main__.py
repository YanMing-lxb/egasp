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
 ·······························································888·····
 ··························································Y8b·d88P·····
 ···························································"Y88P"······
 =======================================================================

 -----------------------------------------------------------------------
Author       : 焱铭
Date         : 2025-04-22 10:43:55 +0800
LastEditTime : 2025-11-08 11:05:28 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /egasp/src/egasp/__main__.py
Description  : 
 -----------------------------------------------------------------------
'''
import os
import sys
import argparse
from rich import box
from rich import print
from rich.table import Table
from rich.prompt import Prompt
from rich.console import Console
from rich_argparse import RichHelpFormatter

from egasp.core import EGASP
from egasp.logger_config import setup_logger
from egasp.check_version import UpdateChecker
# 版本信息
from egasp.version import __project_name__, __version__

logger = setup_logger(False)
eg = EGASP()  # 初始化核心计算类实例

def print_table(result: dict):
    console = Console(width=59)
    # 创建表格
    table = Table(show_header=True, header_style="bold dark_orange", box=box.ASCII_DOUBLE_HEAD, title="乙二醇水溶液查询结果")

    # 添加列
    table.add_column("属性", justify="left", style="cyan", no_wrap=True)
    table.add_column("单位", justify="left", style="magenta", no_wrap=True)
    table.add_column("数值", justify="left", style="green", no_wrap=True)
    table.add_column("属性", justify="left", style="cyan", no_wrap=True)
    table.add_column("单位", justify="left", style="magenta", no_wrap=True)
    table.add_column("数值", justify="left", style="green", no_wrap=True)

    # ✨ 添加行，处理None值的情况
    def format_value(value, format_str):
        if value is None:
            return "N/A"
        else:
            return f"{value:{format_str}}"
    
    # 添加行
    table.add_row("质量浓度", " %", format_value(result['mass']*100, ".2f"), "密度", "kg/m³", format_value(result['rho'], ".2f"))
    table.add_row("体积浓度", " %", format_value(result['volume']*100, ".2f"), "比热容", "J/kg·K", format_value(result['cp'], ".2f"))
    table.add_row("冰点", "°C", format_value(result['freezing'], ".2f"), "导热率", "W/m·K", format_value(result['k'], ".4f"))
    table.add_row("沸点", "°C", format_value(result['boiling'], ".2f"), "粘度", "Pa·s", format_value(result['mu'], ".5f"))

    # 打印表格
    console.print(table)


def print_multi_temp_table(results: list, query_type: str):
    """
    打印多温度查询结果的表格
    :param results: 结果列表，每个元素是包含温度和属性的字典
    :param query_type: 查询类型 (volume/mass)
    """
    from rich.text import Text
    from rich.console import Console
    console = Console()
    
    # 根据查询类型确定输出的浓度类型
    output_conc_type = "Mass Conc." if query_type in ["volume", "v"] else "Vol. Conc."
    
    # 提取固定值
    if results:
        freezing = results[0]['freezing']
        boiling = results[0]['boiling']
        output_conc = results[0]['mass'] * 100 if query_type in ["volume", "v"] else results[0]['volume'] * 100
    
    # 打印标题和符号分割线
    console.print(  Text("乙二醇水溶液多温度查询结果", style="bold dark_orange"), width=54, justify="center")
    
    # 打印表格分隔线（首行）
    console.print(Text("  +-------+---------+---------+--------+------------+"))
    
    # 打印表头
    header_line = f"  {'Temp':^9}{'Dens':^9}{'Cp':^11}{'Cond':^9}{'Visc':^13}"
    console.print(Text(header_line, style="bold dark_orange"))
    units_line = f"  {'deg C':^9}{'kg/m3':^9}{'J/kg-K':^11}{'W/m-K':^9}{'Pa-s':^13}"
    console.print(Text(units_line, style="red"))
    console.print(Text("  +=======+=========+=========+========+============+"))
    
    # 格式化值的函数
    def format_str(value, format_str):
        if value is None:
            return "N/A"
        return f"{value:{format_str}}"
    
    # 打印数据行
    for res in results:
        data_line = (
            f"  {format_str(res['temp'], '.2f'):^9}"
            f"{format_str(res['rho'], '.2f'):^9}"
            f"{format_str(res['cp'], '.2f'):^11}"
            f"{format_str(res['k'], '.4f'):^9}"
            f"{format_str(res['mu'], '.4e'):^13}"
        )
        console.print(Text(data_line, style="green"))
    console.print(Text("  +-------+---------+---------+--------+------------+"))

    # 打印固定属性 - 使用不同颜色区分，更紧凑
    console.print(Text(f" {output_conc_type}: ", style="cyan"), end="")
    console.print(Text(f"{output_conc:.2f}", style="green"), end="")
    console.print(Text(" %", style="red"), end="  ")
    
    console.print(Text("Freez./Boil.: ", style="magenta"), end="")
    console.print(Text(f"{freezing:.2f}/{boiling:.2f}", style="green"), end="")
    console.print(Text(" deg C", style="red"))
    print('-----+--------------------------------------------+-----')

def cli_main():
    parser = argparse.ArgumentParser(
        prog='egasp',
        description="[i]乙二醇水溶液属性查询程序  ---- 焱铭[/]",
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument("-qt", "--query_type", type=str, default="volume", help="浓度类型 (volume/mass or v/m), 默认值为 volume (体积浓度)")
    parser.add_argument("-qv", "--query_value", type=float, default=0.5, help="查询浓度 (范围: 0.1 ~ 0.9), 默认值为 0.5")
    parser.add_argument("query_temp", nargs='+', type=float, help="查询温度 °C (范围: -35 ~ 125)，支持多个温度值")

    args = parser.parse_args()

    console = Console(width=59)
    console.print(f"\n[bold green]{__project_name__}[/bold green]", justify="center")
    print('-----+--------------------------------------------+-----')
    # 打印校验后的查询参数
    print(f"查询类型: {args.query_type}")
    print(f"查询浓度: {args.query_value}")
    print(f"查询温度: {args.query_temp} °C")
    
    # 判断是否为多温度查询
    if len(args.query_temp) > 1:
        # 多温度查询
        results = []
        for temp in args.query_temp:
            mass, volume, freezing, boiling, rho, cp, k, mu = eg.props(temp, args.query_type, args.query_value)
            results.append({
                "temp": temp,
                "mass": mass,
                "volume": volume,
                "freezing": freezing,
                "boiling": boiling,
                "rho": rho,
                "cp": cp,
                "k": k,
                "mu": mu
            })
        print('-----+--------------------------------------------+-----')
        print_multi_temp_table(results, args.query_type)
    else:
        # 单温度查询
        mass, volume, freezing, boiling, rho, cp, k, mu = eg.props(args.query_temp[0], args.query_type, args.query_value)
        print('-----+--------------------------------------------+-----\n')
        result = {"mass": mass, "volume": volume, "freezing": freezing, "boiling": boiling, "rho": rho, "cp": cp, "k": k, "mu": mu}
        print_table(result)

    # 检查更新（异步）
    uc = UpdateChecker(1, 6)
    uc.check_for_updates_async()


def input_main():
    try:
        # 初始化控制台输出
        console = Console(width=59)
        console.print(f"\n[bold green]{__project_name__}[/bold green]", justify="center")
        print('-----+--------------------------------------------+-----')

        # 交互式输入参数
        while True:
            try:
                console.print("[bold cyan]参数输入[/]")
                query_type = Prompt.ask("[bold]1. 浓度类型 [dim](volume/mass)[/]", default="volume")
                console.print(f"[green]✓ 已选择类型: {query_type}[/]")

                query_value = float(Prompt.ask("[bold]2. 输入浓度 [dim](0.1-0.9)[/]", default="0.5"))
                console.print(f"[green]✓ 浓度已确认: {query_value}[/]")

                query_temp = float(Prompt.ask("[bold]3. 输入温度 [dim](-35-125°C)[/]"))
                console.print(f"[green]✓ 温度已确认: {query_temp}°C[/]\n")
            except ValueError as e:
                console.print(f"[red]输入格式错误: {str(e)}，请重新输入[/red]")

            # 获取计算结果（复用原有核心逻辑）
            mass, volume, freezing, boiling, rho, cp, k, mu = eg.props(query_temp, query_type, query_value)

            # 打印结果表格
            print('-----+--------------------------------------------+-----\n')
            result = {"mass": mass, "volume": volume, "freezing": freezing, "boiling": boiling, "rho": rho, "cp": cp, "k": k, "mu": mu}
            print_table(result)

            # 检查更新（异步）
            uc = UpdateChecker(1, 6)
            uc.check_for_updates_async()

            console.input("[green]按任意键退出...[/]")
            
            # 显示异步版本检查结果
            uc.get_async_result()

            break

    except Exception:
        logger.exception("程序发生异常:")
        console.input("[red]程序运行出错，按任意键退出...[/red]")


def excel_entry():
    """
    用于 Excel/WPS 调用的入口函数 - 使用新的 excel_integration 模块
    支持多种调用模式：单属性、完整数据、批量处理
    """
    from egasp.excel_integration import excel_main
    excel_main()


def main():
    # 检查 --version 参数
    if '--version' in sys.argv or '-v' in sys.argv:
        print(f"{__project_name__} {__version__}")
        return

    if len(sys.argv) > 1:
        if sys.argv[1] == '--excel':
            # 移除第一个参数 '--excel'，避免干扰 argparse
            sys.argv.pop(1)
            excel_entry()
        else:
            cli_main()
    else:
        input_main()


if __name__ == "__main__":
    main()
