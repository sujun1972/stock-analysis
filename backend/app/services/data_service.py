"""
数据下载服务
封装数据下载功能
"""

from typing import Optional, List, Dict
import asyncio
from datetime import datetime, timedelta
from loguru import logger
import pandas as pd

import akshare as ak
# 使用docker-compose挂载的/app/src目录
from src.database.db_manager import DatabaseManager


class DataDownloadService:
    """数据下载服务类"""

    def __init__(self):
        """初始化"""
        self.db = DatabaseManager()
        logger.info("✓ DataDownloadService initialized")

    async def download_stock_list(self) -> Dict:
        """
        下载股票列表

        Returns:
            {count: int, message: str}
        """
        try:
            logger.info("开始下载股票列表...")

            # 在线程池中执行（避免阻塞）
            stock_info_df = await asyncio.to_thread(
                ak.stock_info_a_code_name
            )

            if stock_info_df is None or stock_info_df.empty:
                raise ValueError("获取股票列表失败，返回数据为空")

            # 重命名列
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

            # 保存到数据库
            count = await asyncio.to_thread(
                self.db.save_stock_list,
                stock_info_df
            )

            logger.info(f"✓ 股票列表下载完成: {count} 只")

            return {
                "count": count,
                "message": f"成功下载 {count} 只股票信息"
            }

        except Exception as e:
            logger.error(f"下载股票列表失败: {e}")
            raise

    async def download_single_stock(
        self,
        code: str,
        years: int = 5
    ) -> Optional[int]:
        """
        下载单只股票数据

        Args:
            code: 股票代码
            years: 下载年数

        Returns:
            保存的记录数
        """
        try:
            # 计算日期范围
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=years * 365)).strftime('%Y%m%d')

            logger.info(f"下载 {code} ({start_date} - {end_date})")

            # 在线程池中执行
            df = await asyncio.to_thread(
                ak.stock_zh_a_hist,
                symbol=code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"  # 前复权
            )

            if df is None or df.empty:
                logger.warning(f"  {code}: 无数据")
                return None

            # 重命名列
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

            # 设置日期索引
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')

            # 保存到数据库
            count = await asyncio.to_thread(
                self.db.save_daily_data,
                df,
                code
            )

            logger.info(f"  ✓ {code}: {count} 条记录")
            return count

        except Exception as e:
            logger.error(f"  ✗ {code}: {e}")
            return None

    async def download_batch(
        self,
        codes: Optional[List[str]] = None,
        years: int = 5,
        max_stocks: Optional[int] = None,
        delay: float = 0.5
    ) -> Dict:
        """
        批量下载股票数据

        Args:
            codes: 股票代码列表（None表示全部）
            years: 下载年数
            max_stocks: 最大下载数量
            delay: 请求间隔（秒）

        Returns:
            {success: int, failed: int, total: int}
        """
        try:
            # 如果没有指定codes，从数据库获取
            if codes is None:
                stock_list_df = await asyncio.to_thread(
                    self.db.get_stock_list
                )
                codes = stock_list_df['code'].tolist()

            # 限制数量
            if max_stocks:
                codes = codes[:max_stocks]

            total = len(codes)
            success_count = 0
            failed_count = 0

            logger.info(f"开始批量下载 {total} 只股票...")

            for idx, code in enumerate(codes, 1):
                logger.info(f"[{idx}/{total}] 处理 {code}")

                result = await self.download_single_stock(code, years)

                if result is not None:
                    success_count += 1
                else:
                    failed_count += 1

                # 延迟避免限流
                if idx < total:
                    await asyncio.sleep(delay)

            logger.info(f"✓ 批量下载完成: 成功 {success_count}, 失败 {failed_count}")

            return {
                "success": success_count,
                "failed": failed_count,
                "total": total
            }

        except Exception as e:
            logger.error(f"批量下载失败: {e}")
            raise
