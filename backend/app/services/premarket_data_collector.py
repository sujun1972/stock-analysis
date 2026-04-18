"""盘前碰撞分析 - 数据聚合模块

职责：
- 读取/生成当日（或上一交易日）的明日战术
- 读取今晨的隔夜外盘数据（overnight_market_data）
- 读取今晨的核心快讯（premarket_news_flash）
"""

from typing import Dict, Any, Optional, List
from loguru import logger

from src.database.connection_pool_manager import ConnectionPoolManager
from app.core.config import settings


class PremarketDataCollector:
    """盘前数据聚合器"""

    def __init__(self):
        self._pool_manager: Optional[ConnectionPoolManager] = None

    def _get_pool_manager(self) -> ConnectionPoolManager:
        if self._pool_manager is None:
            self._pool_manager = ConnectionPoolManager(settings.db_config_dict())
        return self._pool_manager

    async def get_or_generate_tactics(self, trade_date: str) -> Optional[Dict[str, Any]]:
        """获取或生成战术数据

        策略：
        1. 优先读取当日的战术（如果已生成）
        2. 如果当日战术未生成，尝试读取/生成上一个交易日的战术
        3. 失败返回 None
        """
        try:
            tactics = self._fetch_tactics_by_date(trade_date)
            if tactics:
                logger.info(f"读取到 {trade_date} 的明日战术")
                return tactics

            logger.warning(f"{trade_date} 的战术未生成，尝试上一个交易日的战术")
            prev_trade_date = self._get_previous_trade_date(trade_date)
            if not prev_trade_date:
                logger.error(f"无法获取 {trade_date} 的上一个交易日")
                return None

            prev_tactics = self._fetch_tactics_by_date(prev_trade_date)
            if prev_tactics:
                logger.info(f"读取到上一交易日 {prev_trade_date} 的明日战术")
                return prev_tactics

            logger.info(f"开始生成 {prev_trade_date} 的明日战术...")
            generated = await self._trigger_tactics_generation(prev_trade_date)
            if generated:
                logger.success(f"成功生成 {prev_trade_date} 的明日战术")
                return self._fetch_tactics_by_date(prev_trade_date)

            logger.error(f"生成 {prev_trade_date} 的战术失败")
            return None

        except Exception as e:
            logger.error(f"获取或生成战术数据失败: {e}", exc_info=True)
            return None

    def fetch_overnight_data(self, trade_date: str) -> Optional[Dict[str, float]]:
        """读取今晨外盘数据"""
        try:
            pool_manager = self._get_pool_manager()
            conn = pool_manager.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    a50_change, china_concept_change,
                    wti_crude_change, comex_gold_change, lme_copper_change,
                    usdcnh_change, sp500_change, nasdaq_change, dow_change
                FROM overnight_market_data
                WHERE trade_date = %s
            """, (trade_date,))

            row = cursor.fetchone()
            cursor.close()
            pool_manager.release_connection(conn)

            if not row:
                return None

            return {
                'a50_change': float(row[0]) if row[0] else 0,
                'china_concept_change': float(row[1]) if row[1] else 0,
                'wti_crude_change': float(row[2]) if row[2] else 0,
                'comex_gold_change': float(row[3]) if row[3] else 0,
                'lme_copper_change': float(row[4]) if row[4] else 0,
                'usdcnh_change': float(row[5]) if row[5] else 0,
                'sp500_change': float(row[6]) if row[6] else 0,
                'nasdaq_change': float(row[7]) if row[7] else 0,
                'dow_change': float(row[8]) if row[8] else 0,
            }

        except Exception as e:
            logger.error(f"读取隔夜数据失败: {e}")
            return None

    def fetch_critical_news(self, trade_date: str) -> str:
        """读取今晨核心新闻（critical/high 等级，最多 10 条）"""
        try:
            pool_manager = self._get_pool_manager()
            conn = pool_manager.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT news_time, title, content, keywords
                FROM premarket_news_flash
                WHERE trade_date = %s
                  AND importance_level IN ('critical', 'high')
                ORDER BY news_time DESC
                LIMIT 10
            """, (trade_date,))

            rows: List = cursor.fetchall()
            cursor.close()
            pool_manager.release_connection(conn)

            if not rows:
                return "今晨无重大突发新闻"

            news_lines = []
            for idx, row in enumerate(rows, 1):
                news_time = row[0].strftime('%H:%M') if row[0] else ''
                title = row[1]
                keywords = ', '.join(row[3]) if row[3] else ''
                news_lines.append(f"{idx}. [{news_time}] {title} (关键词: {keywords})")

            return "\n".join(news_lines)

        except Exception as e:
            logger.error(f"读取核心新闻失败: {e}")
            return "今晨无重大突发新闻"

    # ---- 内部辅助 ----

    def _fetch_tactics_by_date(self, trade_date: str) -> Optional[Dict[str, Any]]:
        try:
            pool_manager = self._get_pool_manager()
            conn = pool_manager.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT tomorrow_tactics
                FROM market_sentiment_ai_analysis
                WHERE trade_date = %s
                  AND status = 'success'
                  AND tomorrow_tactics IS NOT NULL
            """, (trade_date,))

            row = cursor.fetchone()
            cursor.close()
            pool_manager.release_connection(conn)

            if row and row[0]:
                return row[0]
            return None

        except Exception as e:
            logger.error(f"读取 {trade_date} 的战术失败: {e}")
            return None

    def _get_previous_trade_date(self, trade_date: str) -> Optional[str]:
        try:
            pool_manager = self._get_pool_manager()
            conn = pool_manager.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT trade_date
                FROM market_sentiment_daily
                WHERE trade_date < %s
                ORDER BY trade_date DESC
                LIMIT 1
            """, (trade_date,))

            row = cursor.fetchone()
            cursor.close()
            pool_manager.release_connection(conn)

            if row:
                return str(row[0])
            return None

        except Exception as e:
            logger.error(f"获取上一交易日失败: {e}")
            return None

    async def _trigger_tactics_generation(self, trade_date: str) -> bool:
        try:
            from app.services.sentiment_ai_analysis_service import SentimentAIAnalysisService

            sentiment_service = SentimentAIAnalysisService()
            result = await sentiment_service.generate_ai_analysis(
                trade_date=trade_date,
                provider="deepseek"
            )
            return result.get("success", False)

        except Exception as e:
            logger.error(f"触发生成 {trade_date} 战术失败: {e}", exc_info=True)
            return False


premarket_data_collector = PremarketDataCollector()
