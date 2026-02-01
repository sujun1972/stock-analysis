"""
完整因子分析示例

演示如何使用统一的FactorAnalyzer门面进行：
1. 单因子快速分析
2. 多因子对比分析
3. 因子组合优化
4. 生成完整分析报告
"""

import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import pandas as pd
import numpy as np
from datetime import datetime

from analysis.factor_analyzer import (
    FactorAnalyzer,
    quick_analyze_factor,
    compare_multiple_factors,
    optimize_factor_combination
)

# 设置随机种子
np.random.seed(42)


def create_sample_data():
    """创建示例数据"""
    print("\n" + "="*60)
    print("1. 创建示例数据")
    print("="*60)

    # 日期范围: 2年数据
    dates = pd.date_range('2020-01-01', '2021-12-31', freq='D')
    stocks = [f'stock_{i:03d}' for i in range(100)]

    print(f"日期范围: {dates[0]} 到 {dates[-1]}")
    print(f"股票数量: {len(stocks)}")

    # 生成价格数据（带趋势和波动）
    base_price = 100
    trend = np.linspace(0, 30, len(dates))
    volatility = np.random.randn(len(dates), len(stocks)) * 2

    prices = pd.DataFrame(
        base_price + trend[:, np.newaxis] + volatility.cumsum(axis=0),
        index=dates,
        columns=stocks
    )

    print(f"价格范围: {prices.min().min():.2f} - {prices.max().max():.2f}")

    return prices, stocks


def create_factors(prices):
    """创建多个Alpha因子"""
    print("\n" + "="*60)
    print("2. 创建Alpha因子")
    print("="*60)

    # 因子1: 20日动量
    factor_mom20 = prices.pct_change(20).shift(1)
    print("✓ MOM20 (20日动量因子)")

    # 因子2: 10日动量
    factor_mom10 = prices.pct_change(10).shift(1)
    print("✓ MOM10 (10日动量因子)")

    # 因子3: 5日反转
    factor_rev5 = -prices.pct_change(5).shift(1)
    print("✓ REV5 (5日反转因子)")

    # 因子4: 20日波动率
    factor_vol20 = prices.pct_change().rolling(20).std().shift(1)
    print("✓ VOL20 (20日波动率因子)")

    # 因子5: 随机因子（作为对比）
    factor_random = pd.DataFrame(
        np.random.randn(len(prices), len(prices.columns)),
        index=prices.index,
        columns=prices.columns
    )
    print("✓ RANDOM (随机因子，用于对比)")

    factor_dict = {
        'MOM20': factor_mom20,
        'MOM10': factor_mom10,
        'REV5': factor_rev5,
        'VOL20': factor_vol20,
        'RANDOM': factor_random
    }

    print(f"\n总计: {len(factor_dict)} 个因子")

    return factor_dict


def example_1_quick_analyze(factor_dict, prices):
    """示例1: 快速分析单个因子"""
    print("\n" + "="*60)
    print("示例1: 快速分析单个因子")
    print("="*60)

    # 使用便捷函数
    print("\n方法1: 使用便捷函数 quick_analyze_factor()")
    report = quick_analyze_factor(
        factor_dict['MOM20'],
        prices,
        factor_name='MOM20'
    )

    print(report)

    # 使用分析器对象
    print("\n方法2: 使用FactorAnalyzer对象")
    analyzer = FactorAnalyzer(
        forward_periods=5,
        n_layers=5,
        method='spearman'
    )

    report2 = analyzer.quick_analyze(
        factor_dict['REV5'],
        prices,
        factor_name='REV5',
        include_layering=True
    )

    print(report2)


def example_2_compare_factors(factor_dict, prices):
    """示例2: 多因子对比分析"""
    print("\n" + "="*60)
    print("示例2: 多因子对比分析")
    print("="*60)

    # 方法1: 使用便捷函数
    print("\n使用便捷函数 compare_multiple_factors()")
    comparison = compare_multiple_factors(
        factor_dict,
        prices
    )

    print("\n因子对比结果:")
    print(comparison.to_string(index=False))

    # 找出最优因子
    best_factor = comparison.iloc[0]['因子名']
    best_icir = comparison.iloc[0]['ICIR']
    print(f"\n最优因子: {best_factor} (ICIR = {best_icir:.4f})")

    # 方法2: 使用分析器对象（更多控制）
    print("\n\n使用FactorAnalyzer对象（按IC排序）")
    analyzer = FactorAnalyzer()

    comparison2 = analyzer.compare_factors(
        factor_dict,
        prices,
        include_correlation=True,
        rank_by='ic'
    )

    print("\n因子对比结果（按IC降序）:")
    print(comparison2[['因子名', 'IC均值', 'ICIR', '综合评分']].to_string(index=False))


