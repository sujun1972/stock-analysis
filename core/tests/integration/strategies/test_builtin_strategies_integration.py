"""
内置策略集成测试

测试从数据库加载内置策略并实际运行的完整流程
"""

import unittest
import pytest
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import numpy as np
import sys
from pathlib import Path


# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'stock_analysis',
    'user': 'stock_user',
    'password': 'stock_password_123'
}


@pytest.mark.integration
class TestBuiltinStrategiesIntegration(unittest.TestCase):
    """内置策略集成测试"""

    @classmethod
    def setUpClass(cls):
        """测试类级别的设置"""
        # 添加src到路径
        core_dir = Path(__file__).resolve().parent.parent.parent.parent
        sys.path.insert(0, str(core_dir / 'src'))
        sys.path.insert(0, str(core_dir))

    def setUp(self):
        """每个测试的设置"""
        # 连接数据库
        try:
            self.conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
            self.db_available = True
        except Exception as e:
            self.db_available = False
            self.skipTest(f"数据库不可用: {e}")

    def tearDown(self):
        """清理"""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

    def load_strategy_from_db(self, strategy_name: str):
        """从数据库加载策略"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM strategies WHERE name = %s AND source_type = 'builtin'",
            (strategy_name,)
        )
        return dict(cursor.fetchone()) if cursor.rowcount > 0 else None

    def instantiate_strategy(self, strategy_data):
        """动态实例化策略"""
        # 准备命名空间
        namespace = {
            '__name__': '__dynamic_strategy__',
            '__file__': '<dynamic>',
        }

        # 导入必要模块
        import pandas as pd
        import numpy as np
        from loguru import logger
        from strategies.base_strategy import BaseStrategy
        from strategies.signal_generator import SignalGenerator

        namespace.update({
            'pd': pd,
            'np': np,
            'logger': logger,
            'BaseStrategy': BaseStrategy,
            'SignalGenerator': SignalGenerator,
            'Optional': __import__('typing').Optional,
            'Dict': __import__('typing').Dict,
            'Any': __import__('typing').Any,
            'List': __import__('typing').List,
        })

        # 执行代码
        exec(strategy_data['code'], namespace)

        # 获取类并实例化
        strategy_class = namespace.get(strategy_data['class_name'])
        if not strategy_class:
            raise ValueError(f"类 {strategy_data['class_name']} 未找到")

        return strategy_class(
            name=f"test_{strategy_data['name']}",
            config=strategy_data['default_params'] or {}
        )

    def test_momentum_strategy_integration(self):
        """测试动量策略完整流程"""
        # 1. 从数据库加载
        strategy_data = self.load_strategy_from_db('momentum_builtin')
        self.assertIsNotNone(strategy_data, "动量策略未在数据库中找到")
        self.assertEqual(strategy_data['class_name'], 'MomentumStrategy')

        # 2. 实例化策略
        strategy = self.instantiate_strategy(strategy_data)
        self.assertEqual(strategy.__class__.__name__, 'MomentumStrategy')

        # 3. 准备测试数据
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        stocks = ['000001', '000002', '000003', '000004', '000005']
        prices = pd.DataFrame(
            np.random.uniform(10, 20, (100, 5)),
            index=dates,
            columns=stocks
        )

        # 4. 生成信号
        signals = strategy.generate_signals(prices)

        # 5. 验证结果
        self.assertIsInstance(signals, pd.DataFrame)
        self.assertEqual(signals.shape, prices.shape)
        self.assertTrue((signals.isin([0, 1])).all().all())

        # 6. 验证元数据
        metadata = strategy.get_metadata()
        self.assertEqual(metadata['category'], 'momentum')
        self.assertEqual(metadata['risk_level'], 'medium')

    def test_mean_reversion_strategy_integration(self):
        """测试均值回归策略完整流程"""
        # 1. 从数据库加载
        strategy_data = self.load_strategy_from_db('mean_reversion_builtin')
        self.assertIsNotNone(strategy_data, "均值回归策略未在数据库中找到")

        # 2. 实例化策略
        strategy = self.instantiate_strategy(strategy_data)
        self.assertEqual(strategy.__class__.__name__, 'MeanReversionStrategy')

        # 3. 准备震荡市场数据
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        stocks = ['000001', '000002', '000003']
        t = np.arange(100)
        price_data = {}
        for stock in stocks:
            # 震荡价格
            trend = 10 + 2 * np.sin(t * 2 * np.pi / 20)
            noise = np.random.normal(0, 0.5, 100)
            price_data[stock] = trend + noise

        prices = pd.DataFrame(price_data, index=dates)

        # 4. 生成信号
        signals = strategy.generate_signals(prices)

        # 5. 验证结果
        self.assertIsInstance(signals, pd.DataFrame)
        self.assertEqual(signals.shape, prices.shape)

        # 6. 验证元数据
        metadata = strategy.get_metadata()
        self.assertEqual(metadata['category'], 'reversal')

    def test_multi_factor_strategy_integration(self):
        """测试多因子策略完整流程"""
        # 1. 从数据库加载
        strategy_data = self.load_strategy_from_db('multi_factor_builtin')
        self.assertIsNotNone(strategy_data, "多因子策略未在数据库中找到")

        # 2. 实例化策略
        strategy = self.instantiate_strategy(strategy_data)
        self.assertEqual(strategy.__class__.__name__, 'MultiFactorStrategy')

        # 3. 准备测试数据
        dates = pd.date_range('2023-01-01', periods=50, freq='D')
        stocks = ['000001', '000002', '000003']

        # 价格数据
        prices = pd.DataFrame(
            np.random.uniform(10, 20, (50, 3)),
            index=dates,
            columns=stocks
        )

        # 特征数据 (简化版)
        # 实际应该使用完整的特征计算,这里只是测试
        features_list = []
        for stock in stocks:
            df = pd.DataFrame({
                'MOM20': prices[stock].pct_change(20) * 100,
                'REV5': -prices[stock].pct_change(5) * 100,
                'VOLATILITY20': prices[stock].pct_change().rolling(20).std() * 100,
            }, index=dates)
            df['stock'] = stock
            features_list.append(df)

        all_features = pd.concat(features_list)

        # 转换为策略需要的格式
        features_df = pd.DataFrame()
        for stock in stocks:
            stock_features = all_features[all_features['stock'] == stock]
            for factor in ['MOM20', 'REV5', 'VOLATILITY20']:
                features_df[f'{factor}_{stock}'] = stock_features[factor].values

        features_df.index = dates

        # 4. 验证因子权重
        factor_weights = strategy.get_factor_weights()
        self.assertEqual(len(factor_weights), 3)
        self.assertIn('MOM20', factor_weights)

        # 5. 验证元数据
        metadata = strategy.get_metadata()
        self.assertEqual(metadata['category'], 'factor')
        self.assertEqual(metadata['risk_level'], 'low')

    def test_all_builtin_strategies_exist(self):
        """测试所有内置策略都存在于数据库中"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT name, display_name FROM strategies WHERE source_type = 'builtin' ORDER BY id"
        )
        strategies = cursor.fetchall()

        # 应该有3个内置策略
        self.assertGreaterEqual(len(strategies), 3)

        strategy_names = [s['name'] for s in strategies]
        self.assertIn('momentum_builtin', strategy_names)
        self.assertIn('mean_reversion_builtin', strategy_names)
        self.assertIn('multi_factor_builtin', strategy_names)

    def test_strategy_code_integrity(self):
        """测试策略代码完整性(哈希验证)"""
        import hashlib

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT code, code_hash FROM strategies WHERE source_type = 'builtin'"
        )
        strategies = cursor.fetchall()

        for strategy in strategies:
            # 计算实际哈希
            actual_hash = hashlib.sha256(strategy['code'].encode('utf-8')).hexdigest()

            # 验证与存储的哈希匹配
            self.assertEqual(
                actual_hash,
                strategy['code_hash'],
                f"策略代码哈希不匹配"
            )

    def test_strategy_validation_status(self):
        """测试策略验证状态"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT name, validation_status, is_enabled FROM strategies WHERE source_type = 'builtin'"
        )
        strategies = cursor.fetchall()

        for strategy in strategies:
            # 所有内置策略应该是已验证和已启用的
            self.assertEqual(strategy['validation_status'], 'passed')
            self.assertTrue(strategy['is_enabled'])

    def test_strategy_metadata_completeness(self):
        """测试策略元数据完整性"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM strategies WHERE source_type = 'builtin'"
        )
        strategies = cursor.fetchall()

        for strategy in strategies:
            # 验证必需字段存在
            self.assertIsNotNone(strategy['name'])
            self.assertIsNotNone(strategy['display_name'])
            self.assertIsNotNone(strategy['class_name'])
            self.assertIsNotNone(strategy['code'])
            self.assertIsNotNone(strategy['category'])
            self.assertIsNotNone(strategy['description'])
            self.assertIsNotNone(strategy['default_params'])

            # 验证数组字段
            self.assertIsInstance(strategy['tags'], list)
            self.assertGreater(len(strategy['tags']), 0)


