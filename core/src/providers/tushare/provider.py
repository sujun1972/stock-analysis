"""
Tushare 数据提供者主类

整合 API 客户端和数据转换器，实现 BaseDataProvider 接口
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import time
import pandas as pd
from src.utils.logger import get_logger
from src.utils.response import Response
from ..base_provider import BaseDataProvider
from .api_client import TushareAPIClient
from .data_converter import TushareDataConverter
from .config import TushareConfig, TushareFields
from .exceptions import (
    TushareDataError,
    TusharePermissionError,
    TushareRateLimitError
)

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

    def get_stock_list(self) -> Response:
        """
        获取全部 A 股股票列表

        Returns:
            Response: 响应对象
                - data: pd.DataFrame 标准化的股票列表
                - metadata: 元数据(n_stocks, provider)
        """
        try:
            start_time = time.time()
            logger.info("正在从 Tushare 获取股票列表...")

            # 获取股票基本信息
            df = self.api_client.execute(
                self.api_client.stock_basic,
                exchange='',
                list_status='L',  # L: 上市, D: 退市, P: 暂停上市
                fields=TushareFields.STOCK_LIST_FIELDS
            )

            if df is None or df.empty:
                return Response.error(
                    error="获取股票列表失败，返回数据为空",
                    error_code="TUSHARE_EMPTY_DATA",
                    provider=self.provider_name
                )

            # 转换为标准格式
            df = self.converter.convert_stock_list(df)
            elapsed = time.time() - start_time

            logger.info(f"成功获取 {len(df)} 只股票")
            return Response.success(
                data=df,
                message=f"成功获取 {len(df)} 只股票",
                n_stocks=len(df),
                provider=self.provider_name,
                elapsed_time=f"{elapsed:.2f}s"
            )

        except TusharePermissionError as e:
            logger.error(f"获取股票列表失败: {e}")
            return Response.error(
                error=str(e),
                error_code="TUSHARE_PERMISSION_ERROR",
                provider=self.provider_name
            )
        except TushareRateLimitError as e:
            logger.error(f"获取股票列表失败: {e}")
            return Response.error(
                error=str(e),
                error_code="TUSHARE_RATE_LIMIT_ERROR",
                provider=self.provider_name,
                retry_after=e.retry_after
            )
        except TushareDataError as e:
            logger.error(f"获取股票列表失败: {e}")
            return Response.error(
                error=str(e),
                error_code="TUSHARE_DATA_ERROR",
                provider=self.provider_name
            )
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return Response.error(
                error=f"获取股票列表失败: {str(e)}",
                error_code="TUSHARE_UNEXPECTED_ERROR",
                provider=self.provider_name
            )

    def get_new_stocks(self, days: int = 30) -> Response:
        """
        获取最近 N 天上市的新股

        Args:
            days: 最近天数

        Returns:
            Response: 响应对象
                - data: pd.DataFrame 标准化的新股列表
                - metadata: 元数据(n_stocks, days)
        """
        try:
            start_time = time.time()
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
            elapsed = time.time() - start_time

            logger.info(f"成功获取 {len(df)} 只新股")
            return Response.success(
                data=df,
                message=f"成功获取最近 {days} 天的 {len(df)} 只新股",
                n_stocks=len(df),
                days=days,
                provider=self.provider_name,
                elapsed_time=f"{elapsed:.2f}s"
            )

        except TusharePermissionError as e:
            logger.error(f"获取新股列表失败: {e}")
            return Response.error(
                error=str(e),
                error_code="TUSHARE_PERMISSION_ERROR",
                provider=self.provider_name,
                days=days
            )
        except TushareRateLimitError as e:
            logger.error(f"获取新股列表失败: {e}")
            return Response.error(
                error=str(e),
                error_code="TUSHARE_RATE_LIMIT_ERROR",
                provider=self.provider_name,
                days=days,
                retry_after=e.retry_after
            )
        except TushareDataError as e:
            logger.error(f"获取新股列表失败: {e}")
            return Response.error(
                error=str(e),
                error_code="TUSHARE_DATA_ERROR",
                provider=self.provider_name,
                days=days
            )
        except Exception as e:
            logger.error(f"获取新股列表失败: {e}")
            return Response.error(
                error=f"获取新股列表失败: {str(e)}",
                error_code="TUSHARE_UNEXPECTED_ERROR",
                provider=self.provider_name,
                days=days
            )

    def get_delisted_stocks(self) -> Response:
        """
        获取退市股票列表

        Returns:
            Response: 响应对象
                - data: pd.DataFrame 标准化的退市股票列表
                - metadata: 元数据(n_stocks)
        """
        try:
            start_time = time.time()
            logger.info("正在从 Tushare 获取退市股票列表...")

            # 使用 stock_basic 接口，list_status='D' 获取退市股票
            df = self.api_client.execute(
                self.api_client.stock_basic,
                exchange='',
                list_status='D',  # 退市
                fields=TushareFields.DELISTED_STOCK_FIELDS
            )

            if df is None or df.empty:
                return Response.error(
                    error="获取退市股票列表失败，返回数据为空",
                    error_code="TUSHARE_EMPTY_DATA",
                    provider=self.provider_name
                )

            # 转换为标准格式
            df = self.converter.convert_delisted_stocks(df)
            elapsed = time.time() - start_time

            logger.info(f"成功获取 {len(df)} 只退市股票")
            return Response.success(
                data=df,
                message=f"成功获取 {len(df)} 只退市股票",
                n_stocks=len(df),
                provider=self.provider_name,
                elapsed_time=f"{elapsed:.2f}s"
            )

        except TusharePermissionError as e:
            logger.error(f"获取退市股票列表失败: {e}")
            return Response.error(
                error=str(e),
                error_code="TUSHARE_PERMISSION_ERROR",
                provider=self.provider_name
            )
        except TushareRateLimitError as e:
            logger.error(f"获取退市股票列表失败: {e}")
            return Response.error(
                error=str(e),
                error_code="TUSHARE_RATE_LIMIT_ERROR",
                provider=self.provider_name,
                retry_after=e.retry_after
            )
        except TushareDataError as e:
            logger.error(f"获取退市股票列表失败: {e}")
            return Response.error(
                error=str(e),
                error_code="TUSHARE_DATA_ERROR",
                provider=self.provider_name
            )
        except Exception as e:
            logger.error(f"获取退市股票列表失败: {e}")
            return Response.error(
                error=f"获取退市股票列表失败: {str(e)}",
                error_code="TUSHARE_UNEXPECTED_ERROR",
                provider=self.provider_name
            )

    # ========== 日线数据相关 ==========

    def get_daily_data(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = 'qfq'
    ) -> Response:
        """
        获取股票日线数据

        Args:
            code: 股票代码 (不含后缀)
            start_date: 开始日期 (YYYYMMDD 或 YYYY-MM-DD)
            end_date: 结束日期
            adjust: 复权方式 ('qfq', 'hfq', '')

        Returns:
            Response: 响应对象
                - data: pd.DataFrame 标准化的日线数据
                - metadata: 元数据(code, n_records, date_range, adjust)
        """
        try:
            start_time = time.time()

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
                return Response.warning(
                    message=f"{code}: 无数据",
                    data=pd.DataFrame(),
                    code=code,
                    date_range=f"{start}~{end}",
                    adjust=adjust,
                    provider=self.provider_name
                )

            # 转换为标准格式
            df = self.converter.convert_daily_data(df)
            elapsed = time.time() - start_time

            logger.debug(f"成功获取 {code} 日线数据 {len(df)} 条")
            return Response.success(
                data=df,
                message=f"成功获取 {code} 日线数据",
                code=code,
                n_records=len(df),
                date_range=f"{start}~{end}",
                adjust=adjust,
                provider=self.provider_name,
                elapsed_time=f"{elapsed:.2f}s"
            )

        except TusharePermissionError as e:
            logger.error(f"获取 {code} 日线数据失败: {e}")
            return Response.error(
                error=str(e),
                error_code="TUSHARE_PERMISSION_ERROR",
                code=code,
                provider=self.provider_name
            )
        except TushareRateLimitError as e:
            logger.error(f"获取 {code} 日线数据失败: {e}")
            return Response.error(
                error=str(e),
                error_code="TUSHARE_RATE_LIMIT_ERROR",
                code=code,
                provider=self.provider_name,
                retry_after=e.retry_after
            )
        except TushareDataError as e:
            logger.error(f"获取 {code} 日线数据失败: {e}")
            return Response.error(
                error=str(e),
                error_code="TUSHARE_DATA_ERROR",
                code=code,
                provider=self.provider_name
            )
        except Exception as e:
            logger.error(f"获取 {code} 日线数据失败: {e}")
            return Response.error(
                error=f"获取日线数据失败: {str(e)}",
                error_code="TUSHARE_UNEXPECTED_ERROR",
                code=code,
                provider=self.provider_name
            )

    def get_daily_batch(
        self,
        codes: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = 'qfq'
    ) -> Response:
        """
        批量获取多只股票的日线数据

        Args:
            codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            adjust: 复权方式

        Returns:
            Response: 响应对象
                - data: Dict[str, pd.DataFrame] 股票代码到数据的映射
                - metadata: 元数据(n_stocks, n_success, n_failed, failed_codes)
        """
        start_time = time.time()
        result = {}
        failed_codes = []

        for i, code in enumerate(codes, 1):
            try:
                logger.info(f"[{i}/{len(codes)}] 获取 {code} 日线数据")
                response = self.get_daily_data(code, start_date, end_date, adjust)
                if response.is_success() and response.data is not None and not response.data.empty:
                    result[code] = response.data
                else:
                    failed_codes.append(code)
            except Exception as e:
                logger.error(f"获取 {code} 日线数据失败: {e}")
                failed_codes.append(code)
                continue

        elapsed = time.time() - start_time
        n_success = len(result)
        n_failed = len(failed_codes)

        logger.info(f"批量获取完成，成功: {n_success}/{len(codes)}")

        if n_success == 0:
            return Response.error(
                error="批量获取失败，所有股票数据获取失败",
                error_code="TUSHARE_BATCH_ALL_FAILED",
                data={},
                n_stocks=len(codes),
                n_success=0,
                n_failed=n_failed,
                failed_codes=failed_codes,
                provider=self.provider_name
            )
        elif n_failed > 0:
            return Response.warning(
                message=f"批量获取完成，部分失败 (成功: {n_success}/{len(codes)})",
                data=result,
                n_stocks=len(codes),
                n_success=n_success,
                n_failed=n_failed,
                failed_codes=failed_codes,
                provider=self.provider_name,
                elapsed_time=f"{elapsed:.2f}s"
            )
        else:
            return Response.success(
                data=result,
                message=f"批量获取完成 (成功: {n_success}/{len(codes)})",
                n_stocks=len(codes),
                n_success=n_success,
                n_failed=0,
                provider=self.provider_name,
                elapsed_time=f"{elapsed:.2f}s"
            )

    # ========== 分时数据相关 ==========

    def get_minute_data(
        self,
        code: str,
        period: str = '5',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = ''
    ) -> Response:
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
            Response: 响应对象
                - data: pd.DataFrame 标准化的分时数据
                - metadata: 元数据(code, period, n_records)
        """
        try:
            start_time = time.time()

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
                return Response.warning(
                    message=f"{code}: 无分时数据",
                    data=pd.DataFrame(),
                    code=code,
                    period=period,
                    provider=self.provider_name
                )

            # 转换为标准格式
            df = self.converter.convert_minute_data(df, period)
            elapsed = time.time() - start_time

            logger.debug(f"成功获取 {code} 分时数据 {len(df)} 条")
            return Response.success(
                data=df,
                message=f"成功获取 {code} {period}分钟数据",
                code=code,
                period=period,
                n_records=len(df),
                provider=self.provider_name,
                elapsed_time=f"{elapsed:.2f}s"
            )

        except TusharePermissionError as e:
            logger.error(f"获取 {code} 分时数据失败: {e}")
            return Response.error(
                error=str(e),
                error_code="TUSHARE_PERMISSION_ERROR",
                code=code,
                period=period,
                provider=self.provider_name
            )
        except TushareRateLimitError as e:
            logger.error(f"获取 {code} 分时数据失败: {e}")
            return Response.error(
                error=str(e),
                error_code="TUSHARE_RATE_LIMIT_ERROR",
                code=code,
                period=period,
                provider=self.provider_name,
                retry_after=e.retry_after
            )
        except TushareDataError as e:
            logger.error(f"获取 {code} 分时数据失败: {e}")
            return Response.error(
                error=str(e),
                error_code="TUSHARE_DATA_ERROR",
                code=code,
                period=period,
                provider=self.provider_name
            )
        except Exception as e:
            logger.error(f"获取 {code} 分时数据失败: {e}")
            return Response.error(
                error=f"获取分时数据失败: {str(e)}",
                error_code="TUSHARE_UNEXPECTED_ERROR",
                code=code,
                period=period,
                provider=self.provider_name
            )

    # ========== 实时行情相关 ==========

    def get_realtime_quotes(
        self,
        codes: Optional[List[str]] = None
    ) -> Response:
        """
        获取实时行情数据

        注意: Tushare 实时行情需要 5000 积分

        Args:
            codes: 股票代码列表 (None 表示获取全部)

        Returns:
            Response: 响应对象
                - data: pd.DataFrame 标准化的实时行情数据
                - metadata: 元数据(n_stocks)
        """
        try:
            start_time = time.time()
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
                return Response.error(
                    error="获取实时行情失败，返回数据为空",
                    error_code="TUSHARE_EMPTY_DATA",
                    provider=self.provider_name
                )

            # 转换为标准格式
            df = self.converter.convert_realtime_quotes(df)
            elapsed = time.time() - start_time

            logger.info(f"成功获取 {len(df)} 只股票的实时行情")
            return Response.success(
                data=df,
                message=f"成功获取 {len(df)} 只股票的实时行情",
                n_stocks=len(df),
                provider=self.provider_name,
                elapsed_time=f"{elapsed:.2f}s"
            )

        except TusharePermissionError as e:
            logger.error(f"获取实时行情失败: {e}")
            return Response.error(
                error=str(e),
                error_code="TUSHARE_PERMISSION_ERROR",
                provider=self.provider_name
            )
        except TushareRateLimitError as e:
            logger.error(f"获取实时行情失败: {e}")
            return Response.error(
                error=str(e),
                error_code="TUSHARE_RATE_LIMIT_ERROR",
                provider=self.provider_name,
                retry_after=e.retry_after
            )
        except TushareDataError as e:
            logger.error(f"获取实时行情失败: {e}")
            return Response.error(
                error=str(e),
                error_code="TUSHARE_DATA_ERROR",
                provider=self.provider_name
            )
        except Exception as e:
            logger.error(f"获取实时行情失败: {e}")
            return Response.error(
                error=f"获取实时行情失败: {str(e)}",
                error_code="TUSHARE_UNEXPECTED_ERROR",
                provider=self.provider_name
            )

    def __repr__(self) -> str:
        token_preview = f"{self.token[:8]}***" if self.token else "未配置"
        return f"<TushareProvider token={token_preview}>"
