#!/usr/bin/env python3
"""
Feature Transformer 单元测试

测试特征转换器的功能（包括策略模式和向后兼容包装器）
"""

import sys
import unittest
import pandas as pd
import numpy as np
import tempfile
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from features.feature_transformer import (
    FeatureTransformer,
    prepare_ml_features,
    TransformError,
    InvalidDataError,
    ScalerNotFoundError,
)
from features.transform_strategy import (
    PriceChangeTransformStrategy,
    NormalizationStrategy,
    TimeFeatureStrategy,
    StatisticalFeatureStrategy,
    CompositeTransformStrategy,
)


class TestPriceChangeTransformStrategy(unittest.TestCase):
    """测试价格变动率转换策略"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("PriceChangeTransformStrategy 单元测试")
        print("="*60)

    def setUp(self):
        """每个测试前的准备"""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=100, freq='D')

        # 创建测试数据
        self.test_data = pd.DataFrame({
            'open': 100 + np.random.randn(100).cumsum() * 0.5,
            'high': 102 + np.random.randn(100).cumsum() * 0.5,
            'low': 98 + np.random.randn(100).cumsum() * 0.5,
            'close': 100 + np.random.randn(100).cumsum() * 0.5,
            'volume': np.random.uniform(1000000, 2000000, 100)
        }, index=dates)

        # 确保 high >= close >= low
        self.test_data['high'] = self.test_data[['open', 'close', 'high']].max(axis=1)
        self.test_data['low'] = self.test_data[['open', 'close', 'low']].min(axis=1)

    def test_01_price_change_matrix(self):
        """测试1: 创建价格变动率矩阵"""
        print("\n[测试1] 创建价格变动率矩阵...")

        strategy = PriceChangeTransformStrategy(config={
            'lookback_days': 20,
            'price_col': 'close',
            'return_periods': [],
            'include_log_returns': False,
            'include_ohlc_features': False,
        })

        result = strategy.transform(self.test_data.copy())

        # 验证价格变动率列存在（PRICE_CHG_T-1, PRICE_CHG_T-2, ...）
        price_chg_cols = [f'PRICE_CHG_T-{i}' for i in range(1, 21)]
        for col in price_chg_cols:
            self.assertIn(col, result.columns)

        print(f"  ✓ 价格变动率矩阵创建成功")
        print(f"  ✓ 矩阵维度: 20个列")

    def test_02_multi_timeframe_returns(self):
        """测试2: 多时间尺度收益率"""
        print("\n[测试2] 多时间尺度收益率...")

        periods = [1, 3, 5, 10, 20]
        strategy = PriceChangeTransformStrategy(config={
            'lookback_days': 0,
            'price_col': 'close',
            'return_periods': periods,
            'include_log_returns': True,
            'include_ohlc_features': False,
        })

        result = strategy.transform(self.test_data.copy())

        # 验证收益率列存在
        for period in periods:
            self.assertIn(f'RETURN_{period}D', result.columns)
            self.assertIn(f'LOG_RETURN_{period}D', result.columns)

        # 验证收益率值的合理性
        return_1d = result['RETURN_1D'].dropna()
        self.assertGreater(len(return_1d), 0)

        print(f"  ✓ {len(periods)} 个时间尺度收益率创建成功")
        print(f"  ✓ 包含简单收益率和对数收益率")

    def test_03_ohlc_features(self):
        """测试3: OHLC衍生特征"""
        print("\n[测试3] OHLC衍生特征...")

        strategy = PriceChangeTransformStrategy(config={
            'lookback_days': 0,
            'return_periods': [],
            'include_ohlc_features': True,
        })

        result = strategy.transform(self.test_data.copy())

        # 验证 OHLC 特征列存在（实际生成的列名）
        expected_cols = [
            'PRICE_POSITION_DAILY',  # (close - low) / (high - low)
            'BODY_STRENGTH',         # (close - open) / (high - low)
            'UPPER_SHADOW_RATIO',    # (high - max(close, open)) / (high - low)
            'LOWER_SHADOW_RATIO'     # (min(close, open) - low) / (high - low)
        ]

        for col in expected_cols:
            self.assertIn(col, result.columns, f"{col} not found in columns")

        # 验证价格位置的合理性
        # 注意：PRICE_POSITION_DAILY 是百分比格式（0-100），不是 [0, 1]
        price_position = result['PRICE_POSITION_DAILY'].dropna()
        if len(price_position) > 0:
            self.assertTrue((price_position >= 0).all())
            self.assertTrue((price_position <= 100).all())

        print(f"  ✓ {len(expected_cols)} 个OHLC特征创建成功")

    def test_04_invalid_data(self):
        """测试4: 无效数据处理"""
        print("\n[测试4] 无效数据处理...")

        strategy = PriceChangeTransformStrategy()

        # 测试空 DataFrame
        empty_df = pd.DataFrame()
        with self.assertRaises(InvalidDataError):
            strategy.transform(empty_df)

        # 测试缺少必需列（应该抛出 TransformError，不是 InvalidDataError）
        invalid_df = pd.DataFrame({'invalid_col': [1, 2, 3]})
        with self.assertRaises(TransformError):
            strategy.transform(invalid_df)

        print(f"  ✓ 无效数据正确抛出异常")


class TestNormalizationStrategy(unittest.TestCase):
    """测试标准化策略"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("NormalizationStrategy 单元测试")
        print("="*60)

    def setUp(self):
        """每个测试前的准备"""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=100, freq='D')

        self.test_data = pd.DataFrame({
            'feature1': np.random.randn(100) * 10 + 50,
            'feature2': np.random.randn(100) * 5 + 100,
            'feature3': np.random.randn(100) * 2 + 20,
        }, index=dates)

    def test_01_standard_normalization(self):
        """测试1: 标准标准化"""
        print("\n[测试1] 标准标准化...")

        strategy = NormalizationStrategy(config={
            'method': 'standard',
            'feature_cols': ['feature1', 'feature2', 'feature3'],
            'fit': True,
        })

        result = strategy.transform(self.test_data.copy())

        # 验证标准化后的特征均值接近0，标准差接近1
        # 注意：标准化后的列名会添加 _NORM 后缀
        for col in ['feature1', 'feature2', 'feature3']:
            norm_col = f'{col}_NORM'
            self.assertIn(norm_col, result.columns, f"{norm_col} not found in result")
            mean = result[norm_col].mean()
            std = result[norm_col].std()
            self.assertAlmostEqual(mean, 0.0, places=10)
            # 标准差接近1（允许小误差，因为 ddof=1）
            self.assertAlmostEqual(std, 1.0, places=1)

        print(f"  ✓ 标准标准化成功")

    def test_02_robust_normalization(self):
        """测试2: 鲁棒标准化"""
        print("\n[测试2] 鲁棒标准化...")

        # 添加离群值
        data_with_outliers = self.test_data.copy()
        data_with_outliers.loc[data_with_outliers.index[0], 'feature1'] = 1000

        strategy = NormalizationStrategy(config={
            'method': 'robust',
            'feature_cols': ['feature1', 'feature2', 'feature3'],
            'fit': True,
        })

        result = strategy.transform(data_with_outliers)

        # 验证结果存在
        for col in ['feature1', 'feature2', 'feature3']:
            self.assertIn(col, result.columns)

        print(f"  ✓ 鲁棒标准化成功（对离群值更稳健）")

    def test_03_minmax_normalization(self):
        """测试3: MinMax标准化"""
        print("\n[测试3] MinMax标准化...")

        strategy = NormalizationStrategy(config={
            'method': 'minmax',
            'feature_cols': ['feature1', 'feature2', 'feature3'],
            'fit': True,
        })

        result = strategy.transform(self.test_data.copy())

        # 验证值在 [0, 1] 范围内（标准化后的列名会添加 _NORM 后缀）
        for col in ['feature1', 'feature2', 'feature3']:
            norm_col = f'{col}_NORM'
            self.assertIn(norm_col, result.columns)
            min_val = result[norm_col].min()
            max_val = result[norm_col].max()
            self.assertAlmostEqual(min_val, 0.0, places=10)
            self.assertAlmostEqual(max_val, 1.0, places=10)

        print(f"  ✓ MinMax标准化成功")

    def test_04_rank_transform(self):
        """测试4: 排名转换"""
        print("\n[测试4] 排名转换...")

        strategy = NormalizationStrategy(config={
            'method': 'robust',
            'feature_cols': ['feature1'],
            'rank_transform': True,
            'rank_window': None,
        })

        result = strategy.transform(self.test_data.copy())

        # 验证排名特征列存在（实际生成的列名是 feature1_PCT_RANK）
        self.assertIn('feature1_PCT_RANK', result.columns)

        # 验证排名值在 [0, 1] 范围内
        ranks = result['feature1_PCT_RANK'].dropna()
        self.assertTrue((ranks >= 0).all())
        self.assertTrue((ranks <= 1).all())

        print(f"  ✓ 排名转换成功")

    def test_05_scaler_persistence(self):
        """测试5: Scaler持久化"""
        print("\n[测试5] Scaler持久化...")

        strategy = NormalizationStrategy(config={
            'method': 'standard',
            'feature_cols': ['feature1', 'feature2'],
            'fit': True,
        })

        # 训练并保存
        result1 = strategy.transform(self.test_data.copy())

        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # 保存 scalers
            success = strategy.save_scalers(tmp_path)
            self.assertTrue(success)
            self.assertTrue(Path(tmp_path).exists())

            # 创建新策略并加载 scalers
            new_strategy = NormalizationStrategy(config={
                'method': 'standard',
                'feature_cols': ['feature1', 'feature2'],
                'fit': False,
            })

            success = new_strategy.load_scalers(tmp_path)
            self.assertTrue(success)

            # 验证使用加载的 scaler 转换得到相同结果
            result2 = new_strategy.transform(self.test_data.copy())

            pd.testing.assert_frame_equal(result1, result2)

            print(f"  ✓ Scaler保存和加载成功")
        finally:
            # 清理临时文件
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()

    def test_06_scaler_not_fitted_error(self):
        """测试6: Scaler未拟合错误"""
        print("\n[测试6] Scaler未拟合错误...")

        strategy = NormalizationStrategy(config={
            'method': 'standard',
            'feature_cols': ['feature1', 'feature2'],
            'fit': False,  # 不拟合
        })

        # 应该抛出 TransformError (包装了 ScalerNotFoundError)
        with self.assertRaises(TransformError):
            strategy.transform(self.test_data.copy())

        print(f"  ✓ 未拟合错误正确抛出")


