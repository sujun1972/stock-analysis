#!/usr/bin/env python3
"""
CLI测试运行器 - 专门用于运行CLI命令行工具的测试

功能：
- 运行CLI模块的所有测试
- 运行特定CLI组件的测试（utils, commands）
- 生成覆盖率报告
- 详细的测试报告和统计

使用方法：
    python run_cli_tests.py                    # 交互式菜单
    python run_cli_tests.py --all              # 运行所有CLI测试
    python run_cli_tests.py --utils            # 只运行工具模块测试
    python run_cli_tests.py --commands         # 只运行命令模块测试
    python run_cli_tests.py --coverage         # 运行测试并生成覆盖率报告
    python run_cli_tests.py --fix-imports      # 修复导入问题并运行测试
    python run_cli_tests.py --verbose          # 详细输出模式

作者: Stock Analysis Team
创建: 2026-01-30
"""

import sys
import os
import argparse
import subprocess
import time
import re
from pathlib import Path
from typing import List, Optional, Dict, Tuple

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
    # 文件位于 core/tests/，项目根在 core/
    return Path(__file__).parent.parent

def get_python_cmd() -> str:
    """获取Python命令"""
    venv_path = get_project_root() / 'venv'
    if venv_path.exists():
        return str(venv_path / 'bin' / 'python')

    # 检查父级stock_env
    stock_env = get_project_root().parent / 'stock_env'
    if stock_env.exists():
        return str(stock_env / 'bin' / 'python')

    return 'python3'

def parse_pytest_output(output: str) -> Dict:
    """解析pytest输出，提取测试统计信息"""
    stats = {
        'passed': 0,
        'failed': 0,
        'skipped': 0,
        'errors': 0,
        'warnings': 0,
        'duration': 0.0,
        'coverage': None
    }

    # 解析测试结果行
    result_pattern = r'(\d+)\s+(passed|failed|skipped|error)'
    for match in re.finditer(result_pattern, output):
        count = int(match.group(1))
        status = match.group(2)
        if status == 'passed':
            stats['passed'] = count
        elif status == 'failed':
            stats['failed'] = count
        elif status == 'skipped':
            stats['skipped'] = count
        elif status == 'error':
            stats['errors'] = count

    # 解析执行时间
    time_pattern = r'in\s+([\d.]+)s'
    time_match = re.search(time_pattern, output)
    if time_match:
        stats['duration'] = float(time_match.group(1))

    # 解析覆盖率
    coverage_pattern = r'TOTAL\s+\d+\s+\d+\s+(\d+)%'
    coverage_match = re.search(coverage_pattern, output)
    if coverage_match:
        stats['coverage'] = int(coverage_match.group(1))

    return stats

def print_test_summary(stats: Dict, duration: float):
    """打印测试摘要"""
    print_header("CLI测试执行摘要")

    total = stats['passed'] + stats['failed'] + stats['skipped']

    print(f"{Colors.BOLD}执行时间:{Colors.ENDC} {duration:.2f}秒")
    print(f"{Colors.BOLD}总测试数:{Colors.ENDC} {total}")
    print()

    if stats['passed'] > 0:
        print_success(f"通过: {stats['passed']} ({stats['passed']/total*100:.1f}%)")

    if stats['failed'] > 0:
        print_error(f"失败: {stats['failed']} ({stats['failed']/total*100:.1f}%)")

    if stats['skipped'] > 0:
        print_warning(f"跳过: {stats['skipped']} ({stats['skipped']/total*100:.1f}%)")

    if stats['errors'] > 0:
        print_error(f"错误: {stats['errors']}")

    if stats.get('coverage') is not None:
        coverage = stats['coverage']
        print()
        if coverage >= 80:
            print_success(f"代码覆盖率: {coverage}%")
        elif coverage >= 70:
            print_warning(f"代码覆盖率: {coverage}% (建议≥80%)")
        else:
            print_error(f"代码覆盖率: {coverage}% (建议≥80%)")

    print()

