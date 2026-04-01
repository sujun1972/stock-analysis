"""
股票基本信息服务

职责：
- 从 stock_basic 表查询完整的股票基础信息（含 Tushare 扩展字段）
- 若库中无完整数据（fullname 为空），则触发一次全量 stock_basic 同步后再返回
"""

import asyncio
from typing import Optional, Dict

from loguru import logger

from app.repositories.stock_basic_repository import StockBasicRepository
from app.repositories.daily_basic_repository import DailyBasicRepository
from app.services.stock_quote_cache import stock_quote_cache


class StockBasicService:
    """
    股票基本信息服务

    对外提供单只股票的完整基础信息（17 个 Tushare 字段 + 实时行情）。
    当数据库中缺少 fullname（说明 Tushare 扩展字段尚未同步），
    会触发一次 stock_basic 全量同步后再重试查询。
    """

    def __init__(self):
        self.repo = StockBasicRepository()
        self.daily_basic_repo = DailyBasicRepository()

    async def get_stock_basic_info(self, ts_code: str) -> Optional[Dict]:
        """
        获取股票完整基础信息

        Args:
            ts_code: Tushare 标准代码（如 '000001.SZ'）或纯数字代码（如 '000001'）

        Returns:
            含全部字段的股票信息字典（追加实时行情字段），不存在则返回 None
        """
        # 自动补全 ts_code
        resolved = await stock_quote_cache.resolve_ts_code(ts_code)
        lookup_code = resolved or ts_code

        # 第一次查询
        info = await asyncio.to_thread(self.repo.get_full_by_ts_code, lookup_code)

        # fullname 为空说明扩展字段未同步，触发一次同步后重试
        if info and not info.get('fullname'):
            logger.info(f"股票 {lookup_code} 的 Tushare 扩展字段为空，触发 stock_basic 同步")
            synced = await self._sync_stock_basic()
            if synced:
                info = await asyncio.to_thread(self.repo.get_full_by_ts_code, lookup_code)

        if not info:
            return None

        # 追加实时行情信息（price / pct_change 等）
        quotes = await stock_quote_cache.get_quotes_batch([lookup_code])
        quote = quotes.get(lookup_code, {})
        info.update({
            'latest_price': quote.get('latest_price'),
            'pct_change': quote.get('pct_change'),
            'change_amount': quote.get('change_amount'),
            'volume': quote.get('volume'),
            'amount': quote.get('amount'),
            'turnover': quote.get('turnover'),
            'trade_time': quote.get('trade_time'),
        })

        return info

    async def get_stock_quote_panel(self, ts_code: str) -> Optional[Dict]:
        """
        获取行情面板数据：合并 stock_realtime（实时价格）+ daily_basic（估值指标）

        字段说明：
          stock_realtime  -> latest_price, open, high, low, pre_close,
                             pct_change, change_amount, volume, amount,
                             amplitude, turnover, trade_time
          daily_basic     -> pe, pe_ttm, pb, ps, ps_ttm,
                             volume_ratio, turnover_rate, turnover_rate_f,
                             dv_ratio, dv_ttm,
                             total_share, float_share, free_share,
                             total_mv, circ_mv,
                             trade_date (daily_basic 日期，供前端显示数据时效)

        Returns:
            合并后的行情面板字典，均无数据时返回 None
        """
        # 自动补全 ts_code
        resolved = await stock_quote_cache.resolve_ts_code(ts_code)
        lookup_code = resolved or ts_code
        # 纯数字 code（用于 stock_realtime 表，该表 code 列存储的是不含后缀的形式）
        pure_code = lookup_code.split('.')[0] if '.' in lookup_code else lookup_code

        # 并发：实时行情 + daily_basic 最新一条
        quotes, daily_rows = await asyncio.gather(
            stock_quote_cache.get_quotes_batch([lookup_code]),
            asyncio.to_thread(
                self.daily_basic_repo.get_by_code_and_date_range,
                lookup_code, None, None, 1
            ),
        )

        quote = quotes.get(lookup_code, {})
        daily = daily_rows[0] if daily_rows else {}

        # 两边都没有数据时返回 None
        if not quote and not daily:
            return None

        def _mv_yi(val):
            """万元 -> 亿元"""
            if val is None:
                return None
            return round(val / 10000, 2)

        result: Dict = {
            # ── 实时行情（stock_realtime） ──
            'latest_price': quote.get('latest_price'),
            'open': quote.get('open'),
            'high': quote.get('high'),
            'low': quote.get('low'),
            'pre_close': quote.get('pre_close'),
            'pct_change': quote.get('pct_change'),
            'change_amount': quote.get('change_amount'),
            'volume': quote.get('volume'),           # 股
            'amount': quote.get('amount'),           # 元
            'amplitude': quote.get('amplitude'),     # %
            'turnover': quote.get('turnover'),        # % (realtime)
            'trade_time': quote.get('trade_time'),
            # ── 每日估值指标（daily_basic，收盘后更新） ──
            'daily_date': daily.get('trade_date'),
            'pe': daily.get('pe'),
            'pe_ttm': daily.get('pe_ttm'),
            'pb': daily.get('pb'),
            'ps': daily.get('ps'),
            'ps_ttm': daily.get('ps_ttm'),
            'volume_ratio': daily.get('volume_ratio'),
            'turnover_rate': daily.get('turnover_rate'),
            'turnover_rate_f': daily.get('turnover_rate_f'),
            'dv_ratio': daily.get('dv_ratio'),
            'dv_ttm': daily.get('dv_ttm'),
            'total_share': daily.get('total_share'),   # 万股
            'float_share': daily.get('float_share'),   # 万股
            'free_share': daily.get('free_share'),     # 万股
            'total_mv': _mv_yi(daily.get('total_mv')),   # 亿元
            'circ_mv': _mv_yi(daily.get('circ_mv')),     # 亿元
        }
        return result

    async def _sync_stock_basic(self) -> bool:
        """
        触发 stock_basic 全量同步（通过已有的 StockListSyncService）

        Returns:
            同步是否成功
        """
        try:
            from app.services.stock_list_sync_service import StockListSyncService
            service = StockListSyncService()
            result = await service.sync_stock_list()
            logger.info(f"stock_basic 同步完成: {result}")
            return True
        except Exception as e:
            logger.warning(f"stock_basic 同步失败（将返回现有数据）: {e}")
            return False
