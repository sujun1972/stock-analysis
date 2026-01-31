"""
机器学习策略模块

使用训练好的ML模型预测收益率并生成交易信号
"""

from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
from loguru import logger

from .base_strategy import BaseStrategy
from .signal_generator import SignalGenerator


class MLStrategy(BaseStrategy):
    """
    机器学习策略

    核心逻辑：
    - 使用训练好的模型预测未来收益率
    - 选择预测收益最高的股票买入

    参数：
        model: 已训练的模型（LightGBM/GRU/Ridge等）
        prediction_threshold: 预测阈值（默认0.01，即预测收益>1%才考虑）
        top_n: 选股数量
        use_probability: 是否使用预测概率（分类模型）

    适用场景：
        - 有足够历史数据训练模型
        - 特征工程充分
        - 需要非线性关系捕获

    注意事项：
        - 模型需要定期重训练
        - 注意过拟合风险
        - 特征需要与训练时保持一致
    """

    def __init__(self, name: str, config: Dict[str, Any], model=None):
        """
        初始化ML策略

        Args:
            name: 策略名称
            config: 策略配置
            model: 训练好的模型实例
        """
        default_config = {
            'prediction_threshold': 0.01,
            'top_n': 50,
            'holding_period': 5,
            'use_probability': False,
            'feature_columns': None,  # None表示使用所有列
        }
        default_config.update(config)

        super().__init__(name, default_config)

        self.model = model
        self.prediction_threshold = self.config.custom_params.get('prediction_threshold', 0.01)
        self.use_probability = self.config.custom_params.get('use_probability', False)
        self.feature_columns = self.config.custom_params.get('feature_columns')

        if self.model is None:
            logger.warning("未提供模型，需要后续设置")
        else:
            logger.info(f"ML策略使用模型: {type(self.model).__name__}")

    def set_model(self, model):
        """
        设置模型

        Args:
            model: 模型实例
        """
        self.model = model
        logger.info(f"设置模型: {type(model).__name__}")

    def predict(self, features: pd.DataFrame) -> pd.Series:
        """
        使用模型预测

        Args:
            features: 特征DataFrame

        Returns:
            predictions: 预测值Series
        """
        if self.model is None:
            raise ValueError("模型未设置，请先调用 set_model()")

        # 选择特征列
        if self.feature_columns is not None:
            X = features[self.feature_columns]
        else:
            X = features

        # 处理缺失值
        X = X.fillna(0)

        # 预测
        try:
            if self.use_probability and hasattr(self.model, 'predict_proba'):
                # 使用概率预测（分类模型）
                predictions = self.model.predict_proba(X)[:, 1]
            else:
                # 使用值预测（回归模型）
                predictions = self.model.predict(X)

            return pd.Series(predictions, index=features.index)

        except Exception as e:
            logger.error(f"模型预测失败: {e}")
            return pd.Series(np.nan, index=features.index)

    def calculate_scores(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        date: Optional[pd.Timestamp] = None
    ) -> pd.Series:
        """
        计算股票评分

        评分 = 模型预测的收益率

        Args:
            prices: 价格DataFrame
            features: 特征DataFrame（必需）
            date: 指定日期

        Returns:
            scores: 预测评分Series
        """
        if features is None:
            raise ValueError("ML策略需要特征DataFrame")

        if date is None:
            date = features.index[-1]

        if date not in features.index:
            logger.warning(f"日期 {date} 不在特征DataFrame中")
            return pd.Series(dtype=float)

        # 提取当日特征
        date_features = features.loc[date:date]

        # 预测
        predictions = self.predict(date_features)

        # 过滤低于阈值的预测
        predictions[predictions < self.prediction_threshold] = np.nan

        return predictions

    def generate_signals(
        self,
        prices: pd.DataFrame,
        features: Optional[pd.DataFrame] = None,
        volumes: Optional[pd.DataFrame] = None,
        **kwargs
    ) -> pd.DataFrame:
        """
        生成交易信号

        Args:
            prices: 价格DataFrame
            features: 特征DataFrame（必需）
            volumes: 成交量DataFrame
            **kwargs: 其他参数

        Returns:
            signals: 信号DataFrame
        """
        logger.info(f"\n生成ML策略信号...")

        if features is None:
            raise ValueError("ML策略需要特征DataFrame")

        if self.model is None:
            raise ValueError("模型未设置")

        # 1. 批量预测所有日期
        predictions_dict = {}
        for date in features.index:
            try:
                scores = self.calculate_scores(prices, features, date)
                predictions_dict[date] = scores
            except Exception as e:
                logger.warning(f"预测日期 {date} 失败: {e}")
                continue

        if not predictions_dict:
            logger.error("没有成功的预测")
            return pd.DataFrame(0, index=prices.index, columns=prices.columns)

        # 转换为DataFrame
        predictions_df = pd.DataFrame(predictions_dict).T

        # 2. 生成排名信号（返回Response对象）
        signals_response = SignalGenerator.generate_rank_signals(
            scores=predictions_df,
            top_n=self.config.top_n
        )

        # 检查信号生成结果并提取数据
        if not signals_response.is_success():
            raise ValueError(f"信号生成失败: {signals_response.error}")
        signals = signals_response.data

        # 3. 对齐索引
        signals = signals.reindex(prices.index, fill_value=0)

        # 4. 过滤
        if volumes is not None:
            for date in signals.index:
                try:
                    valid_stocks = self.filter_stocks(prices, volumes, date)
                    invalid_stocks = [s for s in signals.columns if s not in valid_stocks]
                    signals.loc[date, invalid_stocks] = 0
                except:
                    pass

        # 5. 验证
        signals = self.validate_signals(signals)

        logger.info(f"信号生成完成，总买入信号数: {(signals == 1).sum().sum()}")

        return signals


# ==================== 使用示例 ====================

if __name__ == "__main__":
    from sklearn.ensemble import RandomForestRegressor

    logger.info("ML策略测试\n")
    logger.info("=" * 60)

    # 创建测试数据
    np.random.seed(42)
    n_samples = 100
    n_features = 10

    # 模拟特征
    X_train = np.random.randn(n_samples, n_features)
    y_train = X_train[:, 0] * 0.1 + np.random.randn(n_samples) * 0.01  # 简单线性关系

    # 训练模型
    logger.info("训练模型...")
    model = RandomForestRegressor(n_estimators=10, random_state=42)
    model.fit(X_train, y_train)

    # 创建策略
    logger.info("\n创建ML策略:")
    config = {
        'prediction_threshold': 0.0,
        'top_n': 3,
        'holding_period': 5,
    }

    strategy = MLStrategy('ML_RF', config, model=model)

    # 测试预测
    X_test = np.random.randn(10, n_features)
    test_features = pd.DataFrame(X_test, columns=[f'feature_{i}' for i in range(n_features)])

    predictions = strategy.predict(test_features)
    logger.info(f"\n预测结果:")
    logger.info(predictions)

    logger.success("\n✓ ML策略测试完成")
