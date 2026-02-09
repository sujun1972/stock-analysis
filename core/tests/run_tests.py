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
    python run_tests.py --layer strategies # 运行策略层测试
    python run_tests.py --layer data       # 运行数据层测试
    python run_tests.py --list-modules     # 列出所有测试模块
    python run_tests.py --module xxx       # 运行指定模块测试
    python run_tests.py --parallel         # 并行运行测试
    python run_tests.py --failed-first     # 优先运行上次失败的测试
    python run_tests.py --min-coverage 80  # 设置最小覆盖率阈值

作者: Stock Analysis Team
创建: 2026-01-29
更新: 2026-01-30
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
    # Core项目使用自己的虚拟环境
    venv_path = get_project_root() / 'venv'
    return venv_path.exists()

def get_python_cmd() -> str:
    """获取Python命令"""
    # Core项目使用自己的虚拟环境
    venv_path = get_project_root() / 'venv'
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
        'coverage': None,
        'interrupted': False
    }

    # 首先尝试从最终统计行解析 (例如: "1427 passed, 17 skipped in 26.95s")
    result_pattern = r'(\d+)\s+(passed|failed|skipped|error)'
    found_summary = False
    for match in re.finditer(result_pattern, output):
        found_summary = True
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

    # 如果没有找到统计行（测试被中断），从实时输出中统计
    if not found_summary:
        stats['interrupted'] = True
        # 统计每一行的测试结果
        passed_pattern = r'PASSED\s+\['
        failed_pattern = r'FAILED\s+\['
        skipped_pattern = r'SKIPPED\s+\['
        error_pattern = r'ERROR\s+\['

        stats['passed'] = len(re.findall(passed_pattern, output))
        stats['failed'] = len(re.findall(failed_pattern, output))
        stats['skipped'] = len(re.findall(skipped_pattern, output))
        stats['errors'] = len(re.findall(error_pattern, output))

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

    # 检查是否被中断
    if stats.get('interrupted', False):
        print_warning("⚠️  测试运行被中断或未完成")

    print(f"{Colors.BOLD}执行时间:{Colors.ENDC} {duration:.2f}秒")
    print(f"{Colors.BOLD}总测试数:{Colors.ENDC} {total}", end="")
    if stats.get('interrupted', False):
        print(f" {Colors.WARNING}(统计自实时输出，可能不完整){Colors.ENDC}")
    else:
        print()
    print()

    if total == 0:
        print_error("未检测到任何测试结果")
        print_warning("可能原因:")
        print("  • 测试在收集阶段失败")
        print("  • pytest输出格式改变")
        print("  • 测试进程被强制终止")
        print()
        return

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

        # 如果有失败或错误，显示详细信息提示
        if stats['failed'] > 0 or stats['errors'] > 0:
            print_warning("\n提示: 要查看失败测试的详细信息，请向上滚动查看完整输出")
            print_info("或者运行: pytest <测试文件> -v --tb=short 来查看特定测试的详细信息")

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

    # 总是排除CLI测试（使用专门的run_cli_tests.py运行）
    cmd.append('--ignore=tests/cli/')
    print_info("已排除CLI测试（请使用 python run_cli_tests.py 运行CLI测试）")

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
        # 排除GRU模型测试（最慢的测试，会导致段错误）
        cmd.append('--ignore=tests/unit/models/test_gru_model.py')
        cmd.append('--ignore=tests/unit/test_gru_model_comprehensive.py')

        # 排除耗时的单元测试（每个测试1-5秒）
        cmd.append('--ignore=tests/unit/analysis/test_factor_analyzer.py')  # 5.28s, 4.20s, 1.76s
        cmd.append('--ignore=tests/unit/backtest/test_parallel_backtester.py')  # 1.07s, 1.04s, 1.01s
        cmd.append('--ignore=tests/unit/utils/test_parallel_executor.py')  # 1.55s, 1.29s, 1.12s

        # 排除外部API集成测试（需要网络连接和API token）
        cmd.append('--ignore=tests/integration/providers/akshare/')
        cmd.append('--ignore=tests/integration/providers/test_tushare_provider.py')
        print_warning("已排除慢速测试：GRU模型、因子分析器、并行回测、并行执行器、外部API")

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

    # 预计时间（基于2026-02-01实测数据 - 已优化）
    estimated_times = {
        '1': '~260秒 (4.5分钟)',
        '2': '~38秒',        # 快速单元测试（已优化）⚡
        '3': '~80秒',        # 所有单元测试 (排除GRU)
        '4': '~175秒 (3分钟)',  # 所有集成测试
        '5': '~3秒',
        '6': '变化',
        'I1': '~30秒',       # 集成测试-快速
        'I2': '~120秒',      # 集成测试-完整不含外部API
        'I3': '~175秒',      # 集成测试-全部
    }

    print("请选择要运行的测试:")
    print()
    print(f"{Colors.BOLD}[快速测试 - 推荐日常使用]{Colors.ENDC}")
    print(f"  {Colors.BOLD}[2]{Colors.ENDC} 快速单元测试 (排除慢速测试: GRU/因子分析/并行) {Colors.OKCYAN}[{estimated_times['2']}]{Colors.ENDC} ⚡")
    print(f"  {Colors.BOLD}[Q]{Colors.ENDC} 快速集成测试 (排除外部API) {Colors.OKCYAN}[{estimated_times['I1']}]{Colors.ENDC}")
    print(f"  {Colors.BOLD}[X]{Colors.ENDC} 快速诊断 (只运行失败过的测试) {Colors.OKCYAN}[<10秒]{Colors.ENDC}")
    print(f"  {Colors.BOLD}[QM]{Colors.ENDC} ML快速验证 (ML-2/ML-3/ML-4) {Colors.OKCYAN}[~15秒]{Colors.ENDC} 🚀")
    print()
    print(f"{Colors.BOLD}[完整测试]{Colors.ENDC}")
    print(f"  {Colors.BOLD}[1]{Colors.ENDC} 运行所有测试 (单元+集成, 带覆盖率) {Colors.OKCYAN}[{estimated_times['1']}]{Colors.ENDC}")
    print(f"  {Colors.BOLD}[3]{Colors.ENDC} 所有单元测试 (排除GRU) {Colors.OKCYAN}[{estimated_times['3']}]{Colors.ENDC}")
    print(f"  {Colors.BOLD}[4]{Colors.ENDC} 所有集成测试 {Colors.OKCYAN}[{estimated_times['4']}]{Colors.ENDC}")
    print(f"  {Colors.BOLD}[5]{Colors.ENDC} 性能测试 {Colors.OKCYAN}[{estimated_times['5']}]{Colors.ENDC}")
    print()
    print(f"{Colors.BOLD}[集成测试分类 - 按速度]{Colors.ENDC}")
    print(f"  {Colors.BOLD}[I1]{Colors.ENDC} 快速集成测试 (排除外部API) {Colors.OKCYAN}[{estimated_times['I1']}]{Colors.ENDC}")
    print(f"  {Colors.BOLD}[I2]{Colors.ENDC} 中速集成测试 (含数据库/不含API) {Colors.OKCYAN}[{estimated_times['I2']}]{Colors.ENDC}")
    print(f"  {Colors.BOLD}[I3]{Colors.ENDC} 完整集成测试 (含外部API) {Colors.OKCYAN}[{estimated_times['I3']}]{Colors.ENDC}")
    print()
    print(f"{Colors.BOLD}[单元测试 - 按功能层]{Colors.ENDC}")
    print(f"  {Colors.BOLD}[D]{Colors.ENDC} 数据层 (data + providers) {Colors.OKCYAN}[~8秒]{Colors.ENDC}")
    print(f"  {Colors.BOLD}[F]{Colors.ENDC} 特征层 (features) {Colors.OKCYAN}[~15秒]{Colors.ENDC}")
    print(f"  {Colors.BOLD}[M]{Colors.ENDC} 模型层 (models, 排除GRU) {Colors.OKCYAN}[~20秒]{Colors.ENDC}")
    print(f"  {Colors.BOLD}[B]{Colors.ENDC} 回测层 (backtest) {Colors.OKCYAN}[~8秒]{Colors.ENDC}")
    print(f"  {Colors.BOLD}[S]{Colors.ENDC} 策略层 (strategies) {Colors.OKCYAN}[~5秒]{Colors.ENDC}")
    print(f"  {Colors.BOLD}[R]{Colors.ENDC} 风控层 (risk_management) {Colors.OKCYAN}[~2秒]{Colors.ENDC}")
    print(f"  {Colors.BOLD}[A]{Colors.ENDC} 因子分析层 (analysis) {Colors.OKCYAN}[~4秒]{Colors.ENDC}")
    print(f"  {Colors.BOLD}[O]{Colors.ENDC} 参数优化层 (optimization) {Colors.OKCYAN}[~3秒]{Colors.ENDC}")
    print()
    print(f"{Colors.BOLD}[其他选项]{Colors.ENDC}")
    print(f"  {Colors.BOLD}[6]{Colors.ENDC} 运行特定模块测试 {Colors.OKCYAN}[{estimated_times['6']}]{Colors.ENDC}")
    print(f"  {Colors.BOLD}[L]{Colors.ENDC} 按层级查看所有可用测试模块 {Colors.OKCYAN}[<1秒]{Colors.ENDC}")
    print(f"  {Colors.BOLD}[P]{Colors.ENDC} 切换并行模式 (加速测试执行)")
    print(f"  {Colors.BOLD}[T]{Colors.ENDC} 查看测试统计信息")
    print(f"  {Colors.BOLD}[0]{Colors.ENDC} 退出")
    print()

    choice = input(f"{Colors.OKBLUE}请输入选项: {Colors.ENDC}")
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

