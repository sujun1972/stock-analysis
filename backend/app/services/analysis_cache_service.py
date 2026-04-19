"""
分析结果缓存服务

基于 sync_history 的依赖检测机制：
- 分析结果生成时，记录其依赖的数据表最近一次成功同步时间戳
- 下次请求时，比较当前依赖表的最新同步时间戳与缓存中记录的时间戳
- 如果一致，直接返回缓存；如果不一致，说明底层数据已更新，需重新计算

使用 Redis 存储缓存，避免占用数据库连接。
"""

import asyncio
import hashlib
import json
from typing import Any, Dict, List, Optional

from loguru import logger

from app.core.cache import cache
from app.repositories.sync_history_repository import SyncHistoryRepository


# ────────────────────────────────────────────────────────
# 分析类型 → 依赖数据表映射
# 当依赖表中任意一张表有新的成功同步，该分析类型的缓存即失效
# ────────────────────────────────────────────────────────

ANALYSIS_DEPENDENCIES: Dict[str, List[str]] = {
    # 技术指标 / Alpha 因子 / 特征工程（依赖行情 + 基础数据）
    'features': [
        'stock_daily', 'adj_factor', 'daily_basic', 'stk_limit_d', 'suspend',
    ],
    'features_technical': [
        'stock_daily', 'adj_factor', 'daily_basic',
    ],
    'features_alpha': [
        'stock_daily', 'adj_factor', 'daily_basic',
    ],

    # 资金流向分析
    'moneyflow_analysis': [
        'moneyflow', 'moneyflow_stock_dc', 'moneyflow_ind_dc',
        'moneyflow_mkt_dc', 'moneyflow_hsgt',
    ],

    # 财务分析
    'financial_analysis': [
        'income', 'balancesheet', 'cashflow', 'forecast', 'express',
        'dividend', 'fina_indicator', 'fina_audit', 'fina_mainbz',
        'disclosure_date',
    ],

    # 筹码分析
    'chip_analysis': [
        'cyq_perf', 'cyq_chips',
    ],

    # 两融分析
    'margin_analysis': [
        'margin', 'margin_detail', 'margin_secs', 'slb_len',
    ],

    # 北向资金分析
    'northbound_analysis': [
        'hk_hold', 'hsgt_top10', 'moneyflow_hsgt',
        'ccass_hold', 'ccass_hold_detail',
    ],

    # 打板 / 涨停分析
    'limit_analysis': [
        'limit_list', 'limit_step', 'limit_cpt',
        'top_list', 'top_inst',
        'dc_index', 'dc_member', 'dc_daily',
    ],

    # 板块行情分析（板块元数据 + 日行情 + 板块资金 + 涨停板集中度）
    'sector_analysis': [
        'dc_index', 'dc_daily', 'moneyflow_ind_dc', 'limit_cpt',
    ],

    # 市场情绪 AI 分析（打板专题 + 大盘/北向资金 + 龙虎榜机构席位）
    'sentiment_analysis': [
        'limit_list', 'limit_step', 'limit_cpt',
        'top_list', 'top_inst',
        'moneyflow_mkt_dc', 'moneyflow_hsgt',
    ],

    # 综合选股（依赖几乎全部行情 + 财务 + 资金）
    'stock_selection': [
        'stock_daily', 'adj_factor', 'daily_basic',
        'moneyflow', 'moneyflow_stock_dc',
        'income', 'balancesheet', 'cashflow', 'fina_indicator',
        'margin', 'hk_hold',
    ],

    # 参考数据分析
    'reference_analysis': [
        'stk_shock', 'stk_high_shock', 'stk_alert',
        'pledge_stat', 'repurchase', 'share_float',
        'block_trade', 'stk_holdernumber', 'stk_holdertrade',
    ],

    # 集合竞价 / 特色数据分析
    'auction_analysis': [
        'stk_auction_o', 'stk_auction_c', 'stk_nineturn',
        'stk_ah_comparison', 'stk_surv', 'broker_recommend',
        'report_rc',
    ],
}

# Redis 缓存 TTL（秒），作为兜底过期时间（即使依赖未变也最多缓存这么久）
ANALYSIS_CACHE_TTL = 86400  # 24 小时


