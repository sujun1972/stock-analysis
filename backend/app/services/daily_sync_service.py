"""
日线数据同步服务
负责单只和批量股票日线数据的同步
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger
import asyncio

from src.providers import DataProviderFactory
from app.services.config_service import ConfigService
from app.services.data_service import DataDownloadService


class DailySyncService:
    """
    日线数据同步服务

    职责：
    - 单只股票日线数据同步
    - 批量股票日线数据同步
    - 数据完整性检查
    - 进度追踪
    - 中止控制
    """

    def __init__(self):
        """初始化日线数据同步服务"""
        self.config_service = ConfigService()
        self.data_service = DataDownloadService()

    async def sync_single_stock(
        self,
        code: str,
        years: int = 5
    ) -> Dict:
        """
        同步单只股票日线数据

        Args:
            code: 股票代码
            years: 历史年数

        Returns:
            同步结果字典
        """
        # 获取数据源配置
        config = await self.config_service.get_data_source_config()

        # 创建数据提供者
        provider = DataProviderFactory.create_provider(
            source=config['data_source'],
            token=config.get('tushare_token', '')
        )

        # 计算日期范围
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=years * 365)).strftime('%Y%m%d')

        logger.info(f"同步 {code} 日线数据 ({start_date} - {end_date})")

        # 获取日线数据 (添加30秒超时)
        try:
            df = await asyncio.wait_for(
                asyncio.to_thread(
                    provider.get_daily_data,
                    code=code,
                    start_date=start_date,
                    end_date=end_date,
                    adjust='qfq'
                ),
                timeout=30.0  # 30秒超时
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"{code}: 数据获取超时")

        if df.empty:
            raise ValueError(f"{code}: 无数据")

        # 保存到数据库
        count = await asyncio.to_thread(
            self.data_service.db.save_daily_data,
            df,
            code
        )

        logger.info(f"✓ {code}: {count} 条记录")

        return {
            "code": code,
            "records": count
        }

    async def sync_batch(
        self,
        codes: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        years: Optional[int] = None
    ) -> Dict:
        """
        批量同步日线数据

        Args:
            codes: 股票代码列表 (None 表示全部)
            start_date: 开始日期 (优先使用，格式: YYYYMMDD 或 YYYY-MM-DD)
            end_date: 结束日期 (默认今天)
            years: 历史年数 (仅在未提供start_date时使用，默认 5 年)

        Returns:
            同步结果统计
        """
        # 获取数据源配置
        config = await self.config_service.get_data_source_config()

        # 创建数据提供者
        provider = DataProviderFactory.create_provider(
            source=config['data_source'],
            token=config.get('tushare_token', '')
        )

        # 获取要同步的股票代码（只获取正常状态和非停牌股票）
        if codes is None:
            stock_list_df = await asyncio.to_thread(
                self.data_service.db.get_stock_list
            )
            # 过滤：只同步状态为"正常"或空字符串的股票（排除退市、停牌等）
            normal_stocks = stock_list_df[
                stock_list_df['status'].isin(['正常', '']) |
                stock_list_df['status'].isna()
            ]
            codes = normal_stocks['code'].tolist()
            logger.info(f"从 {len(stock_list_df)} 只股票中筛选出 {len(codes)} 只正常股票")

        total = len(codes)
        success_count = 0
        failed_count = 0
        skipped_count = 0

        # 清除之前的中止标志
        await self.config_service.clear_sync_abort_flag()

        # 更新同步状态
        await self.config_service.update_sync_status(
            status='running',
            progress=0,
            total=total,
            completed=0
        )

        # 计算日期范围
        if end_date:
            end_date_formatted = end_date.replace('-', '')
        else:
            end_date_formatted = datetime.now().strftime('%Y%m%d')

        if start_date:
            start_date_formatted = start_date.replace('-', '')
        else:
            years_val = years if years else 5
            start_date_formatted = (datetime.now() - timedelta(days=years_val * 365)).strftime('%Y%m%d')

        logger.info(f"开始批量同步 {total} 只股票的日线数据 ({start_date_formatted} 至 {end_date_formatted})")

        # 计算最小期望交易日数
        start_dt = datetime.strptime(start_date_formatted, '%Y%m%d')
        end_dt = datetime.strptime(end_date_formatted, '%Y%m%d')
        date_diff_days = (end_dt - start_dt).days
        min_expected_days = int(date_diff_days * 0.7)  # 约为自然日的 70%

        # 批量同步
        aborted = False
        for idx, code in enumerate(codes, 1):
            try:
                # 检查是否收到中止请求
                if await self.config_service.check_sync_abort_flag():
                    logger.warning(f"⚠️ 收到中止请求，停止同步（已完成 {idx-1}/{total}）")
                    aborted = True
                    break

                logger.info(f"[{idx}/{total}] 检查 {code}")

                # 检查数据完整性
                completeness = await asyncio.to_thread(
                    self.data_service.db.check_daily_data_completeness,
                    code=code,
                    start_date=start_date_formatted,
                    end_date=end_date_formatted,
                    min_expected_days=min_expected_days
                )

                # 如果数据已经完整，跳过
                if completeness['is_complete']:
                    logger.info(
                        f"  ⊙ {code}: 数据已完整 ({completeness['record_count']} 条记录，"
                        f"最新日期: {completeness['latest_date']})，跳过"
                    )
                    success_count += 1
                    skipped_count += 1

                    # 更新进度
                    progress = int((idx / total) * 100)
                    await self.config_service.update_sync_status(
                        progress=progress,
                        completed=idx
                    )
                    continue

                # 如果有部分数据，提示更新
                if completeness['has_data']:
                    logger.info(f"  ↻ {code}: 数据不完整 ({completeness['record_count']} 条记录)，更新中...")
                else:
                    logger.info(f"  + {code}: 无数据，开始同步...")

                # 获取日线数据 (添加30秒超时)
                try:
                    df = await asyncio.wait_for(
                        asyncio.to_thread(
                            provider.get_daily_data,
                            code=code,
                            start_date=start_date_formatted,
                            end_date=end_date_formatted,
                            adjust='qfq'
                        ),
                        timeout=30.0  # 单个股票数据获取超时30秒
                    )
                except asyncio.TimeoutError:
                    logger.error(f"  ✗ {code}: 数据获取超时 (30秒)")
                    failed_count += 1
                    continue

                if not df.empty:
                    # 保存到数据库
                    count = await asyncio.to_thread(
                        self.data_service.db.save_daily_data,
                        df,
                        code
                    )
                    logger.info(f"  ✓ {code}: {count} 条记录")
                    success_count += 1
                else:
                    logger.warning(f"  {code}: 无数据")
                    failed_count += 1

                # 更新进度
                progress = int((idx / total) * 100)
                await self.config_service.update_sync_status(
                    progress=progress,
                    completed=idx
                )

                # 请求间隔
                await asyncio.sleep(0.3)

            except Exception as e:
                logger.error(f"  ✗ {code}: {e}")
                failed_count += 1

        # 清除中止标志
        await self.config_service.clear_sync_abort_flag()

        # 根据是否中止来更新状态
        if aborted:
            await self.config_service.update_sync_status(
                status='aborted',
                last_sync_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            logger.warning(
                f"⚠️ 同步已中止: 成功 {success_count} (跳过 {skipped_count}), "
                f"失败 {failed_count}, 总计 {total}"
            )

            return {
                "success": success_count,
                "failed": failed_count,
                "skipped": skipped_count,
                "total": total,
                "aborted": True
            }
        else:
            # 更新同步状态为完成
            await self.config_service.update_sync_status(
                status='completed',
                last_sync_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                progress=100
            )

            logger.info(f"✓ 批量同步完成: 成功 {success_count} (跳过 {skipped_count}), 失败 {failed_count}")

            return {
                "success": success_count,
                "failed": failed_count,
                "skipped": skipped_count,
                "total": total,
                "aborted": False
            }
