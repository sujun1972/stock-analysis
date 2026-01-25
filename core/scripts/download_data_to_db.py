#!/usr/bin/env python3
"""
股票数据下载脚本（数据库版本）
支持将数据直接保存到PostgreSQL/TimescaleDB数据库
"""

import sys
import os
from pathlib import Path
import time
from datetime import datetime, timedelta
import argparse
import logging

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database.db_manager import DatabaseManager
from a_stock_list_fetcher import fetch_akshare_stock_list
import akshare as ak
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class StockDataDownloader:
    """股票数据下载器（数据库版）"""

    def __init__(self, db_manager: DatabaseManager):
        """
        初始化下载器

        Args:
            db_manager: 数据库管理器实例
        """
        self.db = db_manager

    def download_stock_list(self) -> pd.DataFrame:
        """
        下载并保存股票列表到数据库

        Returns:
            股票列表DataFrame
        """
        logger.info("=" * 60)
        logger.info("1. 下载A股股票列表")
        logger.info("=" * 60)

        try:
            # 获取股票列表
            stock_info_df = ak.stock_info_a_code_name()

            if stock_info_df is None or stock_info_df.empty:
                raise ValueError("获取股票列表失败，返回数据为空")

            # 重命名列以匹配数据库字段
            stock_info_df = stock_info_df.rename(columns={
                'code': 'code',
                'name': 'name'
            })

            # 添加市场类型
            stock_info_df['market'] = stock_info_df['code'].apply(
                lambda x: '上海主板' if x.startswith(('60', '68'))
                else '深圳主板' if x.startswith('000')
                else '创业板' if x.startswith('300')
                else '科创板' if x.startswith('688')
                else '北交所' if x.startswith(('8', '4'))
                else '其他'
            )

            logger.info(f"✓ 获取到 {len(stock_info_df)} 只股票")

            # 保存到数据库
            count = self.db.save_stock_list(stock_info_df)
            logger.info(f"✓ 已保存到数据库: {count} 条记录\n")

            return stock_info_df

        except Exception as e:
            logger.error(f"❌ 下载股票列表失败: {e}")
            raise

    def download_daily_data(self, stock_code: str, years: int = 5) -> pd.DataFrame:
        """
        下载单只股票的日线数据

        Args:
            stock_code: 股票代码
            years: 获取数据的年数

        Returns:
            日线数据DataFrame
        """
        try:
            # 计算日期范围
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=years * 365)).strftime('%Y%m%d')

            # 调用AkShare获取历史数据
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"  # 前复权
            )

            if df is None or df.empty:
                logger.warning(f"  ⚠ {stock_code}: 无数据")
                return None

            # 重命名列以匹配数据库字段（AkShare返回中文列名）
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'pct_change',
                '涨跌额': 'change',
                '换手率': 'turnover'
            })

            # 设置日期为索引
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')

            return df

        except Exception as e:
            logger.error(f"  ❌ {stock_code}: 下载失败 - {e}")
            return None

    def batch_download(self,
                      stock_list: pd.DataFrame,
                      years: int = 5,
                      max_stocks: int = None,
                      delay: float = 0.5,
                      markets: list = None):
        """
        批量下载股票数据

        Args:
            stock_list: 股票列表DataFrame
            years: 获取数据的年数
            max_stocks: 最大下载数量（None表示全部）
            delay: 请求间隔（秒）
            markets: 要下载的市场类型列表（None表示全部）
        """
        logger.info("=" * 60)
        logger.info("2. 批量下载股票日线数据")
        logger.info("=" * 60)

        # 过滤市场
        if markets:
            stock_list = stock_list[stock_list['market'].isin(markets)]
            logger.info(f"市场过滤: {markets} → {len(stock_list)} 只股票")

        # 限制数量
        if max_stocks:
            stock_list = stock_list.head(max_stocks)
            logger.info(f"数量限制: 前 {max_stocks} 只股票")

        total = len(stock_list)
        success_count = 0
        fail_count = 0
        start_time = time.time()

        logger.info(f"\n开始下载 {total} 只股票的 {years} 年历史数据...")
        logger.info(f"请求间隔: {delay} 秒\n")

        for idx, (_, row) in enumerate(stock_list.iterrows(), 1):
            stock_code = row['code']
            stock_name = row.get('name', '')

            logger.info(f"[{idx}/{total}] {stock_code} ({stock_name})")

            try:
                # 下载数据
                df = self.download_daily_data(stock_code, years)

                if df is not None and not df.empty:
                    # 保存到数据库
                    count = self.db.save_daily_data(df, stock_code)
                    success_count += 1
                    logger.info(f"  ✓ 保存成功: {count} 条记录")
                else:
                    fail_count += 1

                # 延迟避免限流
                if idx < total:
                    time.sleep(delay)

            except Exception as e:
                fail_count += 1
                logger.error(f"  ❌ 处理失败: {e}")
                continue

            # 每10只股票显示一次进度
            if idx % 10 == 0:
                elapsed = time.time() - start_time
                avg_time = elapsed / idx
                eta = avg_time * (total - idx)
                logger.info(f"\n进度: {idx}/{total} | 成功: {success_count} | 失败: {fail_count} | 预计剩余: {eta/60:.1f}分钟\n")

        # 最终统计
        elapsed = time.time() - start_time
        logger.info("\n" + "=" * 60)
        logger.info("下载完成！")
        logger.info("=" * 60)
        logger.info(f"总数: {total} | 成功: {success_count} | 失败: {fail_count}")
        logger.info(f"耗时: {elapsed/60:.1f} 分钟")
        logger.info("=" * 60 + "\n")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='下载A股数据到数据库')

    parser.add_argument('--years', type=int, default=5,
                       help='获取数据的年数（默认：5）')
    parser.add_argument('--max-stocks', type=int, default=None,
                       help='最大下载数量（默认：全部）')
    parser.add_argument('--delay', type=float, default=0.5,
                       help='请求间隔秒数（默认：0.5）')
    parser.add_argument('--markets', nargs='+', default=None,
                       help='市场类型过滤（如：上海主板 创业板 科创板）')
    parser.add_argument('--init-db', action='store_true',
                       help='初始化数据库表结构')
    parser.add_argument('--stock-list-only', action='store_true',
                       help='仅下载股票列表，不下载日线数据')

    args = parser.parse_args()

    print("\n" + "📊" * 30)
    print("A股数据下载工具（数据库版）")
    print("📊" * 30 + "\n")

    try:
        # 1. 初始化数据库管理器
        logger.info("连接数据库...")
        db = DatabaseManager()
        logger.info("✓ 数据库连接成功\n")

        # 2. 初始化数据库（如果需要）
        if args.init_db:
            logger.info("初始化数据库表结构...")
            db.init_database()

        # 3. 创建下载器
        downloader = StockDataDownloader(db)

        # 4. 下载股票列表
        stock_list = downloader.download_stock_list()

        # 5. 下载日线数据（除非仅下载股票列表）
        if not args.stock_list_only:
            downloader.batch_download(
                stock_list=stock_list,
                years=args.years,
                max_stocks=args.max_stocks,
                delay=args.delay,
                markets=args.markets
            )

        logger.info("✅ 全部完成！\n")

        # 6. 显示数据库统计
        logger.info("=" * 60)
        logger.info("数据库统计")
        logger.info("=" * 60)
        stock_count = len(db.get_stock_list())
        logger.info(f"股票数量: {stock_count}")
        logger.info("=" * 60 + "\n")

    except Exception as e:
        logger.error(f"\n❌ 程序执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
