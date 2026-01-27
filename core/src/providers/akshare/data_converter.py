"""
AkShare 数据格式转换器

负责将 AkShare 返回的数据转换为标准格式
"""

from typing import Any
from datetime import datetime
import pandas as pd
from src.utils.logger import get_logger
from .config import AkShareConfig, AkShareFields

logger = get_logger(__name__)


class AkShareDataConverter:
    """
    AkShare 数据格式转换器

    职责：
    - 字段名映射
    - 数据类型转换
    - 日期格式标准化
    - 市场类型解析
    """

    @staticmethod
    def safe_float(value: Any, default: float = 0.0) -> float:
        """
        安全转换为 float

        Args:
            value: 原始值
            default: 默认值

        Returns:
            float: 转换后的值
        """
        try:
            if value is None or value == '' or value == '-':
                return default
            return float(str(value).replace(',', '').replace('%', ''))
        except (ValueError, TypeError):
            return default

    @staticmethod
    def safe_int(value: Any, default: int = 0) -> int:
        """
        安全转换为 int

        Args:
            value: 原始值
            default: 默认值

        Returns:
            int: 转换后的值
        """
        try:
            if value is None or value == '' or value == '-':
                return default
            return int(float(str(value).replace(',', '')))
        except (ValueError, TypeError):
            return default

    def convert_stock_list(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        转换股票列表为标准格式

        Args:
            df: AkShare 原始数据

        Returns:
            pd.DataFrame: 标准化的股票列表
        """
        if df is None or df.empty:
            return pd.DataFrame()

        # 标准化字段名
        df = df.rename(columns=AkShareFields.STOCK_LIST_RENAME)

        # 添加市场类型
        df['market'] = df['code'].apply(AkShareConfig.parse_market_from_code)

        # 添加默认状态
        df['status'] = '正常'

        # 选择标准字段
        return df[AkShareFields.STOCK_LIST_OUTPUT]

    def convert_daily_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        转换日线数据为标准格式

        Args:
            df: AkShare 原始数据

        Returns:
            pd.DataFrame: 标准化的日线数据
        """
        if df is None or df.empty:
            return pd.DataFrame()

        # 标准化字段名
        df = df.rename(columns=AkShareFields.DAILY_DATA_RENAME)

        # 转换日期类型
        df['trade_date'] = pd.to_datetime(df['trade_date']).dt.date

        # 选择标准字段（保留存在的字段）
        available_columns = [col for col in AkShareFields.DAILY_DATA_OUTPUT if col in df.columns]
        return df[available_columns]

    def convert_minute_data(self, df: pd.DataFrame, period: str) -> pd.DataFrame:
        """
        转换分时数据为标准格式

        Args:
            df: AkShare 原始数据
            period: 分时周期

        Returns:
            pd.DataFrame: 标准化的分时数据
        """
        if df is None or df.empty:
            return pd.DataFrame()

        # 标准化字段名
        df = df.rename(columns=AkShareFields.MINUTE_DATA_RENAME)

        # 转换时间类型
        df['trade_time'] = pd.to_datetime(df['trade_time'])

        # 添加周期字段
        df['period'] = period

        # 选择标准字段（保留存在的字段）
        available_columns = [col for col in AkShareFields.MINUTE_DATA_OUTPUT if col in df.columns]
        return df[available_columns]

    def convert_realtime_quotes(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        转换实时行情为标准格式（全量接口）

        Args:
            df: AkShare 原始数据

        Returns:
            pd.DataFrame: 标准化的实时行情数据
        """
        if df is None or df.empty:
            return pd.DataFrame()

        # 标准化字段名
        df = df.rename(columns=AkShareFields.REALTIME_QUOTE_RENAME)

        # 添加行情时间
        df['trade_time'] = datetime.now()

        # 选择标准字段（保留存在的字段）
        available_columns = [col for col in AkShareFields.REALTIME_QUOTE_OUTPUT if col in df.columns]
        return df[available_columns]

    def convert_realtime_quote_single(self, quote_dict: dict) -> dict:
        """
        转换单个股票的实时行情为标准格式

        Args:
            quote_dict: 单个股票的行情字典

        Returns:
            dict: 标准化的行情字典
        """
        return quote_dict  # 已经在 provider 中处理为标准格式

    def convert_new_stocks(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        转换新股列表为标准格式

        Args:
            df: AkShare 原始数据

        Returns:
            pd.DataFrame: 标准化的新股列表
        """
        if df is None or df.empty:
            return pd.DataFrame()

        # 标准化字段名
        df = df.rename(columns=AkShareFields.NEW_STOCK_RENAME)

        # 转换日期为 date 对象
        df['list_date'] = pd.to_datetime(df['list_date'], errors='coerce').dt.date

        # 添加市场类型
        df['market'] = df['code'].apply(AkShareConfig.parse_market_from_code)

        # 添加默认状态
        df['status'] = '正常'

        # 选择标准字段
        return df[AkShareFields.NEW_STOCK_OUTPUT]

    def convert_delisted_stocks(self, df: pd.DataFrame, exchange: str = '') -> pd.DataFrame:
        """
        转换退市股票列表为标准格式

        Args:
            df: AkShare 原始数据
            exchange: 交易所类型（'SH' 或 'SZ'）

        Returns:
            pd.DataFrame: 标准化的退市股票列表
        """
        if df is None or df.empty:
            return pd.DataFrame()

        # 根据交易所选择字段映射
        if exchange == 'SH':
            rename_map = AkShareFields.DELISTED_STOCK_RENAME_SH
        elif exchange == 'SZ':
            rename_map = AkShareFields.DELISTED_STOCK_RENAME_SZ
        else:
            # 自动检测
            if '暂停上市日期' in df.columns:
                rename_map = AkShareFields.DELISTED_STOCK_RENAME_SH
            elif '终止上市日期' in df.columns:
                rename_map = AkShareFields.DELISTED_STOCK_RENAME_SZ
            else:
                rename_map = AkShareFields.DELISTED_STOCK_RENAME_SH

        # 标准化字段名
        df = df.rename(columns=rename_map)

        # 转换日期格式
        df['list_date'] = pd.to_datetime(df['list_date'], errors='coerce').dt.date
        df['delist_date'] = pd.to_datetime(df['delist_date'], errors='coerce').dt.date

        # 选择标准字段（保留存在的字段）
        available_columns = [col for col in AkShareFields.DELISTED_STOCK_OUTPUT if col in df.columns]
        return df[available_columns]

    def __repr__(self) -> str:
        return "<AkShareDataConverter>"


__all__ = ['AkShareDataConverter']
