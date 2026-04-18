"""
股票行情缓存服务

从 stock_realtime 表读取价格/涨跌幅，从 stock_basic 表读取名称，
存入 Redis。交易时间 TTL=60s，非交易时间 TTL=3600s。
缓存不可用时降级为直接查数据库，不影响主流程。
"""
import asyncio
from datetime import time, datetime
from typing import Dict, List, Optional

import pytz
from loguru import logger

from app.core.cache import cache
from app.core.config import settings
from app.repositories.base_repository import BaseRepository


# Redis key 前缀
KEY_PREFIX = "stock:quote"


def is_trading_hours() -> bool:
    """判断当前是否处于 A 股交易时间（上海时区，周一至周五 09:30-11:30 / 13:00-15:00）"""
    tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(tz)
    if now.weekday() >= 5:
        return False
    t = now.time()
    return (time(9, 30) <= t <= time(11, 30)) or (time(13, 0) <= t <= time(15, 0))


def quote_ttl() -> int:
    """根据当前是否交易时间返回合适的 TTL（来自 settings.cache_ttl）"""
    return settings.cache_ttl.quote_trading if is_trading_hours() else settings.cache_ttl.quote_non_trading


class _QuoteRepository(BaseRepository):
    """内部用：从数据库批量查询行情快照"""

    def get_quotes(self, ts_codes: List[str]) -> Dict[str, dict]:
        """
        批量查询股票行情（price/pct_change）和名称。

        ts_code 格式：000001.SZ
        stock_realtime.code 格式：000001（无交易所后缀）
        stock_basic.ts_code 格式：000001.SZ

        Args:
            ts_codes: ts_code 列表

        Returns:
            { ts_code: { name, latest_price, pct_change, change_amount, open, high, low,
                         pre_close, volume, amount, turnover, amplitude, trade_time, price } }
        """
        if not ts_codes:
            return {}

        placeholders = ','.join(['%s'] * len(ts_codes))

        # stock_realtime 用纯代码（去后缀）关联，stock_basic 用 ts_code 关联
        query = f"""
            SELECT
                sb.ts_code,
                sb.name,
                sr.latest_price,
                sr.pct_change,
                sr.change_amount,
                sr.open,
                sr.high,
                sr.low,
                sr.pre_close,
                sr.volume,
                sr.amount,
                sr.turnover,
                sr.amplitude,
                sr.trade_time
            FROM stock_basic sb
            LEFT JOIN stock_realtime sr
                ON sr.code = split_part(sb.ts_code, '.', 1)
            WHERE sb.ts_code IN ({placeholders})
        """

        try:
            rows = self.execute_query(query, tuple(ts_codes))
            result = {}
            for row in rows:
                ts_code = row[0]
                result[ts_code] = {
                    "name":          row[1] or "",
                    "latest_price":  float(row[2])  if row[2]  is not None else None,
                    "pct_change":    float(row[3])  if row[3]  is not None else None,
                    "change_amount": float(row[4])  if row[4]  is not None else None,
                    "open":          float(row[5])  if row[5]  is not None else None,
                    "high":          float(row[6])  if row[6]  is not None else None,
                    "low":           float(row[7])  if row[7]  is not None else None,
                    "pre_close":     float(row[8])  if row[8]  is not None else None,
                    "volume":        int(row[9])     if row[9]  is not None else None,
                    "amount":        float(row[10]) if row[10] is not None else None,
                    "turnover":      float(row[11]) if row[11] is not None else None,
                    "amplitude":     float(row[12]) if row[12] is not None else None,
                    "trade_time":    str(row[13])   if row[13] is not None else None,
                    # 兼容旧字段名
                    "price":         float(row[2])  if row[2]  is not None else None,
                }
            return result
        except Exception as e:
            logger.error(f"_QuoteRepository.get_quotes 失败: {e}")
            return {}

    def resolve_ts_codes(self, pure_codes: List[str]) -> Dict[str, str]:
        """
        将纯股票代码批量补全为完整 ts_code。

        从 stock_basic 表查询，支持 stock_basic.code（纯数字代码）字段。

        Args:
            pure_codes: 纯代码列表，如 ['000001', '600519']

        Returns:
            { pure_code: ts_code }，如 {'000001': '000001.SZ', '600519': '600519.SH'}
            查不到的 pure_code 不出现在结果中
        """
        if not pure_codes:
            return {}

        placeholders = ','.join(['%s'] * len(pure_codes))
        query = f"SELECT code, ts_code FROM stock_basic WHERE code IN ({placeholders})"

        try:
            rows = self.execute_query(query, tuple(pure_codes))
            return {row[0]: row[1] for row in rows if row[0] and row[1]}
        except Exception as e:
            logger.error(f"_QuoteRepository.resolve_ts_codes 失败: {e}")
            return {}


