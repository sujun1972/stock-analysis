"""股票价值度量 Service

三个指标：
  ROC = EBIT / (净营运资本 + 净固定资产)                        《股市稳赚》
  Earnings Yield = EBIT / EV                                   《股市稳赚》
  Intrinsic Value = basic_eps * (8.5 + 2g)                     《聪明的投资者》

EPS 口径：
  反推 TTM EPS = close / pe_ttm（pe_ttm 缺失时兜底 pe）。不直接取 income.basic_eps——
  Greenblatt 原书用 TTM；且 income.basic_eps 对 CDR / A+H / A+B 双重上市股口径失真严重
  （689009 九号公司年报 EPS=24.72 而市场真实 EPS ≈ 2.43，差 10 倍）。pe ≤ 0 的亏损股
  过滤（公式不适用负 EPS）。

g 的推算（双路径，封顶不同）：
  1. 研报路径：report_rc 近 180 天一致预期 EPS 的【序列内部 CAGR】（最远预测/最近预测）
     - 封顶 15%
     - 不以已实现 basic_eps 为基准——否则"年报滞后 + 研报抢跑"会把跳升误判为年化增长
  2. 历史路径：近 3 年年报 basic_eps 的 CAGR
     - 封顶 10%（比研报更严，历史 CAGR 是机械外推无法识别基数效应）
     - 要求每一年 EPS 均为正，杜绝亏损恢复的"触底反弹型" CAGR

筛子：
  - ROC > 150% / EY > 50% 视作数据异常（口径失真 / 极小分母），置 NULL
  - ST / *ST 股不输出内在价值（格雷厄姆公式前提是"持续经营稳定盈利"）

设计原则：
  单只计算纯 CPU + 一次 SQL，天然线程安全；数据现场 JOIN income/balancesheet/daily_basic/
  stock_basic 取最新快照（基于 ann_date <= today 的 MAX end_date），不依赖"哪张表刚刚同步完"，
  解决 5 个同步源到达顺序不定的问题。
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional

from loguru import logger

from app.repositories.stock_basic_repository import StockBasicRepository
from app.repositories.value_metrics_repository import ValueMetricsRepository
from src.database.db_manager import DatabaseManager


# 研报路径 g 封顶 15%：业界通行做法，防止新股/高成长股算出爆炸 IV。
# 参见 Benjamin Graham 原始公式的保守修正（Intelligent Investor 第 11 章）。
G_CAP_ANALYST = 0.15

# 历史路径 g 封顶 10%（比研报路径更严）：历史 CAGR 是机械外推，无法识别基数效应。
# 如 002731 ST 萃华 2022 EPS=0.19 谷底反弹至 2024=0.85，算出 112% CAGR 显然不可持续。
# 研报路径的 CAGR 已隐含分析师对行业/公司质地的判断，可放宽到 15%。
G_CAP_HISTORY = 0.10

# 研报路径：至少 N 家机构一致预期才采信
MIN_ANALYST_COUNT = 3

# 研报路径回看窗口（天）
ANALYST_LOOKBACK_DAYS = 180

# 历史路径 CAGR 回看年数
HISTORY_CAGR_YEARS = 3

# ROC / EY 异常值上限：超过即视作口径失真（如极小分母、单季 EBIT 折算到年化），置 NULL。
# ROC 1.5：三七互娱这种极端轻资产公司真实 ROC ≈ 99%，150% 以上基本都是数据问题。
# EY 0.5：EBIT / EV > 50% 对应 PE 不到 2 倍，几乎不可能真实。
ROC_SANITY_CAP = 1.5
EY_SANITY_CAP = 0.5


def _to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    try:
        f = float(v)
        if f != f:  # NaN
            return None
        return f
    except (TypeError, ValueError):
        return None


def _exec_fetchall(sql: str, params: Dict[str, Any]) -> List[tuple]:
    """执行 SELECT 返回全部行。封装 DatabaseManager 连接借还样板。"""
    db = DatabaseManager()
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        db.release_connection(conn)


def _exec_fetchone(sql: str, params: Dict[str, Any]) -> Optional[tuple]:
    """执行 SELECT 返回首行，无结果时返回 None。"""
    rows = _exec_fetchall(sql, params)
    return rows[0] if rows else None


class ValueMetricsService:
    """股票价值度量计算 Service

    使用方式：
      svc = ValueMetricsService()
      await svc.recompute_one(ts_code)           # 单只重算
      await svc.recompute_batch(ts_codes)        # 批量重算（从 Redis dirty set 捞出来的）
      await svc.recompute_all()                  # 全市场重算（日终兜底 / daily_basic 触发）
    """

    def __init__(self) -> None:
        self.repo = ValueMetricsRepository()
        self.stock_basic_repo = StockBasicRepository()

    # ========================================================================
    # 外部入口（异步）
    # ========================================================================

    async def recompute_one(self, ts_code: str) -> bool:
        """重算单只股票，写入失败/数据不足时返回 False。"""
        if not ts_code:
            return False
        row = await asyncio.to_thread(self._compute_for_one, ts_code)
        if row is None:
            return False
        await asyncio.to_thread(self.repo.upsert_one, row)
        return True

    async def recompute_batch(self, ts_codes: Iterable[str]) -> Dict[str, int]:
        """批量重算。同步执行（计算是纯 CPU + 单次 SQL），单只失败不影响其他。"""
        codes = [c for c in dict.fromkeys(ts_codes) if c]
        return await asyncio.to_thread(self._compute_and_upsert_batch, codes)

    async def recompute_all(self) -> Dict[str, int]:
        """全市场重算。"""
        codes = await asyncio.to_thread(self.stock_basic_repo.get_listed_ts_codes, 'L')
        return await asyncio.to_thread(self._compute_and_upsert_batch, codes)

    # ========================================================================
    # 批量执行（同步，避开 async for 多表 JOIN 的事务开销）
    # ========================================================================

    def _compute_and_upsert_batch(self, ts_codes: List[str]) -> Dict[str, int]:
        ok = 0
        skipped = 0
        failed = 0
        for ts_code in ts_codes:
            try:
                row = self._compute_for_one(ts_code)
                if row is None:
                    skipped += 1
                    continue
                self.repo.upsert_one(row)
                ok += 1
            except Exception as e:
                failed += 1
                logger.warning(f"[value_metrics] 重算失败 {ts_code}: {e}")
        total = len(ts_codes)
        logger.info(
            f"[value_metrics] 批量重算完成: total={total} ok={ok} "
            f"skipped={skipped} failed={failed}"
        )
        return {"total": total, "ok": ok, "skipped": skipped, "failed": failed}

    # ========================================================================
    # 单只计算：一次数据拉取 → 原料组装 → 三公式
    # ========================================================================

    def _compute_for_one(self, ts_code: str) -> Optional[Dict[str, Any]]:
        today = datetime.now().strftime("%Y%m%d")
        raw = self._fetch_raw_snapshot(ts_code, today)
        if raw is None:
            return None

        ebit = raw["ebit"]
        basic_eps = raw["basic_eps"]
        working_capital = raw["working_capital"]
        net_fixed_assets = raw["net_fixed_assets"]
        total_mv_wan = raw["total_mv"]  # daily_basic.total_mv 单位是万元
        close_price = raw["close"]
        net_debt = raw["net_debt"]

        # --- ROC: EBIT / (净营运资本 + 净固定资产) ---
        roc: Optional[float] = None
        invested_capital = None
        if working_capital is not None and net_fixed_assets is not None:
            invested_capital = working_capital + net_fixed_assets
        if ebit is not None and invested_capital and invested_capital > 0:
            roc = ebit / invested_capital

        # --- Earnings Yield: EBIT / EV ---
        # EV = 市值(元) + 净有息负债(元)
        ev: Optional[float] = None
        earnings_yield: Optional[float] = None
        if total_mv_wan is not None:
            market_cap_yuan = total_mv_wan * 10000.0
            ev = market_cap_yuan + (net_debt or 0.0)
            if ebit is not None and ev and ev > 0:
                earnings_yield = ebit / ev

        # 异常值过滤：超过合理上限的 ROC / EY 一般是口径问题（极小分母、单季 EBIT 等），
        # 污染排序且误导用户。阈值见模块常量 ROC_SANITY_CAP / EY_SANITY_CAP。
        if roc is not None and roc > ROC_SANITY_CAP:
            roc = None
        if earnings_yield is not None and earnings_yield > EY_SANITY_CAP:
            earnings_yield = None

        # --- Intrinsic Value: EPS * (8.5 + 2g) ---
        # ST / *ST 股不输出内在价值：格雷厄姆公式前提是"持续经营、盈利稳定"，
        # ST 股处于退市风险警示，PE 低是"风险折价"而非"低估机会"。业界价值筛选标配是剔除 ST。
        # ROC / EY 保留（两者对 ST 股仍有参考意义，便于用户判断基本面）。
        stock_name = raw.get("stock_name") or ""
        is_st = stock_name.startswith("ST") or stock_name.startswith("*ST")

        g_rate, g_source = self._estimate_g(ts_code, basic_eps)
        intrinsic_value: Optional[float] = None
        intrinsic_margin: Optional[float] = None
        if not is_st and basic_eps is not None and basic_eps > 0 and g_rate is not None:
            # 公式中的 g 按百分数形式代入（如 10% 增长代入 10，而非 0.10），
            # 与 Graham 原版公式一致。
            intrinsic_value = basic_eps * (8.5 + 2.0 * (g_rate * 100.0))
            if close_price and close_price > 0:
                intrinsic_margin = intrinsic_value / close_price - 1.0
        if is_st:
            g_rate = None
            g_source = 'na'

        return {
            "ts_code": ts_code,
            "roc": roc,
            "earnings_yield": earnings_yield,
            "intrinsic_value": intrinsic_value,
            "intrinsic_margin": intrinsic_margin,
            "g_rate": g_rate,
            "g_source": g_source,
            "ebit": ebit,
            "basic_eps": basic_eps,
            "total_mv": total_mv_wan,
            "ev": ev,
            "working_capital": working_capital,
            "net_fixed_assets": net_fixed_assets,
            "latest_price": close_price,
            "income_end_date": raw["income_end_date"],
            "balance_end_date": raw["balance_end_date"],
            "quote_trade_date": raw["quote_trade_date"],
        }

    # ========================================================================
    # 数据拉取：一次查询抓齐 income + balancesheet + daily_basic 最新快照
    # ========================================================================

    def _fetch_raw_snapshot(self, ts_code: str, today: str) -> Optional[Dict[str, Any]]:
        """取最新的 income / balancesheet / daily_basic 快照。

        - income / balancesheet：按 ts_code 取 ann_date <= today 的 MAX(end_date)，
          该 end_date 下按 ann_date DESC 取第一条（防止同期有多次修订时拿到旧的）
        - daily_basic：取 MAX(trade_date) 最新一行
        """
        sql = """
        WITH inc AS (
            SELECT *
            FROM income
            WHERE ts_code = %(code)s
              AND ann_date <= %(today)s
              AND end_date = (
                  SELECT MAX(end_date) FROM income
                  WHERE ts_code = %(code)s AND ann_date <= %(today)s
              )
            ORDER BY ann_date DESC
            LIMIT 1
        ),
        bs AS (
            SELECT *
            FROM balancesheet
            WHERE ts_code = %(code)s
              AND ann_date <= %(today)s
              AND end_date = (
                  SELECT MAX(end_date) FROM balancesheet
                  WHERE ts_code = %(code)s AND ann_date <= %(today)s
              )
            ORDER BY ann_date DESC
            LIMIT 1
        ),
        db AS (
            SELECT *
            FROM daily_basic
            WHERE ts_code = %(code)s
            ORDER BY trade_date DESC
            LIMIT 1
        ),
        sb AS (
            SELECT name FROM stock_basic WHERE ts_code = %(code)s LIMIT 1
        )
        SELECT
            inc.end_date        AS income_end_date,
            inc.ebit,
            inc.operate_profit,
            inc.fin_exp,
            bs.end_date         AS bs_end_date,
            bs.total_cur_assets,
            bs.total_cur_liab,
            bs.fix_assets,
            bs.lt_borr,
            bs.st_borr,
            bs.bond_payable,
            bs.money_cap,
            db.trade_date       AS quote_trade_date,
            db.total_mv,
            db.close,
            db.pe,
            db.pe_ttm,
            sb.name             AS stock_name
        FROM inc
        FULL OUTER JOIN bs ON TRUE
        FULL OUTER JOIN db ON TRUE
        FULL OUTER JOIN sb ON TRUE
        """
        row = _exec_fetchone(sql, {"code": ts_code, "today": today})
        if row is None:
            return None

        (
            income_end_date, ebit_raw, operate_profit_raw, fin_exp_raw,
            bs_end_date, cur_assets, cur_liab, fix_assets,
            lt_borr, st_borr, bond_payable, money_cap,
            quote_trade_date, total_mv, close_price, pe_raw, pe_ttm_raw,
            stock_name,
        ) = row

        ebit = _to_float(ebit_raw)
        # EBIT 兜底：ebit 字段缺失时用 operate_profit + fin_exp 近似（经营利润 + 财务费用）
        if ebit is None:
            op = _to_float(operate_profit_raw)
            fe = _to_float(fin_exp_raw)
            if op is not None:
                ebit = op + (fe or 0.0)

        cur_assets_f = _to_float(cur_assets)
        cur_liab_f = _to_float(cur_liab)
        working_capital = (
            (cur_assets_f - cur_liab_f)
            if cur_assets_f is not None and cur_liab_f is not None
            else None
        )

        # 净固定资产直接用 Tushare 的 fix_assets（固定资产净值，已扣累计折旧，对应 PP&E net）。
        # Greenblatt 原书 Net Fixed Assets 就是 PP&E net；减去 cip / const_materials 会把
        # 在建工程大的公司（如 600080 金花股份 cip=4.74 亿 > fix=1.72 亿）算出负数分母，把 ROC
        # 放大到几十倍。cip 算不算投入资本可以争论，但至少不能用减法。
        net_fixed_assets = _to_float(fix_assets)

        # 净有息负债 = 长借 + 短借 + 应付债券 − 货币资金
        debts = (_to_float(lt_borr) or 0.0) + (_to_float(st_borr) or 0.0) + (_to_float(bond_payable) or 0.0)
        cash = _to_float(money_cap) or 0.0
        net_debt = debts - cash

        # EPS 反推口径（业界 / Greenblatt 原书标准：TTM）：
        # 不再用 income.basic_eps 直接值——CDR / A+H / A+B 双重上市公司（如 689009 九号公司）
        # 的 income.basic_eps 按"A 股发行前股本"折算，会被放大 ~10 倍（九号公司年报 EPS=24.72
        # 而市场真实 EPS ≈ 2.43，对应 PE=1.77 vs 真实 PE=18.02）。
        # 市场 PE 是唯一可信的每股盈利口径锚。优先 pe_ttm（Greenblatt 用 TTM）；若 pe_ttm
        # 为空则兜底用静态 pe（新上市公司可能未到首份 TTM）。pe ≤ 0 的亏损公司直接返回 None，
        # 格雷厄姆公式本就不适用负 EPS，过滤是正确行为。
        pe_for_eps = _to_float(pe_ttm_raw) or _to_float(pe_raw)
        close_f = _to_float(close_price)
        eps_ttm: Optional[float] = None
        if pe_for_eps is not None and pe_for_eps > 0 and close_f is not None and close_f > 0:
            eps_ttm = close_f / pe_for_eps

        return {
            "income_end_date": income_end_date,
            "balance_end_date": bs_end_date,
            "quote_trade_date": quote_trade_date.strftime("%Y%m%d") if hasattr(quote_trade_date, "strftime") else quote_trade_date,
            "ebit": ebit,
            "basic_eps": eps_ttm,  # 字段名保留向后兼容；实际语义为 TTM EPS
            "working_capital": working_capital,
            "net_fixed_assets": net_fixed_assets,
            "net_debt": net_debt,
            "total_mv": _to_float(total_mv),
            "close": close_f,
            "stock_name": stock_name,
        }

    # ========================================================================
    # 增长率 g 估算（研报路径封顶 15% + 历史 CAGR 回退封顶 10%）
    # ========================================================================

    def _estimate_g(self, ts_code: str, basic_eps: Optional[float]) -> tuple[Optional[float], str]:
        """返回 (g_rate_小数, source)。
        - source='analyst' | 'history' | 'na'
        - g <= 0 或原料不足时返回 (None, 'na')，上游 IV 置 NULL
        - 研报路径封顶 15%，历史路径封顶 10%（详见常量定义）
        """
        # 路径 1：券商一致预期（近 180 天 ≥ MIN_ANALYST_COUNT 家，对同一预测期聚合后算隐含 CAGR）
        if basic_eps is not None and basic_eps > 0:
            g = self._g_from_analyst_consensus(ts_code, basic_eps)
            if g is not None and g > 0:
                return min(g, G_CAP_ANALYST), 'analyst'

        # 路径 2：历史 EPS CAGR（近 HISTORY_CAGR_YEARS 年年报；要求每年 EPS 均为正）
        g = self._g_from_history_cagr(ts_code)
        if g is not None and g > 0:
            return min(g, G_CAP_HISTORY), 'history'

        return None, 'na'

    def _g_from_analyst_consensus(self, ts_code: str, basic_eps: float) -> Optional[float]:
        """研报路径：近 ANALYST_LOOKBACK_DAYS 天 report_rc 对每个 quarter 取中位数 EPS，
        用【研报序列内部】的最远预测 / 最近预测算 CAGR。

        为什么不拿已实现 basic_eps 当基准（踩过的坑）：
          山东路桥 2025 年报 basic_eps=1.16，研报对 2025~2028 一致预期 ≈ 1.51~1.58（零增长）。
          若 (1.51/1.16)^(1/2)-1 算出 14% 年化增长，内在价值被拉到 42 元（安全边际 +637%），
          而真实 g ≈ 0。根因是年报发布时滞 + 研报年初就押正值导致的跳升被误判为增速。

        参数 basic_eps：仅由调用方 `_estimate_g` 用作"是否有正利润"的门槛（亏损股不走研报路径），
        不参与本函数计算。保留参数以对齐调用语义。
        """
        sql = f"""
        WITH recent AS (
            SELECT ts_code, quarter, eps, report_date
            FROM report_rc
            WHERE ts_code = %(code)s
              AND eps IS NOT NULL
              AND eps > 0
              AND report_date >= to_char(CURRENT_DATE - INTERVAL '{ANALYST_LOOKBACK_DAYS} days', 'YYYYMMDD')
        )
        SELECT quarter, COUNT(*) AS n, percentile_cont(0.5) WITHIN GROUP (ORDER BY eps) AS eps_median
        FROM recent
        GROUP BY quarter
        HAVING COUNT(*) >= %(min_n)s
        ORDER BY quarter ASC
        """
        rows = _exec_fetchall(sql, {"code": ts_code, "min_n": MIN_ANALYST_COUNT})
        if not rows:
            return None

        # quarter 可能是 "2025" / "2025Q4" / "2026" 等，取首 4 位解析年份。
        # 不做 yr > current_year 过滤——研报的"2025Q4"可能在 2026 年初发布、
        # 与 2026Q4 并列构成序列的近端/远端，直接按年份升序排取首尾两端即可。
        forecasts: List[tuple[int, float]] = []
        for quarter, _n, eps_med in rows:
            try:
                yr = int(str(quarter)[:4])
                eps_val = _to_float(eps_med)
                if eps_val is None or eps_val <= 0:
                    continue
                forecasts.append((yr, eps_val))
            except (ValueError, TypeError):
                continue

        # 至少 2 个不同年度才能算斜率；单点序列无法判断增速方向。
        if len(forecasts) < 2:
            return None

        forecasts.sort()
        yr_near, eps_near = forecasts[0]
        yr_far, eps_far = forecasts[-1]
        years = yr_far - yr_near
        if years <= 0:
            return None
        try:
            return (eps_far / eps_near) ** (1.0 / years) - 1.0
        except (ValueError, ZeroDivisionError):
            return None

    def _g_from_history_cagr(self, ts_code: str) -> Optional[float]:
        """历史路径：近 HISTORY_CAGR_YEARS 年年报（end_date 以 1231 结尾）的 basic_eps CAGR。
        要求**每一年**的 EPS 都必须为正——首尾为正还不够，中间任一年为负或为零都拒绝。

        为什么：格雷厄姆公式的 g 是"可持续未来复合增速"。如果历史序列里有亏损年份
        （例如 0.19 → 亏损 → 0.85），数学上算出来的 CAGR 是业绩"触底反弹"的基数
        效应，而不是可持续增速。业界对价值投资筛选的标准做法是要求近 N 年连续盈利。
        """
        sql = """
        SELECT end_date, basic_eps
        FROM income
        WHERE ts_code = %(code)s
          AND basic_eps IS NOT NULL
          AND end_date LIKE '%%1231'
          AND ann_date <= to_char(CURRENT_DATE, 'YYYYMMDD')
        ORDER BY end_date DESC
        LIMIT %(limit)s
        """
        rows = _exec_fetchall(sql, {"code": ts_code, "limit": HISTORY_CAGR_YEARS + 1})
        if len(rows) < 2:
            return None
        # 每一年 EPS 都必须为正；任一年缺失或非正都拒绝此股票走历史路径
        eps_series = [_to_float(r[1]) for r in rows]
        if any(e is None or e <= 0 for e in eps_series):
            return None
        # rows 按 end_date DESC，最新在前；首(newest) = rows[0]，尾(oldest) = rows[-1]
        newest_eps = eps_series[0]
        oldest_eps = eps_series[-1]
        years = len(rows) - 1
        try:
            return (newest_eps / oldest_eps) ** (1.0 / years) - 1.0
        except (ValueError, ZeroDivisionError):
            return None
