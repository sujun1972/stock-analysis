"""
AkShare API 客户端封装

负责 API 调用、重试机制、频率限制、错误处理
"""

import time
from typing import Any, Callable, Optional
from src.utils.logger import get_logger
from .config import AkShareConfig
from .exceptions import (
    AkShareImportError,
    AkShareDataError,
    AkShareRateLimitError,
    AkShareTimeoutError,
    AkShareNetworkError
)

logger = get_logger(__name__)


class AkShareAPIClient:
    """
    AkShare API 客户端

    封装 AkShare API 调用逻辑，提供：
    - 自动重试机制
    - 频率限制控制
    - 统一错误处理
    - 请求日志记录
    """

    def __init__(
        self,
        timeout: int = AkShareConfig.DEFAULT_TIMEOUT,
        retry_count: int = AkShareConfig.DEFAULT_RETRY_COUNT,
        retry_delay: int = AkShareConfig.DEFAULT_RETRY_DELAY,
        request_delay: float = AkShareConfig.DEFAULT_REQUEST_DELAY
    ):
        """
        初始化 API 客户端

        Args:
            timeout: 请求超时时间（秒）
            retry_count: 失败重试次数
            retry_delay: 重试延迟（秒）
            request_delay: 请求间隔（秒）
        """
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.request_delay = request_delay

        # 初始化 AkShare
        self._init_akshare()

    def _init_akshare(self) -> None:
        """初始化 AkShare 库"""
        try:
            import akshare as ak
            self.ak = ak
            logger.info("AkShare API 客户端初始化成功")
        except ImportError:
            error_msg = "AkShare 未安装，请运行: pip install akshare"
            logger.error(error_msg)
            raise AkShareImportError(error_msg)

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
            AkShareRateLimitError: IP 限流
            AkShareTimeoutError: 请求超时
            AkShareNetworkError: 网络错误
            AkShareDataError: 其他 API 错误
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
                error_msg = str(e).lower()

                # 检查是否是 IP 限流错误
                if '限流' in error_msg or 'rate limit' in error_msg or '访问频繁' in error_msg:
                    logger.warning(f"{func_name} 调用失败: IP 限流 - {e}")
                    # IP 限流不重试，直接抛出
                    raise AkShareRateLimitError(f"IP 限流: {e}") from e

                # 检查是否是超时错误
                if 'timeout' in error_msg or '超时' in error_msg:
                    logger.warning(f"{func_name} 调用失败: 请求超时 - {e}")
                    # 如果还有重试机会，继续重试
                    if attempt < self.retry_count:
                        logger.debug(f"等待 {self.retry_delay} 秒后重试...")
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        raise AkShareTimeoutError(f"请求超时: {e}") from e

                # 检查是否是网络错误
                if 'network' in error_msg or '网络' in error_msg or 'connection' in error_msg:
                    logger.warning(f"{func_name} 调用失败: 网络错误 - {e}")
                    # 如果还有重试机会，继续重试
                    if attempt < self.retry_count:
                        logger.debug(f"等待 {self.retry_delay} 秒后重试...")
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        raise AkShareNetworkError(f"网络错误: {e}") from e

                # 其他错误，记录并准备重试
                logger.warning(
                    f"{func_name} 调用失败 (尝试 {attempt}/{self.retry_count}): {e}"
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
        raise AkShareDataError(error_msg) from last_exception

    # ========== API 接口属性 ==========

    @property
    def stock_info_a_code_name(self):
        """获取股票列表接口"""
        return self.ak.stock_info_a_code_name

    @property
    def stock_zh_a_hist(self):
        """获取日线数据接口"""
        return self.ak.stock_zh_a_hist

    @property
    def stock_zh_a_hist_min_em(self):
        """获取分时数据接口"""
        return self.ak.stock_zh_a_hist_min_em

    @property
    def stock_zh_a_spot_em(self):
        """获取实时行情接口（全量）"""
        return self.ak.stock_zh_a_spot_em

    @property
    def stock_bid_ask_em(self):
        """获取实时盘口接口（单个股票）"""
        return self.ak.stock_bid_ask_em

    @property
    def stock_individual_info_em(self):
        """获取股票基本信息接口（单个股票）"""
        return self.ak.stock_individual_info_em

    @property
    def stock_new_a_spot_em(self):
        """获取新股列表接口"""
        return self.ak.stock_new_a_spot_em

    @property
    def stock_info_sh_delist(self):
        """获取上交所退市股票接口"""
        return self.ak.stock_info_sh_delist

    @property
    def stock_info_sz_delist(self):
        """获取深交所退市股票接口"""
        return self.ak.stock_info_sz_delist

    def __repr__(self) -> str:
        return f"<AkShareAPIClient timeout={self.timeout} retry={self.retry_count}>"
