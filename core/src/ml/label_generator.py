"""
标签生成器
对齐文档: core/docs/ml/README.md (阶段2)
"""
from typing import List, Literal
import pandas as pd
import numpy as np


LabelType = Literal['return', 'direction', 'classification', 'regression']


class LabelGenerator:
    """
    标签生成器

    支持多种标签类型:
    - 'return': 未来收益率 (回归任务)
    - 'direction': 涨跌方向 (二分类)
    - 'classification': 多分类 (涨/平/跌)
    - 'regression': 标准化收益率

    使用示例:
        >>> generator = LabelGenerator(
        ...     forward_window=5,
        ...     label_type='return'
        ... )
        >>> labels = generator.generate_labels(
        ...     stock_codes=['600000.SH', '000001.SZ'],
        ...     market_data=data,
        ...     date='2024-01-15'
        ... )
    """

    def __init__(
        self,
        forward_window: int = 5,
        label_type: LabelType = 'return',
        classification_thresholds: tuple = (-0.02, 0.02)
    ):
        """
        初始化标签生成器

        Args:
            forward_window: 前向窗口(天数)
            label_type: 标签类型
            classification_thresholds: 分类阈值 (下跌, 上涨)
        """
        self.forward_window = forward_window
        self.label_type = label_type
        self.classification_thresholds = classification_thresholds

    def generate_labels(
        self,
        stock_codes: List[str],
        market_data: pd.DataFrame,
        date: str
    ) -> pd.Series:
        """
        生成标签

        Args:
            stock_codes: 股票代码列表
            market_data: 市场数据
            date: 计算日期

        Returns:
            pd.Series: 标签序列
                - index: stock_codes
                - values: 标签值
        """
        labels = {}

        for stock in stock_codes:
            stock_data = market_data[
                market_data['stock_code'] == stock
            ].sort_values('date').reset_index(drop=True)

            # 找到当前日期
            current_mask = stock_data['date'] == pd.to_datetime(date)
            if not current_mask.any():
                continue

            current_idx = stock_data[current_mask].index[0]
            future_idx = current_idx + self.forward_window

            if future_idx >= len(stock_data):
                continue

            # 计算收益率
            current_price = stock_data.loc[current_idx, 'close']
            future_price = stock_data.loc[future_idx, 'close']

            if current_price == 0:
                continue

            return_value = (future_price - current_price) / current_price
            label = self._convert_label(return_value)
            labels[stock] = label

        return pd.Series(labels, name='label')

    def _convert_label(self, return_value: float) -> float:
        """将收益率转换为标签"""
        if self.label_type == 'return':
            return return_value

        elif self.label_type == 'direction':
            return 1.0 if return_value > 0 else 0.0

        elif self.label_type == 'classification':
            lower, upper = self.classification_thresholds
            if return_value < lower:
                return 0.0  # 下跌
            elif return_value > upper:
                return 2.0  # 上涨
            else:
                return 1.0  # 横盘

        elif self.label_type == 'regression':
            return return_value

        else:
            raise ValueError(f"Unknown label_type: {self.label_type}")

    def generate_multi_horizon_labels(
        self,
        stock_codes: List[str],
        market_data: pd.DataFrame,
        date: str,
        horizons: List[int] = [1, 3, 5, 10, 20]
    ) -> pd.DataFrame:
        """
        生成多个时间窗口的标签

        Args:
            stock_codes: 股票代码列表
            market_data: 市场数据
            date: 计算日期
            horizons: 时间窗口列表

        Returns:
            pd.DataFrame: 多窗口标签
                columns: ['label_1d', 'label_3d', 'label_5d', ...]
        """
        result = pd.DataFrame(index=stock_codes)

        for horizon in horizons:
            temp_gen = LabelGenerator(
                forward_window=horizon,
                label_type=self.label_type,
                classification_thresholds=self.classification_thresholds
            )

            labels = temp_gen.generate_labels(
                stock_codes, market_data, date
            )
            result[f'label_{horizon}d'] = labels

        return result
