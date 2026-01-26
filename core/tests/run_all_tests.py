#!/usr/bin/env python3
"""
统一测试运行器

运行所有单元测试并生成报告
"""

import sys
import unittest
from pathlib import Path
import time

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))


def run_all_tests(verbosity=2):
    """
    运行所有测试

    Args:
        verbosity: 详细程度 (0=静默, 1=正常, 2=详细)

    Returns:
        bool: 是否所有测试通过
    """
    print("="*80)
    print(" "*25 + "Core 项目测试套件")
    print("="*80)
    print()

    # 测试模块列表
    test_modules = [
        'test_data_loader',
        'test_feature_engineer',
        'test_data_cleaner',
        'test_data_splitter',
        'test_feature_cache',
        'test_database_manager_refactored',
        'test_performance_iterrows',
        'test_performance_sample_balancing',
    ]

    # 测试结果统计
    total_tests = 0
    total_failures = 0
    total_errors = 0
    total_skipped = 0
    module_results = []

    start_time = time.time()

    # 逐个运行测试模块
    for module_name in test_modules:
        print(f"\n{'='*80}")
        print(f"运行模块: {module_name}")
        print(f"{'='*80}")

        try:
            # 导入测试模块
            module = __import__(module_name)

            # 创建测试套件
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromModule(module)

            # 运行测试
            runner = unittest.TextTestRunner(verbosity=verbosity)
            result = runner.run(suite)

            # 收集统计信息
            total_tests += result.testsRun
            total_failures += len(result.failures)
            total_errors += len(result.errors)
            total_skipped += len(result.skipped)

            # 记录模块结果
            module_results.append({
                'module': module_name,
                'tests': result.testsRun,
                'failures': len(result.failures),
                'errors': len(result.errors),
                'skipped': len(result.skipped),
                'success': result.wasSuccessful()
            })

        except Exception as e:
            print(f"✗ 运行 {module_name} 失败: {e}")
            module_results.append({
                'module': module_name,
                'tests': 0,
                'failures': 0,
                'errors': 1,
                'skipped': 0,
                'success': False
            })

    elapsed_time = time.time() - start_time

    # 打印总结报告
    print("\n" + "="*80)
    print(" "*30 + "测试总结报告")
    print("="*80)

    # 模块级统计
    print("\n模块级别测试结果:")
    print(f"{'模块名称':<30} {'测试数':>8} {'成功':>8} {'失败':>8} {'错误':>8} {'跳过':>8}")
    print("-" * 80)

    for result in module_results:
        status = "✓" if result['success'] else "✗"
        success_count = result['tests'] - result['failures'] - result['errors'] - result['skipped']
        print(f"{status} {result['module']:<28} {result['tests']:>8} {success_count:>8} "
              f"{result['failures']:>8} {result['errors']:>8} {result['skipped']:>8}")

    # 整体统计
    print("-" * 80)
    total_success = total_tests - total_failures - total_errors - total_skipped
    success_rate = (total_success / total_tests * 100) if total_tests > 0 else 0

    print(f"{'总计':<30} {total_tests:>8} {total_success:>8} "
          f"{total_failures:>8} {total_errors:>8} {total_skipped:>8}")

    print("\n" + "="*80)
    print(f"测试总数: {total_tests}")
    print(f"成功: {total_success} ({success_rate:.1f}%)")
    print(f"失败: {total_failures}")
    print(f"错误: {total_errors}")
    print(f"跳过: {total_skipped}")
    print(f"总耗时: {elapsed_time:.2f}秒")
    print("="*80)

    # 最终结果
    all_passed = (total_failures == 0 and total_errors == 0)

    if all_passed:
        print("\n✓ 所有测试通过!")
    else:
        print(f"\n✗ 有 {total_failures + total_errors} 个测试失败")

    return all_passed


def run_specific_test(test_module_name, verbosity=2):
    """
    运行特定的测试模块

    Args:
        test_module_name: 测试模块名称
        verbosity: 详细程度

    Returns:
        bool: 是否测试通过
    """
    print(f"\n{'='*80}")
    print(f"运行测试: {test_module_name}")
    print(f"{'='*80}\n")

    try:
        module = __import__(test_module_name)
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(module)
        runner = unittest.TextTestRunner(verbosity=verbosity)
        result = runner.run(suite)

        return result.wasSuccessful()

    except Exception as e:
        print(f"✗ 运行测试失败: {e}")
        return False


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Core 项目测试运行器')
    parser.add_argument(
        '--module', '-m',
        help='运行特定测试模块 (例如: test_data_loader)',
        default=None
    )
    parser.add_argument(
        '--verbosity', '-v',
        help='详细程度 (0=静默, 1=正常, 2=详细)',
        type=int,
        choices=[0, 1, 2],
        default=2
    )

    args = parser.parse_args()

    if args.module:
        # 运行特定模块
        success = run_specific_test(args.module, verbosity=args.verbosity)
    else:
        # 运行所有测试
        success = run_all_tests(verbosity=args.verbosity)

    sys.exit(0 if success else 1)
