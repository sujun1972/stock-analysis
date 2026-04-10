"""
Tushare 数据提供者主类

整合 API 客户端和数据转换器，实现 BaseDataProvider 接口。
方法按功能域拆分到 _mixins/ 子模块，本文件只包含初始化和核心辅助逻辑。
"""

from typing import Optional, Any
import pandas as pd

from src.utils.logger import get_logger
from src.utils.response import Response
from ..base_provider import BaseDataProvider
from .api_client import TushareAPIClient
from .data_converter import TushareDataConverter
from .config import TushareConfig
from .exceptions import (
    TushareDataError,
    TushareRateLimitError,
)
from ._mixins import (
    StockListMixin,
    MarketDataMixin,
    ExtendedDataMixin,
    FundFlowMixin,
    CorporateMixin,
    AdvancedMixin,
)

logger = get_logger(__name__)


class TushareProvider(
    StockListMixin,
    MarketDataMixin,
    ExtendedDataMixin,
    FundFlowMixin,
    CorporateMixin,
    AdvancedMixin,
    BaseDataProvider,
):
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
                - max_requests_per_minute: 每分钟最大请求数，0 表示不限速（默认 0）
        """
        self.token: str = kwargs.get('token', '')
        self.timeout: int = kwargs.get('timeout', TushareConfig.DEFAULT_TIMEOUT)
        self.retry_count: int = kwargs.get('retry_count', TushareConfig.DEFAULT_RETRY_COUNT)
        self.retry_delay: int = kwargs.get('retry_delay', TushareConfig.DEFAULT_RETRY_DELAY)
        self.request_delay: float = kwargs.get('request_delay', TushareConfig.DEFAULT_REQUEST_DELAY)
        self.max_requests_per_minute: int = kwargs.get('max_requests_per_minute', TushareConfig.DEFAULT_MAX_REQUESTS_PER_MINUTE)

        self.api_client: Optional[TushareAPIClient] = None
        self.converter = TushareDataConverter()

        # 调用父类初始化（会调用 _validate_config）
        super().__init__(**kwargs)

        logger.info("TushareProvider 初始化成功")

    def _validate_config(self) -> None:
        """验证配置并初始化 API 客户端"""
        if not self.token:
            raise ValueError("Tushare Token 未配置，请在系统设置中配置 Token")

        self.api_client = TushareAPIClient(
            token=self.token,
            timeout=self.timeout,
            retry_count=self.retry_count,
            retry_delay=self.retry_delay,
            request_delay=self.request_delay,
            max_requests_per_minute=self.max_requests_per_minute,
        )

    # ------------------------------------------------------------------
    # 内部辅助（供所有 Mixin 共用）
    # ------------------------------------------------------------------

    @staticmethod
    def _build_params(**kwargs) -> dict:
        """过滤 None/空值，构建 Tushare 查询参数字典。"""
        return {k: v for k, v in kwargs.items() if v is not None}

    def _query(self, api_name: str, data_desc: str, **params) -> pd.DataFrame:
        """统一执行 Tushare 查询，记录入参/结果日志，统一异常处理。

        Args:
            api_name: Tushare 接口名（如 'share_float'）
            data_desc: 数据描述（用于日志，如 '限售股解禁'）
            **params: 已过滤好的查询参数（直接传给 api_client.query）
        """
        try:
            logger.info(f"获取{data_desc}数据: {params}")
            df = self.api_client.query(api_name, **params)
            logger.info(f"获取到 {len(df)} 条{data_desc}记录 {params}")
            return df
        except TushareRateLimitError:
            raise
        except Exception as e:
            logger.error(f"获取{data_desc}数据失败: {e}")
            raise TushareDataError(f"获取{data_desc}数据失败: {str(e)}")

    def __repr__(self) -> str:
        token_preview = f"{self.token[:8]}***" if self.token else "未配置"
        return f"<TushareProvider token={token_preview}>"
