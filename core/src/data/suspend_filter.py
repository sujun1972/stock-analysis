"""
停牌股票过滤器 - 识别和过滤停牌股票数据

功能：
- 检测成交量为0的停牌股票
- 检测价格连续不变的停牌股票
- 检测涨跌停板
- 过滤停牌期间的数据
- 生成停牌统计报告

作者: AI Assistant
日期: 2026-01-30
"""

import pandas as pd
import numpy as np
from typing import Optional, Literal, Dict, List, Tuple, Any
from loguru import logger
from datetime import datetime


class SuspendFilter:
    """
    停牌股票过滤器 - 识别并过滤停牌股票

    停牌检测方法：
    1. 成交量为0或极小
    2. 价格连续多日不变
    3. 涨跌幅为0且成交量极小
    4. 同时满足多个条件

    用途：
    - 数据清洗（去除停牌期间数据）
    - 选股过滤（排除当前停牌股票）
    - 回测优化（避免买入停牌股票）
    """

    def __init__(
        self,
        df: pd.DataFrame = None,
        prices: pd.DataFrame = None,
        volumes: pd.DataFrame = None,
        price_col: str = 'close',
        volume_col: str = None
    ):
        """
        初始化停牌过滤器

        支持两种初始化方式：
        1. 单个DataFrame（包含价格和成交量列）
        2. 分离的价格和成交量DataFrame（多股票面板数据）

        参数：
            df: 单股票DataFrame（包含价格和成交量）
            prices: 价格DataFrame (index=date, columns=stock_codes)
            volumes: 成交量DataFrame (index=date, columns=stock_codes)
            price_col: 价格列名（单股票模式）
            volume_col: 成交量列名（单股票模式，自动检测）
        """
        self.single_stock_mode = df is not None

        if self.single_stock_mode:
            # 单股票模式
            self.df = df.copy()
            self.price_col = price_col

            # 检测成交量列
            if volume_col is None:
                if 'volume' in df.columns:
                    self.volume_col = 'volume'
                elif 'vol' in df.columns:
                    self.volume_col = 'vol'
                else:
                    self.volume_col = None
                    logger.warning("未找到成交量列，部分功能将不可用")
            else:
                self.volume_col = volume_col

            logger.debug(f"单股票模式: 价格列={price_col}, 成交量列={self.volume_col}")

        else:
            # 多股票模式
            if prices is None:
                raise ValueError("多股票模式需要提供 prices DataFrame")

            self.prices = prices.copy()
            self.volumes = volumes.copy() if volumes is not None else None

            if self.volumes is None:
                logger.warning("未提供成交量数据，部分功能将不可用")

            logger.debug(
                f"多股票模式: 股票数={len(prices.columns)}, "
                f"日期范围={prices.index[0]} 到 {prices.index[-1]}"
            )

    def detect_zero_volume(
        self,
        threshold: float = 100
    ) -> pd.Series | pd.DataFrame:
        """
        检测成交量为0或极小的停牌

        参数：
            threshold: 成交量阈值（默认100股）

        返回：
            布尔序列/DataFrame，True表示停牌
        """
        if self.single_stock_mode:
            # 单股票模式
            if self.volume_col is None:
                logger.warning("缺少成交量列，无法检测零成交量停牌")
                return pd.Series(False, index=self.df.index)

            zero_vol = (self.df[self.volume_col] <= threshold) | self.df[self.volume_col].isna()

            suspended_count = zero_vol.sum()
            suspended_pct = (suspended_count / len(self.df)) * 100

            logger.info(
                f"零成交量检测: 停牌={suspended_count}天 ({suspended_pct:.2f}%), "
                f"阈值={threshold}"
            )

            return zero_vol

        else:
            # 多股票模式
            if self.volumes is None:
                logger.warning("缺少成交量数据，无法检测零成交量停牌")
                return pd.DataFrame(False, index=self.prices.index, columns=self.prices.columns)

            zero_vol = (self.volumes <= threshold) | self.volumes.isna()

            total_suspended = zero_vol.sum().sum()
            total_records = zero_vol.size
            suspended_pct = (total_suspended / total_records) * 100

            logger.info(
                f"零成交量检测: 停牌记录={total_suspended} ({suspended_pct:.2f}%), "
                f"阈值={threshold}"
            )

            return zero_vol

    def detect_price_unchanged(
        self,
        consecutive_days: int = 3,
        tolerance: float = 1e-6
    ) -> pd.Series | pd.DataFrame:
        """
        检测价格连续多日不变的停牌

        参数：
            consecutive_days: 连续不变天数阈值（默认3天）
            tolerance: 价格变化容忍度（处理浮点数精度问题）

        返回：
            布尔序列/DataFrame，True表示停牌
        """
        if self.single_stock_mode:
            # 单股票模式
            if self.price_col not in self.df.columns:
                logger.warning(f"缺少价格列 '{self.price_col}'")
                return pd.Series(False, index=self.df.index)

            prices = self.df[self.price_col]

            # 计算价格变化
            price_change = prices.diff().abs()

            # 检测连续N天价格不变
            unchanged = price_change <= tolerance

            # 滚动窗口检测连续天数
            suspended = unchanged.rolling(window=consecutive_days).sum() >= consecutive_days

            suspended_count = suspended.sum()
            suspended_pct = (suspended_count / len(self.df)) * 100

            logger.info(
                f"价格不变检测: 停牌={suspended_count}天 ({suspended_pct:.2f}%), "
                f"连续天数≥{consecutive_days}"
            )

            return suspended

        else:
            # 多股票模式
            price_change = self.prices.diff().abs()
            unchanged = price_change <= tolerance

            # 滚动窗口检测
            suspended = unchanged.rolling(window=consecutive_days).sum() >= consecutive_days

            total_suspended = suspended.sum().sum()
            total_records = suspended.size
            suspended_pct = (total_suspended / total_records) * 100

            logger.info(
                f"价格不变检测: 停牌记录={total_suspended} ({suspended_pct:.2f}%), "
                f"连续天数≥{consecutive_days}"
            )

            return suspended

    def detect_limit_move(
        self,
        limit_threshold: float = 0.095
    ) -> Dict[str, pd.Series | pd.DataFrame]:
        """
        检测涨跌停板

        A股涨跌停板：±10%（ST股票±5%）

        参数：
            limit_threshold: 涨跌停阈值（默认9.5%，考虑浮点数误差）

        返回：
            包含涨停和跌停标记的字典
        """
        if self.single_stock_mode:
            # 单股票模式
            if self.price_col not in self.df.columns:
                logger.warning(f"缺少价格列 '{self.price_col}'")
                return {
                    'upper_limit': pd.Series(False, index=self.df.index),
                    'lower_limit': pd.Series(False, index=self.df.index)
                }

            returns = self.df[self.price_col].pct_change()

            # 涨停: 涨幅 ≥ 9.5%
            upper_limit = returns >= limit_threshold

            # 跌停: 跌幅 ≤ -9.5%
            lower_limit = returns <= -limit_threshold

            upper_count = upper_limit.sum()
            lower_count = lower_limit.sum()

            logger.info(
                f"涨跌停检测: 涨停={upper_count}天, 跌停={lower_count}天, "
                f"阈值={limit_threshold*100:.1f}%"
            )

            return {
                'upper_limit': upper_limit,
                'lower_limit': lower_limit,
                'any_limit': upper_limit | lower_limit
            }

        else:
            # 多股票模式
            returns = self.prices.pct_change()

            upper_limit = returns >= limit_threshold
            lower_limit = returns <= -limit_threshold

            upper_count = upper_limit.sum().sum()
            lower_count = lower_limit.sum().sum()

            logger.info(
                f"涨跌停检测: 涨停={upper_count}次, 跌停={lower_count}次, "
                f"阈值={limit_threshold*100:.1f}%"
            )

            return {
                'upper_limit': upper_limit,
                'lower_limit': lower_limit,
                'any_limit': upper_limit | lower_limit
            }

    def detect_all_suspended(
        self,
        volume_threshold: float = 100,
        consecutive_days: int = 3,
        detect_limit: bool = False
    ) -> pd.DataFrame | Dict[str, pd.DataFrame]:
        """
        综合检测所有类型的停牌

        参数：
            volume_threshold: 成交量阈值
            consecutive_days: 价格不变天数
            detect_limit: 是否检测涨跌停

        返回：
            包含各类停牌标记的DataFrame（单股票模式）
            或 包含 'suspended' 和 'limit' DataFrame的字典（多股票模式）
        """
        logger.info("开始综合停牌检测...")

        # 1. 零成交量停牌
        zero_vol = self.detect_zero_volume(threshold=volume_threshold)

        # 2. 价格不变停牌
        price_unchanged = self.detect_price_unchanged(consecutive_days=consecutive_days)

        # 3. 合并停牌标记（满足任一条件即为停牌）
        if self.single_stock_mode:
            suspended_df = pd.DataFrame({
                'zero_volume': zero_vol,
                'price_unchanged': price_unchanged,
                'is_suspended': zero_vol | price_unchanged
            }, index=self.df.index)

            # 4. 涨跌停检测（可选）
            if detect_limit:
                limit_dict = self.detect_limit_move()
                suspended_df['upper_limit'] = limit_dict['upper_limit']
                suspended_df['lower_limit'] = limit_dict['lower_limit']

            total_suspended = suspended_df['is_suspended'].sum()
            total_pct = (total_suspended / len(self.df)) * 100

            logger.info(f"综合停牌检测完成: 停牌={total_suspended}天 ({total_pct:.2f}%)")

            return suspended_df

        else:
            # 多股票模式
            is_suspended = zero_vol | price_unchanged

            total_suspended = is_suspended.sum().sum()
            total_records = is_suspended.size
            suspended_pct = (total_suspended / total_records) * 100

            logger.info(
                f"综合停牌检测完成: 停牌记录={total_suspended} ({suspended_pct:.2f}%)"
            )

            result = {
                'zero_volume': zero_vol,
                'price_unchanged': price_unchanged,
                'is_suspended': is_suspended
            }

            # 涨跌停检测（可选）
            if detect_limit:
                limit_dict = self.detect_limit_move()
                result['upper_limit'] = limit_dict['upper_limit']
                result['lower_limit'] = limit_dict['lower_limit']

            return result

    def get_suspension_periods(
        self,
        suspended: pd.Series,
        min_duration: int = 3
    ) -> List[Tuple[datetime, datetime, int]]:
        """
        获取停牌期间列表（单股票模式）

        参数：
            suspended: 停牌标记布尔序列
            min_duration: 最小停牌天数（过滤短期停牌）

        返回：
            停牌期间列表: [(开始日期, 结束日期, 天数), ...]
        """
        if not self.single_stock_mode:
            logger.warning("多股票模式不支持此方法")
            return []

        periods = []
        in_suspension = False
        start_date = None

        for date, is_suspended in suspended.items():
            if is_suspended and not in_suspension:
                # 进入停牌期
                in_suspension = True
                start_date = date
            elif not is_suspended and in_suspension:
                # 退出停牌期
                in_suspension = False
                duration = len(pd.date_range(start_date, date, freq='D')) - 1

                if duration >= min_duration:
                    periods.append((start_date, date, duration))

        # 处理最后一个停牌期（如果仍在停牌中）
        if in_suspension:
            end_date = suspended.index[-1]
            duration = len(pd.date_range(start_date, end_date, freq='D'))
            if duration >= min_duration:
                periods.append((start_date, end_date, duration))

        logger.info(f"识别到 {len(periods)} 个停牌期间（≥{min_duration}天）")

        return periods

    def get_suspension_summary(
        self,
        suspended_df: pd.DataFrame | Dict[str, pd.DataFrame]
    ) -> Dict[str, any]:
        """
        获取停牌统计摘要

        参数：
            suspended_df: detect_all_suspended() 返回的结果

        返回：
            摘要统计字典
        """
        if self.single_stock_mode:
            # 单股票模式
            summary = {
                'total_days': len(self.df),
                'suspended_days': int(suspended_df['is_suspended'].sum()),
                'suspension_rate': round(
                    (suspended_df['is_suspended'].sum() / len(self.df)) * 100, 2
                ),
                'by_type': {
                    'zero_volume': int(suspended_df['zero_volume'].sum()),
                    'price_unchanged': int(suspended_df['price_unchanged'].sum())
                }
            }

            # 停牌期间
            periods = self.get_suspension_periods(suspended_df['is_suspended'])
            if periods:
                summary['suspension_periods'] = len(periods)
                summary['longest_suspension'] = max(periods, key=lambda x: x[2])
                summary['average_suspension_days'] = round(
                    sum(p[2] for p in periods) / len(periods), 1
                )

            return summary

        else:
            # 多股票模式
            is_suspended = suspended_df['is_suspended']

            summary = {
                'total_records': is_suspended.size,
                'suspended_records': int(is_suspended.sum().sum()),
                'suspension_rate': round(
                    (is_suspended.sum().sum() / is_suspended.size) * 100, 2
                ),
                'stocks': len(is_suspended.columns),
                'by_stock': {}
            }

            # 各股票停牌统计
            for stock in is_suspended.columns:
                suspended_count = is_suspended[stock].sum()
                suspended_pct = (suspended_count / len(is_suspended)) * 100

                summary['by_stock'][stock] = {
                    'suspended_days': int(suspended_count),
                    'suspension_rate': round(suspended_pct, 2)
                }

            return summary

    # ==================== 数据过滤方法 ====================

    def filter_suspended(
        self,
        suspended: pd.Series | pd.DataFrame,
        fill_value: any = np.nan
    ) -> pd.DataFrame:
        """
        过滤掉停牌期间的数据

        参数：
            suspended: 停牌标记（布尔序列/DataFrame）
            fill_value: 填充值（默认NaN）

        返回：
            过滤后的DataFrame
        """
        if self.single_stock_mode:
            # 单股票模式
            df_filtered = self.df.copy()

            # 将停牌期间的数据设为NaN
            for col in df_filtered.columns:
                df_filtered.loc[suspended, col] = fill_value

            filtered_count = suspended.sum()
            logger.info(f"停牌数据过滤: {filtered_count}天数据已过滤")

            return df_filtered

        else:
            # 多股票模式
            prices_filtered = self.prices.copy()

            # 将停牌期间的价格设为NaN
            prices_filtered[suspended] = fill_value

            filtered_count = suspended.sum().sum()
            logger.info(f"停牌数据过滤: {filtered_count}条记录已过滤")

            return prices_filtered

    def remove_suspended_rows(
        self,
        suspended: pd.Series
    ) -> pd.DataFrame:
        """
        完全移除停牌期间的行（单股票模式）

        参数：
            suspended: 停牌标记布尔序列

        返回：
            移除停牌行的DataFrame
        """
        if not self.single_stock_mode:
            logger.warning("多股票模式不支持移除行操作")
            return self.prices

        df_filtered = self.df[~suspended].copy()

        removed_count = suspended.sum()
        logger.info(f"移除停牌行: {removed_count}行已删除")

        return df_filtered


