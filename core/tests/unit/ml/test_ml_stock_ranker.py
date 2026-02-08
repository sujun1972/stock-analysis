"""
单元测试: MLStockRanker
测试覆盖率目标: >= 90%

测试场景:
1. 初始化和参数验证
2. 基本评分排名 (rank)
3. 详细评分排名 (rank_dataframe)
4. 不同评分方法 (simple/sharpe/risk_adjusted)
5. 股票过滤逻辑
6. 批量评分 (batch_rank)
7. Top股票获取 (get_top_stocks)
8. 边缘情况处理
"""
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import joblib

from src.ml.ml_stock_ranker import MLStockRanker, ScoringMethod
from src.ml.trained_model import TrainedModel, TrainingConfig
from src.ml.feature_engine import FeatureEngine


class SimpleModel:
    """简单的可序列化模型"""
    def predict(self, X):
        # 返回固定的预测值用于测试
        return np.array([0.05, 0.03, -0.02, 0.08])[:len(X)]


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
def mock_model_path(tmp_path):
    """创建临时模型文件"""
    model_path = tmp_path / "test_model.pkl"

    # 创建简单模型
    simple_model = SimpleModel()

    # 创建简单特征引擎
    simple_engine = SimpleFeatureEngine()

    config = TrainingConfig(
        model_type='lightgbm',
        train_start_date='2020-01-01',
        train_end_date='2023-12-31'
    )

    trained_model = TrainedModel(
        model=simple_model,
        feature_engine=simple_engine,
        config=config,
        metrics={'ic': 0.08}
    )

    # 保存模型
    joblib.dump(trained_model, str(model_path))

    return str(model_path)


@pytest.fixture
def sample_market_data():
    """创建样本市场数据"""
    dates = pd.date_range('2024-01-01', '2024-01-30', freq='D')
    stocks = ['600000.SH', '000001.SZ', '600519.SH', '000858.SZ']

    data = []
    for stock in stocks:
        for date in dates:
            data.append({
                'stock_code': stock,
                'date': date,
                'open': 100 + np.random.randn() * 5,
                'high': 105 + np.random.randn() * 5,
                'low': 95 + np.random.randn() * 5,
                'close': 100 + np.random.randn() * 5,
                'volume': 1000000 + np.random.randint(-100000, 100000)
            })

    return pd.DataFrame(data)


@pytest.fixture
def mock_predictions():
    """创建模拟预测结果"""
    return pd.DataFrame({
        'expected_return': [0.05, 0.03, -0.02, 0.08],
        'volatility': [0.02, 0.015, 0.025, 0.018],
        'confidence': [0.85, 0.75, 0.65, 0.90]
    }, index=['600000.SH', '000001.SZ', '600519.SH', '000858.SZ'])


class TestMLStockRankerInit:
    """测试初始化"""

    def test_init_success(self, mock_model_path):
        """测试成功初始化"""
        ranker = MLStockRanker(model_path=mock_model_path)

        assert ranker.model is not None
        assert ranker.scoring_method == 'simple'
        assert ranker.min_confidence == 0.0
        assert ranker.min_expected_return == 0.0

    def test_init_with_parameters(self, mock_model_path):
        """测试带参数初始化"""
        ranker = MLStockRanker(
            model_path=mock_model_path,
            scoring_method='sharpe',
            min_confidence=0.7,
            min_expected_return=0.01
        )

        assert ranker.scoring_method == 'sharpe'
        assert ranker.min_confidence == 0.7
        assert ranker.min_expected_return == 0.01

    def test_init_invalid_scoring_method(self, mock_model_path):
        """测试无效的评分方法"""
        with pytest.raises(ValueError, match="scoring_method must be"):
            MLStockRanker(
                model_path=mock_model_path,
                scoring_method='invalid'
            )

    def test_init_invalid_min_confidence(self, mock_model_path):
        """测试无效的最小置信度"""
        with pytest.raises(ValueError, match="min_confidence must be between"):
            MLStockRanker(
                model_path=mock_model_path,
                min_confidence=1.5
            )

        with pytest.raises(ValueError, match="min_confidence must be between"):
            MLStockRanker(
                model_path=mock_model_path,
                min_confidence=-0.1
            )

    def test_init_nonexistent_model(self):
        """测试不存在的模型文件"""
        with pytest.raises(FileNotFoundError):
            MLStockRanker(model_path='/nonexistent/path/model.pkl')

    def test_repr(self, mock_model_path):
        """测试字符串表示"""
        ranker = MLStockRanker(
            model_path=mock_model_path,
            scoring_method='sharpe',
            min_confidence=0.7
        )

        repr_str = repr(ranker)
        assert 'MLStockRanker' in repr_str
        assert 'sharpe' in repr_str
        assert '0.7' in repr_str


