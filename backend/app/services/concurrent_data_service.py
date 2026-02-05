"""
并发数据服务

✅ 任务 2.3: 并发性能优化
- 批量获取股票数据（异步并发）
- 连接池优化
- 压力测试支持

作者: Backend Team
创建日期: 2026-02-05
版本: 1.0.0
"""

import asyncio
from datetime import date
from typing import List, Dict, Any, Optional
from loguru import logger

from app.core_adapters.data_adapter import DataAdapter
from app.core.exceptions import DataNotFoundError, ExternalAPIError


class ConcurrentDataService:
    """
    并发数据服务

    提供高性能的批量数据获取功能，支持异步并发处理
    """

    def __init__(self, max_concurrent: int = 50):
        """
        初始化并发数据服务

        Args:
            max_concurrent: 最大并发数（默认 50）
        """
        self.data_adapter = DataAdapter()
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def get_multiple_stocks_data(
        self,
        codes: List[str],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        批量获取多只股票的日线数据（并发优化）

        Args:
            codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            {
                "total": 100,
                "success": 95,
                "failed": 5,
                "data": {
                    "000001.SZ": DataFrame,
                    "000002.SZ": DataFrame,
                    ...
                },
                "errors": {
                    "600001.SH": "数据不存在",
                    ...
                }
            }
        """
        logger.info(f"批量获取 {len(codes)} 只股票数据（并发数: {self.max_concurrent}）")

        # 创建并发任务
        tasks = [
            self._get_single_stock_data_with_semaphore(code, start_date, end_date)
            for code in codes
        ]

        # 执行并发获取
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 结果汇总
        success_count = 0
        failed_count = 0
        data_dict = {}
        errors_dict = {}

        for code, result in zip(codes, results):
            if isinstance(result, Exception):
                failed_count += 1
                errors_dict[code] = str(result)
                logger.warning(f"❌ {code}: {result}")
            elif result is None or (hasattr(result, 'empty') and result.empty):
                failed_count += 1
                errors_dict[code] = "无数据"
                logger.warning(f"⚠️  {code}: 无数据")
            else:
                success_count += 1
                data_dict[code] = result
                logger.debug(f"✅ {code}: {len(result)} 条记录")

        logger.info(f"批量获取完成: 成功 {success_count}/{len(codes)}, 失败 {failed_count}/{len(codes)}")

        return {
            "total": len(codes),
            "success": success_count,
            "failed": failed_count,
            "data": data_dict,
            "errors": errors_dict
        }

    async def _get_single_stock_data_with_semaphore(
        self,
        code: str,
        start_date: Optional[date],
        end_date: Optional[date]
    ):
        """
        使用信号量控制的单只股票数据获取

        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            DataFrame 或 None
        """
        async with self.semaphore:
            try:
                return await self.data_adapter.get_daily_data(
                    code=code,
                    start_date=start_date,
                    end_date=end_date
                )
            except DataNotFoundError:
                return None
            except Exception as e:
                logger.error(f"获取 {code} 数据失败: {e}")
                raise

    async def download_multiple_stocks(
        self,
        codes: List[str],
        start_date: date,
        end_date: date,
        batch_size: int = 50
    ) -> Dict[str, Any]:
        """
        批量下载多只股票数据（并发优化）

        Args:
            codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            batch_size: 批次大小（默认 50）

        Returns:
            {
                "total": 100,
                "success": 95,
                "failed": 5,
                "failed_codes": ["600001.SH", ...],
                "duration_seconds": 45.2
            }
        """
        import time
        start_time = time.time()

        logger.info(f"批量下载 {len(codes)} 只股票数据")

        success_count = 0
        failed_count = 0
        failed_codes = []

        # 分批处理
        for i in range(0, len(codes), batch_size):
            batch = codes[i:i + batch_size]
            logger.info(f"处理批次 {i//batch_size + 1}: {len(batch)} 只股票")

            # 并发下载
            tasks = [
                self._download_single_stock_with_semaphore(code, start_date, end_date)
                for code in batch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 统计结果
            for code, result in zip(batch, results):
                if isinstance(result, Exception) or result is False:
                    failed_count += 1
                    failed_codes.append(code)
                else:
                    success_count += 1

        duration = time.time() - start_time

        logger.info(
            f"批量下载完成: 成功 {success_count}/{len(codes)}, "
            f"失败 {failed_count}/{len(codes)}, 耗时 {duration:.2f}s"
        )

        return {
            "total": len(codes),
            "success": success_count,
            "failed": failed_count,
            "failed_codes": failed_codes[:20],  # 最多返回 20 个失败代码
            "duration_seconds": round(duration, 2)
        }

    async def _download_single_stock_with_semaphore(
        self,
        code: str,
        start_date: date,
        end_date: date
    ) -> bool:
        """
        使用信号量控制的单只股票下载

        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            成功返回 True，失败返回 False
        """
        async with self.semaphore:
            try:
                # 下载数据
                df = await self.data_adapter.download_daily_data(
                    code=code,
                    start_date=start_date,
                    end_date=end_date
                )

                if df is None or df.empty:
                    logger.warning(f"⚠️  {code}: 无数据")
                    return False

                # 保存数据
                await self.data_adapter.insert_daily_data(df, code)
                logger.debug(f"✅ {code}: {len(df)} 条记录")
                return True

            except ExternalAPIError as e:
                logger.error(f"❌ {code}: 数据源API错误 - {e}")
                return False
            except Exception as e:
                logger.error(f"❌ {code}: 下载失败 - {e}")
                return False

    async def health_check_concurrent(self, test_codes: List[str]) -> Dict[str, Any]:
        """
        并发健康检查（用于压力测试）

        Args:
            test_codes: 测试股票代码列表

        Returns:
            健康检查结果
        """
        import time
        start_time = time.time()

        logger.info(f"并发健康检查: {len(test_codes)} 只股票")

        # 并发获取数据
        result = await self.get_multiple_stocks_data(test_codes)

        duration = time.time() - start_time
        avg_response_time = duration / len(test_codes) * 1000  # ms

        return {
            "test_count": len(test_codes),
            "success_count": result["success"],
            "failed_count": result["failed"],
            "success_rate": result["success"] / len(test_codes) if test_codes else 0,
            "total_duration_seconds": round(duration, 2),
            "avg_response_time_ms": round(avg_response_time, 2),
            "concurrent_limit": self.max_concurrent
        }