def example_3_optimize_portfolio(factor_dict, prices):
    """示例3: 因子组合优化"""
    print("\n" + "="*60)
    print("示例3: 因子组合优化")
    print("="*60)

    # 选择表现较好的因子进行组合
    selected_factors = {
        'MOM20': factor_dict['MOM20'],
        'MOM10': factor_dict['MOM10'],
        'REV5': factor_dict['REV5']
    }

    analyzer = FactorAnalyzer()

    # 方法1: 等权重
    print("\n方法1: 等权重组合")
    opt_result1, combined1 = analyzer.optimize_factor_portfolio(
        selected_factors,
        prices,
        optimization_method='equal'
    )

    print("权重分配:")
    for factor_name, weight in opt_result1.weights.items():
        print(f"  {factor_name}: {weight:.4f}")

    # 方法2: IC加权
    print("\n方法2: IC加权组合")
    opt_result2, combined2 = analyzer.optimize_factor_portfolio(
        selected_factors,
        prices,
        optimization_method='ic'
    )

    print("权重分配:")
    for factor_name, weight in opt_result2.weights.items():
        print(f"  {factor_name}: {weight:.4f}")

    # 方法3: ICIR加权
    print("\n方法3: ICIR加权组合")
    opt_result3, combined3 = analyzer.optimize_factor_portfolio(
        selected_factors,
        prices,
        optimization_method='ic_ir'
    )

    print("权重分配:")
    for factor_name, weight in opt_result3.weights.items():
        print(f"  {factor_name}: {weight:.4f}")

    # 方法4: 最大化ICIR优化
    print("\n方法4: 最大化ICIR优化（推荐）")
    opt_result4, combined4 = analyzer.optimize_factor_portfolio(
        selected_factors,
        prices,
        optimization_method='max_icir',
        max_weight=0.6,
        min_weight=0.1
    )

    print("优化结果:")
    print(f"  组合IC均值: {opt_result4.ic_mean:.4f}")
    print(f"  组合ICIR: {opt_result4.ic_ir:.4f}")
    print("\n最优权重分配:")
    for factor_name, weight in opt_result4.weights.items():
        print(f"  {factor_name}: {weight:.4f}")

    # 使用便捷函数
    print("\n\n使用便捷函数 optimize_factor_combination()")
    opt_result5, combined5 = optimize_factor_combination(
        selected_factors,
        prices,
        method='max_icir'
    )

    print("优化权重:")
    for factor_name, weight in opt_result5.weights.items():
        print(f"  {factor_name}: {weight:.4f}")


def example_4_batch_analyze(factor_dict, prices):
    """示例4: 批量分析多个因子"""
    print("\n" + "="*60)
    print("示例4: 批量分析多个因子")
    print("="*60)

    analyzer = FactorAnalyzer()

    reports = analyzer.batch_analyze(factor_dict, prices)

    print(f"\n成功分析 {len(reports)}/{len(factor_dict)} 个因子\n")

    # 显示每个因子的摘要
    for factor_name, report in reports.items():
        print(f"\n{factor_name}:")
        print(f"  综合评分: {report.overall_score:.2f}/100")
        print(f"  建议: {report.recommendation}")

        if report.ic_result:
            print(f"  IC均值: {report.ic_result.mean_ic:.4f}")
            print(f"  ICIR: {report.ic_result.ic_ir:.4f}")


def example_5_full_report(factor_dict, prices):
    """示例5: 生成完整分析报告"""
    print("\n" + "="*60)
    print("示例5: 生成完整分析报告")
    print("="*60)

    analyzer = FactorAnalyzer()

    # 选择部分因子生成报告（避免过大）
    selected_factors = {
        'MOM20': factor_dict['MOM20'],
        'REV5': factor_dict['REV5'],
        'VOL20': factor_dict['VOL20']
    }

    print("\n生成完整报告...")
    full_report = analyzer.generate_full_report(
        selected_factors,
        prices,
        include_ic=True,
        include_layering=True,
        include_correlation=True,
        include_optimization=True
    )

    # 显示报告摘要
    print("\n报告摘要:")
    print(f"  分析日期: {full_report['summary']['analysis_date']}")
    print(f"  因子数量: {full_report['summary']['n_factors']}")
    print(f"  因子列表: {', '.join(full_report['summary']['factor_names'])}")

    # 显示单因子分析结果
    print("\n单因子分析:")
    for factor_name in selected_factors.keys():
        if factor_name in full_report['individual_analysis']:
            analysis = full_report['individual_analysis'][factor_name]
            print(f"\n  {factor_name}:")
            if 'ic_analysis' in analysis:
                ic = analysis['ic_analysis']
                print(f"    IC均值: {ic['mean_ic']:.4f}")
                print(f"    ICIR: {ic['ic_ir']:.4f}")
            if 'overall_score' in analysis:
                print(f"    综合评分: {analysis['overall_score']:.2f}")

    # 显示相关性分析
    if full_report['correlation']:
        print("\n相关性分析:")
        print(f"  发现 {len(full_report['correlation']['high_correlation_pairs'])} 对高相关因子")

        if full_report['correlation']['high_correlation_pairs']:
            print("\n  高相关因子对 (相关系数 > 0.7):")
            for pair in full_report['correlation']['high_correlation_pairs'][:3]:
                print(f"    {pair['factor1']} <-> {pair['factor2']}: {pair['correlation']:.4f}")

    # 显示优化结果
    if full_report['optimization']:
        print("\n因子组合优化:")
        opt = full_report['optimization']
        print(f"  组合IC均值: {opt['ic_mean']:.4f}")
        print(f"  组合ICIR: {opt['ic_ir']:.4f}")
        print("\n  最优权重:")
        for factor_name, weight in opt['权重'].items():
            print(f"    {factor_name}: {weight:.4f}")

    # 保存报告到文件
    output_file = Path(__file__).parent / 'factor_analysis_report.json'
    full_report2 = analyzer.generate_full_report(
        selected_factors,
        prices,
        include_ic=True,
        include_layering=False,
        include_correlation=False,
        include_optimization=True,
        output_path=str(output_file)
    )

    print(f"\n报告已保存到: {output_file}")


