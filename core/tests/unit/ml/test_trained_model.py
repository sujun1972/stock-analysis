"""
TrainedModel 单元测试

测试覆盖:
1. TrainingConfig 初始化和验证
2. TrainedModel 初始化
3. 预测功能 (predict)
4. 波动率估算
5. 置信度估算
6. 模型保存和加载
7. 特征列对齐
8. 边缘情况处理

创建时间: 2026-02-08
"""
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import joblib

from src.ml.trained_model import TrainedModel, TrainingConfig
from src.ml.feature_engine import FeatureEngine


# ==================== 1. Fixtures ====================

@pytest.fixture
def sample_market_data():
    """创建样本市场数据"""
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    stocks = ['600000.SH', '000001.SZ', '000002.SZ']

    data = []
    for stock in stocks:
        for i, date in enumerate(dates):
            # 生成价格趋势
            base_price = 10 + i * 0.1
            noise = np.random.randn() * 0.5

            data.append({
                'stock_code': stock,
                'date': date,
                'open': base_price + noise,
                'high': base_price + abs(noise) + 0.5,
                'low': base_price - abs(noise) - 0.5,
                'close': base_price + noise * 0.5,
                'volume': 1000000 + np.random.randint(-100000, 100000),
                'amount': (base_price + noise * 0.5) * (1000000 + np.random.randint(-100000, 100000))
            })

    return pd.DataFrame(data)


class MockModel:
    """模拟的机器学习模型（顶层类，可序列化）"""
    def predict(self, X):
        """返回简单的预测结果"""
        # 返回0.01到0.05之间的随机收益率预测
        return np.random.uniform(0.01, 0.05, size=len(X))


@pytest.fixture
def mock_model():
    """创建模拟模型"""
    return MockModel()


@pytest.fixture
def feature_engine():
    """创建特征引擎"""
    return FeatureEngine(
        feature_groups=['technical'],
        lookback_window=20,
        cache_enabled=False
    )


@pytest.fixture
def training_config():
    """创建训练配置"""
    return TrainingConfig(
        model_type='lightgbm',
        train_start_date='2023-01-01',
        train_end_date='2023-12-31',
        validation_split=0.2,
        forward_window=5,
        feature_groups=['technical']
    )


@pytest.fixture
def trained_model(mock_model, feature_engine, training_config):
    """创建训练好的模型"""
    return TrainedModel(
        model=mock_model,
        feature_engine=feature_engine,
        config=training_config,
        metrics={'ic': 0.08, 'rank_ic': 0.12}
    )


# ==================== 2. TrainingConfig Tests ====================

class TestTrainingConfig:
    """测试 TrainingConfig"""

    def test_default_config(self):
        """测试默认配置"""
        config = TrainingConfig()

        assert config.model_type == 'lightgbm'
        assert config.train_start_date == '2020-01-01'
        assert config.train_end_date == '2023-12-31'
        assert config.validation_split == 0.2
        assert config.forward_window == 5
        assert config.feature_groups == ['all']
        assert config.hyperparameters is None

    def test_custom_config(self):
        """测试自定义配置"""
        config = TrainingConfig(
            model_type='xgboost',
            train_start_date='2022-01-01',
            train_end_date='2023-06-30',
            validation_split=0.3,
            forward_window=10,
            feature_groups=['alpha', 'technical'],
            hyperparameters={'n_estimators': 100, 'max_depth': 5}
        )

        assert config.model_type == 'xgboost'
        assert config.train_start_date == '2022-01-01'
        assert config.train_end_date == '2023-06-30'
        assert config.validation_split == 0.3
        assert config.forward_window == 10
        assert config.feature_groups == ['alpha', 'technical']
        assert config.hyperparameters == {'n_estimators': 100, 'max_depth': 5}

    def test_invalid_model_type(self):
        """测试无效的模型类型"""
        # 现在允许任何非空字符串作为model_type，测试空字符串
        with pytest.raises(ValueError, match="model_type must be a non-empty string"):
            TrainingConfig(model_type='')

    def test_invalid_validation_split(self):
        """测试无效的验证集比例"""
        with pytest.raises(ValueError, match="validation_split must be between 0 and 1"):
            TrainingConfig(validation_split=1.5)

        with pytest.raises(ValueError, match="validation_split must be between 0 and 1"):
            TrainingConfig(validation_split=-0.1)

    def test_invalid_forward_window(self):
        """测试无效的前向窗口"""
        with pytest.raises(ValueError, match="forward_window must be positive"):
            TrainingConfig(forward_window=-5)