def run_integration_tests(coverage: bool = True, parallel: bool = False, speed_level: str = 'all'):
    """
    运行集成测试

    Args:
        coverage: 是否生成覆盖率报告
        parallel: 是否并行运行
        speed_level: 速度级别
            - 'fast': 快速测试，排除外部API和慢速测试 (~30秒)
            - 'medium': 中速测试，包含数据库测试，排除外部API (~120秒)
            - 'all': 所有集成测试 (~175秒)
    """
    if speed_level == 'fast':
        print_header("运行快速集成测试 (排除外部API和慢速测试)")
    elif speed_level == 'medium':
        print_header("运行中速集成测试 (包含数据库，排除外部API)")
    else:
        print_header("运行所有集成测试")

    # 构建命令
    python_cmd = get_python_cmd()
    cmd = [python_cmd, '-m', 'pytest', 'tests/integration/']

    # 根据速度级别排除测试
    if speed_level in ['fast', 'medium']:
        # 排除外部API测试 (最耗时: 每个测试4-5秒)
        cmd.append('--ignore=tests/integration/providers/')
        cmd.append('--ignore=tests/integration/test_multi_data_source.py')
        cmd.append('--ignore=tests/integration/test_end_to_end_workflow.py')
        print_info("已排除外部API测试 (providers, multi_data_source, end_to_end_workflow)")

    if speed_level == 'fast':
        # 额外排除中速测试
        cmd.append('--ignore=tests/integration/test_database_security_and_concurrency.py')
        cmd.append('--ignore=tests/integration/test_database_manager_refactored.py')
        cmd.append('--ignore=tests/integration/test_parallel_ic_calculation.py')
        cmd.append('--ignore=tests/integration/test_gpu_integration.py')
        cmd.append('--ignore=tests/integration/test_model_trainer_integration.py')
        print_info("已排除数据库和GPU相关慢速测试")

    # 覆盖率选项
    if coverage:
        cmd.extend([
            '--cov=src',
            '--cov-report=html:tests/reports/htmlcov',
            '--cov-report=term',
        ])

    # 其他选项
    cmd.extend(['-v', '--tb=short'])

    if parallel:
        cmd.extend(['-n', '4'])

    returncode, _ = run_command(cmd, "运行集成测试", capture_output=True)
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

