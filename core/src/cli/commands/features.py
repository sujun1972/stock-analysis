"""
features命令 - 计算技术指标和Alpha因子

支持计算60+技术指标和125+ Alpha因子
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import click

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from cli.utils.output import print_success, print_error, print_info, print_table
from cli.utils.progress import ProgressTracker
from cli.utils.validators import SymbolListType
from utils.logger import get_logger
from config.settings import get_settings

logger = get_logger(__name__)


def compute_features_for_stock(
    symbol: str,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    output_format: str,
    output_dir: Path,
) -> bool:
    """
    计算单只股票的特征

    Args:
        symbol: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        output_format: 输出格式
        output_dir: 输出目录

    Returns:
        是否成功
    """
    try:
        from database.db_manager import DatabaseManager
        from features.technical_indicators import TechnicalIndicators
        from features.alpha_factors import AlphaFactors
        import pandas as pd

        # 从数据库加载数据
        db_manager = DatabaseManager()
        table_name = f"stock_daily_{symbol}"

        query = f"SELECT * FROM {table_name}"
        if start_date and end_date:
            query += f" WHERE trade_date >= '{start_date.date()}' AND trade_date <= '{end_date.date()}'"
        query += " ORDER BY trade_date"

        df = db_manager.execute_query(query)

        if df is None or df.empty:
            logger.warning(f"{symbol}: 无数据")
            return False

        # 计算技术指标
        tech_indicators = TechnicalIndicators(df)
        df_with_indicators = tech_indicators.calculate_all_indicators()

        # 计算Alpha因子
        alpha_factors = AlphaFactors(df_with_indicators)
        df_with_factors = alpha_factors.calculate_all_factors()

        # 保存结果
        output_file = output_dir / f"{symbol}.{output_format}"

        if output_format == "csv":
            df_with_factors.to_csv(output_file, index=False)
        elif output_format == "parquet":
            df_with_factors.to_parquet(output_file, index=False)
        elif output_format == "hdf5":
            df_with_factors.to_hdf(output_file, key="data", mode="w")
        else:
            raise ValueError(f"不支持的输出格式: {output_format}")

        logger.info(
            f"{symbol}: 计算完成，共 {len(df_with_factors)} 条记录，"
            f"{len(df_with_factors.columns)} 个特征"
        )
        return True

    except Exception as e:
        logger.error(f"{symbol}: 计算失败 - {e}")
        return False


@click.command()
@click.option(
    "--symbols",
    type=SymbolListType(),
    required=True,
    help='股票代码（逗号分隔，如: 000001,600000）或 "all" 表示所有股票',
)
@click.option(
    "--start", type=click.DateTime(formats=["%Y-%m-%d"]), help="开始日期 (YYYY-MM-DD)"
)
@click.option("--end", type=click.DateTime(formats=["%Y-%m-%d"]), help="结束日期 (YYYY-MM-DD)")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["csv", "parquet", "hdf5"], case_sensitive=False),
    default="parquet",
    help="输出格式",
)
@click.option(
    "--output",
    type=click.Path(file_okay=False),
    help="输出目录（默认从配置读取）",
)
@click.option("--workers", type=int, default=4, help="并行计算线程数")
@click.pass_context
def features(ctx, symbols, start, end, output_format, output, workers):
    """
    计算股票技术指标和Alpha因子

    \b
    功能:
        • 60+ 技术指标 (MA, EMA, RSI, MACD, Bollinger, KDJ等)
        • 125+ Alpha因子 (动量、反转、波动率、成交量等)
        • 支持多种输出格式 (CSV, Parquet, HDF5)

    \b
    示例:
        # 计算指定股票的所有特征
        stock-cli features --symbols 000001,600000

    \b
        # 计算所有股票的特征并保存为Parquet格式
        stock-cli features --symbols all --format parquet

    \b
        # 计算指定时间范围的特征
        stock-cli features --symbols 000001 \\
            --start 2024-01-01 --end 2024-12-31
    """
    try:
        # ==================== 参数处理 ====================
        settings = get_settings()

        # 确定股票列表
        if symbols == "all":
            print_info("获取所有股票列表...")
            from ..commands.download import get_stock_list

            symbol_list = get_stock_list()
        else:
            symbol_list = symbols

        # 确定输出目录
        if output is None:
            output_dir = settings.PATH_DATA_PATH / "features"
        else:
            output_dir = Path(output)

        output_dir.mkdir(parents=True, exist_ok=True)

        # ==================== 显示任务信息 ====================
        print_info("\n[bold green]开始特征计算[/bold green]", bold=True)
        task_info = {
            "股票数量": len(symbol_list),
            "时间范围": f"{start.date() if start else '全部'} ~ {end.date() if end else '全部'}",
            "输出格式": output_format.upper(),
            "输出目录": str(output_dir),
            "并行线程": workers,
        }
        print_table(task_info, title="任务信息")

        # ==================== 执行计算 ====================
        with ProgressTracker(
            total=len(symbol_list), description="[cyan]计算特征...", show_time=True
        ) as tracker:

            if workers == 1:
                # 单线程顺序计算
                for symbol in symbol_list:
                    try:
                        success = compute_features_for_stock(
                            symbol, start, end, output_format, output_dir
                        )
                        if success:
                            tracker.mark_success(symbol)
                        else:
                            tracker.mark_failure(symbol, "无数据")
                    except Exception as e:
                        tracker.mark_failure(symbol, str(e))
            else:
                # 多线程并行计算
                from concurrent.futures import ThreadPoolExecutor, as_completed

                with ThreadPoolExecutor(max_workers=workers) as executor:
                    # 提交所有任务
                    futures = {
                        executor.submit(
                            compute_features_for_stock,
                            symbol,
                            start,
                            end,
                            output_format,
                            output_dir,
                        ): symbol
                        for symbol in symbol_list
                    }

                    # 处理完成的任务
                    for future in as_completed(futures):
                        symbol = futures[future]
                        try:
                            success = future.result()
                            if success:
                                tracker.mark_success(symbol)
                            else:
                                tracker.mark_failure(symbol, "无数据")
                        except Exception as e:
                            tracker.mark_failure(symbol, str(e))

        # ==================== 显示结果 ====================
        summary = tracker.get_summary()
        print_info("\n[bold]特征计算完成![/bold]", bold=True)
        print_table(summary, title="计算结果")

        if tracker.fail_count > 0:
            print_info(
                f"\n有 {tracker.fail_count} 只股票计算失败，详细信息请查看日志文件"
            )

        print_success(f"\n特征已保存至: {output_dir}")

        # 非零退出码表示有失败
        if tracker.fail_count > 0:
            sys.exit(1)

    except KeyboardInterrupt:
        print_error("\n\n用户中断计算")
        sys.exit(130)
    except Exception as e:
        logger.exception("特征计算命令执行失败")
        print_error(f"计算失败: {e}")
        sys.exit(1)