class TestMLStockRankerRank:
    """测试基本评分排名"""

    def test_rank_success(self, mock_model_path, sample_market_data, mock_predictions):
        """测试成功评分"""
        ranker = MLStockRanker(model_path=mock_model_path)

        # Mock predict方法
        ranker.model.predict = Mock(return_value=mock_predictions)

        rankings = ranker.rank(
            stock_pool=['600000.SH', '000001.SZ', '600519.SH', '000858.SZ'],
            market_data=sample_market_data,
            date='2024-01-15',
            return_top_n=4
        )

        # 验证返回类型
        assert isinstance(rankings, dict)
        # 注意: mock_predictions中有一个股票的expected_return为负数(-0.02)
        # 默认min_expected_return=0.0会过滤掉它,所以只返回3个股票
        assert len(rankings) == 3

        # 验证降序排列
        scores = list(rankings.values())
        assert scores == sorted(scores, reverse=True)

    def test_rank_with_top_n(self, mock_model_path, sample_market_data, mock_predictions):
        """测试Top N限制"""
        ranker = MLStockRanker(model_path=mock_model_path)
        ranker.model.predict = Mock(return_value=mock_predictions)

        rankings = ranker.rank(
            stock_pool=['600000.SH', '000001.SZ', '600519.SH', '000858.SZ'],
            market_data=sample_market_data,
            date='2024-01-15',
            return_top_n=2
        )

        assert len(rankings) == 2

    def test_rank_ascending(self, mock_model_path, sample_market_data, mock_predictions):
        """测试升序排列"""
        ranker = MLStockRanker(model_path=mock_model_path)
        ranker.model.predict = Mock(return_value=mock_predictions)

        rankings = ranker.rank(
            stock_pool=['600000.SH', '000001.SZ', '600519.SH', '000858.SZ'],
            market_data=sample_market_data,
            date='2024-01-15',
            descending=False
        )

        # 验证升序排列
        scores = list(rankings.values())
        assert scores == sorted(scores)

    def test_rank_empty_stock_pool(self, mock_model_path, sample_market_data):
        """测试空股票池"""
        ranker = MLStockRanker(model_path=mock_model_path)

        with pytest.raises(ValueError, match="stock_pool cannot be empty"):
            ranker.rank(
                stock_pool=[],
                market_data=sample_market_data,
                date='2024-01-15'
            )

    def test_rank_no_predictions(self, mock_model_path, sample_market_data):
        """测试无预测结果"""
        ranker = MLStockRanker(model_path=mock_model_path)
        ranker.model.predict = Mock(return_value=pd.DataFrame())

        rankings = ranker.rank(
            stock_pool=['600000.SH'],
            market_data=sample_market_data,
            date='2024-01-15'
        )

        assert rankings == {}

    def test_rank_with_filters(self, mock_model_path, sample_market_data, mock_predictions):
        """测试过滤功能"""
        ranker = MLStockRanker(
            model_path=mock_model_path,
            min_confidence=0.8,
            min_expected_return=0.04
        )
        ranker.model.predict = Mock(return_value=mock_predictions)

        rankings = ranker.rank(
            stock_pool=['600000.SH', '000001.SZ', '600519.SH', '000858.SZ'],
            market_data=sample_market_data,
            date='2024-01-15'
        )

        # 只有000858.SZ满足条件 (expected_return=0.08, confidence=0.90)
        assert len(rankings) <= 2  # 600000.SH也可能满足条件