def run_quick_tests():
    """
    运行ML快速验证测试（ML-2, ML-3, ML-4）

    这些测试验证核心ML功能的完整工作流程：
    - ML-2: 多因子加权模型（归一化、因子权重、因子分组）
    - ML-3: LightGBM排序模型（训练、保存、加载、选股）
    - ML-4: 因子库集成（125+因子、通配符特征、性能对比）
    """
    print_header("运行ML快速验证测试")

    print_info("这些测试将验证以下ML功能模块:")
    print("  • ML-2: 多因子加权模型增强功能")
    print("  • ML-3: LightGBM排序模型训练与选股")
    print("  • ML-4: 完整因子库集成（125+因子）")
    print()

    # 运行ML相关的单元测试
    print_info("运行ML选股器单元测试...")
    cmd = build_pytest_cmd(
        'tests/unit/strategies/three_layer/selectors/test_ml_selector.py',
        coverage=False,
        verbose=True
    )
    returncode, output = run_command(cmd, "运行ML选股器测试", capture_output=True)

    if returncode == 0:
        print_success("✅ ML快速验证测试全部通过!")
        print()
        print_info("验证的功能包括:")
        print("  ✓ 多因子加权模型（归一化、权重配置）")
        print("  ✓ LightGBM排序模型（训练、预测）")
        print("  ✓ 因子库集成（125+因子）")
        print("  ✓ 通配符特征解析")
        print("  ✓ 向后兼容性")
        return 0
    else:
        print_error("❌ ML快速验证测试失败")
        print_warning("请检查上述输出以了解失败原因")
        return 1

