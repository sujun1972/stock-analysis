"""
快讯正文个股代码提取器（Task 2.4）

从快讯 title/summary 中提取 A 股 `ts_code`，采用"正则 + stock_basic 白名单"双重校验：
  1. 正则匹配 6 位数字（前缀限定为 A 股合法段：000/001/002/003/300/301/600/601/603/605/688/689/830-839/870-873）
  2. 用 `StockBasicRepository.get_all_ts_codes_set()` 缓存过滤非上市 / 已退市代码
  3. 返回去重后的 ts_code 列表（如 `['000001.SZ', '600519.SH']`）

缓存刷新：首次调用时从 DB 加载一次全量白名单（~5500 条）并常驻内存；
重启 Celery worker / backend 时自动重新加载。白名单不常变（每周新增几只新股），
过时的影响可接受。如需主动刷新，调用 `StockCodeExtractor.refresh_whitelist()`。
"""

from __future__ import annotations

import re
import threading
from typing import Iterable, List, Optional, Set

from loguru import logger

# 正则说明：前瞻 + 后顾断言确保不命中 7 位及以上连号（如电话号码 18512345678）
_TS_CODE_RE = re.compile(
    r'(?<!\d)'
    r'(?:000|001|002|003|300|301|600|601|603|605|688|689|'
    r'830|831|832|833|835|836|837|838|839|870|871|872|873)'
    r'\d{3}'
    r'(?!\d)'
)


class _WhitelistCache:
    """`'000001' → '000001.SZ'` 映射的内存缓存，延迟加载 + 手动刷新。"""

    def __init__(self) -> None:
        self._pure_to_ts: Optional[dict[str, str]] = None
        self._lock = threading.Lock()

    def pure_to_ts(self) -> dict[str, str]:
        """返回缓存映射；首次调用时从 `stock_basic` 加载全量股票代码。"""
        if self._pure_to_ts is not None:
            return self._pure_to_ts
        with self._lock:
            if self._pure_to_ts is None:
                self._pure_to_ts = self._load_from_db()
                logger.info(f"[StockCodeExtractor] 白名单加载完成，{len(self._pure_to_ts)} 只股票")
            return self._pure_to_ts

    def refresh(self) -> None:
        with self._lock:
            self._pure_to_ts = self._load_from_db()
            logger.info(f"[StockCodeExtractor] 白名单刷新，{len(self._pure_to_ts)} 只股票")

    @staticmethod
    def _load_from_db() -> dict[str, str]:
        """含上市 + 退市 + 暂停，历史快讯可能提及已退市代码；`get_listed_ts_codes`
        只支持单 status，循环三次合并。"""
        from app.repositories.stock_basic_repository import StockBasicRepository
        repo = StockBasicRepository()
        ts_codes: Set[str] = set()
        for status in ('L', 'D', 'P'):
            try:
                ts_codes.update(repo.get_listed_ts_codes(status=status))
            except Exception as e:
                logger.warning(f"[StockCodeExtractor] 加载 status={status} 白名单失败: {e}")
        return {tc.split('.', 1)[0]: tc for tc in ts_codes if '.' in tc}


_cache = _WhitelistCache()


class StockCodeExtractor:
    """快讯文本中的 A 股代码提取器。"""

    @staticmethod
    def extract(text: Optional[str]) -> List[str]:
        """从文本中抽取合法 A 股 ts_code 列表（去重，保持首次出现顺序）。

        Args:
            text: 任意中文文本（title + summary）

        Returns:
            ['000001.SZ', '600519.SH', ...]；无命中返回 []
        """
        if not text:
            return []
        candidates = _TS_CODE_RE.findall(str(text))
        if not candidates:
            return []
        pure_map = _cache.pure_to_ts()
        seen: Set[str] = set()
        out: List[str] = []
        for pure in candidates:
            ts_code = pure_map.get(pure)
            if not ts_code or ts_code in seen:
                continue
            seen.add(ts_code)
            out.append(ts_code)
        return out

    @staticmethod
    def extract_from_items(items: Iterable[dict]) -> None:
        """就地为一批快讯 dict 填充 `related_ts_codes`（合并已有 + 正则抽取结果）。

        约定每条 dict 至少包含 `title` / `summary` 之一；已有 `related_ts_codes` 则合并去重。
        用于 Service 层批量处理：eastmoney 来源已自带 [ts_code]，caixin 来源需 extract。
        """
        for item in items:
            existing = item.get('related_ts_codes') or []
            # AkShare 返回的 tuple / numpy array 统一成 list
            if not isinstance(existing, list):
                existing = list(existing)
            text_parts = [str(item.get('title') or ''), str(item.get('summary') or '')]
            extracted = StockCodeExtractor.extract(' '.join(text_parts))
            merged: List[str] = []
            seen: Set[str] = set()
            for tc in (*existing, *extracted):
                if tc and tc not in seen:
                    seen.add(tc)
                    merged.append(tc)
            item['related_ts_codes'] = merged

    @staticmethod
    def refresh_whitelist() -> None:
        """强制刷新白名单缓存（上市新股后可手动触发）。"""
        _cache.refresh()


__all__ = ['StockCodeExtractor']
