"""
信号生成器模块

提供通用的信号生成工具函数
"""

from enum import Enum
from typing import List, Optional, Callable
import pandas as pd
import numpy as np
from loguru import logger

from src.utils.response import Response


class SignalType(Enum):
    """信号类型枚举"""
    BUY = 1  # 买入信号
    HOLD = 0  # 持有信号
    SELL = -1  # 卖出信号


class SignalGenerator:
    """
    信号生成器

    提供多种常用的信号生成方法：
    - 阈值信号
    - 排名信号
    - 交叉信号
    - 趋势信号
    """

    @staticmethod
    def generate_threshold_signals(
        scores: pd.DataFrame,
        buy_threshold: float,
        sell_threshold: Optional[float] = None
    ) -> Response:
        """
        基于阈值生成信号

        Args:
            scores: 评分DataFrame (index=date, columns=stock_codes)
            buy_threshold: 买入阈值（评分 > 阈值 则买入）
            sell_threshold: 卖出阈值（评分 < 阈值 则卖出，默认为买入阈值）

        Returns:
            Response对象，包含信号DataFrame
        """
        try:
            if scores.empty:
                return Response.error(
                    error="评分数据为空",
                    error_code="EMPTY_SCORES",
                    signal_type="threshold"
                )

            if sell_threshold is None:
                sell_threshold = buy_threshold

            signals = pd.DataFrame(
                SignalType.HOLD.value,
                index=scores.index,
                columns=scores.columns
            )

            # 买入信号
            signals[scores > buy_threshold] = SignalType.BUY.value

            # 卖出信号
            signals[scores < sell_threshold] = SignalType.SELL.value

            n_buy = (signals == SignalType.BUY.value).sum().sum()
            n_sell = (signals == SignalType.SELL.value).sum().sum()
            n_hold = (signals == SignalType.HOLD.value).sum().sum()

            return Response.success(
                data=signals,
                message="阈值信号生成完成",
                signal_type="threshold",
                buy_threshold=buy_threshold,
                sell_threshold=sell_threshold,
                n_buy=int(n_buy),
                n_sell=int(n_sell),
                n_hold=int(n_hold)
            )

        except Exception as e:
            logger.error(f"阈值信号生成失败: {str(e)}")
            return Response.error(
                error=f"阈值信号生成失败: {str(e)}",
                error_code="SIGNAL_GENERATION_ERROR",
                signal_type="threshold",
                exception_type=type(e).__name__
            )

    @staticmethod
    def generate_rank_signals(
        scores: pd.DataFrame,
        top_n: int,
        bottom_n: Optional[int] = None
    ) -> Response:
        """
        基于排名生成信号

        选择评分最高的 top_n 只股票买入

        Args:
            scores: 评分DataFrame
            top_n: 买入前N只
            bottom_n: 卖出后N只（可选，用于做空）

        Returns:
            Response对象，包含信号DataFrame
        """
        try:
            if scores.empty:
                return Response.error(
                    error="评分数据为空",
                    error_code="EMPTY_SCORES",
                    signal_type="rank"
                )

            signals = pd.DataFrame(
                SignalType.HOLD.value,
                index=scores.index,
                columns=scores.columns
            )

            for date in scores.index:
                date_scores = scores.loc[date].dropna()

                if len(date_scores) == 0:
                    continue

                # 买入信号：选择评分最高的 top_n 只
                top_stocks = date_scores.nlargest(top_n).index
                signals.loc[date, top_stocks] = SignalType.BUY.value

                # 卖出信号：选择评分最低的 bottom_n 只（如果指定）
                if bottom_n is not None and bottom_n > 0:
                    bottom_stocks = date_scores.nsmallest(bottom_n).index
                    signals.loc[date, bottom_stocks] = SignalType.SELL.value

            n_buy = (signals == SignalType.BUY.value).sum().sum()
            n_sell = (signals == SignalType.SELL.value).sum().sum()

            return Response.success(
                data=signals,
                message="排名信号生成完成",
                signal_type="rank",
                top_n=top_n,
                bottom_n=bottom_n if bottom_n is not None else 0,
                n_buy=int(n_buy),
                n_sell=int(n_sell)
            )

        except Exception as e:
            logger.error(f"排名信号生成失败: {str(e)}")
            return Response.error(
                error=f"排名信号生成失败: {str(e)}",
                error_code="SIGNAL_GENERATION_ERROR",
                signal_type="rank",
                exception_type=type(e).__name__
            )

    @staticmethod
    def generate_cross_signals(
        fast_line: pd.DataFrame,
        slow_line: pd.DataFrame,
        method: str = 'golden'
    ) -> Response:
        """
        基于双线交叉生成信号

        Args:
            fast_line: 快线DataFrame (如短期均线)
            slow_line: 慢线DataFrame (如长期均线)
            method: 交叉方法
                - 'golden': 金叉买入，死叉卖出
                - 'death': 死叉买入，金叉卖出（反向）

        Returns:
            Response对象，包含信号DataFrame
        """
        try:
            if fast_line.empty or slow_line.empty:
                return Response.error(
                    error="快线或慢线数据为空",
                    error_code="EMPTY_DATA",
                    signal_type="cross"
                )

            if fast_line.shape != slow_line.shape:
                return Response.error(
                    error="快线和慢线形状不匹配",
                    error_code="SHAPE_MISMATCH",
                    signal_type="cross",
                    fast_shape=fast_line.shape,
                    slow_shape=slow_line.shape
                )

            if method not in ['golden', 'death']:
                return Response.error(
                    error=f"不支持的交叉方法: {method}",
                    error_code="INVALID_METHOD",
                    signal_type="cross",
                    method=method,
                    valid_methods=['golden', 'death']
                )

            signals = pd.DataFrame(
                SignalType.HOLD.value,
                index=fast_line.index,
                columns=fast_line.columns
            )

            # 计算交叉
            # 金叉: 快线从下方穿越慢线
            golden_cross = (fast_line > slow_line) & (fast_line.shift(1) <= slow_line.shift(1))

            # 死叉: 快线从上方穿越慢线
            death_cross = (fast_line < slow_line) & (fast_line.shift(1) >= slow_line.shift(1))

            if method == 'golden':
                # 金叉买入，死叉卖出
                signals[golden_cross] = SignalType.BUY.value
                signals[death_cross] = SignalType.SELL.value
            elif method == 'death':
                # 反向操作
                signals[death_cross] = SignalType.BUY.value
                signals[golden_cross] = SignalType.SELL.value

            n_golden = golden_cross.sum().sum()
            n_death = death_cross.sum().sum()
            n_buy = (signals == SignalType.BUY.value).sum().sum()
            n_sell = (signals == SignalType.SELL.value).sum().sum()

            return Response.success(
                data=signals,
                message="交叉信号生成完成",
                signal_type="cross",
                method=method,
                n_golden_cross=int(n_golden),
                n_death_cross=int(n_death),
                n_buy=int(n_buy),
                n_sell=int(n_sell)
            )

        except Exception as e:
            logger.error(f"交叉信号生成失败: {str(e)}")
            return Response.error(
                error=f"交叉信号生成失败: {str(e)}",
                error_code="SIGNAL_GENERATION_ERROR",
                signal_type="cross",
                exception_type=type(e).__name__
            )

    @staticmethod
    def generate_trend_signals(
        prices: pd.DataFrame,
        lookback_period: int = 20,
        threshold: float = 0.0
    ) -> Response:
        """
        基于趋势生成信号

        Args:
            prices: 价格DataFrame
            lookback_period: 回看期
            threshold: 趋势阈值（收益率 > threshold 则认为上涨趋势）

        Returns:
            Response对象，包含信号DataFrame
        """
        try:
            if prices.empty:
                return Response.error(
                    error="价格数据为空",
                    error_code="EMPTY_PRICES",
                    signal_type="trend"
                )

            if lookback_period <= 0:
                return Response.error(
                    error="回看期必须大于0",
                    error_code="INVALID_LOOKBACK_PERIOD",
                    signal_type="trend",
                    lookback_period=lookback_period
                )

            if len(prices) < lookback_period:
                return Response.error(
                    error=f"数据长度 ({len(prices)}) 小于回看期 ({lookback_period})",
                    error_code="INSUFFICIENT_DATA",
                    signal_type="trend",
                    data_length=len(prices),
                    lookback_period=lookback_period
                )

            # 计算趋势（N日收益率）
            returns = prices.pct_change(lookback_period)

            signals = pd.DataFrame(
                SignalType.HOLD.value,
                index=prices.index,
                columns=prices.columns
            )

            # 上涨趋势 -> 买入
            signals[returns > threshold] = SignalType.BUY.value

            # 下跌趋势 -> 卖出
            signals[returns < -threshold] = SignalType.SELL.value

            n_buy = (signals == SignalType.BUY.value).sum().sum()
            n_sell = (signals == SignalType.SELL.value).sum().sum()
            n_hold = (signals == SignalType.HOLD.value).sum().sum()

            return Response.success(
                data=signals,
                message="趋势信号生成完成",
                signal_type="trend",
                lookback_period=lookback_period,
                threshold=threshold,
                n_buy=int(n_buy),
                n_sell=int(n_sell),
                n_hold=int(n_hold)
            )

        except Exception as e:
            logger.error(f"趋势信号生成失败: {str(e)}")
            return Response.error(
                error=f"趋势信号生成失败: {str(e)}",
                error_code="SIGNAL_GENERATION_ERROR",
                signal_type="trend",
                exception_type=type(e).__name__
            )

    @staticmethod
    def generate_breakout_signals(
        prices: pd.DataFrame,
        lookback_period: int = 20,
        threshold: float = 0.0
    ) -> Response:
        """
        基于突破生成信号

        突破新高 -> 买入
        跌破新低 -> 卖出

        Args:
            prices: 价格DataFrame
            lookback_period: 回看期
            threshold: 突破阈值（0.01 表示需要突破1%才算有效）

        Returns:
            Response对象，包含信号DataFrame
        """
        try:
            if prices.empty:
                return Response.error(
                    error="价格数据为空",
                    error_code="EMPTY_PRICES",
                    signal_type="breakout"
                )

            if lookback_period <= 0:
                return Response.error(
                    error="回看期必须大于0",
                    error_code="INVALID_LOOKBACK_PERIOD",
                    signal_type="breakout",
                    lookback_period=lookback_period
                )

            if len(prices) < lookback_period:
                return Response.error(
                    error=f"数据长度 ({len(prices)}) 小于回看期 ({lookback_period})",
                    error_code="INSUFFICIENT_DATA",
                    signal_type="breakout",
                    data_length=len(prices),
                    lookback_period=lookback_period
                )

            # 计算历史最高价和最低价
            rolling_high = prices.rolling(window=lookback_period).max()
            rolling_low = prices.rolling(window=lookback_period).min()

            signals = pd.DataFrame(
                SignalType.HOLD.value,
                index=prices.index,
                columns=prices.columns
            )

            # 突破新高 -> 买入
            # 使用shift(1)来比较当前价格与前一期的最高价
            breakout_high = prices > rolling_high.shift(1) * (1 + threshold)
            signals[breakout_high] = SignalType.BUY.value

            # 跌破新低 -> 卖出
            breakout_low = prices < rolling_low.shift(1) * (1 - threshold)
            signals[breakout_low] = SignalType.SELL.value

            n_breakout_high = breakout_high.sum().sum()
            n_breakout_low = breakout_low.sum().sum()
            n_buy = (signals == SignalType.BUY.value).sum().sum()
            n_sell = (signals == SignalType.SELL.value).sum().sum()

            return Response.success(
                data=signals,
                message="突破信号生成完成",
                signal_type="breakout",
                lookback_period=lookback_period,
                threshold=threshold,
                n_breakout_high=int(n_breakout_high),
                n_breakout_low=int(n_breakout_low),
                n_buy=int(n_buy),
                n_sell=int(n_sell)
            )

        except Exception as e:
            logger.error(f"突破信号生成失败: {str(e)}")
            return Response.error(
                error=f"突破信号生成失败: {str(e)}",
                error_code="SIGNAL_GENERATION_ERROR",
                signal_type="breakout",
                exception_type=type(e).__name__
            )

    @staticmethod
    def combine_signals(
        signal_list: List[pd.DataFrame],
        weights: Optional[List[float]] = None,
        method: str = 'vote'
    ) -> Response:
        """
        组合多个信号

        Args:
            signal_list: 信号DataFrame列表
            weights: 权重列表（可选）
            method: 组合方法
                - 'vote': 投票法（多数决定）
                - 'weighted': 加权平均
                - 'and': 全部同意才买入
                - 'or': 任意一个同意就买入

        Returns:
            Response对象，包含组合后的信号DataFrame
        """
        try:
            if not signal_list:
                return Response.error(
                    error="信号列表不能为空",
                    error_code="EMPTY_SIGNAL_LIST",
                    signal_type="combined"
                )

            # 确保所有信号形状一致
            base_shape = signal_list[0].shape
            for i, sig in enumerate(signal_list):
                if sig.shape != base_shape:
                    return Response.error(
                        error=f"信号{i}的形状与第一个信号不一致",
                        error_code="SHAPE_MISMATCH",
                        signal_type="combined",
                        base_shape=base_shape,
                        signal_index=i,
                        signal_shape=sig.shape
                    )

            if weights is None:
                weights = [1.0] * len(signal_list)

            if len(weights) != len(signal_list):
                return Response.error(
                    error="权重列表长度必须与信号列表长度一致",
                    error_code="WEIGHT_LENGTH_MISMATCH",
                    signal_type="combined",
                    n_signals=len(signal_list),
                    n_weights=len(weights)
                )

            valid_methods = ['vote', 'weighted', 'and', 'or']
            if method not in valid_methods:
                return Response.error(
                    error=f"不支持的组合方法: {method}",
                    error_code="INVALID_METHOD",
                    signal_type="combined",
                    method=method,
                    valid_methods=valid_methods
                )

            combined = pd.DataFrame(
                0.0,
                index=signal_list[0].index,
                columns=signal_list[0].columns
            )

            if method == 'vote':
                # 投票法：统计买入/卖出信号数量
                for sig in signal_list:
                    combined += sig

                # 归一化到 [-1, 0, 1]
                combined[combined > 0] = SignalType.BUY.value
                combined[combined < 0] = SignalType.SELL.value
                combined[combined == 0] = SignalType.HOLD.value

            elif method == 'weighted':
                # 加权平均
                for sig, weight in zip(signal_list, weights):
                    combined += sig * weight

                # 归一化
                total_weight = sum(weights)
                combined = combined / total_weight

                # 阈值化
                combined[combined > 0.5] = SignalType.BUY.value
                combined[combined < -0.5] = SignalType.SELL.value
                combined[(combined >= -0.5) & (combined <= 0.5)] = SignalType.HOLD.value

            elif method == 'and':
                # AND 逻辑：全部同意才买入
                combined = signal_list[0].copy()
                for sig in signal_list[1:]:
                    # 只有当前信号和新信号都是买入时，才保留买入信号
                    combined = combined.where(
                        (combined == SignalType.BUY.value) & (sig == SignalType.BUY.value),
                        SignalType.HOLD.value
                    )

            elif method == 'or':
                # OR 逻辑：任意一个同意就买入
                for sig in signal_list:
                    combined[sig == SignalType.BUY.value] = SignalType.BUY.value

            n_buy = (combined == SignalType.BUY.value).sum().sum()
            n_sell = (combined == SignalType.SELL.value).sum().sum()
            n_hold = (combined == SignalType.HOLD.value).sum().sum()

            return Response.success(
                data=combined,
                message="信号组合完成",
                signal_type="combined",
                method=method,
                n_input_signals=len(signal_list),
                weights=weights,
                n_buy=int(n_buy),
                n_sell=int(n_sell),
                n_hold=int(n_hold)
            )

        except Exception as e:
            logger.error(f"信号组合失败: {str(e)}")
            return Response.error(
                error=f"信号组合失败: {str(e)}",
                error_code="SIGNAL_COMBINATION_ERROR",
                signal_type="combined",
                exception_type=type(e).__name__
            )

    @staticmethod
    def apply_filter(
        signals: pd.DataFrame,
        filter_fn: Callable[[pd.DataFrame], pd.DataFrame]
    ) -> Response:
        """
        应用自定义过滤函数

        Args:
            signals: 原始信号DataFrame
            filter_fn: 过滤函数 (接收 signals, 返回过滤后的 signals)

        Returns:
            Response对象，包含过滤后的信号DataFrame
        """
        try:
            if signals.empty:
                return Response.error(
                    error="信号数据为空",
                    error_code="EMPTY_SIGNALS",
                    signal_type="filtered"
                )

            if filter_fn is None:
                return Response.error(
                    error="过滤函数不能为空",
                    error_code="EMPTY_FILTER_FUNCTION",
                    signal_type="filtered"
                )

            # 记录原始信号统计
            n_buy_before = (signals == SignalType.BUY.value).sum().sum()
            n_sell_before = (signals == SignalType.SELL.value).sum().sum()

            # 应用过滤函数
            filtered = filter_fn(signals)

            # 记录过滤后信号统计
            n_buy_after = (filtered == SignalType.BUY.value).sum().sum()
            n_sell_after = (filtered == SignalType.SELL.value).sum().sum()
            n_hold = (filtered == SignalType.HOLD.value).sum().sum()

            return Response.success(
                data=filtered,
                message="信号过滤完成",
                signal_type="filtered",
                n_buy_before=int(n_buy_before),
                n_sell_before=int(n_sell_before),
                n_buy_after=int(n_buy_after),
                n_sell_after=int(n_sell_after),
                n_hold=int(n_hold),
                buy_reduction=int(n_buy_before - n_buy_after),
                sell_reduction=int(n_sell_before - n_sell_after)
            )

        except Exception as e:
            logger.error(f"信号过滤失败: {str(e)}")
            return Response.error(
                error=f"信号过滤失败: {str(e)}",
                error_code="SIGNAL_FILTER_ERROR",
                signal_type="filtered",
                exception_type=type(e).__name__
            )