def run_layer_tests(layer: str, coverage: bool = True, parallel: bool = False):
    """
    按核心层运行测试

    Args:
        layer: 层级名称 ('data', 'features', 'models', 'backtest', 'strategies',
                        'risk_management', 'analysis', 'optimization')
        coverage: 是否生成覆盖率
        parallel: 是否并行运行
    """
    layer_config = {
        'data': {
            'name': '数据层',
            'paths': ['tests/unit/data/', 'tests/unit/providers/'],
            'src': ['src/data/', 'src/providers/']
        },
        'features': {
            'name': '特征层',
            'paths': ['tests/unit/features/'],
            'src': ['src/features/']
        },
        'models': {
            'name': '模型层',
            'paths': ['tests/unit/models/'],
            'src': ['src/models/'],
            'exclude': ['tests/unit/models/test_gru_model.py', 'tests/unit/test_gru_model_comprehensive.py']
        },
        'backtest': {
            'name': '回测层',
            'paths': ['tests/unit/backtest/', 'tests/integration/test_backtest_with_cost_analysis.py'],
            'src': ['src/backtest/']
        },
        'strategies': {
            'name': '策略层',
            'paths': ['tests/unit/strategies/'],
            'src': ['src/strategies/']
        },
        'risk_management': {
            'name': '风控层',
            'paths': ['tests/unit/risk_management/'],
            'src': ['src/risk_management/']
        },
        'analysis': {
            'name': '因子分析层',
            'paths': ['tests/unit/analysis/'],
            'src': ['src/analysis/']
        },
        'optimization': {
            'name': '参数优化层',
            'paths': ['tests/unit/optimization/'],
            'src': ['src/optimization/']
        }
    }

    if layer not in layer_config:
        print_error(f"未知的层级: {layer}")
        return 1

    config = layer_config[layer]
    print_header(f"运行{config['name']}测试")

    # 构建测试路径
    test_paths = ' '.join(config['paths'])

    # 构建pytest命令
    python_cmd = get_python_cmd()
    cmd = [python_cmd, '-m', 'pytest'] + config['paths']

    # 添加覆盖率选项
    if coverage:
        # 为每个源码路径单独添加 --cov 参数
        for src_path in config['src']:
            cmd.append(f'--cov={src_path}')
        cmd.extend([
            '--cov-report=html:tests/reports/htmlcov',
            '--cov-report=term',
        ])

    # 添加排除项
    if 'exclude' in config:
        for exclude_path in config['exclude']:
            cmd.extend(['--ignore', exclude_path])

    # 添加其他选项
    cmd.extend(['-v', '--tb=short'])

    if parallel:
        cmd.extend(['-n', '4'])

    returncode, output = run_command(cmd, f"运行{config['name']}测试", capture_output=True)
    return returncode

def list_all_test_modules():
    """列出所有可用的测试模块（按层级）"""
    print_header("可用的测试模块")

    layers = {
        '数据层': 'tests/unit/data tests/unit/providers',
        '特征层': 'tests/unit/features',
        '模型层': 'tests/unit/models',
        '回测层': 'tests/unit/backtest',
        '策略层': 'tests/unit/strategies',
        '风控层': 'tests/unit/risk_management',
        '因子分析层': 'tests/unit/analysis',
        '参数优化层': 'tests/unit/optimization',
        '配置层': 'tests/unit/config',
        '工具层': 'tests/unit/utils',
    }

    for layer_name, path in layers.items():
        print(f"\n{Colors.BOLD}{layer_name}:{Colors.ENDC}")
        paths = path.split()
        for p in paths:
            full_path = get_project_root() / p
            if full_path.exists():
                files = sorted(full_path.glob('test_*.py'))
                for f in files:
                    print(f"  - {f.relative_to(get_project_root())}")

    print()
    return 0

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
    returncode, _ = run_command(cmd, "优先运行失败测试", capture_output=True)
    return returncode

