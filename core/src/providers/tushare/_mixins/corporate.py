"""
公司行为数据 Mixin

包含：get_pledge_stat, get_share_float, get_stk_holdernumber, get_repurchase,
      get_forecast, get_fina_indicator, get_express, get_dividend, get_fina_audit,
      get_stk_holdertrade, get_income, get_balancesheet, get_cashflow,
      get_fina_mainbz_vip, get_disclosure_date
"""

import pandas as pd
from typing import Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


class CorporateMixin:
    """公司行为、财务报表数据获取"""

    def get_pledge_stat(
        self,
        ts_code: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        start_date: Optional[str] = None,  # 接口不支持，忽略（供全量同步兼容）
    ) -> pd.DataFrame:
        """
        获取股权质押统计数据
        积分消耗：500分，单次最大1000行
        """
        return self._query(
            'pledge_stat', '股权质押统计',
            **self._build_params(ts_code=ts_code, end_date=end_date,
                                 limit=limit, offset=offset)
        )

    def get_share_float(
        self,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        float_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        获取限售股解禁数据
        积分消耗：120分
        """
        return self._query(
            'share_float', '限售股解禁',
            **self._build_params(
                ts_code=ts_code, ann_date=ann_date, float_date=float_date,
                start_date=start_date, end_date=end_date, limit=limit, offset=offset,
            )
        )

    def get_stk_holdernumber(
        self,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        enddate: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        获取上市公司股东户数数据
        积分消耗：600分
        """
        return self._query(
            'stk_holdernumber', '股东户数',
            **self._build_params(
                ts_code=ts_code, ann_date=ann_date,
                start_date=start_date, end_date=end_date,
                enddate=enddate, limit=limit, offset=offset,
            )
        )

    def get_repurchase(
        self,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        获取上市公司回购股票数据
        积分消耗：600分
        """
        return self._query(
            'repurchase', '股票回购',
            **self._build_params(
                ann_date=ann_date, start_date=start_date, end_date=end_date,
                limit=limit, offset=offset,
            )
        )

    def get_forecast(
        self,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        type_: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取业绩预告数据
        积分消耗：2000分
        """
        params = self._build_params(
            ts_code=ts_code, ann_date=ann_date,
            start_date=start_date, end_date=end_date, period=period,
        )
        if type_:
            params['type'] = type_
        return self._query('forecast_vip', '业绩预告', **params)

    def get_fina_indicator(
        self,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取财务指标数据
        积分消耗：2000分，每次最多100条
        """
        return self._query(
            'fina_indicator_vip', '财务指标',
            **self._build_params(
                ts_code=ts_code, ann_date=ann_date,
                start_date=start_date, end_date=end_date, period=period,
            )
        )

    def get_express(
        self,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取业绩快报数据
        积分消耗：2000分
        """
        return self._query(
            'express_vip', '业绩快报',
            **self._build_params(
                ts_code=ts_code, ann_date=ann_date,
                start_date=start_date, end_date=end_date, period=period,
            )
        )

    def get_dividend(
        self,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        record_date: Optional[str] = None,
        ex_date: Optional[str] = None,
        imp_ann_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取分红送股数据
        积分消耗：2000分
        注意：以上参数至少有一个不能为空
        """
        params = self._build_params(
            ts_code=ts_code, ann_date=ann_date, record_date=record_date,
            ex_date=ex_date, imp_ann_date=imp_ann_date,
        )
        if not params:
            raise ValueError("至少需要提供一个查询参数: ts_code, ann_date, record_date, ex_date, imp_ann_date")
        return self._query('dividend', '分红送股', **params)

    def get_fina_audit(
        self,
        ts_code: str,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取上市公司定期财务审计意见数据
        积分消耗：500分
        """
        return self._query(
            'fina_audit', '财务审计意见',
            **self._build_params(
                ts_code=ts_code, ann_date=ann_date,
                start_date=start_date, end_date=end_date, period=period,
            )
        )

    def get_stk_holdertrade(
        self,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        trade_type: Optional[str] = None,
        holder_type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        获取上市公司股东增减持数据
        积分消耗：2000分
        """
        return self._query(
            'stk_holdertrade', '股东增减持',
            **self._build_params(
                ts_code=ts_code, ann_date=ann_date,
                start_date=start_date, end_date=end_date,
                trade_type=trade_type, holder_type=holder_type,
                limit=limit, offset=offset,
            )
        )

    def get_income(
        self,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        f_ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        report_type: Optional[str] = None,
        comp_type: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取上市公司利润表数据（income_vip接口）
        积分消耗：2000分
        """
        return self._query(
            'income_vip', '利润表',
            **self._build_params(
                ts_code=ts_code, ann_date=ann_date, f_ann_date=f_ann_date,
                start_date=start_date, end_date=end_date,
                period=period, report_type=report_type, comp_type=comp_type,
            )
        )

    def get_balancesheet(
        self,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        f_ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        report_type: Optional[str] = None,
        comp_type: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取上市公司资产负债表数据（balancesheet_vip接口）
        积分消耗：2000分
        """
        return self._query(
            'balancesheet_vip', '资产负债表',
            **self._build_params(
                ts_code=ts_code, ann_date=ann_date, f_ann_date=f_ann_date,
                start_date=start_date, end_date=end_date,
                period=period, report_type=report_type, comp_type=comp_type,
            )
        )

    def get_cashflow(
        self,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        f_ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = None,
        report_type: Optional[str] = None,
        comp_type: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取上市公司现金流量表数据（cashflow_vip接口）
        积分消耗：2000分
        """
        return self._query(
            'cashflow_vip', '现金流量表',
            **self._build_params(
                ts_code=ts_code, ann_date=ann_date, f_ann_date=f_ann_date,
                start_date=start_date, end_date=end_date,
                period=period, report_type=report_type, comp_type=comp_type,
            )
        )

    def get_fina_mainbz_vip(
        self,
        ts_code: Optional[str] = None,
        period: Optional[str] = None,
        type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取上市公司主营业务构成数据（分产品/地区/行业）
        积分消耗：2000分
        """
        params = self._build_params(
            ts_code=ts_code, period=period,
            start_date=start_date, end_date=end_date,
        )
        if type:
            params['type'] = type
        return self._query('fina_mainbz_vip', '主营业务构成', **params)

    def get_disclosure_date(
        self,
        ts_code: Optional[str] = None,
        end_date: Optional[str] = None,
        pre_date: Optional[str] = None,
        ann_date: Optional[str] = None,
        actual_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取财报披露计划日期
        积分消耗：500分起
        """
        return self._query(
            'disclosure_date', '财报披露计划',
            **self._build_params(
                ts_code=ts_code, end_date=end_date, pre_date=pre_date,
                ann_date=ann_date, actual_date=actual_date,
            )
        )
