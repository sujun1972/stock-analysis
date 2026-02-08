"""
MLEntry 单元测试
对齐文档: core/docs/planning/ml_system_refactoring_plan.md (Phase 1 Day 7-8)

测试覆盖:
- 初始化和参数验证
- 交易信号生成 (做多/做空)
- 置信度和夏普比率筛选
- 权重归一化
- 辅助方法
- 边缘情况处理
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile
import joblib

from src.ml.ml_entry import MLEntry
from src.ml.trained_model import TrainedModel, TrainingConfig
from src.ml.feature_engine import FeatureEngine


class SimpleModel:
    """简单的可序列化模型"""
    def predict(self, X):
        return np.random.randn(len(X)) * 0.05


class SimpleFeatureEngine:
    """简单的可序列化特征引擎"""
    def __init__(self):
        self.feature_groups = ['technical']
        self.lookback_window = 60
        self.cache_enabled = True

    def calculate_features(self, stock_codes, market_data, date):
        # 返回简单特征
        return pd.DataFrame(
            np.random.randn(len(stock_codes), 10),
            index=stock_codes
        )


@pytest.fixture
def mock_model_file():
    """创建临时模型文件"""
    # 创建简单模型
    simple_model = SimpleModel()

    # 创建简单特征引擎
    simple_engine = SimpleFeatureEngine()

    # 创建 TrainedModel
    config = TrainingConfig(
        model_type='lightgbm',
        forward_window=5,
        feature_groups=['technical']
    )

    trained_model = TrainedModel(
        model=simple_model,
        feature_engine=simple_engine,
        config=config,
        metrics={'ic': 0.08, 'rank_ic': 0.12}
    )

    # 保存到临时文件
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.pkl') as f:
        temp_path = f.name

    joblib.dump(trained_model, temp_path)

    yield temp_path

    # 清理
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def sample_market_data():
    """创建示例市场数据"""
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    stocks = ['600000.SH', '000001.SZ', '600036.SH', '000002.SZ', '600519.SH']

    data = []
    for stock in stocks:
        for date in dates:
            data.append({
                'stock_code': stock,
                'date': date,
                'open': 10.0,
                'high': 10.5,
                'low': 9.5,
                'close': 10.0 + np.random.randn() * 0.5,
                'volume': 1000000
            })

    return pd.DataFrame(data)


@pytest.fixture
def mock_predictions():
    """创建模拟预测结果"""
    return pd.DataFrame({
        'expected_return': [0.05, -0.03, 0.08, -0.02, 0.01],
        'volatility': [0.02, 0.015, 0.025, 0.01, 0.018],
        'confidence': [0.85, 0.90, 0.75, 0.80, 0.65]
    }, index=['600000.SH', '000001.SZ', '600036.SH', '000002.SZ', '600519.SH'])


class TestMLEntryInitialization:
    """测试初始化"""

    def test_init_success(self, mock_model_file):
        """测试成功初始化"""
        entry = MLEntry(
            model_path=mock_model_file,
            confidence_threshold=0.7,
            top_long=20,
            top_short=10
        )

        assert entry.confidence_threshold == 0.7
        assert entry.top_long == 20
        assert entry.top_short == 10
        assert entry.enable_short is False
        assert entry.min_expected_return == 0.0

    def test_init_with_custom_params(self, mock_model_file):
        """测试自定义参数初始化"""
        entry = MLEntry(
            model_path=mock_model_file,
            confidence_threshold=0.8,
            top_long=10,
            top_short=5,
            enable_short=True,
            min_expected_return=0.01
        )

        assert entry.confidence_threshold == 0.8
        assert entry.enable_short is True
        assert entry.min_expected_return == 0.01

    def test_init_invalid_confidence(self, mock_model_file):
        """测试无效置信度阈值"""
        with pytest.raises(ValueError, match="confidence_threshold must be between 0 and 1"):
            MLEntry(
                model_path=mock_model_file,
                confidence_threshold=1.5
            )

    def test_init_negative_top_long(self, mock_model_file):
        """测试负数top_long"""
        with pytest.raises(ValueError, match="top_long must be non-negative"):
            MLEntry(
                model_path=mock_model_file,
                top_long=-5
            )

    def test_init_model_not_found(self):
        """测试模型文件不存在"""
        with pytest.raises(FileNotFoundError):
            MLEntry(model_path='nonexistent_model.pkl')


class TestGenerateSignals:
    """测试信号生成"""

    def test_generate_signals_long_only(self, mock_model_file, sample_market_data):
        """测试仅做多信号"""
        entry = MLEntry(
            model_path=mock_model_file,
            confidence_threshold=0.6,
            top_long=3,
            enable_short=False
        )

        # Mock model.predict
        with patch.object(entry.model, 'predict') as mock_predict:
            mock_predict.return_value = pd.DataFrame({
                'expected_return': [0.05, -0.03, 0.08, -0.02, 0.01],
                'volatility': [0.02, 0.015, 0.025, 0.01, 0.018],
                'confidence': [0.85, 0.90, 0.75, 0.80, 0.65]
            }, index=['600000.SH', '000001.SZ', '600036.SH', '000002.SZ', '600519.SH'])

            signals = entry.generate_signals(
                stock_pool=['600000.SH', '000001.SZ', '600036.SH', '000002.SZ', '600519.SH'],
                market_data=sample_market_data,
                date='2024-01-15'
            )

        # 验证信号
        assert len(signals) <= 3  # 最多3个做多信号
        for stock, info in signals.items():
            assert info['action'] == 'long'
            assert 0 <= info['weight'] <= 1
            assert 'expected_return' in info
            assert 'confidence' in info

        # 验证权重之和
        total_weight = sum(s['weight'] for s in signals.values())
        assert abs(total_weight - 1.0) < 1e-6

    def test_generate_signals_with_short(self, mock_model_file, sample_market_data):
        """测试做多做空信号"""
        entry = MLEntry(
            model_path=mock_model_file,
            confidence_threshold=0.6,
            top_long=2,
            top_short=1,
            enable_short=True
        )

        with patch.object(entry.model, 'predict') as mock_predict:
            mock_predict.return_value = pd.DataFrame({
                'expected_return': [0.05, -0.03, 0.08, -0.02, 0.01],
                'volatility': [0.02, 0.015, 0.025, 0.01, 0.018],
                'confidence': [0.85, 0.90, 0.75, 0.80, 0.65]
            }, index=['600000.SH', '000001.SZ', '600036.SH', '000002.SZ', '600519.SH'])

            signals = entry.generate_signals(
                stock_pool=['600000.SH', '000001.SZ', '600036.SH', '000002.SZ', '600519.SH'],
                market_data=sample_market_data,
                date='2024-01-15'
            )

        # 验证做多和做空信号
        long_signals = {k: v for k, v in signals.items() if v['action'] == 'long'}
        short_signals = {k: v for k, v in signals.items() if v['action'] == 'short'}

        assert len(long_signals) <= 2
        assert len(short_signals) <= 1

        # 验证权重之和
        total_weight = sum(s['weight'] for s in signals.values())
        assert abs(total_weight - 1.0) < 1e-6

    def test_generate_signals_empty_pool(self, mock_model_file, sample_market_data):
        """测试空股票池"""
        entry = MLEntry(model_path=mock_model_file)

        with pytest.raises(ValueError, match="stock_pool cannot be empty"):
            entry.generate_signals(
                stock_pool=[],
                market_data=sample_market_data,
                date='2024-01-15'
            )

    def test_generate_signals_no_qualified_stocks(self, mock_model_file, sample_market_data):
        """测试没有符合条件的股票"""
        entry = MLEntry(
            model_path=mock_model_file,
            confidence_threshold=0.99  # 极高阈值
        )

        with patch.object(entry.model, 'predict') as mock_predict:
            mock_predict.return_value = pd.DataFrame({
                'expected_return': [0.01, 0.01],
                'volatility': [0.02, 0.02],
                'confidence': [0.5, 0.6]  # 都低于阈值
            }, index=['600000.SH', '000001.SZ'])

            signals = entry.generate_signals(
                stock_pool=['600000.SH', '000001.SZ'],
                market_data=sample_market_data,
                date='2024-01-15'
            )

        assert signals == {}


class TestFilterCandidates:
    """测试候选筛选"""

    def test_filter_long_candidates(self, mock_model_file, mock_predictions):
        """测试做多候选筛选"""
        entry = MLEntry(
            model_path=mock_model_file,
            confidence_threshold=0.7,
            top_long=2
        )

        candidates = entry._filter_long_candidates(mock_predictions)

        # 验证筛选结果
        assert len(candidates) <= 2
        assert all(candidates['expected_return'] > 0)
        assert all(candidates['confidence'] > 0.7)
        assert 'sharpe' in candidates.columns
        assert 'weight' in candidates.columns

        # 验证排序
        weights = candidates['weight'].tolist()
        assert weights == sorted(weights, reverse=True)

    def test_filter_short_candidates(self, mock_model_file, mock_predictions):
        """测试做空候选筛选"""
        entry = MLEntry(
            model_path=mock_model_file,
            confidence_threshold=0.7,
            top_short=1,
            enable_short=True
        )

        candidates = entry._filter_short_candidates(mock_predictions)

        # 验证筛选结果
        assert len(candidates) <= 1
        assert all(candidates['expected_return'] < 0)
        assert all(candidates['confidence'] > 0.7)

    def test_filter_short_disabled(self, mock_model_file, mock_predictions):
        """测试禁用做空"""
        entry = MLEntry(
            model_path=mock_model_file,
            enable_short=False
        )

        candidates = entry._filter_short_candidates(mock_predictions)
        assert len(candidates) == 0


class TestWeightNormalization:
    """测试权重归一化"""

    def test_normalize_weights_normal(self, mock_model_file):
        """测试正常权重归一化"""
        entry = MLEntry(model_path=mock_model_file)

        signals = {
            '600000.SH': {'action': 'long', 'weight': 2.0, 'expected_return': 0.05, 'confidence': 0.8},
            '000001.SZ': {'action': 'long', 'weight': 3.0, 'expected_return': 0.03, 'confidence': 0.9}
        }

        normalized = entry._normalize_weights(signals)

        # 验证权重之和为1
        total_weight = sum(s['weight'] for s in normalized.values())
        assert abs(total_weight - 1.0) < 1e-6

        # 验证比例保持
        assert abs(normalized['600000.SH']['weight'] - 0.4) < 1e-6
        assert abs(normalized['000001.SZ']['weight'] - 0.6) < 1e-6

    def test_normalize_weights_zero_total(self, mock_model_file):
        """测试总权重为零"""
        entry = MLEntry(model_path=mock_model_file)

        signals = {
            '600000.SH': {'action': 'long', 'weight': 0.0, 'expected_return': 0.05, 'confidence': 0.8},
            '000001.SZ': {'action': 'long', 'weight': 0.0, 'expected_return': 0.03, 'confidence': 0.9}
        }

        normalized = entry._normalize_weights(signals)

        # 验证均分权重
        assert abs(normalized['600000.SH']['weight'] - 0.5) < 1e-6
        assert abs(normalized['000001.SZ']['weight'] - 0.5) < 1e-6

    def test_normalize_weights_empty(self, mock_model_file):
        """测试空信号"""
        entry = MLEntry(model_path=mock_model_file)

        normalized = entry._normalize_weights({})
        assert normalized == {}


class TestGetTopStocks:
    """测试获取Top股票"""

    def test_get_top_stocks_long(self, mock_model_file, sample_market_data):
        """测试获取Top做多股票"""
        entry = MLEntry(
            model_path=mock_model_file,
            confidence_threshold=0.6,
            top_long=5
        )

        with patch.object(entry.model, 'predict') as mock_predict:
            mock_predict.return_value = pd.DataFrame({
                'expected_return': [0.05, 0.03, 0.08, 0.02, 0.01],
                'volatility': [0.02, 0.015, 0.025, 0.01, 0.018],
                'confidence': [0.85, 0.90, 0.75, 0.80, 0.65]
            }, index=['600000.SH', '000001.SZ', '600036.SH', '000002.SZ', '600519.SH'])

            top_stocks = entry.get_top_stocks(
                stock_pool=['600000.SH', '000001.SZ', '600036.SH', '000002.SZ', '600519.SH'],
                market_data=sample_market_data,
                date='2024-01-15',
                top_n=3,
                action='long'
            )

        assert len(top_stocks) <= 3
        assert all(isinstance(stock, str) for stock in top_stocks)

    def test_get_top_stocks_short(self, mock_model_file, sample_market_data):
        """测试获取Top做空股票"""
        entry = MLEntry(
            model_path=mock_model_file,
            confidence_threshold=0.6,
            top_short=2,
            enable_short=True
        )

        with patch.object(entry.model, 'predict') as mock_predict:
            mock_predict.return_value = pd.DataFrame({
                'expected_return': [0.05, -0.03, 0.08, -0.02, 0.01],
                'volatility': [0.02, 0.015, 0.025, 0.01, 0.018],
                'confidence': [0.85, 0.90, 0.75, 0.80, 0.65]
            }, index=['600000.SH', '000001.SZ', '600036.SH', '000002.SZ', '600519.SH'])

            top_stocks = entry.get_top_stocks(
                stock_pool=['600000.SH', '000001.SZ', '600036.SH', '000002.SZ', '600519.SH'],
                market_data=sample_market_data,
                date='2024-01-15',
                top_n=2,
                action='short'
            )

        assert len(top_stocks) <= 2

    def test_get_top_stocks_invalid_action(self, mock_model_file, sample_market_data):
        """测试无效action参数"""
        entry = MLEntry(model_path=mock_model_file)

        with pytest.raises(ValueError, match="action must be 'long' or 'short'"):
            entry.get_top_stocks(
                stock_pool=['600000.SH'],
                market_data=sample_market_data,
                date='2024-01-15',
                action='invalid'
            )


class TestEdgeCases:
    """测试边缘情况"""

    def test_zero_volatility(self, mock_model_file, sample_market_data):
        """测试零波动率"""
        entry = MLEntry(
            model_path=mock_model_file,
            confidence_threshold=0.5
        )

        with patch.object(entry.model, 'predict') as mock_predict:
            mock_predict.return_value = pd.DataFrame({
                'expected_return': [0.05, 0.03],
                'volatility': [0.0, 0.02],  # 第一个为0
                'confidence': [0.8, 0.9]
            }, index=['600000.SH', '000001.SZ'])

            signals = entry.generate_signals(
                stock_pool=['600000.SH', '000001.SZ'],
                market_data=sample_market_data,
                date='2024-01-15'
            )

        # 零波动率的股票应该被过滤
        assert '600000.SH' not in signals

    def test_high_min_expected_return(self, mock_model_file, sample_market_data):
        """测试高最小预期收益率阈值"""
        entry = MLEntry(
            model_path=mock_model_file,
            confidence_threshold=0.5,
            min_expected_return=0.1  # 很高的阈值
        )

        with patch.object(entry.model, 'predict') as mock_predict:
            mock_predict.return_value = pd.DataFrame({
                'expected_return': [0.05, 0.03],  # 都低于阈值
                'volatility': [0.02, 0.02],
                'confidence': [0.8, 0.9]
            }, index=['600000.SH', '000001.SZ'])

            signals = entry.generate_signals(
                stock_pool=['600000.SH', '000001.SZ'],
                market_data=sample_market_data,
                date='2024-01-15'
            )

        assert signals == {}


class TestRepr:
    """测试字符串表示"""

    def test_repr(self, mock_model_file):
        """测试__repr__方法"""
        entry = MLEntry(
            model_path=mock_model_file,
            confidence_threshold=0.75,
            top_long=15,
            top_short=5,
            enable_short=True
        )

        repr_str = repr(entry)

        assert 'MLEntry' in repr_str
        assert 'confidence_threshold=0.75' in repr_str
        assert 'top_long=15' in repr_str
        assert 'top_short=5' in repr_str
        assert 'enable_short=True' in repr_str


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
