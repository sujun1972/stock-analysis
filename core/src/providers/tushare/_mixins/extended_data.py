"""
扩展基础数据 Mixin

包含：get_daily_basic, get_moneyflow, get_adj_factor, get_margin, get_slb_len,
      get_margin_detail, get_block_trade
"""

import pandas as pd
from typing import Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ExtendedDataMixin:
    """扩展基础数据获取（均调用 _query 返回 DataFrame）"""

    def get_daily_basic(self, ts_code: Optional[str] = None,
                        trade_date: Optional[str] = None,
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取每日指标数据
        积分消耗：120分
        """
        return self._query(
            'daily_basic', '每日指标',
            **self._build_params(
                ts_code=ts_code, trade_date=trade_date,
                start_date=start_date, end_date=end_date,
            )
        )

    def get_moneyflow(self, ts_code: Optional[str] = None,
                      trade_date: Optional[str] = None,
                      start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取个股资金流向
        积分消耗：2000分
        """
        return self._query(
            'moneyflow', '个股资金流向',
            **self._build_params(
                ts_code=ts_code, trade_date=trade_date,
                start_date=start_date, end_date=end_date,
            )
        )

    def get_adj_factor(self, ts_code: Optional[str] = None,
                       trade_date: Optional[str] = None,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None,
                       limit: int = 2000,
                       offset: int = 0) -> pd.DataFrame:
        """
        获取复权因子
        积分消耗：120分
        """
        return self._query(
            'adj_factor', '复权因子',
            **self._build_params(
                ts_code=ts_code, trade_date=trade_date,
                start_date=start_date, end_date=end_date,
                limit=limit, offset=offset,
            )
        )

    def get_margin(self,
                   trade_date: Optional[str] = None,
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None,
                   exchange_id: Optional[str] = None) -> pd.DataFrame:
        """
        获取融资融券交易汇总数据
        积分消耗：2000分，单次最大4000行
        """
        return self._query(
            'margin', '融资融券汇总',
            **self._build_params(
                trade_date=trade_date, start_date=start_date,
                end_date=end_date, exchange_id=exchange_id,
            )
        )

    def get_slb_len(self,
                    trade_date: Optional[str] = None,
                    start_date: Optional[str] = None,
                    end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取转融资交易汇总数据
        积分消耗：2000分，单次最大5000行
        """
        return self._query(
            'slb_len', '转融资汇总',
            **self._build_params(
                trade_date=trade_date, start_date=start_date, end_date=end_date,
            )
        )

    def get_margin_detail(self, ts_code: Optional[str] = None,
                          trade_date: Optional[str] = None,
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None,
                          limit: Optional[int] = None,
                          offset: Optional[int] = None) -> pd.DataFrame:
        """
        获取融资融券详细数据（个股）
        积分消耗：300分
        """
        return self._query(
            'margin_detail', '融资融券明细',
            **self._build_params(
                ts_code=ts_code, trade_date=trade_date,
                start_date=start_date, end_date=end_date,
                limit=limit, offset=offset,
            )
        )

    def get_block_trade(self, ts_code: Optional[str] = None,
                        trade_date: Optional[str] = None,
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None,
                        limit: Optional[int] = None,
                        offset: Optional[int] = None) -> pd.DataFrame:
        """
        获取大宗交易数据
        积分消耗：300分
        """
        return self._query(
            'block_trade', '大宗交易',
            **self._build_params(
                ts_code=ts_code, trade_date=trade_date,
                start_date=start_date, end_date=end_date,
                limit=limit, offset=offset,
            )
        )
