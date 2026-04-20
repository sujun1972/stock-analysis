"""
新闻资讯 & 公司公告 Mixin（AkShare）

Phase 1：公司公告 — 全市场日级 + 个股日期范围两入口
Phase 2：财经快讯（财新要闻精选）+ 个股新闻（东财搜索）+ 新闻联播（cctv xwlb）
Phase 3 占位：宏观经济指标（后续迭代实现）

数据源：完全基于 AkShare 免费接口，替代 Tushare 付费的 `anns_d` / `news` / `cctv_news` 等。
- 公司公告：`ts_code / ann_date / title / url / anno_type / stock_name / source`
- 财经快讯：`publish_time / source / title / summary / url / tags`
- 个股新闻：东财搜索接口，`ts_code / publish_time / title / summary / url / source`
- 新闻联播：`news_date / seq_no / title / content`
"""

from __future__ import annotations

import re
import time
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from src.utils.logger import get_logger
from src.utils.response import Response

from ..exceptions import AkShareDataError

logger = get_logger(__name__)


# AkShare 返回的东方财富列名
_EASTMONEY_COLS = {
    'code': '代码',
    'name': '名称',
    'title': '公告标题',
    'type': '公告类型',
    'date': '公告日期',
    'url': '网址',
}

# 项目数据库 schema（bulk_upsert 需要的列顺序与命名）
_OUTPUT_COLUMNS = [
    'ts_code', 'stock_name', 'title', 'anno_type', 'ann_date', 'url', 'source',
]

# 财经快讯输出 schema（对应 news_flash 表）
# caixin 与 eastmoney 来源共用同一张表，通过 source / related_ts_codes 区分
_NEWS_FLASH_COLUMNS = [
    'publish_time', 'source', 'title', 'summary', 'url', 'tags', 'related_ts_codes',
]

# 新闻联播输出 schema（对应 cctv_news 表）
_CCTV_NEWS_COLUMNS = [
    'news_date', 'seq_no', 'title', 'content',
]


def _to_ts_code(pure_code: str) -> str:
    """纯 6 位代码 → ts_code（复用 TushareDataConverter.to_ts_code 保证前缀映射一致）。"""
    # 局部 import：避免模块加载期触发 Tushare token 校验
    from ...tushare.data_converter import TushareDataConverter
    return TushareDataConverter.to_ts_code(str(pure_code).strip())


def _empty_anns_df() -> pd.DataFrame:
    """标准空 DataFrame（列顺序与 schema 一致）。"""
    return pd.DataFrame(columns=_OUTPUT_COLUMNS)


def _normalize_anns_df(df: pd.DataFrame) -> pd.DataFrame:
    """将 AkShare 东方财富公告 DataFrame 标准化到项目 schema。"""
    if df is None or df.empty:
        return _empty_anns_df()

    out = pd.DataFrame()
    out['ts_code'] = df[_EASTMONEY_COLS['code']].astype(str).map(_to_ts_code)
    out['stock_name'] = df[_EASTMONEY_COLS['name']].astype(str)
    out['title'] = df[_EASTMONEY_COLS['title']].astype(str)
    out['anno_type'] = df[_EASTMONEY_COLS['type']].astype(str)
    # 日期可能是 datetime/date/str，统一成 YYYY-MM-DD 字符串
    out['ann_date'] = pd.to_datetime(df[_EASTMONEY_COLS['date']], errors='coerce').dt.strftime('%Y-%m-%d')
    out['url'] = df[_EASTMONEY_COLS['url']].astype(str)
    out['source'] = 'eastmoney'

    # 丢弃关键字段缺失的行
    out = out.dropna(subset=['ts_code', 'ann_date', 'title'])
    out = out[out['title'].str.len() > 0]
    out = out[out['ts_code'].str.contains(r'\.[A-Z]{2}$')]
    # AkShare 会把同一公告拆成多条"分类别名"（如年度报告 + 年度报告摘要），
    # 按主键三元组去重
    out = out.drop_duplicates(subset=['ts_code', 'ann_date', 'title'], keep='first')
    return out.reset_index(drop=True)


# ------------------------------------------------------------------
# 财经快讯 / 个股新闻 / 新闻联播标准化
# ------------------------------------------------------------------

