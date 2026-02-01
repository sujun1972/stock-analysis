"""
visualize命令 - 生成可视化报告

支持生成回测报告、因子分析报告等可视化内容
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import click
import pandas as pd
import numpy as np

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from cli.utils.output import print_success, print_error, print_info
from src.utils.logger import get_logger

logger = get_logger(__name__)


@click.group()
def visualize():
    """
    生成可视化报告

    \b
    子命令:
        • backtest - 生成回测可视化报告
        • factor   - 生成因子分析可视化报告
    """
    pass


@visualize.command()
@click.option("--data", type=click.Path(exists=True), required=True, help="回测数据文件（CSV/JSON）")
@click.option("--output", type=click.Path(), required=True, help="输出HTML路径")
@click.option("--strategy-name", default="策略", help="策略名称")
@click.option("--theme", type=click.Choice(["default_theme", "dark_theme"]), default="default_theme", help="可视化主题")
def backtest(data, output, strategy_name, theme):
    """
    生成回测可视化报告

    \b
    示例:
        stock-cli visualize backtest --data backtest_result.csv --output report.html

        stock-cli visualize backtest \\
            --data my_strategy.json \\
            --output visual_report.html \\
            --strategy-name "我的动量策略" \\
            --theme dark_theme
    """
    try:
        print_info(f"正在加载回测数据: {data}")

        from visualization.report_generator import HTMLReportGenerator

        # 加载数据
        data_path = Path(data)
        if data_path.suffix == ".csv":
            df = pd.read_csv(data_path, index_col=0, parse_dates=True)
        elif data_path.suffix == ".json":
            df = pd.read_json(data_path)
        else:
            raise ValueError(f"不支持的文件格式: {data_path.suffix}")

        # 提取净值曲线和收益率
        if "equity" in df.columns:
            equity_curve = df["equity"]
            returns = equity_curve.pct_change().dropna()
        elif "returns" in df.columns:
            returns = df["returns"]
            equity_curve = (1 + returns).cumprod()
        else:
            raise ValueError("数据文件必须包含 'equity' 或 'returns' 列")

        # 提取基准数据（如果有）
        benchmark_curve = df.get("benchmark_equity")
        benchmark_returns = df.get("benchmark_returns")

        # 提取持仓数据（如果有）
        position_cols = [col for col in df.columns if col.startswith("pos_")]
        positions = df[position_cols] if position_cols else None

        # 计算基本指标
        total_return = equity_curve.iloc[-1] / equity_curve.iloc[0] - 1
        annual_return = (1 + total_return) ** (252 / len(returns)) - 1
        annual_vol = returns.std() * np.sqrt(252)
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
        }

        print_info("正在生成可视化报告...")

        # 创建报告生成器
        report_gen = HTMLReportGenerator(theme=theme)

        # 生成报告
        report_gen.generate_backtest_report(
            equity_curve=equity_curve,
            returns=returns,
            positions=positions,
            benchmark_curve=benchmark_curve,
            benchmark_returns=benchmark_returns,
            metrics=metrics,
            strategy_name=strategy_name,
            output_path=output,
        )

        print_success(f"\n✓ 可视化报告已生成: {output}")

    except Exception as e:
        logger.exception("生成可视化报告失败")
        print_error(f"失败: {e}")
        sys.exit(1)


@visualize.command()
@click.option("--ic-data", type=click.Path(exists=True), required=True, help="IC数据文件（CSV）")
@click.option("--output", type=click.Path(), required=True, help="输出HTML路径")
@click.option("--factor-name", required=True, help="因子名称")
@click.option("--quantile-data", type=click.Path(exists=True), help="分层收益数据文件（可选）")
@click.option("--theme", type=click.Choice(["default_theme", "dark_theme"]), default="default_theme", help="可视化主题")
def factor(ic_data, output, factor_name, quantile_data, theme):
    """
    生成因子分析可视化报告

    \b
    示例:
        stock-cli visualize factor \\
            --ic-data ic_result.csv \\
            --output factor_report.html \\
            --factor-name MOM_20

        stock-cli visualize factor \\
            --ic-data ic_result.csv \\
            --quantile-data quantile_result.csv \\
            --output report.html \\
            --factor-name "动量因子" \\
            --theme dark_theme
    """
    try:
        print_info(f"正在加载因子数据: {ic_data}")

        from visualization.report_generator import HTMLReportGenerator

        # 加载IC数据
        ic_series = pd.read_csv(ic_data, index_col=0, parse_dates=True, squeeze=True)
        if isinstance(ic_series, pd.DataFrame):
            ic_series = ic_series.iloc[:, 0]  # 取第一列

        # 加载分层收益数据（如果提供）
        quantile_returns = None
        quantile_cum_returns = None
        long_short_returns = None

        if quantile_data:
            print_info(f"正在加载分层数据: {quantile_data}")
            quantile_df = pd.read_csv(quantile_data, index_col=0)

            if "mean_return" in quantile_df.columns:
                quantile_returns = quantile_df
            elif "Q1" in quantile_df.columns:
                # 累计收益格式
                quantile_cum_returns = quantile_df
                # 计算多空组合收益
                if "Q5" in quantile_df.columns and "Q1" in quantile_df.columns:
                    long_short_returns = quantile_df["Q5"] - quantile_df["Q1"]

        # 计算因子指标
        ic_mean = ic_series.mean()
        ic_std = ic_series.std()
        ic_ir = ic_mean / ic_std if ic_std != 0 else 0
        ic_positive_rate = (ic_series > 0).sum() / len(ic_series)

        metrics = {
            "IC均值": f"{ic_mean:.4f}",
            "IC标准差": f"{ic_std:.4f}",
            "IR比率": f"{ic_ir:.4f}",
            "IC>0占比": f"{ic_positive_rate*100:.2f}%",
        }

        print_info("正在生成可视化报告...")

        # 创建报告生成器
        report_gen = HTMLReportGenerator(theme=theme)

        # 生成报告
        report_gen.generate_factor_report(
            factor_name=factor_name,
            ic_series=ic_series,
            quantile_returns=quantile_returns,
            quantile_cum_returns=quantile_cum_returns,
            long_short_returns=long_short_returns,
            metrics=metrics,
            output_path=output,
        )

        print_success(f"\n✓ 可视化报告已生成: {output}")

    except Exception as e:
        logger.exception("生成可视化报告失败")
        print_error(f"失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    visualize()
