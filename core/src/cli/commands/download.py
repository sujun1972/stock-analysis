"""
download命令 - 下载股票数据

支持从AkShare或Tushare下载股票历史数据到TimescaleDB
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
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


def get_stock_list(provider: str = "akshare", limit: Optional[int] = None) -> List[str]:
    """
    获取股票列表

    Args:
        provider: 数据源
        limit: 限制数量

    Returns:
        股票代码列表
    """
    try:
        from a_stock_list_fetcher import fetch_akshare_stock_list
        import pandas as pd

        # 使用临时文件
        temp_file = "/tmp/stock_list.csv"
        if fetch_akshare_stock_list(save_path=temp_file, save_to_db=False):
            df = pd.read_csv(temp_file)
            symbols = df["symbol"].tolist()

            if limit:
                symbols = symbols[:limit]

            return symbols
        else:
            raise Exception("获取股票列表失败")
    except Exception as e:
        logger.error(f"获取股票列表失败: {e}")
        raise


def download_single_stock(
    symbol: str, start_date: datetime, end_date: datetime, provider: str
) -> bool:
    """
    下载单只股票数据

    Args:
        symbol: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        provider: 数据源

    Returns:
        是否成功
    """
    try:
        from providers.provider_factory import DataProviderFactory
        from database.db_manager import DatabaseManager

        # 创建数据提供者
        factory = DataProviderFactory()
        data_provider = factory.create_provider(provider)

        # 获取数据
        df = data_provider.get_stock_daily(
            symbol=symbol, start_date=start_date.strftime("%Y%m%d"), end_date=end_date.strftime("%Y%m%d")
        )

        if df is None or df.empty:
            logger.warning(f"{symbol}: 无数据")
            return False

        # 保存到数据库
        db_manager = DatabaseManager()
        table_name = f"stock_daily_{symbol}"

        # 确保表存在
        db_manager.create_stock_daily_table(table_name)

        # 插入数据
        db_manager.insert_dataframe(table_name, df, if_exists="replace")

        logger.info(f"{symbol}: 下载完成，共 {len(df)} 条记录")
        return True

    except Exception as e:
        logger.error(f"{symbol}: 下载失败 - {e}")
        return False


@click.command()
@click.option(
    "--symbols",
    type=SymbolListType(),
    help='股票代码（逗号分隔，如: 000001,600000）或 "all" 表示所有股票',
)
@click.option("--days", type=int, help="下载最近N天数据（与--start/--end互斥）")
@click.option(
    "--start", type=click.DateTime(formats=["%Y-%m-%d"]), help="开始日期 (YYYY-MM-DD)"
)
@click.option("--end", type=click.DateTime(formats=["%Y-%m-%d"]), help="结束日期 (YYYY-MM-DD)")
@click.option(
    "--provider",
    type=click.Choice(["akshare", "tushare"], case_sensitive=False),
    help="数据源（默认从配置文件读取）",
)
@click.option("--limit", type=int, help="限制下载股票数量（用于测试）")
@click.option("--workers", type=int, default=4, help="并行下载线程数")
@click.pass_context
def download(ctx, symbols, days, start, end, provider, limit, workers):
    """
    下载股票历史数据到数据库

    \b
    示例:
        # 下载所有股票最近30天数据
        stock-cli download --days 30

    \b
        # 下载指定股票指定时间段
        stock-cli download --symbols 000001,600000 \\
            --start 2024-01-01 --end 2024-12-31

    \b
        # 使用Tushare数据源（需配置TOKEN）
        stock-cli download --provider tushare --days 60

    \b
        # 测试下载前10只股票
        stock-cli download --limit 10 --days 7
    """
    try:
        # ==================== 参数处理 ====================
        settings = get_settings()

        # 确定数据源
        if provider is None:
            provider = settings.DATA_PROVIDER
            logger.info(f"使用默认数据源: {provider}")

        # 检查Tushare token
        if provider == "tushare" and not settings.TUSHARE_TOKEN:
            print_error("使用Tushare数据源需要配置TOKEN")
            print_info("请运行 'stock-cli init' 配置TOKEN，或设置环境变量 DATA_TUSHARE_TOKEN")
            sys.exit(1)

        # 确定日期范围
        if days is not None:
            if start or end:
                print_error("--days 参数与 --start/--end 参数互斥，请只使用其中一种")
                sys.exit(1)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
        elif start and end:
            start_date = start
            end_date = end
        else:
            # 默认下载最近30天
            print_info("未指定日期范围，默认下载最近30天数据")
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)

        # 确定股票列表
        if symbols == "all" or symbols is None:
            print_info(f"获取所有A股列表...")
            symbol_list = get_stock_list(provider=provider, limit=limit)
        else:
            symbol_list = symbols
            if limit:
                symbol_list = symbol_list[:limit]

        # ==================== 显示任务信息 ====================
        print_info(f"\n[bold green]开始下载任务[/bold green]", bold=True)
        task_info = {
            "股票数量": len(symbol_list),
            "时间范围": f"{start_date.date()} ~ {end_date.date()}",
            "数据源": provider,
            "并行线程": workers,
        }
        print_table(task_info, title="任务信息")

        # ==================== 执行下载 ====================
        with ProgressTracker(
            total=len(symbol_list), description="[cyan]下载中...", show_time=True
        ) as tracker:

            if workers == 1:
                # 单线程顺序下载
                for symbol in symbol_list:
                    try:
                        success = download_single_stock(symbol, start_date, end_date, provider)
                        if success:
                            tracker.mark_success(symbol)
                        else:
                            tracker.mark_failure(symbol, "无数据")
                    except Exception as e:
                        tracker.mark_failure(symbol, str(e))
            else:
                # 多线程并行下载
                from concurrent.futures import ThreadPoolExecutor, as_completed

                with ThreadPoolExecutor(max_workers=workers) as executor:
                    # 提交所有任务
                    futures = {
                        executor.submit(download_single_stock, symbol, start_date, end_date, provider): symbol
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
        print_info("\n[bold]下载完成![/bold]", bold=True)
        print_table(summary, title="下载结果")

        if tracker.fail_count > 0:
            print_info(
                f"\n有 {tracker.fail_count} 只股票下载失败，详细信息请查看日志文件"
            )

        # 非零退出码表示有失败
        if tracker.fail_count > 0:
            sys.exit(1)

    except KeyboardInterrupt:
        print_error("\n\n用户中断下载")
        sys.exit(130)
    except Exception as e:
        logger.exception("下载命令执行失败")
        print_error(f"下载失败: {e}")
        sys.exit(1)
