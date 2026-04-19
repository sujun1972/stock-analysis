"""原始财报三表快照取数器（选股策略专用）

对选股策略暴露 income / balancesheet / cashflow 原始字段，支持构造自定义
价值/质量因子（Piotroski F-Score、Sloan 应计、FCF 收益率等）。

**关键约束：防前视偏差**
所有查询强制 `ann_date <= as_of_date`——以公告日为准，而非报告期末日；
未公告的财报对策略不可见。

**重述处理**
同一 (ts_code, end_date) 可能有多行（原报 + 调整后），通过
`DISTINCT ON (ts_code, end_date) ORDER BY ts_code, end_date DESC, ann_date DESC`
取最新公告版本。

**报表类型**
只取 `report_type='1'`（合并报表），忽略母公司单独报表。
"""

import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List

import numpy as np
import pandas as pd
from loguru import logger

from app.repositories.income_repository import IncomeRepository


_COLUMN_LIST = [
    'ts_code', 'end_date', 'latest_ann_date',
    # income
    'inc_total_revenue', 'inc_revenue', 'inc_oper_cost',
    'inc_sell_exp', 'inc_admin_exp', 'inc_rd_exp',
    'inc_operate_profit', 'inc_n_income', 'inc_ebit', 'inc_basic_eps',
    # balancesheet
    'bs_total_assets', 'bs_total_cur_assets', 'bs_total_cur_liab',
    'bs_accounts_receiv', 'bs_inventories', 'bs_fix_assets',
    'bs_lt_borr', 'bs_st_borr', 'bs_total_share', 'bs_money_cap',
    # cashflow
    'cf_n_cashflow_act', 'cf_free_cashflow', 'cf_c_inf_fr_operate_a',
]


