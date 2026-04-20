"""
公告全文按需抓取。

输入一批 URL → 下载 HTML/PDF → 提取正文纯文本 → 写回 stock_anns.content。
使用场景：CIO Agent 深挖某条公告，或用户点"查看全文"按钮。

原则：
  - 按需触发，不做批量预取（避免触发反爬）
  - 限流：单次最多 `MAX_URLS_PER_CALL=5` 个 URL，间隔 `REQUEST_INTERVAL_SEC=2` 秒
  - 网络 / 解析失败不抛异常，逐条返回
  - PDF 依赖 `pdfplumber`：未安装时降级返回 None（HTML 正常）

已知局限：东方财富公告详情页是 SPA（正文由 JS 渲染），本模块只能抓到页面外壳。
拿到真正正文需切巨潮 PDF 直链或引入 Playwright，留给后续迭代；
当前模块可立即用于静态 HTML 源和 PDF 直链。
"""

from __future__ import annotations

import asyncio
import io
import re
from typing import Dict, List, Optional

import requests
from loguru import logger

from app.repositories.stock_anns_repository import StockAnnsRepository
from app.services.news_anns.retry_decorator import (
    AkShareRateLimitError,
    AkShareRetryDecorator,
    AkShareRetryExhaustedError,
)


# ------------------------------------------------------------------
# 常量
# ------------------------------------------------------------------

MAX_URLS_PER_CALL = 5
REQUEST_INTERVAL_SEC = 2
REQUEST_TIMEOUT_SEC = 15
MAX_CONTENT_BYTES = 8 * 1024 * 1024  # 8 MB 上限，超过认为异常（如整本研报 PDF）

