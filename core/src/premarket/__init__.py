"""
盘前预期管理模块

负责每日早8:00的盘前数据采集和AI碰撞分析。

主要功能:
- 抓取隔夜外盘数据(A50、中概股、大宗商品、汇率)
- 过滤盘前核心新闻(财联社/金十快讯)
- AI碰撞分析(昨晚计划 vs 今晨现实)
- 生成早盘竞价行动指令

作者: AI Strategy Team
创建日期: 2026-03-11
"""

from .fetcher import PremarketDataFetcher
from .models import OvernightData, PremarketNews, CollisionAnalysisResult

__all__ = [
    'PremarketDataFetcher',
    'OvernightData',
    'PremarketNews',
    'CollisionAnalysisResult'
]