class AnalysisCacheService:
    """
    分析结果缓存服务

    使用方式：
    1. get_cached(analysis_type, params) — 查缓存，依赖表未变更则命中
    2. set_cached(analysis_type, params, data) — 写缓存，自动记录依赖时间戳
    3. invalidate(analysis_type) — 手动清除某类缓存
    """

    def __init__(self):
        self._sync_history_repo = SyncHistoryRepository()
        self._cache = cache

    def _make_cache_key(self, analysis_type: str, params_hash: str) -> str:
        return f"analysis_cache:{analysis_type}:{params_hash}"

    def _hash_params(self, params: Dict[str, Any]) -> str:
        params_str = json.dumps(params, sort_keys=True, default=str)
        return hashlib.md5(params_str.encode()).hexdigest()

    async def get_dep_sync_timestamp(
        self,
        analysis_type: str,
        dep_tables: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        获取分析类型依赖的数据表最近一次成功同步的时间戳。

        Args:
            analysis_type: 分析类型（对应 ANALYSIS_DEPENDENCIES 的 key）
            dep_tables: 自定义依赖表列表（覆盖默认映射）

        Returns:
            ISO 格式时间戳字符串，或 None
        """
        tables = dep_tables or ANALYSIS_DEPENDENCIES.get(analysis_type)
        if not tables:
            logger.warning(f"未找到分析类型 '{analysis_type}' 的依赖映射，缓存将不会生效")
            return None
        return await asyncio.to_thread(
            self._sync_history_repo.get_max_completed_at, tables
        )

    async def get_cached(
        self,
        analysis_type: str,
        params: Dict[str, Any],
        dep_tables: Optional[List[str]] = None,
    ) -> Optional[Any]:
        """
        尝试获取有效的缓存结果。

        如果缓存存在且依赖表未发生新的同步，返回缓存数据；
        否则返回 None。

        Args:
            analysis_type: 分析类型
            params: 查询参数（用于生成唯一缓存键）
            dep_tables: 自定义依赖表列表

        Returns:
            缓存的分析结果，或 None
        """
        params_hash = self._hash_params(params)
        cache_key = self._make_cache_key(analysis_type, params_hash)

        cached = await self._cache.get(cache_key)
        if cached is None:
            return None

        # 校验依赖是否变更
        cached_dep_ts = cached.get('dep_sync_at')
        current_dep_ts = await self.get_dep_sync_timestamp(analysis_type, dep_tables)

        if cached_dep_ts == current_dep_ts:
            logger.debug(f"分析缓存命中: {analysis_type} (dep_sync_at={cached_dep_ts})")
            return cached.get('data')

        logger.info(
            f"分析缓存失效: {analysis_type} "
            f"(cached={cached_dep_ts}, current={current_dep_ts})"
        )
        return None

    async def set_cached(
        self,
        analysis_type: str,
        params: Dict[str, Any],
        data: Any,
        dep_tables: Optional[List[str]] = None,
    ) -> bool:
        """
        缓存分析结果，同时记录当前依赖表的同步时间戳。

        Args:
            analysis_type: 分析类型
            params: 查询参数
            data: 分析结果数据
            dep_tables: 自定义依赖表列表

        Returns:
            是否成功写入缓存
        """
        current_dep_ts = await self.get_dep_sync_timestamp(analysis_type, dep_tables)

        params_hash = self._hash_params(params)
        cache_key = self._make_cache_key(analysis_type, params_hash)

        cache_value = {
            'dep_sync_at': current_dep_ts,
            'data': data,
        }

        return await self._cache.set(
            cache_key, cache_value, ttl=ANALYSIS_CACHE_TTL
        )

    async def invalidate(self, analysis_type: str) -> int:
        """
        手动清除某分析类型的所有缓存。

        Args:
            analysis_type: 分析类型

        Returns:
            删除的缓存键数量
        """
        pattern = f"analysis_cache:{analysis_type}:*"
        return await self._cache.delete_pattern(pattern)

    async def invalidate_all(self) -> int:
        """清除所有分析缓存。"""
        return await self._cache.delete_pattern("analysis_cache:*")


# 单例
_analysis_cache_service: Optional[AnalysisCacheService] = None


def get_analysis_cache_service() -> AnalysisCacheService:
    global _analysis_cache_service
    if _analysis_cache_service is None:
        _analysis_cache_service = AnalysisCacheService()
    return _analysis_cache_service