def example_6_complete_workflow(factor_dict, prices):
    """示例6: 完整的因子分析工作流"""
    print("\n" + "="*60)
    print("示例6: 完整的因子分析工作流")
    print("="*60)

    print("\n步骤1: 初始化分析器")
    analyzer = FactorAnalyzer(
        forward_periods=5,
        n_layers=5,
        holding_period=5,
        method='spearman'
    )

    print("\n步骤2: 多因子对比，筛选优质因子")
    comparison = analyzer.compare_factors(
        factor_dict,
        prices,
        rank_by='ic_ir'
    )

    print("\n因子排名（按ICIR）:")
    print(comparison[['因子名', 'IC均值', 'ICIR', '综合评分']].head(3).to_string(index=False))

    # 选择Top3因子
    top3_factors = comparison.head(3)['因子名'].tolist()
    selected_factor_dict = {name: factor_dict[name] for name in top3_factors}

    print(f"\n选择Top3因子: {', '.join(top3_factors)}")

    print("\n步骤3: 检查因子相关性")
    corr_matrix = analyzer.correlation_analyzer.calculate_factor_correlation(
        selected_factor_dict,
        aggregate_method='concat'
    )

    print("\n相关性矩阵:")
    print(corr_matrix.round(3))

    high_corr_pairs = analyzer.correlation_analyzer.find_high_correlation_pairs(
        corr_matrix,
        threshold=0.7
    )

    if high_corr_pairs:
        print(f"\n发现 {len(high_corr_pairs)} 对高相关因子")
        for f1, f2, corr in high_corr_pairs:
            print(f"  {f1} <-> {f2}: {corr:.3f}")
    else:
        print("\n未发现高相关因子对，因子独立性良好")

    print("\n步骤4: 优化因子组合权重")
    opt_result, combined_factor = analyzer.optimize_factor_portfolio(
        selected_factor_dict,
        prices,
        optimization_method='max_icir',
        max_weight=0.6,
        min_weight=0.1
    )

    print("\n优化结果:")
    print(f"  组合IC均值: {opt_result.ic_mean:.4f}")
    print(f"  组合ICIR: {opt_result.ic_ir:.4f}")
    print("\n最优权重:")
    for factor_name, weight in opt_result.weights.items():
        print(f"  {factor_name}: {weight:.4f}")

    print("\n步骤5: 分析组合因子")
    combined_report = analyzer.quick_analyze(
        combined_factor,
        prices,
        factor_name='Combined_Factor'
    )

    print(f"\n组合因子综合评分: {combined_report.overall_score:.2f}/100")
    print(f"建议: {combined_report.recommendation}")

    if combined_report.ic_result:
        print(f"\n组合因子IC统计:")
        print(f"  IC均值: {combined_report.ic_result.mean_ic:.4f}")
        print(f"  ICIR: {combined_report.ic_result.ic_ir:.4f}")
        print(f"  IC正值率: {combined_report.ic_result.positive_rate:.2%}")

    print("\n✓ 完整工作流执行完成！")


def main():
    """主函数"""
    print("\n" + "="*60)
    print("统一因子分析器 (FactorAnalyzer) 完整示例")
    print("="*60)

    # 创建数据
    prices, stocks = create_sample_data()
    factor_dict = create_factors(prices)

    # 运行所有示例
    example_1_quick_analyze(factor_dict, prices)
    example_2_compare_factors(factor_dict, prices)
    example_3_optimize_portfolio(factor_dict, prices)
    example_4_batch_analyze(factor_dict, prices)
    example_5_full_report(factor_dict, prices)
    example_6_complete_workflow(factor_dict, prices)

    print("\n" + "="*60)
    print("所有示例运行完成！")
    print("="*60)


if __name__ == '__main__':
    main()
