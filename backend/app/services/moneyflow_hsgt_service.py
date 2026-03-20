"""
沪深港通资金流向业务逻辑层

提供沪股通、深股通、港股通的资金流向数据业务逻辑处理，
包含数据查询、统计分析等功能。

数据源：Tushare沪深港通资金流向
"""

from typing import Dict, List, Optional
from loguru import logger

from app.repositories.moneyflow_hsgt_repository import MoneyflowHsgtRepository


class MoneyflowHsgtService:
    """
    沪深港通资金流向业务逻辑层

    职责：
    - 日期格式转换（YYYY-MM-DD -> YYYYMMDD）
    - 数据聚合和统计
    - 最新数据查询
    - 分页处理
    """

    def __init__(self):
        """初始化Service，注入Repository依赖"""
        self.repo = MoneyflowHsgtRepository()
        logger.debug("✓ MoneyflowHsgtService initialized")

    def get_moneyflow_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
        offset: int = 0
    ) -> Dict:
        """
        获取沪深港通资金流向数据（带分页和统计）

        Args:
            start_date: 开始日期，格式：YYYY-MM-DD（可选）
            end_date: 结束日期，格式：YYYY-MM-DD（可选）
            limit: 返回记录数
            offset: 偏移量

        Returns:
            包含数据列表、统计信息和总数的字典

        Examples:
            >>> service = MoneyflowHsgtService()
            >>> result = service.get_moneyflow_data(start_date='2024-01-01')
        """
        # 1. 日期格式转换（业务逻辑）
        start_date_fmt = start_date.replace('-', '') if start_date else None
        end_date_fmt = end_date.replace('-', '') if end_date else None

        # 2. 获取数据（通过 Repository）
        items = self.repo.get_by_date_range(
            start_date=start_date_fmt or '19900101',
            end_date=end_date_fmt or '29991231',
            limit=limit,
            offset=offset
        )

        # 3. 获取总数（通过 Repository）
        total_count = self.repo.get_record_count(
            start_date=start_date_fmt,
            end_date=end_date_fmt
        )

        # 4. 获取统计信息（通过 Repository）
        statistics = self.repo.get_statistics(
            start_date=start_date_fmt,
            end_date=end_date_fmt
        )

        # 5. 单位换算：百万元 -> 亿元（业务逻辑）
        for item in items:
            for key in ['ggt_ss', 'ggt_sz', 'hgt', 'sgt', 'north_money', 'south_money']:
                if key in item and item[key]:
                    item[key] = round(item[key] / 100, 2)

        for key in ['avg_north', 'max_north', 'min_north', 'total_north',
                    'avg_south', 'max_south', 'min_south', 'total_south']:
            if key in statistics and statistics[key]:
                statistics[key] = round(statistics[key] / 100, 2)

        return {
            "items": items,
            "statistics": statistics,
            "total": total_count,
            "limit": limit,
            "offset": offset
        }

    def get_latest_moneyflow(self) -> Optional[Dict]:
        """
        获取最新的资金流向数据

        Returns:
            最新资金流向数据，如果没有数据则返回None

        Examples:
            >>> service = MoneyflowHsgtService()
            >>> latest = service.get_latest_moneyflow()
        """
        # 获取最新数据（通过 Repository）
        data = self.repo.get_latest()

        if not data:
            return None

        # 单位换算：百万元 -> 亿元（业务逻辑）
        for key in ['ggt_ss', 'ggt_sz', 'hgt', 'sgt', 'north_money', 'south_money']:
            if key in data and data[key]:
                data[key] = round(data[key] / 100, 2)

        # 计算净流入（业务逻辑）
        if data.get('north_money') is not None and data.get('south_money') is not None:
            data['net_inflow'] = round(data['north_money'] - data['south_money'], 2)
        else:
            data['net_inflow'] = 0

        return data
