"""
Tushare 数据转换器

负责将 Tushare API 返回的数据转换为标准格式
包括字段重命名、单位转换、日期格式化等
"""

from datetime import datetime
from typing import Optional
import pandas as pd
from src.utils.logger import get_logger
from .config import TushareConfig, TushareFields

logger = get_logger(__name__)


class TushareDataConverter:
    """
    Tushare 数据转换器

    提供统一的数据转换方法，确保输出符合项目标准
    """

    @staticmethod
    def to_ts_code(code: str) -> str:
        """
        转换为 Tushare 格式的股票代码

        Args:
            code: 股票代码（如 '000001'）

        Returns:
            str: Tushare 格式代码（如 '000001.SZ'）
        """
        if '.' in code:
            return code

        suffix = TushareConfig.get_exchange_suffix(code)
        return f"{code}.{suffix}"

    @staticmethod
    def from_ts_code(ts_code: str) -> str:
        """
        从 Tushare 格式提取股票代码

        Args:
            ts_code: Tushare 格式代码（如 '000001.SZ'）

        Returns:
            str: 股票代码（如 '000001'）
        """
        return ts_code.split('.')[0] if '.' in ts_code else ts_code

    @staticmethod
    def convert_stock_list(df: pd.DataFrame) -> pd.DataFrame:
        """
        转换股票列表数据

        Args:
            df: 原始 DataFrame

        Returns:
            pd.DataFrame: 标准化的股票列表
        """
        if df is None or df.empty:
            logger.warning("股票列表数据为空")
            return pd.DataFrame(columns=TushareFields.STOCK_LIST_OUTPUT)

        # 重命名字段
        df = df.rename(columns=TushareFields.STOCK_LIST_RENAME)

        # 处理市场类型映射
        if 'market' in df.columns:
            df['market'] = df['market'].map(TushareConfig.MARKET_TYPE_MAP).fillna('其他')

        # 转换上市日期
        if 'list_date' in df.columns:
            df['list_date'] = pd.to_datetime(
                df['list_date'],
                format='%Y%m%d',
                errors='coerce'
            ).dt.date

        # 添加默认状态
        df['status'] = '正常'

        # 选择标准字段
        available_cols = [col for col in TushareFields.STOCK_LIST_OUTPUT if col in df.columns]
        return df[available_cols].copy()

    @staticmethod
    def convert_daily_data(df: pd.DataFrame) -> pd.DataFrame:
        """
        转换日线数据

        Args:
            df: 原始 DataFrame

        Returns:
            pd.DataFrame: 标准化的日线数据
        """
        if df is None or df.empty:
            logger.warning("日线数据为空")
            return pd.DataFrame(columns=TushareFields.DAILY_DATA_OUTPUT)

        # 重命名字段
        df = df.rename(columns=TushareFields.DAILY_DATA_RENAME)

        # 转换日期类型
        if 'trade_date' in df.columns:
            df['trade_date'] = pd.to_datetime(
                df['trade_date'],
                format='%Y%m%d'
            ).dt.date

        # 计算派生字段
        if 'pre_close' in df.columns and 'close' in df.columns:
            df['change_amount'] = df['close'] - df['pre_close']

        if all(col in df.columns for col in ['high', 'low', 'pre_close']):
            df['amplitude'] = ((df['high'] - df['low']) / df['pre_close'] * 100)

        # 成交量单位转换（手 -> 股）
        if 'volume' in df.columns:
            df['volume'] = df['volume'] * 100

        # 成交额单位转换（千元 -> 元）
        if 'amount' in df.columns:
            df['amount'] = df['amount'] * 1000

        # 选择标准字段并排序
        available_cols = [col for col in TushareFields.DAILY_DATA_OUTPUT if col in df.columns]
        df = df[available_cols].copy()

        # 按日期升序排序
        if 'trade_date' in df.columns:
            df = df.sort_values('trade_date')

        return df

    @staticmethod
    def convert_minute_data(df: pd.DataFrame, period: str = '5') -> pd.DataFrame:
        """
        转换分钟数据

        Args:
            df: 原始 DataFrame
            period: 分钟周期

        Returns:
            pd.DataFrame: 标准化的分钟数据
        """
        if df is None or df.empty:
            logger.warning("分钟数据为空")
            return pd.DataFrame(columns=TushareFields.MINUTE_DATA_OUTPUT)

        # 重命名字段
        df = df.rename(columns=TushareFields.MINUTE_DATA_RENAME)

        # 转换时间类型
        if 'trade_time' in df.columns:
            df['trade_time'] = pd.to_datetime(df['trade_time'])

        # 添加周期字段
        df['period'] = period

        # 成交量单位转换（手 -> 股）
        if 'volume' in df.columns:
            df['volume'] = df['volume'] * 100

        # 成交额单位转换（千元 -> 元）
        if 'amount' in df.columns:
            df['amount'] = df['amount'] * 1000

        # 选择标准字段
        available_cols = [col for col in TushareFields.MINUTE_DATA_OUTPUT if col in df.columns]
        return df[available_cols].copy()

    @staticmethod
    def convert_realtime_quotes(df: pd.DataFrame) -> pd.DataFrame:
        """
        转换实时行情数据

        Args:
            df: 原始 DataFrame

        Returns:
            pd.DataFrame: 标准化的实时行情数据
        """
        if df is None or df.empty:
            logger.warning("实时行情数据为空")
            return pd.DataFrame(columns=TushareFields.REALTIME_QUOTE_OUTPUT)

        # 重命名字段
        df = df.rename(columns=TushareFields.REALTIME_QUOTE_RENAME)

        # 提取股票代码（去除后缀）
        if 'ts_code_raw' in df.columns:
            df['code'] = df['ts_code_raw'].apply(
                lambda x: TushareDataConverter.from_ts_code(x) if pd.notna(x) else None
            )

        # 计算振幅
        if all(col in df.columns for col in ['high', 'low', 'pre_close']):
            df['amplitude'] = ((df['high'] - df['low']) / df['pre_close'] * 100)

        # 添加行情时间
        df['trade_time'] = datetime.now()

        # 选择标准字段
        available_cols = [col for col in TushareFields.REALTIME_QUOTE_OUTPUT if col in df.columns]
        return df[available_cols].copy()

    @staticmethod
    def convert_new_stocks(df: pd.DataFrame) -> pd.DataFrame:
        """
        转换新股数据

        Args:
            df: 原始 DataFrame

        Returns:
            pd.DataFrame: 标准化的新股列表
        """
        if df is None or df.empty:
            logger.warning("新股数据为空")
            return pd.DataFrame(columns=['code', 'name', 'market', 'list_date', 'status'])

        # 标准化字段
        rename_map = {
            'ts_code': 'ts_code',
            'name': 'name'
        }

        # ipo_date 和 issue_date 只能有一个，优先使用 ipo_date
        if 'ipo_date' in df.columns:
            rename_map['ipo_date'] = 'list_date'
        elif 'issue_date' in df.columns:
            rename_map['issue_date'] = 'list_date'

        df = df.rename(columns=rename_map)

        # 提取股票代码
        if 'symbol' in df.columns:
            df = df.rename(columns={'symbol': 'code'})
        elif 'ts_code' in df.columns:
            df['code'] = df['ts_code'].apply(
                lambda x: TushareDataConverter.from_ts_code(x) if pd.notna(x) else None
            )

        # 添加市场类型
        if 'market' not in df.columns and 'code' in df.columns:
            df['market'] = df['code'].apply(
                lambda x: TushareConfig.parse_market_from_code(x) if pd.notna(x) else '其他'
            )

        # 转换日期格式
        if 'list_date' in df.columns:
            df['list_date'] = pd.to_datetime(
                df['list_date'],
                format='%Y%m%d',
                errors='coerce'
            ).dt.date

        # 添加状态
        df['status'] = '正常'

        # 选择标准字段
        output_cols = ['code', 'name', 'market', 'list_date', 'status']
        available_cols = [col for col in output_cols if col in df.columns]
        return df[available_cols].copy()

    @staticmethod
    def convert_delisted_stocks(df: pd.DataFrame) -> pd.DataFrame:
        """
        转换退市股票数据

        Args:
            df: 原始 DataFrame

        Returns:
            pd.DataFrame: 标准化的退市股票列表
        """
        if df is None or df.empty:
            logger.warning("退市股票数据为空")
            return pd.DataFrame(columns=TushareFields.DELISTED_STOCK_OUTPUT)

        # 重命名字段
        df = df.rename(columns={
            'symbol': 'code',
            'name': 'name',
            'list_date': 'list_date',
            'delist_date': 'delist_date',
            'market': 'market'
        })

        # 转换日期格式
        for date_col in ['list_date', 'delist_date']:
            if date_col in df.columns:
                df[date_col] = pd.to_datetime(
                    df[date_col],
                    format='%Y%m%d',
                    errors='coerce'
                ).dt.date

        # 处理市场类型映射
        if 'market' in df.columns:
            df['market'] = df['market'].map(TushareConfig.MARKET_TYPE_MAP).fillna('其他')

        # 选择标准字段
        available_cols = [col for col in TushareFields.DELISTED_STOCK_OUTPUT if col in df.columns]
        return df[available_cols].copy()