# 东方财富公告页的 UA（避免默认 requests UA 被反爬）
_DEFAULT_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/pdf,application/xhtml+xml;q=0.9,*/*;q=0.8',
}

# 东方财富公告详情页的正文容器（经验值，后续若页面改版需更新）
_EASTMONEY_BODY_SELECTORS = [
    'div.detail-body',
    'div#ContentBody',
    'div.content-box',
    'div.article-content',
]


# ------------------------------------------------------------------
# 下载 + 解析
# ------------------------------------------------------------------

@AkShareRetryDecorator(max_retries=2, base_delay=1.5, max_delay=5.0)
def _http_get(url: str) -> requests.Response:
    """下载单个 URL（带指数退避 + 限流识别）。"""
    resp = requests.get(url, headers=_DEFAULT_HEADERS, timeout=REQUEST_TIMEOUT_SEC, stream=True)
    # content-length 检查：超限文件直接拒绝读，避免 OOM
    content_length = resp.headers.get('content-length')
    if content_length and int(content_length) > MAX_CONTENT_BYTES:
        resp.close()
        raise ValueError(f"content-length {content_length} 超上限 {MAX_CONTENT_BYTES}")
    resp.raise_for_status()
    return resp


def _extract_html_text(html_bytes: bytes, encoding: Optional[str] = None) -> Optional[str]:
    """从 HTML 提取正文纯文本。"""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        logger.warning("[anns_fetcher] 未安装 beautifulsoup4，跳过 HTML 正文提取")
        return None

    try:
        text = html_bytes.decode(encoding or 'utf-8', errors='ignore')
    except Exception:
        text = html_bytes.decode('gbk', errors='ignore')

    soup = BeautifulSoup(text, 'lxml' if _has_lxml() else 'html.parser')
    # 移除干扰节点
    for tag in soup(['script', 'style', 'noscript', 'iframe', 'header', 'footer', 'nav']):
        tag.decompose()

    # 优先匹配东方财富正文容器
    for sel in _EASTMONEY_BODY_SELECTORS:
        node = soup.select_one(sel)
        if node:
            body = node.get_text(separator='\n', strip=True)
            if len(body) > 200:  # 认为是有效正文
                return _collapse_whitespace(body)

    # 降级：抓整个 body
    body_node = soup.body or soup
    body = body_node.get_text(separator='\n', strip=True)
    return _collapse_whitespace(body) if body else None


def _extract_pdf_text(pdf_bytes: bytes) -> Optional[str]:
    """从 PDF 提取正文纯文本（依赖 pdfplumber）。"""
    try:
        import pdfplumber
    except ImportError:
        logger.info("[anns_fetcher] 未安装 pdfplumber，PDF 正文抓取降级返回 None")
        return None

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages = []
            for page in pdf.pages:
                txt = page.extract_text() or ''
                if txt.strip():
                    pages.append(txt)
            if not pages:
                return None
            return _collapse_whitespace('\n'.join(pages))
    except Exception as e:
        logger.warning(f"[anns_fetcher] PDF 解析失败: {e}")
        return None


def _collapse_whitespace(text: str) -> str:
    """合并空白字符：多个空行 → 一个，行内多空格 → 一个。"""
    # 行内连续空格
    text = re.sub(r'[ \t\u3000]+', ' ', text)
    # 多空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _has_lxml() -> bool:
    try:
        import lxml  # noqa: F401
        return True
    except ImportError:
        return False


def _fetch_one(url: str) -> Optional[str]:
    """下载并提取单个 URL 的正文；失败时返回 None（不抛异常）。"""
    if not url or not url.startswith(('http://', 'https://')):
        logger.warning(f"[anns_fetcher] 非法 URL: {url}")
        return None

    try:
        resp = _http_get(url)
    except (AkShareRateLimitError, AkShareRetryExhaustedError) as e:
        logger.warning(f"[anns_fetcher] 下载失败 {url}: {e}")
        return None
    except Exception as e:
        logger.warning(f"[anns_fetcher] 下载异常 {url}: {e}")
        return None

    try:
        raw = resp.content
        if len(raw) > MAX_CONTENT_BYTES:
            logger.warning(f"[anns_fetcher] 正文超上限 {len(raw)} > {MAX_CONTENT_BYTES}，跳过 {url}")
            return None
    finally:
        resp.close()

    ctype = (resp.headers.get('content-type') or '').lower()
    if 'pdf' in ctype or url.lower().endswith('.pdf'):
        return _extract_pdf_text(raw)
    return _extract_html_text(raw, resp.encoding)


# ------------------------------------------------------------------
# 主入口（Service 层 API）
# ------------------------------------------------------------------

class AnnsContentFetcher:
    """公告全文按需抓取器。"""

    def __init__(self) -> None:
        self.anns_repo = StockAnnsRepository()

    async def fetch_batch(
        self,
        entries: List[Dict[str, str]],
        write_back: bool = True,
    ) -> List[Dict[str, Optional[str]]]:
        """批量抓取正文（串行 + 限流）。

        Args:
            entries: 每项含 `ts_code / ann_date / title / url`
            write_back: 是否把抓取到的正文写回 stock_anns.content（默认 True）

        Returns:
            每个条目的抓取结果：`{ts_code, ann_date, title, url, content, ok}`
            `content` 为 None 时 `ok=False`（下载失败 / PDF 无 pdfplumber / 正文为空）
        """
        if not entries:
            return []
        batch = entries[:MAX_URLS_PER_CALL]
        if len(entries) > MAX_URLS_PER_CALL:
            logger.warning(
                f"[anns_fetcher] 单次请求最多 {MAX_URLS_PER_CALL} 个 URL，忽略多余 {len(entries) - MAX_URLS_PER_CALL} 个"
            )

        results: List[Dict[str, Optional[str]]] = []
        for i, entry in enumerate(batch):
            if i > 0:
                await asyncio.sleep(REQUEST_INTERVAL_SEC)  # 串行间隔
            url = entry.get('url') or ''
            content = await asyncio.to_thread(_fetch_one, url)
            results.append({
                'ts_code': entry.get('ts_code'),
                'ann_date': entry.get('ann_date'),
                'title': entry.get('title'),
                'url': url,
                'content': content,
                'ok': bool(content),
            })

            if write_back and content and entry.get('ts_code') and entry.get('ann_date') and entry.get('title'):
                try:
                    await asyncio.to_thread(
                        self.anns_repo.update_content,
                        entry['ts_code'], entry['ann_date'], entry['title'], content,
                    )
                except Exception as e:
                    logger.warning(f"[anns_fetcher] 写回 content 失败 {entry.get('ts_code')}/{entry.get('ann_date')}: {e}")

        ok_count = sum(1 for r in results if r['ok'])
        logger.info(f"[anns_fetcher] 抓取完成 {ok_count}/{len(results)} 成功")
        return results

    async def fetch_missing(self, limit: int = 5) -> List[Dict[str, Optional[str]]]:
        """抓取 N 条尚未抓取正文的公告（按 ann_date 降序）。"""
        limit = max(1, min(int(limit), MAX_URLS_PER_CALL))
        entries = await asyncio.to_thread(self.anns_repo.get_missing_content_urls, limit)
        if not entries:
            logger.debug("[anns_fetcher] 没有待抓取的公告")
            return []
        return await self.fetch_batch(entries, write_back=True)

    async def fetch_for_stock(self, ts_code: str, days: int = 30, limit: int = 5) -> List[Dict[str, Optional[str]]]:
        """针对某只股票：抓取近 N 天内尚未有正文的公告。"""
        limit = max(1, min(int(limit), MAX_URLS_PER_CALL))
        all_recent = await asyncio.to_thread(
            self.anns_repo.query_by_stock, ts_code, int(days), 200
        )
        missing = [
            {'ts_code': r['ts_code'], 'ann_date': r['ann_date'], 'title': r['title'], 'url': r['url']}
            for r in all_recent if not r.get('has_content') and r.get('url')
        ][:limit]
        if not missing:
            return []
        return await self.fetch_batch(missing, write_back=True)
