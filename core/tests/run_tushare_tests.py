#!/usr/bin/env python3
"""
TushareProvider 测试运行脚本

运行所有 Tushare 相关的测试（单元测试 + 集成测试）
"""

import sys
import os
import unittest
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'core' / 'src'))


def run_unit_tests():
    """运行单元测试"""
    print("\n" + "="*80)
    print("运行 TushareProvider 单元测试")
    print("="*80)

    # 导入单元测试模块
    from unit.providers.tushare.test_api_client import TestTushareAPIClient
    from unit.providers.tushare.test_data_converter import TestTushareDataConverter
    from unit.providers.tushare.test_provider import TestTushareProvider

    # 创建测试套件
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestTushareAPIClient))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestTushareDataConverter))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestTushareProvider))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


def run_integration_tests():
    """运行集成测试"""
    print("\n" + "="*80)
    print("运行 TushareProvider 集成测试")
    print("="*80)

    # 检查是否设置了 Token
    if not os.getenv('TUSHARE_TOKEN'):
        print("\n警告: 未设置 TUSHARE_TOKEN 环境变量")
        print("跳过集成测试...")
        print("\n如需运行集成测试，请设置环境变量:")
        print("  export TUSHARE_TOKEN=your_token_here")
        return True

    # 导入集成测试模块
    from integration.providers.test_tushare_provider import TestTushareProviderIntegration

    # 创建测试套件
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestTushareProviderIntegration))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


def main():
    """主函数"""
    print("\n" + "="*80)
    print("TushareProvider 完整测试套件")
    print("="*80)

    # 运行单元测试
    unit_success = run_unit_tests()

    # 运行集成测试
    integration_success = run_integration_tests()

    # 打印总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)
    print(f"单元测试: {'✓ 通过' if unit_success else '✗ 失败'}")
    print(f"集成测试: {'✓ 通过' if integration_success else '✗ 失败'}")

    if unit_success and integration_success:
        print("\n🎉 所有测试通过!")
        return 0
    else:
        print("\n❌ 部分测试失败，请检查上面的错误信息")
        return 1


if __name__ == '__main__':
    sys.exit(main())
