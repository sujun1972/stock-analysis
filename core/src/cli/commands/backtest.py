"""
backtest命令 - 运行策略回测

支持运行动量、均值回归、多因子、机器学习等策略
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import click

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from cli.utils.output import (
    print_success,
    print_error,
    print_info,
    print_table,
    format_percentage,
    format_number,
)
from cli.utils.progress import create_progress_bar
from src.utils.logger import get_logger
from config.settings import get_settings

logger = get_logger(__name__)


def load_backtest_data(start_date: datetime, end_date: datetime):
    """
    加载回测数据

    Args:
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        价格和信号数据
    """
    from database.db_manager import DatabaseManager
    import pandas as pd

    db_manager = DatabaseManager()

    # 这里简化处理，实际应该从数据库加载多只股票数据
    # 示例：加载指数数据作为市场基准
    query = f"""
        SELECT trade_date, close
        FROM stock_daily_000001
        WHERE trade_date >= '{start_date.date()}'
          AND trade_date <= '{end_date.date()}'
        ORDER BY trade_date
    """

    df = db_manager.execute_query(query)

    if df is None or df.empty:
        raise ValueError(f"未找到 {start_date.date()} ~ {end_date.date()} 的数据")

    return df


def run_momentum_strategy(prices_df, **params):
    """运行动量策略"""
    from strategies.momentum_strategy import MomentumStrategy
    import pandas as pd
    import numpy as np

    # 创建策略
    strategy = MomentumStrategy(**params)

    # 生成信号
    signals = strategy.generate_signals(prices_df)

    return signals


def run_mean_reversion_strategy(prices_df, **params):
    """运行均值回归策略"""
    from strategies.mean_reversion_strategy import MeanReversionStrategy

    strategy = MeanReversionStrategy(**params)
    signals = strategy.generate_signals(prices_df)

    return signals


def run_multi_factor_strategy(prices_df, features_df, **params):
    """运行多因子策略"""
    from strategies.multi_factor_strategy import MultiFactorStrategy

    strategy = MultiFactorStrategy(**params)
    signals = strategy.generate_signals(features_df)

    return signals


def run_ml_strategy(prices_df, model_path, **params):
    """
    运行机器学习策略

    注意: 旧的 MLStrategy 已被删除，请使用新的 ml.MLEntry 策略
    参考: core/docs/planning/ml_system_refactoring_plan.md
    """
    raise NotImplementedError(
        "旧的 MLStrategy 已被删除。请使用新的 ml.MLEntry 策略。\n"
        "详情参考: core/docs/planning/ml_system_refactoring_plan.md"
    )


def calculate_performance_metrics(portfolio_value, daily_returns):
    """
    计算绩效指标

    Args:
        portfolio_value: 组合净值序列
        daily_returns: 每日收益率序列

    Returns:
        绩效指标字典
    """
    import numpy as np

    # 基础统计
    total_return = (portfolio_value.iloc[-1] / portfolio_value.iloc[0] - 1) * 100
    trading_days = len(portfolio_value)
    annual_return = (
        (1 + total_return / 100) ** (252 / trading_days) - 1
    ) * 100

    # 风险指标
    volatility = daily_returns.std() * np.sqrt(252) * 100
    sharpe_ratio = annual_return / volatility if volatility > 0 else 0

    # 回撤
    cumulative = (1 + daily_returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max * 100
    max_drawdown = drawdown.min()

    # 胜率
    win_rate = (daily_returns > 0).sum() / len(daily_returns) * 100

    return {
        "总收益率": total_return,
        "年化收益率": annual_return,
        "波动率": volatility,
        "夏普比率": sharpe_ratio,
        "最大回撤": max_drawdown,
        "胜率": win_rate,
        "交易天数": trading_days,
    }


@click.command()
@click.option(
    "--strategy",
    type=click.Choice(
        ["momentum", "mean_reversion", "multi_factor", "ml"], case_sensitive=False
    ),
    required=True,
    help="策略类型",
)
@click.option(
    "--start",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="回测开始日期（默认1年前）",
)
@click.option(
    "--end", type=click.DateTime(formats=["%Y-%m-%d"]), help="回测结束日期（默认今天）"
)
@click.option("--capital", type=float, default=1000000, help="初始资金")
@click.option("--model", type=click.Path(exists=True), help="模型路径（ML策略必需）")
@click.option(
    "--report",
    type=click.Choice(["text", "html", "json"], case_sensitive=False),
    default="text",
    help="报告格式",
)
@click.option("--output", type=click.Path(), help="报告保存路径")
@click.option("--visualize", is_flag=True, help="生成可视化报告（自动使用HTML格式）")
@click.pass_context
def backtest(ctx, strategy, start, end, capital, model, report, output, visualize):
    """
    运行策略回测

    \b
    支持的策略:
        • momentum       - 动量策略
        • mean_reversion - 均值回归策略
        • multi_factor   - 多因子策略
        • ml             - 机器学习策略

    \b
    示例:
        # 运行动量策略回测
        stock-cli backtest --strategy momentum --capital 1000000

    \b
        # 指定回测时间范围
        stock-cli backtest --strategy multi_factor \\
            --start 2023-01-01 --end 2024-12-31

    \b
        # 使用机器学习策略
        stock-cli backtest --strategy ml \\
            --model /data/models/lightgbm_model.pkl

    \b
        # 生成HTML报告
        stock-cli backtest --strategy momentum \\
            --report html --output results/backtest.html
    """
    try:
        from backtest.backtest_engine import BacktestEngine
        from backtest.performance_analyzer import PerformanceAnalyzer
        import pandas as pd
        import numpy as np
        from datetime import timedelta

        settings = get_settings()

        # ML策略需要模型
        if strategy == "ml" and not model:
            print_error("ML策略需要指定模型路径（--model）")
            sys.exit(1)

        # 默认日期范围
        if end is None:
            end = datetime.now()
        if start is None:
            start = end - timedelta(days=365)

        print_info("\n[bold green]开始策略回测[/bold green]", bold=True)

        task_info = {
            "策略类型": strategy.upper(),
            "初始资金": f"{capital:,.0f}",
            "回测时间": f"{start.date()} ~ {end.date()}",
            "报告格式": report.upper(),
        }
        print_table(task_info, title="回测配置")

        # ==================== 1. 加载数据 ====================
        print_info("\n[1/4] 加载回测数据...")

        # 生成模拟数据（实际应从数据库加载）
        dates = pd.date_range(start, end, freq="D")
        n_days = len(dates)
        n_stocks = 50

        # 模拟价格数据
        np.random.seed(42)
        stocks = [f"{600000+i:06d}" for i in range(n_stocks)]

        price_data = {}
        for i, stock in enumerate(stocks):
            base_price = 10.0 + i * 0.1
            returns = np.random.normal(0.0002, 0.015, n_days)
            prices = base_price * (1 + returns).cumprod()
            price_data[stock] = prices

        prices_df = pd.DataFrame(price_data, index=dates)
        print_info(f"  已加载 {len(prices_df)} 天 x {len(stocks)} 只股票")

        # ==================== 2. 生成信号 ====================
        print_info(f"[2/4] 运行{strategy.upper()}策略生成信号...")

        # 模拟信号：基于动量
        signals_df = prices_df.pct_change(20).shift(-5) * 100  # 简化的动量信号

        # ==================== 3. 运行回测 ====================
        print_info("[3/4] 执行回测...")

        with create_progress_bar() as progress:
            task = progress.add_task("[cyan]回测中...", total=None)

            # 创建回测引擎
            engine = BacktestEngine(
                initial_capital=capital,
                commission_rate=0.0003,
                stamp_tax_rate=0.001,
                slippage=0.001,
                verbose=False,
            )

            # 运行回测
            results = engine.run_vectorized_backtest(
                prices=prices_df, signals=signals_df, n_positions=10
            )

            progress.update(task, completed=True)

        # ==================== 4. 分析结果 ====================
        print_info("[4/4] 分析回测结果...")

        # 获取组合净值和收益率
        portfolio_value = results["portfolio_value"]
        daily_returns = results["daily_returns"]

        # 计算绩效指标
        metrics = calculate_performance_metrics(portfolio_value, daily_returns)

        # 交易统计
        trades_count = len(results.get("trades", []))

        # ==================== 显示结果 ====================
        print_info("\n[bold]回测完成![/bold]", bold=True)

        # 格式化指标
        formatted_metrics = {
            "总收益率": f"{metrics['总收益率']:.2f}%",
            "年化收益率": f"{metrics['年化收益率']:.2f}%",
            "波动率": f"{metrics['波动率']:.2f}%",
            "夏普比率": f"{metrics['夏普比率']:.2f}",
            "最大回撤": f"{metrics['最大回撤']:.2f}%",
            "胜率": f"{metrics['胜率']:.2f}%",
            "交易天数": metrics["交易天数"],
        }

        if trades_count > 0:
            formatted_metrics["交易次数"] = trades_count

        print_table(formatted_metrics, title="回测结果")

        # 绘制净值曲线（文本模式）
        print_info("\n净值曲线:")
        print_info(
            f"  起始: {portfolio_value.iloc[0]:,.2f} -> 结束: {portfolio_value.iloc[-1]:,.2f}"
        )

        # ==================== 保存报告 ====================
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if report == "html" or visualize:
                if visualize:
                    # 生成交互式可视化报告
                    print_info("\n正在生成可视化报告...")

                    try:
                        from visualization.report_generator import HTMLReportGenerator
                        import pandas as pd
                        import numpy as np

                        report_gen = HTMLReportGenerator()

                        # TODO: 集成实际的回测引擎数据
                        # 当前使用模拟数据作为示例，实际应从backtest_result中提取：
                        # - equity_curve: 策略净值曲线
                        # - returns: 策略收益率序列
                        # - positions: 持仓DataFrame（可选）
                        # - benchmark_curve/returns: 基准数据（可选）

                        dates = pd.date_range(
                            start=start or datetime.now() - pd.Timedelta(days=365),
                            end=end or datetime.now(),
                            freq='D'
                        )

                        # 使用模拟数据生成报告
                        equity_curve = pd.Series(
                            np.cumprod(1 + np.random.randn(len(dates)) * 0.01 + 0.0003),
                            index=dates
                        )
                        returns = pd.Series(
                            np.random.randn(len(dates)) * 0.01 + 0.0003,
                            index=dates
                        )

                        report_gen.generate_backtest_report(
                            equity_curve=equity_curve,
                            returns=returns,
                            metrics=formatted_metrics,
                            strategy_name=strategy.upper(),
                            output_path=str(output_path)
                        )
                        print_success(f"\n✓ 可视化报告已保存: {output_path}")

                    except ImportError:
                        print_error("\n可视化模块未安装，请运行: pip install plotly kaleido jinja2")
                        print_info("继续生成简单HTML报告...")
                        visualize = False

                if not visualize:
                    # 生成简单HTML报告（不含可视化图表）
                    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>回测报告 - {strategy.upper()}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
    </style>
</head>
<body>
    <h1>回测报告</h1>
    <h2>策略: {strategy.upper()}</h2>
    <h3>绩效指标</h3>
    <table>
"""
                    for key, value in formatted_metrics.items():
                        html_content += f"<tr><td>{key}</td><td>{value}</td></tr>\n"

                    html_content += """
    </table>
</body>
</html>
"""
                    output_path.write_text(html_content)
                    print_success(f"\nHTML报告已保存: {output_path}")

            elif report == "json":
                # 保存JSON格式
                import json

                report_data = {
                    "strategy": strategy,
                    "config": task_info,
                    "metrics": metrics,
                }

                with open(output_path, "w") as f:
                    json.dump(report_data, f, indent=2)

                print_success(f"\nJSON报告已保存: {output_path}")

            else:
                # 保存文本格式
                with open(output_path, "w") as f:
                    f.write("=" * 60 + "\n")
                    f.write(f"回测报告 - {strategy.upper()}\n")
                    f.write("=" * 60 + "\n\n")

                    for key, value in formatted_metrics.items():
                        f.write(f"{key}: {value}\n")

                print_success(f"\n文本报告已保存: {output_path}")

    except KeyboardInterrupt:
        print_error("\n\n用户中断回测")
        sys.exit(130)
    except Exception as e:
        logger.exception("回测执行失败")
        print_error(f"回测失败: {e}")
        sys.exit(1)
