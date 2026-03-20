"""
批量下载编排服务

职责：
- 批量下载编排（串行/并发）
- 进度跟踪和错误处理
- 下载策略选择
"""

import asyncio
import time
from typing import Dict, List, Optional

from loguru import logger

from app.core.exceptions import DataSyncError
from app.services.stock.daily_data_service import DailyDataService
from app.services.stock.stock_list_service import StockListService


class BatchDownloadService:
    """
    批量下载编排服务

    职责：
    - 编排批量下载流程
    - 管理并发控制
    - 统计下载结果
    - 错误处理和重试

    重构说明：
    - 从 DataDownloadService 提取批量下载相关功能
    - 委托给 DailyDataService 和 StockListService
    - 专注于编排逻辑，不直接处理数据
    """

    def __init__(
        self,
        stock_list_service: Optional[StockListService] = None,
        daily_data_service: Optional[DailyDataService] = None
    ):
        """
        初始化批量下载服务

        Args:
            stock_list_service: 股票列表服务（可选，用于依赖注入）
            daily_data_service: 日线数据服务（可选，用于依赖注入）
        """
        self.stock_list_service = stock_list_service or StockListService()
        self.daily_data_service = daily_data_service or DailyDataService()
        logger.debug("✓ BatchDownloadService initialized")

    # ==================== 串行下载 ====================

    async def download_batch_serial(
        self,
        codes: Optional[List[str]] = None,
        years: int = 5,
        max_stocks: Optional[int] = None,
        delay: float = 0.5,
        module: str = "main"
    ) -> Dict:
        """
        批量下载股票数据（串行模式，带延迟避免限流）

        适用场景：
        - 数据源有严格的限流要求
        - 需要稳定可靠的下载
        - 对时间要求不高

        Args:
            codes: 股票代码列表（None表示全部）
            years: 下载年数
            max_stocks: 最大下载数量
            delay: 请求间隔（秒）
            module: 使用的数据源模块（默认 'main'）

        Returns:
            {
                success: int,
                failed: int,
                total: int,
                failed_codes: List[str],
                duration_seconds: float,
                message: str
            }

        Raises:
            DataSyncError: 批量下载失败

        Examples:
            >>> service = BatchDownloadService()
            >>> result = await service.download_batch_serial(
            ...     codes=['000001', '600000'],
            ...     years=5,
            ...     delay=1.0
            ... )
            >>> print(f"成功: {result['success']}, 失败: {result['failed']}")
        """
        start_time = time.time()

        try:
            # 1. 获取股票代码列表
            if codes is None:
                codes = await self.stock_list_service.get_codes_list()

            # 2. 限制数量
            if max_stocks:
                codes = codes[:max_stocks]

            total = len(codes)
            success_count = 0
            failed_count = 0
            failed_codes = []

            logger.info(f"开始串行批量下载: {total} 只股票（间隔 {delay}s）...")

            # 3. 串行下载
            for idx, code in enumerate(codes, 1):
                logger.info(f"[{idx}/{total}] 处理 {code}")

                try:
                    result = await self.daily_data_service.download_and_save(
                        code=code,
                        years=years,
                        module=module
                    )

                    if result is not None:
                        success_count += 1
                    else:
                        failed_count += 1
                        failed_codes.append(code)

                except Exception as e:
                    # 单只股票下载失败不影响整体流程
                    logger.error(f"  ✗ {code} 下载失败: {e}")
                    failed_count += 1
                    failed_codes.append(code)

                # 延迟避免限流
                if idx < total:
                    await asyncio.sleep(delay)

            duration = time.time() - start_time

            logger.info(
                f"✓ 串行批量下载完成: 成功 {success_count}/{total}, "
                f"失败 {failed_count}/{total}, 耗时 {duration:.2f}s"
            )

            return {
                "success": success_count,
                "failed": failed_count,
                "total": total,
                "failed_codes": failed_codes,
                "duration_seconds": round(duration, 2),
                "message": f"批量下载完成: 成功 {success_count}/{total}, 耗时 {duration:.2f}s"
            }

        except Exception as e:
            logger.error(f"串行批量下载失败: {e}")
            raise DataSyncError(
                "串行批量下载失败",
                error_code="SERIAL_BATCH_DOWNLOAD_FAILED",
                total=total if 'total' in locals() else 0,
                success=success_count if 'success_count' in locals() else 0,
                failed=failed_count if 'failed_count' in locals() else 0,
                reason=str(e)
            )

    # ==================== 并发下载 ====================

    async def download_batch_concurrent(
        self,
        codes: Optional[List[str]] = None,
        years: int = 5,
        max_stocks: Optional[int] = None,
        max_concurrent: int = 10,
        batch_size: int = 50,
        module: str = "main"
    ) -> Dict:
        """
        并发批量下载股票数据（高性能模式）

        适用场景：
        - 数据源支持较高并发
        - 需要快速完成大量下载
        - 有稳定的网络环境

        Args:
            codes: 股票代码列表（None表示全部）
            years: 下载年数
            max_stocks: 最大下载数量
            max_concurrent: 最大并发数（默认10）
            batch_size: 批次大小（默认50）
            module: 使用的数据源模块（默认 'main'）

        Returns:
            {
                success: int,
                failed: int,
                total: int,
                failed_codes: List[str],
                duration_seconds: float,
                message: str
            }

        Raises:
            DataSyncError: 批量下载失败

        Examples:
            >>> service = BatchDownloadService()
            >>> result = await service.download_batch_concurrent(
            ...     codes=['000001', '600000'],
            ...     years=5,
            ...     max_concurrent=20
            ... )
            >>> print(f"成功: {result['success']}, 耗时: {result['duration_seconds']}s")
        """
        start_time = time.time()

        try:
            # 1. 获取股票代码列表
            if codes is None:
                codes = await self.stock_list_service.get_codes_list()

            # 2. 限制数量
            if max_stocks:
                codes = codes[:max_stocks]

            total = len(codes)
            success_count = 0
            failed_count = 0
            failed_codes = []

            logger.info(f"开始并发批量下载: {total} 只股票（并发数: {max_concurrent}）...")

            # 3. 信号量控制并发数
            semaphore = asyncio.Semaphore(max_concurrent)

            async def download_with_semaphore(code: str) -> bool:
                """带信号量控制的下载"""
                async with semaphore:
                    try:
                        result = await self.daily_data_service.download_and_save(
                            code=code,
                            years=years,
                            module=module
                        )
                        return result is not None
                    except Exception as e:
                        logger.error(f"  ✗ {code} 下载失败: {e}")
                        return False

            # 4. 分批处理
            for i in range(0, total, batch_size):
                batch = codes[i:i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (total + batch_size - 1) // batch_size

                logger.info(f"处理批次 {batch_num}/{total_batches}: {len(batch)} 只股票")

                # 并发下载当前批次
                tasks = [download_with_semaphore(code) for code in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # 统计结果
                for code, result in zip(batch, results):
                    if isinstance(result, Exception):
                        failed_count += 1
                        failed_codes.append(code)
                        logger.error(f"  ✗ {code}: {result}")
                    elif result:
                        success_count += 1
                        logger.debug(f"  ✓ {code}")
                    else:
                        failed_count += 1
                        failed_codes.append(code)

            duration = time.time() - start_time

            logger.info(
                f"✓ 并发批量下载完成: 成功 {success_count}/{total}, "
                f"失败 {failed_count}/{total}, 耗时 {duration:.2f}s"
            )

            return {
                "success": success_count,
                "failed": failed_count,
                "total": total,
                "failed_codes": failed_codes[:50],  # 最多返回50个失败代码
                "duration_seconds": round(duration, 2),
                "message": f"并发批量下载完成: 成功 {success_count}/{total}, 耗时 {duration:.2f}s"
            }

        except Exception as e:
            logger.error(f"并发批量下载失败: {e}")
            raise DataSyncError(
                "并发批量下载失败",
                error_code="CONCURRENT_BATCH_DOWNLOAD_FAILED",
                total=total if 'total' in locals() else 0,
                success=success_count if 'success_count' in locals() else 0,
                failed=failed_count if 'failed_count' in locals() else 0,
                reason=str(e)
            )

    # ==================== 增量更新 ====================

    async def update_latest_batch(
        self,
        codes: Optional[List[str]] = None,
        days: int = 30,
        max_concurrent: int = 10,
        module: str = "main"
    ) -> Dict:
        """
        批量增量更新最新数据

        只更新最近 N 天的数据，用于日常更新

        Args:
            codes: 股票代码列表（None表示全部）
            days: 更新最近N天（默认30天）
            max_concurrent: 最大并发数（默认10）
            module: 数据源模块

        Returns:
            更新结果字典

        Examples:
            >>> service = BatchDownloadService()
            >>> result = await service.update_latest_batch(days=30)
        """
        start_time = time.time()

        try:
            # 1. 获取股票代码列表
            if codes is None:
                codes = await self.stock_list_service.get_codes_list()

            total = len(codes)
            success_count = 0
            failed_count = 0
            failed_codes = []

            logger.info(f"开始批量增量更新: {total} 只股票（最近 {days} 天）...")

            # 2. 信号量控制并发
            semaphore = asyncio.Semaphore(max_concurrent)

            async def update_with_semaphore(code: str) -> bool:
                """带信号量控制的更新"""
                async with semaphore:
                    try:
                        result = await self.daily_data_service.update_latest_data(
                            code=code,
                            module=module,
                            days=days
                        )
                        return result is not None
                    except Exception as e:
                        logger.error(f"  ✗ {code} 更新失败: {e}")
                        return False

            # 3. 并发更新
            tasks = [update_with_semaphore(code) for code in codes]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 4. 统计结果
            for code, result in zip(codes, results):
                if isinstance(result, Exception):
                    failed_count += 1
                    failed_codes.append(code)
                elif result:
                    success_count += 1
                else:
                    failed_count += 1
                    failed_codes.append(code)

            duration = time.time() - start_time

            logger.info(
                f"✓ 批量增量更新完成: 成功 {success_count}/{total}, "
                f"失败 {failed_count}/{total}, 耗时 {duration:.2f}s"
            )

            return {
                "success": success_count,
                "failed": failed_count,
                "total": total,
                "failed_codes": failed_codes[:50],
                "duration_seconds": round(duration, 2),
                "message": f"增量更新完成: 成功 {success_count}/{total}, 耗时 {duration:.2f}s"
            }

        except Exception as e:
            logger.error(f"批量增量更新失败: {e}")
            raise DataSyncError(
                "批量增量更新失败",
                error_code="BATCH_UPDATE_FAILED",
                reason=str(e)
            )

    # ==================== 智能选择 ====================

    async def download_batch_auto(
        self,
        codes: Optional[List[str]] = None,
        years: int = 5,
        max_stocks: Optional[int] = None,
        module: str = "main"
    ) -> Dict:
        """
        自动选择下载模式

        根据股票数量自动选择串行或并发模式：
        - < 10 只: 串行（延迟 0.5s）
        - >= 10 只: 并发（并发数 10）

        Args:
            codes: 股票代码列表（None表示全部）
            years: 下载年数
            max_stocks: 最大下载数量
            module: 数据源模块

        Returns:
            下载结果字典

        Examples:
            >>> service = BatchDownloadService()
            >>> result = await service.download_batch_auto(codes=['000001'])
        """
        # 获取股票列表
        if codes is None:
            codes = await self.stock_list_service.get_codes_list()

        if max_stocks:
            codes = codes[:max_stocks]

        total = len(codes)

        # 自动选择模式
        if total < 10:
            logger.info(f"股票数量 {total} < 10，使用串行模式")
            return await self.download_batch_serial(
                codes=codes,
                years=years,
                delay=0.5,
                module=module
            )
        else:
            logger.info(f"股票数量 {total} >= 10，使用并发模式")
            return await self.download_batch_concurrent(
                codes=codes,
                years=years,
                max_concurrent=10,
                module=module
            )