def run_command(cmd: List[str], description: str = "", capture_output: bool = False) -> Tuple[int, str]:
    """运行命令"""
    if description:
        print_info(f"{description}...")

    print(f"{Colors.OKCYAN}执行命令: {' '.join(cmd)}{Colors.ENDC}\n")

    start_time = time.time()

    if capture_output:
        result = subprocess.run(cmd, cwd=get_project_root(),
                              capture_output=True, text=True)
        output = result.stdout + result.stderr
        print(output)  # 同时打印到终端
    else:
        result = subprocess.run(cmd, cwd=get_project_root())
        output = ""

    duration = time.time() - start_time

    # 解析并打印摘要
    if capture_output and output:
        stats = parse_pytest_output(output)
        print_test_summary(stats, duration)

    return result.returncode, output

def build_pytest_cmd(
    test_path: Optional[str] = None,
    coverage: bool = False,
    verbose: bool = True,
    markers: Optional[str] = None,
) -> List[str]:
    """构建pytest命令"""
    python_cmd = get_python_cmd()
    cmd = [python_cmd, '-m', 'pytest']

    # 测试路径
    if test_path:
        cmd.append(test_path)
    else:
        cmd.append('tests/cli/')

    # 覆盖率选项
    if coverage:
        cmd.extend([
            '--cov=src/cli',
            '--cov-report=html:tests/reports/cli_htmlcov',
            '--cov-report=term',
            '--cov-report=xml:tests/reports/cli_coverage.xml'
        ])

    # 详细输出
    if verbose:
        cmd.append('-v')
    else:
        cmd.append('-q')

    # 标记过滤
    if markers:
        cmd.extend(['-m', markers])

    # 其他有用的选项
    cmd.extend([
        '--tb=short',  # 简短的错误回溯
    ])

    return cmd

def show_menu():
    """显示交互式菜单"""
    print_header("CLI测试运行器")

    print("请选择要运行的测试:")
    print()
    print(f"{Colors.BOLD}[CLI组件测试]{Colors.ENDC}")
    print(f"  {Colors.BOLD}[1]{Colors.ENDC} 运行所有CLI测试 (带覆盖率报告)")
    print(f"  {Colors.BOLD}[2]{Colors.ENDC} 运行所有CLI测试 (快速模式)")
    print(f"  {Colors.BOLD}[3]{Colors.ENDC} 只运行工具模块测试 (utils)")
    print(f"  {Colors.BOLD}[4]{Colors.ENDC} 只运行命令模块测试 (commands)")
    print()
    print(f"{Colors.BOLD}[具体命令测试]{Colors.ENDC}")
    print(f"  {Colors.BOLD}[D]{Colors.ENDC} 测试 download 命令")
    print(f"  {Colors.BOLD}[F]{Colors.ENDC} 测试 features 命令")
    print(f"  {Colors.BOLD}[T]{Colors.ENDC} 测试 train 命令")
    print(f"  {Colors.BOLD}[B]{Colors.ENDC} 测试 backtest 命令")
    print(f"  {Colors.BOLD}[A]{Colors.ENDC} 测试 analyze 命令")
    print()
    print(f"{Colors.BOLD}[工具模块测试]{Colors.ENDC}")
    print(f"  {Colors.BOLD}[O]{Colors.ENDC} 测试 output 输出工具")
    print(f"  {Colors.BOLD}[P]{Colors.ENDC} 测试 progress 进度条")
    print(f"  {Colors.BOLD}[V]{Colors.ENDC} 测试 validators 验证器")
    print()
    print(f"{Colors.BOLD}[其他选项]{Colors.ENDC}")
    print(f"  {Colors.BOLD}[L]{Colors.ENDC} 列出所有CLI测试文件")
    print(f"  {Colors.BOLD}[I]{Colors.ENDC} 检查并修复常见问题")
    print(f"  {Colors.BOLD}[0]{Colors.ENDC} 退出")
    print()

    choice = input(f"{Colors.OKBLUE}请输入选项 [0-4/D/F/T/B/A/O/P/V/L/I]: {Colors.ENDC}")
    return choice.strip().upper()