def show_test_statistics():
    """显示测试统计信息"""
    print_header("测试统计信息")

    test_categories = {
        '单元测试': {
            '数据层': 'tests/unit/data tests/unit/providers',
            '特征层': 'tests/unit/features',
            '模型层': 'tests/unit/models',
            '回测层': 'tests/unit/backtest',
            '策略层': 'tests/unit/strategies',
            '风控层': 'tests/unit/risk_management',
            '因子分析层': 'tests/unit/analysis',
            '参数优化层': 'tests/unit/optimization',
            '其他': 'tests/unit/config tests/unit/utils tests/unit/api',
        },
        '集成测试': {
            '外部API (慢)': 'tests/integration/providers tests/integration/test_multi_data_source.py tests/integration/test_end_to_end_workflow.py',
            '数据库 (中)': 'tests/integration/test_database_*.py',
            'GPU/模型 (中)': 'tests/integration/test_gpu_integration.py tests/integration/test_model_trainer_integration.py',
            '其他 (快)': 'tests/integration/test_phase*.py tests/integration/test_backtest*.py tests/integration/test_feature*.py',
        }
    }

    for category, subcats in test_categories.items():
        print(f"\n{Colors.BOLD}{category}:{Colors.ENDC}")
        for subcat, paths in subcats.items():
            count = 0
            for path in paths.split():
                full_path = get_project_root() / path
                if full_path.exists():
                    if full_path.is_file():
                        count += 1
                    else:
                        files = list(full_path.glob('test_*.py'))
                        count += len(files)

            print(f"  {subcat}: {count} 个测试文件")

    print(f"\n{Colors.BOLD}耗时参考 (基于2026-02-01实测):{Colors.ENDC}")
    print(f"  快速单元测试: ~38秒 (2582个测试) ⚡")
    print(f"  完整单元测试 (排除GRU): ~80秒 (2665个测试)")
    print(f"  快速集成测试: ~30秒")
    print(f"  中速集成测试: ~120秒")
    print(f"  完整集成测试: ~175秒")
    print(f"  所有测试: ~260秒 (4.5分钟)")
    print()

    return 0