# 纯 6 位 A 股代码的正则；交由 Service 层再基于 stock_basic 白名单校验
_TS_CODE_RE = re.compile(r'(?<!\d)(?:000|001|002|003|300|301|600|601|603|605|688|689|830|831|832|833|835|836|837|838|839|870|871|872|873)\d{3}(?!\d)')


def _empty_news_flash_df() -> pd.DataFrame:
    return pd.DataFrame(columns=_NEWS_FLASH_COLUMNS)


def _empty_cctv_df() -> pd.DataFrame:
    return pd.DataFrame(columns=_CCTV_NEWS_COLUMNS)


def _normalize_caixin_flash_df(df: pd.DataFrame) -> pd.DataFrame:
    """财新要闻精选（`ak.stock_news_main_cx`）→ 项目 schema。

    AkShare 原始列：`tag / summary / url`（无独立 title / publish_time）。
    - title 由 summary 首段截取（≤ 60 字）；
    - publish_time 取当前抓取时刻（接口本身不带时间）；
    - tags 存入 [tag]；related_ts_codes 由 summary 正则提取后由 Service 层过滤。
    """
    if df is None or df.empty:
        return _empty_news_flash_df()

    now = pd.Timestamp.now().floor('s')
    out = pd.DataFrame()
    out['publish_time'] = [now] * len(df)
    out['source'] = 'caixin'
    summary = df.get('summary', pd.Series(['' for _ in range(len(df))])).astype(str)
    out['summary'] = summary
    out['title'] = summary.str.slice(0, 60)
    out['url'] = df.get('url', pd.Series(['' for _ in range(len(df))])).astype(str)
    tag_col = df.get('tag', pd.Series(['' for _ in range(len(df))])).astype(str)
    out['tags'] = [[t] if t else [] for t in tag_col]
    out['related_ts_codes'] = [sorted(set(_TS_CODE_RE.findall(s))) for s in summary]

    out = out.dropna(subset=['title'])
    out = out[out['title'].str.len() > 0]
    out = out.drop_duplicates(subset=['source', 'title'], keep='first')
    return out.reset_index(drop=True)


def _normalize_em_stock_news_df(df: pd.DataFrame, ts_code: str) -> pd.DataFrame:
    """东方财富-个股搜索新闻（`ak.stock_news_em`）→ 项目 schema。

    AkShare 原始列：`关键词 / 新闻标题 / 新闻内容 / 发布时间 / 文章来源 / 新闻链接`。
    每条新闻标记 `related_ts_codes=[ts_code]`，以便 Service 写入 GIN 数组索引。
    """
    if df is None or df.empty:
        return _empty_news_flash_df()

    out = pd.DataFrame()
    out['publish_time'] = pd.to_datetime(df['发布时间'], errors='coerce')
    out['source'] = 'eastmoney'
    out['title'] = df['新闻标题'].astype(str)
    out['summary'] = df.get('新闻内容', pd.Series(['' for _ in range(len(df))])).astype(str)
    out['url'] = df.get('新闻链接', pd.Series(['' for _ in range(len(df))])).astype(str)
    media = df.get('文章来源', pd.Series(['' for _ in range(len(df))])).astype(str)
    out['tags'] = [[m] if m else [] for m in media]
    # 统一成 'XXXXXX.SZ' / .SH / .BJ 格式：不论传入是纯数字还是带后缀，都先剥到 6 位再走映射
    ts_code_norm = _to_ts_code(str(ts_code).split('.')[0])
    out['related_ts_codes'] = [[ts_code_norm] for _ in range(len(out))]

    out = out.dropna(subset=['publish_time', 'title'])
    out = out[out['title'].str.len() > 0]
    out = out.drop_duplicates(subset=['source', 'title', 'publish_time'], keep='first')
    return out.reset_index(drop=True)