# ==================== 3. TrainedModel Initialization Tests ====================

class TestTrainedModelInit:
    """测试 TrainedModel 初始化"""

    def test_init_success(self, mock_model, feature_engine, training_config):
        """测试成功初始化"""
        model = TrainedModel(
            model=mock_model,
            feature_engine=feature_engine,
            config=training_config,
            metrics={'ic': 0.08}
        )

        assert model.model == mock_model
        assert model.feature_engine == feature_engine
        assert model.config == training_config
        assert model.metrics == {'ic': 0.08}
        assert model.feature_columns is None

    def test_init_with_invalid_model(self, feature_engine, training_config):
        """测试使用无效模型初始化"""
        class InvalidModel:
            pass  # 没有 predict 方法

        with pytest.raises(ValueError, match="Model must implement 'predict' method"):
            TrainedModel(
                model=InvalidModel(),
                feature_engine=feature_engine,
                config=training_config,
                metrics={}
            )

    def test_repr(self, trained_model):
        """测试字符串表示"""
        repr_str = repr(trained_model)

        assert 'TrainedModel' in repr_str
        assert 'lightgbm' in repr_str
        assert '0.08' in repr_str


# ==================== 4. Predict Tests ====================

class TestPredict:
    """测试预测功能"""

    def test_predict_basic(self, trained_model, sample_market_data):
        """测试基本预测"""
        stock_codes = ['600000.SH', '000001.SZ']
        date = '2024-02-15'

        result = trained_model.predict(stock_codes, sample_market_data, date)

        # 检查返回结构
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ['expected_return', 'volatility', 'confidence']
        assert len(result) == len(stock_codes)

        # 检查数值范围
        assert result['expected_return'].notna().all()
        assert (result['volatility'] >= 0).all()
        assert (result['confidence'] >= 0.5).all()
        assert (result['confidence'] <= 1.0).all()

    def test_predict_with_feature_columns(self, trained_model, sample_market_data):
        """测试设置特征列后的预测"""
        stock_codes = ['600000.SH']
        date = '2024-02-15'

        # 第一次预测,获取特征列
        result1 = trained_model.predict(stock_codes, sample_market_data, date)
        feature_cols = trained_model.feature_engine.calculate_features(
            stock_codes, sample_market_data, date
        ).columns.tolist()

        # 设置特征列
        trained_model.set_feature_columns(feature_cols)

        # 第二次预测
        result2 = trained_model.predict(stock_codes, sample_market_data, date)

        assert result2 is not None
        assert len(result2) == 1

    def test_predict_with_missing_data(self, trained_model, sample_market_data):
        """测试数据不足时的预测"""
        stock_codes = ['600000.SH']
        date = '2024-01-05'  # 数据刚开始,可能不足

        # 应该能处理或抛出明确错误
        try:
            result = trained_model.predict(stock_codes, sample_market_data, date)
            # 如果成功,检查结果
            assert isinstance(result, pd.DataFrame)
        except ValueError as e:
            # 预期的错误
            assert "Failed to calculate features" in str(e)

    def test_predict_invalid_date(self, trained_model, sample_market_data):
        """测试无效日期"""
        stock_codes = ['600000.SH']
        date = '2099-12-31'  # 未来日期

        with pytest.raises(ValueError):
            trained_model.predict(stock_codes, sample_market_data, date)


# ==================== 5. Volatility Estimation Tests ====================

