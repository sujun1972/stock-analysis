"""
财报披露计划服务

负责财报披露计划数据的业务逻辑处理
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List
import asyncio
from loguru import logger

from app.repositories.disclosure_date_repository import DisclosureDateRepository
from app.repositories.sync_config_repository import SyncConfigRepository
from core.src.providers import DataProviderFactory
from app.core.config import settings


class DisclosureDateService:
    """财报披露计划服务"""

    def __init__(self):
        self.disclosure_date_repo = DisclosureDateRepository()
        self.provider_factory = DataProviderFactory()

    async def sync_incremental(self) -> Dict:
        """增量同步：从 sync_configs 读取回看天数，自动计算日期范围。"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, 'disclosure_date')
        default_days = (cfg.get('incremental_default_days') or 90) if cfg else 90
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=default_days)).strftime('%Y%m%d')
        logger.info(f"[disclosure_date] 增量同步 start_date={start_date} end_date={end_date}（回看 {default_days} 天）")
        return await self.sync_disclosure_date(end_date=end_date)

    def _get_provider(self):
        """获取Tushare数据提供者（缓存，每个实例只初始化一次）"""
        if not hasattr(self, '_provider') or self._provider is None:
            self._provider = self.provider_factory.create_provider(
                source='tushare',
                token=settings.TUSHARE_TOKEN
            )
        return self._provider

    async def get_disclosure_date_data(
        self,
        ts_code: Optional[str] = None,
        end_date: Optional[str] = None,
        start_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0
    ) -> Dict:
        """
        获取财报披露计划数据

        Args:
            ts_code: 股票代码
            end_date: 截止日期（报告期），格式：YYYYMMDD
            start_date: 开始日期（报告期），格式：YYYYMMDD
            limit: 限制返回记录数
            offset: 偏移量

        Returns:
            包含数据列表和统计信息的字典
        """
        try:
            total, items, statistics = await asyncio.gather(
                asyncio.to_thread(
                    self.disclosure_date_repo.get_total_count,
                    start_date=start_date,
                    end_date=end_date,
                    ts_code=ts_code
                ),
                asyncio.to_thread(
                    self.disclosure_date_repo.get_by_date_range,
                    start_date,
                    end_date,
                    ts_code,
                    limit,
                    offset
                ),
                asyncio.to_thread(
                    self.disclosure_date_repo.get_statistics,
                    start_date,
                    end_date
                )
            )

            # 日期格式转换：YYYYMMDD -> YYYY-MM-DD（用于前端显示）
            for item in items:
                for field in ['ann_date', 'end_date', 'pre_date', 'actual_date', 'modify_date']:
                    if item.get(field) and len(str(item[field])) == 8:
                        date_str = str(item[field])
                        item[field] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

            return {
                "items": items,
                "statistics": statistics,
                "total": total
            }

        except Exception as e:
            logger.error(f"获取财报披露计划数据失败: {e}")
            raise

    @staticmethod
    def _generate_quarters(start_date: str) -> List[str]:
        """生成从 start_date 到今天的所有季度末日期列表（YYYYMMDD）"""
        start_year = int(start_date[:4])
        quarter_ends = [331, 630, 930, 1231]
        today_int = int(datetime.now().strftime("%Y%m%d"))
        start_int = int(start_date)
        periods = []
        for y in range(start_year, datetime.now().year + 1):
            for qe in quarter_ends:
                period_str = f"{y}{qe:04d}"
                if start_int <= int(period_str) <= today_int:
                    periods.append(period_str)
        return periods

    async def sync_full_history(
        self,
        redis_client,
        start_date: Optional[str] = None,
        update_state_fn=None
    ) -> Dict:
        """
        全量历史同步：按季度 period 切片，支持 Redis 续继

        Args:
            redis_client: Redis 客户端
            start_date: 起始日期 YYYYMMDD，默认 20090101
            update_state_fn: Celery 进度回调

        Returns:
            同步结果
        """
        PROGRESS_KEY = "sync:disclosure_date:full_history:progress"
        start_date = start_date or "20090101"
        all_periods = self._generate_quarters(start_date)

        completed_raw = redis_client.smembers(PROGRESS_KEY) if redis_client else set()
        completed = {p.decode() if isinstance(p, bytes) else p for p in (completed_raw or [])}
        pending = [p for p in all_periods if p not in completed]

        logger.info(f"全量同步财报披露计划: 共 {len(all_periods)} 个季度，待同步 {len(pending)} 个")

        sem = asyncio.Semaphore(3)
        total_records = 0
        errors = []

        async def sync_one(period: str):
            nonlocal total_records
            async with sem:
                try:
                    result = await self.sync_disclosure_date(end_date=period)
                    records = result.get("records", 0)
                    total_records += records
                    if redis_client:
                        redis_client.sadd(PROGRESS_KEY, period)
                    logger.info(f"✓ period={period}: {records} 条")
                except Exception as e:
                    errors.append(f"period={period}: {e}")
                    logger.error(f"同步 period={period} 失败: {e}")

        tasks_list = [sync_one(p) for p in pending]
        for i, coro in enumerate(asyncio.as_completed(tasks_list)):
            await coro
            if update_state_fn:
                progress = int((len(completed) + i + 1) / max(len(all_periods), 1) * 100)
                update_state_fn(state='PROGRESS', meta={'progress': progress})

        if not errors and redis_client:
            redis_client.delete(PROGRESS_KEY)

        return {
            "status": "success" if not errors else "partial",
            "records": total_records,
            "errors": errors,
            "message": f"同步完成，共 {total_records} 条记录" + (f"，{len(errors)} 个季度失败" if errors else "")
        }

    async def sync_disclosure_date(
        self,
        ts_code: Optional[str] = None,
        end_date: Optional[str] = None,
        pre_date: Optional[str] = None,
        ann_date: Optional[str] = None,
        actual_date: Optional[str] = None
    ) -> Dict:
        """
        同步财报披露计划数据

        Args:
            ts_code: 股票代码
            end_date: 报告期（每个季度最后一天），格式：YYYYMMDD
            pre_date: 计划披露日期，格式：YYYYMMDD
            ann_date: 最新披露公告日，格式：YYYYMMDD
            actual_date: 实际披露日期，格式：YYYYMMDD

        Returns:
            同步结果
        """
        try:
            # 获取 Tushare Provider
            provider = self._get_provider()

            # 调用 Tushare API 获取数据
            logger.info(f"开始从Tushare获取财报披露计划数据: ts_code={ts_code}, end_date={end_date}")
            df = await asyncio.to_thread(
                provider.get_disclosure_date,
                ts_code=ts_code,
                end_date=end_date,
                pre_date=pre_date,
                ann_date=ann_date,
                actual_date=actual_date
            )

            if df is None or df.empty:
                logger.warning("未获取到财报披露计划数据")
                return {
                    "status": "success",
                    "records": 0,
                    "message": "未获取到数据"
                }

            logger.info(f"获取到 {len(df)} 条财报披露计划数据")

            # 数据验证和清洗
            df = self._validate_and_clean_data(df)

            # 批量插入数据库
            records = await asyncio.to_thread(
                self.disclosure_date_repo.bulk_upsert,
                df
            )

            logger.info(f"成功同步 {records} 条财报披露计划数据")

            return {
                "status": "success",
                "records": records,
                "message": f"成功同步 {records} 条数据"
            }

        except Exception as e:
            logger.error(f"同步财报披露计划数据失败: {e}")
            return {
                "status": "error",
                "records": 0,
                "error": str(e)
            }

    def _validate_and_clean_data(self, df):
        """
        验证和清洗数据

        Args:
            df: 原始DataFrame

        Returns:
            清洗后的DataFrame
        """
        try:
            # 确保必需字段存在（只有ts_code和end_date是必需的）
            required_fields = ['ts_code', 'end_date']
            for field in required_fields:
                if field not in df.columns:
                    raise ValueError(f"缺少必需字段: {field}")

            # 移除重复记录（根据主键：ts_code + end_date）
            df = df.drop_duplicates(subset=['ts_code', 'end_date'], keep='last')

            # 填充可选字段的None值
            optional_fields = ['ann_date', 'pre_date', 'actual_date', 'modify_date']
            for field in optional_fields:
                if field not in df.columns:
                    df[field] = None

            logger.debug(f"数据验证完成，共 {len(df)} 条有效记录")
            return df

        except Exception as e:
            logger.error(f"数据验证失败: {e}")
            raise
