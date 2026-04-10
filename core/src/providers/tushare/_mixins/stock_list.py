"""
股票列表相关方法 Mixin

包含：get_stock_list, get_new_stocks, get_delisted_stocks
"""

import time
import pandas as pd
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from src.utils.response import Response
from src.utils.logger import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class StockListMixin:
    """股票列表相关数据获取"""

    def get_stock_list(self) -> Response:
        """
        获取全部 A 股股票列表

        Returns:
            Response: 响应对象
                - data: pd.DataFrame 标准化的股票列表
                - metadata: 元数据(n_stocks, provider)
        """
        from ..config import TushareFields
        from ..exceptions import TusharePermissionError, TushareRateLimitError, TushareDataError

        try:
            start_time = time.time()
            logger.info("正在从 Tushare 获取股票列表...")

            df = self.api_client.execute(
                self.api_client.stock_basic,
                exchange='',
                list_status='L',
                fields=TushareFields.STOCK_LIST_FIELDS
            )

            if df is None or df.empty:
                return Response.error(
                    error="获取股票列表失败，返回数据为空",
                    error_code="TUSHARE_EMPTY_DATA",
                    provider=self.provider_name
                )

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
            return Response.error(error=str(e), error_code="TUSHARE_PERMISSION_ERROR", provider=self.provider_name)
        except TushareRateLimitError as e:
            logger.error(f"获取股票列表失败: {e}")
            return Response.error(error=str(e), error_code="TUSHARE_RATE_LIMIT_ERROR", provider=self.provider_name, retry_after=e.retry_after)
        except TushareDataError as e:
            logger.error(f"获取股票列表失败: {e}")
            return Response.error(error=str(e), error_code="TUSHARE_DATA_ERROR", provider=self.provider_name)
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            return Response.error(error=f"获取股票列表失败: {str(e)}", error_code="TUSHARE_UNEXPECTED_ERROR", provider=self.provider_name)

    def get_new_stocks(self, days: int = 30, start_date: str = None, end_date: str = None) -> Response:
        """
        获取新股列表（来自 new_share 接口，保留完整字段）

        Args:
            days: 最近天数（当 start_date 未指定时使用）
            start_date: 上网发行开始日期，格式 YYYYMMDD（优先使用）
            end_date: 上网发行结束日期，格式 YYYYMMDD（默认今天）

        Returns:
            Response: 响应对象
                - data: pd.DataFrame，字段：ts_code, sub_code, name, ipo_date,
                        issue_date, amount, market_amount, price, pe,
                        limit_amount, funds, ballot
        """
        from ..exceptions import TusharePermissionError, TushareRateLimitError, TushareDataError

        try:
            start_time = time.time()

            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
            if not start_date:
                start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

            logger.info(f"正在从 Tushare 获取新股（{start_date} ~ {end_date}）...")

            df = self.api_client.execute(
                self.api_client.new_share,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                logger.warning(f"new_share 接口未返回数据（{start_date} ~ {end_date}）")
                return Response.success(
                    data=pd.DataFrame(),
                    message="该日期范围内无新股数据",
                    n_stocks=0,
                    provider=self.provider_name,
                    elapsed_time="0s"
                )

            elapsed = time.time() - start_time
            logger.info(f"成功获取 {len(df)} 只新股")
            return Response.success(
                data=df,
                message=f"成功获取 {len(df)} 只新股（{start_date} ~ {end_date}）",
                n_stocks=len(df),
                provider=self.provider_name,
                elapsed_time=f"{elapsed:.2f}s"
            )

        except TusharePermissionError as e:
            logger.error(f"获取新股列表失败: {e}")
            return Response.error(error=str(e), error_code="TUSHARE_PERMISSION_ERROR", provider=self.provider_name, days=days)
        except TushareRateLimitError as e:
            logger.error(f"获取新股列表失败: {e}")
            return Response.error(error=str(e), error_code="TUSHARE_RATE_LIMIT_ERROR", provider=self.provider_name, days=days, retry_after=e.retry_after)
        except TushareDataError as e:
            logger.error(f"获取新股列表失败: {e}")
            return Response.error(error=str(e), error_code="TUSHARE_DATA_ERROR", provider=self.provider_name, days=days)
        except Exception as e:
            logger.error(f"获取新股列表失败: {e}")
            return Response.error(error=f"获取新股列表失败: {str(e)}", error_code="TUSHARE_UNEXPECTED_ERROR", provider=self.provider_name, days=days)

    def get_delisted_stocks(self) -> Response:
        """
        获取退市股票列表

        Returns:
            Response: 响应对象
                - data: pd.DataFrame 标准化的退市股票列表
                - metadata: 元数据(n_stocks)
        """
        from ..config import TushareFields
        from ..exceptions import TusharePermissionError, TushareRateLimitError, TushareDataError

        try:
            start_time = time.time()
            logger.info("正在从 Tushare 获取退市股票列表...")

            df = self.api_client.execute(
                self.api_client.stock_basic,
                exchange='',
                list_status='D',
                fields=TushareFields.DELISTED_STOCK_FIELDS
            )

            if df is None or df.empty:
                return Response.error(
                    error="获取退市股票列表失败，返回数据为空",
                    error_code="TUSHARE_EMPTY_DATA",
                    provider=self.provider_name
                )

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
            return Response.error(error=str(e), error_code="TUSHARE_PERMISSION_ERROR", provider=self.provider_name)
        except TushareRateLimitError as e:
            logger.error(f"获取退市股票列表失败: {e}")
            return Response.error(error=str(e), error_code="TUSHARE_RATE_LIMIT_ERROR", provider=self.provider_name, retry_after=e.retry_after)
        except TushareDataError as e:
            logger.error(f"获取退市股票列表失败: {e}")
            return Response.error(error=str(e), error_code="TUSHARE_DATA_ERROR", provider=self.provider_name)
        except Exception as e:
            logger.error(f"获取退市股票列表失败: {e}")
            return Response.error(error=f"获取退市股票列表失败: {str(e)}", error_code="TUSHARE_UNEXPECTED_ERROR", provider=self.provider_name)
