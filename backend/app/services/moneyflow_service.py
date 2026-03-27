"""
个股资金流向业务逻辑层（Tushare标准接口）

提供资金流向数据的业务逻辑处理，包含数据查询、统计分析、排名查询等功能。
Service层负责日期格式转换、数据聚合等业务逻辑，数据访问委托给Repository层。

数据源：Tushare pro.moneyflow()
积分消耗：2000积分/次
"""

from datetime import datetime
from typing import Dict, Optional
from loguru import logger

from app.repositories.moneyflow_repository import MoneyflowRepository
from app.services.stock_quote_cache import stock_quote_cache


class MoneyflowService:
    """
    个股资金流向业务逻辑层

    职责：
    - 日期格式转换（YYYY-MM-DD -> YYYYMMDD）
    - 数据聚合和统计
    - 排名查询
    - 分页处理
    """

    def __init__(self):
        """初始化Service，注入Repository依赖"""
        self.moneyflow_repo = MoneyflowRepository()
        logger.debug("✓ MoneyflowService initialized")

    def resolve_default_trade_date(self) -> Optional[str]:
        """
        解析默认交易日期：优先今天，否则回退到表中最新交易日。

        Returns:
            日期字符串 YYYY-MM-DD，无数据时返回 None
        """
        today = datetime.now().strftime('%Y%m%d')
        if self.moneyflow_repo.exists_by_date(today):
            return f"{today[:4]}-{today[4:6]}-{today[6:8]}"
        latest = self.moneyflow_repo.get_latest_trade_date()
        if latest:
            return f"{latest[:4]}-{latest[4:6]}-{latest[6:8]}"
        return None

    def get_moneyflow_data(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict:
        """
        获取个股资金流向数据（带分页和统计）

        Args:
            ts_code: 股票代码（可选）
            trade_date: 单日交易日期，格式：YYYY-MM-DD（可选，优先于 start/end_date）
            start_date: 开始日期，格式：YYYY-MM-DD（可选）
            end_date: 结束日期，格式：YYYY-MM-DD（可选）
            limit: 返回记录数
            offset: 偏移量

        Returns:
            包含数据列表、统计信息、总数和回填交易日期的字典
        """
        # 1. 日期格式转换（业务逻辑）
        if trade_date:
            trade_date_fmt = trade_date.replace('-', '')
            start_date_fmt = trade_date_fmt
            end_date_fmt = trade_date_fmt
            resolved_date = trade_date
        else:
            start_date_fmt = start_date.replace('-', '') if start_date else None
            end_date_fmt = end_date.replace('-', '') if end_date else None
            resolved_date = self.resolve_default_trade_date()
            if resolved_date and not start_date and not end_date:
                # 无任何日期条件时默认取最近有数据的交易日
                trade_date_fmt = resolved_date.replace('-', '')
                start_date_fmt = trade_date_fmt
                end_date_fmt = trade_date_fmt

        # 2. 获取数据（通过 Repository）
        items = self.moneyflow_repo.get_by_date_range(
            start_date=start_date_fmt or '19900101',
            end_date=end_date_fmt or '29991231',
            ts_code=ts_code,
            limit=limit,
            offset=offset
        )

        # 3. 获取总数（通过 Repository）
        total_count = self.moneyflow_repo.get_record_count(
            start_date=start_date_fmt,
            end_date=end_date_fmt,
            ts_code=ts_code
        )

        # 4. 获取统计信息（通过 Repository）
        statistics = self.moneyflow_repo.get_statistics(
            start_date=start_date_fmt,
            end_date=end_date_fmt,
            ts_code=ts_code
        )

        # 5. 注入股票名称（通过 StockQuoteCache 同步方法）
        if items:
            ts_codes = list(dict.fromkeys(item['ts_code'] for item in items))
            quotes = stock_quote_cache._repo.get_quotes(ts_codes)
            for item in items:
                item['name'] = quotes.get(item['ts_code'], {}).get('name', '')

        return {
            "items": items,
            "statistics": statistics,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "trade_date": resolved_date  # 前端用于回填日期选择器
        }

    def get_top_stocks(
        self,
        trade_date: Optional[str] = None,
        limit: int = 20
    ) -> Dict:
        """
        获取资金净流入排名前N的股票

        如果未指定日期，则使用最新交易日。

        Args:
            trade_date: 交易日期，格式：YYYY-MM-DD（可选）
            limit: 返回记录数

        Returns:
            包含排名数据和交易日期的字典

        Examples:
            >>> service = MoneyflowService()
            >>> result = service.get_top_stocks(limit=10)
        """
        # 1. 日期格式转换（业务逻辑）
        if trade_date:
            trade_date_fmt = trade_date.replace('-', '')
        else:
            # 获取最新交易日（通过 Repository）
            trade_date_fmt = self.moneyflow_repo.get_latest_trade_date()

        if not trade_date_fmt:
            logger.warning("数据库中没有资金流向数据")
            return {
                "items": [],
                "trade_date": None
            }

        # 2. 获取排名数据（通过 Repository）
        items = self.moneyflow_repo.get_top_by_net_amount(
            trade_date=trade_date_fmt,
            limit=limit
        )

        # 3. 注入股票名称
        if items:
            ts_codes = list(dict.fromkeys(item['ts_code'] for item in items))
            quotes = stock_quote_cache._repo.get_quotes(ts_codes)
            for item in items:
                item['name'] = quotes.get(item['ts_code'], {}).get('name', '')

        return {
            "items": items,
            "trade_date": trade_date_fmt
        }
