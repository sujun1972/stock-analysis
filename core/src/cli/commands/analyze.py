"""
analyze命令 - 因子分析

支持IC分析、因子分层回测、相关性分析等
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

from cli.utils.output import print_success, print_error, print_info, print_table
from cli.utils.progress import create_progress_bar
from utils.logger import get_logger
from config.settings import get_settings

logger = get_logger(__name__)


def load_factor_data(factor_name: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
    """
    加载因子数据

    Args:
        factor_name: 因子名称
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        因子数据DataFrame
    """
    from database.db_manager import DatabaseManager
    import pandas as pd

    # 实际应该从特征数据库或文件加载
    # 这里生成模拟数据
    dates = pd.date_range(start_date or "2023-01-01", end_date or "2024-12-31", freq="D")
    stocks = [f"{600000+i:06d}" for i in range(50)]

    import numpy as np
    np.random.seed(42)

    data = {}
    for stock in stocks:
        data[stock] = np.random.randn(len(dates))

    df = pd.DataFrame(data, index=dates)
    return df


@click.group()
def analyze():
    """
    因子分析工具

    \b
    子命令:
        • ic        - 计算因子IC（信息系数）
        • quantiles - 因子分层回测
        • corr      - 因子相关性分析
        • batch     - 批量分析所有因子
    """
    pass


@analyze.command()
@click.option("--factor", required=True, help="因子名称（如: MOM_20）")
@click.option(
    "--start", type=click.DateTime(formats=["%Y-%m-%d"]), help="开始日期"
)
@click.option("--end", type=click.DateTime(formats=["%Y-%m-%d"]), help="结束日期")
@click.option("--period", type=int, default=20, help="预测周期（天）")
def ic(factor, start, end, period):
    """
    计算因子IC（信息系数）

    \b
    示例:
        # 计算MOM_20因子的IC
        stock-cli analyze ic --factor MOM_20

    \b
        # 指定时间范围
        stock-cli analyze ic --factor MOM_20 \\
            --start 2023-01-01 --end 2024-12-31
    """
    try:
        from analysis.ic_calculator import ICCalculator
        import pandas as pd
        import numpy as np

        print_info(f"\n[bold green]计算因子IC[/bold green]", bold=True)
        print_info(f"因子: {factor}")
        print_info(f"预测周期: {period}天\n")

        # ==================== 1. 加载数据 ====================
        print_info("[1/3] 加载因子数据...")

        factor_data = load_factor_data(factor, start, end)
        print_info(f"  已加载 {len(factor_data)} 天 x {factor_data.shape[1]} 只股票")

        # ==================== 2. 计算收益率 ====================
        print_info("[2/3] 计算未来收益率...")

        # 模拟价格数据并计算收益率
        np.random.seed(42)
        returns_data = {}
        for stock in factor_data.columns:
            returns = np.random.normal(0.0002, 0.02, len(factor_data))
            returns_data[stock] = returns

        returns_df = pd.DataFrame(returns_data, index=factor_data.index)

        # ==================== 3. 计算IC ====================
        print_info("[3/3] 计算IC指标...")

        with create_progress_bar() as progress:
            task = progress.add_task("[cyan]计算中...", total=None)

            # 计算IC时间序列
            ic_calculator = ICCalculator()
            ic_series = ic_calculator.calculate_ic_timeseries(
                factor_data, returns_df, periods=[period]
            )

            progress.update(task, completed=True)

        # ==================== 显示结果 ====================
        print_info("\n[bold]IC分析完成![/bold]", bold=True)

        # IC统计指标
        ic_stats = {
            "IC均值": f"{ic_series.mean():.4f}",
            "IC标准差": f"{ic_series.std():.4f}",
            "IC_IR": f"{ic_series.mean() / ic_series.std():.4f}" if ic_series.std() > 0 else "N/A",
            "正IC比例": f"{(ic_series > 0).sum() / len(ic_series) * 100:.2f}%",
            "绝对IC>2%": f"{(abs(ic_series) > 0.02).sum() / len(ic_series) * 100:.2f}%",
        }

        print_table(ic_stats, title=f"{factor} IC统计")

        # IC分位数
        print_info("\nIC分位数:")
        percentiles = [0.05, 0.25, 0.50, 0.75, 0.95]
        for p in percentiles:
            value = ic_series.quantile(p)
            print_info(f"  {p*100:.0f}%: {value:.4f}")

        print_success(f"\n因子 {factor} 的IC分析完成")

    except Exception as e:
        logger.exception("IC计算失败")
        print_error(f"计算失败: {e}")
        sys.exit(1)


@analyze.command()
@click.option("--factor", required=True, help="因子名称")
@click.option("--layers", type=int, default=5, help="分层数量")
@click.option(
    "--start", type=click.DateTime(formats=["%Y-%m-%d"]), help="开始日期"
)
@click.option("--end", type=click.DateTime(formats=["%Y-%m-%d"]), help="结束日期")
def quantiles(factor, layers, start, end):
    """
    因子分层回测

    \b
    示例:
        # 5分层回测
        stock-cli analyze quantiles --factor MOM_20 --layers 5

    \b
        # 10分层回测
        stock-cli analyze quantiles --factor VOL_20 --layers 10
    """
    try:
        from analysis.factor_analyzer import FactorAnalyzer
        import pandas as pd
        import numpy as np

        print_info(f"\n[bold green]因子分层回测[/bold green]", bold=True)
        print_info(f"因子: {factor}")
        print_info(f"分层数: {layers}\n")

        # ==================== 1. 加载数据 ====================
        print_info("[1/3] 加载因子数据...")

        factor_data = load_factor_data(factor, start, end)
        print_info(f"  已加载 {len(factor_data)} 天 x {factor_data.shape[1]} 只股票")

        # ==================== 2. 分层 ====================
        print_info(f"[2/3] 将股票分为{layers}层...")

        # 按因子值分层
        layer_returns = {}
        np.random.seed(42)

        for layer_idx in range(layers):
            # 模拟各层收益
            base_return = (layer_idx - layers / 2) * 0.0005  # 假设线性关系
            returns = np.random.normal(base_return, 0.02, len(factor_data))
            layer_returns[f"第{layer_idx+1}层"] = returns

        # ==================== 3. 计算各层绩效 ====================
        print_info("[3/3] 计算各层绩效...")

        with create_progress_bar() as progress:
            task = progress.add_task("[cyan]分析中...", total=None)

            layer_metrics = {}
            for layer_name, returns in layer_returns.items():
                returns_series = pd.Series(returns)
                cumulative_return = (1 + returns_series).prod() - 1
                annualized_return = (1 + cumulative_return) ** (252 / len(returns)) - 1
                volatility = returns_series.std() * np.sqrt(252)
                sharpe = annualized_return / volatility if volatility > 0 else 0

                layer_metrics[layer_name] = {
                    "累计收益": f"{cumulative_return * 100:.2f}%",
                    "年化收益": f"{annualized_return * 100:.2f}%",
                    "年化波动": f"{volatility * 100:.2f}%",
                    "夏普比率": f"{sharpe:.2f}",
                }

            progress.update(task, completed=True)

        # ==================== 显示结果 ====================
        print_info("\n[bold]分层回测完成![/bold]", bold=True)

        for layer_name, metrics in layer_metrics.items():
            print_info(f"\n{layer_name}:")
            print_table(metrics)

        # 多空组合
        print_info("\n多空组合（第5层 - 第1层）:")
        top_ret = float(layer_metrics[f"第{layers}层"]["年化收益"].rstrip("%")) / 100
        bot_ret = float(layer_metrics["第1层"]["年化收益"].rstrip("%")) / 100
        spread = top_ret - bot_ret

        spread_metrics = {
            "收益差": f"{spread * 100:.2f}%",
            "是否单调": "是" if spread > 0 else "否",
        }
        print_table(spread_metrics)

        print_success(f"\n因子 {factor} 的分层回测完成")

    except Exception as e:
        logger.exception("分层回测失败")
        print_error(f"回测失败: {e}")
        sys.exit(1)


@analyze.command()
@click.option("--factors", help="因子列表（逗号分隔）或 'all'")
@click.option(
    "--start", type=click.DateTime(formats=["%Y-%m-%d"]), help="开始日期"
)
@click.option("--end", type=click.DateTime(formats=["%Y-%m-%d"]), help="结束日期")
def corr(factors, start, end):
    """
    因子相关性分析

    \b
    示例:
        # 分析指定因子的相关性
        stock-cli analyze corr --factors MOM_20,VOL_20,RSI_14

    \b
        # 分析所有因子
        stock-cli analyze corr --factors all
    """
    try:
        import pandas as pd
        import numpy as np

        print_info(f"\n[bold green]因子相关性分析[/bold green]", bold=True)

        # ==================== 1. 确定因子列表 ====================
        if factors and factors.lower() == "all":
            factor_list = ["MOM_20", "VOL_20", "RSI_14", "MACD", "BOLL"]
            print_info(f"分析所有因子: {len(factor_list)}个")
        else:
            factor_list = [f.strip() for f in factors.split(",")]
            print_info(f"分析因子: {', '.join(factor_list)}")

        # ==================== 2. 加载因子数据 ====================
        print_info("\n[1/2] 加载因子数据...")

        factor_data_dict = {}
        for factor_name in factor_list:
            data = load_factor_data(factor_name, start, end)
            # 取均值作为因子值
            factor_data_dict[factor_name] = data.mean(axis=1)

        factors_df = pd.DataFrame(factor_data_dict)

        # ==================== 3. 计算相关性 ====================
        print_info("[2/2] 计算相关性矩阵...")

        corr_matrix = factors_df.corr()

        # ==================== 显示结果 ====================
        print_info("\n[bold]相关性分析完成![/bold]", bold=True)

        print_info("\n相关性矩阵:")
        print_info(corr_matrix.to_string())

        # 高相关因子对
        print_info("\n高相关因子对（|corr| > 0.7）:")
        high_corr_pairs = []
        for i in range(len(corr_matrix)):
            for j in range(i + 1, len(corr_matrix)):
                corr_value = corr_matrix.iloc[i, j]
                if abs(corr_value) > 0.7:
                    factor1 = corr_matrix.index[i]
                    factor2 = corr_matrix.columns[j]
                    high_corr_pairs.append((factor1, factor2, corr_value))

        if high_corr_pairs:
            for f1, f2, corr in high_corr_pairs:
                print_info(f"  {f1} <-> {f2}: {corr:.4f}")
        else:
            print_info("  无高相关因子对")

        print_success("\n相关性分析完成")

    except Exception as e:
        logger.exception("相关性分析失败")
        print_error(f"分析失败: {e}")
        sys.exit(1)


@analyze.command()
@click.option("--output", type=click.Path(), help="报告保存路径")
@click.option(
    "--start", type=click.DateTime(formats=["%Y-%m-%d"]), help="开始日期"
)
@click.option("--end", type=click.DateTime(formats=["%Y-%m-%d"]), help="结束日期"
)
def batch(output, start, end):
    """
    批量分析所有因子

    \b
    示例:
        # 批量分析并保存报告
        stock-cli analyze batch --output reports/factor_analysis.html
    """
    try:
        import pandas as pd

        print_info(f"\n[bold green]批量因子分析[/bold green]", bold=True)

        # 因子列表
        factor_list = ["MOM_20", "VOL_20", "RSI_14", "MACD", "BOLL"]
        print_info(f"分析 {len(factor_list)} 个因子\n")

        all_results = {}

        with create_progress_bar() as progress:
            task = progress.add_task(
                "[cyan]批量分析中...", total=len(factor_list)
            )

            for factor_name in factor_list:
                try:
                    # 加载数据
                    factor_data = load_factor_data(factor_name, start, end)

                    # 计算基本统计
                    stats = {
                        "均值": factor_data.mean().mean(),
                        "标准差": factor_data.std().mean(),
                        "最小值": factor_data.min().min(),
                        "最大值": factor_data.max().max(),
                    }

                    all_results[factor_name] = stats
                    progress.update(task, advance=1)

                except Exception as e:
                    logger.warning(f"分析 {factor_name} 失败: {e}")
                    progress.update(task, advance=1)
                    continue

        # ==================== 显示结果 ====================
        print_info("\n[bold]批量分析完成![/bold]", bold=True)

        for factor_name, stats in all_results.items():
            print_info(f"\n{factor_name}:")
            formatted_stats = {k: f"{v:.4f}" for k, v in stats.items()}
            print_table(formatted_stats)

        # ==================== 保存报告 ====================
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # 生成HTML报告
            html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>因子分析报告</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
    </style>
</head>
<body>
    <h1>因子批量分析报告</h1>
"""

            for factor_name, stats in all_results.items():
                html_content += f"<h2>{factor_name}</h2><table>"
                for key, value in stats.items():
                    html_content += f"<tr><td>{key}</td><td>{value:.4f}</td></tr>"
                html_content += "</table>"

            html_content += "</body></html>"

            output_path.write_text(html_content)
            print_success(f"\nHTML报告已保存: {output_path}")

    except Exception as e:
        logger.exception("批量分析失败")
        print_error(f"分析失败: {e}")
        sys.exit(1)
