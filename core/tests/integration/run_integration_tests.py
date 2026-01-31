#!/usr/bin/env python3
"""
集成测试运行脚本

运行任务1.3新增的所有集成测试，并生成测试报告
"""

import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime


def run_tests(output_file=None, verbose=False, specific_test=None):
    """运行集成测试"""

    # 测试文件列表
    test_files = [
        'test_end_to_end_workflow.py',
        'test_multi_data_source.py',
        'test_persistence_integration.py',
    ]

    # 如果指定了特定测试
    if specific_test:
        test_files = [f for f in test_files if specific_test in f]

    # 构建pytest命令
    cmd = [
        sys.executable, '-m', 'pytest',
        *test_files,
        '-v',
        '--tb=short',
    ]

    if output_file:
        cmd.extend(['--html=' + output_file, '--self-contained-html'])

    if verbose:
        cmd.append('-s')

    # 添加覆盖率选项
    cmd.extend(['--cov=src', '--cov-report=term-missing'])

    print("=" * 80)
    print("运行集成测试 (任务1.3)")
    print("=" * 80)
    print(f"\n测试文件:")
    for f in test_files:
        print(f"  - {f}")
    print(f"\n运行命令:")
    print(f"  {' '.join(cmd)}")
    print("=" * 80)
    print()

    # 运行测试
    result = subprocess.run(cmd, cwd=Path(__file__).parent)

    return result.returncode


def print_summary(returncode):
    """打印测试总结"""
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)

    if returncode == 0:
        print("✅ 所有测试通过")
    elif returncode == 5:
        print("⚠️  所有测试被跳过 (可能缺少依赖)")
    else:
        print(f"❌ 测试失败 (退出码: {returncode})")

    print("\n提示:")
    print("  - 如果测试被跳过，请检查是否安装了必需依赖")
    print("  - 运行 'pip install akshare lightgbm pyarrow' 安装常用依赖")
    print("  - 查看 README.md 了解详细的依赖要求")
    print("=" * 80)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='运行集成测试 (任务1.3)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 运行所有集成测试
  python run_integration_tests.py

  # 生成HTML报告
  python run_integration_tests.py --report report.html

  # 运行特定测试
  python run_integration_tests.py --test end_to_end

  # 详细输出
  python run_integration_tests.py -v
        """
    )

    parser.add_argument(
        '--report', '-r',
        help='生成HTML报告文件',
        metavar='FILE'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='显示详细输出'
    )

    parser.add_argument(
        '--test', '-t',
        help='运行特定测试 (end_to_end, multi_data, persistence)',
        choices=['end_to_end', 'multi_data', 'persistence'],
        metavar='TEST'
    )

    args = parser.parse_args()

    # 运行测试
    returncode = run_tests(
        output_file=args.report,
        verbose=args.verbose,
        specific_test=args.test
    )

    # 打印总结
    print_summary(returncode)

    sys.exit(returncode)


if __name__ == '__main__':
    main()