def run_all_cli_tests(coverage: bool = True):
    """运行所有CLI测试"""
    print_header("运行所有CLI测试")
    cmd = build_pytest_cmd(coverage=coverage)
    returncode, output = run_command(cmd, "运行完整CLI测试套件", capture_output=True)
    return returncode

def run_utils_tests(coverage: bool = True):
    """运行工具模块测试"""
    print_header("运行CLI工具模块测试")
    cmd = build_pytest_cmd('tests/cli/utils/', coverage=coverage)
    returncode, output = run_command(cmd, "运行工具模块测试", capture_output=True)
    return returncode

def run_commands_tests(coverage: bool = True):
    """运行命令模块测试"""
    print_header("运行CLI命令模块测试")
    cmd = build_pytest_cmd('tests/cli/commands/', coverage=coverage)
    returncode, output = run_command(cmd, "运行命令模块测试", capture_output=True)
    return returncode

def run_specific_test(test_file: str, coverage: bool = True):
    """运行特定测试文件"""
    test_path = f'tests/cli/{test_file}'
    full_path = get_project_root() / test_path

    if not full_path.exists():
        print_error(f"测试文件不存在: {test_path}")
        return 1

    print_header(f"运行 {test_file} 测试")
    cmd = build_pytest_cmd(test_path, coverage=coverage)
    returncode, output = run_command(cmd, f"运行 {test_file}", capture_output=True)
    return returncode

def list_cli_tests():
    """列出所有CLI测试文件"""
    print_header("CLI测试文件列表")

    cli_tests_dir = get_project_root() / 'tests' / 'cli'

    if not cli_tests_dir.exists():
        print_error("CLI测试目录不存在")
        return 1

    print(f"{Colors.BOLD}工具模块测试 (utils/):{Colors.ENDC}")
    utils_dir = cli_tests_dir / 'utils'
    if utils_dir.exists():
        for test_file in sorted(utils_dir.glob('test_*.py')):
            print(f"  - {test_file.name}")
    print()

    print(f"{Colors.BOLD}命令模块测试 (commands/):{Colors.ENDC}")
    commands_dir = cli_tests_dir / 'commands'
    if commands_dir.exists():
        for test_file in sorted(commands_dir.glob('test_*.py')):
            print(f"  - {test_file.name}")
    print()

    return 0

