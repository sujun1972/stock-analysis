#!/usr/bin/env python3
"""
批量下载A股历史数据脚本
- 自动获取股票列表并过滤ST/退市/停牌股票
- 批量下载5年历史日线数据（前复权）
- 数据清洗和验证
- 保存到本地文件
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import time
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data_fetcher import DataFetcher
from a_stock_list_fetcher import fetch_akshare_stock_list
from data.stock_filter import StockFilter, filter_stocks_by_market
from data.data_cleaner import DataCleaner
from config.trading_rules import AdjustType, DataQualityRules


class DataDownloader:
    """数据下载管理器"""

    def __init__(
        self,
        data_source: str = 'akshare',
        save_dir: str = 'data/raw/daily',
        years: int = 5,
        verbose: bool = True
    ):
        """
        初始化数据下载器

        参数:
            data_source: 数据源 ('akshare', 'tushare')
            save_dir: 数据保存目录
            years: 下载历史数据年数
            verbose: 是否打印详细信息
        """
        self.data_source = data_source
        self.save_dir = Path(save_dir)
        self.years = years
        self.verbose = verbose

        # 创建保存目录
        self.save_dir.mkdir(parents=True, exist_ok=True)

        # 初始化组件
        self.fetcher = DataFetcher(data_source=data_source)
        self.stock_filter = StockFilter(verbose=verbose)
        self.data_cleaner = DataCleaner(verbose=False)  # 批量下载时关闭详细输出

        # 计算日期范围
        self.end_date = datetime.now().strftime('%Y%m%d')
        self.start_date = (datetime.now() - timedelta(days=years*365)).strftime('%Y%m%d')

        # 统计信息
        self.stats = {
            'total_stocks': 0,
            'filtered_stocks': 0,
            'downloaded': 0,
            'failed': 0,
            'cleaned': 0,
            'saved': 0
        }

    def download_stock_list(self, markets: list = ['主板', '中小板', '创业板']) -> pd.DataFrame:
        """
        下载并过滤股票列表

        参数:
            markets: 允许的市场类型列表

        返回:
            过滤后的股票列表DataFrame
        """
        print("\n" + "="*60)
        print("步骤1: 获取股票列表")
        print("="*60)

        # 下载完整股票列表
        list_path = self.save_dir.parent / 'stock_list' / 'stock_list.csv'
        list_path.parent.mkdir(parents=True, exist_ok=True)

        success = fetch_akshare_stock_list(
            save_path=str(list_path),
            save_to_db=False
        )

        if not success:
            raise RuntimeError("获取股票列表失败")

        # 读取股票列表
        stock_df = pd.read_csv(list_path)
        self.stats['total_stocks'] = len(stock_df)

        # 按市场过滤
        stock_df = stock_df[stock_df['market'].isin(markets)]
        print(f"\n市场过滤后: {len(stock_df)} 只股票")

        # 过滤ST/退市股票
        stock_df = self.stock_filter.filter_stock_list(stock_df)
        self.stats['filtered_stocks'] = len(stock_df)

        # 保存过滤后的列表
        filtered_path = self.save_dir.parent / 'stock_list' / 'filtered_stock_list.csv'
        stock_df.to_csv(filtered_path, index=False, encoding='utf-8-sig')
        print(f"\n过滤后的股票列表已保存至: {filtered_path}")

        return stock_df

    def download_single_stock(self, stock_code: str, stock_name: str = '') -> tuple:
        """
        下载单只股票数据

        参数:
            stock_code: 股票代码
            stock_name: 股票名称（用于日志）

        返回:
            (成功标志, 数据DataFrame, 错误信息)
        """
        try:
            # 下载数据
            df = self.fetcher.fetch_data(
                symbol=stock_code,
                start_date=self.start_date,
                end_date=self.end_date,
                adjust=AdjustType.FORWARD  # 前复权
            )

            if df is None or df.empty:
                return False, None, "数据为空"

            # 数据质量过滤
            passed, cleaned_df, reason = self.stock_filter.filter_price_data(
                df,
                stock_code,
                min_trading_days=DataQualityRules.MIN_TRADING_DAYS
            )

            if not passed:
                return False, None, reason

            # 数据清洗
            cleaned_df = self.data_cleaner.clean_price_data(cleaned_df, stock_code)
            cleaned_df = self.data_cleaner.validate_ohlc(cleaned_df, fix=True)

            return True, cleaned_df, "成功"

        except Exception as e:
            return False, None, str(e)

    def save_stock_data(self, stock_code: str, df: pd.DataFrame):
        """
        保存股票数据到CSV

        参数:
            stock_code: 股票代码
            df: 数据DataFrame
        """
        file_path = self.save_dir / f"{stock_code}.csv"
        df.to_csv(file_path, encoding='utf-8-sig')

        if self.verbose:
            print(f"  ✓ 已保存: {file_path}")

    def download_all_stocks(
        self,
        stock_df: pd.DataFrame,
        max_stocks: int = None,
        delay: float = 0.5
    ):
        """
        批量下载所有股票数据

        参数:
            stock_df: 股票列表DataFrame
            max_stocks: 最大下载数量（用于测试）
            delay: 每次请求间隔（秒）
        """
        print("\n" + "="*60)
        print("步骤2: 批量下载股票数据")
        print("="*60)
        print(f"数据时间范围: {self.start_date} - {self.end_date}")
        print(f"数据年数: {self.years} 年")
        print(f"复权方式: 前复权")
        print(f"股票总数: {len(stock_df)}")

        if max_stocks:
            stock_df = stock_df.head(max_stocks)
            print(f"测试模式: 仅下载前 {max_stocks} 只股票")

        print("\n开始下载...\n")

        failed_stocks = []
        start_time = time.time()

        for idx, row in stock_df.iterrows():
            stock_code = row['symbol']
            stock_name = row['name']
            progress = idx + 1

            print(f"[{progress}/{len(stock_df)}] {stock_code} ({stock_name})")

            # 下载数据
            success, df, message = self.download_single_stock(stock_code, stock_name)

            if success:
                # 保存数据
                self.save_stock_data(stock_code, df)
                self.stats['downloaded'] += 1
                self.stats['cleaned'] += 1
                self.stats['saved'] += 1
            else:
                self.stats['failed'] += 1
                failed_stocks.append((stock_code, stock_name, message))
                print(f"  ✗ 失败: {message}")

            # 显示进度
            if progress % 50 == 0:
                elapsed = time.time() - start_time
                avg_time = elapsed / progress
                remaining = (len(stock_df) - progress) * avg_time
                print(f"\n进度: {progress}/{len(stock_df)} "
                      f"({progress/len(stock_df)*100:.1f}%) "
                      f"| 成功: {self.stats['downloaded']} "
                      f"| 失败: {self.stats['failed']} "
                      f"| 预计剩余: {remaining/60:.1f}分钟\n")

            # 请求延迟（避免被限流）
            time.sleep(delay)

        # 保存失败列表
        if failed_stocks:
            failed_df = pd.DataFrame(
                failed_stocks,
                columns=['stock_code', 'stock_name', 'reason']
            )
            failed_path = self.save_dir.parent / 'stock_list' / 'failed_stocks.csv'
            failed_df.to_csv(failed_path, index=False, encoding='utf-8-sig')
            print(f"\n失败股票列表已保存至: {failed_path}")

        # 打印总结
        self._print_summary(start_time)

    def _print_summary(self, start_time: float):
        """打印下载总结"""
        elapsed = time.time() - start_time

        print("\n" + "="*60)
        print("下载完成总结")
        print("="*60)
        print(f"总耗时:             {elapsed/60:.1f} 分钟")
        print(f"股票列表总数:       {self.stats['total_stocks']}")
        print(f"过滤后股票数:       {self.stats['filtered_stocks']}")
        print(f"下载成功:           {self.stats['downloaded']}")
        print(f"下载失败:           {self.stats['failed']}")
        print(f"成功率:             {self.stats['downloaded']/(self.stats['downloaded']+self.stats['failed'])*100:.1f}%")
        print(f"数据保存路径:       {self.save_dir}")
        print("="*60 + "\n")


# ==================== 主函数 ====================

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='批量下载A股历史数据')
    parser.add_argument('--years', type=int, default=5,
                      help='下载历史数据年数 (默认: 5)')
    parser.add_argument('--max-stocks', type=int, default=None,
                      help='最大下载股票数量，用于测试 (默认: 全部)')
    parser.add_argument('--data-source', type=str, default='akshare',
                      choices=['akshare', 'tushare'],
                      help='数据源 (默认: akshare)')
    parser.add_argument('--markets', nargs='+',
                      default=['主板', '中小板', '创业板'],
                      help='市场类型 (默认: 主板 中小板 创业板)')
    parser.add_argument('--delay', type=float, default=0.5,
                      help='请求延迟(秒) (默认: 0.5)')

    args = parser.parse_args()

    print("\n" + "🚀"*30)
    print("A股历史数据批量下载工具")
    print("🚀"*30 + "\n")

    print("配置信息:")
    print(f"  数据源:     {args.data_source}")
    print(f"  时间跨度:   {args.years} 年")
    print(f"  市场类型:   {', '.join(args.markets)}")
    print(f"  请求延迟:   {args.delay} 秒")
    if args.max_stocks:
        print(f"  测试模式:   仅下载 {args.max_stocks} 只股票")

    # 创建下载器
    downloader = DataDownloader(
        data_source=args.data_source,
        years=args.years,
        verbose=True
    )

    try:
        # 步骤1: 获取并过滤股票列表
        stock_df = downloader.download_stock_list(markets=args.markets)

        # 步骤2: 批量下载数据
        downloader.download_all_stocks(
            stock_df,
            max_stocks=args.max_stocks,
            delay=args.delay
        )

        print("\n✅ 数据下载完成！")
        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断下载")
        downloader._print_summary(time.time())
        return 1

    except Exception as e:
        print(f"\n\n❌ 下载过程出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