def fetch_fundamentals_snapshot(
    ts_codes: List[str],
    as_of_date: str,
    periods: int = 4,
    staleness_days: int = 365,
) -> pd.DataFrame:
    """为一组股票在指定时间锚点拉取最近 N 期原始财报数据。

    Args:
        ts_codes: 股票代码列表（如 ['600000.SH', '000001.SZ']）。
        as_of_date: 锚点日期 YYYYMMDD。查询只返回 `ann_date <= as_of_date` 的记录。
        periods: 每只股票最多返回的报告期数（按 end_date 倒序）。
        staleness_days: 超出此天数的旧数据直接剔除（默认 1 年）。

    Returns:
        长格式 DataFrame，每行 = 一个 (ts_code, end_date)。
        列：ts_code, end_date, latest_ann_date, inc_*, bs_*, cf_*。
        Index 为 RangeIndex。
        缺失列（如某公司某期未披露现金流量表）为 NaN。

    Performance: 单 SQL + CTE，约 1-2 秒处理 3000 股 × 8 期。
    """
    if not ts_codes:
        return pd.DataFrame(columns=_COLUMN_LIST)

    if not (isinstance(as_of_date, str) and len(as_of_date) == 8 and as_of_date.isdigit()):
        raise ValueError(f"as_of_date 必须为 YYYYMMDD 字符串，实际: {as_of_date!r}")

    stale_cutoff = (
        datetime.strptime(as_of_date, '%Y%m%d') - timedelta(days=staleness_days)
    ).strftime('%Y%m%d')

    sql = """
    WITH inc AS (
        SELECT DISTINCT ON (ts_code, end_date)
            ts_code, end_date, ann_date,
            total_revenue, revenue, oper_cost,
            sell_exp, admin_exp, rd_exp,
            operate_profit, n_income, ebit, basic_eps
        FROM income
        WHERE ts_code = ANY(%(codes)s)
          AND ann_date <= %(as_of)s
          AND ann_date >= %(stale)s
          AND report_type = '1'
        ORDER BY ts_code, end_date DESC, ann_date DESC
    ),
    bs AS (
        SELECT DISTINCT ON (ts_code, end_date)
            ts_code, end_date, ann_date,
            total_assets, total_cur_assets, total_cur_liab,
            accounts_receiv, inventories, fix_assets,
            lt_borr, st_borr, total_share, money_cap
        FROM balancesheet
        WHERE ts_code = ANY(%(codes)s)
          AND ann_date <= %(as_of)s
          AND ann_date >= %(stale)s
          AND report_type = '1'
        ORDER BY ts_code, end_date DESC, ann_date DESC
    ),
    cf AS (
        SELECT DISTINCT ON (ts_code, end_date)
            ts_code, end_date, ann_date,
            n_cashflow_act, free_cashflow, c_inf_fr_operate_a
        FROM cashflow
        WHERE ts_code = ANY(%(codes)s)
          AND ann_date <= %(as_of)s
          AND ann_date >= %(stale)s
          AND report_type = '1'
        ORDER BY ts_code, end_date DESC, ann_date DESC
    ),
    merged AS (
        SELECT
            COALESCE(inc.ts_code, bs.ts_code, cf.ts_code)  AS ts_code,
            COALESCE(inc.end_date, bs.end_date, cf.end_date) AS end_date,
            GREATEST(inc.ann_date, bs.ann_date, cf.ann_date) AS latest_ann_date,
            inc.total_revenue   AS inc_total_revenue,
            inc.revenue         AS inc_revenue,
            inc.oper_cost       AS inc_oper_cost,
            inc.sell_exp        AS inc_sell_exp,
            inc.admin_exp       AS inc_admin_exp,
            inc.rd_exp          AS inc_rd_exp,
            inc.operate_profit  AS inc_operate_profit,
            inc.n_income        AS inc_n_income,
            inc.ebit            AS inc_ebit,
            inc.basic_eps       AS inc_basic_eps,
            bs.total_assets     AS bs_total_assets,
            bs.total_cur_assets AS bs_total_cur_assets,
            bs.total_cur_liab   AS bs_total_cur_liab,
            bs.accounts_receiv  AS bs_accounts_receiv,
            bs.inventories      AS bs_inventories,
            bs.fix_assets       AS bs_fix_assets,
            bs.lt_borr          AS bs_lt_borr,
            bs.st_borr          AS bs_st_borr,
            bs.total_share      AS bs_total_share,
            bs.money_cap        AS bs_money_cap,
            cf.n_cashflow_act      AS cf_n_cashflow_act,
            cf.free_cashflow       AS cf_free_cashflow,
            cf.c_inf_fr_operate_a  AS cf_c_inf_fr_operate_a,
            ROW_NUMBER() OVER (
                PARTITION BY COALESCE(inc.ts_code, bs.ts_code, cf.ts_code)
                ORDER BY COALESCE(inc.end_date, bs.end_date, cf.end_date) DESC
            ) AS rn
        FROM inc
        FULL OUTER JOIN bs USING (ts_code, end_date)
        FULL OUTER JOIN cf USING (ts_code, end_date)
    )
    SELECT
        ts_code, end_date, latest_ann_date,
        inc_total_revenue, inc_revenue, inc_oper_cost,
        inc_sell_exp, inc_admin_exp, inc_rd_exp,
        inc_operate_profit, inc_n_income, inc_ebit, inc_basic_eps,
        bs_total_assets, bs_total_cur_assets, bs_total_cur_liab,
        bs_accounts_receiv, bs_inventories, bs_fix_assets,
        bs_lt_borr, bs_st_borr, bs_total_share, bs_money_cap,
        cf_n_cashflow_act, cf_free_cashflow, cf_c_inf_fr_operate_a
    FROM merged
    WHERE rn <= %(periods)s
    ORDER BY ts_code, end_date DESC
    """

    params = {
        'codes': list(ts_codes),
        'as_of': as_of_date,
        'stale': stale_cutoff,
        'periods': int(periods),
    }

    t0 = time.perf_counter()
    repo = IncomeRepository()
    conn = repo.db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
    finally:
        repo.db.release_connection(conn)

    if not rows:
        logger.info(
            f"fetch_fundamentals_snapshot: 0 rows (ts_codes={len(ts_codes)}, "
            f"as_of={as_of_date}, stale={stale_cutoff})"
        )
        return pd.DataFrame(columns=_COLUMN_LIST)

    records = []
    for row in rows:
        rec = {}
        for col_name, val in zip(_COLUMN_LIST, row):
            if val is None:
                rec[col_name] = np.nan if col_name not in ('ts_code', 'end_date', 'latest_ann_date') else None
            elif isinstance(val, Decimal):
                rec[col_name] = float(val)
            elif isinstance(val, (int, float)):
                rec[col_name] = float(val)
            else:
                rec[col_name] = val
        records.append(rec)

    df = pd.DataFrame.from_records(records, columns=_COLUMN_LIST)
    elapsed = time.perf_counter() - t0
    logger.info(
        f"fetch_fundamentals_snapshot: {len(df)} rows, "
        f"{df['ts_code'].nunique()} unique ts_code, "
        f"{elapsed * 1000:.1f} ms (as_of={as_of_date}, periods={periods})"
    )
    return df