def check_and_fix_issues():
    """检查并修复常见问题"""
    print_header("检查CLI测试常见问题")

    issues_found = []

    # 检查1: 是否安装了pyarrow
    print_info("检查依赖库...")
    python_cmd = get_python_cmd()
    result = subprocess.run(
        [python_cmd, '-c', 'import pyarrow'],
        capture_output=True
    )

    if result.returncode != 0:
        issues_found.append("缺少 pyarrow 库")
        print_warning("pyarrow 未安装")

        install = input(f"{Colors.OKBLUE}是否安装 pyarrow? [y/N]: {Colors.ENDC}")
        if install.lower() == 'y':
            print_info("正在安装 pyarrow...")
            subprocess.run([python_cmd, '-m', 'pip', 'install', 'pyarrow'])
            print_success("pyarrow 安装完成")
    else:
        print_success("pyarrow 已安装")

    # 检查2: 测试文件是否存在
    print_info("检查测试文件...")
    cli_tests_dir = get_project_root() / 'tests' / 'cli'

    if not cli_tests_dir.exists():
        issues_found.append("CLI测试目录不存在")
        print_error("tests/cli/ 目录不存在")
    else:
        test_files = list(cli_tests_dir.rglob('test_*.py'))
        print_success(f"找到 {len(test_files)} 个测试文件")

    # 检查3: 是否有validate_path导入错误
    print_info("检查导入问题...")
    validators_test = cli_tests_dir / 'utils' / 'test_validators.py'

    if validators_test.exists():
        with open(validators_test, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'validate_path' in content:
                print_warning("test_validators.py 中引用了 validate_path 函数")
                issues_found.append("validate_path 函数未实现")

                print_info("建议: 从测试中移除 validate_path 相关测试，或实现该函数")

    print()
    if issues_found:
        print_header("发现的问题")
        for i, issue in enumerate(issues_found, 1):
            print_error(f"{i}. {issue}")
    else:
        print_success("未发现常见问题")

    print()
    return 0

def interactive_mode():
    """交互式模式"""
    while True:
        choice = show_menu()

        if choice == '0':
            print_info("退出CLI测试运行器")
            return 0
        elif choice == '1':
            return run_all_cli_tests(coverage=True)
        elif choice == '2':
            return run_all_cli_tests(coverage=False)
        elif choice == '3':
            return run_utils_tests(coverage=True)
        elif choice == '4':
            return run_commands_tests(coverage=True)
        # 具体命令测试
        elif choice == 'D':
            return run_specific_test('commands/test_download.py')
        elif choice == 'F':
            return run_specific_test('commands/test_features.py')
        elif choice == 'T':
            return run_specific_test('commands/test_train.py')
        elif choice == 'B':
            return run_specific_test('commands/test_backtest.py')
        elif choice == 'A':
            return run_specific_test('commands/test_analyze.py')
        # 工具模块测试
        elif choice == 'O':
            return run_specific_test('utils/test_output.py')
        elif choice == 'P':
            return run_specific_test('utils/test_progress.py')
        elif choice == 'V':
            return run_specific_test('utils/test_validators.py')
        # 其他选项
        elif choice == 'L':
            list_cli_tests()
            continue
        elif choice == 'I':
            check_and_fix_issues()
            continue
        else:
            print_error("无效的选项，请重新选择")
            continue

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='CLI测试运行器 - 专门用于运行CLI命令行工具的测试',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                    # 交互式菜单
  %(prog)s --all              # 运行所有CLI测试
  %(prog)s --all --coverage   # 运行所有CLI测试并生成覆盖率
  %(prog)s --utils            # 只运行工具模块测试
  %(prog)s --commands         # 只运行命令模块测试
  %(prog)s --test download    # 运行download命令测试
  %(prog)s --list             # 列出所有CLI测试文件
  %(prog)s --check            # 检查并修复常见问题
        """
    )

    parser.add_argument('--all', action='store_true', help='运行所有CLI测试')
    parser.add_argument('--utils', action='store_true', help='运行工具模块测试')
    parser.add_argument('--commands', action='store_true', help='运行命令模块测试')
    parser.add_argument('--test', type=str,
                       choices=['download', 'features', 'train', 'backtest', 'analyze',
                               'output', 'progress', 'validators'],
                       help='运行特定测试')
    parser.add_argument('--list', action='store_true', help='列出所有CLI测试文件')
    parser.add_argument('--check', action='store_true', help='检查并修复常见问题')
    parser.add_argument('--coverage', action='store_true', default=True, help='生成覆盖率报告（默认开启）')
    parser.add_argument('--no-coverage', action='store_true', help='不生成覆盖率报告')
    parser.add_argument('--verbose', action='store_true', help='详细输出模式')

    args = parser.parse_args()

    # 确定覆盖率选项
    coverage = args.coverage and not args.no_coverage

    # 如果没有任何参数，进入交互模式
    if len(sys.argv) == 1:
        return interactive_mode()

    # 列出测试文件
    if args.list:
        return list_cli_tests()

    # 检查问题
    if args.check:
        return check_and_fix_issues()

    # 运行测试
    returncode = 0

    if args.all:
        returncode = run_all_cli_tests(coverage=coverage)
    elif args.utils:
        returncode = run_utils_tests(coverage=coverage)
    elif args.commands:
        returncode = run_commands_tests(coverage=coverage)
    elif args.test:
        # 映射测试名称到文件路径
        test_map = {
            'download': 'commands/test_download.py',
            'features': 'commands/test_features.py',
            'train': 'commands/test_train.py',
            'backtest': 'commands/test_backtest.py',
            'analyze': 'commands/test_analyze.py',
            'output': 'utils/test_output.py',
            'progress': 'utils/test_progress.py',
            'validators': 'utils/test_validators.py',
        }
        returncode = run_specific_test(test_map[args.test], coverage=coverage)
    else:
        parser.print_help()
        return 0

    return returncode

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
