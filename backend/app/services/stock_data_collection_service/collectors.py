"""
数据收集模块

从本地数据库收集各维度数据：基础盘面、资金流向、股东信息、财报、风险、神奇九转。
技术指标收集见 technical.py。
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from loguru import logger

from .formatters import days_since, format_date_dashed, quantile, safe_float


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

    # PE-TTM 近3年估值分位 + PE Band（高/中/低位估值通道）
    if pe_history and result.get('pe_ttm') is not None:
        pe_values = sorted([
            safe_float(r.get('pe_ttm'))
            for r in pe_history
            if safe_float(r.get('pe_ttm')) is not None
            and safe_float(r.get('pe_ttm')) > 0
        ])
        if len(pe_values) >= 30:
            current_pe = result['pe_ttm']
            if current_pe and current_pe > 0:
                lower_count = sum(1 for v in pe_values if v < current_pe)
                percentile = round(lower_count / len(pe_values) * 100, 1)
                result['pe_percentile_3y'] = percentile
                result['pe_sample_count'] = len(pe_values)

                # 估值档位中性标签（仅描述分位区间，不做高/低估判断，由 AI 自行解读）
                if percentile >= 95:
                    band_label = '≥95%分位区间'
                elif percentile >= 80:
                    band_label = '80~95%分位区间'
                elif percentile >= 60:
                    band_label = '60~80%分位区间'
                elif percentile >= 40:
                    band_label = '40~60%分位区间'
                elif percentile >= 20:
                    band_label = '20~40%分位区间'
                else:
                    band_label = '<20%分位区间'
                result['pe_band_label'] = band_label

                # PE Band 通道数值（10/50/90 分位 = 估值通道下/中/上轨）
                result['pe_band'] = {
                    'p10': quantile(pe_values, 0.10),
                    'p50': quantile(pe_values, 0.50),
                    'p90': quantile(pe_values, 0.90),
                    'p99': quantile(pe_values, 0.99),
                    'min': round(pe_values[0], 2),
                    'max': round(pe_values[-1], 2),
                }

    # 东财行业板块及近5交易日涨跌幅
    industry_bk = await _get_industry_board(ts_code)
    if industry_bk:
        result['industry_board_name'] = industry_bk.get('name', '')
        result['industry_5d'] = await _get_board_pct_5d(industry_bk['ts_code'])

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
    # 公认机构席位（任何"机构专用"都是机构；席位名为固定字符串）
    '机构专用': '机构席位',
    # 知名一线游资席位（仅做标记，未来可扩展；命中字符串为子串匹配）
    '中信证券股份有限公司深圳福田金田路证券营业部': '一线游资·深圳金田路（炒新/打板风）',
    '国泰海通证券股份有限公司上海长宁区江苏路证券营业部': '一线游资·上海溧阳路（章盟主系）',
    '华鑫证券有限责任公司上海茅台路证券营业部': '一线量化席位（华鑫茅台路）',
    '中信证券(山东)有限责任公司青岛分公司': '量化/对冲席位（中信山东青岛）',
}


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

    return result