class StockQuoteCache:
    """
    股票行情缓存服务（单例，对外暴露 get_quotes_batch）

    使用方式：
        from app.services.stock_quote_cache import stock_quote_cache

        quotes = await stock_quote_cache.get_quotes_batch(['000001.SZ', '600519.SH'])
        # quotes = { '000001.SZ': { name, price, pct_change }, ... }
    """

    def __init__(self):
        self._repo = _QuoteRepository()

    async def get_quotes_batch(self, ts_codes: List[str]) -> Dict[str, dict]:
        """
        批量获取股票行情，优先走 Redis 缓存，未命中则查数据库并回填缓存。

        Args:
            ts_codes: ts_code 列表（去重后处理）

        Returns:
            { ts_code: { name, price, pct_change } }
            对于查不到的股票返回 { name: '', price: None, pct_change: None }
        """
        unique_codes = list(dict.fromkeys(ts_codes))  # 去重保序
        if not unique_codes:
            return {}

        result: Dict[str, dict] = {}
        miss: List[str] = []

        # 1. 并发读 Redis
        cache_results = await asyncio.gather(
            *[cache.get(f"{KEY_PREFIX}:{code}") for code in unique_codes],
            return_exceptions=True
        )

        for code, cached in zip(unique_codes, cache_results):
            if isinstance(cached, Exception) or cached is None:
                miss.append(code)
            else:
                result[code] = cached

        # 2. 未命中部分查数据库
        if miss:
            db_data = await asyncio.to_thread(self._repo.get_quotes, miss)

            ttl = quote_ttl()
            write_tasks = []
            for code in miss:
                quote = db_data.get(code, {"name": "", "price": None, "pct_change": None})
                result[code] = quote
                write_tasks.append(cache.set(f"{KEY_PREFIX}:{code}", quote, ttl))

            # 异步回填缓存，不阻塞返回
            if write_tasks:
                asyncio.create_task(_write_cache_background(write_tasks))

            logger.debug(f"StockQuoteCache miss {len(miss)} 条，TTL={ttl}s")

        return result

    async def resolve_ts_code(self, user_input: str) -> Optional[str]:
        """
        将用户输入的股票代码（可能是纯数字代码或完整 ts_code）补全为完整 ts_code。

        规则：
          - 输入已包含 '.' → 视为完整 ts_code，直接返回（如 '000001.SZ'）
          - 否则视为纯代码 → 查 stock_basic.code 补全后缀（如 '000001' → '000001.SZ'）

        优先从 Redis 缓存读取已解析结果（key: stock:code_map:{pure_code}），
        未命中则查数据库，结果缓存 24 小时（交易所后缀极少变化）。

        Args:
            user_input: 用户输入的代码，如 '000001' 或 '000001.SZ'

        Returns:
            完整 ts_code，如 '000001.SZ'；查不到返回 None
        """
        if not user_input:
            return None

        cleaned = user_input.strip()

        # 已包含后缀，直接返回
        if '.' in cleaned:
            return cleaned.upper()

        pure_code = cleaned

        # 先查缓存
        cache_key = f"stock:code_map:{pure_code}"
        cached = await cache.get(cache_key)
        if cached:
            return cached

        # 查数据库
        mapping = await asyncio.to_thread(self._repo.resolve_ts_codes, [pure_code])
        ts_code = mapping.get(pure_code)

        if ts_code:
            # 代码映射很稳定，缓存 24 小时
            await cache.set(cache_key, ts_code, 86400)

        return ts_code

    def get_quotes_sync(self, ts_codes: List[str]) -> Dict[str, dict]:
        """
        批量获取股票行情（同步版本，不走 Redis，直接查数据库）。

        用于 Service 在同步上下文中注入股票名称（如被 `asyncio.to_thread` 包围的同步方法，
        或已在后台线程中执行的任务）。调用方应自行决定是否用 `asyncio.to_thread` 包裹。

        返回字段与 `get_quotes_batch` 一致。
        """
        unique_codes = list(dict.fromkeys(ts_codes))
        if not unique_codes:
            return {}
        return self._repo.get_quotes(unique_codes)

    async def invalidate(self, ts_codes: List[str]) -> None:
        """主动失效指定股票的缓存（行情更新后调用）"""
        for code in ts_codes:
            await cache.delete(f"{KEY_PREFIX}:{code}")

    async def invalidate_all(self) -> int:
        """清空所有股票行情缓存"""
        return await cache.delete_pattern(f"{KEY_PREFIX}:*")


async def _write_cache_background(tasks):
    """后台批量写缓存，捕获异常不影响主流程"""
    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        logger.warning(f"StockQuoteCache 后台写缓存失败: {e}")


# 全局单例
stock_quote_cache = StockQuoteCache()
