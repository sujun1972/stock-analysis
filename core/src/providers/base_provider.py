"""
抽象数据提供者基类
定义统一的数据获取接口规范
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from datetime import datetime, date
import pandas as pd


class BaseDataProvider(ABC):
    """
    抽象数据提供者基类

    所有数据源（AkShare、Tushare等）必须实现此接口
    确保系统可以无缝切换数据源
    """

    def __init__(self, **kwargs):
        """
        初始化数据提供者

        Args:
            **kwargs: 各数据源特定的配置参数
                - token: Tushare API Token
                - timeout: 请求超时时间
                - retry_count: 重试次数
        """
        self.config = kwargs
        self.provider_name = self.__class__.__name__
        self._validate_config()

    @abstractmethod
    def _validate_config(self) -> None:
        """
        验证配置参数

        Raises:
            ValueError: 配置参数无效
        """
        pass

    # ========== 股票列表相关 ==========

    @abstractmethod
    def get_stock_list(self) -> pd.DataFrame:
        """
        获取全部 A 股股票列表

        Returns:
            pd.DataFrame: 包含以下标准化字段
                - code: 股票代码 (str, 如 '000001')
                - name: 股票名称 (str)
                - market: 市场类型 (str, 如 '上海主板')
                - industry: 行业 (str, 可选)
                - area: 地区 (str, 可选)
                - list_date: 上市日期 (date, 可选)
                - status: 状态 (str, 如 '正常')

        Raises:
            Exception: 获取数据失败
        """
        pass

    @abstractmethod
    def get_new_stocks(self, days: int = 30) -> pd.DataFrame:
        """
        获取最近 N 天上市的新股

        Args:
            days: 最近天数，默认 30 天

        Returns:
            pd.DataFrame: 包含标准化字段（同 get_stock_list）

        Raises:
            Exception: 获取数据失败
        """
        pass

    @abstractmethod
    def get_delisted_stocks(self) -> pd.DataFrame:
        """
        获取退市股票列表

        Returns:
            pd.DataFrame: 包含以下标准化字段
                - code: 股票代码
                - name: 股票名称
                - list_date: 上市日期
                - delist_date: 退市日期
                - market: 市场类型

        Raises:
            Exception: 获取数据失败
        """
        pass

    # ========== 日线数据相关 ==========

    @abstractmethod
    def get_daily_data(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = 'qfq'
    ) -> pd.DataFrame:
        """
        获取股票日线数据

        Args:
            code: 股票代码 (如 '000001')
            start_date: 开始日期 (格式: 'YYYYMMDD' 或 'YYYY-MM-DD')
            end_date: 结束日期 (格式: 'YYYYMMDD' 或 'YYYY-MM-DD')
            adjust: 复权方式 ('qfq': 前复权, 'hfq': 后复权, '': 不复权)

        Returns:
            pd.DataFrame: 包含以下标准化字段
                - trade_date: 交易日期 (date)
                - open: 开盘价 (float)
                - high: 最高价 (float)
                - low: 最低价 (float)
                - close: 收盘价 (float)
                - volume: 成交量 (int)
                - amount: 成交额 (float)
                - amplitude: 振幅 (float, 可选)
                - pct_change: 涨跌幅 (float, 可选)
                - change_amount: 涨跌额 (float, 可选)
                - turnover: 换手率 (float, 可选)

        Raises:
            Exception: 获取数据失败
        """
        pass

    @abstractmethod
    def get_daily_batch(
        self,
        codes: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = 'qfq'
    ) -> Dict[str, pd.DataFrame]:
        """
        批量获取多只股票的日线数据

        Args:
            codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            adjust: 复权方式

        Returns:
            Dict[str, pd.DataFrame]: 字典，key为股票代码，value为日线数据
        """
        pass

    # ========== 分时数据相关 ==========

    @abstractmethod
    def get_minute_data(
        self,
        code: str,
        period: str = '5',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = ''
    ) -> pd.DataFrame:
        """
        获取股票分时数据

        Args:
            code: 股票代码
            period: 分时周期 ('1', '5', '15', '30', '60')
            start_date: 开始日期时间 (格式: 'YYYY-MM-DD HH:MM:SS')
            end_date: 结束日期时间
            adjust: 复权方式

        Returns:
            pd.DataFrame: 包含以下标准化字段
                - trade_time: 交易时间 (datetime)
                - open: 开盘价 (float)
                - high: 最高价 (float)
                - low: 最低价 (float)
                - close: 收盘价 (float)
                - volume: 成交量 (int)
                - amount: 成交额 (float)
                - amplitude: 振幅 (float, 可选)
                - pct_change: 涨跌幅 (float, 可选)
                - change_amount: 涨跌额 (float, 可选)
                - turnover: 换手率 (float, 可选)
        """
        pass

    # ========== 实时行情相关 ==========

    @abstractmethod
    def get_realtime_quotes(
        self,
        codes: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        获取实时行情数据

        Args:
            codes: 股票代码列表 (None 表示获取全部)

        Returns:
            pd.DataFrame: 包含以下标准化字段
                - code: 股票代码 (str)
                - name: 股票名称 (str)
                - latest_price: 最新价 (float)
                - open: 开盘价 (float)
                - high: 最高价 (float)
                - low: 最低价 (float)
                - pre_close: 昨收价 (float)
                - volume: 成交量 (int)
                - amount: 成交额 (float)
                - pct_change: 涨跌幅 (float)
                - change_amount: 涨跌额 (float)
                - turnover: 换手率 (float, 可选)
                - amplitude: 振幅 (float, 可选)
                - trade_time: 行情时间 (datetime)
        """
        pass

    # ========== 工具方法 ==========

    @staticmethod
    def normalize_date(date_value: any) -> Optional[str]:
        """
        标准化日期格式为 YYYYMMDD

        Args:
            date_value: 日期值 (str, date, datetime)

        Returns:
            str: 格式化后的日期字符串 (YYYYMMDD)
        """
        if date_value is None:
            return None

        if isinstance(date_value, str):
            # 移除分隔符
            date_value = date_value.replace('-', '').replace('/', '')
            if len(date_value) == 8:
                return date_value
            raise ValueError(f"Invalid date format: {date_value}")

        if isinstance(date_value, (date, datetime)):
            return date_value.strftime('%Y%m%d')

        raise ValueError(f"Unsupported date type: {type(date_value)}")

    @staticmethod
    def normalize_datetime(datetime_value: any) -> Optional[str]:
        """
        标准化日期时间格式为 YYYY-MM-DD HH:MM:SS

        Args:
            datetime_value: 日期时间值

        Returns:
            str: 格式化后的日期时间字符串
        """
        if datetime_value is None:
            return None

        if isinstance(datetime_value, str):
            return datetime_value

        if isinstance(datetime_value, datetime):
            return datetime_value.strftime('%Y-%m-%d %H:%M:%S')

        if isinstance(datetime_value, date):
            return f"{datetime_value.strftime('%Y-%m-%d')} 00:00:00"

        raise ValueError(f"Unsupported datetime type: {type(datetime_value)}")

    def __repr__(self) -> str:
        return f"<{self.provider_name}>"