# ==================== 便捷函数 ====================


def detect_suspended_stocks(
    df: pd.DataFrame = None,
    prices: pd.DataFrame = None,
    volumes: pd.DataFrame = None,
    volume_threshold: float = 100,
    consecutive_days: int = 3
) -> pd.DataFrame | Dict[str, pd.DataFrame]:
    """
    便捷函数：快速检测停牌股票

    参数：
        df: 单股票DataFrame（二选一）
        prices: 价格DataFrame（多股票）
        volumes: 成交量DataFrame（多股票）
        volume_threshold: 成交量阈值
        consecutive_days: 价格不变天数

    返回：
        停牌标记DataFrame或字典
    """
    filter_obj = SuspendFilter(df=df, prices=prices, volumes=volumes)
    return filter_obj.detect_all_suspended(
        volume_threshold=volume_threshold,
        consecutive_days=consecutive_days
    )


def filter_suspended_data(
    df: pd.DataFrame = None,
    prices: pd.DataFrame = None,
    volumes: pd.DataFrame = None,
    volume_threshold: float = 100,
    consecutive_days: int = 3,
    fill_value: any = np.nan
) -> pd.DataFrame:
    """
    便捷函数：一键检测并过滤停牌数据

    参数：
        df: 单股票DataFrame
        prices: 价格DataFrame（多股票）
        volumes: 成交量DataFrame（多股票）
        volume_threshold: 成交量阈值
        consecutive_days: 价格不变天数
        fill_value: 填充值

    返回：
        过滤后的DataFrame
    """
    filter_obj = SuspendFilter(df=df, prices=prices, volumes=volumes)

    # 检测停牌
    suspended_result = filter_obj.detect_all_suspended(
        volume_threshold=volume_threshold,
        consecutive_days=consecutive_days
    )

    # 提取停牌标记
    if isinstance(suspended_result, dict):
        suspended = suspended_result['is_suspended']
    else:
        suspended = suspended_result['is_suspended']

    # 过滤数据
    return filter_obj.filter_suspended(suspended, fill_value=fill_value)


