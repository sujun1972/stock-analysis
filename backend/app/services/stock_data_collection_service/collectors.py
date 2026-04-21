"""
数据收集模块

从本地数据库收集各维度数据：基础盘面、资金流向、股东信息、财报、风险、神奇九转。
技术指标收集见 technical.py。
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from loguru import logger

from .formatters import days_since, format_date_dashed, parse_date_loose, quantile, safe_float


# ------------------------------------------------------------------
# 一、基础盘面与行业位置
# ------------------------------------------------------------------

async def get_basic_market(ts_code: str, pure_code: str) -> Dict:
    from app.repositories.stock_daily_repository import StockDailyRepository
    from app.repositories.daily_basic_repository import DailyBasicRepository
    from app.repositories.stock_basic_repository import StockBasicRepository
    from app.repositories.cyq_perf_repository import CyqPerfRepository
    from app.repositories.fina_indicator_repository import FinaIndicatorRepository
    from app.repositories.repurchase_repository import RepurchaseRepository

    daily_repo = StockDailyRepository()
    basic_repo = DailyBasicRepository()
    stock_repo = StockBasicRepository()
    cyq_repo = CyqPerfRepository()
    fina_repo = FinaIndicatorRepository()
    repurchase_repo = RepurchaseRepository()

    today = datetime.now()
    start_dash = (today - timedelta(days=14)).strftime('%Y-%m-%d')
    end_dash = today.strftime('%Y-%m-%d')
    start_yyyymmdd = (today - timedelta(days=14)).strftime('%Y%m%d')
    end_yyyymmdd = today.strftime('%Y%m%d')
    # 估值分位双窗口：3 年（近周期视角）+ 10 年（全周期视角）
    # 3 年窗口在行业下行期会因分母缩水虚高分位；10 年窗口可识别周期底部
    pe_pb_start_10y = (today - timedelta(days=365 * 10)).strftime('%Y%m%d')
    start_365d = (today - timedelta(days=365)).strftime('%Y%m%d')

    daily_df, basic_data, stock_info, cyq_data, fina_data, valuation_history_10y, repurchase_data = await asyncio.gather(
        asyncio.to_thread(daily_repo.get_by_code_and_date_range, ts_code, start_dash, end_dash),
        asyncio.to_thread(basic_repo.get_by_code_and_date_range, ts_code, start_yyyymmdd, end_yyyymmdd, 5),
        asyncio.to_thread(stock_repo.get_full_by_ts_code, ts_code),
        asyncio.to_thread(cyq_repo.get_by_date_range, start_yyyymmdd, end_yyyymmdd, ts_code, 1, 1),
        asyncio.to_thread(fina_repo.get_by_code, ts_code, None, None, 4),
        asyncio.to_thread(basic_repo.get_by_code_and_date_range, ts_code, pe_pb_start_10y, end_yyyymmdd, 5000),
        asyncio.to_thread(repurchase_repo.get_by_date_range, start_365d, end_yyyymmdd, ts_code, None, 10, 0),
    )

    result: Dict[str, Any] = {}

    if daily_df is not None and not daily_df.empty:
        latest = daily_df.iloc[-1]
        result['close'] = safe_float(latest.get('close'))
        result['pct_change'] = safe_float(latest.get('pct_change'))
        result['volume'] = safe_float(latest.get('volume'))
        result['amount'] = safe_float(latest.get('amount'))
        result['trade_date'] = str(daily_df.index[-1])[:10]
        result['recent_5d'] = [
            {
                'date': str(idx)[:10],
                'close': safe_float(row.get('close')),
                'pct_change': safe_float(row.get('pct_change')),
                'volume': safe_float(row.get('volume')),
            }
            for idx, row in daily_df.tail(5).iterrows()
        ]

    if basic_data:
        b = basic_data[0]
        result['pe_ttm'] = safe_float(b.get('pe_ttm'))
        result['pb'] = safe_float(b.get('pb'))
        result['turnover_rate'] = safe_float(b.get('turnover_rate'))
        result['total_mv'] = safe_float(b.get('total_mv'))
        result['circ_mv'] = safe_float(b.get('circ_mv'))

    # 交易所属性（SSE/SZSE/BSE）
    if stock_info:
        result['industry'] = stock_info.get('industry') or ''
        result['area'] = stock_info.get('area') or ''
        exchange = stock_info.get('exchange') or ''
        result['exchange'] = exchange
        if exchange == 'BSE':
            result['exchange_note'] = '北交所（涨跌幅±30%）'
        elif exchange == 'SSE':
            result['exchange_note'] = '上交所（涨跌幅±10%）'
        elif exchange == 'SZSE':
            result['exchange_note'] = '深交所（涨跌幅±10%）'
        else:
            result['exchange_note'] = ''
        # 科创板/创业板特殊涨跌幅
        if ts_code.startswith('688') or ts_code.startswith('300'):
            result['exchange_note'] = result['exchange_note'].replace('±10%', '±20%')

    # 财务指标（最新一期）
    # days_since_end 用于告知 AI 该报告期距今多久（季报快照容易被当作即时基本面误用）
    if fina_data:
        latest_fina = fina_data[0]
        end_date_str = str(latest_fina.get('end_date') or '')
        result['fina'] = {
            'end_date': end_date_str,
            'days_since_end': days_since(end_date_str, today.date()),
            'roe': safe_float(latest_fina.get('roe')),
            'grossprofit_margin': safe_float(latest_fina.get('grossprofit_margin')),
            'netprofit_yoy': safe_float(latest_fina.get('netprofit_yoy')),
            'or_yoy': safe_float(latest_fina.get('or_yoy')),
        }

    # 估值分位（PE-TTM / PB）双窗口：3 年（近周期）+ 10 年（全周期）+ 估值通道
    # 设计意图：单一窗口（尤其 3 年）对周期股存在"盈利塌陷导致分母变小、分位虚高"陷阱。
    # 同时给出 10 年窗口后，LLM 可识别"3 年分位 vs 10 年分位"的分歧并作出更稳健判断。
    if valuation_history_10y and (
        result.get('pe_ttm') is not None or result.get('pb') is not None
    ):
        # 按 trade_date 降序切分 3 年子集（daily_basic 查询已按 DESC 返回）
        three_year_cutoff = (today - timedelta(days=365 * 3)).strftime('%Y%m%d')
        history_3y = [
            r for r in valuation_history_10y
            if str(r.get('trade_date', '')) >= three_year_cutoff
        ]
        history_10y = valuation_history_10y

        result['pe_valuation'] = _compute_valuation_percentile(
            history_3y, history_10y, current_value=result.get('pe_ttm'),
            value_key='pe_ttm', require_positive=True,
        )
        result['pb_valuation'] = _compute_valuation_percentile(
            history_3y, history_10y, current_value=result.get('pb'),
            value_key='pb', require_positive=True,
        )

        # 向后兼容：langchain_tools.get_basic_market 的 CIO Agent 工具仍按旧键读取
        # PE 3 年分位，这里把 pe_valuation.window_3y 展平成 pe_percentile_3y 等旧字段
        pe_view = result.get('pe_valuation') or {}
        pe_3y = pe_view.get('window_3y') or {}
        if pe_3y.get('percentile') is not None:
            result['pe_percentile_3y'] = pe_3y.get('percentile')
            result['pe_sample_count'] = pe_3y.get('sample_count')
            result['pe_band_label'] = pe_3y.get('band_label')
            result['pe_band'] = pe_3y.get('band')

    # 东财行业板块及近5交易日涨跌幅
    industry_bk = await _get_industry_board(ts_code)
    if industry_bk:
        result['industry_board_name'] = industry_bk.get('name', '')
        result['industry_5d'] = await _get_board_pct_5d(industry_bk['ts_code'])

    # 所属概念板块 + 概念板块近5日涨幅 TOP3（A 股题材炒作的核心线索）
    # Tushare 的 stock_basic.industry 字段静态且粗糙（如"铝"），DC 概念板块日频更新，
    # 能反映真实题材归属（锂电池/储能/华为概念等）。
    concept_info = await _get_concept_boards_with_perf(ts_code)
    if concept_info:
        result['concept_boards'] = concept_info

    # 当日大盘指数（上证/深证）涨跌幅 — 用于个股相对强度对比
    market_index = await _get_market_index_today()
    if market_index:
        result['market_index'] = market_index

    if cyq_data:
        c = cyq_data[0]
        result['chip'] = {
            'winner_rate': safe_float(c.get('winner_rate')),
            'cost_50pct': safe_float(c.get('cost_50pct')),
            'cost_15pct': safe_float(c.get('cost_15pct')),
            'cost_85pct': safe_float(c.get('cost_85pct')),
            'weight_avg': safe_float(c.get('weight_avg')),
        }

    # 近 1 年回购计划（正面估值信号）
    if repurchase_data:
        active_statuses = {'预案', '股东大会通过', '实施'}
        active_plans = [r for r in repurchase_data if r.get('proc') in active_statuses]
        completed = [r for r in repurchase_data if r.get('proc') == '完成']
        latest_active = active_plans[0] if active_plans else None

        result['repurchase'] = {
            'active_plan': {
                'ann_date': str(latest_active.get('ann_date', '')) if latest_active else '',
                'end_date': str(latest_active.get('end_date', '') or '') if latest_active else '',
                'exp_date': str(latest_active.get('exp_date', '') or '') if latest_active else '',
                'proc': latest_active.get('proc', '') if latest_active else '',
                'vol': safe_float(latest_active.get('vol')) if latest_active else None,
                'amount': safe_float(latest_active.get('amount')) if latest_active else None,
                'high_limit': safe_float(latest_active.get('high_limit')) if latest_active else None,
                'low_limit': safe_float(latest_active.get('low_limit')) if latest_active else None,
            } if latest_active else None,
            'active_count_1y': len(active_plans),
            'completed_count_1y': len(completed),
            'total_completed_amount_1y': sum((r.get('amount') or 0) for r in completed),
        }

    return result


def _compute_valuation_window(history: list, value_key: str, require_positive: bool) -> Optional[Dict]:
    """对一段历史数据计算分位指标 + 估值通道（P10/P50/P90/P99）。"""
    vals = []
    for r in history:
        v = safe_float(r.get(value_key))
        if v is None:
            continue
        if require_positive and v <= 0:
            continue
        vals.append(v)
    if len(vals) < 30:
        return None
    vals.sort()
    return {
        'sample_count': len(vals),
        'values_sorted': vals,
        'band': {
            'p10': quantile(vals, 0.10),
            'p50': quantile(vals, 0.50),
            'p90': quantile(vals, 0.90),
            'p99': quantile(vals, 0.99),
            'min': round(vals[0], 2),
            'max': round(vals[-1], 2),
        },
    }


def _percentile_from_sorted(sorted_vals: list, current: float) -> Optional[float]:
    if not sorted_vals or current is None:
        return None
    lower = sum(1 for v in sorted_vals if v < current)
    return round(lower / len(sorted_vals) * 100, 1)


def _band_label(pct: Optional[float]) -> str:
    if pct is None:
        return ''
    if pct >= 95:
        return '≥95%分位区间'
    if pct >= 80:
        return '80~95%分位区间'
    if pct >= 60:
        return '60~80%分位区间'
    if pct >= 40:
        return '40~60%分位区间'
    if pct >= 20:
        return '20~40%分位区间'
    return '<20%分位区间'


def _compute_valuation_percentile(
    history_3y: list,
    history_10y: list,
    current_value: Optional[float],
    value_key: str,
    require_positive: bool = True,
) -> Dict:
    """
    计算 3 年 / 10 年双窗口估值分位。

    返回结构:
        {
          'current': <当前值>,
          'window_3y':  {percentile, sample_count, band_label, band: {...}},
          'window_10y': {percentile, sample_count, band_label, band: {...}, years_available},
          'divergence': {
              'abs_pct_diff': float,             # |3年分位 - 10年分位|
              'direction': '3y_higher' / '10y_higher' / 'aligned',
              'note': 一句话中性事实陈述（仅 >=30pct 偏离时出）
          } | None,
        }
    注意：10 年窗口不足时按实际可用年数给，并在 `years_available` 标注。
    """
    out: Dict[str, Any] = {'current': current_value}

    if current_value is None or (require_positive and current_value <= 0):
        return out

    w3 = _compute_valuation_window(history_3y, value_key, require_positive)
    w10 = _compute_valuation_window(history_10y, value_key, require_positive)

    def _fmt_window(win: Optional[Dict]) -> Optional[Dict]:
        if not win:
            return None
        pct = _percentile_from_sorted(win['values_sorted'], current_value)
        return {
            'percentile': pct,
            'sample_count': win['sample_count'],
            'band_label': _band_label(pct),
            'band': win['band'],
        }

    window_3y = _fmt_window(w3)
    window_10y = _fmt_window(w10)
    if window_3y:
        out['window_3y'] = window_3y
    if window_10y:
        # 标注真实覆盖年数（首尾交易日距今差），让 AI 知道样本是否充足
        first_td_raw = history_10y[-1].get('trade_date') if history_10y else None
        last_td_raw = history_10y[0].get('trade_date') if history_10y else None
        first_td = parse_date_loose(first_td_raw)
        last_td = parse_date_loose(last_td_raw)
        years_avail = None
        if first_td and last_td:
            years_avail = round((last_td - first_td).days / 365.0, 1)
        window_10y['years_available'] = years_avail
        out['window_10y'] = window_10y

    # 分位分歧：仅当 >=30pct 差距才输出中性提示；由 AI 自行判断是否为周期效应
    if window_3y and window_10y:
        p3 = window_3y.get('percentile')
        p10 = window_10y.get('percentile')
        if p3 is not None and p10 is not None:
            diff = round(p3 - p10, 1)
            abs_diff = abs(diff)
            if abs_diff >= 30:
                direction = '3y_higher' if diff > 0 else '10y_higher'
                out['divergence'] = {
                    'abs_pct_diff': abs_diff,
                    'direction': direction,
                    'note': (
                        f'3 年分位（{p3}%）较 10 年分位（{p10}%）{"高" if diff > 0 else "低"} '
                        f'{abs_diff} pct，样本窗口选择差异显著'
                    ),
                }
            else:
                out['divergence'] = None
    return out


async def _get_industry_board(ts_code: str) -> Optional[Dict]:
    """通过 dc_member JOIN dc_index 查找股票所属行业板块（idx_type='行业板块'）。"""
    try:
        from app.repositories.dc_member_repository import DcMemberRepository
        return await asyncio.to_thread(
            DcMemberRepository().get_industry_board_by_con_code, ts_code
        )
    except Exception as e:
        logger.warning(f"查询行业板块失败: {e}")
        return None


async def _get_board_pct_5d(board_ts_code: str) -> list:
    """从 dc_daily 获取板块近5个交易日涨跌幅。"""
    try:
        from app.repositories.dc_daily_repository import DcDailyRepository
        today = datetime.now()
        start = (today - timedelta(days=14)).strftime('%Y%m%d')
        end = today.strftime('%Y%m%d')
        data = await asyncio.to_thread(
            DcDailyRepository().get_by_date_range, start, end, board_ts_code, 5
        )
        return [
            {
                'trade_date': str(r.get('trade_date', ''))[:8],
                'pct_change': safe_float(r.get('pct_change')),
            }
            for r in (data or [])
        ]
    except Exception as e:
        logger.warning(f"查询板块近5日涨跌幅失败: {e}")
        return []


# DC 概念板块中属于"短期炒作标签"的噪音词，不代表真实题材归属，应过滤
# （如"昨日涨停"、"昨日连板"等是 DC 按盘口特征动态打的标签）
_CONCEPT_NOISE_KEYWORDS = (
    '昨日', '今日', '热股', '多板', '涨停', '连板', '炸板', '触板',
    '换手', '振幅', '打板', '融资融券', '深股通', '沪股通',
)


def _is_noise_concept(name: str) -> bool:
    """判断概念板块名是否为短期炒作/通道类噪音标签。"""
    if not name:
        return True
    return any(kw in name for kw in _CONCEPT_NOISE_KEYWORDS)


async def _get_concept_boards_with_perf(ts_code: str, top_n: int = 8) -> list:
    """拉取股票所属概念板块，并按"最新一日 + 近5日累计"涨跌幅排序返回 TOP N。

    概念板块是 A 股题材炒作的直接载体，比 Tushare 静态 industry 字段更能反映
    近期资金关注的题材线索。同时过滤"昨日涨停/昨日连板"等短期标签噪音。
    """
    try:
        from app.repositories.dc_member_repository import DcMemberRepository
        from app.repositories.dc_daily_repository import DcDailyRepository

        boards = await asyncio.to_thread(
            DcMemberRepository().get_boards_by_con_code,
            ts_code, '概念板块', 50,
        )
        # 过滤噪音 + 去重（同义板块如"锂电池"/"锂电池概念"归一，保留其一）
        def _dedup_key(name: str) -> str:
            for suffix in ('概念', '板块'):
                if name.endswith(suffix) and len(name) > len(suffix):
                    return name[:-len(suffix)]
            return name

        seen_keys = set()
        real_boards = []
        for b in boards:
            name = b.get('name', '')
            if _is_noise_concept(name):
                continue
            key = _dedup_key(name)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            real_boards.append(b)

        if not real_boards:
            return []

        today = datetime.now()
        start = (today - timedelta(days=14)).strftime('%Y%m%d')
        end = today.strftime('%Y%m%d')
        dc_daily_repo = DcDailyRepository()

        async def _fetch_perf(board):
            rows = await asyncio.to_thread(
                dc_daily_repo.get_by_date_range,
                start, end, board['ts_code'], 5,
            )
            rows = rows or []
            pct_1d = safe_float(rows[0].get('pct_change')) if rows else None
            cum_5d = None
            if rows:
                cum = 1.0
                for r in rows:
                    p = safe_float(r.get('pct_change')) or 0
                    cum *= (1 + p / 100)
                cum_5d = round((cum - 1) * 100, 2)
            latest_date = str(rows[0].get('trade_date', ''))[:8] if rows else ''
            return {
                'name': board['name'],
                'ts_code': board['ts_code'],
                'pct_1d': pct_1d,
                'cum_5d': cum_5d,
                'latest_date': latest_date,
            }

        perfs = await asyncio.gather(*[_fetch_perf(b) for b in real_boards])
        # 按近5日累计涨幅降序（无数据的排最后）
        perfs.sort(key=lambda x: (x['cum_5d'] is None, -(x['cum_5d'] or 0)))
        return perfs[:top_n]
    except Exception as e:
        logger.warning(f"查询概念板块业绩失败 ({ts_code}): {e}")
        return []


async def _get_market_index_today() -> Optional[Dict[str, Any]]:
    """从 moneyflow_mkt_dc 获取最近一个交易日上证/深证收盘 + 涨跌幅，
    用于和个股涨跌幅做相对强度对比（个股 - 大盘 = 相对强弱）。"""
    try:
        from app.repositories.moneyflow_mkt_dc_repository import MoneyflowMktDcRepository
        today = datetime.now()
        start = (today - timedelta(days=14)).strftime('%Y%m%d')
        end = today.strftime('%Y%m%d')
        rows = await asyncio.to_thread(
            MoneyflowMktDcRepository().get_by_date_range,
            start, end, 1, 0,
        )
        if not rows:
            return None
        r = rows[0]
        return {
            'trade_date': str(r.get('trade_date', ''))[:8],
            'close_sh': safe_float(r.get('close_sh')),
            'pct_change_sh': safe_float(r.get('pct_change_sh')),
            'close_sz': safe_float(r.get('close_sz')),
            'pct_change_sz': safe_float(r.get('pct_change_sz')),
        }
    except Exception as e:
        logger.warning(f"查询大盘指数失败: {e}")
        return None


# ------------------------------------------------------------------
# 二、资金流向
# ------------------------------------------------------------------

async def get_capital_flow(ts_code: str, pure_code: str) -> Dict:
    from app.repositories.moneyflow_stock_dc_repository import MoneyflowStockDcRepository
    from app.repositories.hk_hold_repository import HkHoldRepository
    from app.repositories.block_trade_repository import BlockTradeRepository

    today = datetime.now()
    start_10d = (today - timedelta(days=20)).strftime('%Y%m%d')
    start_30d = (today - timedelta(days=30)).strftime('%Y%m%d')
    end_today = today.strftime('%Y%m%d')

    # 北交所(.BJ)不适用北向资金，跳过 hk_hold 查询
    is_bse = ts_code.endswith('.BJ')

    tasks = [
        asyncio.to_thread(MoneyflowStockDcRepository().get_by_date_range, start_10d, end_today, ts_code, 10),
        asyncio.to_thread(BlockTradeRepository().get_by_code_and_date_range, ts_code, start_30d, end_today, 50),
    ]
    if not is_bse:
        tasks.append(
            asyncio.to_thread(HkHoldRepository().get_paged, None, ts_code, None, None, 'trade_date', 'desc', 1, 10),
        )

    gather_results = await asyncio.gather(*tasks)
    flow_data = gather_results[0]
    block_data = gather_results[1]
    hk_data = gather_results[2] if not is_bse else None

    result: Dict[str, Any] = {}

    if flow_data:
        # 东方财富个股资金流向口径：
        #   buy_elg_amount = 超大单（>=100万元）净额
        #   buy_lg_amount  = 大单（20~100万元）净额
        #   buy_md_amount  = 中单（4~20万元）净额
        #   buy_sm_amount  = 小单（<4万元）净额
        #   net_amount     = 主力净额 = 超大单净额 + 大单净额（即 elg + lg）
        # 单位：万元（DC 原始单位即为万元）
        net_amounts = [safe_float(r.get('net_amount')) or 0 for r in flow_data]
        result['net_1d'] = net_amounts[0] if net_amounts else None
        result['net_5d'] = sum(net_amounts[:5])
        result['net_10d'] = sum(net_amounts[:10])
        result['flow_caliber'] = (
            '主力净额 = 超大单(≥100万元)净额 + 大单(20~100万元)净额；'
            '不含中单(4~20万元)与小单(<4万元)；单位：万元'
        )
        result['flow_detail'] = [
            {
                'trade_date': str(r.get('trade_date', ''))[:8],
                'net_amount': safe_float(r.get('net_amount')) or 0,
                'net_elg': safe_float(r.get('buy_elg_amount')) or 0,
                'net_lg': safe_float(r.get('buy_lg_amount')) or 0,
                'net_md': safe_float(r.get('buy_md_amount')) or 0,
                'net_sm': safe_float(r.get('buy_sm_amount')) or 0,
                'pct_change': safe_float(r.get('pct_change')) or 0,
            }
            for r in flow_data[:5]
        ]

        # 资金 vs 价格 累计对比（5 日 / 10 日）：用复合涨幅（连乘）算累计涨幅
        # 主力净额 = 超大单+大单，但两者方向可能相反。拆开看可识别"游资/机构博弈"结构：
        # 例如超大单（大资金）派发、大单（活跃游资）接力，用总净额会误导。
        def _cumulative_pct(rows):
            cum = 1.0
            for r in rows:
                p = safe_float(r.get('pct_change')) or 0
                cum *= (1 + p / 100)
            return round((cum - 1) * 100, 2)

        def _cumulative_net(rows, key):
            return round(sum((safe_float(r.get(key)) or 0) for r in rows), 2)

        if flow_data:
            cum_5d_pct = _cumulative_pct(flow_data[:5]) if len(flow_data) >= 5 else None
            cum_10d_pct = _cumulative_pct(flow_data[:10]) if len(flow_data) >= 10 else None
            elg_5d = _cumulative_net(flow_data[:5], 'buy_elg_amount') if len(flow_data) >= 5 else None
            lg_5d = _cumulative_net(flow_data[:5], 'buy_lg_amount') if len(flow_data) >= 5 else None
            elg_10d = _cumulative_net(flow_data[:10], 'buy_elg_amount') if len(flow_data) >= 10 else None
            lg_10d = _cumulative_net(flow_data[:10], 'buy_lg_amount') if len(flow_data) >= 10 else None
            net_5d = result['net_5d']
            net_10d = result['net_10d']

            def _battle_tag(elg_val, lg_val):
                """超大单 vs 大单方向是否分歧：同向返回 None；分歧返回描述文字。"""
                if elg_val is None or lg_val is None:
                    return None
                if elg_val * lg_val < 0:
                    if elg_val < 0 < lg_val:
                        return '超大单派发、大单承接（筹码由大资金向游资转移）'
                    return '超大单吸筹、大单派发（大资金逆势建仓）'
                return None

            result['flow_vs_price'] = {
                'cum_pct_5d': cum_5d_pct,
                'cum_pct_10d': cum_10d_pct,
                'net_5d': net_5d,
                'net_10d': net_10d,
                'elg_5d': elg_5d,
                'lg_5d': lg_5d,
                'elg_10d': elg_10d,
                'lg_10d': lg_10d,
                'battle_5d': _battle_tag(elg_5d, lg_5d),
                'battle_10d': _battle_tag(elg_10d, lg_10d),
                'same_direction_5d': (
                    None if cum_5d_pct is None
                    else (cum_5d_pct >= 0) == (net_5d >= 0)
                ),
                'same_direction_10d': (
                    None if cum_10d_pct is None
                    else (cum_10d_pct >= 0) == (net_10d >= 0)
                ),
            }

    if hk_data:
        latest_hk = hk_data[0]
        latest_date_str = format_date_dashed(latest_hk.get('trade_date'))
        result['hk_hold'] = {
            'trade_date': latest_date_str,
            'vol': latest_hk.get('vol'),
            'ratio': safe_float(latest_hk.get('ratio')),
            # days_lag：北向持股部分股票为季报频次，告知 AI 该快照距今多久，避免把过期数据当即时持仓
            'days_lag': days_since(latest_date_str, today.date()),
        }
        # 与上一期对比时取 hk_data[1]（已按 trade_date desc 排序），
        # 确保是真正的"上一期环比"，而非窗口最末记录（可能跨年）
        if len(hk_data) > 1:
            prev_record = hk_data[1]
            prev_vol = safe_float(prev_record.get('vol')) or 0
            curr_vol = safe_float(latest_hk.get('vol')) or 0
            result['hk_hold']['prev_vol'] = prev_vol
            result['hk_hold']['prev_date'] = format_date_dashed(prev_record.get('trade_date'))
            result['hk_hold']['vol_change_pct'] = (
                round((curr_vol - prev_vol) / prev_vol * 100, 2) if prev_vol else None
            )

    # 近 30 日大宗交易（vol 单位：万股；amount 单位：万元）
    if block_data:
        # 查询近 30 日日线收盘价，用于计算折溢价
        from app.repositories.stock_daily_repository import StockDailyRepository
        daily_start_dash = (today - timedelta(days=30)).strftime('%Y-%m-%d')
        daily_end_dash = today.strftime('%Y-%m-%d')
        close_map: Dict[str, float] = {}
        try:
            daily_df = await asyncio.to_thread(
                StockDailyRepository().get_by_code_and_date_range,
                ts_code, daily_start_dash, daily_end_dash,
            )
            if daily_df is not None and not daily_df.empty:
                for idx, row in daily_df.iterrows():
                    date_key = str(idx)[:10].replace('-', '')
                    close_val = safe_float(row.get('close'))
                    if close_val:
                        close_map[date_key] = close_val
        except Exception as e:
            logger.warning(f"获取日线数据失败（用于大宗折溢价）: {e}")

        premium_list = []
        buyer_amount: Dict[str, float] = {}
        total_amount_wan = 0.0
        total_vol_wan = 0.0
        for r in block_data:
            total_amount_wan += float(r.get('amount') or 0)
            total_vol_wan += float(r.get('vol') or 0)
            buyer = (r.get('buyer') or '').strip() or '未知'
            buyer_amount[buyer] = buyer_amount.get(buyer, 0.0) + float(r.get('amount') or 0)
            date_key = str(r.get('trade_date') or '').replace('-', '')
            close_ref = close_map.get(date_key)
            price = safe_float(r.get('price'))
            if close_ref and price:
                premium_list.append((price - close_ref) / close_ref * 100)

        avg_premium_pct = round(sum(premium_list) / len(premium_list), 2) if premium_list else None
        top_buyers = sorted(buyer_amount.items(), key=lambda x: x[1], reverse=True)[:3]

        result['block_trade'] = {
            'records_30d': len(block_data),
            'total_amount_wan': round(total_amount_wan, 2),
            'total_vol_wan': round(total_vol_wan, 2),
            'avg_premium_pct': avg_premium_pct,
            'top_buyers': [
                {'buyer': b, 'amount_wan': round(a, 2)} for b, a in top_buyers
            ],
        }

    return result


# ------------------------------------------------------------------
# 三、股东信息
# ------------------------------------------------------------------

async def get_shareholder_info(ts_code: str) -> Dict:
    from app.repositories.stk_holdernumber_repository import StkHolderNumberRepository
    from app.repositories.stk_holdertrade_repository import StkHoldertradeRepository
    from app.repositories.share_float_repository import ShareFloatRepository

    today = datetime.now()
    three_months_ago = (today - timedelta(days=90)).strftime('%Y%m%d')
    one_month_later = (today + timedelta(days=30)).strftime('%Y%m%d')
    today_str = today.strftime('%Y%m%d')

    holder_nums, reductions, floats = await asyncio.gather(
        asyncio.to_thread(StkHolderNumberRepository().get_latest_by_code, ts_code, 5),
        asyncio.to_thread(
            StkHoldertradeRepository().get_by_date_range,
            three_months_ago, today_str, ts_code, None, 'DE', 20
        ),
        asyncio.to_thread(
            ShareFloatRepository().get_by_date_range, today_str, one_month_later, ts_code, None, None, 20
        ),
    )

    result: Dict[str, Any] = {}

    if holder_nums:
        seen: Dict[str, Any] = {}
        for r in holder_nums:
            quarter_key = str(r.get('end_date', ''))[:6]
            if quarter_key not in seen:
                seen[quarter_key] = r
        deduped = list(seen.values())[:4]
        nums_list = [
            {
                'ann_date': str(r.get('ann_date', '')),
                'end_date': str(r.get('end_date', '')),
                'holder_num': int(r.get('holder_num') or 0),
            }
            for r in deduped
        ]
        for i in range(len(nums_list) - 1):
            curr = nums_list[i]['holder_num']
            prev = nums_list[i + 1]['holder_num']
            nums_list[i]['qoq_pct'] = round((curr - prev) / prev * 100, 2) if prev else None
        result['holder_nums'] = nums_list

        # 最新一条股东人数距今天数：超过 60 天（≈一个季度）由 text_formatter 触发滞后提示
        if nums_list:
            lag = days_since(nums_list[0].get('end_date'), today.date())
            if lag is not None:
                result['holder_nums_days_lag'] = lag

    if reductions:
        result['reductions'] = [
            {
                'ann_date': str(r.get('ann_date', '')),
                'holder_name': r.get('holder_name', ''),
                'change_vol': r.get('change_vol'),
                'change_ratio': r.get('change_ratio'),
                'avg_price': r.get('avg_price'),
                'begin_date': str(r.get('begin_date', '')),
                'close_date': str(r.get('close_date', '')),
            }
            for r in reductions
        ]

    if floats:
        result['upcoming_floats'] = [
            {
                'float_date': str(r.get('float_date', '')),
                'float_share': r.get('float_share'),
                'float_ratio': r.get('float_ratio'),
                'share_type': r.get('share_type', ''),
            }
            for r in floats
        ]

    return result


# ------------------------------------------------------------------
# 三B、股息与现金回报
# ------------------------------------------------------------------

async def get_dividend_context(ts_code: str) -> Dict:
    """
    收集股息与分红数据，用于长线价值分析补全"分红回报"维度。

    数据源：
      - daily_basic.dv_ttm / dv_ratio — 最近一日股息率（%），口径为 TTM / 近一年度
      - dividend 表 — 分红派息明细（cash_div_tax 单位：元/股，每股派息含税）
      - income.n_income_attr_p — 归母净利润，用于推算分红率

    返回结构：
      {
        'dv_ttm': 5.56,                    # 股息率 TTM（%）
        'dv_ratio': 5.56,                  # 股息率（近一期年度口径，%）
        'latest_year': {                   # 最近 1 个已实施年度
          'end_date': 'YYYYMMDD',
          'ann_date': 'YYYYMMDD',
          'cash_div_tax': 0.2715,          # 每股派息（含税，元）
          'payout_ratio': 28.75,           # 分红率（%）
        },
        'history': [                       # 近 5 年每股派息（报告期末倒序）
          {'end_date': 'YYYYMMDD', 'cash_div_tax': 0.2715, 'div_proc': '实施'},
          ...
        ],
        'consecutive_years': 5,            # 连续实施现金分红的年数
        'latest_plan': {...} | None,       # 最新未实施的年度预案
      }
    """
    from app.repositories.daily_basic_repository import DailyBasicRepository
    from app.repositories.dividend_repository import DividendRepository
    from app.repositories.income_repository import IncomeRepository

    today = datetime.now()
    start_yyyymmdd = (today - timedelta(days=14)).strftime('%Y%m%d')
    end_yyyymmdd = today.strftime('%Y%m%d')
    # 近 6 年年度分红（覆盖"连续分红 N 年"判断）
    start_6y = (today - timedelta(days=365 * 6)).strftime('%Y%m%d')

    basic_data, dividend_rows, income_rows = await asyncio.gather(
        asyncio.to_thread(
            DailyBasicRepository().get_by_code_and_date_range,
            ts_code, start_yyyymmdd, end_yyyymmdd, 5,
        ),
        asyncio.to_thread(
            DividendRepository().get_by_ts_code,
            ts_code, start_6y, end_yyyymmdd, 40,
        ),
        asyncio.to_thread(
            IncomeRepository().get_by_date_range,
            start_6y, end_yyyymmdd, ts_code, '1', None, 20,
        ),
    )

    result: Dict[str, Any] = {}

    # 1. 股息率（dv_ttm / dv_ratio）
    if basic_data:
        b0 = basic_data[0]
        result['dv_ttm'] = safe_float(b0.get('dv_ttm'))
        result['dv_ratio'] = safe_float(b0.get('dv_ratio'))

    # 2. 年报期现金分红明细（仅保留报告期末为 YYYY1231 的年度分红，剔除中期预案）
    annual_dividends = [
        r for r in (dividend_rows or [])
        if str(r.get('end_date', '')).endswith('1231')
    ]
    # 按 end_date desc 排序已由 repo 保证；这里再按 end_date + 状态双排序防御
    annual_dividends.sort(
        key=lambda r: (str(r.get('end_date', '')), 0 if r.get('div_proc') == '实施' else 1),
        reverse=True,
    )

    # 3. 年度归母净利润（用于推算分红率）
    income_by_year: Dict[str, float] = {}
    for r in (income_rows or []):
        end_d = str(r.get('end_date', ''))
        if end_d.endswith('1231'):
            np_val = safe_float(r.get('n_income_attr_p'))
            if np_val is not None:
                income_by_year[end_d] = np_val

    # 4. 从 daily_basic 拿最新 total_share（单位：万股）用于分红率估算
    total_share_wan = None
    if basic_data:
        total_share_wan = safe_float(basic_data[0].get('total_share'))

    # 5. 组装 history + 识别最新"实施年"和最新"预案年"
    history: list = []
    latest_year = None
    latest_plan = None
    seen_end_dates = set()
    for r in annual_dividends:
        end_d = str(r.get('end_date', ''))
        if end_d in seen_end_dates:
            continue
        seen_end_dates.add(end_d)
        proc = r.get('div_proc', '')
        cash_div = safe_float(r.get('cash_div_tax'))
        history.append({
            'end_date': end_d,
            'cash_div_tax': cash_div,
            'div_proc': proc,
            'ann_date': str(r.get('ann_date', '')),
        })
        if proc == '实施' and latest_year is None and cash_div is not None and cash_div > 0:
            payout_ratio = None
            net_profit = income_by_year.get(end_d)
            if net_profit and total_share_wan and cash_div:
                # cash_div (元/股) × total_share (万股) × 1e4 = 总分红（元）
                total_div = cash_div * total_share_wan * 1e4
                if net_profit > 0:
                    payout_ratio = round(total_div / net_profit * 100, 2)
            latest_year = {
                'end_date': end_d,
                'ann_date': str(r.get('ann_date', '')),
                'cash_div_tax': cash_div,
                'payout_ratio': payout_ratio,
            }
        elif proc == '预案' and latest_plan is None and cash_div is not None and cash_div > 0:
            latest_plan = {
                'end_date': end_d,
                'ann_date': str(r.get('ann_date', '')),
                'cash_div_tax': cash_div,
            }

    if latest_year:
        result['latest_year'] = latest_year
    if latest_plan:
        result['latest_plan'] = latest_plan

    # 6. 连续分红年数：从 history 中找"实施"且金额 >0 的连续年度数
    consecutive = 0
    last_year_int: Optional[int] = None
    for h in history:
        end_d = h['end_date']
        if h.get('div_proc') == '实施' and (h.get('cash_div_tax') or 0) > 0:
            try:
                yr = int(end_d[:4])
            except (ValueError, TypeError):
                break
            if last_year_int is None:
                consecutive = 1
                last_year_int = yr
            elif last_year_int - yr == 1:
                consecutive += 1
                last_year_int = yr
            else:
                break
    if consecutive > 0:
        result['consecutive_years'] = consecutive

    # 7. 截断 history 到最近 6 年；仅保留实施/预案两类
    if history:
        result['history'] = [h for h in history if h.get('div_proc') in ('实施', '预案')][:6]

    return result


# ------------------------------------------------------------------
# 三C、卖方盈利预测（券商一致预期）
# ------------------------------------------------------------------

# 清洗规则：report_rc.tp 字段单位异常（实际为市值/总股本的衍生值，数量级 10^6）。
# 目标价应从 min_price 取（数量级合理，如 7.78 / 5.41 / 6.00）。
# 异常保护：若 min_price 缺失或 > 当前价 × 4（机构目标价不会超过当前价 4 倍），剔除该目标价。
_ANALYST_TARGET_PRICE_MAX_MULTIPLIER = 4.0

# 评级归类（A 股研报"增持/买入/跑赢行业"等大量同义表述，统一 4 档便于 AI 解读）
_ANALYST_RATING_BULLISH = ('买入', '强烈推荐', '推荐', 'Strong Buy', 'Buy')
_ANALYST_RATING_OVERWEIGHT = ('增持', '谨慎推荐', '跑赢行业', '优于大市', 'Outperform')
_ANALYST_RATING_NEUTRAL = ('中性', '持有', '观望', 'Hold', 'Neutral')
_ANALYST_RATING_BEARISH = ('减持', '卖出', '跑输行业', '弱于大市', 'Sell', 'Underperform')


def _classify_rating(rating: Optional[str]) -> str:
    if not rating:
        return '未知'
    r = str(rating).strip()
    for kw in _ANALYST_RATING_BULLISH:
        if kw in r:
            return '买入'
    for kw in _ANALYST_RATING_OVERWEIGHT:
        if kw in r:
            return '增持'
    for kw in _ANALYST_RATING_NEUTRAL:
        if kw in r:
            return '中性'
    for kw in _ANALYST_RATING_BEARISH:
        if kw in r:
            return '减持/卖出'
    return '未知'


async def get_analyst_consensus(ts_code: str) -> Dict:
    """
    收集近 60 日券商卖方盈利预测与评级共识，作为"第三方独立视角"注入数据层。

    用途：解决"LLM 看不到机构评级分歧"这一系统性盲区。中国建筑案例中，机构
    给出的是"买入"评级共识（目标价 5.41~7.78 元，当前价 4.88 元），但仅依赖
    PE 分位 + 业绩 YoY 的三专家系统无法感知这一信息。

    返回结构:
      {
        'report_count': 21,                    # 近 60 日总报告数
        'org_count': 7,                        # 覆盖机构数
        'window_days': 60,
        'latest_report_date': 'YYYYMMDD',      # 最近一份报告日
        'rating_distribution': {               # 评级分布（归类后）
          '买入': 5, '增持': 2, '中性': 0, '减持/卖出': 0, '未知': 0,
        },
        'eps_consensus': [                     # 按预测年度聚合的一致预期 EPS
          {
            'quarter_key': '2026Q4',          # Tushare 口径：YYYYQ4 = 全年预测
            'count': 7, 'median': 0.94, 'min': 0.88, 'max': 1.05,
          },
          ...
        ],
        'target_price_latest': [               # 每家机构最新一份报告的目标价
          {'org_name': '中信建投', 'rating': '买入', 'target_price': 7.78,
           'report_date': 'YYYYMMDD', 'upside_pct': 59.4},
          ...
        ],
        'target_price_stats': {
          'median': 6.45, 'min': 5.41, 'max': 7.78, 'count': 5,
          'median_upside_pct': 32.2,           # 中位目标价相对当前价的上涨空间 %
        },
      }
    数据缺失/全部异常时返回 {} 兼容空状态。
    """
    from app.repositories.report_rc_repository import ReportRcRepository
    from app.repositories.stock_daily_repository import StockDailyRepository

    today = datetime.now()
    start_60d = (today - timedelta(days=60)).strftime('%Y%m%d')
    end_today = today.strftime('%Y%m%d')

    rows, daily_df = await asyncio.gather(
        asyncio.to_thread(
            ReportRcRepository().get_by_date_range,
            start_60d, end_today, None, ts_code, None, 1, 500,
        ),
        asyncio.to_thread(
            StockDailyRepository().get_by_code_and_date_range,
            ts_code,
            (today - timedelta(days=14)).strftime('%Y-%m-%d'),
            today.strftime('%Y-%m-%d'),
        ),
    )

    if not rows:
        return {}

    current_price: Optional[float] = None
    if daily_df is not None and not daily_df.empty:
        current_price = safe_float(daily_df.iloc[-1].get('close'))

    # 1. 评级分布：按 (org_name) 取最新一份报告的评级（避免一家机构一天多条重复计票）
    latest_report_per_org: Dict[str, Dict] = {}
    for r in rows:
        org = r.get('org_name')
        if not org:
            continue
        rdate = str(r.get('report_date', ''))
        existing = latest_report_per_org.get(org)
        if existing is None or rdate > str(existing.get('report_date', '')):
            latest_report_per_org[org] = r

    rating_distribution: Dict[str, int] = {
        '买入': 0, '增持': 0, '中性': 0, '减持/卖出': 0, '未知': 0,
    }
    for r in latest_report_per_org.values():
        key = _classify_rating(r.get('rating'))
        rating_distribution[key] = rating_distribution.get(key, 0) + 1

    # 2. EPS 一致预期：按 quarter 分组（quarter 形如 '2026Q4' 表示 2026 年全年预测）
    #    同一机构同一 quarter 取最新 report_date
    latest_eps: Dict[tuple, Dict] = {}
    for r in rows:
        org = r.get('org_name')
        q = r.get('quarter')
        eps_val = safe_float(r.get('eps'))
        if not org or not q or eps_val is None:
            continue
        key = (org, q)
        existing = latest_eps.get(key)
        rdate = str(r.get('report_date', ''))
        if existing is None or rdate > str(existing.get('report_date', '')):
            latest_eps[key] = r

    eps_by_quarter: Dict[str, list] = {}
    for (_, q), r in latest_eps.items():
        eps_val = safe_float(r.get('eps'))
        if eps_val is not None:
            eps_by_quarter.setdefault(q, []).append(eps_val)

    eps_consensus: list = []
    for q in sorted(eps_by_quarter.keys()):
        vals = sorted(eps_by_quarter[q])
        if not vals:
            continue
        eps_consensus.append({
            'quarter_key': q,
            'count': len(vals),
            'median': round(vals[len(vals) // 2], 3),
            'min': round(vals[0], 3),
            'max': round(vals[-1], 3),
        })

    # 3. 目标价：每家机构取最新一份报告中有效的 min_price
    target_prices: list = []
    for org, r in latest_report_per_org.items():
        tp = safe_float(r.get('min_price'))
        if tp is None or tp <= 0:
            continue
        # 异常保护：目标价不应 > 当前价 × MAX_MULTIPLIER（否则必然是单位错误或数据污染）
        if current_price and current_price > 0 and tp > current_price * _ANALYST_TARGET_PRICE_MAX_MULTIPLIER:
            continue
        upside = None
        if current_price and current_price > 0:
            upside = round((tp - current_price) / current_price * 100, 1)
        target_prices.append({
            'org_name': org,
            'rating': _classify_rating(r.get('rating')),
            'target_price': round(tp, 2),
            'report_date': str(r.get('report_date', '')),
            'upside_pct': upside,
        })
    target_prices.sort(key=lambda x: x['target_price'], reverse=True)

    tp_vals = sorted(x['target_price'] for x in target_prices)
    target_price_stats = None
    if tp_vals:
        median_tp = tp_vals[len(tp_vals) // 2]
        median_upside = None
        if current_price and current_price > 0:
            median_upside = round((median_tp - current_price) / current_price * 100, 1)
        target_price_stats = {
            'count': len(tp_vals),
            'median': round(median_tp, 2),
            'min': round(tp_vals[0], 2),
            'max': round(tp_vals[-1], 2),
            'median_upside_pct': median_upside,
        }

    # 4. 最新报告日
    latest_report_date = max((str(r.get('report_date', '')) for r in rows), default='')

    return {
        'report_count': len(rows),
        'org_count': len(latest_report_per_org),
        'window_days': 60,
        'latest_report_date': latest_report_date,
        'current_price_ref': current_price,
        'rating_distribution': rating_distribution,
        'eps_consensus': eps_consensus,
        'target_price_latest': target_prices,
        'target_price_stats': target_price_stats,
    }


# ------------------------------------------------------------------
# 四、财报与敏感公告
# ------------------------------------------------------------------

async def get_financial_reports(ts_code: str) -> Dict:
    from app.repositories.disclosure_date_repository import DisclosureDateRepository
    from app.repositories.forecast_repository import ForecastRepository
    from app.repositories.express_repository import ExpressRepository

    today = datetime.now()
    end_yyyymmdd = today.strftime('%Y%m%d')
    # 业绩预告/快报：拉近 24 个月，覆盖至少 2 个同期报告，便于做同比/环比定性。
    # 多数公司年内仅 1-2 次预告，12 个月窗口经常只剩 1 条无法对比。
    start_24m = (today - timedelta(days=730)).strftime('%Y%m%d')

    disclosures, forecasts, express_list = await asyncio.gather(
        asyncio.to_thread(DisclosureDateRepository().get_by_ts_code, ts_code, 8),
        asyncio.to_thread(
            ForecastRepository().get_by_date_range,
            start_24m, end_yyyymmdd, ts_code, None, None, 8
        ),
        asyncio.to_thread(
            ExpressRepository().get_by_code, ts_code, start_24m, end_yyyymmdd, 8
        ),
    )

    result: Dict[str, Any] = {}
    if disclosures:
        cutoff = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
        filtered = [r for r in disclosures if str(r.get('end_date', '')) >= cutoff][:5]
        result['disclosures'] = [
            {
                'end_date': str(r.get('end_date', '')),
                'pre_date': str(r.get('pre_date', '')),
                'actual_date': str(r.get('actual_date', '') or ''),
                'modify_date': str(r.get('modify_date', '') or ''),
            }
            for r in filtered
        ]

    if forecasts:
        result['forecasts'] = [
            {
                'ann_date': str(r.get('ann_date', '')),
                'end_date': str(r.get('end_date', '')),
                'type': r.get('type', '') or '',
                'p_change_min': safe_float(r.get('p_change_min')),
                'p_change_max': safe_float(r.get('p_change_max')),
                'net_profit_min': safe_float(r.get('net_profit_min')),
                'net_profit_max': safe_float(r.get('net_profit_max')),
                'change_reason': (r.get('change_reason') or r.get('summary') or '')[:200],
            }
            for r in forecasts
        ]

        # 最新一份预告：计算 Forward PE 区间（中值/下限/上限），判断股价是否已透支预期
        # net_profit_min/max 单位：万元；total_mv 单位：万元 → 直接相除即为 PE 倍数
        latest = result['forecasts'][0]
        np_min = latest.get('net_profit_min')
        np_max = latest.get('net_profit_max')
        if np_min and np_max and np_min > 0 and np_max > 0:
            try:
                from app.repositories.daily_basic_repository import DailyBasicRepository
                start_30 = (today - timedelta(days=30)).strftime('%Y%m%d')
                basic_rows = await asyncio.to_thread(
                    DailyBasicRepository().get_by_code_and_date_range,
                    ts_code, start_30, end_yyyymmdd, 1
                )
                total_mv = (
                    safe_float(basic_rows[0].get('total_mv'))
                    if basic_rows else None
                )
                pe_ttm = (
                    safe_float(basic_rows[0].get('pe_ttm'))
                    if basic_rows else None
                )
                if total_mv and total_mv > 0:
                    np_mid = (np_min + np_max) / 2
                    fwd_pe_low = round(total_mv / np_max, 2)   # 用最高净利得到最低 PE
                    fwd_pe_high = round(total_mv / np_min, 2)  # 用最低净利得到最高 PE
                    fwd_pe_mid = round(total_mv / np_mid, 2)
                    result['forecast_forward_pe'] = {
                        'forecast_ann_date': latest.get('ann_date'),
                        'forecast_end_date': latest.get('end_date'),
                        'np_min_yi': round(np_min / 10000, 2),  # 万元 → 亿元
                        'np_max_yi': round(np_max / 10000, 2),
                        'np_mid_yi': round(np_mid / 10000, 2),
                        'total_mv_yi': round(total_mv / 10000, 2),
                        'forward_pe_low': fwd_pe_low,    # 最乐观（按预告净利上限）
                        'forward_pe_mid': fwd_pe_mid,    # 中值
                        'forward_pe_high': fwd_pe_high,  # 最保守（按预告净利下限）
                        'current_pe_ttm': pe_ttm,
                    }
            except Exception as e:
                logger.warning(f"计算业绩预告 Forward PE 失败: {e}")

    if express_list:
        result['express'] = [
            {
                'ann_date': str(r.get('ann_date', '')),
                'end_date': str(r.get('end_date', '')),
                'revenue': safe_float(r.get('revenue')),
                'n_income': safe_float(r.get('n_income')),
                'diluted_eps': safe_float(r.get('diluted_eps')),
                'diluted_roe': safe_float(r.get('diluted_roe')),
                'yoy_net_profit': safe_float(r.get('yoy_net_profit')),
                'yoy_sales': safe_float(r.get('yoy_sales')),
            }
            for r in express_list
        ]

    return result


# ------------------------------------------------------------------
# 五、风险警示
# ------------------------------------------------------------------

async def get_risk_alerts(ts_code: str) -> Dict:
    from app.repositories.stk_alert_repository import StkAlertRepository
    from app.repositories.pledge_stat_repository import PledgeStatRepository

    alerts, pledge_data = await asyncio.gather(
        asyncio.to_thread(StkAlertRepository().get_by_stock, ts_code),
        asyncio.to_thread(PledgeStatRepository().get_by_stock, ts_code),
    )

    result: Dict[str, Any] = {}

    if alerts:
        result['alerts'] = [
            {
                'start_date': str(r.get('start_date', '')),
                'end_date': str(r.get('end_date', '')),
                'type': r.get('type', ''),
            }
            for r in alerts[:5]
        ]

    if pledge_data:
        p = pledge_data[0]
        result['pledge'] = {
            'end_date': str(p.get('end_date', '')),
            'pledge_count': p.get('pledge_count'),
            'pledge_ratio': safe_float(p.get('pledge_ratio')),
            'unrest_pledge': safe_float(p.get('unrest_pledge')),
        }

    return result


# ------------------------------------------------------------------
# 六、神奇九转
# ------------------------------------------------------------------

async def get_nine_turn(ts_code: str) -> Dict:
    from app.repositories.stk_nineturn_repository import StkNineturnRepository

    today = datetime.now()
    start_dash = (today - timedelta(days=30)).strftime('%Y-%m-%d')
    end_dash = today.strftime('%Y-%m-%d')

    rows = await asyncio.to_thread(
        StkNineturnRepository().get_by_date_range,
        start_date=start_dash,
        end_date=end_dash,
        ts_code=ts_code,
        sort_by='trade_date',
        sort_order='desc',
        limit=10,
    )

    if not rows:
        return {}

    result: Dict[str, Any] = {}

    latest = rows[0]
    result['latest_date'] = latest.get('trade_date', '')[:10]
    result['up_count'] = latest.get('up_count')
    result['down_count'] = latest.get('down_count')
    result['nine_up_turn'] = latest.get('nine_up_turn')
    result['nine_down_turn'] = latest.get('nine_down_turn')

    # 只取真正的"触发日"：count 首次达到 9 的那一天（即 count==9）。
    # count>9 是触发后序列继续延伸，nine_up_turn 字段虽仍为 '+9' 但属同一次信号的延续，不是新触发。
    initial_signals = []
    for r in rows:
        up_c = r.get('up_count')
        down_c = r.get('down_count')
        if r.get('nine_up_turn') == '+9' and up_c is not None and int(up_c) == 9:
            initial_signals.append({'date': r.get('trade_date', '')[:10], 'type': '九转见顶'})
        elif r.get('nine_down_turn') == '-9' and down_c is not None and int(down_c) == 9:
            initial_signals.append({'date': r.get('trade_date', '')[:10], 'type': '九转见底'})
    result['recent_signals'] = initial_signals

    # 序列是否仍在延续：触发后未断（count > 9）
    up_c_latest = latest.get('up_count')
    down_c_latest = latest.get('down_count')
    if latest.get('nine_up_turn') == '+9' and up_c_latest is not None and int(up_c_latest) > 9:
        result['extension_days'] = int(up_c_latest) - 9
        result['extension_direction'] = 'up'
    elif latest.get('nine_down_turn') == '-9' and down_c_latest is not None and int(down_c_latest) > 9:
        result['extension_days'] = int(down_c_latest) - 9
        result['extension_direction'] = 'down'

    return result


# ------------------------------------------------------------------
# 七、集合竞价（盘前/盘后）
# ------------------------------------------------------------------

async def get_auction(ts_code: str) -> Dict:
    """查询最近一个交易日的开盘/收盘集合竞价数据，计算跳空幅度与成交占比。"""
    from app.repositories.stk_auction_o_repository import StkAuctionORepository
    from app.repositories.stk_auction_c_repository import StkAuctionCRepository
    from app.repositories.stock_daily_repository import StockDailyRepository

    today = datetime.now()
    start_14d = (today - timedelta(days=14)).strftime('%Y%m%d')
    end_today = today.strftime('%Y%m%d')
    start_dash = (today - timedelta(days=14)).strftime('%Y-%m-%d')
    end_dash = today.strftime('%Y-%m-%d')

    auction_o_rows, auction_c_rows, daily_df = await asyncio.gather(
        asyncio.to_thread(
            StkAuctionORepository().get_by_date_range,
            start_14d, end_today, ts_code, 5, 0,
        ),
        asyncio.to_thread(
            StkAuctionCRepository().get_by_date_range,
            start_14d, end_today, ts_code, 5, 0,
        ),
        asyncio.to_thread(
            StockDailyRepository().get_by_code_and_date_range,
            ts_code, start_dash, end_dash,
        ),
    )

    result: Dict[str, Any] = {}

    # 构建 trade_date → (close, vol) 字典
    daily_map: Dict[str, Dict[str, Optional[float]]] = {}
    if daily_df is not None and not daily_df.empty:
        for idx, row in daily_df.iterrows():
            date_key = str(idx)[:10].replace('-', '')
            daily_map[date_key] = {
                'close': safe_float(row.get('close')),
                'volume': safe_float(row.get('volume')),
            }

    if auction_o_rows:
        latest_o = auction_o_rows[0]
        auction_date = str(latest_o.get('trade_date') or '')
        auction_open = safe_float(latest_o.get('open'))
        auction_vol = safe_float(latest_o.get('vol'))
        auction_amount = safe_float(latest_o.get('amount'))

        # 前一交易日收盘 → 跳空幅度
        sorted_dates = sorted(daily_map.keys())
        prev_close = None
        if auction_date in sorted_dates:
            idx_here = sorted_dates.index(auction_date)
            if idx_here > 0:
                prev_close = daily_map[sorted_dates[idx_here - 1]].get('close')
        elif sorted_dates:
            earlier = [d for d in sorted_dates if d < auction_date]
            if earlier:
                prev_close = daily_map[earlier[-1]].get('close')

        gap_pct = None
        if prev_close and auction_open:
            gap_pct = round((auction_open - prev_close) / prev_close * 100, 2)

        result['open_auction'] = {
            'trade_date': auction_date,
            'open': auction_open,
            'vol': auction_vol,
            'amount': auction_amount,
            'gap_pct': gap_pct,
            'prev_close': prev_close,
        }

    if auction_c_rows:
        latest_c = auction_c_rows[0]
        auction_date_c = str(latest_c.get('trade_date') or '')
        auction_close = safe_float(latest_c.get('close'))
        auction_vol_c = safe_float(latest_c.get('vol'))
        auction_amount_c = safe_float(latest_c.get('amount'))

        # 尾盘竞价成交占当日总成交比例（stock_daily.volume 与 auction.vol 单位均为"股"）
        day_vol = daily_map.get(auction_date_c, {}).get('volume')
        vol_share_pct = None
        if day_vol and auction_vol_c:
            vol_share_pct = round(auction_vol_c / day_vol * 100, 2)

        result['close_auction'] = {
            'trade_date': auction_date_c,
            'close': auction_close,
            'vol': auction_vol_c,
            'amount': auction_amount_c,
            'vol_share_pct': vol_share_pct,
        }

    return result


# ------------------------------------------------------------------
# 八、聪明资金（融资融券 + 龙虎榜）
# ------------------------------------------------------------------

# 龙虎榜席位性质识别（用于把营业部名翻译成"游资 / 机构 / 量化 / 北向 / 散户主战场"）
# 名单为公开常识性归类（一线/二线游资席位、量化席位等）。命名命中后才打标签，不命中保留原名。
_SEAT_TAGS = {
    # 北向 / ETF 通道
    '深股通专用': '北向通道',
    '沪股通专用': '北向通道',
    # 公认机构席位
    '机构专用': '机构席位',
}

# 子串匹配的知名席位（按"子串 → 标签"登记，命中即打标签）
# 游资席位主要依据市场公开共识，未必完全代表当前资金主体；仅作定性参考
_SEAT_SUBSTRING_TAGS = [
    ('深圳福田金田路证券', '一线游资·深圳金田路系'),
    ('深圳益田路荣超商务中心', '一线游资·深圳益田路系'),
    ('上海长宁区江苏路证券', '一线游资·上海溧阳路（章盟主/作手系）'),
    ('上海淮海中路证券', '一线游资·上海淮海中路'),
    ('上海茅台路证券', '一线量化席位·华鑫茅台路'),
    ('北京上地', '知名游资·北京上地'),
    ('北京陈家湾', '知名游资·北京陈家湾'),
    ('拉萨东环路', '西藏游资·拉萨东环路'),
    ('拉萨团结路', '西藏游资·拉萨团结路'),
    ('拉萨北京西路', '西藏游资·拉萨北京西路'),
    ('拉萨朵森格路', '西藏游资·朵森格路'),
    ('青岛分公司', '量化/对冲席位·中信山东青岛'),
    ('厦门美湖路', '知名游资·厦门美湖路'),
    ('成都东城根上街', '成都游资·东城根上街'),
    ('杭州庆春路', '浙系游资·杭州庆春路'),
    ('宁波解放南路', '宁波系游资·宁波解放南路'),
]


def _classify_seat(exalter: str) -> str:
    """席位名称 → 性质标签。未命中返回空字符串（保留原名即可）。"""
    if not exalter:
        return ''
    if exalter in _SEAT_TAGS:
        return _SEAT_TAGS[exalter]
    if '机构专用' in exalter:
        return '机构席位'
    if '深股通专用' in exalter or '沪股通专用' in exalter:
        return '北向通道'
    for sub, tag in _SEAT_SUBSTRING_TAGS:
        if sub in exalter:
            return tag
    return ''


async def get_smart_money(ts_code: str) -> Dict:
    """采集"聪明资金"维度：
    1) 融资融券 5 日明细 + 净额变动方向（衡量杠杆资金的进出）
    2) 龙虎榜 60 日内的所有上榜事件，含席位明细及性质标记
    """
    from app.repositories.margin_detail_repository import MarginDetailRepository
    from app.repositories.top_list_repository import TopListRepository
    from app.repositories.top_inst_repository import TopInstRepository

    today = datetime.now()
    end_yyyymmdd = today.strftime('%Y%m%d')
    start_60d = (today - timedelta(days=60)).strftime('%Y%m%d')
    start_10d = (today - timedelta(days=15)).strftime('%Y%m%d')

    # 并行查询（Repository 的 sort_by 白名单不含 trade_date，需在 collector 端再排序）
    margin_rows, top_list_rows = await asyncio.gather(
        asyncio.to_thread(
            MarginDetailRepository().get_by_date_range,
            start_10d, end_yyyymmdd, ts_code, 10, 0, None, None,
        ),
        asyncio.to_thread(
            TopListRepository().get_by_date_range,
            start_60d, end_yyyymmdd, ts_code, 20, 0, None, 'desc',
        ),
    )

    # 强制按 trade_date desc 本地排序（最新在前）
    if margin_rows:
        margin_rows = sorted(
            margin_rows,
            key=lambda r: str(r.get('trade_date') or '')[:10].replace('-', ''),
            reverse=True,
        )
    if top_list_rows:
        top_list_rows = sorted(
            top_list_rows,
            key=lambda r: str(r.get('trade_date') or '')[:8],
            reverse=True,
        )

    result: Dict[str, Any] = {}

    # ---- 融资融券 ----
    if margin_rows:
        latest = margin_rows[0]
        # rzye/rqye/rzrqye 单位：元
        rzye = safe_float(latest.get('rzye'))
        rqye = safe_float(latest.get('rqye'))
        rzrqye = safe_float(latest.get('rzrqye'))

        # 5 日累计净买入（融资买入额 - 融资偿还额）
        net_5d = 0.0
        rzye_change_5d = None
        for r in margin_rows[:5]:
            buy = safe_float(r.get('rzmre')) or 0
            repay = safe_float(r.get('rzche')) or 0
            net_5d += (buy - repay)
        if len(margin_rows) >= 5:
            curr_rzye = safe_float(margin_rows[0].get('rzye')) or 0
            prev_rzye = safe_float(margin_rows[4].get('rzye')) or 0
            if prev_rzye > 0:
                rzye_change_5d = round((curr_rzye - prev_rzye) / prev_rzye * 100, 2)

        latest_date_str = format_date_dashed(latest.get('trade_date'))
        result['margin'] = {
            'trade_date': latest_date_str,
            'days_lag': days_since(latest_date_str, today.date()),
            'rzye': rzye,                     # 元，融资余额
            'rqye': rqye,                     # 元，融券余额
            'rzrqye': rzrqye,                 # 元，两融余额
            'net_buy_5d': net_5d,             # 元，5 日融资净买入
            'rzye_change_5d_pct': rzye_change_5d,
            'detail': [
                {
                    'trade_date': str(r.get('trade_date') or '')[:10].replace('-', ''),
                    'rzye': safe_float(r.get('rzye')),
                    'rzmre': safe_float(r.get('rzmre')),
                    'rzche': safe_float(r.get('rzche')),
                    'net_buy': (safe_float(r.get('rzmre')) or 0) - (safe_float(r.get('rzche')) or 0),
                }
                for r in margin_rows[:5]
            ],
        }

    # ---- 龙虎榜（事件 + 席位明细）----
    if top_list_rows:
        events = []
        for ev in top_list_rows[:5]:  # 最多取近 5 次上榜
            ev_date = str(ev.get('trade_date') or '')[:8]
            # 拉该日席位明细
            insts = await asyncio.to_thread(
                TopInstRepository().get_by_date_range,
                ev_date, ev_date, ts_code, None, 1, 50,
                'net_buy', 'desc',
            )
            buyers = []
            sellers = []
            for inst in insts or []:
                exalter = inst.get('exalter', '') or ''
                tag = _classify_seat(exalter)
                row = {
                    'exalter': exalter,
                    'seat_tag': tag,
                    'buy': safe_float(inst.get('buy')) or 0,
                    'sell': safe_float(inst.get('sell')) or 0,
                    'net_buy': safe_float(inst.get('net_buy')) or 0,
                }
                if str(inst.get('side', '')) == '0':
                    buyers.append(row)
                else:
                    sellers.append(row)
            buyers.sort(key=lambda x: x['net_buy'], reverse=True)
            sellers.sort(key=lambda x: x['net_buy'])
            events.append({
                'trade_date': ev_date,
                'pct_change': safe_float(ev.get('pct_change')),
                'turnover_rate': safe_float(ev.get('turnover_rate')),
                'amount': safe_float(ev.get('amount')),         # 元
                'l_buy': safe_float(ev.get('l_buy')),           # 元
                'l_sell': safe_float(ev.get('l_sell')),         # 元
                'l_amount': safe_float(ev.get('l_amount')),     # 元（前五合计成交）
                'net_amount': safe_float(ev.get('net_amount')), # 元（前五净额）
                'reason': ev.get('reason') or '',
                'buyers': buyers[:5],
                'sellers': sellers[:5],
            })
        result['top_list_events'] = events

    # 明确标记是否上榜（空态语义化，避免 LLM 把"缺字段"误解为"数据缺失"）
    result['on_billboard_60d'] = bool(top_list_rows)
    if not top_list_rows:
        result['top_list_events'] = []

    return result


# ------------------------------------------------------------------
# 九、涨停生态（全市场情绪 + 个股题材身位）
# ------------------------------------------------------------------

async def get_limit_ecology(ts_code: str) -> Dict:
    """采集"涨停生态"维度：
    1) 最近交易日全市场涨停/跌停/炸板家数 → 情绪温度
    2) 连板天梯（最高标板位 + Top 5 连板股票）→ 接力空间
    3) 最强板块（按涨停家数排名 Top 5）→ 主线识别
    4) 个股在最近交易日的涨停状态（板位/炸板次数/封单额）→ 身位
    """
    from app.repositories.limit_list_repository import LimitListRepository
    from app.repositories.limit_step_repository import LimitStepRepository
    from app.repositories.limit_cpt_repository import LimitCptRepository

    # 基准日：limit_list_d 最新日期（非自然日，确保数据存在）
    latest_trade_date = await asyncio.to_thread(
        LimitListRepository().get_latest_trade_date
    )
    if not latest_trade_date:
        return {}

    stats_u, stats_d, stats_z, step_rows, cpt_rows, stock_limit_rows = await asyncio.gather(
        asyncio.to_thread(LimitListRepository().get_statistics, latest_trade_date, latest_trade_date, 'U'),
        asyncio.to_thread(LimitListRepository().get_statistics, latest_trade_date, latest_trade_date, 'D'),
        asyncio.to_thread(LimitListRepository().get_statistics, latest_trade_date, latest_trade_date, 'Z'),
        asyncio.to_thread(LimitStepRepository().get_top_by_nums, latest_trade_date, 20, False),
        asyncio.to_thread(LimitCptRepository().get_top_by_up_nums, latest_trade_date, 10),
        asyncio.to_thread(
            LimitListRepository().get_by_date_range,
            latest_trade_date, latest_trade_date, ts_code, None, 1, 5, None, 'desc',
        ),
        return_exceptions=True,
    )

    # 解包（失败的子查询回退空）
    def _unwrap(v, default):
        if isinstance(v, Exception):
            logger.warning(f"[limit_ecology] 子查询异常: {type(v).__name__}: {v}")
            return default
        return v

    stats_u = _unwrap(stats_u, {})
    stats_d = _unwrap(stats_d, {})
    stats_z = _unwrap(stats_z, {})
    step_rows = _unwrap(step_rows, []) or []
    cpt_rows = _unwrap(cpt_rows, []) or []
    stock_limit_rows = _unwrap(stock_limit_rows, []) or []

    # 市场情绪温度
    market = {
        'trade_date': latest_trade_date,
        'up_count': int(stats_u.get('total_count') or 0),
        'down_count': int(stats_d.get('total_count') or 0),
        'broken_count': int(stats_z.get('total_count') or 0),  # 炸板
    }
    broken_ratio = None
    if (market['up_count'] + market['broken_count']) > 0:
        broken_ratio = round(
            market['broken_count'] / (market['up_count'] + market['broken_count']) * 100, 1
        )
    market['broken_ratio_pct'] = broken_ratio  # 炸板率 = 炸板 / (涨停 + 炸板)

    # 连板天梯：最高标板位 + Top 5
    ladder = []
    max_nums = 0
    for r in step_rows[:5]:
        nums = int(r.get('nums') or 0)
        if nums > max_nums:
            max_nums = nums
        ladder.append({
            'ts_code': r.get('ts_code') or '',
            'name': r.get('name') or '',
            'nums': nums,
        })

    # 最强板块天梯：Top 5
    top_boards = []
    for r in cpt_rows[:5]:
        top_boards.append({
            'ts_code': r.get('ts_code') or '',
            'name': r.get('name') or '',
            'up_nums': int(r.get('up_nums') or 0),
            'cons_nums': int(r.get('cons_nums') or 0),
            'pct_change': safe_float(r.get('pct_chg')),
            'rank': int(r.get('rank') or 0) if r.get('rank') is not None else None,
        })

    # 个股涨停状态（如不在榜则为 None）
    stock_limit = None
    if stock_limit_rows:
        row = stock_limit_rows[0]
        up_stat = str(row.get('up_stat') or '')  # 如 "2/3"
        # 解析连板数（up_stat 前半部分）
        limit_streak = None
        if '/' in up_stat:
            try:
                limit_streak = int(up_stat.split('/')[0])
            except (ValueError, IndexError):
                pass
        stock_limit = {
            'limit_type': row.get('limit_type') or '',          # U / D / Z
            'up_stat': up_stat,                                  # 连板状态 "N板/M日内涨停次数"
            'limit_streak': limit_streak,                        # 当前连板数 N
            'limit_times': int(row.get('limit_times') or 0),    # 当日涨停次数（触板含炸板）
            'open_times': int(row.get('open_times') or 0),      # 炸板次数
            'fd_amount': safe_float(row.get('fd_amount')),      # 封单金额（元）
            'first_time': str(row.get('first_time') or ''),     # 首次涨停时间
            'last_time': str(row.get('last_time') or ''),       # 最后涨停时间
            'pct_change': safe_float(row.get('pct_chg')),
        }

    return {
        'trade_date': latest_trade_date,
        'market_sentiment': market,
        'max_ladder_nums': max_nums,                      # 全市场最高标板位
        'ladder_top5': ladder,
        'top_boards': top_boards,
        'stock_limit_status': stock_limit,
    }


# ------------------------------------------------------------------
# 十、个股历史涨停基因（近 60 日打板记录 + T+1 溢价统计）
# ------------------------------------------------------------------

async def get_limit_history(ts_code: str) -> Dict:
    """采集个股近 60 日涨停历史：
    1) 涨停次数（U 类型，不含炸板）
    2) 每次涨停次日的 pct_change（T+1 溢价）→ 接力成功率
    3) 最近一次涨停距今几交易日
    """
    from app.repositories.limit_list_repository import LimitListRepository
    from app.repositories.stock_daily_repository import StockDailyRepository
    from app.repositories.trading_calendar_repository import TradingCalendarRepository

    # 多取 90 个日历日，保证覆盖 60 个交易日
    today = datetime.now()
    today_str = today.strftime('%Y%m%d')
    start_90d = (today - timedelta(days=90)).strftime('%Y%m%d')

    # 近 60 日涨停记录（U 类型）
    limit_up_rows = await asyncio.to_thread(
        LimitListRepository().get_by_date_range,
        start_90d, today_str, ts_code, 'U', 1, 100, None, 'desc',
    )
    limit_up_rows = limit_up_rows or []

    if not limit_up_rows:
        return {
            'lookback_days': 60,
            'limit_up_count': 0,
            'last_limit_up_date': None,
            'days_since_last': None,
            't1_stats': None,
            'recent_events': [],
        }

    # 拉个股近 90 日日线，计算每次涨停次日涨跌幅
    # stock_daily.code 存 ts_code 格式（如 '002580.SZ'），不是纯 6 位数字
    start_dash = (today - timedelta(days=90)).strftime('%Y-%m-%d')
    end_dash = today.strftime('%Y-%m-%d')
    daily_df = await asyncio.to_thread(
        StockDailyRepository().get_by_code_and_date_range,
        ts_code, start_dash, end_dash,
    )

    # trade_date (YYYYMMDD) → pct_change
    daily_pct_map: Dict[str, float] = {}
    sorted_trade_dates: list = []
    if daily_df is not None and not daily_df.empty:
        for idx, row in daily_df.iterrows():
            key = str(idx)[:10].replace('-', '')
            pct = safe_float(row.get('pct_change'))
            daily_pct_map[key] = pct
            sorted_trade_dates.append(key)
        sorted_trade_dates.sort()

    # 计算每次涨停次日溢价
    events = []
    t1_returns = []
    for r in limit_up_rows:
        ev_date = str(r.get('trade_date') or '')[:8]
        if not ev_date:
            continue
        # 从交易日列表找 T+1
        next_day_pct = None
        if ev_date in sorted_trade_dates:
            idx = sorted_trade_dates.index(ev_date)
            if idx + 1 < len(sorted_trade_dates):
                next_key = sorted_trade_dates[idx + 1]
                next_day_pct = daily_pct_map.get(next_key)
        if next_day_pct is not None:
            t1_returns.append(next_day_pct)
        events.append({
            'trade_date': ev_date,
            'up_stat': str(r.get('up_stat') or ''),
            'open_times': int(r.get('open_times') or 0),
            'pct_change': safe_float(r.get('pct_chg')),
            't1_pct_change': next_day_pct,
        })

    # T+1 溢价统计
    t1_stats = None
    if t1_returns:
        avg = sum(t1_returns) / len(t1_returns)
        win = sum(1 for x in t1_returns if x > 0)
        t1_stats = {
            'sample_size': len(t1_returns),
            'avg_pct': round(avg, 2),
            'win_rate_pct': round(win / len(t1_returns) * 100, 1),
            'max_pct': round(max(t1_returns), 2),
            'min_pct': round(min(t1_returns), 2),
        }

    # 最近一次涨停距今交易日数
    last_date = events[0]['trade_date'] if events else None
    days_since_last = None
    if last_date:
        # 用交易日历计数
        cal_repo = TradingCalendarRepository()
        try:
            # 包含端点共 N 个交易日（last_date ... today）
            days_since_last = await asyncio.to_thread(
                cal_repo.get_trading_days_between, last_date, today_str
            )
            days_since_last = max(0, (days_since_last or 0) - 1)  # 去掉起点
        except Exception:
            days_since_last = None

    return {
        'lookback_days': 60,
        'limit_up_count': len(limit_up_rows),
        'last_limit_up_date': last_date,
        'days_since_last': days_since_last,
        't1_stats': t1_stats,
        'recent_events': events[:5],  # 最近 5 次
    }


# ------------------------------------------------------------------
# 十一、竞价基准（近 20 日开盘/收盘竞价均值对比）
# ------------------------------------------------------------------

async def get_auction_baseline(ts_code: str) -> Dict:
    """对比当日开盘/收盘集合竞价成交额与近 20 日均值，识别"盘前抢筹/撤单"信号。

    get_auction 只给了绝对数（67 万元），游资无法判断冷热；
    本模块提供近 20 日均值作为对比锚点，得出相对倍数。
    """
    from app.repositories.stk_auction_o_repository import StkAuctionORepository
    from app.repositories.stk_auction_c_repository import StkAuctionCRepository

    # 40 个日历日对应约 25~28 个交易日，保证足够覆盖近 20 个交易日的竞价样本
    today = datetime.now()
    end_yyyymmdd = today.strftime('%Y%m%d')
    start_40d = (today - timedelta(days=40)).strftime('%Y%m%d')

    auction_o_rows, auction_c_rows = await asyncio.gather(
        asyncio.to_thread(
            StkAuctionORepository().get_by_date_range,
            start_40d, end_yyyymmdd, ts_code, 25, 0,
        ),
        asyncio.to_thread(
            StkAuctionCRepository().get_by_date_range,
            start_40d, end_yyyymmdd, ts_code, 25, 0,
        ),
        return_exceptions=True,
    )

    def _unwrap(v):
        if isinstance(v, Exception):
            logger.warning(f"[auction_baseline] 查询异常: {type(v).__name__}: {v}")
            return []
        return v or []

    auction_o_rows = _unwrap(auction_o_rows)
    auction_c_rows = _unwrap(auction_c_rows)

    def _compute_baseline(rows: list) -> Optional[Dict]:
        if not rows:
            return None
        # rows 已按 trade_date desc 排序，第 0 条为最新
        latest = rows[0]
        latest_amount = safe_float(latest.get('amount'))
        # 用"除最新日外"的历史样本（最多 20 个）计算均值
        historical = [safe_float(r.get('amount')) for r in rows[1:21]]
        historical = [x for x in historical if x is not None and x > 0]
        if not historical or latest_amount is None:
            return {
                'trade_date': str(latest.get('trade_date') or '')[:8],
                'latest_amount': latest_amount,
                'baseline_avg': None,
                'sample_size': len(historical),
                'vs_baseline_x': None,
            }
        avg = sum(historical) / len(historical)
        ratio = round(latest_amount / avg, 2) if avg > 0 else None
        return {
            'trade_date': str(latest.get('trade_date') or '')[:8],
            'latest_amount': latest_amount,
            'baseline_avg': round(avg, 2),
            'sample_size': len(historical),
            'vs_baseline_x': ratio,  # 当日 / 近 20 日均值，倍数
        }

    return {
        'open_auction_baseline': _compute_baseline(auction_o_rows),
        'close_auction_baseline': _compute_baseline(auction_c_rows),
    }


# ------------------------------------------------------------------
# 财经快讯 + 新闻联播 — 供个股专家 + CIO Agent 引用事件/宏观面（news_anns Phase 2）
# ------------------------------------------------------------------

async def get_recent_news(ts_code: str, days: int = 7, limit: int = 30) -> Dict:
    """近 N 天与该股关联的财经快讯（元数据不含正文）。

    数据源：`news_flash` 表（AkShare 财新要闻 + 东财个股新闻，GIN 数组索引按
    `related_ts_codes` 反查）。

    输出字段：
      - items: [{publish_time, source, title, summary, url, tags}]
      - total_in_window: int
      - days: int
      - data_available: bool（False 表示该股票在表中无关联快讯）
    """
    from app.repositories.news_flash_repository import NewsFlashRepository

    repo = NewsFlashRepository()
    try:
        rows = await asyncio.to_thread(repo.query_by_stock, ts_code, int(days), int(limit))
    except Exception as e:
        logger.warning(f"[collectors] get_recent_news({ts_code}) 查询失败: {e}")
        return {'items': [], 'total_in_window': 0, 'days': int(days), 'data_available': False}

    if not rows:
        return {'items': [], 'total_in_window': 0, 'days': int(days), 'data_available': False}

    items = [
        {
            'publish_time': r.get('publish_time'),
            'source': r.get('source'),
            'title': r.get('title'),
            'summary': r.get('summary'),
            'url': r.get('url'),
            'tags': r.get('tags', []),
        }
        for r in rows
    ]
    return {
        'items': items,
        'total_in_window': len(items),
        'days': int(days),
        'data_available': True,
    }


async def get_today_cctv_news(date: Optional[str] = None, lookback_days: int = 3, limit: int = 60) -> Dict:
    """指定日期 / 最近 N 天的新闻联播摘要（宏观上下文）。

    数据源：`cctv_news` 表（AkShare `news_cctv` 同步）。
    - 若传 `date`，返回该日全部条目；
    - 若不传，返回近 `lookback_days` 天的全部条目（按日期降序）。

    输出字段：
      - items: [{news_date, seq_no, title, content}]
      - total: int
      - query_type: 'single_day' / 'recent_window'
      - data_available: bool
    """
    from app.repositories.cctv_news_repository import CctvNewsRepository

    repo = CctvNewsRepository()
    try:
        if date:
            rows = await asyncio.to_thread(repo.query_by_date, date, int(limit))
            query_type = 'single_day'
        else:
            from datetime import datetime, timedelta
            end = datetime.now().strftime('%Y-%m-%d')
            start = (datetime.now() - timedelta(days=int(lookback_days))).strftime('%Y-%m-%d')
            rows = await asyncio.to_thread(
                repo.query_by_filters,
                start_date=start, end_date=end, keyword=None,
                page=1, page_size=int(limit),
                sort_by='news_date', sort_order='desc',
            )
            query_type = 'recent_window'
    except Exception as e:
        logger.warning(f"[collectors] get_today_cctv_news 查询失败: {e}")
        return {'items': [], 'total': 0, 'query_type': 'error', 'data_available': False}

    if not rows:
        return {'items': [], 'total': 0, 'query_type': query_type, 'data_available': False}

    return {
        'items': rows,
        'total': len(rows),
        'query_type': query_type,
        'data_available': True,
    }


# ------------------------------------------------------------------
# 公司公告 — 供个股专家 + CIO Agent 引用事件面（news_anns Phase 1）
# ------------------------------------------------------------------

async def get_recent_announcements(ts_code: str, days: int = 30, limit: int = 20) -> Dict:
    """近 N 天的公司公告元数据（title + date + type + url），不含正文。

    数据源：`stock_anns` 表（由 AkShare 同步，见 news_anns_tasks）。

    输出字段：
      - items: [{ann_date, anno_type, title, url, has_content}]
      - total_in_window: int
      - days: int（实际回看天数）
      - latest_date / earliest_date: 表中数据的最新/最早公告日
      - data_available: bool（False 表示该股票在表中无数据，可能尚未被同步过）
    """
    from app.repositories.stock_anns_repository import StockAnnsRepository

    repo = StockAnnsRepository()
    try:
        rows = await asyncio.to_thread(repo.query_by_stock, ts_code, int(days), int(limit))
    except Exception as e:
        logger.warning(f"[collectors] get_recent_announcements({ts_code}) 查询失败: {e}")
        return {'items': [], 'total_in_window': 0, 'days': int(days), 'data_available': False}

    if not rows:
        return {'items': [], 'total_in_window': 0, 'days': int(days), 'data_available': False}

    items = [
        {
            'ann_date': r.get('ann_date'),
            'anno_type': r.get('anno_type'),
            'title': r.get('title'),
            'url': r.get('url'),
            'has_content': r.get('has_content', False),
        }
        for r in rows
    ]
    dates = [r.get('ann_date') for r in rows if r.get('ann_date')]
    return {
        'items': items,
        'total_in_window': len(items),
        'days': int(days),
        'latest_date': max(dates) if dates else None,
        'earliest_date': min(dates) if dates else None,
        'data_available': True,
    }


# ------------------------------------------------------------------
# 宏观经济指标 — 供宏观风险专家 + CIO Agent 引用量化底座（news_anns Phase 3）
# ------------------------------------------------------------------

async def get_macro_snapshot(lookback_months: int = 0) -> Dict:
    """宏观经济指标快照（最新值 + 可选近 N 月序列）。

    数据源：`macro_indicators` 表（由 AkShare 同步，见 macro_sync_service）。
    覆盖：CPI / PPI / PMI(制造业 + 非制造业) / M2 / 新增社融 / GDP / Shibor(O/N + 1W + 1M)

    Args:
        lookback_months: 序列回看月数。默认 0 = 只取 latest（CIO Tool 场景）；
            API `/snapshot` 端点传 12 以同时拉最近 12 个月序列供前端画图。

    输出字段：
      - latest: { indicator_code: { value, yoy, mom, period_date, publish_date, lag_days } }
      - series: { indicator_code: [最近 lookback_months 条，降序] }，lookback_months<=0 时为空 dict
      - data_available: bool
    """
    from app.services.news_anns import MacroSyncService

    svc = MacroSyncService()
    try:
        snapshot = await svc.get_macro_snapshot(int(lookback_months))
    except Exception as e:
        logger.warning(f"[collectors] get_macro_snapshot 查询失败: {e}")
        return {'latest': {}, 'series': {}, 'data_available': False}

    if not snapshot.get('latest'):
        return {'latest': {}, 'series': {}, 'data_available': False, 'lookback_months': int(lookback_months)}

    return {
        'latest': snapshot.get('latest') or {},
        'series': snapshot.get('series') or {},
        'indicators': snapshot.get('indicators') or [],
        'lookback_months': int(lookback_months),
        'data_available': True,
    }
