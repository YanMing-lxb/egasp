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
LastEditTime : 2025-11-06 20:15:51 +0800
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

    # 添加行
    table.add_row("质量浓度", " %", f"{result['mass']*100:.2f}", "密度", "kg/m³", f"{result['rho']:.2f}")
    table.add_row("体积浓度", " %", f"{result['volume']*100:.2f}", "比热容", "J/kg·K", f"{result['cp']:.2f}")
    table.add_row("冰点", "°C", f"{result['freezing']:.2f}", "导热率", "W/m·K", f"{result['k']:.4f}")
    table.add_row("沸点", "°C", f"{result['boiling']:.2f}", "粘度", "Pa·s", f"{result['mu']:.5f}")

    # 打印表格
    console.print(table)


def cli_main():
    parser = argparse.ArgumentParser(
        prog='egasp',
        description="[i]乙二醇水溶液属性查询程序  ---- 焱铭[/]",
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument("-qt", "--query_type", type=str, default="volume", help="浓度类型 (volume/mass or v/m), 默认值为 volume (体积浓度)")
    parser.add_argument("-qv", "--query_value", type=float, default=0.5, help="查询浓度 (范围: 0.1 ~ 0.9), 默认值为 0.5")  # 修改此处
    parser.add_argument("query_temp", type=float, help="查询温度 °C (范围: -35 ~ 125)")  # 如果温度单位有%也需要转义

    args = parser.parse_args()

    console = Console(width=59)
    console.print(f"\n[bold green]{__project_name__}[/bold green]", justify="center")
    print('-----+--------------------------------------------+-----')
    # 打印校验后的查询参数
    print(f"查询类型: {args.query_type}")
    print(f"查询浓度: {args.query_value}")
    print(f"查询温度: {args.query_temp} °C")
    mass, volume, freezing, boiling, rho, cp, k, mu = eg.props(args.query_temp, args.query_type, args.query_value)
    print('-----+--------------------------------------------+-----\n')

    result = {"mass": mass, "volume": volume, "freezing": freezing, "boiling": boiling, "rho": rho, "cp": cp, "k": k, "mu": mu}

    print_table(result)  # 调用print_table函数

    # 检查更新
    uc = UpdateChecker(1, 6)  # 访问超时, 单位: 秒;缓存时长, 单位: 小时
    uc.check_for_updates()


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

            # 检查更新（复用原有更新逻辑）
            uc = UpdateChecker(1, 6)
            uc.check_for_updates()

            console.input("[green]按任意键退出...[/]")

            break

    except Exception:
        logger.exception("程序发生异常:")
        console.input("[red]程序运行出错，按任意键退出...[/red]")


def excel_entry():
    """
    用于 Excel 调用的入口函数，接收参数并输出单一属性值到临时文件
    使用方式：
        egasp.exe --excel --type=volume --value=50 --temp=25 --prop=rho
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--type', type=str, required=True, help='查询类型 (volume/mass)')
    parser.add_argument('--value', type=float, required=True, help='浓度值')
    parser.add_argument('--temp', type=float, required=True, help='温度值')
    parser.add_argument('--prop', type=str, required=True, help='要查询的属性')
    args = parser.parse_args()


    mass, volume, freezing, boiling, rho, cp, k, mu = eg.props(args.temp, args.type, args.value)
    props_map = {
        'mass': mass,
        'volume': volume,
        'freezing': freezing,
        'boiling': boiling,
        'rho': rho,
        'cp': cp,
        'k': k,
        'mu': mu
    }
    result = props_map.get(args.prop.lower(), '#N/A')
    
    print(result)

    # 将结果写入临时文件供 Excel 读取
    output_path = os.path.join(os.path.dirname(sys.argv[0]), 'egasp_output.tmp')
    with open(output_path, 'w') as f:
        f.write(str(result))


def main():
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
