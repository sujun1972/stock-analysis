#!/usr/bin/env python3
"""
统一测试运行器 - Core项目

功能：
- 运行所有测试或选择特定测试
- 生成覆盖率报告
- 支持排除慢速测试
- 交互式菜单选择
- 详细的测试报告

使用方法：
    python run_tests.py                    # 交互式菜单
    python run_tests.py --all              # 运行所有测试
    python run_tests.py --unit             # 只运行单元测试
    python run_tests.py --integration      # 只运行集成测试
    python run_tests.py --coverage         # 运行测试并生成覆盖率报告
    python run_tests.py --fast             # 快速测试（排除慢速测试）
    python run_tests.py --module xxx       # 运行指定模块测试

作者: Stock Analysis Team
创建: 2026-01-29
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path
from typing import List, Optional

# 颜色输出
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text: str):
    """打印标题"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")

def print_success(text: str):
    """打印成功信息"""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_error(text: str):
    """打印错误信息"""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_warning(text: str):
    """打印警告信息"""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def print_info(text: str):
    """打印信息"""
    print(f"{Colors.OKBLUE}ℹ {text}{Colors.ENDC}")

def get_project_root() -> Path:
    """获取项目根目录"""
    return Path(__file__).parent.parent

def check_venv() -> bool:
    """检查虚拟环境"""
    venv_path = get_project_root().parent / 'stock_env'
    return venv_path.exists()

def get_python_cmd() -> str:
    """获取Python命令"""
    venv_path = get_project_root().parent / 'stock_env'
    if venv_path.exists():
        return str(venv_path / 'bin' / 'python')
    return 'python3'

def run_command(cmd: List[str], description: str = "") -> int:
    """运行命令"""
    if description:
        print_info(f"{description}...")

    print(f"{Colors.OKCYAN}执行命令: {' '.join(cmd)}{Colors.ENDC}\n")

    result = subprocess.run(cmd, cwd=get_project_root())
    return result.returncode

def build_pytest_cmd(
    test_path: Optional[str] = None,
    coverage: bool = False,
    verbose: bool = True,
    exclude_slow: bool = False,
    markers: Optional[str] = None,
    timeout: Optional[int] = None
) -> List[str]:
    """构建pytest命令"""
    python_cmd = get_python_cmd()
    cmd = [python_cmd, '-m', 'pytest']

    # 测试路径
    if test_path:
        cmd.append(test_path)
    else:
        cmd.append('tests/')

    # 覆盖率选项
    if coverage:
        cmd.extend([
            '--cov=src',
            '--cov-report=html:tests/reports/htmlcov',
            '--cov-report=term',
            '--cov-report=xml:tests/reports/coverage.xml'
        ])

    # 详细输出
    if verbose:
        cmd.append('-v')
    else:
        cmd.append('-q')

    # 排除慢速测试
    if exclude_slow:
        # 排除GRU模型测试（最慢的测试）
        cmd.append('--ignore=tests/unit/models/test_gru_model.py')
        cmd.append('--ignore=tests/unit/test_gru_model_comprehensive.py')
        # 排除外部API集成测试（需要网络连接和API token）
        cmd.append('--ignore=tests/integration/providers/akshare/')
        cmd.append('--ignore=tests/integration/providers/test_tushare_provider.py')
        print_warning("已排除慢速GRU模型测试（2个文件）和外部API集成测试（AkShare, Tushare）")

    # 标记过滤
    if markers:
        cmd.extend(['-m', markers])

    # 超时设置
    if timeout:
        cmd.extend(['--timeout', str(timeout)])

    # 其他有用的选项
    cmd.extend([
        '--tb=short',  # 简短的错误回溯
        '-x',          # 遇到第一个失败就停止（可选）
    ])

    # 移除-x选项，让所有测试都运行
    if '-x' in cmd:
        cmd.remove('-x')

    return cmd

