"""
实时行情同步服务
负责实时行情数据的同步
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger
import asyncio

from src.providers import DataProviderFactory
from app.services.config_service import ConfigService
from app.services.data_service import DataDownloadService


class RealtimeSyncService:
    """
    实时行情同步服务

    职责：
    - 实时行情数据同步
    - 分时数据同步
    - 渐进式更新
    - 增量保存
    """

    def __init__(self):
        """初始化实时行情同步服务"""
        self.config_service = ConfigService()
        self.data_service = DataDownloadService()

    async def sync_minute_data(
        self,
        code: str,
        period: str = "5",
        days: int = 5
    ) -> Dict:
        """
        同步分时数据

        Args:
            code: 股票代码
            period: 分时周期 ('1', '5', '15', '30', '60')
            days: 同步天数

        Returns:
            同步结果字典
        """
        # 获取数据源配置
        config = await self.config_service.get_data_source_config()

        # 创建数据提供者（使用分时数据源配置）
        provider = DataProviderFactory.create_provider(
            source=config['minute_data_source'],
            token=config.get('tushare_token', '')
        )

        # 计算日期范围
        end_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d 09:30:00')

        logger.info(f"同步 {code} {period}分钟数据")

        # 获取分时数据
        df = await asyncio.to_thread(
            provider.get_minute_data,
            code=code,
            period=period,
            start_date=start_date,
            end_date=end_date
        )

        if df.empty:
            raise ValueError(f"{code}: 无分时数据")

        # TODO: 保存分时数据到数据库
        # count = await asyncio.to_thread(
        #     self.data_service.db.save_minute_data,
        #     df,
        #     code
        # )

        logger.info(f"✓ {code}: {len(df)} 条分时记录")

        return {
            "code": code,
            "period": period,
            "records": len(df)
        }

    async def sync_realtime_quotes(
        self,
        codes: Optional[List[str]] = None,
        batch_size: Optional[int] = 100,
        update_oldest: bool = False
    ) -> Dict:
        """
        更新实时行情

        Args:
            codes: 股票代码列表 (None 表示全部)
            batch_size: 每批次更新的股票数量（默认100）
            update_oldest: 是否优先更新最旧的数据（默认False）

        Returns:
            更新结果字典
        """
        # 获取数据源配置
        config = await self.config_service.get_data_source_config()

        # 实时行情使用专门的实时数据源配置（默认为 AkShare，因为 Tushare 有访问限制）
        realtime_source = config.get('realtime_data_source', 'akshare')

        # 创建数据提供者
        provider = DataProviderFactory.create_provider(
            source=realtime_source,
            token=config.get('tushare_token', '')
        )

        logger.info("更新实时行情...")
        logger.warning(f"使用实时数据源: {realtime_source}")

        # 确定要更新的股票代码
        codes_to_update = codes

        # 如果启用了优先更新最旧数据的模式
        if update_oldest and not codes:
            batch_size_val = batch_size or 100
            logger.info(f"渐进式更新模式：获取最早更新的 {batch_size_val} 只股票...")

            codes_to_update = await asyncio.to_thread(
                self.data_service.db.get_oldest_realtime_stocks,
                limit=batch_size_val
            )

            logger.info(f"将更新 {len(codes_to_update)} 只股票的实时行情")

        # 根据是否指定代码选择不同的超时时间
        if codes_to_update and len(codes_to_update) <= 500:
            # 小批量更新，动态计算超时时间
            # 每只股票约1.5秒（0.3秒请求 + 网络延迟），再加30秒缓冲
            timeout = len(codes_to_update) * 1.5 + 30
            logger.info(
                f"批量更新 {len(codes_to_update)} 只股票"
                f"（预计耗时约{len(codes_to_update) * 0.3 / 60:.1f}分钟）..."
            )
        else:
            # 全量更新，10分钟超时
            timeout = 600.0
            if realtime_source.lower() == 'akshare':
                logger.warning("AkShare全量实时行情获取需要3-5分钟，请耐心等待...")

        # 增量保存计数器
        saved_count = 0

        # 定义保存回调函数，每获取一条数据就立即保存
        def save_callback(quote: dict):
            nonlocal saved_count
            try:
                self.data_service.db.save_realtime_quote_single(quote, realtime_source)
                saved_count += 1
            except Exception as e:
                logger.warning(f"增量保存 {quote.get('code', 'Unknown')} 失败: {e}")

        # 获取实时行情（使用增量保存回调）
        try:
            df = await asyncio.wait_for(
                asyncio.to_thread(
                    provider.get_realtime_quotes,
                    codes=codes_to_update,
                    save_callback=save_callback
                ),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            # 超时时，部分数据已经通过回调保存
            error_msg = f"实时行情获取超时（{timeout:.0f}秒）"

            if realtime_source.lower() == 'akshare':
                if codes_to_update and len(codes_to_update) <= 500:
                    error_msg += f"\n\n批量获取 {len(codes_to_update)} 只股票超时（预期{len(codes_to_update) * 0.3:.0f}秒）。"
                    if saved_count > 0:
                        error_msg += f"\n\n✓ 已成功保存 {saved_count} 只股票的数据（增量保存）"
                    error_msg += (
                        f"\n\n可能原因：\n1. 网络延迟较大\n2. AkShare接口响应慢\n\n"
                        f"建议：\n1. 检查网络连接\n2. 减少batch_size（当前{len(codes_to_update)}）\n"
                        f"3. 在交易时段使用"
                    )
                else:
                    error_msg += "\n\nAkShare说明：全量获取需要分58个批次爬取数据，耗时较长且容易超时。"
                    if saved_count > 0:
                        error_msg += f"\n\n✓ 已成功保存 {saved_count} 只股票的数据（增量保存）"
                    error_msg += (
                        "\n\n建议：\n1. 使用渐进式更新模式（update_oldest=true）\n"
                        "2. 在交易时段（9:30-15:00）使用\n3. 检查网络连接"
                    )

            logger.warning(error_msg)

            # 如果有部分数据保存成功，返回部分成功响应
            if saved_count > 0:
                return {
                    "total": saved_count,
                    "requested": len(codes_to_update) if codes_to_update else "all",
                    "batch_size": batch_size or "all",
                    "update_mode": "oldest_first" if update_oldest else "full",
                    "updated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "timeout": True,
                    "timeout_message": error_msg,
                    "partial_success": True
                }
            else:
                raise TimeoutError(error_msg)

        if df.empty:
            raise ValueError("无实时行情数据")

        # 数据已通过回调增量保存，这里只记录日志
        logger.info(f"✓ 实时行情更新完成: {saved_count} 只股票（增量保存）")

        return {
            "total": saved_count,
            "batch_size": batch_size or "all",
            "update_mode": "oldest_first" if update_oldest else "full",
            "updated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "incremental_save": True
        }
