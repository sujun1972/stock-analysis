"""
宏观经济指标同步服务（AkShare）

两条入口：
  - sync_incremental(): 遍历 INDICATOR_FETCHERS，每个 key 拉一次完整历史 → bulk_upsert
  - sync_full_history(): AkShare 宏观接口不支持日期参数，退化为单次增量（按钮兼容）

每个 AkShare 宏观接口返回的都是"完整历史序列"（CPI 1996 起、Shibor 2015 起、
PMI 2008 起等）。因此无论增量还是全量，调用一次即全量 UPSERT；后续只是
用 ON CONFLICT 把新一期 / 修订数据覆盖上去。单次总耗时约 2-3 分钟（7 个
接口串行，每个 10~30s）。
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from app.repositories.macro_indicators_repository import MacroIndicatorsRepository
from app.repositories.sync_history_repository import SyncHistoryRepository


class MacroSyncService:
    """宏观经济指标同步服务。"""

    TABLE_KEY = "macro_indicators"
    # AkShare 接口无日期参数，"进度" key 仅作 sync_dashboard 兼容字段，无真实续继语义
    FULL_HISTORY_PROGRESS_KEY = "sync:macro_indicators:full_history:progress"
    FULL_HISTORY_LOCK_KEY = "sync:macro_indicators:full_history:lock"

    def __init__(self) -> None:
        self.repo = MacroIndicatorsRepository()
        self.sync_history_repo = SyncHistoryRepository()

    # -------------------------------------------------
    # Provider（惰性初始化）
    # -------------------------------------------------

    def _get_provider(self):
        cached = getattr(self, '_provider', None)
        if cached is not None:
            return cached
        from core.src.providers import DataProviderFactory
        self._provider = DataProviderFactory.create_provider(source='akshare')
        return self._provider

    def _get_fetcher_keys(self) -> List[str]:
        """Provider 层维护的 indicator fetcher key 列表（不含派生 code，如 pmi_manu）。"""
        provider = self._get_provider()
        fetchers = getattr(provider, 'MACRO_INDICATOR_FETCHERS', None) or {}
        return list(fetchers.keys())

    # -------------------------------------------------
    # 增量（= 遍历所有 fetcher key，各拉一次完整序列）
    # -------------------------------------------------

    async def sync_incremental(
        self,
        start_date: Optional[str] = None,       # 占位：AkShare 宏观接口无日期参数
        end_date: Optional[str] = None,         # 占位
        sync_strategy: Optional[str] = None,    # 占位
        max_requests_per_minute: Optional[int] = None,  # 占位
    ) -> Dict[str, Any]:
        """遍历所有宏观指标并 UPSERT；记录 sync_history。"""
        today = datetime.now().strftime('%Y%m%d')
        history_id = await asyncio.to_thread(
            self.sync_history_repo.create, self.TABLE_KEY, 'incremental', 'snapshot', today,
        )
        keys = self._get_fetcher_keys()
        logger.info(f"[macro_indicators] 增量同步 {len(keys)} 个指标: {keys}")

        total_records = 0
        per_indicator: Dict[str, int] = {}
        errors: List[str] = []

        try:
            for key in keys:
                try:
                    records = await self._sync_one_indicator(key)
                    per_indicator[key] = records
                    total_records += records
                except Exception as e:
                    errors.append(f"{key}: {e}")
                    logger.warning(f"[macro_indicators] {key} 同步失败: {e}")

            # 只要有一个指标入库就视为 success（部分失败不阻断），全部失败才标 failure
            status = 'success' if total_records > 0 else 'failure'
            err_msg = '; '.join(errors[:3]) if errors else None
            await asyncio.to_thread(
                self.sync_history_repo.complete,
                history_id, status, total_records, today, err_msg,
            )
            return {
                "status": status,
                "records": total_records,
                "indicators": per_indicator,
                "errors": errors,
            }
        except Exception as e:
            await asyncio.to_thread(
                self.sync_history_repo.complete,
                history_id, 'failure', total_records, None, str(e),
            )
            raise

    async def _sync_one_indicator(self, key: str) -> int:
        """拉取单个宏观指标的完整序列并 UPSERT。"""
        provider = self._get_provider()
        response = await asyncio.to_thread(provider.get_macro_indicator, key)
        if not response.is_success() and response.status.name != 'WARNING':
            raise RuntimeError(
                f"AkShare get_macro_indicator({key}) 失败: {response.error or response.error_code}"
            )
        df = response.data
        if df is None or df.empty:
            logger.debug(f"[macro_indicators] {key} 空序列（接口 warning 或无数据）")
            return 0
        count = await asyncio.to_thread(self.repo.bulk_upsert, df)
        logger.info(f"[macro_indicators] {key} UPSERT {count} 条（原始 {len(df)}）")
        return count

    # -------------------------------------------------
    # 全量（接口无日期参数，等价于一次增量）
    # -------------------------------------------------

    async def sync_full_history(
        self,
        redis_client,                       # 接口兼容 _task_factory，未使用
        start_date: Optional[str] = None,   # 同上
        concurrency: int = 1,               # 同上
        update_state_fn=None,               # 同上
        max_requests_per_minute: int = 0,   # 同上
    ) -> Dict[str, Any]:
        """AkShare 宏观接口无 date 参数，全量等价于一次增量。"""
        logger.info("[macro_indicators] AkShare 接口无日期参数，全量退化为单次增量")
        result = await self.sync_incremental()
        return {
            "status": result.get("status", "success"),
            "success": 1 if result.get("records", 0) > 0 else 0,
            "skipped": 0,
            "errors": len(result.get("errors") or []),
            "records": result.get("records", 0),
            "note": "AkShare 宏观接口不支持按日期回溯，每次拉完整历史并 UPSERT",
            "indicators": result.get("indicators", {}),
        }

    # -------------------------------------------------
    # 查询辅助（API / CIO Tool / 前端用）
    # -------------------------------------------------

    async def list_indicators(
        self,
        indicator_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        sort_by: Optional[str] = None,
        sort_order: str = 'desc',
    ) -> Dict[str, Any]:
        items, total, summary = await asyncio.gather(
            asyncio.to_thread(
                self.repo.query_by_filters,
                indicator_code=indicator_code,
                start_date=start_date, end_date=end_date,
                page=page, page_size=page_size,
                sort_by=sort_by, sort_order=sort_order,
            ),
            asyncio.to_thread(
                self.repo.count_by_filters,
                indicator_code=indicator_code,
                start_date=start_date, end_date=end_date,
            ),
            asyncio.to_thread(self.repo.get_indicator_summary),
        )
        return {
            'items': items, 'total': total, 'summary': summary,
            'page': int(page), 'page_size': int(page_size),
        }

    async def get_series(
        self,
        indicator_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 60,
    ) -> List[Dict]:
        return await asyncio.to_thread(
            self.repo.query_series, indicator_code, start_date, end_date, int(limit),
        )

    async def get_macro_snapshot(self, lookback_months: int = 12) -> Dict[str, Any]:
        """为 CIO / 宏观专家提供最新一批指标快照。

        返回：
          - latest: {indicator_code: {value/yoy/period_date/publish_date/lag_days}}
          - series: {indicator_code: [最近 lookback_months 条，按时间降序]}；
            当 lookback_months <= 0 时跳过序列拉取（仅需 latest 的场景走此分支）
        """
        # 最新快照用所有已知 indicator_code（含派生如 pmi_manu / shibor_on）
        codes = _KNOWN_INDICATOR_CODES
        latest = await asyncio.to_thread(self.repo.get_latest_snapshot, list(codes))

        if int(lookback_months) > 0:
            async def _fetch_series(code: str):
                return code, await asyncio.to_thread(
                    self.repo.query_series, code, None, None, int(lookback_months),
                )
            series_pairs = await asyncio.gather(*[_fetch_series(c) for c in codes])
            series = {code: rows for code, rows in series_pairs}
        else:
            series = {}

        # 附加 lag_days 供 LLM 直接引用"滞后 N 天"
        today = datetime.now().date()
        for snap in latest.values():
            pd_str = snap.get('period_date')
            if pd_str:
                try:
                    period = datetime.strptime(pd_str, '%Y-%m-%d').date()
                    snap['lag_days'] = (today - period).days
                except ValueError:
                    snap['lag_days'] = None
            else:
                snap['lag_days'] = None

        return {
            'latest': latest,
            'series': series,
            'indicators': list(codes),
            'lookback_months': int(lookback_months),
        }


# 已知的 indicator_code 列表（含 PMI / Shibor 派生 code）——与 Provider mixin 中的 normalizer 输出一致
_KNOWN_INDICATOR_CODES = (
    'cpi_yoy',
    'ppi_yoy',
    'pmi_manu',
    'pmi_nonmanu',
    'm2_yoy',
    'new_credit_month',
    'gdp_yoy',
    'shibor_on',
    'shibor_1w',
    'shibor_1m',
)
