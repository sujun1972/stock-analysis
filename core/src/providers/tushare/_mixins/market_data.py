"""
行情数据相关方法 Mixin

包含：get_daily_data, get_daily_batch, get_minute_data, get_realtime_quotes,
      _get_quotes_from_minute_data（内部辅助）
"""

import time
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable

from src.utils.response import Response
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MarketDataMixin:
    """行情数据获取"""

    def get_daily_data(
        self,
        code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: str = 'none',
        trade_date: Optional[str] = None
    ) -> Response:
        """
        获取股票日线数据（未复权）

        注意：Tushare daily 接口返回未复权数据，不支持 adj 复权参数。
        adjust 参数保留仅为接口兼容，不会影响实际结果。

        Args:
            code: 股票代码（含或不含后缀）。留空时 trade_date 必填，返回全市场当日数据
            start_date: 开始日期 (YYYYMMDD 或 YYYY-MM-DD)
            end_date: 结束日期
            adjust: 已废弃，保留仅为兼容，daily 接口不支持复权
            trade_date: 交易日期（YYYYMMDD），与 code=None 配合使用获取全市场单日数据

        Returns:
            Response: 响应对象
                - data: pd.DataFrame 标准化的日线数据
                - metadata: 元数据(code, n_records, date_range)
        """
        from ..config import TushareConfig
        from ..exceptions import TusharePermissionError, TushareRateLimitError, TushareDataError

        try:
            start_time = time.time()
            params = {}

            if trade_date and not code:
                td = self.normalize_date(trade_date)
                params['trade_date'] = td
                desc = f"全市场({td})"
                logger.debug(f"获取全市场日线数据: trade_date={td}")
            else:
                if not code:
                    raise ValueError("code 和 trade_date 不能同时为空")
                start = self.normalize_date(start_date) if start_date else \
                    (datetime.now() - timedelta(days=TushareConfig.DEFAULT_HISTORY_DAYS)).strftime('%Y%m%d')
                end = self.normalize_date(end_date) if end_date else \
                    datetime.now().strftime('%Y%m%d')

                ts_code = self.converter.to_ts_code(code)
                params['ts_code'] = ts_code
                params['start_date'] = start
                params['end_date'] = end
                desc = code
                logger.debug(f"获取 {ts_code} 日线数据: {start} - {end}")

            df = self.api_client.execute(self.api_client.daily, **params)

            date_range = params.get('trade_date') or \
                f"{params.get('start_date', '')}~{params.get('end_date', '')}"

            if df is None or df.empty:
                logger.warning(f"{desc}: 无数据")
                return Response.warning(
                    message=f"{desc}: 无数据",
                    data=pd.DataFrame(),
                    code=code or '',
                    date_range=date_range,
                    provider=self.provider_name
                )

            df = self.converter.convert_daily_data(df)
            elapsed = time.time() - start_time

            logger.debug(f"成功获取 {desc} 日线数据 {len(df)} 条")
            return Response.success(
                data=df,
                message=f"成功获取 {desc} 日线数据",
                code=code or '',
                n_records=len(df),
                date_range=date_range,
                provider=self.provider_name,
                elapsed_time=f"{elapsed:.2f}s"
            )

        except TusharePermissionError as e:
            logger.error(f"获取日线数据失败: {e}")
            return Response.error(error=str(e), error_code="TUSHARE_PERMISSION_ERROR", code=code or '', provider=self.provider_name)
        except TushareRateLimitError as e:
            logger.error(f"获取日线数据失败: {e}")
            return Response.error(error=str(e), error_code="TUSHARE_RATE_LIMIT_ERROR", code=code or '', provider=self.provider_name, retry_after=e.retry_after)
        except TushareDataError as e:
            logger.error(f"获取日线数据失败: {e}")
            return Response.error(error=str(e), error_code="TUSHARE_DATA_ERROR", code=code or '', provider=self.provider_name)
        except Exception as e:
            logger.error(f"获取日线数据失败: {e}")
            return Response.error(error=f"获取日线数据失败: {str(e)}", error_code="TUSHARE_UNEXPECTED_ERROR", code=code or '', provider=self.provider_name)

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
        from ..config import TushareConfig
        from ..exceptions import TusharePermissionError, TushareRateLimitError, TushareDataError

        try:
            start_time = time.time()

            start = self.normalize_date(start_date) if start_date else \
                (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')
            end = self.normalize_date(end_date) if end_date else \
                datetime.now().strftime('%Y%m%d')

            ts_code = self.converter.to_ts_code(code)
            logger.debug(f"获取 {ts_code} {period}分钟数据: {start} - {end}")

            freq = TushareConfig.MINUTE_FREQ_MAP.get(period, '5min')

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
            return Response.error(error=str(e), error_code="TUSHARE_PERMISSION_ERROR", code=code, period=period, provider=self.provider_name)
        except TushareRateLimitError as e:
            logger.error(f"获取 {code} 分时数据失败: {e}")
            return Response.error(error=str(e), error_code="TUSHARE_RATE_LIMIT_ERROR", code=code, period=period, provider=self.provider_name, retry_after=e.retry_after)
        except TushareDataError as e:
            logger.error(f"获取 {code} 分时数据失败: {e}")
            return Response.error(error=str(e), error_code="TUSHARE_DATA_ERROR", code=code, period=period, provider=self.provider_name)
        except Exception as e:
            logger.error(f"获取 {code} 分时数据失败: {e}")
            return Response.error(error=f"获取分时数据失败: {str(e)}", error_code="TUSHARE_UNEXPECTED_ERROR", code=code, period=period, provider=self.provider_name)

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
        from ..exceptions import TusharePermissionError, TushareRateLimitError, TushareDataError

        try:
            start_time = time.time()

            use_minute_data = False  # stk_mins 每天仅限2次，默认不用

            if use_minute_data and codes and len(codes) <= 5:
                logger.info("正在获取最新行情（使用分钟数据）...")
                minute_df = self._get_quotes_from_minute_data(codes)
                if minute_df is not None and not minute_df.empty:
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

            logger.info("正在获取最新行情（使用daily接口）...")

            ts_codes = None
            if codes:
                ts_codes = ','.join([self.converter.to_ts_code(code) for code in codes])

            today = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')

            df = self.api_client.execute(
                self.api_client.daily,
                ts_code=ts_codes,
                start_date=start_date,
                end_date=today
            )

            if df is not None and not df.empty:
                df = df.sort_values(['ts_code', 'trade_date'], ascending=[True, False])
                df = df.groupby('ts_code').first().reset_index()

            if df is None or df.empty:
                return Response.error(
                    error="获取最新行情失败，返回数据为空",
                    error_code="TUSHARE_EMPTY_DATA",
                    provider=self.provider_name
                )

            ts_code_series = df['ts_code'].copy() if 'ts_code' in df.columns else None
            df = self.converter.convert_daily_data(df)

            if ts_code_series is not None:
                df['code'] = ts_code_series.apply(self.converter.from_ts_code)

            df['latest_price'] = df['close']
            df['trade_time'] = pd.to_datetime(df['trade_date'])

            if 'name' not in df.columns:
                df['name'] = ''

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
            return Response.error(error=str(e), error_code="TUSHARE_PERMISSION_ERROR", provider=self.provider_name)
        except TushareRateLimitError as e:
            logger.error(f"获取最新行情失败: {e}")
            return Response.error(error=str(e), error_code="TUSHARE_RATE_LIMIT_ERROR", provider=self.provider_name, retry_after=e.retry_after)
        except TushareDataError as e:
            logger.error(f"获取最新行情失败: {e}")
            return Response.error(error=str(e), error_code="TUSHARE_DATA_ERROR", provider=self.provider_name)
        except Exception as e:
            logger.error(f"获取最新行情失败: {e}")
            return Response.error(error=f"获取最新行情失败: {str(e)}", error_code="TUSHARE_UNEXPECTED_ERROR", provider=self.provider_name)

    def _get_quotes_from_minute_data(self, codes: List[str]) -> Optional[pd.DataFrame]:
        """
        从分钟数据获取最新行情（内部方法）

        Args:
            codes: 股票代码列表

        Returns:
            pd.DataFrame: 包含最新行情的DataFrame，失败返回None
        """
        try:
            now = datetime.now()
            end_time = now.strftime('%Y-%m-%d %H:%M:%S')
            start_time_str = (now - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')

            all_data = []

            for code in codes:
                ts_code = self.converter.to_ts_code(code)

                try:
                    df_min = self.api_client.execute(
                        self.api_client.stk_mins,
                        ts_code=ts_code,
                        freq='1min',
                        start_date=start_time_str,
                        end_date=end_time
                    )

                    if df_min is not None and not df_min.empty:
                        latest = df_min.iloc[-1]

                        quote_data = {
                            'code': code,
                            'name': '',
                            'latest_price': float(latest['close']),
                            'open': float(latest['open']),
                            'high': float(latest['high']),
                            'low': float(latest['low']),
                            'close': float(latest['close']),
                            'trade_time': pd.to_datetime(latest['trade_time']),
                            'trade_date': pd.to_datetime(latest['trade_time']).date(),
                            'volume': float(latest.get('vol', 0)) * 100,
                            'amount': float(latest.get('amount', 0)) * 1000,
                            'pct_change': 0,
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
