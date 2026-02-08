"""
训练好的模型包装类
对齐文档: core/docs/ml/README.md (阶段2)

功能:
- 封装模型 + 特征引擎
- 提供统一的预测接口
- 支持模型保存和加载
- 自动估算波动率和置信度

版本: v1.0.0
创建时间: 2026-02-08
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
import joblib
from pathlib import Path

from src.ml.feature_engine import FeatureEngine


@dataclass
class TrainingConfig:
    """
    训练配置

    Attributes:
        model_type: 模型类型 ('lightgbm', 'xgboost', 'ridge', 'gru')
        train_start_date: 训练开始日期
        train_end_date: 训练结束日期
        validation_split: 验证集比例
        forward_window: 前向预测窗口(天数)
        feature_groups: 特征组列表 ['alpha', 'technical', 'volume', 'all']
        hyperparameters: 超参数字典
    """
    model_type: str = 'lightgbm'
    train_start_date: str = '2020-01-01'
    train_end_date: str = '2023-12-31'
    validation_split: float = 0.2
    forward_window: int = 5
    feature_groups: List[str] = field(default_factory=lambda: ['all'])
    hyperparameters: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """验证配置参数"""
        if self.model_type not in ['lightgbm', 'xgboost', 'ridge', 'gru', 'ensemble']:
            raise ValueError(f"Invalid model_type: {self.model_type}")

        if not 0 < self.validation_split < 1:
            raise ValueError(f"validation_split must be between 0 and 1, got {self.validation_split}")

        if self.forward_window <= 0:
            raise ValueError(f"forward_window must be positive, got {self.forward_window}")


class TrainedModel:
    """
    训练好的模型 (可保存和加载)

    封装:
    - model: 训练好的ML模型
    - feature_engine: 特征引擎
    - config: 训练配置
    - metrics: 评估指标

    使用示例:
        >>> # 训练后保存
        >>> model = TrainedModel(
        ...     model=lgb_model,
        ...     feature_engine=engine,
        ...     config=config,
        ...     metrics={'ic': 0.08, 'rank_ic': 0.12}
        ... )
        >>> model.save('models/my_model.pkl')

        >>> # 加载后预测
        >>> model = TrainedModel.load('models/my_model.pkl')
        >>> predictions = model.predict(
        ...     stock_codes=['600000.SH'],
        ...     market_data=data,
        ...     date='2024-01-15'
        ... )
    """

    def __init__(
        self,
        model: Any,
        feature_engine: FeatureEngine,
        config: TrainingConfig,
        metrics: Dict[str, float]
    ):
        """
        初始化

        Args:
            model: 训练好的模型实例 (必须实现 predict 方法)
            feature_engine: 特征引擎
            config: 训练配置
            metrics: 评估指标 (如 {'ic': 0.08, 'rank_ic': 0.12})
        """
        self.model = model
        self.feature_engine = feature_engine
        self.config = config
        self.metrics = metrics

        # 特征列名 (用于对齐特征)
        self.feature_columns: Optional[List[str]] = None

        # 验证模型接口
        if not hasattr(model, 'predict'):
            raise ValueError("Model must implement 'predict' method")

    def predict(
        self,
        stock_codes: List[str],
        market_data: pd.DataFrame,
        date: str
    ) -> pd.DataFrame:
        """
        预测

        Args:
            stock_codes: 股票代码列表
            market_data: 市场数据 (包含OHLCV)
            date: 预测日期 (格式: 'YYYY-MM-DD')

        Returns:
            pd.DataFrame:
                columns: ['expected_return', 'volatility', 'confidence']
                index: stock_codes

        Raises:
            ValueError: 如果日期格式无效或数据不足
        """
        # 1. 计算特征
        try:
            features = self.feature_engine.calculate_features(
                stock_codes, market_data, date
            )
        except Exception as e:
            raise ValueError(f"Failed to calculate features: {e}")

        # 2. 数据清洗
        features = features.fillna(0).replace([np.inf, -np.inf], 0)

        # 3. 对齐特征列
        if self.feature_columns is not None:
            # 添加缺失列
            missing_cols = set(self.feature_columns) - set(features.columns)
            for col in missing_cols:
                features[col] = 0

            # 确保列顺序一致
            features = features[self.feature_columns]

        # 4. 模型预测
        try:
            predictions = self.model.predict(features.values)
        except Exception as e:
            raise RuntimeError(f"Model prediction failed: {e}")

        # 5. 构建结果
        result = pd.DataFrame(index=features.index)
        result['expected_return'] = predictions
        result['volatility'] = self._estimate_volatility(
            stock_codes, market_data, date
        )
        result['confidence'] = self._estimate_confidence(features)

        return result

    def _estimate_volatility(
        self,
        stock_codes: List[str],
        market_data: pd.DataFrame,
        date: str,
        window: int = 20
    ) -> pd.Series:
        """
        估计波动率

        Args:
            stock_codes: 股票代码列表
            market_data: 市场数据
            date: 当前日期
            window: 计算窗口 (默认20天)

        Returns:
            pd.Series: 波动率序列 (index=stock_codes)
        """
        volatilities = {}
        end_date = pd.to_datetime(date)
        start_date = end_date - pd.Timedelta(days=window + 10)  # +10天缓冲

        for stock in stock_codes:
            stock_data = market_data[
                (market_data['stock_code'] == stock) &
                (market_data['date'] >= start_date) &
                (market_data['date'] <= end_date)
            ].sort_values('date')

            if len(stock_data) < window:
                # 数据不足,使用默认波动率
                volatilities[stock] = 0.02  # 2%
                continue

            # 计算收益率标准差
            returns = stock_data['close'].pct_change().dropna()
            volatilities[stock] = returns.std()

        return pd.Series(volatilities)

    def _estimate_confidence(
        self,
        features: pd.DataFrame
    ) -> pd.Series:
        """
        估计置信度

        基于特征完整度估算置信度:
        - 特征完整度越高,置信度越高
        - 置信度范围: [0.5, 1.0]

        Args:
            features: 特征矩阵

        Returns:
            pd.Series: 置信度序列 (index=stock_codes)
        """
        # 简单方法: 基于特征完整度
        completeness = 1.0 - features.isna().sum(axis=1) / len(features.columns)

        # 裁剪到合理范围
        return completeness.clip(0.5, 1.0)

    def set_feature_columns(self, columns: List[str]):
        """
        设置特征列名 (用于训练后固定特征顺序)

        Args:
            columns: 特征列名列表
        """
        self.feature_columns = columns

    def save(self, path: str):
        """
        保存模型到文件

        Args:
            path: 保存路径 (如 'models/my_model.pkl')

        Note:
            使用 joblib 进行序列化,支持大型模型
        """
        save_path = Path(path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        joblib.dump(self, path)
        print(f"✅ 模型已保存: {path}")
        print(f"   模型类型: {self.config.model_type}")
        print(f"   特征数量: {len(self.feature_columns) if self.feature_columns else 'N/A'}")
        print(f"   IC: {self.metrics.get('ic', 'N/A')}")

    @staticmethod
    def load(path: str) -> 'TrainedModel':
        """
        从文件加载模型

        Args:
            path: 模型路径

        Returns:
            TrainedModel: 加载的模型实例

        Raises:
            FileNotFoundError: 如果文件不存在
        """
        if not Path(path).exists():
            raise FileNotFoundError(f"模型不存在: {path}")

        model = joblib.load(path)

        # 验证类型
        if not isinstance(model, TrainedModel):
            raise TypeError(f"Loaded object is not TrainedModel, got {type(model)}")

        print(f"✅ 模型已加载: {path}")
        print(f"   模型类型: {model.config.model_type}")
        print(f"   训练时间: {model.config.train_start_date} ~ {model.config.train_end_date}")

        # 打印评估指标
        if model.metrics:
            print(f"   评估指标:")
            for key, value in model.metrics.items():
                if isinstance(value, (int, float)):
                    print(f"     - {key}: {value:.4f}")
                else:
                    print(f"     - {key}: {value}")

        return model

    def __repr__(self) -> str:
        """字符串表示"""
        ic = self.metrics.get('ic', 'N/A')
        return (
            f"TrainedModel("
            f"model_type={self.config.model_type}, "
            f"ic={ic}, "
            f"features={len(self.feature_columns) if self.feature_columns else 'N/A'}"
            f")"
        )
