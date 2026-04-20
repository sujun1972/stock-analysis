"""
新闻资讯 & 公司公告 Mixin（AkShare）

Phase 1：公司公告 — 全市场日级 + 个股日期范围两入口
Phase 2/3 占位：财经快讯、新闻联播、宏观经济指标（后续迭代实现）

数据源：完全基于 AkShare 免费接口，替代 Tushare 付费的 `anns_d` / `anns_l` 等。
输出统一为项目数据库 schema：`ts_code / ann_date / title / url / anno_type / stock_name / source`。
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

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
    ) -> Response:
        """把"调 AkShare + 空结果降级 + 标准化 + 包成 Response" 统一处理。

        AkShare 空结果时会抛 KeyError，被 `_is_empty_result_error` 识别并降级为
        `Response.warning(data=空 DataFrame)`；其余异常落到 error 分支。
        """
        start_time = time.time()
        logger.info(f"AkShare {log_prefix}")

        try:
            raw_df = self.api_client.execute(func, **call_kwargs)
        except AkShareDataError as e:
            # Provider 层重试耗尽 —— 若底层原因是空结果，仍要降级为 warning
            if _is_empty_result_error(e.__cause__ or e):
                return self._empty_warning(warn_on_empty, **extra_metadata)
            logger.error(f"AkShare {label} 获取失败: {e}")
            return self._error_response(
                str(e), error_code="AKSHARE_DATA_ERROR", **extra_metadata,
            )
        except Exception as e:
            if _is_empty_result_error(e):
                logger.warning(f"AkShare {label} 区间内无数据")
                return self._empty_warning(warn_on_empty, **extra_metadata)
            logger.error(f"AkShare {label} 获取失败: {e}")
            return self._error_response(
                f"获取失败: {e}",
                error_code="AKSHARE_UNEXPECTED_ERROR",
                **extra_metadata,
            )

        df = _normalize_anns_df(raw_df)
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

    def _empty_warning(self, message: str, **metadata: Any) -> Response:
        return Response.warning(
            message=message,
            data=_empty_anns_df(),
            n_records=0,
            provider=self.provider_name,
            **metadata,
        )