# ==================== 使用示例 ====================

if __name__ == "__main__":
    logger.info("信号生成器模块测试\n")

    # 创建测试数据
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    stocks = [f'{i:06d}' for i in range(600000, 600010)]

    # 模拟评分数据
    np.random.seed(42)
    scores_data = np.random.randn(len(dates), len(stocks))
    scores = pd.DataFrame(scores_data, index=dates, columns=stocks)

    # 模拟价格数据
    price_data = 10 * (1 + np.random.randn(len(dates), len(stocks)) * 0.02).cumprod(axis=0)
    prices = pd.DataFrame(price_data, index=dates, columns=stocks)

    # 1. 测试排名信号
    logger.info("1. 测试排名信号:")
    rank_response = SignalGenerator.generate_rank_signals(scores, top_n=3)
    if rank_response.is_success():
        rank_signals = rank_response.data
        logger.info(f"   买入信号数量: {rank_response.metadata['n_buy']}")
    else:
        logger.error(f"   失败: {rank_response.error}")

    # 2. 测试阈值信号
    logger.info("\n2. 测试阈值信号:")
    threshold_response = SignalGenerator.generate_threshold_signals(
        scores, buy_threshold=0.5, sell_threshold=-0.5
    )
    if threshold_response.is_success():
        threshold_signals = threshold_response.data
        logger.info(f"   买入信号: {threshold_response.metadata['n_buy']}")
        logger.info(f"   卖出信号: {threshold_response.metadata['n_sell']}")
    else:
        logger.error(f"   失败: {threshold_response.error}")

    # 3. 测试趋势信号
    logger.info("\n3. 测试趋势信号:")
    trend_response = SignalGenerator.generate_trend_signals(prices, lookback_period=10)
    if trend_response.is_success():
        trend_signals = trend_response.data
        logger.info(f"   买入信号: {trend_response.metadata['n_buy']}")
    else:
        logger.error(f"   失败: {trend_response.error}")

    # 4. 测试信号组合
    logger.info("\n4. 测试信号组合:")
    combined_response = SignalGenerator.combine_signals(
        [rank_signals, threshold_signals, trend_signals],
        method='vote'
    )
    if combined_response.is_success():
        combined = combined_response.data
        logger.info(f"   组合后买入信号: {combined_response.metadata['n_buy']}")
    else:
        logger.error(f"   失败: {combined_response.error}")

    logger.success("\n✓ 信号生成器测试完成")