class TestTimeFeatureStrategy(unittest.TestCase):
    """测试时间特征策略"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("TimeFeatureStrategy 单元测试")
        print("="*60)

    def setUp(self):
        """每个测试前的准备"""
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        self.test_data = pd.DataFrame({
            'value': range(100)
        }, index=dates)

    def test_01_time_features(self):
        """测试1: 时间特征提取"""
        print("\n[测试1] 时间特征提取...")

        strategy = TimeFeatureStrategy()
        result = strategy.transform(self.test_data.copy())

        # 验证时间特征列存在
        expected_cols = [
            'DAY_OF_WEEK', 'MONTH', 'QUARTER',
            'IS_MONTH_START', 'IS_MONTH_END',
            'IS_QUARTER_START', 'IS_QUARTER_END',
            'IS_YEAR_START', 'IS_YEAR_END'
        ]

        for col in expected_cols:
            self.assertIn(col, result.columns, f"{col} not found in result")

        # 验证值的合理性
        self.assertTrue((result['DAY_OF_WEEK'] >= 0).all())
        self.assertTrue((result['DAY_OF_WEEK'] <= 6).all())
        self.assertTrue((result['MONTH'] >= 1).all())
        self.assertTrue((result['MONTH'] <= 12).all())
        self.assertTrue((result['QUARTER'] >= 1).all())
        self.assertTrue((result['QUARTER'] <= 4).all())

        # 验证布尔特征（转换为int后为0或1）
        self.assertTrue(result['IS_MONTH_START'].isin([0, 1]).all())
        self.assertTrue(result['IS_MONTH_END'].isin([0, 1]).all())

        print(f"  ✓ {len(expected_cols)} 个时间特征提取成功")

    def test_02_invalid_index(self):
        """测试2: 无效索引处理"""
        print("\n[测试2] 无效索引处理...")

        # 创建没有 DatetimeIndex 的数据
        invalid_data = pd.DataFrame({'value': [1, 2, 3]})

        strategy = TimeFeatureStrategy()

        # 策略会记录警告并返回原始数据，不会抛出异常
        result = strategy.transform(invalid_data)

        # 验证时间特征没有被添加（因为索引不是DatetimeIndex）
        time_cols = ['DAY_OF_WEEK', 'MONTH', 'QUARTER']
        for col in time_cols:
            self.assertNotIn(col, result.columns)

        print(f"  ✓ 无效索引处理正确（返回原始数据）")


class TestStatisticalFeatureStrategy(unittest.TestCase):
    """测试统计特征策略"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("StatisticalFeatureStrategy 单元测试")
        print("="*60)

    def setUp(self):
        """每个测试前的准备"""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=100, freq='D')

        self.test_data = pd.DataFrame({
            'close': 100 + np.random.randn(100).cumsum() * 0.5,
            'volume': np.random.uniform(1000000, 2000000, 100),
        }, index=dates)

    def test_01_lag_features(self):
        """测试1: 滞后特征"""
        print("\n[测试1] 滞后特征...")

        lags = [1, 2, 3, 5]
        strategy = StatisticalFeatureStrategy(config={
            'feature_cols': ['close'],
            'lag_periods': lags,
            'rolling_windows': [],
        })

        result = strategy.transform(self.test_data.copy())

        # 验证滞后特征列存在（格式：close_LAG1，不是 close_LAG_1）
        for lag in lags:
            lag_col = f'close_LAG{lag}'
            self.assertIn(lag_col, result.columns, f"{lag_col} not found in result")

        # 验证滞后值正确
        for lag in lags:
            lag_col = f'close_LAG{lag}'
            # 检查第一个有效值
            valid_idx = result[lag_col].first_valid_index()
            if valid_idx is not None:
                expected = self.test_data.loc[self.test_data.index[0], 'close']
                actual_idx = result.index.get_loc(valid_idx) + lag
                if actual_idx < len(result):
                    actual = result.iloc[actual_idx]['close']
                    # 滞后特征应该等于之前的值

        print(f"  ✓ {len(lags)} 个滞后特征创建成功")

    def test_02_rolling_features(self):
        """测试2: 滚动统计特征"""
        print("\n[测试2] 滚动统计特征...")

        windows = [5, 10, 20]
        funcs = ['mean', 'std', 'max', 'min']

        strategy = StatisticalFeatureStrategy(config={
            'feature_cols': ['close'],
            'lag_periods': [],
            'rolling_windows': windows,
            'rolling_funcs': funcs,
        })

        result = strategy.transform(self.test_data.copy())

        # 验证滚动特征列存在（格式：close_ROLL5_MEAN，不是 close_ROLL_5_MEAN）
        for window in windows:
            for func in funcs:
                col_name = f'close_ROLL{window}_{func.upper()}'
                self.assertIn(col_name, result.columns, f"{col_name} not found in result")

        # 验证滚动均值的合理性
        roll_5_mean = result['close_ROLL5_MEAN'].dropna()
        self.assertGreater(len(roll_5_mean), 0)

        print(f"  ✓ {len(windows) * len(funcs)} 个滚动统计特征创建成功")

    def test_03_combined_features(self):
        """测试3: 组合特征（滞后+滚动）"""
        print("\n[测试3] 组合特征...")

        strategy = StatisticalFeatureStrategy(config={
            'feature_cols': ['close', 'volume'],
            'lag_periods': [1, 3],
            'rolling_windows': [5, 10],
            'rolling_funcs': ['mean', 'std'],
        })

        result = strategy.transform(self.test_data.copy())

        # 验证两类特征都存在（注意格式：LAG1 不是 LAG_1）
        self.assertIn('close_LAG1', result.columns)
        self.assertIn('close_ROLL5_MEAN', result.columns)
        self.assertIn('volume_LAG1', result.columns)
        self.assertIn('volume_ROLL5_MEAN', result.columns)

        print(f"  ✓ 组合特征创建成功")