# ==================== 使用示例 ====================


if __name__ == "__main__":
    # 创建测试数据
    dates = pd.date_range('2023-01-01', periods=100, freq='D')

    np.random.seed(42)
    base_price = 100
    returns = np.random.normal(0.001, 0.02, 100)
    prices = base_price * (1 + returns).cumprod()

    # 模拟停牌: 第20-25天停牌（价格不变，成交量为0）
    prices[20:26] = prices[19]

    volumes = np.random.uniform(1000000, 10000000, 100)
    volumes[20:26] = 0  # 停牌期间成交量为0

    test_df = pd.DataFrame({
        'close': prices,
        'volume': volumes
    }, index=dates)

    print("=" * 60)
    print("停牌股票过滤器测试")
    print("=" * 60)

    # 1. 检测停牌
    filter_obj = SuspendFilter(test_df)
    suspended_df = filter_obj.detect_all_suspended()

    print(f"\n检测到 {suspended_df['is_suspended'].sum()} 天停牌")

    # 2. 获取停牌期间
    periods = filter_obj.get_suspension_periods(suspended_df['is_suspended'])
    print(f"\n停牌期间:")
    for start, end, days in periods:
        print(f"  {start.date()} 至 {end.date()}, 共 {days} 天")

    # 3. 停牌摘要
    summary = filter_obj.get_suspension_summary(suspended_df)
    print(f"\n停牌摘要: {summary}")

    # 4. 过滤停牌数据
    df_filtered = filter_obj.filter_suspended(suspended_df['is_suspended'])

    print(f"\n过滤前后对比:")
    print(f"原始数据: {len(test_df)} 行")
    print(f"过滤后NaN数量: {df_filtered.isnull().sum().sum()}")

    print("\n测试完成！")