def _normalize_cctv_news_df(df: pd.DataFrame, news_date: str) -> pd.DataFrame:
    """新闻联播（`ak.news_cctv`）→ 项目 schema。

    AkShare 原始列：`date / title / content`；seq_no 由行序赋 1..N。
    """
    if df is None or df.empty:
        return _empty_cctv_df()

    out = pd.DataFrame()
    # 日期字符串统一为 YYYY-MM-DD
    raw_date = df.get('date', pd.Series([news_date for _ in range(len(df))])).astype(str)
    out['news_date'] = pd.to_datetime(raw_date, errors='coerce').dt.strftime('%Y-%m-%d')
    out['seq_no'] = list(range(1, len(df) + 1))
    out['title'] = df.get('title', pd.Series(['' for _ in range(len(df))])).astype(str)
    out['content'] = df.get('content', pd.Series(['' for _ in range(len(df))])).astype(str)

    out = out.dropna(subset=['news_date', 'title'])
    out = out[out['title'].str.len() > 0]
    return out.reset_index(drop=True)


def _is_empty_result_error(exc: BaseException) -> bool:
    """AkShare 在接口返回 0 行时会在内部以 KeyError('代码') 抛出（pandas 空 DF 索引失败）。

    这不是"数据错误"，而是"区间内无数据"的正常语义，本函数识别后让调用方降级为
    `Response.warning(空 DataFrame)`。
    """
    return isinstance(exc, KeyError) and '代码' in str(exc)


