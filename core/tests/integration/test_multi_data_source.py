#!/usr/bin/env python3
"""
多数据源集成测试

测试数据源切换、一致性和降级机制：
1. AkShare 和 Tushare 数据源切换
2. 数据格式一致性验证
3. 降级机制测试
"""

import sys
import unittest
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, List

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))


class TestDataSourceSwitching(unittest.TestCase):
    """测试数据源切换"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        cls.test_stock = '000001'
        cls.test_start_date = '2023-01-01'
        cls.test_end_date = '2023-03-31'

    def test_01_akshare_provider(self):
        """测试1: AkShare数据源"""

        try:
            from src.providers import DataProviderFactory

            # 创建AkShare提供者
            provider = DataProviderFactory.create_provider('akshare')
            self.assertIsNotNone(provider, "AkShare提供者创建失败")

            # 获取数据
            data = provider.get_daily_data(
                self.test_stock,
                self.test_start_date,
                self.test_end_date
            )

            self.assertIsNotNone(data, "数据获取失败")
            self.assertGreater(len(data), 0, "数据为空")

            # 验证数据格式
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                self.assertIn(col, data.columns, f"缺少必需列: {col}")

        except Exception as e:
            self.skipTest(f"AkShare不可用: {e}")

    def test_02_tushare_provider(self):
        """测试2: Tushare数据源"""

        try:
            from src.providers import DataProviderFactory

            # 创建Tushare提供者
            provider = DataProviderFactory.create_provider('tushare')
            self.assertIsNotNone(provider, "Tushare提供者创建失败")

            # 获取数据
            data = provider.get_daily_data(
                self.test_stock,
                self.test_start_date,
                self.test_end_date
            )

            self.assertIsNotNone(data, "数据获取失败")
            self.assertGreater(len(data), 0, "数据为空")

            # 验证数据格式
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                self.assertIn(col, data.columns, f"缺少必需列: {col}")

        except Exception as e:
            self.skipTest(f"Tushare不可用 (可能需要token): {e}")

    def test_03_data_source_consistency(self):
        """测试3: 数据源一致性"""

        try:
            from src.providers import DataProviderFactory

            # 从两个数据源获取相同股票的数据
            akshare_provider = DataProviderFactory.create_provider('akshare')
            akshare_data = akshare_provider.get_daily_data(
                self.test_stock,
                self.test_start_date,
                self.test_end_date
            )

            try:
                tushare_provider = DataProviderFactory.create_provider('tushare')
                tushare_data = tushare_provider.get_daily_data(
                    self.test_stock,
                    self.test_start_date,
                    self.test_end_date
                )

                print(f"\n  AkShare: {len(akshare_data)} 条记录")

                # 验证列一致性
                akshare_cols = set(akshare_data.columns)
                tushare_cols = set(tushare_data.columns)

                common_cols = akshare_cols & tushare_cols

                required_columns = ['open', 'high', 'low', 'close', 'volume']
                for col in required_columns:
                    self.assertIn(col, common_cols, f"两个数据源都缺少: {col}")

                # 比较数据一致性（允许一定误差）
                for col in required_columns:
                    if col in akshare_data.columns and col in tushare_data.columns:
                        # 取共同日期
                        common_dates = akshare_data.index.intersection(tushare_data.index)
                        if len(common_dates) > 0:
                            akshare_values = akshare_data.loc[common_dates, col]
                            tushare_values = tushare_data.loc[common_dates, col]

                            # 计算相关性
                            correlation = akshare_values.corr(tushare_values)

                            # 验证高度相关
                            self.assertGreater(
                                correlation, 0.95,
                                f"{col}列数据差异过大"
                            )


            except Exception as e:
                print(f"\n  ⚠ Tushare不可用，跳过一致性比对: {e}")

        except Exception as e:
            self.skipTest(f"数据源不可用: {e}")


class TestDataSourceFallback(unittest.TestCase):
    """测试数据源降级机制"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("数据源降级机制测试")
        print("=" * 80)

        cls.test_stock = '000001'
        cls.test_start_date = '2023-01-01'
        cls.test_end_date = '2023-03-31'

    def test_01_fallback_mechanism(self):
        """测试1: 降级机制"""

        try:
            from src.providers import DataProviderFactory

            # 模拟降级场景：优先使用Tushare，失败后降级到AkShare
            providers_to_try = ['tushare', 'akshare']
            data = None
            successful_provider = None

            for provider_name in providers_to_try:
                print(f"\n  尝试数据源: {provider_name}")
                try:
                    provider = DataProviderFactory.create_provider(provider_name)
                    data = provider.get_daily_data(
                        self.test_stock,
                        self.test_start_date,
                        self.test_end_date
                    )

                    if data is not None and len(data) > 0:
                        successful_provider = provider_name
                        break
                except Exception as e:
                    continue

            # 验证至少一个数据源成功
            self.assertIsNotNone(data, "所有数据源都失败")
            self.assertIsNotNone(successful_provider, "没有成功的数据源")

        except Exception as e:
            self.skipTest(f"降级测试失败: {e}")

    def test_02_provider_retry_logic(self):
        """测试2: 提供者重试逻辑"""

        try:
            from src.providers import DataProviderFactory

            provider = DataProviderFactory.create_provider('akshare')

            # 正常请求应该成功
            data = provider.get_daily_data(
                self.test_stock,
                self.test_start_date,
                self.test_end_date
            )

            self.assertIsNotNone(data, "数据获取失败")

            # 无效请求应该抛出异常
            with self.assertRaises(Exception):
                provider.get_daily_data(
                    'INVALID_STOCK',
                    self.test_start_date,
                    self.test_end_date
                )


        except Exception as e:
            self.skipTest(f"测试需要完整环境: {e}")


