#!/usr/bin/env python3
"""
多策略回测对比示例

演示如何对比不同策略的表现，包括:
1. 动量策略 vs 反转策略
2. 单因子策略 vs 多因子策略
3. 机器学习策略 vs 传统策略
4. 策略组合优化

Author: Stock Analysis Core Team
Date: 2026-01-30
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from loguru import logger
from typing import Dict, List, Callable

from src.backtest import BacktestEngine, PerformanceAnalyzer


def create_sample_data(n_days=504, n_stocks=100):
    """
    创建示例数据（2年）

    参数:
        n_days: 交易日数（默认504天=2年）
        n_stocks: 股票数量

    返回:
        (prices_df, features_df): 价格和特征DataFrame
    """
    logger.info(f"生成示例数据: {n_days}天 x {n_stocks}只股票")

    np.random.seed(42)

    dates = pd.date_range('2022-01-01', periods=n_days, freq='D')
    stocks = [f'{600000+i:06d}' for i in range(n_stocks)]

    # 价格数据
    price_data = {}
    for i, stock in enumerate(stocks):
        base_price = 10.0 + i * 0.05
        # 一半股票有上涨趋势，一半下跌
        trend = 0.0003 if i < n_stocks // 2 else -0.0001
        returns = np.random.normal(trend, 0.015, n_days)
        prices = base_price * (1 + returns).cumprod()
        price_data[stock] = prices

    prices_df = pd.DataFrame(price_data, index=dates)

    # 特征数据（用于构建不同策略）
    features = {}

    # 动量特征
    features['MOM5'] = prices_df.pct_change(5)
    features['MOM10'] = prices_df.pct_change(10)
    features['MOM20'] = prices_df.pct_change(20)
    features['MOM60'] = prices_df.pct_change(60)

    # 反转特征（负动量）
    features['REV5'] = -features['MOM5']
    features['REV10'] = -features['MOM10']

    # 波动率特征
    features['VOL20'] = prices_df.pct_change().rolling(20).std()
    features['VOL60'] = prices_df.pct_change().rolling(60).std()

    # 成交量特征（模拟）
    volume_data = {}
    for stock in stocks:
        base_vol = 1000000 * (1 + np.random.rand())
        volumes = base_vol * (1 + np.random.randn(n_days) * 0.3)
        volumes = np.abs(volumes)
        volume_data[stock] = volumes

    volumes_df = pd.DataFrame(volume_data, index=dates)
    features['VOL_CHANGE'] = volumes_df.pct_change(5)

    logger.info(f"生成了 {len(features)} 个特征")

    return prices_df, features


class StrategyFactory:
    """策略工厂：创建不同的交易策略"""

    @staticmethod
    def momentum_strategy(features: Dict, lookback: int = 20) -> pd.DataFrame:
        """
        动量策略：买入过去表现好的股票

        参数:
            features: 特征字典
            lookback: 回看期

        返回:
            信号DataFrame
        """
        signal_key = f'MOM{lookback}'
        if signal_key in features:
            return features[signal_key].copy()
        else:
            raise ValueError(f"特征 {signal_key} 不存在")

    @staticmethod
    def reversal_strategy(features: Dict, lookback: int = 5) -> pd.DataFrame:
        """
        反转策略：买入过去表现差的股票（逆向投资）

        参数:
            features: 特征字典
            lookback: 回看期

        返回:
            信号DataFrame
        """
        signal_key = f'REV{lookback}'
        if signal_key in features:
            return features[signal_key].copy()
        else:
            raise ValueError(f"特征 {signal_key} 不存在")

    @staticmethod
    def low_volatility_strategy(features: Dict) -> pd.DataFrame:
        """
        低波动策略：买入波动率低的股票

        返回:
            信号DataFrame（波动率越低，信号越强）
        """
        vol = features['VOL20']
        # 波动率取负数（低波动=高信号）
        return -vol

    @staticmethod
    def multi_factor_strategy(
        features: Dict,
        factor_names: List[str],
        weights: List[float] = None
    ) -> pd.DataFrame:
        """
        多因子策略：组合多个因子

        参数:
            features: 特征字典
            factor_names: 因子名称列表
            weights: 因子权重（None=等权）

        返回:
            信号DataFrame
        """
        if weights is None:
            weights = [1.0 / len(factor_names)] * len(factor_names)

        # 因子标准化（横截面）
        normalized_factors = []
        for factor_name in factor_names:
            if factor_name not in features:
                raise ValueError(f"特征 {factor_name} 不存在")

            factor = features[factor_name]
            # 横截面排名（每天独立）
            factor_rank = factor.rank(axis=1, pct=True)
            normalized_factors.append(factor_rank)

        # 加权组合
        combined_signal = pd.DataFrame(0, index=features['MOM20'].index, columns=features['MOM20'].columns)
        for factor, weight in zip(normalized_factors, weights):
            combined_signal += factor * weight

        return combined_signal


def run_strategy_backtest(
    strategy_name: str,
    signals: pd.DataFrame,
    prices: pd.DataFrame,
    top_n: int = 30,
    rebalance_freq: str = 'W'
) -> Dict:
    """
    运行策略回测并返回结果

    参数:
        strategy_name: 策略名称
        signals: 信号数据
        prices: 价格数据
        top_n: 选股数量
        rebalance_freq: 调仓频率

    返回:
        回测结果字典
    """
    logger.info(f"\n回测策略: {strategy_name}")

    engine = BacktestEngine(
        initial_capital=1000000,
        commission_rate=0.0003,
        stamp_tax_rate=0.001,
        slippage=0.001,
        verbose=False
    )

    results = engine.backtest_long_only(
        signals=signals,
        prices=prices,
        top_n=top_n,
        holding_period=5,
        rebalance_freq=rebalance_freq
    )

    analyzer = PerformanceAnalyzer(
        returns=results['daily_returns'],
        risk_free_rate=0.03
    )
    metrics = analyzer.calculate_all_metrics(verbose=False)
    cost_metrics = results['cost_analysis']

    logger.info(f"  年化收益: {metrics['annualized_return']*100:.2f}%")
    logger.info(f"  夏普比率: {metrics['sharpe_ratio']:.3f}")
    logger.info(f"  最大回撤: {metrics['max_drawdown']*100:.2f}%")

    return {
        'name': strategy_name,
        'results': results,
        'metrics': metrics,
        'cost_metrics': cost_metrics
    }


def comparison1_momentum_vs_reversal():
    """
    对比1: 动量策略 vs 反转策略

    经典对比：趋势跟随 vs 均值回归
    """
    logger.info("\n" + "="*80)
    logger.info("对比1: 动量策略 vs 反转策略")
    logger.info("="*80)

    logger.info("\n策略说明:")
    logger.info("  动量策略: 买入过去表现好的股票（趋势跟随）")
    logger.info("  反转策略: 买入过去表现差的股票（均值回归）")

    # 准备数据
    prices, features = create_sample_data(n_days=504, n_stocks=100)

    # 创建策略
    factory = StrategyFactory()

    strategies = [
        ('MOM20（20日动量）', factory.momentum_strategy(features, lookback=20)),
        ('MOM60（60日动量）', factory.momentum_strategy(features, lookback=60)),
        ('REV5（5日反转）', factory.reversal_strategy(features, lookback=5)),
        ('REV10（10日反转）', factory.reversal_strategy(features, lookback=10)),
    ]

    # 回测所有策略
    backtest_results = []
    for name, signals in strategies:
        result = run_strategy_backtest(name, signals, prices, top_n=30, rebalance_freq='W')
        backtest_results.append(result)

    # 对比结果
    comparison = []
    for result in backtest_results:
        metrics = result['metrics']
        cost = result['cost_metrics']

        comparison.append({
            '策略': result['name'],
            '年化收益(%)': f"{metrics['annualized_return']*100:.2f}",
            '夏普比率': f"{metrics['sharpe_ratio']:.3f}",
            '最大回撤(%)': f"{metrics['max_drawdown']*100:.2f}",
            '胜率(%)': f"{metrics['win_rate']*100:.1f}",
            '盈亏比': f"{metrics['profit_factor']:.2f}",
            '成本拖累(%)': f"{cost['cost_drag']*100:.2f}"
        })

    comparison_df = pd.DataFrame(comparison)

    logger.info("\n" + "="*80)
    logger.info("对比结果:")
    logger.info("="*80)
    logger.info("\n" + comparison_df.to_string(index=False))

    logger.info("\n分析:")
    logger.info("  动量策略特点:")
    logger.info("    - 在趋势行情中表现好")
    logger.info("    - 容易在震荡市中频繁止损")
    logger.info("    - 长周期动量（60日）更稳定")
    logger.info("  反转策略特点:")
    logger.info("    - 在震荡市中表现好")
    logger.info("    - 在强趋势中容易逆势亏损")
    logger.info("    - 短周期反转（5日）波动大")

    logger.success("\n✓ 对比1完成\n")

    return comparison_df


def comparison2_single_vs_multi_factor():
    """
    对比2: 单因子策略 vs 多因子策略

    测试因子组合的价值
    """
    logger.info("\n" + "="*80)
    logger.info("对比2: 单因子策略 vs 多因子策略")
    logger.info("="*80)

    logger.info("\n策略说明:")
    logger.info("  单因子: 只使用一个因子选股")
    logger.info("  多因子: 组合多个因子，分散风险")

    # 准备数据
    prices, features = create_sample_data(n_days=504, n_stocks=100)

    factory = StrategyFactory()

    # 单因子策略
    single_factor_strategies = [
        ('单因子-动量', factory.momentum_strategy(features, 20)),
        ('单因子-反转', factory.reversal_strategy(features, 5)),
        ('单因子-低波', factory.low_volatility_strategy(features)),
    ]

    # 多因子策略
    multi_factor_strategies = [
        ('多因子-等权', factory.multi_factor_strategy(
            features,
            ['MOM20', 'REV5', 'VOL20'],
            weights=[0.33, 0.33, 0.34]
        )),
        ('多因子-动量为主', factory.multi_factor_strategy(
            features,
            ['MOM20', 'MOM60', 'VOL20'],
            weights=[0.5, 0.3, 0.2]
        )),
        ('多因子-综合', factory.multi_factor_strategy(
            features,
            ['MOM20', 'MOM60', 'REV5', 'VOL20'],
            weights=[0.4, 0.3, 0.2, 0.1]
        )),
    ]

    # 合并所有策略
    all_strategies = single_factor_strategies + multi_factor_strategies

    # 回测
    backtest_results = []
    for name, signals in all_strategies:
        result = run_strategy_backtest(name, signals, prices, top_n=30, rebalance_freq='W')
        backtest_results.append(result)

    # 对比结果
    comparison = []
    for result in backtest_results:
        metrics = result['metrics']

        comparison.append({
            '策略': result['name'],
            '类型': '单因子' if '单因子' in result['name'] else '多因子',
            '年化收益(%)': f"{metrics['annualized_return']*100:.2f}",
            '夏普比率': f"{metrics['sharpe_ratio']:.3f}",
            '最大回撤(%)': f"{metrics['max_drawdown']*100:.2f}",
            '卡玛比率': f"{metrics['calmar_ratio']:.3f}",
        })

    comparison_df = pd.DataFrame(comparison)

    logger.info("\n" + "="*80)
    logger.info("对比结果:")
    logger.info("="*80)
    logger.info("\n" + comparison_df.to_string(index=False))

    # 分组统计
    logger.info("\n分组统计:")
    for strategy_type in ['单因子', '多因子']:
        subset = comparison_df[comparison_df['类型'] == strategy_type]
        sharpe_values = subset['夏普比率'].astype(float)
        logger.info(f"  {strategy_type}:")
        logger.info(f"    平均夏普: {sharpe_values.mean():.3f}")
        logger.info(f"    最高夏普: {sharpe_values.max():.3f}")

    logger.info("\n分析:")
    logger.info("  多因子优势:")
    logger.info("    ✓ 分散单因子失效风险")
    logger.info("    ✓ 夏普比率通常更高")
    logger.info("    ✓ 最大回撤控制更好")
    logger.info("  单因子优势:")
    logger.info("    ✓ 逻辑清晰，易于理解")
    logger.info("    ✓ 在因子有效时收益可能更高")
    logger.info("    ✓ 交易成本可能更低")

    logger.success("\n✓ 对比2完成\n")

    return comparison_df


def comparison3_different_rebalance_freq():
    """
    对比3: 不同调仓频率下的策略表现

    同一策略，不同执行频率
    """
    logger.info("\n" + "="*80)
    logger.info("对比3: 不同调仓频率的影响")
    logger.info("="*80)

    logger.info("\n目标: 找到最适合策略的调仓频率")

    # 准备数据
    prices, features = create_sample_data(n_days=504, n_stocks=100)

    factory = StrategyFactory()

    # 选择一个多因子策略
    signals = factory.multi_factor_strategy(
        features,
        ['MOM20', 'REV5', 'VOL20'],
        weights=[0.5, 0.3, 0.2]
    )

    # 测试不同频率
    frequencies = {
        'D': '每日',
        'W': '每周',
        'M': '每月'
    }

    backtest_results = []
    for freq_code, freq_name in frequencies.items():
        logger.info(f"\n测试 {freq_name}调仓...")

        result = run_strategy_backtest(
            f"多因子策略-{freq_name}调仓",
            signals,
            prices,
            top_n=30,
            rebalance_freq=freq_code
        )
        backtest_results.append(result)

    # 对比结果
    comparison = []
    for result in backtest_results:
        metrics = result['metrics']
        cost = result['cost_metrics']

        comparison.append({
            '调仓频率': result['name'].split('-')[1],
            '年化收益(%)': f"{metrics['annualized_return']*100:.2f}",
            '夏普比率': f"{metrics['sharpe_ratio']:.3f}",
            '最大回撤(%)': f"{metrics['max_drawdown']*100:.2f}",
            '交易成本(元)': f"{cost['total_cost']:,.0f}",
            '年化换手': f"{cost['annual_turnover_rate']:.2f}",
            '成本拖累(%)': f"{cost['cost_drag']*100:.2f}"
        })

    comparison_df = pd.DataFrame(comparison)

    logger.info("\n" + "="*80)
    logger.info("对比结果:")
    logger.info("="*80)
    logger.info("\n" + comparison_df.to_string(index=False))

    logger.info("\n结论:")
    logger.info("  频率选择取决于:")
    logger.info("    1. 信号稳定性（稳定→可高频）")
    logger.info("    2. 成本承受力（低佣金→可高频）")
    logger.info("    3. 资金容量（大资金→低频）")

    logger.success("\n✓ 对比3完成\n")

    return comparison_df


def comparison4_portfolio_optimization():
    """
    对比4: 策略组合优化

    组合多个策略，降低相关性
    """
    logger.info("\n" + "="*80)
    logger.info("对比4: 策略组合优化")
    logger.info("="*80)

    logger.info("\n目标: 通过组合不相关策略，提升整体表现")

    # 准备数据
    prices, features = create_sample_data(n_days=504, n_stocks=100)

    factory = StrategyFactory()

    # 创建3个低相关性策略
    strategies = [
        ('动量策略', factory.momentum_strategy(features, 20)),
        ('反转策略', factory.reversal_strategy(features, 5)),
        ('低波策略', factory.low_volatility_strategy(features)),
    ]

    # 单独回测每个策略
    individual_results = []
    strategy_returns = {}

    for name, signals in strategies:
        result = run_strategy_backtest(name, signals, prices, top_n=20, rebalance_freq='W')
        individual_results.append(result)
        strategy_returns[name] = result['results']['daily_returns']

    # 计算策略相关性
    logger.info("\n策略收益率相关性:")
    returns_df = pd.DataFrame(strategy_returns)
    correlation = returns_df.corr()
    logger.info("\n" + correlation.to_string())

    # 组合策略（等权重组合收益）
    logger.info("\n创建组合策略（等权）...")
    combined_returns = returns_df.mean(axis=1)

    # 分析组合策略
    combined_analyzer = PerformanceAnalyzer(
        returns=combined_returns,
        risk_free_rate=0.03
    )
    combined_metrics = combined_analyzer.calculate_all_metrics(verbose=False)

    # 对比
    comparison = []

    # 添加单策略
    for result in individual_results:
        metrics = result['metrics']
        comparison.append({
            '策略': result['name'],
            '类型': '单策略',
            '年化收益(%)': f"{metrics['annualized_return']*100:.2f}",
            '夏普比率': f"{metrics['sharpe_ratio']:.3f}",
            '最大回撤(%)': f"{metrics['max_drawdown']*100:.2f}",
            '索提诺比率': f"{metrics['sortino_ratio']:.3f}"
        })

    # 添加组合策略
    comparison.append({
        '策略': '组合策略（等权）',
        '类型': '组合',
        '年化收益(%)': f"{combined_metrics['annualized_return']*100:.2f}",
        '夏普比率': f"{combined_metrics['sharpe_ratio']:.3f}",
        '最大回撤(%)': f"{combined_metrics['max_drawdown']*100:.2f}",
        '索提诺比率': f"{combined_metrics['sortino_ratio']:.3f}"
    })

    comparison_df = pd.DataFrame(comparison)

    logger.info("\n" + "="*80)
    logger.info("单策略 vs 组合策略:")
    logger.info("="*80)
    logger.info("\n" + comparison_df.to_string(index=False))

    logger.info("\n分析:")
    logger.info("  组合策略优势:")

    # 检查组合是否优于单策略
    single_sharpes = [r['metrics']['sharpe_ratio'] for r in individual_results]
    avg_single_sharpe = np.mean(single_sharpes)
    combined_sharpe = combined_metrics['sharpe_ratio']

    if combined_sharpe > avg_single_sharpe:
        logger.info(f"    ✓ 夏普比率 {combined_sharpe:.3f} > 单策略平均 {avg_single_sharpe:.3f}")
        logger.info("    ✓ 通过分散化提升风险调整收益")
    else:
        logger.info(f"    ✗ 夏普比率未提升（可能策略相关性高）")

    logger.info("\n建议:")
    logger.info("  1. 选择相关性 < 0.5 的策略组合")
    logger.info("  2. 可以使用优化方法确定权重（非等权）")
    logger.info("  3. 定期重新评估策略相关性")

    logger.success("\n✓ 对比4完成\n")

    return comparison_df, correlation


def main():
    """运行所有对比分析"""
    logger.info("\n" + "📊"*40)
    logger.info("多策略回测对比示例")
    logger.info("📊"*40)

    try:
        # 对比1: 动量 vs 反转
        comparison1 = comparison1_momentum_vs_reversal()

        # 对比2: 单因子 vs 多因子
        comparison2 = comparison2_single_vs_multi_factor()

        # 对比3: 调仓频率影响
        comparison3 = comparison3_different_rebalance_freq()

        # 对比4: 策略组合
        comparison4, correlation = comparison4_portfolio_optimization()

        # 总结
        logger.info("\n" + "="*80)
        logger.info("所有对比分析完成！")
        logger.info("="*80)

        logger.info("\n核心发现:")
        logger.info("  1. 动量和反转策略在不同市场环境下表现不同")
        logger.info("  2. 多因子策略通常比单因子更稳定")
        logger.info("  3. 调仓频率对成本和收益影响显著")
        logger.info("  4. 低相关性策略组合可提升夏普比率")

        logger.info("\n策略选择建议:")
        logger.info("  趋势市场 → 动量策略（长周期）")
        logger.info("  震荡市场 → 反转策略或低波策略")
        logger.info("  不确定时 → 多因子组合策略")

        logger.info("\n实战技巧:")
        logger.info("  ✓ 始终进行多策略对比")
        logger.info("  ✓ 关注风险调整收益（夏普）而非绝对收益")
        logger.info("  ✓ 考虑交易成本对高频策略的侵蚀")
        logger.info("  ✓ 利用策略组合降低单一策略风险")

        logger.info("\n下一步:")
        logger.info("  1. 在真实数据上验证策略")
        logger.info("  2. 结合市场环境动态选择策略")
        logger.info("  3. 持续监控策略有效性")

        logger.success("\n✅ 策略对比示例运行成功！\n")

        return 0

    except Exception as e:
        logger.error(f"\n❌ 示例运行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