def show_menu():
    """显示交互式菜单"""
    print_header("Core项目测试运行器")

    print("请选择要运行的测试:")
    print()
    print(f"{Colors.BOLD}[1]{Colors.ENDC} 运行所有测试 (带覆盖率报告)")
    print(f"{Colors.BOLD}[2]{Colors.ENDC} 运行所有测试 (快速模式，排除慢速测试和外部API测试)")
    print(f"{Colors.BOLD}[3]{Colors.ENDC} 只运行单元测试")
    print(f"{Colors.BOLD}[4]{Colors.ENDC} 只运行集成测试")
    print(f"{Colors.BOLD}[5]{Colors.ENDC} 只运行性能测试")
    print(f"{Colors.BOLD}[6]{Colors.ENDC} 运行特定模块测试")
    print(f"{Colors.BOLD}[7]{Colors.ENDC} 运行Provider测试 (AkShare + Tushare)")
    print(f"{Colors.BOLD}[8]{Colors.ENDC} 运行模型测试 (排除GRU)")
    print(f"{Colors.BOLD}[9]{Colors.ENDC} 运行特征工程测试")
    print(f"{Colors.BOLD}[0]{Colors.ENDC} 退出")
    print()

    choice = input(f"{Colors.OKBLUE}请输入选项 [0-9]: {Colors.ENDC}")
    return choice.strip()

def run_all_tests(coverage: bool = True, fast: bool = False):
    """运行所有测试"""
    print_header("运行所有测试")
    cmd = build_pytest_cmd(coverage=coverage, exclude_slow=fast)
    return run_command(cmd, "运行完整测试套件")

def run_unit_tests(coverage: bool = True):
    """运行单元测试"""
    print_header("运行单元测试")
    cmd = build_pytest_cmd('tests/unit/', coverage=coverage)
    return run_command(cmd, "运行单元测试")

def run_integration_tests(coverage: bool = True):
    """运行集成测试"""
    print_header("运行集成测试")
    cmd = build_pytest_cmd('tests/integration/', coverage=coverage)
    return run_command(cmd, "运行集成测试")

def run_performance_tests():
    """运行性能测试"""
    print_header("运行性能测试")
    cmd = build_pytest_cmd('tests/performance/', coverage=False)
    return run_command(cmd, "运行性能测试")

def run_provider_tests(coverage: bool = True):
    """运行Provider测试"""
    print_header("运行Provider测试")
    cmd = build_pytest_cmd('tests/unit/providers/', coverage=coverage)
    cmd2 = build_pytest_cmd('tests/integration/providers/', coverage=coverage)

    print_info("运行单元测试...")
    ret1 = run_command(cmd)
    print_info("运行集成测试...")
    ret2 = run_command(cmd2)

    return ret1 + ret2

def run_model_tests(coverage: bool = True, exclude_gru: bool = True):
    """运行模型测试"""
    print_header("运行模型测试")

    if exclude_gru:
        print_warning("排除GRU模型测试（训练较慢）")
        cmd = build_pytest_cmd('tests/unit/models/', coverage=coverage, exclude_slow=True)
    else:
        cmd = build_pytest_cmd('tests/unit/models/', coverage=coverage)

    return run_command(cmd, "运行模型测试")

def run_feature_tests(coverage: bool = True):
    """运行特征工程测试"""
    print_header("运行特征工程测试")
    cmd = build_pytest_cmd('tests/unit/features/', coverage=coverage)
    return run_command(cmd, "运行特征工程测试")

def run_specific_module():
    """运行特定模块测试"""
    print_header("运行特定模块测试")
    print()
    print("可用的测试模块:")
    print("  - unit/test_data_loader.py")
    print("  - unit/test_feature_engineer.py")
    print("  - unit/test_model_trainer.py")
    print("  - integration/test_data_pipeline.py")
    print("  - 等等...")
    print()

    module = input(f"{Colors.OKBLUE}请输入模块路径 (如: unit/test_data_loader.py): {Colors.ENDC}")

    if not module:
        print_error("未输入模块路径")
        return 1

    test_path = f"tests/{module}"
    if not Path(get_project_root() / test_path).exists():
        print_error(f"测试文件不存在: {test_path}")
        return 1

    cmd = build_pytest_cmd(test_path, coverage=True)
    return run_command(cmd, f"运行 {module}")

