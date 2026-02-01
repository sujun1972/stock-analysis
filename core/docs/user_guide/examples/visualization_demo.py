"""
可视化工具演示

展示如何使用可视化模块生成各种图表和HTML报告
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.visualization import (
    BacktestVisualizer,
    FactorVisualizer,
    CorrelationVisualizer,
    HTMLReportGenerator,
)

print("=" * 60)
print("可视化工具演示")
print("=" * 60)


def demo_backtest_visualization():
    """演示回测结果可视化"""
    print("\n【1】回测结果可视化")
    print("-" * 60)

    # 创建可视化器
    viz = BacktestVisualizer()

    # 准备模拟数据
    dates = pd.date_range(start="2023-01-01", periods=252, freq="D")

    # 策略净值曲线
    np.random.seed(42)
    returns = np.random.randn(252) * 0.015 + 0.0005
    equity_curve = pd.Series(
        np.cumprod(1 + returns), index=dates, name="策略净值"
    )

    # 基准净值曲线
    benchmark_returns = np.random.randn(252) * 0.01 + 0.0003
    benchmark_curve = pd.Series(
        np.cumprod(1 + benchmark_returns), index=dates, name="基准净值"
    )

    returns_series = pd.Series(returns, index=dates)
    benchmark_returns_series = pd.Series(benchmark_returns, index=dates)

    # 创建输出目录
    output_dir = Path("visualization_output")
    output_dir.mkdir(exist_ok=True)

    # 1. 净值曲线
    print("  ✓ 生成净值曲线...")
    viz.plot_equity_curve(
        equity_curve,
        benchmark_curve,
        save_path=str(output_dir / "equity_curve.html"),
    )

    # 2. 累计收益率
    print("  ✓ 生成累计收益率...")
    viz.plot_cumulative_returns(
        returns_series,
        benchmark_returns_series,
        save_path=str(output_dir / "cumulative_returns.html"),
    )

    # 3. 回撤曲线
    print("  ✓ 生成回撤曲线...")
    viz.plot_drawdown(
        equity_curve, save_path=str(output_dir / "drawdown.html")
    )

    # 4. 水下曲线
    print("  ✓ 生成水下曲线...")
    viz.plot_underwater(
        equity_curve, save_path=str(output_dir / "underwater.html")
    )

    # 5. 收益分布
    print("  ✓ 生成收益分布...")
    viz.plot_returns_distribution(
        returns_series, save_path=str(output_dir / "returns_dist.html")
    )

    # 6. 月度收益热力图
    print("  ✓ 生成月度收益热力图...")
    viz.plot_monthly_returns_heatmap(
        returns_series,
        save_path=str(output_dir / "monthly_heatmap.html"),
    )

    # 7. 滚动指标
    print("  ✓ 生成滚动指标...")
    viz.plot_rolling_metrics(
        returns_series,
        window=60,
        save_path=str(output_dir / "rolling_metrics.html"),
    )

    # 8. 持仓热力图（模拟数据）
    print("  ✓ 生成持仓热力图...")
    stocks = [f"股票{i:03d}" for i in range(20)]
    position_data = np.random.randn(252, 20) * 0.05
    position_data = position_data / np.abs(position_data).sum(
        axis=1, keepdims=True
    )
    positions = pd.DataFrame(position_data, index=dates, columns=stocks)

    viz.plot_position_heatmap(
        positions,
        top_n=10,
        save_path=str(output_dir / "position_heatmap.html"),
    )

    # 9. 换手率
    print("  ✓ 生成换手率...")
    viz.plot_turnover_rate(
        positions, save_path=str(output_dir / "turnover.html")
    )

    print(f"\n  所有图表已保存到: {output_dir}")


def demo_factor_visualization():
    """演示因子分析可视化"""
    print("\n【2】因子分析可视化")
    print("-" * 60)

    # 创建可视化器
    factor_viz = FactorVisualizer()

    # 准备模拟数据
    dates = pd.date_range(start="2023-01-01", periods=252, freq="D")

    # IC序列（模拟有效因子）
    np.random.seed(42)
    ic_values = np.random.randn(252) * 0.05 + 0.025
    ic_series = pd.Series(ic_values, index=dates, name="IC")

    # 分层收益（单调递增）
    quantile_returns = pd.DataFrame(
        {"mean_return": [0.001, 0.0015, 0.002, 0.0025, 0.003]},
        index=["Q1", "Q2", "Q3", "Q4", "Q5"],
    )

    # 分层累计收益
    quantile_cum_data = {}
    for i in range(1, 6):
        daily_returns = np.random.randn(100) * 0.01 + (i - 3) * 0.0008
        cum_returns = (1 + pd.Series(daily_returns)).cumprod() - 1
        quantile_cum_data[f"Q{i}"] = cum_returns.values

    quantile_cum_returns = pd.DataFrame(
        quantile_cum_data,
        index=pd.date_range(start="2023-01-01", periods=100, freq="D"),
    )

    # 多空组合收益
    long_short_returns = pd.Series(
        np.random.randn(252) * 0.012 + 0.001, index=dates
    )

    output_dir = Path("visualization_output")

    # 1. IC时间序列
    print("  ✓ 生成IC时间序列...")
    factor_viz.plot_ic_time_series(
        ic_series, save_path=str(output_dir / "ic_series.html")
    )

    # 2. IC分布
    print("  ✓ 生成IC分布...")
    factor_viz.plot_ic_histogram(
        ic_series, save_path=str(output_dir / "ic_histogram.html")
    )

    # 3. IC衰减
    print("  ✓ 生成IC衰减...")
    ic_decay = pd.Series(
        [0.025, 0.020, 0.015, 0.012, 0.010],
        index=[1, 2, 3, 4, 5],
        name="IC衰减",
    )
    factor_viz.plot_ic_decay(
        ic_decay, save_path=str(output_dir / "ic_decay.html")
    )

    # 4. 分层收益
    print("  ✓ 生成分层收益...")
    factor_viz.plot_quantile_returns(
        quantile_returns,
        save_path=str(output_dir / "quantile_returns.html"),
    )

    # 5. 分层累计收益
    print("  ✓ 生成分层累计收益...")
    factor_viz.plot_quantile_cumulative_returns(
        quantile_cum_returns,
        save_path=str(output_dir / "quantile_cum_returns.html"),
    )

    # 6. 多空组合表现
    print("  ✓ 生成多空组合表现...")
    factor_viz.plot_long_short_performance(
        long_short_returns,
        save_path=str(output_dir / "long_short.html"),
    )

    # 7. 多因子IC对比
    print("  ✓ 生成多因子IC对比...")
    ic_dict = {
        "MOM_20": ic_series,
        "MOM_60": ic_series * 0.8 + np.random.randn(252) * 0.02,
        "REV_5": -ic_series * 0.5 + np.random.randn(252) * 0.03,
    }
    factor_viz.plot_batch_ic_comparison(
        ic_dict, save_path=str(output_dir / "batch_ic_comparison.html")
    )

    print(f"\n  所有图表已保存到: {output_dir}")


def demo_correlation_visualization():
    """演示相关性分析可视化"""
    print("\n【3】相关性分析可视化")
    print("-" * 60)

    # 创建可视化器
    corr_viz = CorrelationVisualizer()

    # 准备模拟相关性矩阵
    factors = [f"因子{i}" for i in range(1, 9)]
    np.random.seed(42)
    matrix = np.random.rand(8, 8)
    matrix = (matrix + matrix.T) / 2  # 对称化
    np.fill_diagonal(matrix, 1.0)  # 对角线为1
    matrix = np.clip(matrix, -1, 1)  # 确保在[-1, 1]范围

    corr_matrix = pd.DataFrame(matrix, index=factors, columns=factors)

    output_dir = Path("visualization_output")

    # 1. 相关性热力图
    print("  ✓ 生成相关性热力图...")
    corr_viz.plot_correlation_heatmap(
        corr_matrix, save_path=str(output_dir / "corr_heatmap.html")
    )

    # 2. 相关性热力图（聚类）
    print("  ✓ 生成聚类热力图...")
    corr_viz.plot_correlation_heatmap(
        corr_matrix,
        cluster=True,
        save_path=str(output_dir / "corr_heatmap_clustered.html"),
    )

    # 3. 相关性网络图
    print("  ✓ 生成相关性网络图...")
    corr_viz.plot_correlation_network(
        corr_matrix,
        threshold=0.5,
        save_path=str(output_dir / "corr_network.html"),
    )

    # 4. 因子聚类树状图
    print("  ✓ 生成聚类树状图...")
    corr_viz.plot_factor_clustering(
        corr_matrix, save_path=str(output_dir / "clustering.html")
    )

    # 5. VIF分析
    print("  ✓ 生成VIF分析...")
    vif_df = pd.DataFrame(
        {
            "factor": factors,
            "VIF": [2.5, 8.3, 15.6, 3.2, 1.8, 12.4, 4.7, 2.1],
        }
    )
    corr_viz.plot_vif_analysis(
        vif_df, threshold=10.0, save_path=str(output_dir / "vif_analysis.html")
    )

    # 6. 滚动相关性
    print("  ✓ 生成滚动相关性...")
    dates = pd.date_range(start="2023-01-01", periods=252, freq="D")
    factor1 = pd.Series(np.random.randn(252), index=dates, name="因子1")
    factor2 = pd.Series(np.random.randn(252), index=dates, name="因子2")

    corr_viz.plot_rolling_correlation(
        factor1,
        factor2,
        window=60,
        save_path=str(output_dir / "rolling_corr.html"),
    )

    print(f"\n  所有图表已保存到: {output_dir}")


def demo_html_report():
    """演示HTML报告生成"""
    print("\n【4】HTML报告生成")
    print("-" * 60)

    # 创建报告生成器
    report_gen = HTMLReportGenerator()

    # 准备回测数据
    dates = pd.date_range(start="2023-01-01", periods=252, freq="D")
    np.random.seed(42)

    returns = np.random.randn(252) * 0.015 + 0.0008
    equity_curve = pd.Series(np.cumprod(1 + returns), index=dates)
    returns_series = pd.Series(returns, index=dates)

    benchmark_returns = np.random.randn(252) * 0.01 + 0.0003
    benchmark_curve = pd.Series(
        np.cumprod(1 + benchmark_returns), index=dates
    )
    benchmark_returns_series = pd.Series(benchmark_returns, index=dates)

    # 持仓数据
    stocks = [f"股票{i:03d}" for i in range(10)]
    position_data = np.random.randn(252, 10) * 0.05
    position_data = position_data / np.abs(position_data).sum(
        axis=1, keepdims=True
    )
    positions = pd.DataFrame(position_data, index=dates, columns=stocks)

    # 计算指标
    total_return = equity_curve.iloc[-1] / equity_curve.iloc[0] - 1
    annual_return = (1 + total_return) ** (252 / 252) - 1
    annual_vol = returns_series.std() * np.sqrt(252)
    sharpe = annual_return / annual_vol if annual_vol != 0 else 0

    running_max = equity_curve.expanding().max()
    drawdown = (equity_curve - running_max) / running_max
    max_drawdown = drawdown.min()

    metrics = {
        "总收益率": f"{total_return*100:.2f}%",
        "年化收益率": f"{annual_return*100:.2f}%",
        "年化波动率": f"{annual_vol*100:.2f}%",
        "夏普比率": f"{sharpe:.2f}",
        "最大回撤": f"{max_drawdown*100:.2f}%",
        "胜率": f"{(returns_series > 0).sum() / len(returns_series) * 100:.2f}%",
    }

    output_dir = Path("visualization_output")

    # 1. 生成回测报告
    print("  ✓ 生成回测报告...")
    report_gen.generate_backtest_report(
        equity_curve=equity_curve,
        returns=returns_series,
        positions=positions,
        benchmark_curve=benchmark_curve,
        benchmark_returns=benchmark_returns_series,
        metrics=metrics,
        strategy_name="动量策略示例",
        output_path=str(output_dir / "backtest_report.html"),
    )

    # 准备因子数据
    ic_values = np.random.randn(252) * 0.05 + 0.025
    ic_series = pd.Series(ic_values, index=dates)

    quantile_returns = pd.DataFrame(
        {"mean_return": [0.001, 0.0015, 0.002, 0.0025, 0.003]},
        index=["Q1", "Q2", "Q3", "Q4", "Q5"],
    )

    quantile_cum_data = {}
    for i in range(1, 6):
        daily_returns = np.random.randn(100) * 0.01 + (i - 3) * 0.0008
        cum_returns = (1 + pd.Series(daily_returns)).cumprod() - 1
        quantile_cum_data[f"Q{i}"] = cum_returns.values

    quantile_cum_returns = pd.DataFrame(
        quantile_cum_data,
        index=pd.date_range(start="2023-01-01", periods=100, freq="D"),
    )

    long_short_returns = pd.Series(
        np.random.randn(252) * 0.012 + 0.001, index=dates
    )

    ic_mean = ic_series.mean()
    ic_std = ic_series.std()
    ic_ir = ic_mean / ic_std if ic_std != 0 else 0
    ic_positive_rate = (ic_series > 0).sum() / len(ic_series)

    factor_metrics = {
        "IC均值": f"{ic_mean:.4f}",
        "IC标准差": f"{ic_std:.4f}",
        "IR比率": f"{ic_ir:.4f}",
        "IC>0占比": f"{ic_positive_rate*100:.2f}%",
    }

    # 2. 生成因子报告
    print("  ✓ 生成因子报告...")
    report_gen.generate_factor_report(
        factor_name="MOM_20",
        ic_series=ic_series,
        quantile_returns=quantile_returns,
        quantile_cum_returns=quantile_cum_returns,
        long_short_returns=long_short_returns,
        metrics=factor_metrics,
        output_path=str(output_dir / "factor_report.html"),
    )

    print(f"\n  所有报告已保存到: {output_dir}")


def demo_dark_theme():
    """演示暗色主题"""
    print("\n【5】暗色主题演示")
    print("-" * 60)

    # 创建暗色主题可视化器
    dark_viz = BacktestVisualizer(theme="dark_theme")
    dark_report_gen = HTMLReportGenerator(theme="dark_theme")

    # 准备数据
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    np.random.seed(42)
    returns = np.random.randn(100) * 0.015 + 0.0008
    equity_curve = pd.Series(np.cumprod(1 + returns), index=dates)

    output_dir = Path("visualization_output")

    # 生成暗色主题图表
    print("  ✓ 生成暗色主题净值曲线...")
    dark_viz.plot_equity_curve(
        equity_curve, save_path=str(output_dir / "equity_dark.html")
    )

    # 生成暗色主题报告
    print("  ✓ 生成暗色主题报告...")
    dark_report_gen.generate_backtest_report(
        equity_curve=equity_curve,
        returns=pd.Series(returns, index=dates),
        strategy_name="暗色主题示例",
        output_path=str(output_dir / "backtest_report_dark.html"),
    )

    print(f"\n  暗色主题报告已保存到: {output_dir}")


if __name__ == "__main__":
    try:
        # 运行所有演示
        demo_backtest_visualization()
        demo_factor_visualization()
        demo_correlation_visualization()
        demo_html_report()
        demo_dark_theme()

        print("\n" + "=" * 60)
        print("✓ 所有演示完成!")
        print("=" * 60)
        print("\n请在浏览器中打开 visualization_output 目录下的HTML文件查看结果")

    except Exception as e:
        print(f"\n❌ 演示失败: {e}")
        import traceback

        traceback.print_exc()
