"""
外部选股器

支持接入 StarRanker 等外部选股系统
"""

from typing import List, Optional
import pandas as pd
import requests
from loguru import logger

from ..base.stock_selector import SelectorParameter, StockSelector


class ExternalSelector(StockSelector):
    """
    外部选股器

    支持三种模式：
    1. StarRanker 模式：从 StarRanker API 获取股票列表
    2. 自定义 API 模式：从用户指定的 API 获取
    3. 手动输入模式：用户直接输入股票代码

    API 响应格式要求：
    {
        "stocks": ["600000.SH", "000001.SZ", ...]
    }

    示例：
        # 手动输入模式
        selector = ExternalSelector(params={
            'source': 'manual',
            'manual_stocks': '600000.SH,000001.SZ,000002.SZ'
        })

        # 自定义 API 模式
        selector = ExternalSelector(params={
            'source': 'custom_api',
            'api_endpoint': 'http://my-api.com/stocks',
            'api_timeout': 10
        })

        # StarRanker 模式（待实现）
        selector = ExternalSelector(params={
            'source': 'starranker',
            'starranker_config': {
                'mode': 'api',
                'api_endpoint': 'http://starranker-api:8000'
            }
        })
    """

    @property
    def id(self) -> str:
        return "external"

    @property
    def name(self) -> str:
        return "外部数据源选股器"

    @classmethod
    def get_parameters(cls) -> List[SelectorParameter]:
        return [
            SelectorParameter(
                name="source",
                label="数据源",
                type="select",
                default="manual",
                description="选择外部选股数据源",
            ),
            SelectorParameter(
                name="api_endpoint",
                label="API地址（仅自定义API模式）",
                type="string",
                default="",
                description="自定义 API 的完整 URL",
            ),
            SelectorParameter(
                name="api_timeout",
                label="API超时时间（秒）",
                type="integer",
                default=10,
                min_value=1,
                max_value=60,
                description="API 请求超时时间",
            ),
            SelectorParameter(
                name="manual_stocks",
                label="手动股票池（仅手动模式）",
                type="string",
                default="",
                description="逗号分隔的股票代码，如：600000.SH,000001.SZ",
            ),
            SelectorParameter(
                name="api_method",
                label="API请求方法",
                type="select",
                default="GET",
                description="HTTP请求方法",
            ),
            SelectorParameter(
                name="api_headers",
                label="API请求头（JSON格式）",
                type="string",
                default="{}",
                description="自定义请求头，如认证token",
            ),
            SelectorParameter(
                name="max_stocks",
                label="最大股票数量",
                type="integer",
                default=100,
                min_value=1,
                max_value=500,
                description="限制返回的最大股票数量",
            ),
        ]

    def select(self, date: pd.Timestamp, market_data: pd.DataFrame) -> List[str]:
        """
        从外部系统获取股票列表

        参数:
            date: 选股日期
            market_data: 全市场价格数据（本选股器不使用此参数）

        返回:
            选出的股票代码列表
        """
        source = self.params.get("source", "manual")
        max_stocks = self.params.get("max_stocks", 100)

        logger.debug(f"外部选股: date={date}, source={source}")

        # 根据数据源类型调用不同的方法
        if source == "starranker":
            stocks = self._fetch_from_starranker(date)
        elif source == "custom_api":
            api_endpoint = self.params.get("api_endpoint", "")
            if not api_endpoint:
                logger.error("自定义 API 模式必须提供 api_endpoint 参数")
                return []
            stocks = self._fetch_from_custom_api(date, api_endpoint)
        elif source == "manual":
            stocks = self._get_manual_stocks()
        else:
            logger.error(f"未知的数据源：{source}")
            return []

        # 限制股票数量
        if len(stocks) > max_stocks:
            logger.warning(
                f"股票数量 {len(stocks)} 超过限制 {max_stocks}，截取前 {max_stocks} 只"
            )
            stocks = stocks[:max_stocks]

        logger.info(f"外部选股完成: 共获取 {len(stocks)} 只股票")
        return stocks

    def _get_manual_stocks(self) -> List[str]:
        """
        从手动输入获取股票列表

        返回:
            股票代码列表
        """
        manual_stocks = self.params.get("manual_stocks", "")
        if not manual_stocks:
            logger.warning("手动模式未提供股票代码")
            return []

        # 分隔股票代码，去除空白字符
        stocks = [s.strip() for s in manual_stocks.split(",") if s.strip()]

        logger.debug(f"手动输入模式: 获取到 {len(stocks)} 只股票")
        return stocks

    def _fetch_from_starranker(self, date: pd.Timestamp) -> List[str]:
        """
        从 StarRanker 获取股票列表

        集成方式：
        1. HTTP API 调用（推荐）
        2. 数据库查询
        3. 文件读取

        参数:
            date: 选股日期

        返回:
            股票代码列表

        注意:
            当前为占位实现，返回空列表
            实际集成需要与 StarRanker 团队协调确定接口规范
        """
        # TODO: 实现 StarRanker 集成
        # 可能的实现：
        # starranker_config = self.params.get('starranker_config', {})
        # mode = starranker_config.get('mode', 'api')
        #
        # if mode == 'api':
        #     return self._starranker_api_call(date, starranker_config)
        # elif mode == 'database':
        #     return self._starranker_db_query(date, starranker_config)
        # elif mode == 'file':
        #     return self._starranker_file_read(date, starranker_config)

        logger.warning("StarRanker 集成待实现，返回空列表")
        return []

    def _fetch_from_custom_api(
        self, date: pd.Timestamp, api_endpoint: str
    ) -> List[str]:
        """
        从自定义 API 获取股票列表

        API 预期响应格式：
        {
            "stocks": ["600000.SH", "000001.SZ", ...],
            "date": "2023-06-01",  # 可选
            "metadata": {...}       # 可选
        }

        参数:
            date: 选股日期
            api_endpoint: API 端点 URL

        返回:
            股票代码列表
        """
        timeout = self.params.get("api_timeout", 10)
        method = self.params.get("api_method", "GET").upper()
        headers_str = self.params.get("api_headers", "{}")

        # 解析请求头
        try:
            import json

            headers = json.loads(headers_str)
        except json.JSONDecodeError:
            logger.warning(f"无法解析 API 请求头，使用默认值: {headers_str}")
            headers = {}

        # 准备请求参数
        params = {"date": date.strftime("%Y-%m-%d")}

        logger.debug(
            f"调用自定义 API: {method} {api_endpoint}, "
            f"params={params}, timeout={timeout}s"
        )

        try:
            # 发送 HTTP 请求
            if method == "GET":
                response = requests.get(
                    api_endpoint, params=params, headers=headers, timeout=timeout
                )
            elif method == "POST":
                response = requests.post(
                    api_endpoint, json=params, headers=headers, timeout=timeout
                )
            else:
                logger.error(f"不支持的 HTTP 方法: {method}")
                return []

            response.raise_for_status()
            data = response.json()

            # 解析响应
            if "stocks" not in data:
                logger.error("API 响应缺少 'stocks' 字段")
                return []

            stocks = data["stocks"]

            if not isinstance(stocks, list):
                logger.error(f"API 响应 'stocks' 字段格式错误，期望列表，实际: {type(stocks)}")
                return []

            logger.info(f"从自定义 API 获取到 {len(stocks)} 只股票")
            return stocks

        except requests.Timeout:
            logger.error(f"API 请求超时（>{timeout}s）")
            return []
        except requests.HTTPError as e:
            logger.error(f"API 请求失败: HTTP {e.response.status_code}")
            return []
        except requests.RequestException as e:
            logger.error(f"API 请求失败: {e}")
            return []
        except ValueError as e:
            logger.error(f"解析 API 响应失败: {e}")
            return []
        except Exception as e:
            logger.error(f"未知错误: {e}")
            return []