class TestVolatilityEstimation:
    """测试波动率估算"""

    def test_estimate_volatility_basic(self, trained_model, sample_market_data):
        """测试基本波动率估算"""
        stock_codes = ['600000.SH', '000001.SZ']
        date = '2024-02-15'

        volatilities = trained_model._estimate_volatility(
            stock_codes, sample_market_data, date
        )

        assert isinstance(volatilities, pd.Series)
        assert len(volatilities) == len(stock_codes)
        assert (volatilities >= 0).all()

    def test_estimate_volatility_insufficient_data(self, trained_model, sample_market_data):
        """测试数据不足时的波动率估算"""
        stock_codes = ['600000.SH']
        date = '2024-01-05'  # 数据不足20天

        volatilities = trained_model._estimate_volatility(
            stock_codes, sample_market_data, date, window=20
        )

        # 应该返回默认值 0.02
        assert volatilities.loc['600000.SH'] == 0.02

    def test_estimate_volatility_custom_window(self, trained_model, sample_market_data):
        """测试自定义窗口的波动率估算"""
        stock_codes = ['600000.SH']
        date = '2024-02-15'

        vol_short = trained_model._estimate_volatility(
            stock_codes, sample_market_data, date, window=5
        )
        vol_long = trained_model._estimate_volatility(
            stock_codes, sample_market_data, date, window=30
        )

        assert isinstance(vol_short, pd.Series)
        assert isinstance(vol_long, pd.Series)


# ==================== 6. Confidence Estimation Tests ====================

class TestConfidenceEstimation:
    """测试置信度估算"""

    def test_estimate_confidence_complete_features(self, trained_model):
        """测试完整特征的置信度"""
        features = pd.DataFrame({
            'feature1': [1.0, 2.0, 3.0],
            'feature2': [4.0, 5.0, 6.0],
            'feature3': [7.0, 8.0, 9.0]
        }, index=['A', 'B', 'C'])

        confidence = trained_model._estimate_confidence(features)

        assert isinstance(confidence, pd.Series)
        assert len(confidence) == 3
        assert (confidence == 1.0).all()  # 完整特征

    def test_estimate_confidence_partial_features(self, trained_model):
        """测试部分缺失特征的置信度"""
        features = pd.DataFrame({
            'feature1': [1.0, 2.0, 3.0],
            'feature2': [4.0, np.nan, 6.0],
            'feature3': [7.0, 8.0, np.nan]
        }, index=['A', 'B', 'C'])

        confidence = trained_model._estimate_confidence(features)

        assert isinstance(confidence, pd.Series)
        assert len(confidence) == 3
        assert confidence.loc['A'] == 1.0  # 完整
        assert 0.5 <= confidence.loc['B'] <= 1.0  # 部分缺失
        assert 0.5 <= confidence.loc['C'] <= 1.0

    def test_estimate_confidence_range(self, trained_model):
        """测试置信度范围"""
        features = pd.DataFrame({
            'feature1': [np.nan, np.nan, np.nan],
            'feature2': [np.nan, np.nan, np.nan],
        }, index=['A', 'B', 'C'])

        confidence = trained_model._estimate_confidence(features)

        # 即使所有特征缺失,置信度也应该 >= 0.5
        assert (confidence >= 0.5).all()
        assert (confidence <= 1.0).all()


# ==================== 7. Save and Load Tests ====================

