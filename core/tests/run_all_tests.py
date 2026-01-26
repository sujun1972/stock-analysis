#!/usr/bin/env python3
"""
统一测试运行器

运行所有单元测试、集成测试和性能测试并生成报告。

目录结构：
- unit/: 单元测试（组件级测试）
- integration/: 集成测试（端到端测试）
- performance/: 性能测试（性能基准测试）
"""

import sys
import unittest
from pathlib import Path
import time

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))


def discover_tests(test_dir, pattern='test_*.py'):
    """
    自动发现测试文件

    Args:
        test_dir: 测试目录路径
        pattern: 测试文件匹配模式

    Returns:
        list: 测试模块名称列表
    """
    test_path = Path(__file__).parent / test_dir
    if not test_path.exists():
        return []

    test_modules = []
    for test_file in test_path.glob(pattern):
        if test_file.name != '__init__.py':
            module_name = f"{test_dir}.{test_file.stem}"
            test_modules.append(module_name)

    return sorted(test_modules)


def run_all_tests(test_type='all', verbosity=2):
    """
    运行所有测试

    Args:
        test_type: 测试类型 ('all', 'unit', 'integration', 'performance')
        verbosity: 详细程度 (0=静默, 1=正常, 2=详细)

    Returns:
        bool: 是否所有测试通过
    """
    print("="*80)
    print(" "*25 + "Core 项目测试套件")
    print("="*80)
    print()

    # 根据类型选择测试目录
    test_dirs = {
        'unit': ['unit'],
        'integration': ['integration'],
        'performance': ['performance'],
        'all': ['unit', 'integration', 'performance']
    }

    dirs_to_test = test_dirs.get(test_type, ['unit', 'integration', 'performance'])

    # 发现所有测试模块
    all_test_modules = []
    for test_dir in dirs_to_test:
        modules = discover_tests(test_dir)
        all_test_modules.extend(modules)

    if not all_test_modules:
        print("⚠️  未发现任何测试文件")
        return True

    print(f"发现 {len(all_test_modules)} 个测试模块:")
    for module in all_test_modules:
        print(f"  - {module}")
    print()

    # 测试结果统计
    total_tests = 0
    total_failures = 0
    total_errors = 0
    total_skipped = 0
    module_results = []

    start_time = time.time()

    # 逐个运行测试模块
    for module_name in all_test_modules:
        print(f"\n{'='*80}")
        print(f"运行模块: {module_name}")
        print(f"{'='*80}")

        try:
            # 导入测试模块
            module = __import__(module_name, fromlist=[''])

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
            import traceback
            traceback.print_exc()
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
    print(f"{'模块名称':<40} {'测试数':>8} {'成功':>8} {'失败':>8} {'错误':>8} {'跳过':>8}")
    print("-" * 80)

    for result in module_results:
        status = "✓" if result['success'] else "✗"
        success_count = result['tests'] - result['failures'] - result['errors'] - result['skipped']
        print(f"{status} {result['module']:<38} {result['tests']:>8} {success_count:>8} "
              f"{result['failures']:>8} {result['errors']:>8} {result['skipped']:>8}")

    # 整体统计
    print("-" * 80)
    total_success = total_tests - total_failures - total_errors - total_skipped
    success_rate = (total_success / total_tests * 100) if total_tests > 0 else 0

    print(f"{'总计':<40} {total_tests:>8} {total_success:>8} "
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
        test_module_name: 测试模块名称（可含目录前缀，如 unit.test_data_loader）
        verbosity: 详细程度

    Returns:
        bool: 是否测试通过
    """
    print(f"\n{'='*80}")
    print(f"运行测试: {test_module_name}")
    print(f"{'='*80}\n")

    try:
        module = __import__(test_module_name, fromlist=[''])
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(module)
        runner = unittest.TextTestRunner(verbosity=verbosity)
        result = runner.run(suite)

        return result.wasSuccessful()

    except Exception as e:
        print(f"✗ 运行测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Core 项目测试运行器')
    parser.add_argument(
        '--module', '-m',
        help='运行特定测试模块 (例如: unit.test_data_loader)',
        default=None
    )
    parser.add_argument(
        '--type', '-t',
        help='测试类型 (all, unit, integration, performance)',
        choices=['all', 'unit', 'integration', 'performance'],
        default='all'
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
        success = run_all_tests(test_type=args.type, verbosity=args.verbosity)

    sys.exit(0 if success else 1)
