"""
宏观经济指标 Mixin（AkShare）

Phase 3：宏观经济日历 —— 为"宏观风险专家"提供量化指标底座

数据源（AkShare 免费接口，全部无参数，每次返回完整历史序列）：
  - CPI（月度）        `ak.macro_china_cpi_monthly`
  - PPI（月度）        `ak.macro_china_ppi`
  - PMI（月度，制造业 + 非制造业）`ak.macro_china_pmi`
  - M2（月度同比）      `ak.macro_china_m2_yearly`
  - 社融/新增信贷（月度）`ak.macro_china_new_financial_credit`
  - GDP（季度同比）     `ak.macro_china_gdp_yearly`
  - Shibor 利率（日度）  `ak.macro_china_shibor_all`

统一输出 schema（对应 `macro_indicators` 表）：
  indicator_code / period_date / value / yoy / mom / publish_date / source / raw
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from src.utils.logger import get_logger
from src.utils.response import Response

from ..exceptions import AkShareDataError

logger = get_logger(__name__)


# 项目数据库 schema（bulk_upsert 需要的列顺序与命名）
_OUTPUT_COLUMNS = [
    'indicator_code', 'period_date', 'value', 'yoy', 'mom', 'publish_date', 'source', 'raw',
]


def _empty_macro_df() -> pd.DataFrame:
    return pd.DataFrame(columns=_OUTPUT_COLUMNS)


def _parse_cn_month(month_cn: str) -> Optional[str]:
    """'2026年03月份' → '2026-03-01'；解析失败返回 None。"""
    if not isinstance(month_cn, str):
        return None
    s = month_cn.strip()
    try:
        year_end = s.index('年')
        mon_end = s.index('月')
        year = int(s[:year_end])
        month = int(s[year_end + 1:mon_end])
        return f"{year:04d}-{month:02d}-01"
    except (ValueError, IndexError):
        return None


def _to_float_or_none(v: Any) -> Optional[float]:
    """把数值串/NaN 标准化为 float 或 None。"""
    try:
        if v is None:
            return None
        if pd.isna(v):
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _make_raw(row: pd.Series) -> Dict[str, Any]:
    """行 → dict，供 JSONB `raw` 字段兜底保留原始字段（AkShare 中文列名直通）。"""
    out: Dict[str, Any] = {}
    for col, val in row.items():
        key = str(col)
        if pd.isna(val):
            out[key] = None
        elif hasattr(val, 'isoformat'):
            out[key] = val.isoformat()
        elif isinstance(val, (int, float, str, bool)):
            out[key] = val
        else:
            out[key] = str(val)
    return out


def _build_single_code_df(
    df: pd.DataFrame,
    indicator_code: str,
    *,
    period_col: Optional[str] = None,
    period_from_publish_prev_month: Optional[str] = None,
    period_to_quarter_end: bool = False,
    value_col: str,
    yoy_col: Optional[str] = None,
    mom_col: Optional[str] = None,
    publish_col: Optional[str] = None,
) -> pd.DataFrame:
    """通用骨架：构造单 indicator_code 的标准 DataFrame。

    Args:
        period_col: 直接作为 period_date 的中文月份列（如 '月份'）——走 `_parse_cn_month`。
        period_from_publish_prev_month: 从 publish_date 列推导 period_date（取上月月初），
            用于 AkShare "公布日" 型接口（CPI/M2/GDP）。传入的是公布日列名（如 '日期'）。
        period_to_quarter_end: 仅 GDP——将 period_date 进一步对齐到上一季度末。
        value_col / yoy_col / mom_col / publish_col: AkShare 原始列名。
            value_col 必填；若 yoy_col 为 None 则 yoy = value（value 本身就是同比）。
    """
    if df is None or df.empty:
        return _empty_macro_df()

    out = pd.DataFrame()
    out['indicator_code'] = [indicator_code] * len(df)

    if period_from_publish_prev_month is not None:
        publish = pd.to_datetime(df.get(period_from_publish_prev_month), errors='coerce')
        out['publish_date'] = publish.dt.strftime('%Y-%m-%d')
        prev = publish - pd.offsets.MonthBegin(1)
        if period_to_quarter_end:
            # GDP：公布日 → 上月月初 → 对齐到所在季度末（如 4 月公布代表 Q1，即 3 月末）
            prev = prev + pd.offsets.QuarterEnd(0)
        out['period_date'] = prev.dt.strftime('%Y-%m-%d')
    elif period_col is not None:
        out['period_date'] = df.get(period_col, pd.Series(dtype=str)).map(_parse_cn_month)
        out['publish_date'] = (
            pd.to_datetime(df.get(publish_col), errors='coerce').dt.strftime('%Y-%m-%d')
            if publish_col else [None] * len(df)
        )
    else:
        raise ValueError("必须提供 period_col 或 period_from_publish_prev_month 之一")

    out['value'] = df.get(value_col).map(_to_float_or_none) if value_col in df.columns else [None] * len(df)
    if yoy_col is None:
        out['yoy'] = out['value']
    else:
        out['yoy'] = df.get(yoy_col).map(_to_float_or_none) if yoy_col in df.columns else [None] * len(df)
    out['mom'] = df.get(mom_col).map(_to_float_or_none) if (mom_col and mom_col in df.columns) else [None] * len(df)
    out['source'] = 'akshare'
    out['raw'] = [_make_raw(r) for _, r in df.iterrows()]

    out = out.dropna(subset=['period_date'])
    out = out.drop_duplicates(subset=['indicator_code', 'period_date'], keep='last')
    return out.reset_index(drop=True)


# ------------------------------------------------------------------
# 各指标的标准化器（AkShare raw DataFrame → 项目 schema）
# ------------------------------------------------------------------


def _normalize_cpi_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """`macro_china_cpi_monthly`：商品 / 日期 / 今值 / 预测值 / 前值。
    今值 = 当月 CPI 同比(%)；日期 = 预计公布日；period_date = 公布月的上月（CPI 滞后 1 月）。"""
    return _build_single_code_df(
        df, 'cpi_yoy',
        period_from_publish_prev_month='日期',
        value_col='今值',
    )


def _normalize_ppi(df: pd.DataFrame) -> pd.DataFrame:
    """`macro_china_ppi`：月份 / 当月 / 当月同比增长 / 累计。
    当月同比增长 = value（存为同比），`value == yoy`。"""
    return _build_single_code_df(
        df, 'ppi_yoy',
        period_col='月份',
        value_col='当月同比增长',
    )


def _normalize_pmi(df: pd.DataFrame) -> pd.DataFrame:
    """`macro_china_pmi`：月份 / 制造业-指数 / 制造业-同比增长 / 非制造业-指数 / 非制造业-同比增长
    产出两行：pmi_manu + pmi_nonmanu（value = 指数，yoy = 同比）
    """
    if df is None or df.empty:
        return _empty_macro_df()

    period = df.get('月份', pd.Series(dtype=str)).map(_parse_cn_month)
    raw_list = [_make_raw(r) for _, r in df.iterrows()]

    records: List[Dict[str, Any]] = []
    for idx in range(len(df)):
        pd_str = period.iloc[idx] if idx < len(period) else None
        if not pd_str:
            continue
        manu_value = _to_float_or_none(df['制造业-指数'].iloc[idx]) if '制造业-指数' in df.columns else None
        manu_yoy = _to_float_or_none(df['制造业-同比增长'].iloc[idx]) if '制造业-同比增长' in df.columns else None
        nonmanu_value = _to_float_or_none(df['非制造业-指数'].iloc[idx]) if '非制造业-指数' in df.columns else None
        nonmanu_yoy = _to_float_or_none(df['非制造业-同比增长'].iloc[idx]) if '非制造业-同比增长' in df.columns else None

        records.append({
            'indicator_code': 'pmi_manu',
            'period_date': pd_str,
            'value': manu_value,
            'yoy': manu_yoy,
            'mom': None,
            'publish_date': None,
            'source': 'akshare',
            'raw': raw_list[idx],
        })
        records.append({
            'indicator_code': 'pmi_nonmanu',
            'period_date': pd_str,
            'value': nonmanu_value,
            'yoy': nonmanu_yoy,
            'mom': None,
            'publish_date': None,
            'source': 'akshare',
            'raw': raw_list[idx],
        })

    out = pd.DataFrame(records, columns=_OUTPUT_COLUMNS)
    if out.empty:
        return _empty_macro_df()
    out = out.drop_duplicates(subset=['indicator_code', 'period_date'], keep='last')
    return out.reset_index(drop=True)


def _normalize_m2_yearly(df: pd.DataFrame) -> pd.DataFrame:
    """`macro_china_m2_yearly`：商品 / 日期 / 今值 / 预测值 / 前值。
    今值 = M2 同比(%)；period_date = 公布月的上月。"""
    return _build_single_code_df(
        df, 'm2_yoy',
        period_from_publish_prev_month='日期',
        value_col='今值',
    )


def _normalize_new_financial_credit(df: pd.DataFrame) -> pd.DataFrame:
    """`macro_china_new_financial_credit`：月份 / 当月 / 当月-同比增长 / 当月-环比增长 / 累计 / 累计-同比增长。
    当月（单位：亿元）→ value；同时带同比/环比。"""
    return _build_single_code_df(
        df, 'new_credit_month',
        period_col='月份',
        value_col='当月',
        yoy_col='当月-同比增长',
        mom_col='当月-环比增长',
    )


def _normalize_gdp_yearly(df: pd.DataFrame) -> pd.DataFrame:
    """`macro_china_gdp_yearly`：商品 / 日期 / 今值 / 预测值 / 前值。
    今值 = GDP 年率(%)；period_date 对齐到公布所在季度的上一季度末（如 4 月公布 → 3/31）。"""
    return _build_single_code_df(
        df, 'gdp_yoy',
        period_from_publish_prev_month='日期',
        period_to_quarter_end=True,
        value_col='今值',
    )


def _normalize_shibor(df: pd.DataFrame) -> pd.DataFrame:
    """`macro_china_shibor_all`：日期 + 各期限"定价/涨跌幅"。

    为控制写入量，只保留 **O/N**（隔夜）+ **1W**（一周）+ **1M** 三个常用期限，
    value = 当日报价（%）。Shibor 无同比/环比概念。
    """
    if df is None or df.empty:
        return _empty_macro_df()

    # 仅挑 O/N / 1W / 1M 定价列
    tenor_cols = {
        'shibor_on': 'O/N-定价',
        'shibor_1w': '1W-定价',
        'shibor_1m': '1M-定价',
    }
    date_series = pd.to_datetime(df.get('日期'), errors='coerce').dt.strftime('%Y-%m-%d')
    raw_list = [_make_raw(r) for _, r in df.iterrows()]

    records: List[Dict[str, Any]] = []
    for idx in range(len(df)):
        pd_str = date_series.iloc[idx] if idx < len(date_series) else None
        if not pd_str:
            continue
        for code, col in tenor_cols.items():
            if col not in df.columns:
                continue
            v = _to_float_or_none(df[col].iloc[idx])
            if v is None:
                continue
            records.append({
                'indicator_code': code,
                'period_date': pd_str,
                'value': v,
                'yoy': None,
                'mom': None,
                'publish_date': pd_str,
                'source': 'akshare',
                'raw': raw_list[idx],
            })

    out = pd.DataFrame(records, columns=_OUTPUT_COLUMNS)
    if out.empty:
        return _empty_macro_df()
    out = out.drop_duplicates(subset=['indicator_code', 'period_date'], keep='last')
    return out.reset_index(drop=True)


# 统一注册表：供 Service 层遍历拉取
INDICATOR_FETCHERS: Dict[str, Dict[str, Any]] = {
    'cpi_yoy': {
        'ak_method': 'macro_china_cpi_monthly',
        'normalizer': _normalize_cpi_monthly,
        'label': 'CPI 月度同比',
        'frequency': 'monthly',
    },
    'ppi_yoy': {
        'ak_method': 'macro_china_ppi',
        'normalizer': _normalize_ppi,
        'label': 'PPI 月度同比',
        'frequency': 'monthly',
    },
    'pmi': {
        'ak_method': 'macro_china_pmi',
        'normalizer': _normalize_pmi,
        'label': 'PMI 制造业 + 非制造业',
        'frequency': 'monthly',
    },
    'm2_yoy': {
        'ak_method': 'macro_china_m2_yearly',
        'normalizer': _normalize_m2_yearly,
        'label': 'M2 货币供应同比',
        'frequency': 'monthly',
    },
    'new_credit_month': {
        'ak_method': 'macro_china_new_financial_credit',
        'normalizer': _normalize_new_financial_credit,
        'label': '新增社融当月值',
        'frequency': 'monthly',
    },
    'gdp_yoy': {
        'ak_method': 'macro_china_gdp_yearly',
        'normalizer': _normalize_gdp_yearly,
        'label': 'GDP 年率（季度同比）',
        'frequency': 'quarterly',
    },
    'shibor': {
        'ak_method': 'macro_china_shibor_all',
        'normalizer': _normalize_shibor,
        'label': 'Shibor 日度报价（O/N, 1W, 1M）',
        'frequency': 'daily',
    },
}


class MacroIndicatorsMixin:
    """宏观经济指标 Provider 方法集（挂载在 AkShareProvider）。"""

    # 对外暴露注册表（Service 层遍历用）
    MACRO_INDICATOR_FETCHERS = INDICATOR_FETCHERS

    def get_macro_indicator(self, indicator_key: str) -> Response:
        """拉取指定指标的完整历史序列。

        Args:
            indicator_key: `INDICATOR_FETCHERS` 的 key，如 `cpi_yoy` / `pmi` / `shibor`
                           注意 `pmi` 会同时产出 `pmi_manu` + `pmi_nonmanu` 两个 indicator_code；
                           `shibor` 会产出 `shibor_on` / `shibor_1w` / `shibor_1m` 三个。

        Returns:
            Response.success.data = 标准化 DataFrame（列：见 `_OUTPUT_COLUMNS`）
        """
        meta = INDICATOR_FETCHERS.get(indicator_key)
        if meta is None:
            return self._error_response(
                f"未知的宏观指标 key: {indicator_key}（可选: {list(INDICATOR_FETCHERS)}）",
                error_code="AKSHARE_UNKNOWN_MACRO_INDICATOR",
                indicator_key=indicator_key,
            )

        func = getattr(self.api_client.ak, meta['ak_method'], None)
        if func is None:
            return self._error_response(
                f"AkShare 方法不存在: ak.{meta['ak_method']}（可能是版本不兼容）",
                error_code="AKSHARE_METHOD_MISSING",
                indicator_key=indicator_key,
            )

        return self._call_and_wrap_macro(
            label=f"{meta['label']} ({indicator_key})",
            func=func,
            call_kwargs={},
            warn_on_empty=f"{meta['label']} 返回空",
            extra_metadata={'indicator_key': indicator_key, 'frequency': meta['frequency']},
            log_prefix=f"拉取宏观指标 {indicator_key} via ak.{meta['ak_method']}",
            normalizer=meta['normalizer'],
        )

    def _call_and_wrap_macro(
        self,
        *,
        label: str,
        func: Callable[..., pd.DataFrame],
        call_kwargs: Dict[str, Any],
        warn_on_empty: str,
        extra_metadata: Dict[str, Any],
        log_prefix: str,
        normalizer: Callable[[pd.DataFrame], pd.DataFrame],
    ) -> Response:
        """宏观接口专用的调用 + 标准化 + 包 Response（与 news_and_anns 的版本类似，
        但 empty_factory 固定为 `_empty_macro_df`，免去调用点重复传参）。
        """
        start_time = time.time()
        logger.info(f"AkShare {log_prefix}")

        try:
            raw_df = self.api_client.execute(func, **call_kwargs)
        except AkShareDataError as e:
            logger.error(f"AkShare {label} 获取失败: {e}")
            return self._error_response(
                str(e), error_code="AKSHARE_DATA_ERROR", **extra_metadata,
            )
        except Exception as e:
            logger.error(f"AkShare {label} 获取失败: {e}")
            return self._error_response(
                f"获取失败: {e}",
                error_code="AKSHARE_UNEXPECTED_ERROR",
                **extra_metadata,
            )

        if raw_df is None or raw_df.empty:
            return Response.warning(
                message=warn_on_empty,
                data=_empty_macro_df(),
                n_records=0,
                provider=self.provider_name,
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