@pytest.mark.integration
class TestStrategyPerformance(unittest.TestCase):
    """策略性能测试"""

    @classmethod
    def setUpClass(cls):
        """测试类级别的设置"""
        core_dir = Path(__file__).resolve().parent.parent.parent.parent
        sys.path.insert(0, str(core_dir / 'src'))
        sys.path.insert(0, str(core_dir))

    def setUp(self):
        """设置"""
        try:
            self.conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
            self.db_available = True
        except Exception:
            self.db_available = False
            self.skipTest("数据库不可用")

    def tearDown(self):
        """清理"""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

    def test_strategy_loading_performance(self):
        """测试策略加载性能"""
        import time

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM strategies WHERE source_type = 'builtin' LIMIT 1"
        )
        strategy_data = dict(cursor.fetchone())

        # 测试加载时间
        start_time = time.time()

        # 准备命名空间并执行代码
        namespace = {
            '__name__': '__dynamic_strategy__',
        }

        import pandas as pd
        import numpy as np
        from strategies.base_strategy import BaseStrategy
        from strategies.signal_generator import SignalGenerator

        namespace.update({
            'pd': pd,
            'np': np,
            'BaseStrategy': BaseStrategy,
            'SignalGenerator': SignalGenerator,
            'Optional': __import__('typing').Optional,
            'Dict': __import__('typing').Dict,
            'Any': __import__('typing').Any,
        })

        exec(strategy_data['code'], namespace)
        strategy_class = namespace[strategy_data['class_name']]
        strategy = strategy_class(name='perf_test', config={})

        end_time = time.time()
        loading_time = end_time - start_time

        # 加载时间应该小于1秒
        self.assertLess(loading_time, 1.0, f"策略加载时间过长: {loading_time:.3f}s")


if __name__ == '__main__':
    unittest.main()
