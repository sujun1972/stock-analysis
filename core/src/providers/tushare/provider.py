"""
Tushare 数据提供者主类

整合 API 客户端和数据转换器，实现 BaseDataProvider 接口
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
from src.utils.logger import get_logger
from ..base_provider import BaseDataProvider
from .api_client import TushareAPIClient
from .data_converter import TushareDataConverter
from .config import TushareConfig, TushareFields
from .exceptions import TushareDataError

logger = get_logger(__name__)


class TushareProvider(BaseDataProvider):
    """
    Tushare Pro 数据提供者

    特点:
    - 数据质量高，覆盖全面
    - 需要积分和 Token
    - 有积分限制和频率限制

    积分要求:
    - 日线数据: 120 积分
    - 分钟数据: 2000 积分
    - 实时行情: 5000 积分

    注意事项:
    - 每分钟调用次数有限制（与积分等级相关）
    - 建议请求间隔 >= 0.2秒
    - 超出限制会返回错误
    """

    def __init__(self, **kwargs: Any) -> None:
        """
        初始化 Tushare 提供者

        Args:
            **kwargs:
                - token: Tushare API Token (必需)
                - timeout: 请求超时时间（秒，默认 30）
                - retry_count: 失败重试次数（默认 3）
                - retry_delay: 重试延迟（秒，默认 1）
                - request_delay: 请求间隔（秒，默认 0.2）
        """
        # 先设置属性
        self.token: str = kwargs.get('token', '')
        self.timeout: int = kwargs.get('timeout', TushareConfig.DEFAULT_TIMEOUT)
        self.retry_count: int = kwargs.get('retry_count', TushareConfig.DEFAULT_RETRY_COUNT)
        self.retry_delay: int = kwargs.get('retry_delay', TushareConfig.DEFAULT_RETRY_DELAY)
        self.request_delay: float = kwargs.get('request_delay', TushareConfig.DEFAULT_REQUEST_DELAY)

        # 初始化 API 客户端
        self.api_client: Optional[TushareAPIClient] = None

        # 初始化数据转换器
        self.converter = TushareDataConverter()

        # 调用父类初始化（会调用 _validate_config）
        super().__init__(**kwargs)

        logger.info("TushareProvider 初始化成功")

    def _validate_config(self) -> None:
        """验证配置并初始化 API 客户端"""
        if not self.token:
            raise ValueError("Tushare Token 未配置，请在系统设置中配置 Token")

        # 初始化 API 客户端
        self.api_client = TushareAPIClient(
            token=self.token,
            timeout=self.timeout,
            retry_count=self.retry_count,
            retry_delay=self.retry_delay,
            request_delay=self.request_delay
        )

    # ========== 股票列表相关 ==========

    def get_stock_list(self) -> pd.DataFrame:
        """
        获取全部 A 股股票列表

        Returns:
            pd.DataFrame: 标准化的股票列表

        Raises:
            TushareDataError: 获取数据失败
        """
        try:
            logger.info("正在从 Tushare 获取股票列表...")

            # 获取股票基本信息
            df = self.api_client.execute(
                self.api_client.stock_basic,
                exchange='',
                list_status='L',  # L: 上市, D: 退市, P: 暂停上市
                fields=TushareFields.STOCK_LIST_FIELDS
            )

            if df is None or df.empty:
                raise TushareDataError("获取股票列表失败，返回数据为空")

            # 转换为标准格式
            df = self.converter.convert_stock_list(df)

            logger.info(f"成功获取 {len(df)} 只股票")
            return df

        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            raise

    def get_new_stocks(self, days: int = 30) -> pd.DataFrame:
        """
        获取最近 N 天上市的新股

        Args:
            days: 最近天数

        Returns:
            pd.DataFrame: 标准化的新股列表

        Raises:
            TushareDataError: 获取数据失败
        """
        try:
            logger.info(f"正在从 Tushare 获取最近 {days} 天的新股...")

            # 计算日期范围
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

            # 使用 new_share 接口获取新股上市日历
            df = self.api_client.execute(
                self.api_client.new_share,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                logger.warning("未获取到新股数据，尝试使用 stock_basic 接口")
                # 备用方案：从 stock_basic 筛选最近上市的股票
                df_all = self.api_client.execute(
                    self.api_client.stock_basic,
                    exchange='',
                    list_status='L',
                    fields=TushareFields.STOCK_LIST_FIELDS
                )
                df_all['list_date'] = pd.to_datetime(
                    df_all['list_date'],
                    format='%Y%m%d',
                    errors='coerce'
                )
                cutoff_date = datetime.now() - timedelta(days=days)
                df = df_all[df_all['list_date'] >= cutoff_date]

            # 转换为标准格式
            df = self.converter.convert_new_stocks(df)

            logger.info(f"成功获取 {len(df)} 只新股")
            return df

        except Exception as e:
            logger.error(f"获取新股列表失败: {e}")
            raise

    def get_delisted_stocks(self) -> pd.DataFrame:
        """
        获取退市股票列表

        Returns:
            pd.DataFrame: 标准化的退市股票列表

        Raises:
            TushareDataError: 获取数据失败
        """
        try:
            logger.info("正在从 Tushare 获取退市股票列表...")

            # 使用 stock_basic 接口，list_status='D' 获取退市股票
            df = self.api_client.execute(
                self.api_client.stock_basic,
                exchange='',
                list_status='D',  # 退市
                fields=TushareFields.DELISTED_STOCK_FIELDS
            )

            if df is None or df.empty:
                raise TushareDataError("获取退市股票列表失败，返回数据为空")

            # 转换为标准格式
            df = self.converter.convert_delisted_stocks(df)

            logger.info(f"成功获取 {len(df)} 只退市股票")
            return df

        except Exception as e:
            logger.error(f"获取退市股票列表失败: {e}")
            raise

    # ========== 日线数据相关 ==========

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
            code: 股票代码 (不含后缀)
            start_date: 开始日期 (YYYYMMDD 或 YYYY-MM-DD)
            end_date: 结束日期
            adjust: 复权方式 ('qfq', 'hfq', '')

        Returns:
            pd.DataFrame: 标准化的日线数据
        """
        try:
            # 标准化日期格式
            start = self.normalize_date(start_date) if start_date else \
                (datetime.now() - timedelta(days=TushareConfig.DEFAULT_HISTORY_DAYS)).strftime('%Y%m%d')
            end = self.normalize_date(end_date) if end_date else \
                datetime.now().strftime('%Y%m%d')

            # 转换为 Tushare 格式的股票代码
            ts_code = self.converter.to_ts_code(code)

            logger.debug(f"获取 {ts_code} 日线数据: {start} - {end}, 复权: {adjust}")

            # 根据复权类型选择接口参数
            params = {
                'ts_code': ts_code,
                'start_date': start,
                'end_date': end
            }

            if adjust == 'qfq':
                params['adj'] = 'qfq'  # 前复权
            elif adjust == 'hfq':
                params['adj'] = 'hfq'  # 后复权

            # 调用 API
            df = self.api_client.execute(self.api_client.daily, **params)

            if df is None or df.empty:
                logger.warning(f"{code}: 无数据")
                return pd.DataFrame()

            # 转换为标准格式
            df = self.converter.convert_daily_data(df)

            logger.debug(f"成功获取 {code} 日线数据 {len(df)} 条")
            return df

        except Exception as e:
            logger.error(f"获取 {code} 日线数据失败: {e}")
            raise

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
            Dict[str, pd.DataFrame]: 股票代码到数据的映射
        """
        result = {}

        for i, code in enumerate(codes, 1):
            try:
                logger.info(f"[{i}/{len(codes)}] 获取 {code} 日线数据")
                df = self.get_daily_data(code, start_date, end_date, adjust)
                if not df.empty:
                    result[code] = df
            except Exception as e:
                logger.error(f"获取 {code} 日线数据失败: {e}")
                continue

        logger.info(f"批量获取完成，成功: {len(result)}/{len(codes)}")
        return result

    # ========== 分时数据相关 ==========

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

        注意: Tushare 分时数据需要 2000 积分

        Args:
            code: 股票代码
            period: 分时周期 ('1', '5', '15', '30', '60')
            start_date: 开始日期时间
            end_date: 结束日期时间
            adjust: 复权方式

        Returns:
            pd.DataFrame: 标准化的分时数据
        """
        try:
            # 标准化日期格式
            start = self.normalize_date(start_date) if start_date else \
                (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')
            end = self.normalize_date(end_date) if end_date else \
                datetime.now().strftime('%Y%m%d')

            # 转换为 Tushare 格式的股票代码
            ts_code = self.converter.to_ts_code(code)

            logger.debug(f"获取 {ts_code} {period}分钟数据: {start} - {end}")

            # 映射周期
            freq = TushareConfig.MINUTE_FREQ_MAP.get(period, '5min')

            # 获取分时数据（需要高积分）
            df = self.api_client.execute(
                self.api_client.stk_mins,
                ts_code=ts_code,
                start_date=start,
                end_date=end,
                freq=freq,
                adj=adjust
            )

            if df is None or df.empty:
                logger.warning(f"{code}: 无分时数据")
                return pd.DataFrame()

            # 转换为标准格式
            df = self.converter.convert_minute_data(df, period)

            logger.debug(f"成功获取 {code} 分时数据 {len(df)} 条")
            return df

        except Exception as e:
            logger.error(f"获取 {code} 分时数据失败: {e}")
            raise

    # ========== 实时行情相关 ==========

    def get_realtime_quotes(
        self,
        codes: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        获取实时行情数据

        注意: Tushare 实时行情需要 5000 积分

        Args:
            codes: 股票代码列表 (None 表示获取全部)

        Returns:
            pd.DataFrame: 标准化的实时行情数据
        """
        try:
            logger.info("正在获取实时行情...")

            # 如果指定了代码列表，转换格式
            ts_codes = None
            if codes:
                ts_codes = ','.join([self.converter.to_ts_code(code) for code in codes])

            # 获取实时行情（需要高积分）
            df = self.api_client.execute(
                self.api_client.realtime_quotes,
                ts_code=ts_codes
            )

            if df is None or df.empty:
                raise TushareDataError("获取实时行情失败，返回数据为空")

            # 转换为标准格式
            df = self.converter.convert_realtime_quotes(df)

            logger.info(f"成功获取 {len(df)} 只股票的实时行情")
            return df

        except Exception as e:
            logger.error(f"获取实时行情失败: {e}")
            raise

    def __repr__(self) -> str:
        token_preview = f"{self.token[:8]}***" if self.token else "未配置"
        return f"<TushareProvider token={token_preview}>"
