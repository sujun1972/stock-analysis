"""
数据收集模块

从本地数据库收集各维度数据：基础盘面、资金流向、股东信息、财报、风险、神奇九转。
技术指标收集见 technical.py。
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from loguru import logger

from .formatters import safe_float


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
    pe_start_3y = (today - timedelta(days=365 * 3)).strftime('%Y%m%d')
    start_365d = (today - timedelta(days=365)).strftime('%Y%m%d')

    daily_df, basic_data, stock_info, cyq_data, fina_data, pe_history, repurchase_data = await asyncio.gather(
        asyncio.to_thread(daily_repo.get_by_code_and_date_range, ts_code, start_dash, end_dash),
        asyncio.to_thread(basic_repo.get_by_code_and_date_range, ts_code, start_yyyymmdd, end_yyyymmdd, 5),
        asyncio.to_thread(stock_repo.get_full_by_ts_code, ts_code),
        asyncio.to_thread(cyq_repo.get_by_date_range, start_yyyymmdd, end_yyyymmdd, ts_code, 1, 1),
        asyncio.to_thread(fina_repo.get_by_code, ts_code, None, None, 4),
        asyncio.to_thread(basic_repo.get_by_code_and_date_range, ts_code, pe_start_3y, end_yyyymmdd, 2000),
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
    if fina_data:
        latest_fina = fina_data[0]
        result['fina'] = {
            'end_date': latest_fina.get('end_date', ''),
            'roe': safe_float(latest_fina.get('roe')),
            'grossprofit_margin': safe_float(latest_fina.get('grossprofit_margin')),
            'netprofit_yoy': safe_float(latest_fina.get('netprofit_yoy')),
            'or_yoy': safe_float(latest_fina.get('or_yoy')),
        }

    # PE-TTM 近3年估值分位
    if pe_history and result.get('pe_ttm') is not None:
        pe_values = [
            safe_float(r.get('pe_ttm'))
            for r in pe_history
            if safe_float(r.get('pe_ttm')) is not None
            and safe_float(r.get('pe_ttm')) > 0
        ]
        if len(pe_values) >= 30:
            current_pe = result['pe_ttm']
            if current_pe and current_pe > 0:
                lower_count = sum(1 for v in pe_values if v < current_pe)
                percentile = round(lower_count / len(pe_values) * 100, 1)
                result['pe_percentile_3y'] = percentile
                result['pe_sample_count'] = len(pe_values)

    # 东财行业板块及近5交易日涨跌幅
    industry_bk = await _get_industry_board(ts_code)
    if industry_bk:
        result['industry_board_name'] = industry_bk.get('name', '')
        result['industry_5d'] = await _get_board_pct_5d(industry_bk['ts_code'])

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
        net_amounts = [safe_float(r.get('net_amount')) or 0 for r in flow_data]
        result['net_1d'] = net_amounts[0] if net_amounts else None
        result['net_5d'] = sum(net_amounts[:5])
        result['net_10d'] = sum(net_amounts[:10])
        result['flow_detail'] = [
            {
                'trade_date': str(r.get('trade_date', ''))[:8],
                'net_amount': safe_float(r.get('net_amount')) or 0,
                'pct_change': safe_float(r.get('pct_change')) or 0,
            }
            for r in flow_data[:5]
        ]

    if hk_data:
        latest_hk = hk_data[0]
        result['hk_hold'] = {
            'trade_date': str(latest_hk.get('trade_date', ''))[:10],
            'vol': latest_hk.get('vol'),
            'ratio': safe_float(latest_hk.get('ratio')),
        }
        if len(hk_data) > 1:
            prev_vol = safe_float(hk_data[-1].get('vol')) or 0
            curr_vol = safe_float(latest_hk.get('vol')) or 0
            result['hk_hold']['prev_vol'] = prev_vol
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
# 四、财报与敏感公告
# ------------------------------------------------------------------

async def get_financial_reports(ts_code: str) -> Dict:
    from app.repositories.disclosure_date_repository import DisclosureDateRepository
    from app.repositories.forecast_repository import ForecastRepository
    from app.repositories.express_repository import ExpressRepository

    today = datetime.now()
    end_yyyymmdd = today.strftime('%Y%m%d')
    start_365d = (today - timedelta(days=365)).strftime('%Y%m%d')

    disclosures, forecasts, express_list = await asyncio.gather(
        asyncio.to_thread(DisclosureDateRepository().get_by_ts_code, ts_code, 8),
        asyncio.to_thread(
            ForecastRepository().get_by_date_range,
            start_365d, end_yyyymmdd, ts_code, None, None, 5
        ),
        asyncio.to_thread(
            ExpressRepository().get_by_code, ts_code, start_365d, end_yyyymmdd, 5
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

    signals = [
        r for r in rows
        if r.get('nine_up_turn') == '+9' or r.get('nine_down_turn') == '-9'
    ]
    result['recent_signals'] = [
        {
            'date': r.get('trade_date', '')[:10],
            'type': '九转见顶' if r.get('nine_up_turn') == '+9' else '九转见底',
        }
        for r in signals
    ]

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

        # 尾盘竞价成交占当日总成交比例（stock_daily.volume 单位：手；auction.vol 单位：股 → /100 换算）
        day_vol = daily_map.get(auction_date_c, {}).get('volume')
        vol_share_pct = None
        if day_vol and auction_vol_c:
            day_vol_shares = day_vol * 100  # 手 → 股
            vol_share_pct = round(auction_vol_c / day_vol_shares * 100, 2)

        result['close_auction'] = {
            'trade_date': auction_date_c,
            'close': auction_close,
            'vol': auction_vol_c,
            'amount': auction_amount_c,
            'vol_share_pct': vol_share_pct,
        }

    return result