def interactive_mode():
    """交互式模式"""
    parallel_mode = False

    while True:
        choice = show_menu()

        if choice == '0':
            print_info("退出测试运行器")
            return 0
        # 快速测试
        elif choice == '2':
            return run_all_tests(coverage=False, fast=True, parallel=parallel_mode)
        elif choice == 'Q':
            return run_integration_tests(coverage=False, parallel=parallel_mode, speed_level='fast')
        elif choice == 'X':
            return run_failed_first()
        elif choice == 'QM':
            return run_quick_tests()
        # 完整测试
        elif choice == '1':
            return run_all_tests(coverage=True, fast=False, parallel=parallel_mode)
        elif choice == '3':
            return run_unit_tests(coverage=True, parallel=parallel_mode)
        elif choice == '4':
            return run_integration_tests(coverage=True, parallel=parallel_mode, speed_level='all')
        elif choice == '5':
            return run_performance_tests()
        # 集成测试分类
        elif choice == 'I1':
            return run_integration_tests(coverage=False, parallel=parallel_mode, speed_level='fast')
        elif choice == 'I2':
            return run_integration_tests(coverage=False, parallel=parallel_mode, speed_level='medium')
        elif choice == 'I3':
            return run_integration_tests(coverage=True, parallel=parallel_mode, speed_level='all')
        # 单元测试按层
        elif choice == 'D':
            return run_layer_tests('data', coverage=True, parallel=parallel_mode)
        elif choice == 'F':
            return run_layer_tests('features', coverage=True, parallel=parallel_mode)
        elif choice == 'M':
            return run_layer_tests('models', coverage=True, parallel=parallel_mode)
        elif choice == 'B':
            return run_layer_tests('backtest', coverage=True, parallel=parallel_mode)
        elif choice == 'S':
            return run_layer_tests('strategies', coverage=True, parallel=parallel_mode)
        elif choice == 'R':
            return run_layer_tests('risk_management', coverage=True, parallel=parallel_mode)
        elif choice == 'A':
            return run_layer_tests('analysis', coverage=True, parallel=parallel_mode)
        elif choice == 'O':
            return run_layer_tests('optimization', coverage=True, parallel=parallel_mode)
        # 其他选项
        elif choice == '6':
            return run_specific_module()
        elif choice == 'L':
            list_all_test_modules()
            continue
        elif choice == 'T':
            show_test_statistics()
            continue
        elif choice == 'P':
            parallel_mode = not parallel_mode
            if parallel_mode:
                print_success("✓ 已启用并行模式 (使用4个工作进程)")
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
  %(prog)s --quick-ml                # ML快速验证测试（ML-2/ML-3/ML-4）
  %(prog)s --unit                    # 只运行单元测试
  %(prog)s --integration             # 只运行集成测试
  %(prog)s --performance             # 只运行性能测试

  # 核心层测试（推荐）
  %(prog)s --layer strategies        # 运行策略层测试
  %(prog)s --layer data              # 运行数据层测试（含providers）
  %(prog)s --layer features          # 运行特征层测试
  %(prog)s --layer models            # 运行模型层测试
  %(prog)s --layer backtest          # 运行回测层测试
  %(prog)s --layer risk_management   # 运行风控层测试
  %(prog)s --layer analysis          # 运行因子分析层测试
  %(prog)s --layer optimization      # 运行参数优化层测试
  %(prog)s --layer data --parallel   # 并行运行数据层测试
  %(prog)s --list-modules            # 列出所有可用测试模块

  # 传统模块测试（兼容旧版）
  %(prog)s --providers               # 运行Provider测试
  %(prog)s --models                  # 运行模型测试
  %(prog)s --features                # 运行特征工程测试
  %(prog)s --module unit/test_xxx.py # 运行特定模块
  %(prog)s --failed-first            # 优先运行失败的测试
  %(prog)s --min-coverage 80         # 设置最小覆盖率阈值
        """
    )

    # 综合测试选项
    parser.add_argument('--all', action='store_true', help='运行所有测试')
    parser.add_argument('--fast', action='store_true', help='快速模式（排除慢速测试和外部API测试）')
    parser.add_argument('--unit', action='store_true', help='运行单元测试')
    parser.add_argument('--integration', action='store_true', help='运行集成测试')
    parser.add_argument('--performance', action='store_true', help='运行性能测试')
    parser.add_argument('--quick-ml', action='store_true', help='运行ML快速验证测试（ML-2/ML-3/ML-4）')

    # 核心层测试选项
    parser.add_argument('--layer', type=str, choices=[
        'data', 'features', 'models', 'backtest', 'strategies',
        'risk_management', 'analysis', 'optimization'
    ], help='运行指定核心层的测试')

    # 传统模块测试选项（保持向后兼容）
    parser.add_argument('--providers', action='store_true', help='运行Provider测试')
    parser.add_argument('--models', action='store_true', help='运行模型测试')
    parser.add_argument('--features', action='store_true', help='运行特征工程测试')
    parser.add_argument('--module', type=str, help='运行特定模块测试')

    # 其他选项
    parser.add_argument('--list-modules', action='store_true', help='列出所有可用的测试模块')
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

    # 列出模块
    if args.list_modules:
        return list_all_test_modules()

    # 快速ML验证测试
    if args.quick_ml:
        return run_quick_tests()
    # 核心层测试
    elif args.layer:
        returncode = run_layer_tests(args.layer, coverage=coverage, parallel=args.parallel)
    # 综合测试
    elif args.all or args.fast:
        returncode = run_all_tests(coverage=coverage, fast=args.fast,
                                   parallel=args.parallel, failed_first=args.failed_first)
    elif args.unit:
        returncode = run_unit_tests(coverage=coverage, parallel=args.parallel)
    elif args.integration:
        returncode = run_integration_tests(coverage=coverage, parallel=args.parallel, speed_level='all')
    elif args.performance:
        returncode = run_performance_tests()
    # 传统模块测试（保持向后兼容）
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
        returncode, _ = run_command(cmd, f"运行 {args.module}", capture_output=True)
    elif args.failed_first:
        returncode = run_failed_first()
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