def interactive_mode():
    """交互式模式"""
    while True:
        choice = show_menu()

        if choice == '0':
            print_info("退出测试运行器")
            return 0
        elif choice == '1':
            return run_all_tests(coverage=True, fast=False)
        elif choice == '2':
            return run_all_tests(coverage=True, fast=True)
        elif choice == '3':
            return run_unit_tests(coverage=True)
        elif choice == '4':
            return run_integration_tests(coverage=True)
        elif choice == '5':
            return run_performance_tests()
        elif choice == '6':
            return run_specific_module()
        elif choice == '7':
            return run_provider_tests(coverage=True)
        elif choice == '8':
            return run_model_tests(coverage=True, exclude_gru=True)
        elif choice == '9':
            return run_feature_tests(coverage=True)
        else:
            print_error("无效的选项，请重新选择")
            continue

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Core项目统一测试运行器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                           # 交互式菜单
  %(prog)s --all                     # 运行所有测试
  %(prog)s --all --coverage          # 运行所有测试并生成覆盖率
  %(prog)s --fast                    # 快速测试（排除慢速测试和外部API测试）
  %(prog)s --unit                    # 只运行单元测试
  %(prog)s --integration             # 只运行集成测试
  %(prog)s --performance             # 只运行性能测试
  %(prog)s --providers               # 运行Provider测试
  %(prog)s --models                  # 运行模型测试
  %(prog)s --features                # 运行特征工程测试
  %(prog)s --module unit/test_xxx.py # 运行特定模块
        """
    )

    parser.add_argument('--all', action='store_true', help='运行所有测试')
    parser.add_argument('--fast', action='store_true', help='快速模式（排除慢速测试和外部API测试）')
    parser.add_argument('--unit', action='store_true', help='运行单元测试')
    parser.add_argument('--integration', action='store_true', help='运行集成测试')
    parser.add_argument('--performance', action='store_true', help='运行性能测试')
    parser.add_argument('--providers', action='store_true', help='运行Provider测试')
    parser.add_argument('--models', action='store_true', help='运行模型测试')
    parser.add_argument('--features', action='store_true', help='运行特征工程测试')
    parser.add_argument('--module', type=str, help='运行特定模块测试')
    parser.add_argument('--coverage', action='store_true', default=True, help='生成覆盖率报告（默认开启）')
    parser.add_argument('--no-coverage', action='store_true', help='不生成覆盖率报告')

    args = parser.parse_args()

    # 检查虚拟环境
    if not check_venv():
        print_warning("未检测到虚拟环境 stock_env，将使用系统Python")

    # 确定覆盖率选项
    coverage = args.coverage and not args.no_coverage

    # 如果没有任何参数，进入交互模式
    if len(sys.argv) == 1:
        return interactive_mode()

    # 根据参数运行相应的测试
    if args.all or args.fast:
        return run_all_tests(coverage=coverage, fast=args.fast)
    elif args.unit:
        return run_unit_tests(coverage=coverage)
    elif args.integration:
        return run_integration_tests(coverage=coverage)
    elif args.performance:
        return run_performance_tests()
    elif args.providers:
        return run_provider_tests(coverage=coverage)
    elif args.models:
        return run_model_tests(coverage=coverage, exclude_gru=True)
    elif args.features:
        return run_feature_tests(coverage=coverage)
    elif args.module:
        test_path = f"tests/{args.module}"
        if not Path(get_project_root() / test_path).exists():
            print_error(f"测试文件不存在: {test_path}")
            return 1
        cmd = build_pytest_cmd(test_path, coverage=coverage)
        return run_command(cmd, f"运行 {args.module}")
    else:
        parser.print_help()
        return 0

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print_warning("\n\n测试已被用户中断")
        sys.exit(130)
    except Exception as e:
        print_error(f"发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
