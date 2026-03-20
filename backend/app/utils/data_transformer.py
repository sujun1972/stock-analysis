"""
数据转换工具

统一处理不同数据源的格式转换
"""

from typing import Dict, Optional

import pandas as pd
from loguru import logger


class DataTransformer:
    """
    数据转换工具类

    职责：
    - 统一列名转换（中文 -> 英文）
    - 日期格式标准化
    - 数据类型转换
    - DataFrame 索引处理

    Examples:
        >>> transformer = DataTransformer()
        >>> df = pd.DataFrame({'日期': ['2024-01-01'], '开盘': [10.0]})
        >>> df = transformer.transform_daily_data(df)
        >>> print(df.columns)  # Index(['open', ...], dtype='object')
        >>> print(df.index.name)  # 'date'
    """

    # 日线数据列名映射（中文 -> 英文）
    DAILY_DATA_COLUMN_MAPPING: Dict[str, str] = {
        "日期": "date",
        "开盘": "open",
        "最高": "high",
        "最低": "low",
        "收盘": "close",
        "成交量": "volume",
        "成交额": "amount",
        "振幅": "amplitude",
        "涨跌幅": "pct_change",
        "涨跌额": "change",
        "换手率": "turnover",
    }

    # 股票列表列名映射
    STOCK_LIST_COLUMN_MAPPING: Dict[str, str] = {
        "代码": "code",
        "名称": "name",
        "市场": "market",
    }

    @classmethod
    def transform_daily_data(
        cls,
        df: pd.DataFrame,
        set_date_index: bool = True,
        drop_duplicates: bool = True
    ) -> pd.DataFrame:
        """
        转换日线数据格式

        处理步骤：
        1. 列名映射（中文 -> 英文）
        2. 日期格式转换
        3. 设置日期索引（可选）
        4. 去重（可选）

        Args:
            df: 原始数据 DataFrame
            set_date_index: 是否设置日期为索引（默认 True）
            drop_duplicates: 是否删除重复数据（默认 True）

        Returns:
            转换后的 DataFrame

        Raises:
            ValueError: 缺少必需列或数据为空

        Examples:
            >>> df = pd.DataFrame({
            ...     '日期': ['2024-01-01', '2024-01-02'],
            ...     '开盘': [10.0, 10.5],
            ...     '收盘': [10.5, 11.0]
            ... })
            >>> df_transformed = DataTransformer.transform_daily_data(df)
            >>> print(df_transformed.index.name)  # 'date'
            >>> print('open' in df_transformed.columns)  # True
        """
        if df is None or df.empty:
            raise ValueError("DataFrame 为空，无法转换")

        df = df.copy()

        # 1. 列名映射
        df = cls._rename_columns(df, cls.DAILY_DATA_COLUMN_MAPPING)

        # 2. 日期处理
        if "date" in df.columns:
            df = cls._standardize_date_column(df, "date")

            # 3. 设置日期索引
            if set_date_index and "date" in df.columns:
                df = df.set_index("date")
                logger.debug("已设置日期索引")

        # 4. 去重
        if drop_duplicates:
            original_len = len(df)
            df = df.drop_duplicates()
            if len(df) < original_len:
                logger.warning(f"删除重复数据: {original_len - len(df)} 条")

        logger.debug(f"完成日线数据转换: {len(df)} 条记录")
        return df

    @classmethod
    def transform_stock_list(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        转换股票列表格式

        Args:
            df: 原始股票列表 DataFrame

        Returns:
            转换后的 DataFrame

        Raises:
            ValueError: 数据为空或缺少必需列

        Examples:
            >>> df = pd.DataFrame({'代码': ['000001'], '名称': ['平安银行']})
            >>> df_transformed = DataTransformer.transform_stock_list(df)
            >>> print('code' in df_transformed.columns)  # True
        """
        if df is None or df.empty:
            raise ValueError("股票列表 DataFrame 为空")

        df = df.copy()

        # 列名映射
        df = cls._rename_columns(df, cls.STOCK_LIST_COLUMN_MAPPING)

        # 验证必需列
        required_columns = {"code", "name"}
        missing = required_columns - set(df.columns)
        if missing:
            raise ValueError(f"股票列表缺少必需列: {', '.join(missing)}")

        # 去重
        original_len = len(df)
        df = df.drop_duplicates(subset=["code"])
        if len(df) < original_len:
            logger.warning(f"删除重复股票代码: {original_len - len(df)} 条")

        logger.debug(f"完成股票列表转换: {len(df)} 条记录")
        return df

    @classmethod
    def _rename_columns(cls, df: pd.DataFrame, mapping: Dict[str, str]) -> pd.DataFrame:
        """
        根据映射表重命名列

        Args:
            df: DataFrame
            mapping: 列名映射字典

        Returns:
            重命名后的 DataFrame
        """
        # 只重命名存在的列
        rename_dict = {old: new for old, new in mapping.items() if old in df.columns}

        if rename_dict:
            df = df.rename(columns=rename_dict)
            logger.debug(f"重命名列: {len(rename_dict)} 个")

        return df

    @classmethod
    def _standardize_date_column(cls, df: pd.DataFrame, column: str = "date") -> pd.DataFrame:
        """
        标准化日期列格式

        支持的输入格式：
        - YYYYMMDD (如 20240101)
        - YYYY-MM-DD (如 2024-01-01)
        - datetime 对象

        Args:
            df: DataFrame
            column: 日期列名（默认 'date'）

        Returns:
            日期列转换为 datetime 类型的 DataFrame
        """
        if column not in df.columns:
            logger.warning(f"DataFrame 缺少日期列: {column}")
            return df

        try:
            # 尝试转换为 datetime
            df[column] = pd.to_datetime(df[column], errors="coerce")

            # 检查是否有无效日期
            null_count = df[column].isna().sum()
            if null_count > 0:
                logger.warning(f"日期列包含 {null_count} 个无效值")

            logger.debug(f"标准化日期列: {column}")
            return df

        except Exception as e:
            logger.error(f"日期列转换失败 ({column}): {e}")
            raise ValueError(f"无法转换日期列 '{column}': {e}")

    @classmethod
    def add_trade_date_column(cls, df: pd.DataFrame, format: str = "%Y%m%d") -> pd.DataFrame:
        """
        从日期索引生成 trade_date 列

        Args:
            df: 包含日期索引的 DataFrame
            format: 日期格式（默认 '%Y%m%d'）

        Returns:
            添加了 trade_date 列的 DataFrame

        Examples:
            >>> df = pd.DataFrame({'close': [10.0]}, index=pd.to_datetime(['2024-01-01']))
            >>> df = DataTransformer.add_trade_date_column(df)
            >>> print(df['trade_date'].iloc[0])  # '20240101'
        """
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("DataFrame 必须使用 DatetimeIndex")

        df = df.copy()
        df["trade_date"] = df.index.strftime(format)

        logger.debug(f"添加 trade_date 列 (format={format})")
        return df

    @classmethod
    def parse_date_string(cls, date_str: str, input_format: Optional[str] = None, output_format: str = "%Y%m%d") -> str:
        """
        解析日期字符串并转换格式

        Args:
            date_str: 输入日期字符串
            input_format: 输入���式（None 表示自动识别）
            output_format: 输出格式（默认 '%Y%m%d'）

        Returns:
            转换后的日期字符串

        Examples:
            >>> DataTransformer.parse_date_string('2024-01-01')
            '20240101'
            >>> DataTransformer.parse_date_string('20240101', output_format='%Y-%m-%d')
            '2024-01-01'
        """
        try:
            if input_format:
                dt = pd.to_datetime(date_str, format=input_format)
            else:
                dt = pd.to_datetime(date_str)

            return dt.strftime(output_format)

        except Exception as e:
            logger.error(f"日期字符串解析失败 (date_str={date_str}): {e}")
            raise ValueError(f"无法解析日期字符串: {date_str}")

    @classmethod
    def validate_dataframe(cls, df: pd.DataFrame, required_columns: set) -> bool:
        """
        验证 DataFrame 是否包含必需列

        Args:
            df: DataFrame
            required_columns: 必需列集合

        Returns:
            是否包含所有必需列

        Examples:
            >>> df = pd.DataFrame({'code': ['000001'], 'name': ['平安银行']})
            >>> DataTransformer.validate_dataframe(df, {'code', 'name'})
            True
            >>> DataTransformer.validate_dataframe(df, {'code', 'market'})
            False
        """
        if df is None or df.empty:
            logger.warning("DataFrame 为空")
            return False

        missing = required_columns - set(df.columns)
        if missing:
            logger.warning(f"DataFrame 缺少必需列: {', '.join(missing)}")
            return False

        return True

    @classmethod
    def convert_numeric_columns(
        cls,
        df: pd.DataFrame,
        columns: Optional[list] = None,
        errors: str = "coerce"
    ) -> pd.DataFrame:
        """
        将指定列转换为数值类型

        Args:
            df: DataFrame
            columns: 列名列表（None 表示所有数值类型列）
            errors: 错误处理方式（'coerce' 或 'raise'）

        Returns:
            转换后的 DataFrame

        Examples:
            >>> df = pd.DataFrame({'price': ['10.0', '20.5', 'N/A']})
            >>> df = DataTransformer.convert_numeric_columns(df, ['price'])
            >>> print(df['price'].dtype)  # float64
        """
        df = df.copy()

        if columns is None:
            # 自动检测数值列
            columns = df.select_dtypes(include=["object"]).columns.tolist()

        for col in columns:
            if col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col], errors=errors)
                    logger.debug(f"转换列为数值类型: {col}")
                except Exception as e:
                    logger.warning(f"列 {col} 转换失败: {e}")

        return df

    @classmethod
    def remove_null_rows(cls, df: pd.DataFrame, columns: Optional[list] = None) -> pd.DataFrame:
        """
        删除包含空值的行

        Args:
            df: DataFrame
            columns: 检查的列名列表（None 表示所有列）

        Returns:
            删除空值后的 DataFrame

        Examples:
            >>> df = pd.DataFrame({'a': [1, None, 3], 'b': [4, 5, 6]})
            >>> df = DataTransformer.remove_null_rows(df)
            >>> print(len(df))  # 2
        """
        original_len = len(df)

        if columns:
            df = df.dropna(subset=columns)
        else:
            df = df.dropna()

        removed = original_len - len(df)
        if removed > 0:
            logger.debug(f"删除空值行: {removed} 条")

        return df