class NewsAndAnnsMixin:
    """新闻资讯 & 公司公告 Provider 方法集（挂载在 AkShareProvider）。"""

    # ------------------------------------------------------------------
    # Phase 1: 公司公告
    # ------------------------------------------------------------------

    def get_market_anns(self, date: str) -> Response:
        """全市场某交易日所有公告（ak.stock_notice_report）。

        单日接口耗时 60~120s（AkShare 内部分 ~50 批爬取东方财富），返回 ~4000-5000 条。
        非交易日或未来日期通常返回空。

        Args:
            date: YYYYMMDD 或 YYYY-MM-DD

        Returns:
            Response.success.data = 标准化 DataFrame（列：见 `_OUTPUT_COLUMNS`）
            空结果（含未交易日）→ Response.warning(data=空 DataFrame)
        """
        date_clean = self._normalize_yyyymmdd(date)
        if not date_clean:
            return self._error_response(
                f"日期格式错误，期望 YYYYMMDD 或 YYYY-MM-DD，收到: {date}",
                error_code="AKSHARE_INVALID_DATE",
                ann_date=date,
            )

        return self._call_and_wrap(
            label=f"全市场公告 date={date_clean}",
            func=self.api_client.ak.stock_notice_report,
            call_kwargs={'symbol': '全部', 'date': date_clean},
            warn_on_empty=f"{date_clean} 无公告数据",
            extra_metadata={'ann_date': date_clean},
            log_prefix=f"拉取全市场公告 date={date_clean}（预计 60~120s）",
        )

    def get_stock_anns(
        self,
        ts_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Response:
        """单只股票指定日期范围的公告（ak.stock_individual_notice_report）。

        比全市场接口快很多（单次 1~3s），用于被动同步和 CIO Agent 按需查询。

        Args:
            ts_code: 股票代码（支持 '000001' 或 '000001.SZ'）
            start_date / end_date: YYYYMMDD 或 YYYY-MM-DD；均不传时接口返回最近若干条

        Returns:
            Response.success.data = 标准化 DataFrame（列：见 `_OUTPUT_COLUMNS`）
        """
        pure_code = str(ts_code).split('.')[0].strip()
        if not pure_code.isdigit() or len(pure_code) != 6:
            return self._error_response(
                f"股票代码格式错误，期望 6 位数字或 '000001.SZ'：{ts_code}",
                error_code="AKSHARE_INVALID_TS_CODE",
                ts_code=ts_code,
            )

        sd = self._normalize_yyyymmdd(start_date) if start_date else None
        ed = self._normalize_yyyymmdd(end_date) if end_date else None

        return self._call_and_wrap(
            label=f"个股公告 ts_code={pure_code}",
            func=self.api_client.ak.stock_individual_notice_report,
            call_kwargs={
                'security': pure_code, 'symbol': '全部',
                'begin_date': sd, 'end_date': ed,
            },
            warn_on_empty=f"{pure_code} 在该日期范围内无公告",
            extra_metadata={'ts_code': ts_code},
            log_prefix=f"拉取个股公告 ts_code={pure_code} range=[{sd},{ed}]",
        )

    # ------------------------------------------------------------------
    # Phase 2: 财经快讯 + 个股新闻 + 新闻联播
    # ------------------------------------------------------------------

    def get_news_flash(self, source: str = 'caixin') -> Response:
        """财经快讯（当前仅支持 `caixin`：财新网-要闻精选，返回最近 100 条）。

        AkShare `stock_telegraph_cls` 在 1.18+ 已不可用；本方法选择 `stock_news_main_cx`
        作为稳定的宏观财经快讯来源。接口无 date 参数，每次返回最近 ~100 条。

        Args:
            source: 预留参数；当前仅 'caixin' 有效。传入其他值返回 error。

        Returns:
            Response.success.data = 标准化 DataFrame（列：见 `_NEWS_FLASH_COLUMNS`）
        """
        src = (source or '').lower().strip()
        if src != 'caixin':
            return self._error_response(
                f"暂不支持的快讯来源: {source}（当前仅 'caixin'）",
                error_code="AKSHARE_UNSUPPORTED_SOURCE",
                source=source,
            )

        return self._call_and_wrap(
            label=f"财新快讯 source={src}",
            func=self.api_client.ak.stock_news_main_cx,
            call_kwargs={},
            warn_on_empty="财新快讯接口返回空",
            extra_metadata={'source': src},
            log_prefix=f"拉取财新要闻精选（最近 100 条）",
            normalizer=_normalize_caixin_flash_df,
            empty_factory=_empty_news_flash_df,
        )

    def get_stock_news(self, ts_code: str) -> Response:
        """东方财富-个股新闻（最近 ~10 条，`ak.stock_news_em`）。

        Args:
            ts_code: 股票代码（支持 '000001' 或 '000001.SZ'）

        Returns:
            Response.success.data = 标准化 DataFrame（列：见 `_NEWS_FLASH_COLUMNS`；
            `related_ts_codes=[ts_code]`，便于写入 GIN 数组索引与个股反查）

        注意：AkShare 1.18 此接口内部用 `\u3000` 正则清洗，
        pandas+pyarrow string backend 下会抛 `ArrowInvalid: Invalid regular expression`。
        本方法通过 `pd.option_context` 临时切换到 python backend 绕开该 bug。
        """
        pure_code = str(ts_code).split('.')[0].strip()
        if not pure_code.isdigit() or len(pure_code) != 6:
            return self._error_response(
                f"股票代码格式错误，期望 6 位数字或 '000001.SZ'：{ts_code}",
                error_code="AKSHARE_INVALID_TS_CODE",
                ts_code=ts_code,
            )

        def _ctx():
            return pd.option_context('future.infer_string', False, 'mode.string_storage', 'python')

        return self._call_and_wrap(
            label=f"东财个股新闻 ts_code={pure_code}",
            func=self.api_client.ak.stock_news_em,
            call_kwargs={'symbol': pure_code},
            warn_on_empty=f"{pure_code} 无个股新闻",
            extra_metadata={'ts_code': ts_code},
            log_prefix=f"拉取东财个股新闻 ts_code={pure_code}",
            normalizer=lambda df: _normalize_em_stock_news_df(df, ts_code),
            empty_factory=_empty_news_flash_df,
            call_context=_ctx,
        )

    def get_cctv_news(self, date: str) -> Response:
        """新闻联播文字稿（`ak.news_cctv`，支持 2016-02 起的日期）。

        Args:
            date: YYYYMMDD 或 YYYY-MM-DD；非联播日（放假日）返回空。

        Returns:
            Response.success.data = 标准化 DataFrame（列：见 `_CCTV_NEWS_COLUMNS`）
        """
        date_clean = self._normalize_yyyymmdd(date)
        if not date_clean:
            return self._error_response(
                f"日期格式错误，期望 YYYYMMDD 或 YYYY-MM-DD，收到: {date}",
                error_code="AKSHARE_INVALID_DATE",
                news_date=date,
            )

        return self._call_and_wrap(
            label=f"新闻联播 date={date_clean}",
            func=self.api_client.ak.news_cctv,
            call_kwargs={'date': date_clean},
            warn_on_empty=f"{date_clean} 无新闻联播（可能为放假/停播日）",
            extra_metadata={'news_date': date_clean},
            log_prefix=f"拉取新闻联播 date={date_clean}",
            normalizer=lambda df: _normalize_cctv_news_df(df, date_clean),
            empty_factory=_empty_cctv_df,
        )

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_yyyymmdd(date_str: Optional[str]) -> Optional[str]:
        """YYYY-MM-DD / YYYYMMDD → YYYYMMDD；非法格式返回 None。"""
        if not date_str:
            return None
        s = str(date_str).replace('-', '').strip()
        return s if len(s) == 8 and s.isdigit() else None

    def _error_response(self, message: str, error_code: str, **metadata: Any) -> Response:
        return Response.error(
            error=message,
            error_code=error_code,
            provider=self.provider_name,
            **metadata,
        )

    def _call_and_wrap(
        self,
        *,
        label: str,
        func: Callable[..., pd.DataFrame],
        call_kwargs: Dict[str, Any],
        warn_on_empty: str,
        extra_metadata: Dict[str, Any],
        log_prefix: str,
        normalizer: Optional[Callable[[pd.DataFrame], pd.DataFrame]] = None,
        empty_factory: Optional[Callable[[], pd.DataFrame]] = None,
        call_context: Optional[Callable[[], Any]] = None,
    ) -> Response:
        """把"调 AkShare + 空结果降级 + 标准化 + 包成 Response" 统一处理。

        AkShare 空结果时会抛 KeyError，被 `_is_empty_result_error` 识别并降级为
        `Response.warning(data=空 DataFrame)`；其余异常落到 error 分支。

        Args:
            normalizer:     把 AkShare 返回的 raw DataFrame 转换为项目 schema；默认 `_normalize_anns_df`
            empty_factory:  空结果时使用的 DataFrame 工厂；默认 `_empty_anns_df`
            call_context:   可选的 contextmanager 工厂，包裹 AkShare 调用（如 pandas option_context）
        """
        normalizer = normalizer or _normalize_anns_df
        empty_factory = empty_factory or _empty_anns_df

        start_time = time.time()
        logger.info(f"AkShare {log_prefix}")

        def _invoke() -> pd.DataFrame:
            return self.api_client.execute(func, **call_kwargs)

        try:
            if call_context is not None:
                with call_context():
                    raw_df = _invoke()
            else:
                raw_df = _invoke()
        except AkShareDataError as e:
            # Provider 层重试耗尽 —— 若底层原因是空结果，仍要降级为 warning
            if _is_empty_result_error(e.__cause__ or e):
                return self._empty_warning(warn_on_empty, empty_factory=empty_factory, **extra_metadata)
            logger.error(f"AkShare {label} 获取失败: {e}")
            return self._error_response(
                str(e), error_code="AKSHARE_DATA_ERROR", **extra_metadata,
            )
        except Exception as e:
            if _is_empty_result_error(e):
                logger.warning(f"AkShare {label} 区间内无数据")
                return self._empty_warning(warn_on_empty, empty_factory=empty_factory, **extra_metadata)
            logger.error(f"AkShare {label} 获取失败: {e}")
            return self._error_response(
                f"获取失败: {e}",
                error_code="AKSHARE_UNEXPECTED_ERROR",
                **extra_metadata,
            )

        df = normalizer(raw_df)
        elapsed = time.time() - start_time
        logger.info(f"AkShare {label} 获取 {len(df)} 条，耗时 {elapsed:.1f}s")
        return Response.success(
            data=df,
            message=f"成功获取 {label} {len(df)} 条",
            n_records=len(df),
            provider=self.provider_name,
            elapsed_time=f"{elapsed:.2f}s",
            **extra_metadata,
        )

    def _empty_warning(
        self,
        message: str,
        empty_factory: Optional[Callable[[], pd.DataFrame]] = None,
        **metadata: Any,
    ) -> Response:
        empty_factory = empty_factory or _empty_anns_df
        return Response.warning(
            message=message,
            data=empty_factory(),
            n_records=0,
            provider=self.provider_name,
            **metadata,
        )
