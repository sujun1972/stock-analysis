"""
数据下载服务
封装数据下载功能（支持配置化数据源）

重构说明：
- 依赖 DataProviderService 管理数据提供者
- 依赖 StockDataRepository 访问数据库
- 专注于数据下载流程编排
- 移除直接的数据库操作和提供者创建逻辑
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import akshare as ak
import pandas as pd
from loguru import logger

# 使用docker-compose挂载的/app/src目录
from src.database.db_manager import DatabaseManager

from app.core.exceptions import DatabaseError, DataSyncError, ExternalAPIError
from app.repositories.stock_data_repository import StockDataRepository
from app.services.data_provider_service import DataProviderService


class DataDownloadService:
    """
    数据下载服务类（重构版）

    职责：
    - 编排数据下载流程
    - 处理下载错误和重试
    - 数据格式转换和验证
    - 批量下载管理

    依赖：
    - DataProviderService: 数据提供者管理
    - StockDataRepository: 数据持久化
    """

    def __init__(
        self,
        provider_service: Optional[DataProviderService] = None,
        stock_repo: Optional[StockDataRepository] = None,
        db: Optional[DatabaseManager] = None
    ):
        """
        初始化数据下载服务（支持依赖注入）

        Args:
            provider_service: 数据提供者服务实例（可选）
            stock_repo: 股票数据Repository实例（可选）
            db: DatabaseManager 实例（可选，用于依赖注入）
        """
        self.db = db or DatabaseManager()
        self.provider_service = provider_service or DataProviderService(db=self.db)
        self.stock_repo = stock_repo or StockDataRepository(db=self.db)
        logger.info("✓ DataDownloadService initialized (refactored)")

    # ==================== 股票列表下载 ====================

    async def download_stock_list(self, module: str = "main") -> Dict:
        """
        下载股票列表

        Args:
            module: 使用的数据源模块（默认 'main'）

        Returns:
            {count: int, message: str}

        Raises:
            ExternalAPIError: 数据获取失败
            DatabaseError: 数据库操作失败
            DataSyncError: 同步失败
        """
        try:
            logger.info("开始下载股票列表...")

            # 获取数据提供者
            provider = await self.provider_service.get_provider(module)

            # 使用配置的数据源获取股票列表
            response = await asyncio.to_thread(provider.get_stock_list)

            # 检查响应状态并提取数据
            if not response.is_success():
                raise ValueError(
                    response.error_message or "获取股票列表失败"
                )

            stock_info_df = response.data

            if stock_info_df is None or stock_info_df.empty:
                raise ValueError("获取股票列表失败，返回数据为空")

            # 重命名列（确保列名一致）
            stock_info_df = stock_info_df.rename(columns={"code": "code", "name": "name"})

            # 添加市场类型
            stock_info_df["market"] = stock_info_df["code"].apply(
                lambda x: (
                    "上海主板"
                    if x.startswith(("60", "68"))
                    else (
                        "深圳主板"
                        if x.startswith("000")
                        else (
                            "创业板"
                            if x.startswith("300")
                            else (
                                "科创板"
                                if x.startswith("688")
                                else "北交所" if x.startswith(("8", "4")) else "其他"
                            )
                        )
                    )
                )
            )

            # 保存到数据库（使用 Repository）
            count = await asyncio.to_thread(self.stock_repo.save_stock_list, stock_info_df)

            logger.info(f"✓ 股票列表下载完成: {count} 只")

            return {"count": count, "message": f"成功下载 {count} 只股票信息"}

        except ValueError as e:
            # 数据为空
            raise ExternalAPIError(
                "股票列表数据获取失败", error_code="STOCK_LIST_EMPTY", reason=str(e)
            )
        except DatabaseError:
            # 数据库异常直接向上传播
            raise
        except Exception as e:
            # 其他未预期错误
            logger.error(f"下载股票列表失败: {e}")
            raise DataSyncError(
                "股票列表同步失败", error_code="STOCK_LIST_SYNC_FAILED", reason=str(e)
            )

    # ==================== 单只股票数据下载 ====================

    async def download_single_stock(
        self,
        code: str,
        years: int = 5,
        module: str = "main",
        use_akshare_direct: bool = True
    ) -> Optional[int]:
        """
        下载单只股票数据

        Args:
            code: 股票代码
            years: 下载年数
            module: 使用的数据源模块（默认 'main'）
            use_akshare_direct: 是否直接使用akshare（兼容原有逻辑，默认True）

        Returns:
            保存的记录数，如果无数据则返回 None

        Raises:
            ExternalAPIError: 数据获取失败
            DatabaseError: 数据库操作失败
            DataSyncError: 同步失败
        """
        try:
            # 计算日期范围
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=years * 365)).strftime("%Y%m%d")

            logger.info(f"下载 {code} ({start_date} - {end_date})")

            # 兼容模式：直接使用 akshare（原有逻辑）
            # TODO: 后续可以改为使用 provider.get_daily_data()
            if use_akshare_direct:
                df = await asyncio.to_thread(
                    ak.stock_zh_a_hist,
                    symbol=code,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq",  # 前复权
                )
            else:
                # 使用数据提供者（新逻辑）
                provider = await self.provider_service.get_provider(module)
                response = await asyncio.to_thread(
                    provider.get_daily_data,
                    code=code,
                    start_date=start_date,
                    end_date=end_date
                )

                if not response.is_success():
                    raise ValueError(response.error_message or "获取日线数据失败")

                df = response.data

            if df is None or df.empty:
                logger.warning(f"  {code}: 无数据")
                return None

            # 重命名列（如果需要）
            if "日期" in df.columns:
                df = df.rename(
                    columns={
                        "日期": "date",
                        "开盘": "open",
                        "最高": "high",
                        "最低": "low",
                        "收盘": "close",
                        "成交量": "volume",
                        "成交额": "amount",
                        "振幅": "amplitude",
                        "涨跌幅": "pct_change",
                        "涨跌额": "change",
                        "换手率": "turnover",
                    }
                )

            # 设置日期索引
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
                df = df.set_index("date")

            # 保存到数据库（使用 Repository）
            count = await asyncio.to_thread(self.stock_repo.save_daily_data, df, code)

            logger.info(f"  ✓ {code}: {count} 条记录")
            return count

        except (ConnectionError, TimeoutError) as e:
            # 网络相关错误
            logger.error(f"  ✗ {code}: 数据获取超时或网络错误")
            raise ExternalAPIError(
                f"股票 {code} 数据获取失败",
                error_code="DATA_FETCH_TIMEOUT",
                stock_code=code,
                reason=str(e),
            )
        except ValueError as e:
            # 数据为空或提供者错误
            logger.warning(f"  {code}: {e}")
            return None
        except DatabaseError:
            # 数据库错误向上传播
            raise
        except Exception as e:
            # 其他未预期错误
            logger.error(f"  ✗ {code}: {e}")
            raise DataSyncError(
                f"股票 {code} 数据同步失败",
                error_code="DAILY_DATA_SYNC_FAILED",
                stock_code=code,
                reason=str(e),
            )

    # ==================== 批量下载 ====================

    async def download_batch(
        self,
        codes: Optional[List[str]] = None,
        years: int = 5,
        max_stocks: Optional[int] = None,
        delay: float = 0.5,
        module: str = "main",
        use_akshare_direct: bool = True
    ) -> Dict:
        """
        批量下载股票数据

        Args:
            codes: 股票代码列表（None表示全部）
            years: 下载年数
            max_stocks: 最大下载数量
            delay: 请求间隔（秒）
            module: 使用的数据源模块（默认 'main'）
            use_akshare_direct: 是否直接使用akshare（默认True）

        Returns:
            {success: int, failed: int, total: int, message: str}

        Raises:
            DatabaseError: 数据库操作失败
            DataSyncError: 批量下载失败
        """
        try:
            # 如果没有指定codes，从数据库获取（使用 Repository）
            if codes is None:
                stock_list_df = await asyncio.to_thread(self.stock_repo.get_stock_list)
                codes = stock_list_df["code"].tolist()

            # 限制数量
            if max_stocks:
                codes = codes[:max_stocks]

            total = len(codes)
            success_count = 0
            failed_count = 0

            logger.info(f"开始批量下载 {total} 只股票...")

            for idx, code in enumerate(codes, 1):
                logger.info(f"[{idx}/{total}] 处理 {code}")

                try:
                    result = await self.download_single_stock(
                        code,
                        years,
                        module=module,
                        use_akshare_direct=use_akshare_direct
                    )

                    if result is not None:
                        success_count += 1
                    else:
                        failed_count += 1

                except Exception as e:
                    # 单只股票下载失败不影响整体流程
                    logger.error(f"  ✗ {code} 下载失败: {e}")
                    failed_count += 1

                # 延迟避免限流
                if idx < total:
                    await asyncio.sleep(delay)

            logger.info(f"✓ 批量下载完成: 成功 {success_count}, 失败 {failed_count}")

            return {
                "success": success_count,
                "failed": failed_count,
                "total": total,
                "message": f"批量下载完成: 成功 {success_count}/{total}"
            }

        except DatabaseError:
            # 数据库错误向上传播
            raise
        except Exception as e:
            # 其他未预期错误
            logger.error(f"批量下载失败: {e}")
            raise DataSyncError(
                "批量下载失败",
                error_code="BATCH_DOWNLOAD_FAILED",
                total=total if 'total' in locals() else 0,
                success=success_count if 'success_count' in locals() else 0,
                failed=failed_count if 'failed_count' in locals() else 0,
                reason=str(e),
            )

    # ==================== 便捷方法 ====================

    async def get_stock_list_from_db(self, market: Optional[str] = None) -> pd.DataFrame:
        """
        从数据库获取股票列表

        Args:
            market: 市场类型（可选）

        Returns:
            股票列表 DataFrame
        """
        return await asyncio.to_thread(self.stock_repo.get_stock_list, market)

    async def get_daily_data_from_db(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        从数据库获取日线数据

        Args:
            code: 股票代码
            start_date: 起始日期
            end_date: 结束日期
            limit: 最大记录数

        Returns:
            日线数据 DataFrame
        """
        return await asyncio.to_thread(
            self.stock_repo.get_daily_data,
            code,
            start_date,
            end_date,
            limit
        )

    async def get_data_statistics(self) -> Dict:
        """
        获取数据统计信息

        Returns:
            统计信息字典
        """
        return await asyncio.to_thread(self.stock_repo.get_data_statistics)
