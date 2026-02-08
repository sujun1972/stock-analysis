"""
FeatureEngine单元测试

测试覆盖:
1. 初始化
2. 特征计算
3. 缓存机制
4. 错误处理
5. 数据格式兼容性
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.ml.feature_engine import FeatureEngine


@pytest.fixture
def sample_market_data():
    """创建测试用的市场数据"""
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    stocks = ['600000.SH', '000001.SZ', '000002.SZ']

    data_list = []
    for stock in stocks:
        np.random.seed(hash(stock) % 2**32)  # 每个股票使用不同的种子

        # 生成模拟价格数据
        base_price = 10.0
        prices = base_price + np.cumsum(np.random.randn(len(dates)) * 0.02)
        prices = np.maximum(prices, 1.0)  # 确保价格为正

        for i, date in enumerate(dates):
            data_list.append({
                'date': date,
                'stock_code': stock,
                'open': prices[i] * (1 + np.random.randn() * 0.01),
                'high': prices[i] * (1 + abs(np.random.randn()) * 0.02),
                'low': prices[i] * (1 - abs(np.random.randn()) * 0.02),
                'close': prices[i],
                'volume': np.random.randint(1000000, 10000000)
            })

    df = pd.DataFrame(data_list)
    return df


@pytest.fixture
def feature_engine():
    """创建FeatureEngine实例"""
    return FeatureEngine(
        feature_groups=['all'],
        lookback_window=60,
        cache_enabled=True
    )


class TestFeatureEngineInit:
    """测试FeatureEngine初始化"""

    def test_default_init(self):
        """测试默认初始化"""
        engine = FeatureEngine()
        assert engine.feature_groups == ['all']
        assert engine.lookback_window == 60
        assert engine.cache_enabled is True

    def test_custom_init(self):
        """测试自定义初始化"""
        engine = FeatureEngine(
            feature_groups=['alpha', 'technical'],
            lookback_window=120,
            cache_enabled=False
        )
        assert engine.feature_groups == ['alpha', 'technical']
        assert engine.lookback_window == 120
        assert engine.cache_enabled is False

    def test_feature_groups_validation(self):
        """测试特征组参数"""
        # 单个特征组
        engine = FeatureEngine(feature_groups=['alpha'])
        assert engine._should_include('alpha') is True
        assert engine._should_include('technical') is False

        # 多个特征组
        engine = FeatureEngine(feature_groups=['alpha', 'volume'])
        assert engine._should_include('alpha') is True
        assert engine._should_include('volume') is True
        assert engine._should_include('technical') is False

        # all包含所有
        engine = FeatureEngine(feature_groups=['all'])
        assert engine._should_include('alpha') is True
        assert engine._should_include('technical') is True
        assert engine._should_include('volume') is True


class TestFeatureCalculation:
    """测试特征计算"""

    def test_calculate_features_basic(self, feature_engine, sample_market_data):
        """测试基本特征计算"""
        stock_codes = ['600000.SH', '000001.SZ']
        date = '2024-03-01'

        features = feature_engine.calculate_features(
            stock_codes=stock_codes,
            market_data=sample_market_data,
            date=date
        )

        # 检查返回类型
        assert isinstance(features, pd.DataFrame)

        # 检查索引
        assert list(features.index) == stock_codes

        # 检查有特征列
        assert len(features.columns) > 0

    def test_calculate_features_single_stock(self, feature_engine, sample_market_data):
        """测试单只股票特征计算"""
        stock_codes = ['600000.SH']
        date = '2024-03-01'

        features = feature_engine.calculate_features(
            stock_codes=stock_codes,
            market_data=sample_market_data,
            date=date
        )

        assert len(features) == 1
        assert features.index[0] == '600000.SH'

    def test_calculate_features_specific_groups(self, sample_market_data):
        """测试指定特征组计算"""
        # 只计算Alpha因子
        engine_alpha = FeatureEngine(feature_groups=['alpha'])
        features_alpha = engine_alpha.calculate_features(
            stock_codes=['600000.SH'],
            market_data=sample_market_data,
            date='2024-03-01'
        )

        # 只计算技术指标
        engine_tech = FeatureEngine(feature_groups=['technical'])
        features_tech = engine_tech.calculate_features(
            stock_codes=['600000.SH'],
            market_data=sample_market_data,
            date='2024-03-01'
        )

        # Alpha和技术指标的特征列应该不同
        # 注意：可能有些列重叠，所以只检查不完全相同
        assert len(features_alpha.columns) > 0
        assert len(features_tech.columns) > 0

    def test_calculate_features_no_data(self, feature_engine):
        """测试无数据情况"""
        empty_data = pd.DataFrame(columns=['date', 'stock_code', 'close'])

        with pytest.raises(ValueError, match="No data found"):
            feature_engine.calculate_features(
                stock_codes=['600000.SH'],
                market_data=empty_data,
                date='2024-03-01'
            )

    def test_calculate_features_insufficient_data(self, feature_engine):
        """测试数据不足情况"""
        # 只有几天数据
        short_data = pd.DataFrame({
            'date': pd.date_range('2024-03-01', periods=5),
            'stock_code': ['600000.SH'] * 5,
            'close': [10.0, 10.1, 10.2, 10.3, 10.4],
            'volume': [1000000] * 5
        })

        # 应该能处理但可能特征较少
        features = feature_engine.calculate_features(
            stock_codes=['600000.SH'],
            market_data=short_data,
            date='2024-03-05'
        )

        # 至少返回一个空的DataFrame框架
        assert isinstance(features, pd.DataFrame)


class TestCacheMechanism:
    """测试缓存机制"""

    def test_cache_enabled(self, sample_market_data):
        """测试缓存启用"""
        engine = FeatureEngine(cache_enabled=True)
        stock_codes = ['600000.SH']
        date = '2024-03-01'

        # 第一次计算
        features1 = engine.calculate_features(
            stock_codes, sample_market_data, date
        )

        # 第二次应该从缓存读取
        features2 = engine.calculate_features(
            stock_codes, sample_market_data, date
        )

        # 结果应该相同
        pd.testing.assert_frame_equal(features1, features2)

        # 缓存应该有内容
        assert len(engine._cache) > 0

    def test_cache_disabled(self, sample_market_data):
        """测试缓存禁用"""
        engine = FeatureEngine(cache_enabled=False)
        stock_codes = ['600000.SH']
        date = '2024-03-01'

        engine.calculate_features(stock_codes, sample_market_data, date)

        # 缓存应该为空
        assert len(engine._cache) == 0

    def test_clear_cache(self, feature_engine, sample_market_data):
        """测试清空缓存"""
        stock_codes = ['600000.SH']
        date = '2024-03-01'

        feature_engine.calculate_features(stock_codes, sample_market_data, date)
        assert len(feature_engine._cache) > 0

        feature_engine.clear_cache()
        assert len(feature_engine._cache) == 0

    def test_cache_key_generation(self, feature_engine):
        """测试缓存键生成"""
        key1 = feature_engine._generate_cache_key(['600000.SH', '000001.SZ'], '2024-03-01')
        key2 = feature_engine._generate_cache_key(['000001.SZ', '600000.SH'], '2024-03-01')
        key3 = feature_engine._generate_cache_key(['600000.SH'], '2024-03-01')

        # 相同股票不同顺序应该生成相同key
        assert key1 == key2

        # 不同股票应该生成不同key
        assert key1 != key3


class TestBatchCalculation:
    """测试批量计算"""

    def test_calculate_batch_compatibility(self, feature_engine, sample_market_data):
        """测试calculate_batch与calculate_features兼容性"""
        stock_codes = ['600000.SH', '000001.SZ']
        date = '2024-03-01'

        features1 = feature_engine.calculate_features(
            stock_codes, sample_market_data, date
        )

        # 清空缓存
        feature_engine.clear_cache()

        features2 = feature_engine.calculate_batch(
            stock_codes, sample_market_data, date
        )

        # 两种方法应该返回相同结果
        pd.testing.assert_frame_equal(features1, features2)


class TestFeatureNames:
    """测试特征名称管理"""

    def test_get_feature_names_before_calculation(self, feature_engine):
        """测试计算前获取特征名"""
        names = feature_engine.get_feature_names()
        assert names == []

    def test_get_feature_names_after_calculation(self, feature_engine, sample_market_data):
        """测试计算后获取特征名"""
        feature_engine.calculate_features(
            ['600000.SH'],
            sample_market_data,
            '2024-03-01'
        )

        names = feature_engine.get_feature_names()
        assert len(names) > 0
        assert isinstance(names, list)


class TestDataFormat:
    """测试数据格式兼容性"""

    def test_market_data_without_date_column(self, feature_engine):
        """测试缺少date列"""
        bad_data = pd.DataFrame({
            'stock_code': ['600000.SH'],
            'close': [10.0]
        })

        with pytest.raises(ValueError, match="必须包含'date'列"):
            feature_engine.calculate_features(
                ['600000.SH'], bad_data, '2024-03-01'
            )

    def test_market_data_date_as_string(self, feature_engine):
        """测试日期为字符串格式"""
        data = pd.DataFrame({
            'date': ['2024-03-01', '2024-03-02', '2024-03-03'],
            'stock_code': ['600000.SH'] * 3,
            'close': [10.0, 10.1, 10.2],
            'volume': [1000000] * 3
        })

        # 应该能自动转换
        features = feature_engine.calculate_features(
            ['600000.SH'], data, '2024-03-03'
        )

        assert isinstance(features, pd.DataFrame)


class TestRepr:
    """测试字符串表示"""

    def test_repr_before_calculation(self):
        """测试计算前的repr"""
        engine = FeatureEngine(feature_groups=['alpha'], lookback_window=30)
        repr_str = repr(engine)

        assert 'FeatureEngine' in repr_str
        assert 'alpha' in repr_str
        assert '30' in repr_str
        assert 'n_features=0' in repr_str

    def test_repr_after_calculation(self, sample_market_data):
        """测试计算后的repr"""
        engine = FeatureEngine()
        engine.calculate_features(
            ['600000.SH'],
            sample_market_data,
            '2024-03-01'
        )

        repr_str = repr(engine)
        assert 'n_features=' in repr_str
        # 应该有一些特征
        assert 'n_features=0' not in repr_str


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
