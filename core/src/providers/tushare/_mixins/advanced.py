"""
高级/特色数据 Mixin

包含：get_cyq_perf, get_cyq_chips, get_ccass_hold, get_stk_auction_o,
      get_stk_auction_c, get_hk_hold, get_ccass_hold_detail, get_stk_nineturn,
      get_stk_ah_comparison, get_stk_surv, get_broker_recommend, get_report_rc,
      get_dc_member, get_dc_index, get_dc_daily, get_suspend_d, get_stk_limit_d,
      get_hsgt_top10, get_ggt_daily, get_ggt_top10, get_ggt_monthly,
      get_adj_factor (完整版), get_stock_st, get_trade_calendar
"""

import pandas as pd
from typing import Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


class AdvancedMixin:
    """高级数据、特色数据及港股通数据获取"""

    def get_cyq_perf(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        获取A股每日筹码平均成本和胜率情况
        积分消耗：5000分起
        """
        return self._query(
            'cyq_perf', '筹码及胜率',
            **self._build_params(
                ts_code=ts_code, trade_date=trade_date,
                start_date=start_date, end_date=end_date,
                limit=limit, offset=offset,
            )
        )

    def get_cyq_chips(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        获取A股每日的筹码分布情况，提供各价位占比
        积分消耗：5000分起，单次最大2000条
        """
        return self._query(
            'cyq_chips', '筹码分布',
            **self._build_params(
                ts_code=ts_code, trade_date=trade_date,
                start_date=start_date, end_date=end_date,
                limit=limit, offset=offset,
            )
        )

    def get_ccass_hold(
        self,
        ts_code: Optional[str] = None,
        hk_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        获取中央结算系统持股汇总数据
        积分消耗：120积分（试用），5000积分（正式）
        """
        return self._query(
            'ccass_hold', 'CCASS持股汇总',
            **self._build_params(
                ts_code=ts_code, hk_code=hk_code, trade_date=trade_date,
                start_date=start_date, end_date=end_date,
                limit=limit, offset=offset,
            )
        )

    def get_stk_auction_o(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        获取股票开盘集合竞价数据
        需要开通股票分钟权限，单次最大10000行
        """
        return self._query(
            'stk_auction_o', '开盘集合竞价',
            **self._build_params(
                ts_code=ts_code, trade_date=trade_date,
                start_date=start_date, end_date=end_date,
                limit=limit, offset=offset,
            )
        )

    def get_stk_auction_c(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        获取股票收盘集合竞价数据
        需要开通股票分钟权限，单次最大10000行
        """
        return self._query(
            'stk_auction_c', '收盘集合竞价',
            **self._build_params(
                ts_code=ts_code, trade_date=trade_date,
                start_date=start_date, end_date=end_date,
                limit=limit, offset=offset,
            )
        )

    def get_hk_hold(
        self,
        code: Optional[str] = None,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        exchange: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        获取沪深港股通持股明细数据
        积分消耗：120积分（试用），2000积分（正式）
        注：交易所于2024年8月20日起停止发布日度北向资金数据
        """
        return self._query(
            'hk_hold', '沪深港股通持股',
            **self._build_params(
                code=code, ts_code=ts_code, trade_date=trade_date,
                start_date=start_date, end_date=end_date,
                exchange=exchange, limit=limit, offset=offset,
            )
        )

    def get_ccass_hold_detail(
        self,
        ts_code: Optional[str] = None,
        hk_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        获取中央结算系统机构席位持股明细
        积分消耗：8000积分/次，单次最大6000条
        """
        return self._query(
            'ccass_hold_detail', 'CCASS持股明细',
            **self._build_params(
                ts_code=ts_code, hk_code=hk_code, trade_date=trade_date,
                start_date=start_date, end_date=end_date,
                limit=limit, offset=offset,
            )
        )

    def get_stk_nineturn(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        freq: str = 'daily',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        获取神奇九转指标数据
        积分消耗：6000分，单次最大10000行，数据起始20230101
        """
        return self._query(
            'stk_nineturn', '神奇九转指标',
            **self._build_params(
                ts_code=ts_code, trade_date=trade_date, freq=freq,
                start_date=start_date, end_date=end_date,
                limit=limit, offset=offset,
            )
        )

    def get_stk_ah_comparison(
        self,
        hk_code: Optional[str] = None,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        获取AH股比价数据
        积分消耗：5000分起，单次最大1000行，数据起始20250812
        """
        return self._query(
            'stk_ah_comparison', 'AH股比价',
            **self._build_params(
                hk_code=hk_code, ts_code=ts_code, trade_date=trade_date,
                start_date=start_date, end_date=end_date,
                limit=limit, offset=offset,
            )
        )

    def get_stk_surv(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        获取机构调研表数据
        积分消耗：5000分/次，单次最大100行
        """
        return self._query(
            'stk_surv', '机构调研',
            **self._build_params(
                ts_code=ts_code, trade_date=trade_date,
                start_date=start_date, end_date=end_date,
                limit=limit, offset=offset,
            )
        )

    def get_broker_recommend(self, month: str) -> pd.DataFrame:
        """
        获取券商每月荐股数据
        积分消耗：6000分/次，单次最大1000行，每月1-3日更新

        Args:
            month: 月度 YYYYMM（必需）
        """
        return self._query('broker_recommend', '券商荐股', month=month)

    def get_report_rc(
        self,
        ts_code: Optional[str] = None,
        report_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        获取卖方盈利预测数据
        积分消耗：5000分
        """
        return self._query(
            'report_rc', '卖方盈利预测',
            **self._build_params(
                ts_code=ts_code, report_date=report_date,
                start_date=start_date, end_date=end_date,
                limit=limit, offset=offset,
            )
        )

    def get_dc_member(
        self,
        ts_code: Optional[str] = None,
        con_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 5000,
        offset: int = 0
    ) -> pd.DataFrame:
        """
        获取东方财富板块成分数据
        积分消耗：6000分/次，单次最大5000行
        """
        return self._query(
            'dc_member', '东方财富板块成分',
            **self._build_params(
                ts_code=ts_code, con_code=con_code, trade_date=trade_date,
                start_date=start_date, end_date=end_date,
                limit=limit, offset=offset,
            )
        )

    def get_dc_index(
        self,
        ts_code: Optional[str] = None,
        name: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        idx_type: str = '概念板块',
        limit: int = 5000,
        offset: int = 0
    ) -> pd.DataFrame:
        """
        获取东方财富板块数据（概念/行业/地域）
        积分消耗：6000分/次，单次最大5000行
        """
        return self._query(
            'dc_index', '东方财富板块数据',
            **self._build_params(
                ts_code=ts_code, name=name, trade_date=trade_date,
                start_date=start_date, end_date=end_date, idx_type=idx_type,
                limit=limit, offset=offset,
            )
        )

    def get_dc_daily(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        idx_type: Optional[str] = None,
        limit: int = 2000,
        offset: int = 0
    ) -> pd.DataFrame:
        """
        获取东方财富概念板块行情数据
        积分消耗：6000分/次，单次最大2000行，历史数据从2020年开始
        """
        return self._query(
            'dc_daily', '东方财富概念板块行情',
            **self._build_params(
                ts_code=ts_code, trade_date=trade_date,
                start_date=start_date, end_date=end_date, idx_type=idx_type,
                limit=limit, offset=offset,
            )
        )

    def get_suspend_d(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        suspend_type: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取股票每日停复牌信息
        按日期方式获取，suspend_type: S-停牌, R-复牌
        """
        return self._query(
            'suspend_d', '每日停复牌',
            **self._build_params(
                ts_code=ts_code, trade_date=trade_date,
                start_date=start_date, end_date=end_date,
                suspend_type=suspend_type,
            )
        )

    def get_stk_limit_d(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取每日涨跌停价格（全市场含A/B股和基金）
        积分消耗：2000分，单次最多5800条，每交易日8:40更新
        """
        return self._query(
            'stk_limit', '每日涨跌停价格',
            **self._build_params(
                ts_code=ts_code, trade_date=trade_date,
                start_date=start_date, end_date=end_date,
            )
        )

    def get_hsgt_top10(self,
                       ts_code: Optional[str] = None,
                       trade_date: Optional[str] = None,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None,
                       market_type: Optional[str] = None) -> pd.DataFrame:
        """
        获取沪深股通十大成交股数据
        每天18~20点之间完成当日更新
        """
        return self._query(
            'hsgt_top10', '沪深股通十大成交股',
            **self._build_params(
                ts_code=ts_code, trade_date=trade_date,
                start_date=start_date, end_date=end_date,
                market_type=market_type,
            )
        )

    def get_ggt_daily(self,
                      trade_date: Optional[str] = None,
                      start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取港股通每日成交统计数据
        积分消耗：2000分，数据从2014年开始
        """
        return self._query(
            'ggt_daily', '港股通每日成交',
            **self._build_params(
                trade_date=trade_date, start_date=start_date, end_date=end_date,
            )
        )

    def get_ggt_top10(self,
                      ts_code: Optional[str] = None,
                      trade_date: Optional[str] = None,
                      start_date: Optional[str] = None,
                      end_date: Optional[str] = None,
                      market_type: Optional[str] = None) -> pd.DataFrame:
        """
        获取港股通十大成交股数据
        每天18~20点之间完成当日更新
        """
        return self._query(
            'ggt_top10', '港股通十大成交股',
            **self._build_params(
                ts_code=ts_code, trade_date=trade_date,
                start_date=start_date, end_date=end_date,
                market_type=market_type,
            )
        )

    def get_ggt_monthly(self,
                        month: Optional[str] = None,
                        start_month: Optional[str] = None,
                        end_month: Optional[str] = None) -> pd.DataFrame:
        """
        获取港股通每月成交统计数据
        积分消耗：5000分/次，单次最大1000条，数据从2014年开始
        """
        return self._query(
            'ggt_monthly', '港股通每月成交',
            **self._build_params(
                month=month, start_month=start_month, end_month=end_month,
            )
        )

    def get_stock_st(self,
                     ts_code: Optional[str] = None,
                     trade_date: Optional[str] = None,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取ST股票列表（历史每天数据）
        积分消耗：3000分起，数据从20160101开始，每天9:20更新
        """
        return self._query(
            'stock_st', 'ST股票',
            **self._build_params(
                ts_code=ts_code, trade_date=trade_date,
                start_date=start_date, end_date=end_date,
            )
        )

    def get_trade_calendar(
        self,
        exchange: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        is_open: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取交易日历数据
        积分消耗：2000分

        Args:
            exchange: 交易所代码（SSE/SZSE/CFFEX/SHFE/CZCE/DCE/INE）
            is_open: '0'休市 '1'交易
        """
        return self._query(
            'trade_cal', '交易日历',
            **self._build_params(
                exchange=exchange, start_date=start_date,
                end_date=end_date, is_open=is_open,
            )
        )