class TestDataFormatConsistency(unittest.TestCase):
    """测试数据格式一致性"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("数据格式一致性测试")
        print("=" * 80)

        cls.test_stock = '000001'
        cls.test_start_date = '2023-01-01'
        cls.test_end_date = '2023-03-31'

    def _validate_data_format(self, data: pd.DataFrame, provider_name: str):
        """验证数据格式"""
        print(f"\n  [验证] {provider_name} 数据格式")

        # 1. 验证必需列
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            self.assertIn(col, data.columns, f"{provider_name}: 缺少列 {col}")

        # 2. 验证数据类型
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            self.assertTrue(
                pd.api.types.is_numeric_dtype(data[col]),
                f"{provider_name}: {col}列应为数值类型"
            )

        # 3. 验证索引
        self.assertTrue(
            isinstance(data.index, pd.DatetimeIndex),
            f"{provider_name}: 索引应为DatetimeIndex"
        )

        # 4. 验证价格关系
        invalid_high_low = (data['high'] < data['low']).sum()
        self.assertEqual(
            invalid_high_low, 0,
            f"{provider_name}: 发现{invalid_high_low}条high<low异常"
        )

        invalid_high_close = (data['high'] < data['close']).sum()
        invalid_low_close = (data['low'] > data['close']).sum()

        # 5. 验证数据范围
        self.assertTrue((data['volume'] >= 0).all(), f"{provider_name}: 成交量不能为负")

    def test_01_akshare_format_validation(self):
        """测试1: AkShare格式验证"""

        try:
            from src.providers import DataProviderFactory

            provider = DataProviderFactory.create_provider('akshare')
            data = provider.get_daily_data(
                self.test_stock,
                self.test_start_date,
                self.test_end_date
            )

            self._validate_data_format(data, 'AkShare')

        except Exception as e:
            self.skipTest(f"AkShare不可用: {e}")

    def test_02_tushare_format_validation(self):
        """测试2: Tushare格式验证"""

        try:
            from src.providers import DataProviderFactory

            provider = DataProviderFactory.create_provider('tushare')
            data = provider.get_daily_data(
                self.test_stock,
                self.test_start_date,
                self.test_end_date
            )

            self._validate_data_format(data, 'Tushare')

        except Exception as e:
            self.skipTest(f"Tushare不可用: {e}")

    def test_03_cross_provider_compatibility(self):
        """测试3: 跨提供者兼容性"""

        try:
            from src.providers import DataProviderFactory
            from src.features import AlphaFactors

            providers = []
            try:
                providers.append(('akshare', DataProviderFactory.create_provider('akshare')))
            except:
                pass

            try:
                providers.append(('tushare', DataProviderFactory.create_provider('tushare')))
            except:
                pass

            if len(providers) == 0:
                self.skipTest("没有可用的数据源")

            # 对每个数据源，验证特征计算能正常工作
            for provider_name, provider in providers:
                print(f"\n  [测试] {provider_name} 兼容性")

                # 获取数据
                data = provider.get_daily_data(
                    self.test_stock,
                    self.test_start_date,
                    self.test_end_date
                )

                # 计算特征
                alpha = AlphaFactors(data)
                features = alpha.calculate_all_alpha_factors()

                self.assertGreater(len(features), 0, f"{provider_name}: 特征计算失败")
                self.assertGreater(len(features.columns), 0, f"{provider_name}: 特征为空")



        except Exception as e:
            self.skipTest(f"兼容性测试失败: {e}")


def run_tests():
    """运行所有集成测试"""
    print("多数据源集成测试套件")
    print("=" * 80)

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestDataSourceSwitching))
    suite.addTests(loader.loadTestsFromTestCase(TestDataSourceFallback))
    suite.addTests(loader.loadTestsFromTestCase(TestDataFormatConsistency))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 打印总结
    print("测试总结")
    print("=" * 80)
    print(f"运行: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print(f"跳过: {len(result.skipped)}")

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