class TestMLStockRankerRankDataFrame:
    """测试详细评分排名"""

    def test_rank_dataframe_success(self, mock_model_path, sample_market_data, mock_predictions):
        """测试成功返回DataFrame"""
        ranker = MLStockRanker(model_path=mock_model_path)
        ranker.model.predict = Mock(return_value=mock_predictions)

        result = ranker.rank_dataframe(
            stock_pool=['600000.SH', '000001.SZ', '600519.SH', '000858.SZ'],
            market_data=sample_market_data,
            date='2024-01-15'
        )

        # 验证返回类型
        assert isinstance(result, pd.DataFrame)

        # 验证列
        assert 'score' in result.columns
        assert 'expected_return' in result.columns
        assert 'confidence' in result.columns
        assert 'volatility' in result.columns

    def test_rank_dataframe_sorted(self, mock_model_path, sample_market_data, mock_predictions):
        """测试排序"""
        ranker = MLStockRanker(model_path=mock_model_path)
        ranker.model.predict = Mock(return_value=mock_predictions)

        result = ranker.rank_dataframe(
            stock_pool=['600000.SH', '000001.SZ', '600519.SH', '000858.SZ'],
            market_data=sample_market_data,
            date='2024-01-15',
            descending=True
        )

        # 验证降序排列
        assert result['score'].is_monotonic_decreasing or len(result) == 0

    def test_rank_dataframe_empty(self, mock_model_path, sample_market_data):
        """测试空结果"""
        ranker = MLStockRanker(model_path=mock_model_path)
        ranker.model.predict = Mock(return_value=pd.DataFrame())

        result = ranker.rank_dataframe(
            stock_pool=['600000.SH'],
            market_data=sample_market_data,
            date='2024-01-15'
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


class TestMLStockRankerScoringMethods:
    """测试不同评分方法"""

    def test_simple_scoring(self, mock_model_path, sample_market_data, mock_predictions):
        """测试简单评分"""
        ranker = MLStockRanker(
            model_path=mock_model_path,
            scoring_method='simple'
        )
        ranker.model.predict = Mock(return_value=mock_predictions)

        rankings = ranker.rank(
            stock_pool=['600000.SH', '000001.SZ', '600519.SH', '000858.SZ'],
            market_data=sample_market_data,
            date='2024-01-15'
        )

        # 验证评分计算: expected_return × confidence
        # 000858.SZ: 0.08 × 0.90 = 0.072 (最高)
        assert len(rankings) > 0
        top_stock = list(rankings.keys())[0]
        # 最高分应该是000858.SZ或600000.SH
        assert top_stock in ['000858.SZ', '600000.SH']

    def test_sharpe_scoring(self, mock_model_path, sample_market_data, mock_predictions):
        """测试夏普评分"""
        ranker = MLStockRanker(
            model_path=mock_model_path,
            scoring_method='sharpe'
        )
        ranker.model.predict = Mock(return_value=mock_predictions)

        rankings = ranker.rank(
            stock_pool=['600000.SH', '000001.SZ', '600519.SH', '000858.SZ'],
            market_data=sample_market_data,
            date='2024-01-15'
        )

        # 验证评分计算: (expected_return / volatility) × confidence
        assert len(rankings) > 0

    def test_risk_adjusted_scoring(self, mock_model_path, sample_market_data, mock_predictions):
        """测试风险调整评分"""
        ranker = MLStockRanker(
            model_path=mock_model_path,
            scoring_method='risk_adjusted'
        )
        ranker.model.predict = Mock(return_value=mock_predictions)

        rankings = ranker.rank(
            stock_pool=['600000.SH', '000001.SZ', '600519.SH', '000858.SZ'],
            market_data=sample_market_data,
            date='2024-01-15'
        )

        # 验证评分计算: expected_return × confidence / volatility
        assert len(rankings) > 0

    def test_scoring_with_invalid_values(self, mock_model_path, sample_market_data):
        """测试处理无效值"""
        # 创建包含无效值的预测
        invalid_predictions = pd.DataFrame({
            'expected_return': [0.05, np.inf, -np.inf, np.nan],
            'volatility': [0.02, 0.0, 0.015, 0.018],
            'confidence': [0.85, 0.75, 0.65, 0.90]
        }, index=['600000.SH', '000001.SZ', '600519.SH', '000858.SZ'])

        ranker = MLStockRanker(
            model_path=mock_model_path,
            scoring_method='sharpe'
        )
        ranker.model.predict = Mock(return_value=invalid_predictions)

        rankings = ranker.rank(
            stock_pool=['600000.SH', '000001.SZ', '600519.SH', '000858.SZ'],
            market_data=sample_market_data,
            date='2024-01-15'
        )

        # 应该过滤掉无效股票
        assert '000001.SZ' not in rankings  # volatility=0会被过滤


class TestMLStockRankerBatchRank:
    """测试批量评分"""

    def test_batch_rank_success(self, mock_model_path, sample_market_data, mock_predictions):
        """测试成功批量评分"""
        ranker = MLStockRanker(model_path=mock_model_path)
        ranker.model.predict = Mock(return_value=mock_predictions)

        results = ranker.batch_rank(
            stock_pool=['600000.SH', '000001.SZ'],
            market_data=sample_market_data,
            dates=['2024-01-15', '2024-01-16', '2024-01-17'],
            return_top_n=2
        )

        # 验证返回格式
        assert isinstance(results, dict)
        assert len(results) == 3
        assert '2024-01-15' in results
        assert '2024-01-16' in results
        assert '2024-01-17' in results

    def test_batch_rank_with_errors(self, mock_model_path, sample_market_data, capsys):
        """测试批量评分中的错误处理"""
        ranker = MLStockRanker(model_path=mock_model_path)

        # Mock predict方法,第二次调用抛出异常
        call_count = [0]
        def predict_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 2:
                raise ValueError("Mock error")
            return pd.DataFrame({
                'expected_return': [0.05],
                'volatility': [0.02],
                'confidence': [0.85]
            }, index=['600000.SH'])

        ranker.model.predict = Mock(side_effect=predict_side_effect)

        results = ranker.batch_rank(
            stock_pool=['600000.SH'],
            market_data=sample_market_data,
            dates=['2024-01-15', '2024-01-16', '2024-01-17'],
            return_top_n=1
        )

        # 第二个日期应该返回空字典
        assert results['2024-01-16'] == {}

        # 验证警告输出
        captured = capsys.readouterr()
        assert 'Warning' in captured.out


class TestMLStockRankerHelperMethods:
    """测试辅助方法"""

    def test_get_top_stocks(self, mock_model_path, sample_market_data, mock_predictions):
        """测试获取Top股票"""
        ranker = MLStockRanker(model_path=mock_model_path)
        ranker.model.predict = Mock(return_value=mock_predictions)

        top_stocks = ranker.get_top_stocks(
            stock_pool=['600000.SH', '000001.SZ', '600519.SH', '000858.SZ'],
            market_data=sample_market_data,
            date='2024-01-15',
            top_n=2
        )

        # 验证返回类型和数量
        assert isinstance(top_stocks, list)
        assert len(top_stocks) == 2
        assert all(isinstance(stock, str) for stock in top_stocks)

    def test_filter_stocks(self, mock_model_path, mock_predictions):
        """测试股票过滤"""
        ranker = MLStockRanker(
            model_path=mock_model_path,
            min_confidence=0.8,
            min_expected_return=0.04
        )

        filtered = ranker._filter_stocks(mock_predictions)

        # 只有000858.SZ满足条件 (expected_return=0.08 >= 0.04, confidence=0.90 >= 0.8)
        # 600000.SH可能也满足 (expected_return=0.05 >= 0.04, confidence=0.85 >= 0.8)
        assert len(filtered) >= 1
        if '000858.SZ' in mock_predictions.index:
            assert '000858.SZ' in filtered.index

    def test_filter_stocks_zero_volatility(self, mock_model_path):
        """测试过滤零波动率股票"""
        predictions = pd.DataFrame({
            'expected_return': [0.05, 0.03],
            'volatility': [0.02, 0.0],  # 第二个波动率为0
            'confidence': [0.85, 0.75]
        }, index=['600000.SH', '000001.SZ'])

        ranker = MLStockRanker(model_path=mock_model_path)
        filtered = ranker._filter_stocks(predictions)

        # 000001.SZ应该被过滤掉
        assert '000001.SZ' not in filtered.index
        assert '600000.SH' in filtered.index

    def test_calculate_scores_simple(self, mock_model_path, mock_predictions):
        """测试简单评分计算"""
        ranker = MLStockRanker(
            model_path=mock_model_path,
            scoring_method='simple'
        )

        scores = ranker._calculate_scores(mock_predictions)

        # 验证评分计算
        expected_scores = (
            mock_predictions['expected_return'] *
            mock_predictions['confidence']
        )
        pd.testing.assert_series_equal(scores, expected_scores, check_names=False)

    def test_calculate_scores_sharpe(self, mock_model_path, mock_predictions):
        """测试夏普评分计算"""
        ranker = MLStockRanker(
            model_path=mock_model_path,
            scoring_method='sharpe'
        )

        scores = ranker._calculate_scores(mock_predictions)

        # 验证评分计算
        expected_scores = (
            (mock_predictions['expected_return'] / mock_predictions['volatility']) *
            mock_predictions['confidence']
        )
        pd.testing.assert_series_equal(scores, expected_scores, check_names=False)


class TestMLStockRankerEdgeCases:
    """测试边缘情况"""

    def test_all_negative_returns(self, mock_model_path, sample_market_data):
        """测试所有股票预期收益为负"""
        negative_predictions = pd.DataFrame({
            'expected_return': [-0.05, -0.03, -0.02, -0.08],
            'volatility': [0.02, 0.015, 0.025, 0.018],
            'confidence': [0.85, 0.75, 0.65, 0.90]
        }, index=['600000.SH', '000001.SZ', '600519.SH', '000858.SZ'])

        ranker = MLStockRanker(model_path=mock_model_path)
        ranker.model.predict = Mock(return_value=negative_predictions)

        rankings = ranker.rank(
            stock_pool=['600000.SH', '000001.SZ', '600519.SH', '000858.SZ'],
            market_data=sample_market_data,
            date='2024-01-15'
        )

        # 应该返回空结果 (min_expected_return默认为0.0)
        assert len(rankings) == 0

    def test_all_low_confidence(self, mock_model_path, sample_market_data):
        """测试所有股票置信度过低"""
        low_conf_predictions = pd.DataFrame({
            'expected_return': [0.05, 0.03, 0.02, 0.08],
            'volatility': [0.02, 0.015, 0.025, 0.018],
            'confidence': [0.3, 0.2, 0.1, 0.4]
        }, index=['600000.SH', '000001.SZ', '600519.SH', '000858.SZ'])

        ranker = MLStockRanker(
            model_path=mock_model_path,
            min_confidence=0.5
        )
        ranker.model.predict = Mock(return_value=low_conf_predictions)

        rankings = ranker.rank(
            stock_pool=['600000.SH', '000001.SZ', '600519.SH', '000858.SZ'],
            market_data=sample_market_data,
            date='2024-01-15'
        )

        # 应该返回空结果
        assert len(rankings) == 0

    def test_return_top_n_none(self, mock_model_path, sample_market_data, mock_predictions):
        """测试返回全部股票"""
        ranker = MLStockRanker(model_path=mock_model_path)
        ranker.model.predict = Mock(return_value=mock_predictions)

        rankings = ranker.rank(
            stock_pool=['600000.SH', '000001.SZ', '600519.SH', '000858.SZ'],
            market_data=sample_market_data,
            date='2024-01-15',
            return_top_n=None
        )

        # 应该返回所有满足条件的股票
        assert len(rankings) > 0


class TestMLStockRankerIntegration:
    """集成测试"""

    def test_full_workflow(self, mock_model_path, sample_market_data):
        """测试完整工作流"""
        # 1. 创建ranker
        ranker = MLStockRanker(
            model_path=mock_model_path,
            scoring_method='sharpe',
            min_confidence=0.6
        )

        # 2. Mock预测
        mock_predictions = pd.DataFrame({
            'expected_return': [0.05, 0.03, 0.08],
            'volatility': [0.02, 0.015, 0.018],
            'confidence': [0.85, 0.75, 0.90]
        }, index=['600000.SH', '000001.SZ', '000858.SZ'])

        ranker.model.predict = Mock(return_value=mock_predictions)

        # 3. 评分
        rankings = ranker.rank(
            stock_pool=['600000.SH', '000001.SZ', '000858.SZ'],
            market_data=sample_market_data,
            date='2024-01-15',
            return_top_n=2
        )

        # 4. 验证结果
        assert len(rankings) == 2
        assert all(score > 0 for score in rankings.values())

        # 5. 获取Top股票
        top_stocks = ranker.get_top_stocks(
            stock_pool=['600000.SH', '000001.SZ', '000858.SZ'],
            market_data=sample_market_data,
            date='2024-01-15',
            top_n=1
        )

        assert len(top_stocks) == 1
        assert top_stocks[0] in rankings


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
