#!/usr/bin/env python3
"""
统一测试运行器 - Core项目

功能：
- 运行所有测试或选择特定测试
- 生成覆盖率报告并检查阈值
- 支持排除慢速测试
- 交互式菜单选择（显示预计时间）
- 详细的测试报告和统计
- 并行测试支持
- 失败测试优先重试

使用方法：
    python run_tests.py                    # 交互式菜单
    python run_tests.py --all              # 运行所有测试
    python run_tests.py --unit             # 只运行单元测试
    python run_tests.py --integration      # 只运行集成测试
    python run_tests.py --coverage         # 运行测试并生成覆盖率报告
    python run_tests.py --fast             # 快速测试（排除慢速测试）
    python run_tests.py --module xxx       # 运行指定模块测试
    python run_tests.py --parallel         # 并行运行测试
    python run_tests.py --failed-first     # 优先运行上次失败的测试
    python run_tests.py --min-coverage 80  # 设置最小覆盖率阈值

作者: Stock Analysis Team
创建: 2026-01-29
更新: 2026-01-29
"""

import sys
import os
import argparse
import subprocess
import time
import json
import re
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from datetime import datetime

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

    # 解析测试结果行 (例如: "1427 passed, 17 skipped in 26.95s")
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
    print_header("测试执行摘要")

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

def check_coverage_threshold(output: str, min_coverage: int) -> bool:
    """检查覆盖率是否达到阈值"""
    coverage_pattern = r'TOTAL\s+\d+\s+\d+\s+(\d+)%'
    coverage_match = re.search(coverage_pattern, output)

    if not coverage_match:
        print_warning("无法提取覆盖率信息")
        return True

    coverage = int(coverage_match.group(1))

    if coverage < min_coverage:
        print_error(f"覆盖率 {coverage}% 低于阈值 {min_coverage}%")
        return False

    print_success(f"覆盖率 {coverage}% 达到阈值 {min_coverage}%")
    return True

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
    exclude_slow: bool = False,
    markers: Optional[str] = None,
    timeout: Optional[int] = None,
    parallel: bool = False,
    failed_first: bool = False,
    num_workers: int = 4
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

    # 并行测试
    if parallel:
        cmd.extend(['-n', str(num_workers)])
        print_info(f"启用并行测试，使用 {num_workers} 个工作进程")

    # 优先运行失败的测试
    if failed_first:
        cmd.append('--failed-first')
        print_info("优先运行上次失败的测试")

    # 其他有用的选项
    cmd.extend([
        '--tb=short',  # 简短的错误回溯
    ])

    return cmd

def show_menu():
    """显示交互式菜单"""
    print_header("Core项目测试运行器")

    # 预计时间（基于历史数据）
    estimated_times = {
        '1': '~90秒',
        '2': '~27秒',
        '3': '~60秒',
        '4': '~30秒',
        '5': '~3秒',
        '6': '变化',
        '7': '~5秒',
        '8': '~20秒',
        '9': '~15秒'
    }

    print("请选择要运行的测试:")
    print()
    print(f"{Colors.BOLD}[1]{Colors.ENDC} 运行所有测试 (带覆盖率报告) {Colors.OKCYAN}[{estimated_times['1']}]{Colors.ENDC}")
    print(f"{Colors.BOLD}[2]{Colors.ENDC} 运行所有测试 (快速模式，排除慢速测试和外部API测试) {Colors.OKCYAN}[{estimated_times['2']}]{Colors.ENDC}")
    print(f"{Colors.BOLD}[3]{Colors.ENDC} 只运行单元测试 {Colors.OKCYAN}[{estimated_times['3']}]{Colors.ENDC}")
    print(f"{Colors.BOLD}[4]{Colors.ENDC} 只运行集成测试 {Colors.OKCYAN}[{estimated_times['4']}]{Colors.ENDC}")
    print(f"{Colors.BOLD}[5]{Colors.ENDC} 只运行性能测试 {Colors.OKCYAN}[{estimated_times['5']}]{Colors.ENDC}")
    print(f"{Colors.BOLD}[6]{Colors.ENDC} 运行特定模块测试 {Colors.OKCYAN}[{estimated_times['6']}]{Colors.ENDC}")
    print(f"{Colors.BOLD}[7]{Colors.ENDC} 运行Provider测试 (AkShare + Tushare) {Colors.OKCYAN}[{estimated_times['7']}]{Colors.ENDC}")
    print(f"{Colors.BOLD}[8]{Colors.ENDC} 运行模型测试 (排除GRU) {Colors.OKCYAN}[{estimated_times['8']}]{Colors.ENDC}")
    print(f"{Colors.BOLD}[9]{Colors.ENDC} 运行特征工程测试 {Colors.OKCYAN}[{estimated_times['9']}]{Colors.ENDC}")
    print()
    print(f"{Colors.BOLD}[F]{Colors.ENDC} 快速诊断 (只运行失败过的测试)")
    print(f"{Colors.BOLD}[P]{Colors.ENDC} 并行模式 (加速测试执行)")
    print(f"{Colors.BOLD}[0]{Colors.ENDC} 退出")
    print()

    choice = input(f"{Colors.OKBLUE}请输入选项 [0-9/F/P]: {Colors.ENDC}")
    return choice.strip().upper()

def run_all_tests(coverage: bool = True, fast: bool = False, parallel: bool = False, failed_first: bool = False):
    """运行所有测试"""
    print_header("运行所有测试")
    cmd = build_pytest_cmd(coverage=coverage, exclude_slow=fast, parallel=parallel, failed_first=failed_first)
    returncode, output = run_command(cmd, "运行完整测试套件", capture_output=True)
    return returncode

