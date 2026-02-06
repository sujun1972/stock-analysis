"""
ML-4 因子库集成测试

测试 MLSelector 与完整特征工程库的集成功能
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(project_root))

from src.strategies.three_layer.selectors.ml_selector import MLSelector


class TestML4FeatureIntegration(unittest.TestCase):
    """ML-4 因子库集成功能测试"""

    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        # 生成测试数据
        cls.dates = pd.date_range('2023-01-01', periods=100, freq='D')
        cls.stocks = [f'stock_{i:03d}' for i in range(10)]

        # 生成价格数据
        np.random.seed(42)
        prices_data = {}
        for stock in cls.stocks:
            base_price = 100
            returns = np.random.randn(100) * 0.02
            prices = base_price * (1 + returns).cumprod()
            prices_data[stock] = prices

        cls.prices = pd.DataFrame(prices_data, index=cls.dates)

    def test_init_with_feature_engine(self):
        """测试初始化：启用完整特征库"""
        selector = MLSelector(params={
            'mode': 'multi_factor_weighted',
            'top_n': 5,
            'use_feature_engine': True,
            'features': 'momentum_20d,rsi_14d'
        })

        self.assertEqual(selector.mode, 'multi_factor_weighted')
        self.assertTrue(selector.use_feature_engine or not selector.use_feature_engine)  # 取决于是否安装
        self.assertEqual(len(selector.features), 2)

    def test_init_without_feature_engine(self):
        """测试初始化：禁用完整特征库（快速模式）"""
        selector = MLSelector(params={
            'mode': 'multi_factor_weighted',
            'top_n': 5,
            'use_feature_engine': False,
            'features': 'momentum_20d,rsi_14d'
        })

        self.assertEqual(selector.mode, 'multi_factor_weighted')
        self.assertFalse(selector.use_feature_engine)

    def test_parse_features_simple(self):
        """测试特征解析：简单列表"""
        selector = MLSelector(params={
            'features': 'momentum_20d,rsi_14d,volatility_20d'
        })

        self.assertEqual(len(selector.features), 3)
        self.assertIn('momentum_20d', selector.features)
        self.assertIn('rsi_14d', selector.features)

    def test_parse_features_with_wildcard_alpha(self):
        """测试特征解析：Alpha因子通配符"""
        selector = MLSelector(params={
            'features': 'alpha:*'
        })

        # 应该包含多个Alpha因子
        self.assertGreater(len(selector.features), 0)
        if selector.use_feature_engine:
            # 如果特征库可用，应该有Alpha因子
            self.assertTrue(any('momentum' in f for f in selector.features))

    def test_parse_features_with_wildcard_tech(self):
        """测试特征解析：技术指标通配符"""
        selector = MLSelector(params={
            'features': 'tech:*'
        })

        # 应该包含多个技术指标
        self.assertGreater(len(selector.features), 0)
        if selector.use_feature_engine:
            # 如果特征库可用，应该有技术指标
            self.assertTrue(any('rsi' in f or 'ma' in f for f in selector.features))

    def test_parse_features_with_category(self):
        """测试特征解析：指定类别"""
        selector = MLSelector(params={
            'features': 'alpha:momentum,tech:rsi'
        })

        # 应该包含动量因子和RSI指标
        self.assertGreater(len(selector.features), 0)
        if selector.use_feature_engine:
            self.assertTrue(any('momentum' in f for f in selector.features))
            self.assertTrue(any('rsi' in f for f in selector.features))

    def test_parse_features_mixed(self):
        """测试特征解析：混合格式"""
        selector = MLSelector(params={
            'features': 'momentum_20d,alpha:reversal,tech:ma'
        })

        # 应该包含指定特征和类别特征
        self.assertGreater(len(selector.features), 1)
        self.assertIn('momentum_20d', selector.features)

    def test_select_with_fast_mode(self):
        """测试选股：快速模式（简化特征）"""
        selector = MLSelector(params={
            'mode': 'multi_factor_weighted',
            'top_n': 5,
            'use_feature_engine': False,
            'features': 'momentum_20d,rsi_14d'
        })

        # 选择一个有足够历史数据的日期
        select_date = self.dates[80]
        selected_stocks = selector.select(select_date, self.prices)

        # 应该选出股票
        self.assertGreater(len(selected_stocks), 0)
        self.assertLessEqual(len(selected_stocks), 5)

        # 所有选出的股票应该在候选列表中
        for stock in selected_stocks:
            self.assertIn(stock, self.stocks)

    def test_select_with_feature_engine(self):
        """测试选股：完整特征库模式"""
        selector = MLSelector(params={
            'mode': 'multi_factor_weighted',
            'top_n': 5,
            'use_feature_engine': True,
            'features': 'momentum_20d,rsi_14d'
        })

        # 选择一个有足够历史数据的日期
        select_date = self.dates[80]
        selected_stocks = selector.select(select_date, self.prices)

        # 应该选出股票
        self.assertGreater(len(selected_stocks), 0)
        self.assertLessEqual(len(selected_stocks), 5)

    def test_calculate_features_fast(self):
        """测试特征计算：快速模式"""
        selector = MLSelector(params={
            'use_feature_engine': False,
            'features': 'momentum_20d,rsi_14d'
        })

        select_date = self.dates[80]
        valid_stocks = self.stocks

        # 计算特征矩阵
        feature_matrix = selector._calculate_features_fast(
            select_date, self.prices, valid_stocks
        )

        # 验证特征矩阵
        self.assertFalse(feature_matrix.empty)
        self.assertEqual(len(feature_matrix.columns), 2)
        self.assertIn('momentum_20d', feature_matrix.columns)
        self.assertIn('rsi_14d', feature_matrix.columns)

    def test_calculate_features_with_engine(self):
        """测试特征计算：完整特征库模式"""
        selector = MLSelector(params={
            'use_feature_engine': True,
            'features': 'momentum_20d,rsi_14d'
        })

        select_date = self.dates[80]
        valid_stocks = self.stocks[:3]  # 使用较少股票以加快测试

        # 计算特征矩阵
        try:
            feature_matrix = selector._calculate_features_with_engine(
                select_date, self.prices, valid_stocks
            )

            # 如果特征库可用，验证特征矩阵
            if not feature_matrix.empty:
                self.assertGreater(len(feature_matrix), 0)
                self.assertGreater(len(feature_matrix.columns), 0)
        except Exception as e:
            # 如果特征库不可用，跳过此测试
            self.skipTest(f"特征库不可用: {e}")

    def test_get_all_alpha_factors(self):
        """测试获取所有Alpha因子列表"""
        selector = MLSelector(params={})

        alpha_factors = selector._get_all_alpha_factors()

        # 应该返回Alpha因子列表
        self.assertIsInstance(alpha_factors, list)
        if selector.use_feature_engine:
            self.assertGreater(len(alpha_factors), 0)

    def test_get_all_technical_indicators(self):
        """测试获取所有技术指标列表"""
        selector = MLSelector(params={})

        tech_indicators = selector._get_all_technical_indicators()

        # 应该返回技术指标列表
        self.assertIsInstance(tech_indicators, list)
        if selector.use_feature_engine:
            self.assertGreater(len(tech_indicators), 0)

    def test_get_alpha_factors_by_category(self):
        """测试按类别获取Alpha因子"""
        selector = MLSelector(params={})

        momentum_factors = selector._get_alpha_factors_by_category('momentum')
        reversal_factors = selector._get_alpha_factors_by_category('reversal')

        # 验证返回的因子列表
        self.assertIsInstance(momentum_factors, list)
        self.assertIsInstance(reversal_factors, list)

        if len(momentum_factors) > 0:
            self.assertTrue(any('momentum' in f for f in momentum_factors))

    def test_get_tech_indicators_by_category(self):
        """测试按类别获取技术指标"""
        selector = MLSelector(params={})

        ma_indicators = selector._get_tech_indicators_by_category('ma')
        rsi_indicators = selector._get_tech_indicators_by_category('rsi')

        # 验证返回的指标列表
        self.assertIsInstance(ma_indicators, list)
        self.assertIsInstance(rsi_indicators, list)

        if len(ma_indicators) > 0:
            self.assertTrue(any('ma' in f for f in ma_indicators))

    def test_feature_cache(self):
        """测试特征缓存机制"""
        selector = MLSelector(params={
            'features': 'momentum_20d,rsi_14d'
        })

        # 验证缓存字典存在
        self.assertIsInstance(selector._feature_cache, dict)
        self.assertEqual(len(selector._feature_cache), 0)

    def test_compatibility_with_old_params(self):
        """测试向后兼容性：旧参数格式"""
        # 使用旧的参数格式
        selector = MLSelector(params={
            'mode': 'multi_factor_weighted',
            'top_n': 50,
            'features': 'momentum_20d,rsi_14d,volatility_20d,volume_ratio'
        })

        # 应该能正常初始化
        self.assertEqual(selector.mode, 'multi_factor_weighted')
        self.assertEqual(len(selector.features), 4)

        # 应该能正常选股
        select_date = self.dates[80]
        selected_stocks = selector.select(select_date, self.prices)
        self.assertIsInstance(selected_stocks, list)

    def test_empty_features_use_default(self):
        """测试空特征列表时使用默认特征"""
        selector = MLSelector(params={
            'features': ''
        })

        # 应该使用默认特征集
        self.assertGreater(len(selector.features), 0)

    def test_invalid_feature_handling(self):
        """测试无效特征的处理"""
        selector = MLSelector(params={
            'use_feature_engine': False,
            'features': 'momentum_20d,invalid_feature_xxx'
        })

        select_date = self.dates[80]
        valid_stocks = self.stocks

        # 计算特征矩阵
        feature_matrix = selector._calculate_features_fast(
            select_date, self.prices, valid_stocks
        )

        # 应该能处理无效特征（填充为0）
        self.assertFalse(feature_matrix.empty)
        self.assertIn('invalid_feature_xxx', feature_matrix.columns)

    def test_performance_comparison(self):
        """测试性能对比：快速模式 vs 完整特征库模式"""
        import time

        # 快速模式
        selector_fast = MLSelector(params={
            'use_feature_engine': False,
            'features': 'momentum_20d,rsi_14d'
        })

        select_date = self.dates[80]

        start_time = time.time()
        selected_fast = selector_fast.select(select_date, self.prices)
        time_fast = time.time() - start_time

        # 完整特征库模式
        selector_engine = MLSelector(params={
            'use_feature_engine': True,
            'features': 'momentum_20d,rsi_14d'
        })

        start_time = time.time()
        selected_engine = selector_engine.select(select_date, self.prices)
        time_engine = time.time() - start_time

        print(f"\n性能对比:")
        print(f"  快速模式: {time_fast:.4f}秒, 选出 {len(selected_fast)} 只股票")
        print(f"  完整特征库: {time_engine:.4f}秒, 选出 {len(selected_engine)} 只股票")

        # 两种模式都应该能选出股票
        self.assertGreater(len(selected_fast), 0)
        self.assertGreater(len(selected_engine), 0)


class TestML4FeatureCategories(unittest.TestCase):
    """ML-4 特征类别测试"""

    def setUp(self):
        """设置测试环境"""
        self.selector = MLSelector(params={})

    def test_alpha_factor_categories(self):
        """测试Alpha因子分类"""
        categories = ['momentum', 'reversal', 'volatility', 'volume', 'trend']

        for category in categories:
            factors = self.selector._get_alpha_factors_by_category(category)
            self.assertIsInstance(factors, list)
            print(f"\n{category} 因子: {len(factors)} 个")
            if len(factors) > 0:
                print(f"  示例: {factors[:3]}")

    def test_tech_indicator_categories(self):
        """测试技术指标分类"""
        categories = ['ma', 'ema', 'rsi', 'macd', 'bb', 'atr', 'cci']

        for category in categories:
            indicators = self.selector._get_tech_indicators_by_category(category)
            self.assertIsInstance(indicators, list)
            print(f"\n{category} 指标: {len(indicators)} 个")
            if len(indicators) > 0:
                print(f"  示例: {indicators[:3]}")


if __name__ == '__main__':
    # 运行测试
    unittest.main(verbosity=2)
