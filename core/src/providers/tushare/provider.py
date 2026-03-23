"""
Tushare 数据提供者主类

整合 API 客户端和数据转换器，实现 BaseDataProvider 接口
"""

from typing import Optional, List, Dict, Any, Callable
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
        codes: Optional[List[str]] = None,
        save_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Response:
        """
        获取最新行情数据

        实现策略：
        1. 主要使用 daily 接口获取最近交易日数据
        2. 可选：对少量股票使用分钟数据获取盘中价格（需高级权限）

        注意事项：
        - 交易日15:00后可获取当天收盘数据
        - 非交易时段获取的是最近交易日数据
        - stk_mins 接口限制严格（2次/天），谨慎使用

        Args:
            codes: 股票代码列表 (None 表示获取全部)
            save_callback: 增量保存回调函数

        Returns:
            Response: 包含行情数据的响应对象
        """
        try:
            start_time = time.time()

            # 由于stk_mins接口限制严格（每天2次），默认使用daily接口
            # 如需使用分钟数据，可单独调用 get_minute_data 方法
            use_minute_data = False  # 可通过环境变量或配置控制

            if use_minute_data and codes and len(codes) <= 5:  # 严格限制使用场景
                logger.info("正在获取最新行情（使用分钟数据）...")
                minute_df = self._get_quotes_from_minute_data(codes)
                if minute_df is not None and not minute_df.empty:
                    # 如果提供了保存回调，逐条调用
                    if save_callback:
                        for _, row in minute_df.iterrows():
                            quote_dict = row.to_dict()
                            try:
                                save_callback(quote_dict)
                            except Exception as e:
                                logger.warning(f"保存回调失败 {quote_dict.get('code', 'Unknown')}: {e}")

                    elapsed = time.time() - start_time
                    logger.info(f"成功获取 {len(minute_df)} 只股票的最新行情（来自分钟数据）")
                    return Response.success(
                        data=minute_df,
                        message=f"成功获取 {len(minute_df)} 只股票的最新行情",
                        n_stocks=len(minute_df),
                        provider=self.provider_name,
                        elapsed_time=f"{elapsed:.2f}s"
                    )

            # 使用daily接口（主要方案）
            logger.info("正在获取最新行情（使用daily接口）...")

            # 如果指定了代码列表，转换格式
            ts_codes = None
            if codes:
                ts_codes = ','.join([self.converter.to_ts_code(code) for code in codes])

            # 使用 daily 接口获取最新数据
            # 指定今天日期，如果今天不是交易日会返回空，所以用日期范围
            from datetime import datetime, timedelta
            today = datetime.now().strftime('%Y%m%d')
            # 获取最近7天的数据，然后取最新的
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')

            df = self.api_client.execute(
                self.api_client.daily,
                ts_code=ts_codes,
                start_date=start_date,
                end_date=today
            )

            # 如果有数据，只保留每个股票的最新记录
            if df is not None and not df.empty:
                # 按股票代码和日期排序，保留每个股票最新的一条
                df = df.sort_values(['ts_code', 'trade_date'], ascending=[True, False])
                df = df.groupby('ts_code').first().reset_index()

            if df is None or df.empty:
                return Response.error(
                    error="获取最新行情失败，返回数据为空",
                    error_code="TUSHARE_EMPTY_DATA",
                    provider=self.provider_name
                )

            # 保存ts_code用于后续转换
            ts_code_series = df['ts_code'].copy() if 'ts_code' in df.columns else None

            # 转换为标准格式（复用daily数据转换）
            df = self.converter.convert_daily_data(df)

            # 转换股票代码格式（ts_code -> code）- 在convert_daily_data之后
            if ts_code_series is not None:
                df['code'] = ts_code_series.apply(self.converter.from_ts_code)

            # 添加 latest_price 字段（使用收盘价作为最新价）
            df['latest_price'] = df['close']
            df['trade_time'] = pd.to_datetime(df['trade_date'])

            # 添加name字段（daily接口不返回股票名称，暂时置空）
            if 'name' not in df.columns:
                df['name'] = ''

            # 如果提供了保存回调，逐条调用
            if save_callback:
                for _, row in df.iterrows():
                    quote_dict = row.to_dict()
                    try:
                        save_callback(quote_dict)
                    except Exception as e:
                        logger.warning(f"保存回调失败 {quote_dict.get('code', 'Unknown')}: {e}")

            elapsed = time.time() - start_time

            logger.info(f"成功获取 {len(df)} 只股票的最新行情（来自daily接口）")
            return Response.success(
                data=df,
                message=f"成功获取 {len(df)} 只股票的最新行情",
                n_stocks=len(df),
                provider=self.provider_name,
                elapsed_time=f"{elapsed:.2f}s"
            )

        except TusharePermissionError as e:
            logger.error(f"获取最新行情失败: {e}")
            return Response.error(
                error=str(e),
                error_code="TUSHARE_PERMISSION_ERROR",
                provider=self.provider_name
            )
        except TushareRateLimitError as e:
            logger.error(f"获取最新行情失败: {e}")
            return Response.error(
                error=str(e),
                error_code="TUSHARE_RATE_LIMIT_ERROR",
                provider=self.provider_name,
                retry_after=e.retry_after
            )
        except TushareDataError as e:
            logger.error(f"获取最新行情失败: {e}")
            return Response.error(
                error=str(e),
                error_code="TUSHARE_DATA_ERROR",
                provider=self.provider_name
            )
        except Exception as e:
            logger.error(f"获取最新行情失败: {e}")
            return Response.error(
                error=f"获取最新行情失败: {str(e)}",
                error_code="TUSHARE_UNEXPECTED_ERROR",
                provider=self.provider_name
            )

    def _get_quotes_from_minute_data(self, codes: List[str]) -> Optional[pd.DataFrame]:
        """
        从分钟数据获取最新行情（内部方法）

        Args:
            codes: 股票代码列表

        Returns:
            pd.DataFrame: 包含最新行情的DataFrame，失败返回None
        """
        try:
            from datetime import datetime, timedelta

            # 准备时间参数（获取最近1小时的数据）
            now = datetime.now()
            end_time = now.strftime('%Y-%m-%d %H:%M:%S')
            start_time_str = (now - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')

            all_data = []

            # 逐个股票获取分钟数据
            for code in codes:
                ts_code = self.converter.to_ts_code(code)

                try:
                    # 获取分钟数据
                    df_min = self.api_client.execute(
                        self.api_client.stk_mins,
                        ts_code=ts_code,
                        freq='1min',
                        start_date=start_time_str,
                        end_date=end_time
                    )

                    if df_min is not None and not df_min.empty:
                        # 取最新的一条记录
                        latest = df_min.iloc[-1]

                        # 构建实时行情数据
                        quote_data = {
                            'code': code,
                            'name': '',  # 分钟数据不含股票名称
                            'latest_price': float(latest['close']),
                            'open': float(latest['open']),
                            'high': float(latest['high']),
                            'low': float(latest['low']),
                            'close': float(latest['close']),
                            'trade_time': pd.to_datetime(latest['trade_time']),
                            'trade_date': pd.to_datetime(latest['trade_time']).date(),
                            'volume': float(latest.get('vol', 0)) * 100,  # 手转股
                            'amount': float(latest.get('amount', 0)) * 1000,  # 千元转元
                            'pct_change': 0,  # 分钟数据无涨跌幅
                            'change_amount': 0,
                            'amplitude': 0
                        }

                        all_data.append(quote_data)
                    else:
                        logger.info(f"{code}: 无分钟数据")

                except Exception as e:
                    logger.warning(f"获取 {code} 分钟数据失败: {e}")
                    continue

            if all_data:
                return pd.DataFrame(all_data)
            return None

        except Exception as e:
            logger.warning(f"获取分钟数据失败: {e}")
            return None

    # ========== 扩展数据获取方法 ==========

    def get_daily_basic(self, ts_code: Optional[str] = None,
                       trade_date: Optional[str] = None,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取每日指标数据
        积分消耗：120分

        Args:
            ts_code: 股票代码
            trade_date: 交易日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            pd.DataFrame: 每日指标数据
        """
        try:
            logger.info(f"获取每日指标数据: ts_code={ts_code}, trade_date={trade_date}")
            df = self.api_client.query('daily_basic',
                                     ts_code=ts_code,
                                     trade_date=trade_date,
                                     start_date=start_date,
                                     end_date=end_date)
            return df
        except Exception as e:
            logger.error(f"获取每日指标数据失败: {e}")
            raise TushareDataError(f"获取每日指标数据失败: {str(e)}")

    def get_moneyflow(self, ts_code: Optional[str] = None,
                     trade_date: Optional[str] = None,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取个股资金流向
        积分消耗：2000分

        Args:
            ts_code: 股票代码
            trade_date: 交易日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            pd.DataFrame: 资金流向数据
        """
        try:
            logger.info(f"获取资金流向数据: ts_code={ts_code}, trade_date={trade_date}")
            df = self.api_client.query('moneyflow',
                                     ts_code=ts_code,
                                     trade_date=trade_date,
                                     start_date=start_date,
                                     end_date=end_date)
            return df
        except Exception as e:
            logger.error(f"获取资金流向数据失败: {e}")
            raise TushareDataError(f"获取资金流向数据失败: {str(e)}")

    def get_adj_factor(self, ts_code: Optional[str] = None,
                      trade_date: Optional[str] = None,
                      start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取复权因子
        积分消耗：120分

        Args:
            ts_code: 股票代码
            trade_date: 交易日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            pd.DataFrame: 复权因子数据
        """
        try:
            logger.info(f"获取复权因子数据: ts_code={ts_code}")
            df = self.api_client.query('adj_factor',
                                     ts_code=ts_code,
                                     trade_date=trade_date,
                                     start_date=start_date,
                                     end_date=end_date)
            return df
        except Exception as e:
            logger.error(f"获取复权因子数据失败: {e}")
            raise TushareDataError(f"获取复权因子数据失败: {str(e)}")

    def get_margin(self,
                   trade_date: Optional[str] = None,
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None,
                   exchange_id: Optional[str] = None) -> pd.DataFrame:
        """
        获取融资融券交易汇总数据
        积分消耗：2000分
        单次请求最大返回4000行数据

        Args:
            trade_date: 交易日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            exchange_id: 交易所代码（SSE上交所/SZSE深交所/BSE北交所）

        Returns:
            pd.DataFrame: 融资融券交易汇总数据，包含以下字段：
                - trade_date: 交易日期
                - exchange_id: 交易所代码
                - rzye: 融资余额(元)
                - rzmre: 融资买入额(元)
                - rzche: 融资偿还额(元)
                - rqye: 融券余额(元)
                - rqmcl: 融券卖出量(股,份,手)
                - rzrqye: 融资融券余额(元)
                - rqyl: 融券余量(股,份,手)
        """
        try:
            logger.info(f"获取融资融券交易汇总: trade_date={trade_date}, exchange_id={exchange_id}")
            df = self.api_client.query('margin',
                                     trade_date=trade_date,
                                     start_date=start_date,
                                     end_date=end_date,
                                     exchange_id=exchange_id)
            return df
        except Exception as e:
            logger.error(f"获取融资融券交易汇总失败: {e}")
            raise TushareDataError(f"获取融资融券交易汇总失败: {str(e)}")

    def get_slb_len(self,
                    trade_date: Optional[str] = None,
                    start_date: Optional[str] = None,
                    end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取转融资交易汇总数据
        积分消耗：2000分/分钟200次，5000分500次
        单次请求最大返回5000行数据

        Args:
            trade_date: 交易日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            pd.DataFrame: 转融资交易汇总数据，包含以下字段：
                - trade_date: 交易日期
                - ob: 期初余额(亿元)
                - auc_amount: 竞价成交金额(亿元)
                - repo_amount: 再借成交金额(亿元)
                - repay_amount: 偿还金额(亿元)
                - cb: 期末余额(亿元)
        """
        try:
            logger.info(f"获取转融资交易汇总: trade_date={trade_date}, start_date={start_date}, end_date={end_date}")
            df = self.api_client.query('slb_len',
                                     trade_date=trade_date,
                                     start_date=start_date,
                                     end_date=end_date)
            return df
        except Exception as e:
            logger.error(f"获取转融资交易汇总失败: {e}")
            raise TushareDataError(f"获取转融资交易汇总失败: {str(e)}")

    def get_margin_detail(self, ts_code: Optional[str] = None,
                         trade_date: Optional[str] = None,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取融资融券详细数据（个股）
        积分消耗：300分

        Args:
            ts_code: 股票代码
            trade_date: 交易日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            pd.DataFrame: 融资融券数据
        """
        try:
            logger.info(f"获取融资融券数据: ts_code={ts_code}, trade_date={trade_date}")
            df = self.api_client.query('margin_detail',
                                     ts_code=ts_code,
                                     trade_date=trade_date,
                                     start_date=start_date,
                                     end_date=end_date)
            return df
        except Exception as e:
            logger.error(f"获取融资融券数据失败: {e}")
            raise TushareDataError(f"获取融资融券数据失败: {str(e)}")

    def get_block_trade(self, ts_code: Optional[str] = None,
                       trade_date: Optional[str] = None,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取大宗交易数据
        积分消耗：300分

        Args:
            ts_code: 股票代码
            trade_date: 交易日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            pd.DataFrame: 大宗交易数据
        """
        try:
            logger.info(f"获取大宗交易数据: ts_code={ts_code}, trade_date={trade_date}")
            df = self.api_client.query('block_trade',
                                     ts_code=ts_code,
                                     trade_date=trade_date,
                                     start_date=start_date,
                                     end_date=end_date)
            return df
        except Exception as e:
            logger.error(f"获取大宗交易数据失败: {e}")
            raise TushareDataError(f"获取大宗交易数据失败: {str(e)}")

    def get_moneyflow_hsgt(self, trade_date: Optional[str] = None,
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取沪深港通资金流向数据
        积分消耗：2000分

        Args:
            trade_date: 交易日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            pd.DataFrame: 资金流向数据，包含以下字段：
                - trade_date: 交易日期
                - ggt_ss: 港股通（上海）百万元
                - ggt_sz: 港股通（深圳）百万元
                - hgt: 沪股通（百万元）
                - sgt: 深股通（百万元）
                - north_money: 北向资金（百万元）
                - south_money: 南向资金（百万元）
        """
        try:
            logger.info(f"获取沪深港通资金流向: trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

            # 注意：moneyflow_hsgt接口必须指定日期参数
            if trade_date:
                df = self.api_client.query('moneyflow_hsgt', trade_date=trade_date)
            elif start_date and end_date:
                df = self.api_client.query('moneyflow_hsgt', start_date=start_date, end_date=end_date)
            elif start_date:
                # 只有开始日期，默认到今天
                from datetime import datetime
                end_date = datetime.now().strftime('%Y%m%d')
                df = self.api_client.query('moneyflow_hsgt', start_date=start_date, end_date=end_date)
            else:
                # 获取最近30天的数据
                from datetime import datetime, timedelta
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

        Args:
            trade_date: 交易日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            pd.DataFrame: 大盘资金流向数据，包含以下字段：
                - trade_date: 交易日期
                - close_sh: 上证收盘价（点）
                - pct_change_sh: 上证涨跌幅(%)
                - close_sz: 深证收盘价（点）
                - pct_change_sz: 深证涨跌幅(%)
                - net_amount: 今日主力净流入净额（元）
                - net_amount_rate: 今日主力净流入净占比(%)
                - buy_elg_amount: 今日超大单净流入净额（元）
                - buy_elg_amount_rate: 今日超大单净流入净占比(%)
                - buy_lg_amount: 今日大单净流入净额（元）
                - buy_lg_amount_rate: 今日大单净流入净占比(%)
                - buy_md_amount: 今日中单净流入净额（元）
                - buy_md_amount_rate: 今日中单净流入净占比(%)
                - buy_sm_amount: 今日小单净流入净额（元）
                - buy_sm_amount_rate: 今日小单净流入净占比(%)
        """
        try:
            logger.info(f"获取大盘资金流向: trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

            if trade_date:
                df = self.api_client.query('moneyflow_mkt_dc', trade_date=trade_date)
            elif start_date and end_date:
                df = self.api_client.query('moneyflow_mkt_dc', start_date=start_date, end_date=end_date)
            elif start_date:
                # 只有开始日期，默认到今天
                from datetime import datetime
                end_date = datetime.now().strftime('%Y%m%d')
                df = self.api_client.query('moneyflow_mkt_dc', start_date=start_date, end_date=end_date)
            else:
                # 获取最近30天的数据
                from datetime import datetime, timedelta
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
                df = self.api_client.query('moneyflow_mkt_dc', start_date=start_date, end_date=end_date)

            return df
        except Exception as e:
            logger.error(f"获取大盘资金流向失败: {e}")
            raise TushareDataError(f"获取大盘资金流向失败: {str(e)}")

    def get_moneyflow_ind_dc(self,
                             ts_code: Optional[str] = None,
                             trade_date: Optional[str] = None,
                             start_date: Optional[str] = None,
                             end_date: Optional[str] = None,
                             content_type: Optional[str] = None) -> pd.DataFrame:
        """
        获取板块资金流向数据（东财概念及行业板块资金流向 DC）
        积分消耗：6000分

        Args:
            ts_code: 代码
            trade_date: 交易日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            content_type: 资金类型(行业、概念、地域)

        Returns:
            pd.DataFrame: 板块资金流向数据，包含以下字段：
                - trade_date: 交易日期
                - content_type: 数据类型
                - ts_code: DC板块代码（行业、概念、地域）
                - name: 板块名称
                - pct_change: 板块涨跌幅（%）
                - close: 板块最新指数
                - net_amount: 今日主力净流入净额（元）
                - net_amount_rate: 今日主力净流入净占比%
                - buy_elg_amount: 今日超大单净流入净额（元）
                - buy_elg_amount_rate: 今日超大单净流入净占比%
                - buy_lg_amount: 今日大单净流入净额（元）
                - buy_lg_amount_rate: 今日大单净流入净占比%
                - buy_md_amount: 今日中单净流入净额（元）
                - buy_md_amount_rate: 今日中单净流入净占比%
                - buy_sm_amount: 今日小单净流入净额（元）
                - buy_sm_amount_rate: 今日小单净流入净占比%
                - buy_sm_amount_stock: 今日主力净流入最大股
                - rank: 序号
        """
        try:
            logger.info(f"获取板块资金流向: ts_code={ts_code}, trade_date={trade_date}, start_date={start_date}, end_date={end_date}, content_type={content_type}")

            params = {}
            if ts_code:
                params['ts_code'] = ts_code
            if trade_date:
                params['trade_date'] = trade_date
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            if content_type:
                params['content_type'] = content_type

            df = self.api_client.query('moneyflow_ind_dc', **params)
            return df
        except Exception as e:
            logger.error(f"获取板块资金流向失败: {e}")
            raise TushareDataError(f"获取板块资金流向失败: {str(e)}")

    def get_moneyflow_stock_dc(self,
                               ts_code: Optional[str] = None,
                               trade_date: Optional[str] = None,
                               start_date: Optional[str] = None,
                               end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取个股资金流向数据（东方财富DC）
        积分消耗：5000分，单次最大6000条
        数据开始时间：20230911

        Args:
            ts_code: 股票代码
            trade_date: 交易日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            pd.DataFrame: 个股资金流向数据，包含以下字段：
                - trade_date: 交易日期
                - ts_code: 股票代码
                - name: 股票名称
                - pct_change: 涨跌幅(%)
                - close: 最新价（元）
                - net_amount: 今日主力净流入额（万元）
                - net_amount_rate: 今日主力净流入净占比(%)
                - buy_elg_amount: 今日超大单净流入额（万元）
                - buy_elg_amount_rate: 今日超大单净流入占比(%)
                - buy_lg_amount: 今日大单净流入额（万元）
                - buy_lg_amount_rate: 今日大单净流入占比(%)
                - buy_md_amount: 今日中单净流入额（万元）
                - buy_md_amount_rate: 今日中单净流入占比(%)
                - buy_sm_amount: 今日小单净流入额（万元）
                - buy_sm_amount_rate: 今日小单净流入占比(%)
        """
        try:
            logger.info(f"获取个股资金流向: ts_code={ts_code}, trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

            params = {}
            if ts_code:
                params['ts_code'] = ts_code
            if trade_date:
                params['trade_date'] = trade_date
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date

            df = self.api_client.query('moneyflow_dc', **params)
            return df
        except Exception as e:
            logger.error(f"获取个股资金流向失败: {e}")
            raise TushareDataError(f"获取个股资金流向失败: {str(e)}")

    def get_stk_limit(self, ts_code: Optional[str] = None,
                     trade_date: Optional[str] = None,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取每日涨跌停价格
        积分消耗：120分

        Args:
            ts_code: 股票代码
            trade_date: 交易日期 YYYYMMDD
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD

        Returns:
            pd.DataFrame: 涨跌停价格数据
        """
        try:
            logger.info(f"获取涨跌停价格数据: ts_code={ts_code}, trade_date={trade_date}")
            df = self.api_client.query('stk_limit',
                                     ts_code=ts_code,
                                     trade_date=trade_date,
                                     start_date=start_date,
                                     end_date=end_date)
            return df
        except Exception as e:
            logger.error(f"获取涨跌停价格数据失败: {e}")
            raise TushareDataError(f"获取涨跌停价格数据失败: {str(e)}")

    def get_suspend(self, ts_code: Optional[str] = None,
                   suspend_date: Optional[str] = None,
                   resume_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取停复牌信息
        积分消耗：120分

        Args:
            ts_code: 股票代码
            suspend_date: 停牌日期 YYYYMMDD
            resume_date: 复牌日期 YYYYMMDD

        Returns:
            pd.DataFrame: 停复牌信息数据
        """
        try:
            logger.info(f"获取停复牌信息: ts_code={ts_code}")
            df = self.api_client.query('suspend',
                                     ts_code=ts_code,
                                     suspend_date=suspend_date,
                                     resume_date=resume_date)
            return df
        except Exception as e:
            logger.error(f"获取停复牌信息失败: {e}")
            raise TushareDataError(f"获取停复牌信息失败: {str(e)}")

    def get_top_list(self, trade_date: str,
                    ts_code: Optional[str] = None) -> pd.DataFrame:
        """
        获取龙虎榜每日明细
        积分消耗：2000分
        单次返回最大10000行数据

        Args:
            trade_date: 交易日期 YYYYMMDD（必需）
            ts_code: 股票代码（可选）

        Returns:
            pd.DataFrame: 龙虎榜明细数据，包含以下列：
                - trade_date: 交易日期
                - ts_code: 股票代码
                - name: 股票名称
                - close: 收盘价
                - pct_change: 涨跌幅
                - turnover_rate: 换手率
                - amount: 总成交额
                - l_sell: 龙虎榜卖出额
                - l_buy: 龙虎榜买入额
                - l_amount: 龙虎榜成交额
                - net_amount: 龙虎榜净买入额
                - net_rate: 龙虎榜净买额占比
                - amount_rate: 龙虎榜成交额占比
                - float_values: 当日流通市值
                - reason: 上榜理由
        """
        try:
            logger.info(f"获取龙虎榜每日明细: trade_date={trade_date}, ts_code={ts_code}")

            # 构建查询参数（只包含非空参数）
            params = {}
            if trade_date:
                params['trade_date'] = trade_date
            if ts_code:
                params['ts_code'] = ts_code

            df = self.api_client.query('top_list', **params)
            logger.info(f"获取到 {len(df)} 条龙虎榜记录")
            return df
        except Exception as e:
            logger.error(f"获取龙虎榜每日明细失败: {e}")
            raise TushareDataError(f"获取龙虎榜每日明细失败: {str(e)}")

    def get_top_inst(self, trade_date: str,
                    ts_code: Optional[str] = None) -> pd.DataFrame:
        """
        获取龙虎榜机构明细
        积分消耗：5000分
        单次返回最大10000行数据

        Args:
            trade_date: 交易日期 YYYYMMDD（必需）
            ts_code: 股票代码（可选）

        Returns:
            pd.DataFrame: 龙虎榜机构明细数据，包含以下列：
                - trade_date: 交易日期
                - ts_code: 股票代码
                - exalter: 营业部名称
                - side: 买卖类型（0：买入金额最大的前5名，1：卖出金额最大的前5名）
                - buy: 买入额（元）
                - buy_rate: 买入占总成交比例
                - sell: 卖出额（元）
                - sell_rate: 卖出占总成交比例
                - net_buy: 净成交额（元）
                - reason: 上榜理由
        """
        try:
            logger.info(f"获取龙虎榜机构明细: trade_date={trade_date}, ts_code={ts_code}")

            # 构建查询参数（只包含非空参数）
            params = {}
            if trade_date:
                params['trade_date'] = trade_date
            if ts_code:
                params['ts_code'] = ts_code

            df = self.api_client.query('top_inst', **params)
            logger.info(f"获取到 {len(df)} 条龙虎榜机构明细记录")
            return df
        except Exception as e:
            logger.error(f"获取龙虎榜机构明细失败: {e}")
            raise TushareDataError(f"获取龙虎榜机构明细失败: {str(e)}")

    def get_limit_list_d(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        limit_type: Optional[str] = None,
        exchange: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取涨跌停列表
        积分消耗：5000分
        单次返回最大2500行数据

        Args:
            trade_date: 交易日期 YYYYMMDD（可选）
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）
            ts_code: 股票代码（可选）
            limit_type: 涨跌停类型（U涨停D跌停Z炸板）（可选）
            exchange: 交易所（SH上交所SZ深交所BJ北交所）（可选）

        Returns:
            pd.DataFrame: 涨跌停列表数据，包含以下列：
                - trade_date: 交易日期
                - ts_code: 股票代码
                - industry: 所属行业
                - name: 股票名称
                - close: 收盘价
                - pct_chg: 涨跌幅
                - amount: 成交额
                - limit_amount: 板上成交金额
                - float_mv: 流通市值
                - total_mv: 总市值
                - turnover_ratio: 换手率
                - fd_amount: 封单金额
                - first_time: 首次封板时间
                - last_time: 最后封板时间
                - open_times: 炸板次数
                - up_stat: 涨停统计
                - limit_times: 连板数
                - limit: D跌停U涨停Z炸板
        """
        try:
            logger.info(f"获取涨跌停列表: trade_date={trade_date}, start_date={start_date}, end_date={end_date}, limit_type={limit_type}")

            # 构建查询参数（只包含非空参数）
            params = {}
            if trade_date:
                params['trade_date'] = trade_date
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            if ts_code:
                params['ts_code'] = ts_code
            if limit_type:
                params['limit_type'] = limit_type
            if exchange:
                params['exchange'] = exchange

            df = self.api_client.query('limit_list_d', **params)
            logger.info(f"获取到 {len(df)} 条涨跌停列表记录")
            return df
        except Exception as e:
            logger.error(f"获取涨跌停列表失败: {e}")
            raise TushareDataError(f"获取涨跌停列表失败: {str(e)}")

    def get_limit_step(
        self,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        nums: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取连板天梯（每天连板个数晋级的股票）
        积分消耗：8000分以上每分钟500次，每天总量不限制
        单次返回最大2000行数据

        Args:
            trade_date: 交易日期 YYYYMMDD（可选）
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）
            ts_code: 股票代码（可选）
            nums: 连板次数，支持多个输入，例如 nums='2,3'（可选）

        Returns:
            pd.DataFrame: 连板天梯数据，包含以下列：
                - ts_code: 股票代码
                - name: 股票名称
                - trade_date: 交易日期
                - nums: 连板次数
        """
        try:
            logger.info(f"获取连板天梯: trade_date={trade_date}, start_date={start_date}, end_date={end_date}, nums={nums}")

            # 构建查询参数（只包含非空参数）
            params = {}
            if trade_date:
                params['trade_date'] = trade_date
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            if ts_code:
                params['ts_code'] = ts_code
            if nums:
                params['nums'] = nums

            df = self.api_client.query('limit_step', **params)
            logger.info(f"获取到 {len(df)} 条连板天梯记录")
            return df
        except Exception as e:
            logger.error(f"获取连板天梯失败: {e}")
            raise TushareDataError(f"获取连板天梯失败: {str(e)}")

    def get_limit_cpt_list(
        self,
        trade_date: Optional[str] = None,
        ts_code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取最强板块统计（每天涨停股票最多最强的概念板块）
        积分消耗：8000分
        单次返回最大2000行数据

        Args:
            trade_date: 交易日期 YYYYMMDD（可选）
            ts_code: 板块代码（可选）
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）

        Returns:
            pd.DataFrame: 最强板块统计数据，包含以下列：
                - ts_code: 板块代码
                - name: 板块名称
                - trade_date: 交易日期
                - days: 上榜天数
                - up_stat: 连板高度（如：9天7板）
                - cons_nums: 连板家数
                - up_nums: 涨停家数
                - pct_chg: 涨跌幅%
                - rank: 板块热点排名
        """
        try:
            logger.info(f"获取最强板块统计: trade_date={trade_date}, ts_code={ts_code}, start_date={start_date}, end_date={end_date}")

            # 构建查询参数（只包含非空参数）
            params = {}
            if trade_date:
                params['trade_date'] = trade_date
            if ts_code:
                params['ts_code'] = ts_code
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date

            df = self.api_client.query('limit_cpt_list', **params)
            logger.info(f"获取到 {len(df)} 条最强板块统计记录")
            return df
        except Exception as e:
            logger.error(f"获取最强板块统计失败: {e}")
            raise TushareDataError(f"获取最强板块统计失败: {str(e)}")

    def get_stk_shock(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取个股异常波动数据
        积分消耗：6000分
        单次返回最大1000行数据

        Args:
            ts_code: 股票代码（可选）
            trade_date: 交易日期 YYYYMMDD（可选）
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）

        Returns:
            pd.DataFrame: 个股异常波动数据，包含以下列：
                - ts_code: 股票代码
                - trade_date: 公告日期
                - name: 股票名称
                - trade_market: 交易所
                - reason: 异常说明
                - period: 异常期间
        """
        try:
            logger.info(f"获取个股异常波动: ts_code={ts_code}, trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

            # 构建查询参数（只包含非空参数）
            params = {}
            if ts_code:
                params['ts_code'] = ts_code
            if trade_date:
                params['trade_date'] = trade_date
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date

            df = self.api_client.query('stk_shock', **params)
            logger.info(f"获取到 {len(df)} 条个股异常波动记录")
            return df
        except Exception as e:
            logger.error(f"获取个股异常波动失败: {e}")
            raise TushareDataError(f"获取个股异常波动失败: {str(e)}")

    def get_stk_high_shock(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取个股严重异常波动数据
        积分消耗：6000分
        单次返回最大1000行数据

        Args:
            ts_code: 股票代码（可选）
            trade_date: 公告日期 YYYYMMDD（可选）
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）

        Returns:
            pd.DataFrame: 个股严重异常波动数据，包含以下列：
                - ts_code: 股票代码
                - trade_date: 公告日期
                - name: 股票名称
                - trade_market: 交易所
                - reason: 异常说明
                - period: 异常期间
        """
        try:
            logger.info(f"获取个股严重异常波动: ts_code={ts_code}, trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

            # 构建查询参数（只包含非空参数）
            params = {}
            if ts_code:
                params['ts_code'] = ts_code
            if trade_date:
                params['trade_date'] = trade_date
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date

            df = self.api_client.query('stk_high_shock', **params)
            logger.info(f"获取到 {len(df)} 条个股严重异常波动记录")
            return df
        except Exception as e:
            logger.error(f"获取个股严重异常波动失败: {e}")
            raise TushareDataError(f"获取个股严重异常波动失败: {str(e)}")

    def get_stk_alert(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取交易所重点提示证券数据
        积分消耗：6000分
        单次返回最大1000行数据

        Args:
            ts_code: 股票代码（可选）
            trade_date: 交易日期 YYYYMMDD（可选）
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）

        Returns:
            pd.DataFrame: 交易所重点提示证券数据，包含以下列：
                - ts_code: 股票代码
                - name: 股票名称
                - start_date: 交易所重点提示起始日期
                - end_date: 交易所重点提示参考截至日期
                - type: 提示类型
        """
        try:
            logger.info(f"获取交易所重点提示证券: ts_code={ts_code}, trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

            # 构建查询参数（只包含非空参数）
            params = {}
            if ts_code:
                params['ts_code'] = ts_code
            if trade_date:
                params['trade_date'] = trade_date
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date

            df = self.api_client.query('stk_alert', **params)
            logger.info(f"获取到 {len(df)} 条交易所重点提示证券记录")
            return df
        except Exception as e:
            logger.error(f"获取交易所重点提示证券失败: {e}")
            raise TushareDataError(f"获取交易所重点提示证券失败: {str(e)}")

    def get_pledge_stat(
        self,
        ts_code: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取股权质押统计数据
        积分消耗：500分
        单次返回最大1000行数据

        Args:
            ts_code: 股票代码（可选）
            end_date: 截止日期 YYYYMMDD（可选）

        Returns:
            pd.DataFrame: 股权质押统计数据，包含以下列：
                - ts_code: TS代码
                - end_date: 截止日期
                - pledge_count: 质押次数
                - unrest_pledge: 无限售股质押数量(万)
                - rest_pledge: 限售股份质押数量(万)
                - total_share: 总股本
                - pledge_ratio: 质押比例
        """
        try:
            logger.info(f"获取股权质押统计数据: ts_code={ts_code}, end_date={end_date}")

            # 构建查询参数（只包含非空参数）
            params = {}
            if ts_code:
                params['ts_code'] = ts_code
            if end_date:
                params['end_date'] = end_date

            df = self.api_client.query('pledge_stat', **params)
            logger.info(f"获取到 {len(df)} 条股权质押统计记录")
            return df
        except Exception as e:
            logger.error(f"获取股权质押统计数据失败: {e}")
            raise TushareDataError(f"获取股权质押统计数据失败: {str(e)}")

    def get_share_float(
        self,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        float_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取限售股解禁数据
        积分消耗：120分

        Args:
            ts_code: TS股票代码（可选）
            ann_date: 公告日期 YYYYMMDD（可选）
            float_date: 解禁日期 YYYYMMDD（可选）
            start_date: 解禁开始日期 YYYYMMDD（可选）
            end_date: 解禁结束日期 YYYYMMDD（可选）

        Returns:
            pd.DataFrame: 限售股解禁数据，包含以下列：
                - ts_code: TS代码
                - ann_date: 公告日期
                - float_date: 解禁日期
                - float_share: 流通股份(股)
                - float_ratio: 流通股份占总股本比率
                - holder_name: 股东名称
                - share_type: 股份类型
        """
        try:
            logger.info(f"获取限售股解禁数据: ts_code={ts_code}, ann_date={ann_date}, "
                       f"float_date={float_date}, start_date={start_date}, end_date={end_date}")

            # 构建查询参数（只包含非空参数）
            params = {}
            if ts_code:
                params['ts_code'] = ts_code
            if ann_date:
                params['ann_date'] = ann_date
            if float_date:
                params['float_date'] = float_date
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date

            df = self.api_client.query('share_float', **params)
            logger.info(f"获取到 {len(df)} 条限售股解禁记录")
            return df
        except Exception as e:
            logger.error(f"获取限售股解禁数据失败: {e}")
            raise TushareDataError(f"获取限售股解禁数据失败: {str(e)}")

    def get_stk_holdernumber(
        self,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        enddate: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取上市公司股东户数数据
        积分消耗：600分

        Args:
            ts_code: TS股票代码（可选）
            ann_date: 公告日期 YYYYMMDD（可选）
            start_date: 公告开始日期 YYYYMMDD（可选）
            end_date: 公告结束日期 YYYYMMDD（可选）
            enddate: 截止日期 YYYYMMDD（可选）

        Returns:
            pd.DataFrame: 股东户数数据，包含以下列：
                - ts_code: TS代码
                - ann_date: 公告日期
                - end_date: 截止日期
                - holder_num: 股东户数
        """
        try:
            logger.info(f"获取股东户数数据: ts_code={ts_code}, ann_date={ann_date}, "
                       f"start_date={start_date}, end_date={end_date}, enddate={enddate}")

            # 构建查询参数（只包含非空参数）
            params = {}
            if ts_code:
                params['ts_code'] = ts_code
            if ann_date:
                params['ann_date'] = ann_date
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            if enddate:
                params['enddate'] = enddate

            df = self.api_client.query('stk_holdernumber', **params)
            logger.info(f"获取到 {len(df)} 条股东户数记录")
            return df
        except Exception as e:
            logger.error(f"获取股东户数数据失败: {e}")
            raise TushareDataError(f"获取股东户数数据失败: {str(e)}")

    def get_repurchase(
        self,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取上市公司回购股票数据
        积分消耗：600分

        Args:
            ann_date: 公告日期 YYYYMMDD（可选）
            start_date: 公告开始日期 YYYYMMDD（可选）
            end_date: 公告结束日期 YYYYMMDD（可选）

        Returns:
            pd.DataFrame: 股票回购数据，包含以下列：
                - ts_code: TS代码
                - ann_date: 公告日期
                - end_date: 截止日期
                - proc: 进度
                - exp_date: 过期日期
                - vol: 回购数量
                - amount: 回购金额
                - high_limit: 回购最高价
                - low_limit: 回购最低价
        """
        try:
            logger.info(f"获取股票回购数据: ann_date={ann_date}, start_date={start_date}, end_date={end_date}")

            # 构建查询参数（只包含非空参数）
            params = {}
            if ann_date:
                params['ann_date'] = ann_date
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date

            df = self.api_client.query('repurchase', **params)
            logger.info(f"获取到 {len(df)} 条股票回购记录")
            return df
        except Exception as e:
            logger.error(f"获取股票回购数据失败: {e}")
            raise TushareDataError(f"获取股票回购数据失败: {str(e)}")

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

        Args:
            ts_code: 股票代码 (可选)
            ann_date: 公告日期 YYYYMMDD（可选）
            start_date: 公告开始日期 YYYYMMDD（可选）
            end_date: 公告结束日期 YYYYMMDD（可选）
            period: 报告期 YYYYMMDD（可选，如20171231表示年报）
            type_: 预告类型（可选，如预增/预减/扭亏/首亏）

        Returns:
            pd.DataFrame: 业绩预告数据，包含以下列：
                - ts_code: TS股票代码
                - ann_date: 公告日期
                - end_date: 报告期
                - type: 业绩预告类型
                - p_change_min: 预告净利润变动幅度下限（%）
                - p_change_max: 预告净利润变动幅度上限（%）
                - net_profit_min: 预告净利润下限（万元）
                - net_profit_max: 预告净利润上限（万元）
                - last_parent_net: 上年同期归属母公司净利润
                - first_ann_date: 首次公告日
                - summary: 业绩预告摘要
                - change_reason: 业绩变动原因
        """
        try:
            logger.info(f"获取业绩预告数据: ts_code={ts_code}, ann_date={ann_date}, start_date={start_date}, end_date={end_date}, period={period}, type={type_}")

            # 构建查询参数（只包含非空参数）
            params = {}
            if ts_code:
                params['ts_code'] = ts_code
            if ann_date:
                params['ann_date'] = ann_date
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            if period:
                params['period'] = period
            if type_:
                params['type'] = type_

            df = self.api_client.query('forecast_vip', **params)
            logger.info(f"获取到 {len(df)} 条业绩预告记录")
            return df
        except Exception as e:
            logger.error(f"获取业绩预告数据失败: {e}")
            raise TushareDataError(f"获取业绩预告数据失败: {str(e)}")

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
        积分消耗：2000分
        注意：每次请求最多返回100条记录

        Args:
            ts_code: 股票代码 (可选)
            ann_date: 公告日期 YYYYMMDD（可选）
            start_date: 报告期开始日期 YYYYMMDD（可选）
            end_date: 报告期结束日期 YYYYMMDD（可选）
            period: 报告期 YYYYMMDD（可选，如20231231表示年报）

        Returns:
            pd.DataFrame: 财务指标数据，包含150+财务指标字段
        """
        try:
            logger.info(f"获取财务指标数据: ts_code={ts_code}, ann_date={ann_date}, start_date={start_date}, end_date={end_date}, period={period}")

            # 构建查询参数（只包含非空参数）
            params = {}
            if ts_code:
                params['ts_code'] = ts_code
            if ann_date:
                params['ann_date'] = ann_date
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            if period:
                params['period'] = period

            df = self.api_client.query('fina_indicator_vip', **params)
            logger.info(f"获取到 {len(df)} 条财务指标记录")
            return df
        except Exception as e:
            logger.error(f"获取财务指标数据失败: {e}")
            raise TushareDataError(f"获取财务指标数据失败: {str(e)}")

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

        Args:
            ts_code: 股票代码 (可选)
            ann_date: 公告日期 YYYYMMDD（可选）
            start_date: 公告开始日期 YYYYMMDD（可选）
            end_date: 公告结束日期 YYYYMMDD（可选）
            period: 报告期 YYYYMMDD（可选，如20171231表示年报，20170630半年报）

        Returns:
            pd.DataFrame: 业绩快报数据，包含以下列：
                - ts_code: TS股票代码
                - ann_date: 公告日期
                - end_date: 报告期
                - revenue: 营业收入(元)
                - operate_profit: 营业利润(元)
                - total_profit: 利润总额(元)
                - n_income: 净利润(元)
                - total_assets: 总资产(元)
                - total_hldr_eqy_exc_min_int: 股东权益合计(不含少数股东权益)(元)
                - diluted_eps: 每股收益(摊薄)(元)
                - diluted_roe: 净资产收益率(摊薄)(%)
                - yoy_net_profit: 去年同期修正后净利润
                - bps: 每股净资产
                - yoy_sales: 同比增长率:营业收入
                - yoy_op: 同比增长率:营业利润
                - yoy_tp: 同比增长率:利润总额
                - yoy_dedu_np: 同比增长率:归属母公司股东的净利润
                - yoy_eps: 同比增长率:基本每股收益
                - yoy_roe: 同比增减:加权平均净资产收益率
                - growth_assets: 比年初增长率:总资产
                - yoy_equity: 比年初增长率:归属母公司的股东权益
                - growth_bps: 比年初增长率:归属于母公司股东的每股净资产
                - or_last_year: 去年同期营业收入
                - op_last_year: 去年同期营业利润
                - tp_last_year: 去年同期利润总额
                - np_last_year: 去年同期净利润
                - eps_last_year: 去年同期每股收益
                - open_net_assets: 期初净资产
                - open_bps: 期初每股净资产
                - perf_summary: 业绩简要说明
                - is_audit: 是否审计：1是 0否
                - remark: 备注
        """
        try:
            logger.info(f"获取业绩快报数据: ts_code={ts_code}, ann_date={ann_date}, start_date={start_date}, end_date={end_date}, period={period}")

            # 构建查询参数（只包含非空参数）
            params = {}
            if ts_code:
                params['ts_code'] = ts_code
            if ann_date:
                params['ann_date'] = ann_date
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            if period:
                params['period'] = period

            df = self.api_client.query('express_vip', **params)
            logger.info(f"获取到 {len(df)} 条业绩快报记录")
            return df
        except Exception as e:
            logger.error(f"获取业绩快报数据失败: {e}")
            raise TushareDataError(f"获取业绩快报数据失败: {str(e)}")

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

        Args:
            ts_code: TS股票代码（可选）
            ann_date: 公告日期 YYYYMMDD（可选）
            record_date: 股权登记日 YYYYMMDD（可选）
            ex_date: 除权除息日 YYYYMMDD（可选）
            imp_ann_date: 实施公告日 YYYYMMDD（可选）
            注意：以上参数至少有一个不能为空

        Returns:
            pd.DataFrame: 分红送股数据，包含以下列：
                - ts_code: TS代码
                - end_date: 分红年度
                - ann_date: 预案公告日
                - div_proc: 实施进度
                - stk_div: 每股送转
                - stk_bo_rate: 每股送股比例
                - stk_co_rate: 每股转增比例
                - cash_div: 每股分红（税后）
                - cash_div_tax: 每股分红（税前）
                - record_date: 股权登记日
                - ex_date: 除权除息日
                - pay_date: 派息日
                - div_listdate: 红股上市日
                - imp_ann_date: 实施公告日
                - base_date: 基准日
                - base_share: 基准股本（万）
        """
        try:
            logger.info(f"获取分红送股数据: ts_code={ts_code}, ann_date={ann_date}, record_date={record_date}, ex_date={ex_date}, imp_ann_date={imp_ann_date}")

            # 构建查询参数（只包含非空参数）
            params = {}
            if ts_code:
                params['ts_code'] = ts_code
            if ann_date:
                params['ann_date'] = ann_date
            if record_date:
                params['record_date'] = record_date
            if ex_date:
                params['ex_date'] = ex_date
            if imp_ann_date:
                params['imp_ann_date'] = imp_ann_date

            # 至少需要一个参数
            if not params:
                raise ValueError("至少需要提供一个查询参数: ts_code, ann_date, record_date, ex_date, imp_ann_date")

            df = self.api_client.query('dividend', **params)
            logger.info(f"获取到 {len(df)} 条分红送股记录")
            return df
        except Exception as e:
            logger.error(f"获取分红送股数据失败: {e}")
            raise TushareDataError(f"获取分红送股数据失败: {str(e)}")

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

        Args:
            ts_code: TS股票代码（必需）
            ann_date: 公告日期 YYYYMMDD（可选）
            start_date: 公告开始日期 YYYYMMDD（可选）
            end_date: 公告结束日期 YYYYMMDD（可选）
            period: 报告期 YYYYMMDD（可选，每个季度最后一天的日期）

        Returns:
            pd.DataFrame: 财务审计意见数据，包含以下列：
                - ts_code: TS股票代码
                - ann_date: 公告日期
                - end_date: 报告期
                - audit_result: 审计结果
                - audit_fees: 审计总费用（元）
                - audit_agency: 会计事务所
                - audit_sign: 签字会计师
        """
        try:
            logger.info(f"获取财务审计意见数据: ts_code={ts_code}, ann_date={ann_date}, start_date={start_date}, end_date={end_date}, period={period}")

            # 构建查询参数（只包含非空参数）
            params = {'ts_code': ts_code}
            if ann_date:
                params['ann_date'] = ann_date
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            if period:
                params['period'] = period

            df = self.api_client.query('fina_audit', **params)
            logger.info(f"获取到 {len(df)} 条财务审计意见记录")
            return df
        except Exception as e:
            logger.error(f"获取财务审计意见数据失败: {e}")
            raise TushareDataError(f"获取财务审计意见数据失败: {str(e)}")

    def get_stk_holdertrade(
        self,
        ts_code: Optional[str] = None,
        ann_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        trade_type: Optional[str] = None,
        holder_type: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取上市公司股东增减持数据
        积分消耗：2000分

        Args:
            ts_code: TS股票代码（可选）
            ann_date: 公告日期 YYYYMMDD（可选）
            start_date: 公告开始日期 YYYYMMDD（可选）
            end_date: 公告结束日期 YYYYMMDD（可选）
            trade_type: 交易类型 IN=增持 DE=减持（可选）
            holder_type: 股东类型 G=高管 P=个人 C=公司（可选）

        Returns:
            pd.DataFrame: 股东增减持数据，包含以下列：
                - ts_code: TS股票代码
                - ann_date: 公告日期
                - holder_name: 股东名称
                - holder_type: 股东类型 G=高管 P=个人 C=公司
                - in_de: 类型 IN=增持 DE=减持
                - change_vol: 变动数量
                - change_ratio: 占流通比例(%)
                - after_share: 变动后持股
                - after_ratio: 变动后占流通比例(%)
                - avg_price: 平均价格
                - total_share: 持股总数
                - begin_date: 增减持开始日期
                - close_date: 增减持结束日期
        """
        try:
            logger.info(f"获取股东增减持数据: ts_code={ts_code}, ann_date={ann_date}, "
                       f"start_date={start_date}, end_date={end_date}, "
                       f"trade_type={trade_type}, holder_type={holder_type}")

            # 构建查询参数（只包含非空参数）
            params = {}
            if ts_code:
                params['ts_code'] = ts_code
            if ann_date:
                params['ann_date'] = ann_date
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            if trade_type:
                params['trade_type'] = trade_type
            if holder_type:
                params['holder_type'] = holder_type

            df = self.api_client.query('stk_holdertrade', **params)
            logger.info(f"获取到 {len(df)} 条股东增减持记录")
            return df
        except Exception as e:
            logger.error(f"获取股东增减持数据失败: {e}")
            raise TushareDataError(f"获取股东增减持数据失败: {str(e)}")

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

        积分消耗: 2000

        Args:
            ts_code: 股票代码（可选）
            ann_date: 公告日期（YYYYMMDD格式）
            f_ann_date: 实际公告日期（YYYYMMDD格式）
            start_date: 报告期开始日期（YYYYMMDD格式）
            end_date: 报告期结束日期（YYYYMMDD格式）
            period: 报告期（YYYYMMDD或YYYYQQ格式，如20241Q1）
            report_type: 报告类型
                1-合并报表
                2-单季合并
                3-调整单季合并表
                4-调整合并报表
                5-调整前合并报表
                6-母公司报表
                7-母公司单季表
                8-母公司调整单季表
                9-母公司调整表
                10-母公司调整前报表
                11-调整前合并报表
                12-母公司调整前报表
            comp_type: 公司类型（1一般工商业 2银行 3保险 4证券）

        Returns:
            pd.DataFrame: 利润表数据

        Examples:
            >>> provider = TushareProvider(token='your_token')
            >>> # 查询某股票某报告期数据
            >>> df = provider.get_income(ts_code='600000.SH', period='20240331')
            >>> # 查询某报告期所有股票数据
            >>> df = provider.get_income(period='20240331')
            >>> # 查询日期范围内的数据
            >>> df = provider.get_income(start_date='20240101', end_date='20241231')
        """
        try:
            params = {}

            if ts_code:
                params['ts_code'] = ts_code
            if ann_date:
                params['ann_date'] = ann_date
            if f_ann_date:
                params['f_ann_date'] = f_ann_date
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            if period:
                params['period'] = period
            if report_type:
                params['report_type'] = report_type
            if comp_type:
                params['comp_type'] = comp_type

            df = self.api_client.query('income_vip', **params)
            logger.info(f"获取到 {len(df)} 条利润表记录")
            return df
        except Exception as e:
            logger.error(f"获取利润表数据失败: {e}")
            raise TushareDataError(f"获取利润表数据失败: {str(e)}")

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

        积分消耗: 2000

        Args:
            ts_code: 股票代码（可选）
            ann_date: 公告日期（YYYYMMDD格式）
            f_ann_date: 实际公告日期（YYYYMMDD格式）
            start_date: 报告期开始日期（YYYYMMDD格式）
            end_date: 报告期结束日期（YYYYMMDD格式）
            period: 报告期（YYYYMMDD格式，如20231231表示年报）
            report_type: 报告类型
                1-合并报表
                2-单季合并
                3-调整单季合并表
                4-调整合并报表
                5-调整前合并报表
                6-母公司报表
                7-母公司单季表
                8-母公司调整单季表
                9-母公司调整表
                10-母公司调整前报表
                11-调整前合并报表
                12-母公司调整前报表
            comp_type: 公司类型（1一般工商业 2银行 3保险 4证券）

        Returns:
            pd.DataFrame: 资产负债表数据

        Examples:
            >>> provider = TushareProvider(token='your_token')
            >>> # 查询某股票某报告期数据
            >>> df = provider.get_balancesheet(ts_code='600000.SH', period='20231231')
            >>> # 查询某报告期所有股票数据
            >>> df = provider.get_balancesheet(period='20231231')
            >>> # 查询日期范围内的数据
            >>> df = provider.get_balancesheet(start_date='20230101', end_date='20231231')
        """
        try:
            params = {}

            if ts_code:
                params['ts_code'] = ts_code
            if ann_date:
                params['ann_date'] = ann_date
            if f_ann_date:
                params['f_ann_date'] = f_ann_date
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            if period:
                params['period'] = period
            if report_type:
                params['report_type'] = report_type
            if comp_type:
                params['comp_type'] = comp_type

            df = self.api_client.query('balancesheet_vip', **params)
            logger.info(f"获取到 {len(df)} 条资产负债表记录")
            return df
        except Exception as e:
            logger.error(f"获取资产负债表数据失败: {e}")
            raise TushareDataError(f"获取资产负债表数据失败: {str(e)}")

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

        积分消耗: 2000

        Args:
            ts_code: 股票代码（可选）
            ann_date: 公告日期（YYYYMMDD格式）
            f_ann_date: 实际公告日期（YYYYMMDD格式）
            start_date: 报告期开始日期（YYYYMMDD格式）
            end_date: 报告期结束日期（YYYYMMDD格式）
            period: 报告期（YYYYMMDD格式，如20231231表示年报）
            report_type: 报告类型
                1-合并报表
                2-单季合并
                3-调整单季合并表
                4-调整合并报表
                5-调整前合并报表
                6-母公司报表
                7-母公司单季表
                8-母公司调整单季表
                9-母公司调整表
                10-母公司调整前报表
                11-调整前合并报表
                12-母公司调整前报表
            comp_type: 公司类型（1一般工商业 2银行 3保险 4证券）

        Returns:
            pd.DataFrame: 现金流量表数据

        Examples:
            >>> provider = TushareProvider(token='your_token')
            >>> # 查询某股票某报告期数据
            >>> df = provider.get_cashflow(ts_code='600000.SH', period='20231231')
            >>> # 查询某报告期所有股票数据
            >>> df = provider.get_cashflow(period='20231231')
            >>> # 查询日期范围内的数据
            >>> df = provider.get_cashflow(start_date='20230101', end_date='20231231')
        """
        try:
            params = {}

            if ts_code:
                params['ts_code'] = ts_code
            if ann_date:
                params['ann_date'] = ann_date
            if f_ann_date:
                params['f_ann_date'] = f_ann_date
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            if period:
                params['period'] = period
            if report_type:
                params['report_type'] = report_type
            if comp_type:
                params['comp_type'] = comp_type

            df = self.api_client.query('cashflow_vip', **params)
            logger.info(f"获取到 {len(df)} 条现金流量表记录")
            return df
        except Exception as e:
            logger.error(f"获取现金流量表数据失败: {e}")
            raise TushareDataError(f"获取现金流量表数据失败: {str(e)}")

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

        Args:
            ts_code: TS股票代码（可选）
            period: 报告期 YYYYMMDD（可选，每个季度最后一天的日期，如20231231表示年报）
            type: 类型（可选）P按产品 D按地区 I按行业
            start_date: 报告期开始日期 YYYYMMDD（可选）
            end_date: 报告期结束日期 YYYYMMDD（可选）

        Returns:
            pd.DataFrame: 主营业务构成数据，包含以下列：
                - ts_code: TS股票代码
                - end_date: 报告期
                - bz_item: 主营业务来源
                - bz_sales: 主营业务收入(元)
                - bz_profit: 主营业务利润(元)
                - bz_cost: 主营业务成本(元)
                - curr_type: 货币代码
                - update_flag: 是否更新
        """
        try:
            logger.info(f"获取主营业务构成数据: ts_code={ts_code}, period={period}, type={type}, "
                       f"start_date={start_date}, end_date={end_date}")

            # 构建查询参数（只包含非空参数）
            params = {}
            if ts_code:
                params['ts_code'] = ts_code
            if period:
                params['period'] = period
            if type:
                params['type'] = type
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date

            df = self.api_client.query('fina_mainbz_vip', **params)
            logger.info(f"获取到 {len(df)} 条主营业务构成记录")
            return df
        except Exception as e:
            logger.error(f"获取主营业务构成数据失败: {e}")
            raise TushareDataError(f"获取主营业务构成数据失败: {str(e)}")

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

        Args:
            ts_code: TS股票代码（可选）
            end_date: 财报周期（每个季度最后一天的日期，如20181231表示2018年年报，20180630表示中报）
            pre_date: 计划披露日期 YYYYMMDD（可选）
            ann_date: 最新披露公告日 YYYYMMDD（可选）
            actual_date: 实际披露日期 YYYYMMDD（可选）

        Returns:
            pd.DataFrame: 财报披露计划数据，包含以下列：
                - ts_code: TS代码
                - ann_date: 最新披露公告日
                - end_date: 报告期
                - pre_date: 预计披露日期
                - actual_date: 实际披露日期
                - modify_date: 披露日期修正记录
        """
        try:
            logger.info(f"获取财报披露计划: ts_code={ts_code}, end_date={end_date}, "
                       f"pre_date={pre_date}, ann_date={ann_date}, actual_date={actual_date}")

            # 构建查询参数（只包含非空参数）
            params = {}
            if ts_code:
                params['ts_code'] = ts_code
            if end_date:
                params['end_date'] = end_date
            if pre_date:
                params['pre_date'] = pre_date
            if ann_date:
                params['ann_date'] = ann_date
            if actual_date:
                params['actual_date'] = actual_date

            df = self.api_client.query('disclosure_date', **params)
            logger.info(f"获取到 {len(df)} 条财报披露计划记录")
            return df
        except Exception as e:
            logger.error(f"获取财报披露计划失败: {e}")
            raise TushareDataError(f"获取财报披露计划失败: {str(e)}")

    def get_cyq_perf(
        self,
        ts_code: str,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取A股每日筹码平均成本和胜率情况
        积分消耗：5000分起

        Args:
            ts_code: 股票代码（必填）
            trade_date: 交易日期 YYYYMMDD（可选）
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）

        Returns:
            pd.DataFrame: 筹码及胜率数据，包含以下列：
                - ts_code: 股票代码
                - trade_date: 交易日期
                - his_low: 历史最低价
                - his_high: 历史最高价
                - cost_5pct: 5分位成本
                - cost_15pct: 15分位成本
                - cost_50pct: 50分位成本（中位数）
                - cost_85pct: 85分位成本
                - cost_95pct: 95分位成本
                - weight_avg: 加权平均成本
                - winner_rate: 胜率(%)
        """
        try:
            logger.info(f"获取筹码及胜率数据: ts_code={ts_code}, trade_date={trade_date}, "
                       f"start_date={start_date}, end_date={end_date}")

            # 构建查询参数（只包含非空参数）
            params = {'ts_code': ts_code}
            if trade_date:
                params['trade_date'] = trade_date
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date

            df = self.api_client.query('cyq_perf', **params)
            logger.info(f"获取到 {len(df)} 条筹码及胜率记录")
            return df
        except Exception as e:
            logger.error(f"获取筹码及胜率数据失败: {e}")
            raise TushareDataError(f"获取筹码及胜率数据失败: {str(e)}")

    def get_cyq_chips(
        self,
        ts_code: str,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取A股每日的筹码分布情况，提供各价位占比
        数据从2018年开始，每天18~19点之间更新当日数据
        积分消耗：5000积分每天20000次，10000积分每天200000次，15000积分每天不限总量
        单次最大2000条，可以按股票代码和日期循环提取

        Args:
            ts_code: 股票代码（必填）
            trade_date: 交易日期 YYYYMMDD（可选）
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）

        Returns:
            pd.DataFrame: 筹码分布数据，包含以下列：
                - ts_code: 股票代码
                - trade_date: 交易日期
                - price: 成本价格
                - percent: 价格占比(%)
        """
        try:
            logger.info(f"获取筹码分布数据: ts_code={ts_code}, trade_date={trade_date}, "
                       f"start_date={start_date}, end_date={end_date}")

            # 构建查询参数（只包含非空参数）
            params = {'ts_code': ts_code}
            if trade_date:
                params['trade_date'] = trade_date
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date

            df = self.api_client.query('cyq_chips', **params)
            logger.info(f"获取到 {len(df)} 条筹码分布记录")
            return df
        except Exception as e:
            logger.error(f"获取筹码分布数据失败: {e}")
            raise TushareDataError(f"获取筹码分布数据失败: {str(e)}")

    def get_ccass_hold(
        self,
        ts_code: Optional[str] = None,
        hk_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取中央结算系统持股汇总数据
        积分消耗：120积分（试用），5000积分（正式）

        Args:
            ts_code: 股票代码（如 605009.SH）
            hk_code: 港交所代码（如 95009）
            trade_date: 交易日期 YYYYMMDD（可选）
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）

        Returns:
            pd.DataFrame: 中央结算系统持股汇总数据，包含以下列：
                - trade_date: 交易日期
                - ts_code: 股票代号
                - name: 股票名称
                - shareholding: 于中央结算系统的持股量(股)
                - hold_nums: 参与者数目（个）
                - hold_ratio: 占于上交所上市及交易的A股总数的百分比（%）
        """
        try:
            logger.info(f"获取中央结算系统持股汇总数据: ts_code={ts_code}, hk_code={hk_code}, "
                       f"trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

            # 构建查询参数（只包含非空参数）
            params = {}
            if ts_code:
                params['ts_code'] = ts_code
            if hk_code:
                params['hk_code'] = hk_code
            if trade_date:
                params['trade_date'] = trade_date
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date

            df = self.api_client.query('ccass_hold', **params)
            logger.info(f"获取到 {len(df)} 条中央结算系统持股汇总记录")
            return df
        except Exception as e:
            logger.error(f"获取中央结算系统持股汇总数据失败: {e}")
            raise TushareDataError(f"获取中央结算系统持股汇总数据失败: {str(e)}")

    def get_ccass_hold_detail(
        self,
        ts_code: Optional[str] = None,
        hk_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        获取中央结算系统机构席位持股明细
        积分消耗：8000积分/次，单次最大返回6000条数据

        Args:
            ts_code: 股票代码（如 605009.SH 或 00960.HK）
            hk_code: 港交所代码（如 95009）
            trade_date: 交易日期 YYYYMMDD（可选）
            start_date: 开始日期 YYYYMMDD（可选）
            end_date: 结束日期 YYYYMMDD（可选）

        Returns:
            pd.DataFrame: 中央结算系统持股明细数据，包含以下列：
                - trade_date: 交易日期
                - ts_code: 股票代号
                - name: 股票名称
                - col_participant_id: 参与者编号
                - col_participant_name: 机构名称
                - col_shareholding: 持股量(股)
                - col_shareholding_percent: 占已发行股份/权证/单位百分比(%)
        """
        try:
            logger.info(f"获取中央结算系统持股明细数据: ts_code={ts_code}, hk_code={hk_code}, "
                       f"trade_date={trade_date}, start_date={start_date}, end_date={end_date}")

            # 构建查询参数（只包含非空参数）
            params = {}
            if ts_code:
                params['ts_code'] = ts_code
            if hk_code:
                params['hk_code'] = hk_code
            if trade_date:
                params['trade_date'] = trade_date
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date

            df = self.api_client.query('ccass_hold_detail', **params)
            logger.info(f"获取到 {len(df)} 条中央结算系统持股明细记录")
            return df
        except Exception as e:
            logger.error(f"获取中央结算系统持股明细数据失败: {e}")
            raise TushareDataError(f"获取中央结算系统持股明细数据失败: {str(e)}")

    def __repr__(self) -> str:
        token_preview = f"{self.token[:8]}***" if self.token else "未配置"
        return f"<TushareProvider token={token_preview}>"