class TestSaveAndLoad:
    """测试模型保存和加载"""

    def test_save_and_load(self, trained_model):
        """测试保存和加载模型"""
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / 'test_model.pkl'

            # 保存
            trained_model.save(str(model_path))
            assert model_path.exists()

            # 加载
            loaded_model = TrainedModel.load(str(model_path))

            # 验证
            assert loaded_model.config.model_type == trained_model.config.model_type
            assert loaded_model.metrics == trained_model.metrics
            assert isinstance(loaded_model.feature_engine, FeatureEngine)

    def test_save_creates_directory(self, trained_model):
        """测试保存时自动创建目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / 'subdir' / 'models' / 'test_model.pkl'

            trained_model.save(str(model_path))
            assert model_path.exists()

    def test_load_nonexistent_file(self):
        """测试加载不存在的文件"""
        with pytest.raises(FileNotFoundError, match="模型不存在"):
            TrainedModel.load('nonexistent_model.pkl')

    def test_save_and_load_with_feature_columns(self, trained_model):
        """测试保存和加载带特征列的模型"""
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / 'test_model.pkl'

            # 设置特征列
            trained_model.set_feature_columns(['feature1', 'feature2', 'feature3'])

            # 保存
            trained_model.save(str(model_path))

            # 加载
            loaded_model = TrainedModel.load(str(model_path))

            assert loaded_model.feature_columns == ['feature1', 'feature2', 'feature3']


# ==================== 8. Feature Columns Tests ====================

class TestFeatureColumns:
    """测试特征列管理"""

    def test_set_feature_columns(self, trained_model):
        """测试设置特征列"""
        columns = ['feature1', 'feature2', 'feature3']
        trained_model.set_feature_columns(columns)

        assert trained_model.feature_columns == columns

    def test_predict_with_aligned_features(self, trained_model, sample_market_data):
        """测试特征对齐后的预测"""
        stock_codes = ['600000.SH']
        date = '2024-02-15'

        # 第一次预测
        result1 = trained_model.predict(stock_codes, sample_market_data, date)

        # 获取特征列
        features = trained_model.feature_engine.calculate_features(
            stock_codes, sample_market_data, date
        )
        trained_model.set_feature_columns(features.columns.tolist())

        # 第二次预测
        result2 = trained_model.predict(stock_codes, sample_market_data, date)

        assert result2 is not None
        assert len(result2) == 1


# ==================== 9. Edge Cases Tests ====================

class TestEdgeCases:
    """测试边缘情况"""

    def test_predict_empty_stock_codes(self, trained_model, sample_market_data):
        """测试空股票列表"""
        date = '2024-02-15'

        # 空列表应该抛出错误或返回空结果
        with pytest.raises(ValueError, match="Failed to calculate features"):
            result = trained_model.predict([], sample_market_data, date)

    def test_predict_single_stock(self, trained_model, sample_market_data):
        """测试单个股票预测"""
        stock_codes = ['600000.SH']
        date = '2024-02-15'

        result = trained_model.predict(stock_codes, sample_market_data, date)

        assert len(result) == 1
        assert result.index[0] == '600000.SH'

    def test_predict_many_stocks(self, trained_model, sample_market_data):
        """测试多个股票预测"""
        stock_codes = ['600000.SH', '000001.SZ', '000002.SZ']
        date = '2024-02-15'

        result = trained_model.predict(stock_codes, sample_market_data, date)

        assert len(result) == 3
        assert set(result.index) == set(stock_codes)

    def test_metrics_with_different_types(self, mock_model, feature_engine, training_config):
        """测试不同类型的指标"""
        metrics = {
            'ic': 0.08,
            'rank_ic': 0.12,
            'sharpe': 1.5,
            'max_drawdown': -0.15,
            'status': 'good'
        }

        model = TrainedModel(
            model=mock_model,
            feature_engine=feature_engine,
            config=training_config,
            metrics=metrics
        )

        assert model.metrics == metrics


# ==================== 10. Integration Tests ====================

class TestIntegration:
    """集成测试"""

    def test_full_workflow(self, mock_model, sample_market_data):
        """测试完整工作流"""
        # 1. 创建配置
        config = TrainingConfig(
            model_type='lightgbm',
            forward_window=5,
            feature_groups=['technical']
        )

        # 2. 创建特征引擎
        engine = FeatureEngine(
            feature_groups=['technical'],
            lookback_window=20,
            cache_enabled=False
        )

        # 3. 创建模型
        model = TrainedModel(
            model=mock_model,
            feature_engine=engine,
            config=config,
            metrics={'ic': 0.08}
        )

        # 4. 预测
        stock_codes = ['600000.SH', '000001.SZ']
        date = '2024-02-15'
        result = model.predict(stock_codes, sample_market_data, date)

        # 5. 验证
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        assert 'expected_return' in result.columns
        assert 'volatility' in result.columns
        assert 'confidence' in result.columns

        # 6. 保存和加载
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / 'model.pkl'
            model.save(str(model_path))

            loaded_model = TrainedModel.load(str(model_path))

            # 7. 用加载的模型预测
            result2 = loaded_model.predict(stock_codes, sample_market_data, date)
            assert isinstance(result2, pd.DataFrame)
            assert len(result2) == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
