"""
AkShare 数据提供者主类

整合 API 客户端和数据转换器，实现 BaseDataProvider 接口
"""

from typing import Optional, List, Dict, Callable, Any
from datetime import datetime, timedelta
import time
import pandas as pd
from src.utils.logger import get_logger
from src.utils.response import Response
from ..base_provider import BaseDataProvider
from .api_client import AkShareAPIClient
from .data_converter import AkShareDataConverter
from .config import AkShareConfig
from .exceptions import AkShareDataError

logger = get_logger(__name__)


class AkShareProvider(BaseDataProvider):
    """
    AkShare 数据提供者

    特点:
    - 免费开源，无需 Token
    - 数据来源稳定（东方财富、新浪财经等）
    - 存在 IP 限流风险

    注意事项:
    - 避免过于频繁的请求
    - 建议请求间隔 >= 0.3秒
    - 实时行情获取较慢（需要爬取多个页面）
    """

    def __init__(self, **kwargs: Any) -> None:
        """
        初始化 AkShare 提供者

        Args:
            **kwargs:
                - timeout: 请求超时时间（秒，默认 30）
                - retry_count: 失败重试次数（默认 3）
                - retry_delay: 重试延迟（秒，默认 1）
                - request_delay: 请求间隔（秒，默认 0.3）
        """
        # 设置属性
        self.timeout: int = kwargs.get('timeout', AkShareConfig.DEFAULT_TIMEOUT)
        self.retry_count: int = kwargs.get('retry_count', AkShareConfig.DEFAULT_RETRY_COUNT)
        self.retry_delay: int = kwargs.get('retry_delay', AkShareConfig.DEFAULT_RETRY_DELAY)
        self.request_delay: float = kwargs.get('request_delay', AkShareConfig.DEFAULT_REQUEST_DELAY)

        # 初始化 API 客户端
        self.api_client: Optional[AkShareAPIClient] = None

        # 初始化数据转换器
        self.converter = AkShareDataConverter()

        # 调用父类初始化（会调用 _validate_config）
        super().__init__(**kwargs)

        logger.info("AkShareProvider 初始化成功")

    def _validate_config(self) -> None:
        """验证配置并初始化 API 客户端"""
        # AkShare 无需特殊配置，直接初始化客户端
        self.api_client = AkShareAPIClient(
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
            logger.info("正在从 AkShare 获取股票列表...")

            # 获取股票基本信息
            df = self.api_client.execute(self.api_client.stock_info_a_code_name)

            if df is None or df.empty:
                return Response.error(
                    error="获取股票列表失败，返回数据为空",
                    error_code="AKSHARE_EMPTY_DATA",
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

        except AkShareDataError as e:
            logger.error(f"获取股票列表失败: {e}")
            return Response.error(
                error=str(e),
                error_code="AKSHARE_DATA_ERROR",
                provider=self.provider_name
            )
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return Response.error(
                error=f"获取股票列表失败: {str(e)}",
                error_code="AKSHARE_UNEXPECTED_ERROR",
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
            logger.info(f"正在从 AkShare 获取最近 {days} 天的新股...")

            # 获取次新股数据（包含上市日期）
            df = self.api_client.execute(self.api_client.stock_new_a_spot_em)

            if df is None or df.empty:
                return Response.error(
                    error="获取新股列表失败，返回数据为空",
                    error_code="AKSHARE_EMPTY_DATA",
                    provider=self.provider_name,
                    days=days
                )

            # 筛选最近 N 天上市的股票
            cutoff_date = datetime.now() - timedelta(days=days)
            df['上市日期'] = pd.to_datetime(df['上市日期'], errors='coerce')
            df = df[df['上市日期'] >= cutoff_date]

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

        except AkShareDataError as e:
            logger.error(f"获取新股列表失败: {e}")
            return Response.error(
                error=str(e),
                error_code="AKSHARE_DATA_ERROR",
                provider=self.provider_name,
                days=days
            )
        except Exception as e:
            logger.error(f"获取新股列表失败: {e}")
            return Response.error(
                error=f"获取新股列表失败: {str(e)}",
                error_code="AKSHARE_UNEXPECTED_ERROR",
                provider=self.provider_name,
                days=days
            )

    def get_delisted_stocks(self) -> Response:
        """
        获取退市股票列表

        Returns:
            Response: 响应对象
                - data: pd.DataFrame 标准化的退市股票列表
                - metadata: 元数据(n_stocks, provider)
        """
        try:
            start_time = time.time()
            logger.info("正在从 AkShare 获取退市股票列表...")

            # 获取上交所退市股票
            df_sh = self.api_client.execute(self.api_client.stock_info_sh_delist)
            if df_sh is not None and not df_sh.empty:
                df_sh = self.converter.convert_delisted_stocks(df_sh, exchange='SH')
                df_sh['market'] = '上海主板'

            # 获取深交所退市股票
            try:
                df_sz = self.api_client.execute(self.api_client.stock_info_sz_delist)
                if df_sz is not None and not df_sz.empty:
                    df_sz = self.converter.convert_delisted_stocks(df_sz, exchange='SZ')
                    df_sz['market'] = '深圳主板'
            except Exception:
                logger.warning("深交所退市数据获取失败，仅使用上交所数据")
                df_sz = pd.DataFrame()

            # 合并上深两市数据
            dfs = [df for df in [df_sh, df_sz] if df is not None and not df.empty]
            if not dfs:
                return Response.error(
                    error="获取退市股票列表失败，返回数据为空",
                    error_code="AKSHARE_EMPTY_DATA",
                    provider=self.provider_name
                )

            df = pd.concat(dfs, ignore_index=True)
            elapsed = time.time() - start_time

            logger.info(f"成功获取 {len(df)} 只退市股票")
            return Response.success(
                data=df,
                message=f"成功获取 {len(df)} 只退市股票",
                n_stocks=len(df),
                provider=self.provider_name,
                elapsed_time=f"{elapsed:.2f}s"
            )

        except AkShareDataError as e:
            logger.error(f"获取退市股票列表失败: {e}")
            return Response.error(
                error=str(e),
                error_code="AKSHARE_DATA_ERROR",
                provider=self.provider_name
            )
        except Exception as e:
            logger.error(f"获取退市股票列表失败: {e}")
            return Response.error(
                error=f"获取退市股票列表失败: {str(e)}",
                error_code="AKSHARE_UNEXPECTED_ERROR",
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
            code: 股票代码
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
                (datetime.now() - timedelta(days=AkShareConfig.DEFAULT_HISTORY_DAYS)).strftime('%Y%m%d')
            end = self.normalize_date(end_date) if end_date else \
                datetime.now().strftime('%Y%m%d')

            logger.debug(f"获取 {code} 日线数据: {start} - {end}, 复权: {adjust}")

            # 获取历史数据
            df = self.api_client.execute(
                self.api_client.stock_zh_a_hist,
                symbol=code,
                period='daily',
                start_date=start,
                end_date=end,
                adjust=adjust
            )

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

        except AkShareDataError as e:
            logger.error(f"获取 {code} 日线数据失败: {e}")
            return Response.error(
                error=str(e),
                error_code="AKSHARE_DATA_ERROR",
                code=code,
                provider=self.provider_name
            )
        except Exception as e:
            logger.error(f"获取 {code} 日线数据失败: {e}")
            return Response.error(
                error=f"获取日线数据失败: {str(e)}",
                error_code="AKSHARE_UNEXPECTED_ERROR",
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
            logger.info(f"[{i}/{len(codes)}] 获取 {code} 日线数据")
            response = self.get_daily_data(code, start_date, end_date, adjust)
            if response.is_success() and response.data is not None and not response.data.empty:
                result[code] = response.data
            else:
                failed_codes.append(code)

        elapsed = time.time() - start_time
        n_success = len(result)
        n_failed = len(failed_codes)

        logger.info(f"批量获取完成，成功: {n_success}/{len(codes)}")

        if n_success == 0:
            return Response.error(
                error="批量获取失败，所有股票数据获取失败",
                error_code="AKSHARE_BATCH_ALL_FAILED",
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
                failed_codes=[],
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

            # 标准化日期时间格式
            start = self.normalize_datetime(start_date) if start_date else \
                (datetime.now() - timedelta(days=AkShareConfig.DEFAULT_MINUTE_DAYS)).strftime('%Y-%m-%d 09:30:00')
            end = self.normalize_datetime(end_date) if end_date else \
                datetime.now().strftime('%Y-%m-%d 15:00:00')

            logger.debug(f"获取 {code} {period}分钟数据: {start} - {end}")

            # 获取分时数据
            df = self.api_client.execute(
                self.api_client.stock_zh_a_hist_min_em,
                symbol=code,
                period=period,
                start_date=start,
                end_date=end,
                adjust=adjust
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
                message=f"成功获取 {code} 分时数据",
                code=code,
                period=period,
                n_records=len(df),
                provider=self.provider_name,
                elapsed_time=f"{elapsed:.2f}s"
            )

        except AkShareDataError as e:
            logger.error(f"获取 {code} 分时数据失败: {e}")
            return Response.error(
                error=str(e),
                error_code="AKSHARE_DATA_ERROR",
                code=code,
                period=period,
                provider=self.provider_name
            )
        except Exception as e:
            logger.error(f"获取 {code} 分时数据失败: {e}")
            return Response.error(
                error=f"获取分时数据失败: {str(e)}",
                error_code="AKSHARE_UNEXPECTED_ERROR",
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
        获取实时行情数据

        注意: AkShare 实时行情获取较慢（需要爬取多个页面）
        建议用于定时批量更新，不适合高频调用

        Args:
            codes: 股票代码列表 (None 表示获取全部)
            save_callback: 可选的回调函数，用于每获取一条数据后立即保存

        Returns:
            Response: 响应对象
                - data: pd.DataFrame 标准化的实时行情数据
                - metadata: 元数据(n_stocks, provider)
        """
        try:
            start_time = time.time()

            # 如果指定了股票代码且数量<=100，使用单个股票行情接口（更快）
            if codes and len(codes) <= 100:
                df_result = self._get_realtime_quotes_batch(codes, save_callback=save_callback)
                elapsed = time.time() - start_time
                return Response.success(
                    data=df_result,
                    message=f"成功获取 {len(df_result)} 只股票的实时行情",
                    n_stocks=len(df_result),
                    provider=self.provider_name,
                    elapsed_time=f"{elapsed:.2f}s"
                )

            # 获取全部实时行情
            logger.info("正在获取实时行情... (此操作可能需要 3-5 分钟，共58个批次)")
            logger.warning("AkShare实时行情接口需要分批次爬取东方财富网数据，请耐心等待...")

            # 注意：此接口会分58个批次请求，每批次约2-3秒，总耗时3-5分钟
            df = self.api_client.execute(self.api_client.stock_zh_a_spot_em)

            if df is None or df.empty:
                return Response.error(
                    error="获取实时行情失败，返回数据为空。可能原因：\n"
                          "1. 网络连接超时（数据获取需3-5分钟）\n"
                          "2. 东方财富网接口限流\n"
                          "3. 非交易时段数据源无响应\n"
                          "建议：稍后重试或使用Tushare数据源",
                    error_code="AKSHARE_EMPTY_DATA",
                    provider=self.provider_name
                )

            # 转换为标准格式
            df = self.converter.convert_realtime_quotes(df)

            # 筛选指定股票
            if codes:
                df = df[df['code'].isin(codes)]

            elapsed = time.time() - start_time
            logger.info(f"成功获取 {len(df)} 只股票的实时行情")
            return Response.success(
                data=df,
                message=f"成功获取 {len(df)} 只股票的实时行情",
                n_stocks=len(df),
                provider=self.provider_name,
                elapsed_time=f"{elapsed:.2f}s"
            )

        except AkShareDataError as e:
            logger.error(f"获取实时行情失败: {e}")
            return Response.error(
                error=str(e),
                error_code="AKSHARE_DATA_ERROR",
                provider=self.provider_name
            )
        except Exception as e:
            logger.error(f"获取实时行情失败: {e}")
            return Response.error(
                error=f"获取实时行情失败: {str(e)}",
                error_code="AKSHARE_UNEXPECTED_ERROR",
                provider=self.provider_name
            )

    def _get_realtime_quotes_batch(
        self,
        codes: List[str],
        save_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> pd.DataFrame:
        """
        批量获取指定股票的实时行情（使用单个股票接口）

        Args:
            codes: 股票代码列表
            save_callback: 可选的回调函数，用于每获取一条数据后立即保存

        Returns:
            pd.DataFrame: 标准化的实时行情数据
        """
        try:
            logger.info(f"正在批量获取 {len(codes)} 只股票的实时行情...")

            all_data = []
            success_count = 0
            failed_codes = []

            for i, code in enumerate(codes, 1):
                try:
                    # 使用 stock_bid_ask_em 接口获取实时盘口数据
                    data = self.api_client.execute(
                        self.api_client.stock_bid_ask_em,
                        symbol=code
                    )

                    if data is not None and not data.empty:
                        # 提取关键字段
                        info = {}
                        for _, row in data.iterrows():
                            key = row.get('item', row.get('属性', ''))
                            value = row.get('value', row.get('值', ''))
                            info[key] = value

                        # 获取股票名称
                        try:
                            basic_info = self.api_client.execute(
                                self.api_client.stock_individual_info_em,
                                symbol=code
                            )
                            basic_dict = {}
                            if basic_info is not None and not basic_info.empty:
                                for _, row in basic_info.iterrows():
                                    key = row.get('item', row.get('属性', ''))
                                    value = row.get('value', row.get('值', ''))
                                    basic_dict[key] = value
                            stock_name = basic_dict.get('股票简称', '')
                        except Exception:
                            stock_name = ''

                        # 构造标准格式
                        quote = {
                            'code': code,
                            'name': stock_name,
                            'latest_price': self.converter.safe_float(info.get('最���', 0)),
                            'open': self.converter.safe_float(info.get('今开', 0)),
                            'high': self.converter.safe_float(info.get('最高', 0)),
                            'low': self.converter.safe_float(info.get('最低', 0)),
                            'pre_close': self.converter.safe_float(info.get('昨收', 0)),
                            'volume': self.converter.safe_int(info.get('总手', 0)),
                            'amount': self.converter.safe_float(info.get('金额', 0)),
                            'pct_change': self.converter.safe_float(info.get('涨幅', 0)),
                            'change_amount': self.converter.safe_float(info.get('涨跌', 0)),
                            'turnover': self.converter.safe_float(info.get('换手', 0)),
                            'amplitude': self.converter.safe_float(info.get('振幅', 0)),
                            'trade_time': datetime.now()
                        }

                        # 如果没有振幅数据，根据高低价计算
                        if quote['amplitude'] == 0 and quote['pre_close'] > 0:
                            quote['amplitude'] = (quote['high'] - quote['low']) / quote['pre_close'] * 100

                        all_data.append(quote)
                        success_count += 1

                        # 如果提供了回调函数，立即保存这条数据
                        if save_callback:
                            try:
                                save_callback(quote)
                            except Exception as callback_error:
                                logger.warning(f"保存 {code} 数据时回调失败: {callback_error}")

                        if i % 10 == 0:
                            logger.info(f"进度: {i}/{len(codes)} ({success_count} 成功)")

                    time.sleep(0.3)  # API限流

                except Exception as e:
                    logger.warning(f"获取 {code} 实时行情失败: {e}")
                    failed_codes.append(code)
                    continue

            if not all_data:
                raise AkShareDataError("批量获取实时行情失败，所有股票均失败")

            df = pd.DataFrame(all_data)

            logger.info(f"批量获取完成: {success_count}/{len(codes)} 成功")
            if failed_codes:
                logger.warning(f"失败股票 ({len(failed_codes)}): {', '.join(failed_codes[:10])}...")

            return df

        except Exception as e:
            logger.error(f"批量获取实时行情失败: {e}")
            raise

    def __repr__(self) -> str:
        return "<AkShareProvider (免费，无需Token)>"


__all__ = ['AkShareProvider']
