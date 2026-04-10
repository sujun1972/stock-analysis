"""
资金流向及交易监控数据 Mixin

包含：get_moneyflow_hsgt, get_moneyflow_mkt_dc, get_moneyflow_ind_dc,
      get_moneyflow_stock_dc, get_stk_limit, get_suspend, get_top_list,
      get_top_inst, get_limit_list_d, get_limit_step, get_limit_cpt_list,
      get_stk_shock, get_stk_high_shock, get_stk_alert
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


class FundFlowMixin:
    """资金流向及交易监控数据获取"""

    def get_moneyflow_hsgt(self, trade_date: Optional[str] = None,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取沪深港通资金流向数据
        积分消耗：2000分

        注意：接口必须指定日期参数，未指定时默认取最近30天
        """
        from ..exceptions import TushareDataError

        try:
            logger.info(f"获取沪深港通资金流向: trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

            if trade_date:
                df = self.api_client.query('moneyflow_hsgt', trade_date=trade_date)
            elif start_date and end_date:
                df = self.api_client.query('moneyflow_hsgt', start_date=start_date, end_date=end_date)
            elif start_date:
                end_date = datetime.now().strftime('%Y%m%d')
                df = self.api_client.query('moneyflow_hsgt', start_date=start_date, end_date=end_date)
            else:
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
                df = self.api_client.query('moneyflow_hsgt', start_date=start_date, end_date=end_date)

            return df
        except Exception as e:
            logger.error(f"获取沪深港通资金流向失败: {e}")
            raise TushareDataError(f"获取沪深港通资金流向失败: {str(e)}")

    def get_moneyflow_mkt_dc(self, trade_date: Optional[str] = None,
                              start_date: Optional[str] = None,
                              end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取大盘资金流向数据（东方财富DC）
        积分消耗：120分（试用），6000分（正式）
        """
        return self._query(
            'moneyflow_mkt_dc', '大盘资金流向',
            **self._build_params(
                trade_date=trade_date, start_date=start_date, end_date=end_date,
            )
        )

    def get_moneyflow_ind_dc(self,
                              ts_code: Optional[str] = None,
                              trade_date: Optional[str] = None,
                              start_date: Optional[str] = None,
                              end_date: Optional[str] = None,
                              content_type: Optional[str] = None) -> pd.DataFrame:
        """
        获取板块资金流向数据（东财概念及行业板块资金流向 DC）
        积分消耗：6000分
        """
        return self._query(
            'moneyflow_ind_dc', '板块资金流向',
            **self._build_params(
                ts_code=ts_code, trade_date=trade_date,
                start_date=start_date, end_date=end_date,
                content_type=content_type,
            )
        )

    def get_moneyflow_stock_dc(self,
                                ts_code: Optional[str] = None,
                                trade_date: Optional[str] = None,
                                start_date: Optional[str] = None,
                                end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取个股资金流向数据（东方财富DC）
        积分消耗：5000分，单次最大6000条，数据开始时间：20230911
        """
        return self._query(
            'moneyflow_dc', '个股资金流向DC',
            **self._build_params(
                ts_code=ts_code, trade_date=trade_date,
                start_date=start_date, end_date=end_date,
            )
        )

    def get_stk_limit(self, ts_code: Optional[str] = None,
                      trade_date: Optional[str] = None,
                      start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取每日涨跌停价格
        积分消耗：120分
        """
        return self._query(
            'stk_limit', '每日涨跌停',
            **self._build_params(
                ts_code=ts_code, trade_date=trade_date,
                start_date=start_date, end_date=end_date,
            )
        )

    def get_suspend(self, ts_code: Optional[str] = None,
                    suspend_date: Optional[str] = None,
                    resume_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取停复牌信息
        积分消耗：120分
        """
        return self._query(
            'suspend', '停复牌信息',
            **self._build_params(
                ts_code=ts_code, suspend_date=suspend_date, resume_date=resume_date,
            )
        )

    def get_top_list(self, trade_date: str,
                     ts_code: Optional[str] = None) -> pd.DataFrame:
        """
        获取龙虎榜每日明细
        积分消耗：2000分，单次最大10000行
        """
        return self._query(
            'top_list', '龙虎榜每日明细',
            **self._build_params(trade_date=trade_date, ts_code=ts_code)
        )

    def get_top_inst(self, trade_date: str,
                     ts_code: Optional[str] = None) -> pd.DataFrame:
        """
        获取龙虎榜机构明细
        积分消耗：5000分，单次最大10000行
        """
        return self._query(
            'top_inst', '龙虎榜机构明细',
            **self._build_params(trade_date=trade_date, ts_code=ts_code)
        )

    def get_limit_list_d(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        limit_type: Optional[str] = None,
        exchange: Optional[str] = None,
        limit: int = 2500,
        offset: int = 0
    ) -> pd.DataFrame:
        """
        获取涨跌停列表
        积分消耗：5000分，单次最大2500行
        """
        return self._query(
            'limit_list_d', '涨跌停列表',
            **self._build_params(
                trade_date=trade_date, start_date=start_date, end_date=end_date,
                ts_code=ts_code, limit_type=limit_type, exchange=exchange,
                limit=limit, offset=offset,
            )
        )

    def get_limit_step(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        nums: Optional[str] = None,
        limit: int = 2000,
        offset: int = 0
    ) -> pd.DataFrame:
        """
        获取连板天梯（每天连板个数晋级的股票）
        积分消耗：8000分以上，单次最大2000行
        """
        return self._query(
            'limit_step', '连板天梯',
            **self._build_params(
                trade_date=trade_date, start_date=start_date, end_date=end_date,
                ts_code=ts_code, nums=nums,
                limit=limit, offset=offset,
            )
        )

    def get_limit_cpt_list(
        self,
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 2000,
        offset: int = 0
    ) -> pd.DataFrame:
        """
        获取最强板块统计（每天涨停股票最多最强的概念板块）
        积分消耗：8000分，单次最大2000行
        """
        return self._query(
            'limit_cpt_list', '最强板块',
            **self._build_params(
                trade_date=trade_date, ts_code=ts_code,
                start_date=start_date, end_date=end_date,
                limit=limit, offset=offset,
            )
        )

    def get_stk_shock(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        获取个股异常波动数据
        积分消耗：6000分，单次最大1000行
        """
        return self._query(
            'stk_shock', '个股异常波动',
            **self._build_params(
                ts_code=ts_code, trade_date=trade_date,
                start_date=start_date, end_date=end_date,
                limit=limit, offset=offset,
            )
        )

    def get_stk_high_shock(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        获取个股严重异常波动数据
        积分消耗：6000分，单次最大1000行
        """
        return self._query(
            'stk_high_shock', '个股严重异常波动',
            **self._build_params(
                ts_code=ts_code, trade_date=trade_date,
                start_date=start_date, end_date=end_date,
                limit=limit, offset=offset,
            )
        )

    def get_stk_alert(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        获取交易所重点提示证券数据
        积分消耗：6000分，单次最大1000行
        """
        return self._query(
            'stk_alert', '交易所重点提示证券',
            **self._build_params(
                ts_code=ts_code, trade_date=trade_date,
                start_date=start_date, end_date=end_date,
                limit=limit, offset=offset,
            )
        )