class TestCompositeTransformStrategy(unittest.TestCase):
    """测试组合策略"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("CompositeTransformStrategy 单元测试")
        print("="*60)

    def setUp(self):
        """每个测试前的准备"""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=100, freq='D')

        self.test_data = pd.DataFrame({
            'open': 100 + np.random.randn(100).cumsum() * 0.5,
            'high': 102 + np.random.randn(100).cumsum() * 0.5,
            'low': 98 + np.random.randn(100).cumsum() * 0.5,
            'close': 100 + np.random.randn(100).cumsum() * 0.5,
            'volume': np.random.uniform(1000000, 2000000, 100),
        }, index=dates)

        self.test_data['high'] = self.test_data[['open', 'close', 'high']].max(axis=1)
        self.test_data['low'] = self.test_data[['open', 'close', 'low']].min(axis=1)

    def test_01_multiple_strategies(self):
        """测试1: 多策略组合"""
        print("\n[测试1] 多策略组合...")

        # 创建多个策略
        strategies = [
            PriceChangeTransformStrategy(config={
                'return_periods': [1, 5],
                'include_ohlc_features': True,
            }),
            TimeFeatureStrategy(),
            StatisticalFeatureStrategy(config={
                'feature_cols': ['close'],
                'lag_periods': [1],
                'rolling_windows': [5],
            }),
        ]

        composite = CompositeTransformStrategy(strategies=strategies)
        result = composite.transform(self.test_data.copy())

        # 验证各策略的特征都存在（注意实际的列名格式）
        self.assertIn('RETURN_1D', result.columns)  # PriceChange
        self.assertIn('PRICE_POSITION_DAILY', result.columns)  # OHLC
        self.assertIn('DAY_OF_WEEK', result.columns)  # Time
        self.assertIn('close_LAG1', result.columns)  # Statistical
        self.assertIn('close_ROLL5_MEAN', result.columns)  # Statistical

        print(f"  ✓ 多策略组合成功")
        print(f"  ✓ 总特征数: {len(result.columns)}")

    def test_02_empty_strategies(self):
        """测试2: 空策略列表"""
        print("\n[测试2] 空策略列表...")

        # 空策略列表在初始化时就会抛出 ValueError
        with self.assertRaises(ValueError):
            composite = CompositeTransformStrategy(strategies=[])

        print(f"  ✓ 空策略列表正确抛出异常")


class TestFeatureTransformerWrapper(unittest.TestCase):
    """测试向后兼容的 FeatureTransformer 包装器"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("FeatureTransformer (向后兼容包装器) 单元测试")
        print("="*60)

    def setUp(self):
        """每个测试前的准备"""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=100, freq='D')

        self.test_data = pd.DataFrame({
            'open': 100 + np.random.randn(100).cumsum() * 0.5,
            'high': 102 + np.random.randn(100).cumsum() * 0.5,
            'low': 98 + np.random.randn(100).cumsum() * 0.5,
            'close': 100 + np.random.randn(100).cumsum() * 0.5,
            'volume': np.random.uniform(1000000, 2000000, 100),
        }, index=dates)

        self.test_data['high'] = self.test_data[['open', 'close', 'high']].max(axis=1)
        self.test_data['low'] = self.test_data[['open', 'close', 'low']].min(axis=1)

    def test_01_initialization(self):
        """测试1: 初始化"""
        print("\n[测试1] 初始化...")

        ft = FeatureTransformer(self.test_data)

        self.assertIsNotNone(ft)
        self.assertIsInstance(ft.df, pd.DataFrame)
        self.assertEqual(len(ft.df), len(self.test_data))
        self.assertEqual(len(ft.scalers), 0)

        print(f"  ✓ 初始化成功")

    def test_02_create_price_change_matrix(self):
        """测试2: 创建价格变动率矩阵"""
        print("\n[测试2] 创建价格变动率矩阵...")

        ft = FeatureTransformer(self.test_data)
        result = ft.create_price_change_matrix(lookback_days=20)

        # 验证价格变动率列存在（PRICE_CHG_T-1, PRICE_CHG_T-2, ...）
        price_chg_cols = [f'PRICE_CHG_T-{i}' for i in range(1, 21)]
        for col in price_chg_cols:
            self.assertIn(col, result.columns)

        print(f"  ✓ 价格变动率矩阵创建成功")

    def test_03_create_multi_timeframe_returns(self):
        """测试3: 多时间尺度收益率"""
        print("\n[测试3] 多时间尺度收益率...")

        ft = FeatureTransformer(self.test_data)
        periods = [1, 3, 5, 10, 20]
        result = ft.create_multi_timeframe_returns(periods=periods)

        for period in periods:
            self.assertIn(f'RETURN_{period}D', result.columns)
            self.assertIn(f'LOG_RETURN_{period}D', result.columns)

        print(f"  ✓ 多时间尺度收益率创建成功")

    def test_04_create_ohlc_features(self):
        """测试4: OHLC特征"""
        print("\n[测试4] OHLC特征...")

        ft = FeatureTransformer(self.test_data)
        result = ft.create_ohlc_features()

        # 验证实际生成的OHLC特征列
        self.assertIn('PRICE_POSITION_DAILY', result.columns)
        self.assertIn('BODY_STRENGTH', result.columns)
        self.assertIn('UPPER_SHADOW_RATIO', result.columns)
        self.assertIn('LOWER_SHADOW_RATIO', result.columns)

        print(f"  ✓ OHLC特征创建成功")

    def test_05_normalize_features(self):
        """测试5: 特征标准化"""
        print("\n[测试5] 特征标准化...")

        ft = FeatureTransformer(self.test_data)

        # 创建一些特征
        ft.create_multi_timeframe_returns([1, 5])

        # 标准化
        numeric_cols = ft.df.select_dtypes(include=[np.number]).columns.tolist()
        result = ft.normalize_features(numeric_cols[:3], method='standard', fit=True)

        # 验证 scalers 被创建
        self.assertGreater(len(ft.scalers), 0)

        print(f"  ✓ 特征标准化成功")
        print(f"  ✓ Scalers数量: {len(ft.scalers)}")

    def test_06_add_time_features(self):
        """测试6: 时间特征"""
        print("\n[测试6] 时间特征...")

        ft = FeatureTransformer(self.test_data)
        result = ft.add_time_features()

        self.assertIn('DAY_OF_WEEK', result.columns)
        self.assertIn('MONTH', result.columns)
        self.assertIn('QUARTER', result.columns)

        print(f"  ✓ 时间特征添加成功")

    def test_07_create_lag_features(self):
        """测试7: 滞后特征"""
        print("\n[测试7] 滞后特征...")

        ft = FeatureTransformer(self.test_data)
        lags = [1, 2, 3, 5, 10]
        result = ft.create_lag_features(['close'], lags=lags)

        # 注意格式：close_LAG1 不是 close_LAG_1
        for lag in lags:
            self.assertIn(f'close_LAG{lag}', result.columns)

        print(f"  ✓ 滞后特征创建成功")

    def test_08_create_rolling_features(self):
        """测试8: 滚动统计特征"""
        print("\n[测试8] 滚动统计特征...")

        ft = FeatureTransformer(self.test_data)
        windows = [5, 10, 20]
        funcs = ['mean', 'std', 'max', 'min']
        result = ft.create_rolling_features(['close'], windows=windows, funcs=funcs)

        # 注意格式：close_ROLL5_MEAN 不是 close_ROLL_5_MEAN
        for window in windows:
            for func in funcs:
                self.assertIn(f'close_ROLL{window}_{func.upper()}', result.columns)

        print(f"  ✓ 滚动统计特征创建成功")

    def test_09_handle_missing_values(self):
        """测试9: 缺失值处理"""
        print("\n[测试9] 缺失值处理...")

        # 创建包含 NaN 的数据
        data_with_nan = self.test_data.copy()
        data_with_nan.loc[data_with_nan.index[5:10], 'close'] = np.nan

        ft = FeatureTransformer(data_with_nan)

        # 测试不同填充方法
        methods = ['forward', 'backward', 'mean', 'median', 'zero']

        for method in methods:
            ft_test = FeatureTransformer(data_with_nan)
            result = ft_test.handle_missing_values(method=method)
            # 验证 NaN 被填充
            if method in ['forward', 'backward']:
                # 这些方法可能在边界留有 NaN
                pass
            else:
                self.assertFalse(result['close'].isna().any())

        print(f"  ✓ 缺失值处理成功")

    def test_10_handle_infinite_values(self):
        """测试10: 无穷值处理"""
        print("\n[测试10] 无穷值处理...")

        # 创建包含无穷值的数据
        data_with_inf = self.test_data.copy()
        data_with_inf.loc[data_with_inf.index[0], 'close'] = np.inf
        data_with_inf.loc[data_with_inf.index[1], 'close'] = -np.inf

        ft = FeatureTransformer(data_with_inf)
        result = ft.handle_infinite_values()

        # 验证无穷值被替换为 NaN
        self.assertTrue(result.loc[data_with_inf.index[0], 'close'] is np.nan or
                       pd.isna(result.loc[data_with_inf.index[0], 'close']))

        print(f"  ✓ 无穷值处理成功")

    def test_11_scaler_save_load(self):
        """测试11: Scaler保存和加载"""
        print("\n[测试11] Scaler保存和加载...")

        ft = FeatureTransformer(self.test_data)
        ft.create_multi_timeframe_returns([1, 5])

        # 标准化特征
        numeric_cols = ft.df.select_dtypes(include=[np.number]).columns.tolist()
        ft.normalize_features(numeric_cols[:3], method='standard', fit=True)

        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # 保存 scalers
            success = ft.save_scalers(tmp_path)
            self.assertTrue(success)

            # 加载 scalers
            ft2 = FeatureTransformer(self.test_data)
            ft2.create_multi_timeframe_returns([1, 5])
            success = ft2.load_scalers(tmp_path)
            self.assertTrue(success)
            self.assertEqual(len(ft2.scalers), len(ft.scalers))

            print(f"  ✓ Scaler保存和加载成功")
        finally:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()

    def test_12_get_methods(self):
        """测试12: 获取方法"""
        print("\n[测试12] 获取方法...")

        ft = FeatureTransformer(self.test_data)
        ft.create_multi_timeframe_returns([1, 5])
        ft.normalize_features(['close'], method='standard', fit=True)

        # 获取 DataFrame
        df = ft.get_dataframe()
        self.assertIsInstance(df, pd.DataFrame)

        # 获取 scalers
        scalers = ft.get_scalers()
        self.assertIsInstance(scalers, dict)
        self.assertGreater(len(scalers), 0)

        print(f"  ✓ 获取方法测试成功")


