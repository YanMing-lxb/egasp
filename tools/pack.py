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
Date         : 2025-11-06 21:00:18 +0800
LastEditTime : 2025-11-06 22:09:33 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /egasp/tools/pack.py
Description  : 
 -----------------------------------------------------------------------
'''

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from config import (
    DATA_DIR,
    ENTRY_POINT,
    ICON_FILE,
    PROJECT_NAME,
    __version__,
)
from utils import PerformanceTracker, console, run_command

if sys.stdout.encoding != "UTF-8":
    sys.stdout.reconfigure(encoding="utf-8")


# -----------------------------------------------------------------------
# <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<| 核心功能 |>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# -----------------------------------------------------------------------


def run_pyinstaller() -> bool:
    """
    使用 PyInstaller 将 Python 项目打包为可执行应用程序
    """
    args = [
        "pyinstaller",
        "--name",
        PROJECT_NAME,
        "--workpath",
        "build",
        "--distpath",
        "dist",
        "--specpath",
        ".",
        "--noconfirm",
        "--clean",
        "--add-data",
        f"{DATA_DIR.resolve()}{os.pathsep}data",
        "--icon",
        str(ICON_FILE.resolve()),
        # 移除以下三行
        # "--file-description",
        # PROJECT_NAME,
        # "--product-version",
        # __version__,
        # "--file-version",
        # __version__,
        str(ENTRY_POINT.resolve()),
    ]
    
    success = run_command(
        command=args,
        success_msg=f"PyInstaller 打包成功 → [bold underline]dist/{PROJECT_NAME}[/]",
        error_msg="打包失败",
        process_name="打包应用程序",
    )

    return success

def clean_up():
    """
    清理打包过程中生成的临时文件和目录，保持项目环境整洁

    Returns
    -------
    bool
        清理操作是否成功完成：
        - `True` 表示清理顺利完成；
        - `False` 表示清理过程中发生错误。

    Notes
    -----
    当前清理内容包括：
    1. 目录：`build`, `__pycache__`, 和虚拟环境目录（默认为 [venv_rhs]）
    2. 文件：所有 `.spec` 打包配置文件
    """
    try:
        # 遍历并删除主要打包产物目录
        for artifact in ["build", "__pycache__"]:
            if Path(artifact).exists():
                shutil.rmtree(artifact)  # 删除目录及其内容
                console.print(f"✓ 删除打包产物: {artifact}", style="info")

        # 查找并删除所有 .spec 文件
        for spec_file in Path().glob("*.spec"):
            spec_file.unlink()  # 删除单个文件
            console.print(f"✓ 删除spec文件: {spec_file}", style="info")

        # 提示用户环境清理已完成
        console.print("✓ 环境清理完成", style="success")
        return True

    except Exception as e:
        # 捕获并打印异常信息，返回清理失败状态
        console.print(f"✗ 清理失败: {e}", style="error")
        return False


def delete_dist_project_folder():
    """
    删除 dist 目录下的项目文件夹

    Returns
    -------
    bool
        - `True` 表示删除成功或文件夹不存在；
        - `False` 表示删除失败。
    """
    dist_project_path = Path("dist") / PROJECT_NAME  # 构建目标路径

    if not dist_project_path.exists():
        console.print(f"⚠️ 文件夹不存在：{dist_project_path}", style="warning")
        return True  # 如果文件夹不存在，认为删除成功

    try:
        shutil.rmtree(dist_project_path)  # 删除目录及其内容
        console.print(
            f"✓ 删除 dist 下的项目文件夹: {dist_project_path}", style="success"
        )
        return True
    except Exception as e:
        console.print(f"✗ 删除 dist 下的项目文件夹失败：{e}", style="error")
        return False


# ==========================================================
#                          辅助程序
# ==========================================================
def build_html():
    console.print("📦 开始转换 Readme 文件格式", style="status")
    readme_md = Path("README.md")
    readme_html = Path("README.html")
    html_success = run_command(
        command=["pandoc", readme_md, "-o", readme_html],
        success_msg="Readme 文件格式转换完成",
        error_msg="Readme 文件格式转换失败",
        process_name="转换 Readme 文件格式",
    )

    if not DATA_DIR.exists():
        DATA_DIR.mkdir(parents=True)
        console.log(f"已创建目录: {DATA_DIR}")

    target_html = DATA_DIR / "README.html"
    shutil.move(str(readme_html), str(target_html))
    console.log(f"生成 HTML 并移动到 {target_html}")

    return html_success


# ======================
# 主流程
# ======================
def main():
    """主函数，处理打包流程"""
    parser = argparse.ArgumentParser(description="Python 项目打包工具")
    parser.add_argument(
        "mode",
        choices=["pack", "setup"],
        help="打包模式: pack (打包程序), setup (构建安装包)",
    )
    parser.add_argument(
        "--pack-tool",
        "-t",
        default="flet",
        choices=["flet", "pyinstaller"],
        help="指定打包工具，默认使用 flet",
    )
    parser.add_argument(
        "--clean", "-c", action="store_true", help="清理 Cython 编译源码目录 SRCPYD_DIR"
    )
    args = parser.parse_args()

    tracker = PerformanceTracker()

    try:
        console.rule(f"[bold]🚀 {PROJECT_NAME} 打包系统[/]")

        steps = []
        if not args.clean and args.mode != "setup":
            # 删除 dist 下的项目文件夹
            delete_result, delete_performance_data = tracker.execute_with_timing(
                delete_dist_project_folder, "删除旧打包"
            )
            tracker.add_record(delete_performance_data)

            if not delete_result:
                console.print("✗ 删除旧打包失败，无法继续", style="error")
                sys.exit(1)

        # ====== 根据 mode 分支处理 ======
        if args.mode == "pack":

            # 打包
            pack_result, pack_performance_data = tracker.execute_with_timing(
                run_pyinstaller, "PyInstaller 打包"
            )

            tracker.add_record(pack_performance_data)

            steps.extend([pack_result])


        # ====== 统一执行步骤 ======
        success = all(steps)

        if success:
            if args.mode == "pack":
                console.rule("[bold green]✅ 程序打包成功！[/]")
                console.print(
                    f"生成的可执行文件位于：[bold underline]dist/{PROJECT_NAME}[/]"
                )
                _, clean_up_performance_data = tracker.execute_with_timing(
                    clean_up, "环境清理"
                )
                tracker.add_record(clean_up_performance_data)
            elif args.mode == "setup":
                console.rule("[bold green]✅ 安装包构建成功！[/]")
                console.print(
                    f"安装包位于：[bold underline]dist/{PROJECT_NAME}-{__version__}-setup.exe[/]"
                )
            elif args.mode == "whl":
                console.rule("[bold green]✅ 构建 PyTeXMK PyPi 轮子成功！[/]")
                console.print(
                    f"生成的 PyTeXMK PyPi 轮子位于：[bold underline]dist/{PROJECT_NAME}-{__version__}-py3-none-any.whl[/]"
                )
        else:
            console.rule("[bold red]❌ 构建失败！[/]")
            console.print("部分步骤未完成，请查看上方详细错误信息。")

        # 生成性能报告
        tracker.generate_report()

    except PermissionError as e:
        console.print(f"✗ 权限错误: {e}", style="error")
        console.print("建议：尝试以管理员权限运行本脚本", style="warning")

    except FileNotFoundError as e:
        console.print(f"✗ 文件或路径不存在: {e}", style="error")
        console.print("请确认相关文件是否完整或路径是否正确", style="warning")

    except subprocess.CalledProcessError as e:
        console.print(f"✗ 子进程调用失败: {e}", style="error")
        console.print("命令执行中断，请检查依赖环境或系统资源", style="warning")

    except OSError as e:
        console.print(f"✗ IO 错误: {e}", style="error")
        console.print("可能原因：磁盘空间不足、文件锁定或权限问题", style="warning")

    except KeyboardInterrupt:
        console.print("\n⚠️ 用户中断操作 (Ctrl+C)，程序已终止", style="warning")
        sys.exit(1)

    except Exception as e:
        console.rule("[bold red]💥 发生未知异常！[/]")
        console.print_exception(show_locals=True)
        console.print(f"异常类型: {type(e).__name__}")
        console.print(f"异常内容: {e!s}")
        console.print("请联系开发者并附上以上异常信息以便排查问题", style="warning")
        sys.exit(1)


if __name__ == "__main__":
    main()
