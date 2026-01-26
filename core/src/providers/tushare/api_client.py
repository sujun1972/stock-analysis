"""
Tushare API 客户端封装

负责 API 调用、重试机制、频率限制、错误处理
"""

import time
from typing import Any, Callable, Optional
from src.utils.logger import get_logger
from .config import TushareConfig, TushareErrorMessages
from .exceptions import (
    TushareTokenError,
    TusharePermissionError,
    TushareRateLimitError,
    TushareAPIError
)

logger = get_logger(__name__)


class TushareAPIClient:
    """
    Tushare Pro API 客户端

    封装 Tushare API 调用逻辑，提供：
    - 自动重试机制
    - 频率限制控制
    - 统一错误处理
    - 请求日志记录
    """

    def __init__(
        self,
        token: str,
        timeout: int = TushareConfig.DEFAULT_TIMEOUT,
        retry_count: int = TushareConfig.DEFAULT_RETRY_COUNT,
        retry_delay: int = TushareConfig.DEFAULT_RETRY_DELAY,
        request_delay: float = TushareConfig.DEFAULT_REQUEST_DELAY
    ):
        """
        初始化 API 客户端

        Args:
            token: Tushare API Token
            timeout: 请求超时时间（秒）
            retry_count: 失败重试次数
            retry_delay: 重试延迟（秒）
            request_delay: 请求间隔（秒）
        """
        if not token:
            raise TushareTokenError("Tushare Token 未配置")

        self.token = token
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.request_delay = request_delay

        # 初始化 Tushare API
        self._init_tushare_api()

    def _init_tushare_api(self) -> None:
        """初始化 Tushare Pro API"""
        try:
            import tushare as ts
            ts.set_token(self.token)
            self.pro = ts.pro_api(self.token)
            logger.info("Tushare API 客户端初始化成功")
        except ImportError:
            logger.error("Tushare 未安装，请运行: pip install tushare")
            raise ImportError("Tushare 未安装")
        except Exception as e:
            logger.error(f"Tushare API 初始化失败: {e}")
            raise TushareAPIError(f"Tushare API 初始化失败: {e}")

    def execute(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """
        执行 API 请求（带重试机制）

        Args:
            func: 要执行的 API 函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            API 返回结果

        Raises:
            TusharePermissionError: 积分不足或权限不足
            TushareRateLimitError: 频率限制
            TushareAPIError: 其他 API 错误
        """
        last_exception: Optional[Exception] = None
        func_name = func.__name__ if hasattr(func, '__name__') else str(func)

        for attempt in range(1, self.retry_count + 1):
            try:
                logger.debug(f"调用 {func_name} (尝试 {attempt}/{self.retry_count})")

                # 执行 API 调用
                result = func(*args, **kwargs)

                # 请求成功，等待请求间隔
                time.sleep(self.request_delay)

                logger.debug(f"{func_name} 调用成功")
                return result

            except Exception as e:
                last_exception = e
                error_msg = str(e)

                # 检查是否是权限/积分不足错误（不重试）
                if TushareErrorMessages.is_permission_error(error_msg):
                    logger.error(f"{func_name} 调用失败: 积分不足或权限不足 - {error_msg}")
                    raise TusharePermissionError(error_msg) from e

                # 检查是否是频率限制错误（不重试，由外层决定）
                if TushareErrorMessages.is_rate_limit_error(error_msg):
                    logger.warning(f"{func_name} 调用失败: 频率限制 - {error_msg}")
                    raise TushareRateLimitError(error_msg) from e

                # 其他错误，记录并准备重试
                logger.warning(
                    f"{func_name} 调用失败 (尝试 {attempt}/{self.retry_count}): {error_msg}"
                )

                # 如果还有重试机会，等待后重试
                if attempt < self.retry_count:
                    logger.debug(f"等待 {self.retry_delay} 秒后重试...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"{func_name} 调用失败，已用尽所有重试次数")

        # 重试次数用尽，抛出最后一次异常
        error_msg = f"{func_name} 调用失败: {last_exception}"
        logger.error(error_msg)
        raise TushareAPIError(error_msg) from last_exception

    def query(self, api_name: str, **params: Any) -> Any:
        """
        通用查询接口

        Args:
            api_name: API 接口名称（如 'stock_basic', 'daily' 等）
            **params: API 参数

        Returns:
            查询结果
        """
        if not hasattr(self.pro, api_name):
            raise TushareAPIError(f"未知的 API 接口: {api_name}")

        api_func = getattr(self.pro, api_name)
        return self.execute(api_func, **params)

    @property
    def stock_basic(self):
        """股票基本信息接口"""
        return self.pro.stock_basic

    @property
    def daily(self):
        """日线行情接口"""
        return self.pro.daily

    @property
    def stk_mins(self):
        """分钟行情接口"""
        return self.pro.stk_mins

    @property
    def realtime_quotes(self):
        """实时行情接口"""
        return self.pro.realtime_quotes

    @property
    def new_share(self):
        """新股上市接口"""
        return self.pro.new_share

    def __repr__(self) -> str:
        return f"<TushareAPIClient token={self.token[:8]}***>"