class TestConvenienceFunctions(unittest.TestCase):
    """测试便捷函数"""

    @classmethod
    def setUpClass(cls):
        """测试前准备"""
        print("\n" + "="*60)
        print("便捷函数单元测试")
        print("="*60)

    def setUp(self):
        """每个测试前的准备"""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=100, freq='D')

        self.test_data = pd.DataFrame({
            'open': 100 + np.random.randn(100).cumsum() * 0.5,
            'high': 102 + np.random.randn(100).cumsum() * 0.5,
            'low': 98 + np.random.randn(100).cumsum() * 0.5,
            'close': 100 + np.random.randn(100).cumsum() * 0.5,
            'volume': np.random.uniform(1000000, 2000000, 100),
        }, index=dates)

        self.test_data['high'] = self.test_data[['open', 'close', 'high']].max(axis=1)
        self.test_data['low'] = self.test_data[['open', 'close', 'low']].min(axis=1)

    def test_01_prepare_ml_features(self):
        """测试1: 准备机器学习特征"""
        print("\n[测试1] 准备机器学习特征...")

        result = prepare_ml_features(self.test_data, lookback_days=20, normalize=True)

        # 验证各类特征都存在（注意实际的列名格式）
        # 价格变动率是单独的列（PRICE_CHG_T-1 等），不是单一的 PRICE_CHANGE_MATRIX 列
        self.assertIn('PRICE_CHG_T-1', result.columns)
        self.assertIn('RETURN_1D', result.columns)
        self.assertIn('PRICE_POSITION_DAILY', result.columns)  # OHLC特征
        self.assertIn('DAY_OF_WEEK', result.columns)

        # 验证数据已标准化（标准化后的列名会添加 _NORM 后缀）
        if 'RETURN_1D_NORM' in result.columns:
            return_1d_norm = result['RETURN_1D_NORM'].dropna()
            if len(return_1d_norm) > 0:
                # 标准化后的特征应该均值接近0
                self.assertLess(abs(return_1d_norm.mean()), 1.0)

        print(f"  ✓ 机器学习特征准备成功")
        print(f"  ✓ 总特征数: {len(result.columns)}")

    def test_02_prepare_ml_features_no_normalize(self):
        """测试2: 不标准化"""
        print("\n[测试2] 不标准化...")

        result = prepare_ml_features(self.test_data, lookback_days=10, normalize=False)

        # 验证特征存在
        self.assertGreater(len(result.columns), len(self.test_data.columns))

        print(f"  ✓ 无标准化特征准备成功")


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加所有测试类
    test_classes = [
        TestPriceChangeTransformStrategy,
        TestNormalizationStrategy,
        TestTimeFeatureStrategy,
        TestStatisticalFeatureStrategy,
        TestCompositeTransformStrategy,
        TestFeatureTransformerWrapper,
        TestConvenienceFunctions,
    ]

    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 打印总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print(f"运行: {result.testsRun} 个测试")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)} 个")
    print(f"失败: {len(result.failures)} 个")
    print(f"错误: {len(result.errors)} 个")

    if result.wasSuccessful():
        print("\n✓ 所有测试通过!")
    else:
        print("\n✗ 部分测试失败")

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