def run_unit_tests(coverage: bool = True, parallel: bool = False):
    """运行单元测试"""
    print_header("运行单元测试")
    cmd = build_pytest_cmd('tests/unit/', coverage=coverage, parallel=parallel)
    returncode, output = run_command(cmd, "运行单元测试", capture_output=True)
    return returncode

def run_integration_tests(coverage: bool = True, parallel: bool = False):
    """运行集成测试"""
    print_header("运行集成测试")
    cmd = build_pytest_cmd('tests/integration/', coverage=coverage, parallel=parallel)
    returncode, output = run_command(cmd, "运行集成测试", capture_output=True)
    return returncode

def run_performance_tests():
    """运行性能测试"""
    print_header("运行性能测试")
    cmd = build_pytest_cmd('tests/performance/', coverage=False)
    returncode, output = run_command(cmd, "运行性能测试", capture_output=True)
    return returncode

def run_provider_tests(coverage: bool = True):
    """运行Provider测试"""
    print_header("运行Provider测试")

    print_info("运行单元测试...")
    cmd = build_pytest_cmd('tests/unit/providers/', coverage=coverage)
    ret1, _ = run_command(cmd, capture_output=True)

    print_info("运行集成测试...")
    cmd2 = build_pytest_cmd('tests/integration/providers/', coverage=coverage)
    ret2, _ = run_command(cmd2, capture_output=True)

    return ret1 + ret2

def run_model_tests(coverage: bool = True, exclude_gru: bool = True):
    """运行模型测试"""
    print_header("运行模型测试")

    if exclude_gru:
        print_warning("排除GRU模型测试（训练较慢）")
        cmd = build_pytest_cmd('tests/unit/models/', coverage=coverage, exclude_slow=True)
    else:
        cmd = build_pytest_cmd('tests/unit/models/', coverage=coverage)

    returncode, output = run_command(cmd, "运行模型测试", capture_output=True)
    return returncode

def run_feature_tests(coverage: bool = True):
    """运行特征工程测试"""
    print_header("运行特征工程测试")
    cmd = build_pytest_cmd('tests/unit/features/', coverage=coverage)
    returncode, output = run_command(cmd, "运行特征工程测试", capture_output=True)
    return returncode

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
    returncode, output = run_command(cmd, f"运行 {module}", capture_output=True)
    return returncode

def run_failed_first():
    """优先运行失败的测试"""
    print_header("快速诊断 - 运行失败过的测试")
    cmd = build_pytest_cmd(coverage=False, failed_first=True, exclude_slow=True)
    returncode, output = run_command(cmd, "优先运行失败测试", capture_output=True)
    return returncode

def interactive_mode():
    """交互式模式"""
    parallel_mode = False

    while True:
        choice = show_menu()

        if choice == '0':
            print_info("退出测试运行器")
            return 0
        elif choice == '1':
            return run_all_tests(coverage=True, fast=False, parallel=parallel_mode)
        elif choice == '2':
            return run_all_tests(coverage=True, fast=True, parallel=parallel_mode)
        elif choice == '3':
            return run_unit_tests(coverage=True, parallel=parallel_mode)
        elif choice == '4':
            return run_integration_tests(coverage=True, parallel=parallel_mode)
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
        elif choice == 'F':
            return run_failed_first()
        elif choice == 'P':
            parallel_mode = not parallel_mode
            if parallel_mode:
                print_success("已启用并行模式")
            else:
                print_info("已禁用并行模式")
            continue
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
  %(prog)s --fast --parallel         # 快速+并行测试
  %(prog)s --unit                    # 只运行单元测试
  %(prog)s --integration             # 只运行集成测试
  %(prog)s --performance             # 只运行性能测试
  %(prog)s --providers               # 运行Provider测试
  %(prog)s --models                  # 运行模型测试
  %(prog)s --features                # 运行特征工程测试
  %(prog)s --module unit/test_xxx.py # 运行特定模块
  %(prog)s --failed-first            # 优先运行失败的测试
  %(prog)s --min-coverage 80         # 设置最小覆盖率阈值
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
    parser.add_argument('--parallel', action='store_true', help='并行运行测试')
    parser.add_argument('--failed-first', action='store_true', help='优先运行上次失败的测试')
    parser.add_argument('--min-coverage', type=int, default=0, help='最小覆盖率阈值（百分比）')
    parser.add_argument('--workers', type=int, default=4, help='并行工作进程数（默认4）')

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
    returncode = 0
    output = ""

    if args.all or args.fast:
        returncode = run_all_tests(coverage=coverage, fast=args.fast,
                                   parallel=args.parallel, failed_first=args.failed_first)
    elif args.unit:
        returncode = run_unit_tests(coverage=coverage, parallel=args.parallel)
    elif args.integration:
        returncode = run_integration_tests(coverage=coverage, parallel=args.parallel)
    elif args.performance:
        returncode = run_performance_tests()
    elif args.providers:
        returncode = run_provider_tests(coverage=coverage)
    elif args.models:
        returncode = run_model_tests(coverage=coverage, exclude_gru=True)
    elif args.features:
        returncode = run_feature_tests(coverage=coverage)
    elif args.module:
        test_path = f"tests/{args.module}"
        if not Path(get_project_root() / test_path).exists():
            print_error(f"测试文件不存在: {test_path}")
            return 1
        cmd = build_pytest_cmd(test_path, coverage=coverage)
        returncode, output = run_command(cmd, f"运行 {args.module}", capture_output=True)
    elif args.failed_first:
        returncode = run_failed_first()
    else:
        parser.print_help()
        return 0

    # 检查覆盖率阈值
    if args.min_coverage > 0 and coverage and output:
        if not check_coverage_threshold(output, args.min_coverage):
            return 1

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
