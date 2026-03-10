"""
情绪周期业务服务层

对接Core核心计算引擎，提供业务接口给API层调用。
"""

import sys
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger

# 导入Core模块
sys.path.insert(0, '/app/core')
from src.database.connection_pool_manager import ConnectionPoolManager
from src.sentiment.sentiment_analyzer import SentimentAnalyzer
from src.sentiment.hot_money_classifier import HotMoneyClassifier
from src.sentiment.cycle_calculator import SentimentCycleCalculator


class SentimentCycleService:
    """情绪周期服务"""

    def __init__(self):
        """初始化服务"""
        # 数据库配置
        db_config = {
            'host': os.getenv('DATABASE_HOST', 'timescaledb'),
            'port': int(os.getenv('DATABASE_PORT', 5432)),
            'database': os.getenv('DATABASE_NAME', 'stock_analysis'),
            'user': os.getenv('DATABASE_USER', 'stock_user'),
            'password': os.getenv('DATABASE_PASSWORD', 'stock_password_123')
        }
        self.pool_manager = ConnectionPoolManager(db_config)
        self.analyzer = SentimentAnalyzer(self.pool_manager)
        self.classifier = HotMoneyClassifier(self.pool_manager)
        self.calculator = SentimentCycleCalculator(self.pool_manager)

    def get_cycle_stage(self, date: str = None) -> Dict:
        """
        获取情绪周期阶段

        Args:
            date: 日期 (YYYY-MM-DD)，默认为最新交易日

        Returns:
            情绪周期数据
        """
        try:
            if date is None:
                date = self._get_latest_trading_date()

            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    trade_date, cycle_stage, cycle_stage_cn, confidence_score,
                    limit_up_count, limit_down_count, limit_ratio,
                    blast_rate, max_continuous_days, continuous_growth_rate,
                    money_making_index, sentiment_score,
                    stage_duration_days, previous_stage, stage_change_date,
                    rise_count, fall_count, rise_fall_ratio,
                    total_amount, amount_change_rate, analysis_result
                FROM market_sentiment_cycle
                WHERE trade_date = %s
            """, (date,))

            row = cursor.fetchone()
            cursor.close()
            self.pool_manager.release_connection(conn)

            if not row:
                return {'error': f'{date} 无情绪周期数据'}

            return {
                'trade_date': row[0].strftime('%Y-%m-%d'),
                'cycle_stage': row[1],
                'cycle_stage_cn': row[2],
                'confidence_score': float(row[3]) if row[3] else 0.0,
                'limit_up_count': row[4],
                'limit_down_count': row[5],
                'limit_ratio': float(row[6]) if row[6] else 0.0,
                'blast_rate': float(row[7]) if row[7] else 0.0,
                'max_continuous_days': row[8],
                'continuous_growth_rate': float(row[9]) if row[9] else 0.0,
                'money_making_index': float(row[10]) if row[10] else 0.0,
                'sentiment_score': float(row[11]) if row[11] else 0.0,
                'stage_duration_days': row[12],
                'previous_stage': row[13],
                'stage_change_date': row[14].strftime('%Y-%m-%d') if row[14] else None,
                'rise_count': row[15],
                'fall_count': row[16],
                'rise_fall_ratio': float(row[17]) if row[17] else 0.0,
                'total_amount': float(row[18]) if row[18] else 0.0,
                'amount_change_rate': float(row[19]) if row[19] else 0.0,
                'analysis_result': row[20] if row[20] else {}
            }

        except Exception as e:
            logger.error(f"获取情绪周期阶段失败: {e}")
            raise

    def get_cycle_history(
        self,
        start_date: str,
        end_date: str,
        page: int = 1,
        limit: int = 30
    ) -> Dict:
        """
        获取情绪周期历史

        Args:
            start_date: 开始日期
            end_date: 结束日期
            page: 页码
            limit: 每页数量

        Returns:
            分页的情绪周期历史数据
        """
        try:
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            offset = (page - 1) * limit

            # 查询总数
            cursor.execute("""
                SELECT COUNT(*)
                FROM market_sentiment_cycle
                WHERE trade_date BETWEEN %s AND %s
            """, (start_date, end_date))

            total = cursor.fetchone()[0]

            # 查询数据
            cursor.execute("""
                SELECT
                    trade_date, cycle_stage_cn, money_making_index, sentiment_score,
                    confidence_score, stage_duration_days,
                    limit_up_count, limit_down_count, max_continuous_days
                FROM market_sentiment_cycle
                WHERE trade_date BETWEEN %s AND %s
                ORDER BY trade_date DESC
                LIMIT %s OFFSET %s
            """, (start_date, end_date, limit, offset))

            rows = cursor.fetchall()
            cursor.close()
            self.pool_manager.release_connection(conn)

            records = []
            for row in rows:
                records.append({
                    'trade_date': row[0].strftime('%Y-%m-%d'),
                    'cycle_stage_cn': row[1],
                    'money_making_index': float(row[2]) if row[2] else 0.0,
                    'sentiment_score': float(row[3]) if row[3] else 0.0,
                    'confidence_score': float(row[4]) if row[4] else 0.0,
                    'stage_duration_days': row[5],
                    'limit_up_count': row[6],
                    'limit_down_count': row[7],
                    'max_continuous_days': row[8]
                })

            return {
                'total': total,
                'page': page,
                'limit': limit,
                'pages': (total + limit - 1) // limit,
                'data': records
            }

        except Exception as e:
            logger.error(f"获取情绪周期历史失败: {e}")
            raise

    def get_cycle_trend(self, days: int = 30) -> List[Dict]:
        """
        获取情绪周期趋势（近N天）

        Args:
            days: 天数

        Returns:
            趋势数据
        """
        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    trade_date, cycle_stage_cn, money_making_index, sentiment_score,
                    limit_up_count, max_continuous_days
                FROM market_sentiment_cycle
                WHERE trade_date BETWEEN %s AND %s
                ORDER BY trade_date ASC
            """, (start_date, end_date))

            rows = cursor.fetchall()
            cursor.close()
            self.pool_manager.release_connection(conn)

            trend_data = []
            for row in rows:
                trend_data.append({
                    'date': row[0].strftime('%Y-%m-%d'),
                    'stage': row[1],
                    'money_making_index': float(row[2]) if row[2] else 0.0,
                    'sentiment_score': float(row[3]) if row[3] else 0.0,
                    'limit_up_count': row[4],
                    'max_continuous_days': row[5]
                })

            return trend_data

        except Exception as e:
            logger.error(f"获取情绪周期趋势失败: {e}")
            raise

    def get_institution_ranking(
        self,
        date: str = None,
        limit: int = 3
    ) -> List[Dict]:
        """
        获取机构净买入排行

        Args:
            date: 日期，默认最新交易日
            limit: 返回数量

        Returns:
            机构排行榜
        """
        try:
            if date is None:
                date = self._get_latest_trading_date()

            return self.classifier.get_institution_top_stocks(date, limit)

        except Exception as e:
            logger.error(f"获取机构排行失败: {e}")
            raise

    def get_hot_money_ranking(
        self,
        date: str = None,
        seat_type: str = 'top_tier',
        limit: int = 10
    ) -> List[Dict]:
        """
        获取游资打板排行

        Args:
            date: 日期
            seat_type: 席位类型 (top_tier/famous)
            limit: 返回数量

        Returns:
            游资排行榜
        """
        try:
            if date is None:
                date = self._get_latest_trading_date()

            return self.classifier.get_hot_money_limit_up_stocks(date, seat_type, limit)

        except Exception as e:
            logger.error(f"获取游资排行失败: {e}")
            raise

    def get_hot_money_activity_ranking(
        self,
        days: int = 30,
        limit: int = 20
    ) -> List[Dict]:
        """
        获取游资活跃度排行

        Args:
            days: 统计天数
            limit: 返回数量

        Returns:
            活跃度排行榜
        """
        try:
            return self.classifier.get_seat_activity_ranking(days, limit)

        except Exception as e:
            logger.error(f"获取游资活跃度排行失败: {e}")
            raise

    def get_seat_detail(self, seat_name: str) -> Optional[Dict]:
        """
        获取席位详细信息

        Args:
            seat_name: 席位名称

        Returns:
            席位详细信息
        """
        try:
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    seat_name, seat_type, seat_label, city, broker, branch_office,
                    appearance_count, total_buy_amount, total_sell_amount, net_amount,
                    win_rate, avg_hold_days, trade_style, specialty_sectors, tags,
                    last_appearance_date, description
                FROM hot_money_seats
                WHERE seat_name = %s
            """, (seat_name,))

            row = cursor.fetchone()
            cursor.close()
            self.pool_manager.release_connection(conn)

            if not row:
                return None

            return {
                'seat_name': row[0],
                'seat_type': row[1],
                'seat_label': row[2],
                'city': row[3],
                'broker': row[4],
                'branch_office': row[5],
                'appearance_count': row[6],
                'total_buy_amount': float(row[7]) if row[7] else 0.0,
                'total_sell_amount': float(row[8]) if row[8] else 0.0,
                'net_amount': float(row[9]) if row[9] else 0.0,
                'win_rate': float(row[10]) if row[10] else None,
                'avg_hold_days': float(row[11]) if row[11] else None,
                'trade_style': row[12],
                'specialty_sectors': row[13] or [],
                'tags': row[14] or [],
                'last_appearance_date': row[15].strftime('%Y-%m-%d') if row[15] else None,
                'description': row[16]
            }

        except Exception as e:
            logger.error(f"获取席位详情失败: {e}")
            raise

    def get_daily_analysis(self, date: str = None) -> Dict:
        """
        获取每日情绪综合分析

        Args:
            date: 日期

        Returns:
            综合分析报告
        """
        try:
            if date is None:
                date = self._get_latest_trading_date()

            return self.analyzer.generate_sentiment_report(date)

        except Exception as e:
            logger.error(f"获取每日分析失败: {e}")
            raise

    def sync_cycle_calculation(self, date: str):
        """
        同步计算情绪周期数据

        Args:
            date: 日期
        """
        try:
            logger.info(f"开始同步计算 {date} 情绪周期...")

            # 执行综合分析（会自动计算周期并保存）
            self.analyzer.analyze_daily_sentiment(date, save_to_db=True)

            logger.success(f"{date} 情绪周期计算完成")

        except Exception as e:
            logger.error(f"同步计算情绪周期失败: {e}")
            raise

    def get_cycle_statistics(self, start_date: str, end_date: str) -> Dict:
        """
        获取情绪周期统计分析

        Args:
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            统计分析数据
        """
        try:
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            # 统计各阶段天数
            cursor.execute("""
                SELECT
                    cycle_stage_cn,
                    COUNT(*) as days,
                    AVG(money_making_index) as avg_index,
                    AVG(sentiment_score) as avg_score
                FROM market_sentiment_cycle
                WHERE trade_date BETWEEN %s AND %s
                GROUP BY cycle_stage_cn
            """, (start_date, end_date))

            rows = cursor.fetchall()

            stage_stats = []
            for row in rows:
                stage_stats.append({
                    'stage': row[0],
                    'days': row[1],
                    'avg_money_making_index': round(float(row[2]), 2) if row[2] else 0.0,
                    'avg_sentiment_score': round(float(row[3]), 2) if row[3] else 0.0
                })

            # 统计平均指标
            cursor.execute("""
                SELECT
                    AVG(money_making_index) as avg_money_index,
                    AVG(sentiment_score) as avg_sentiment,
                    AVG(limit_up_count) as avg_limit_up,
                    AVG(max_continuous_days) as avg_continuous
                FROM market_sentiment_cycle
                WHERE trade_date BETWEEN %s AND %s
            """, (start_date, end_date))

            row = cursor.fetchone()
            cursor.close()
            self.pool_manager.release_connection(conn)

            return {
                'stage_distribution': stage_stats,
                'overall_stats': {
                    'avg_money_making_index': round(float(row[0]), 2) if row[0] else 0.0,
                    'avg_sentiment_score': round(float(row[1]), 2) if row[1] else 0.0,
                    'avg_limit_up_count': round(float(row[2]), 2) if row[2] else 0.0,
                    'avg_continuous_days': round(float(row[3]), 2) if row[3] else 0.0
                }
            }

        except Exception as e:
            logger.error(f"获取周期统计失败: {e}")
            raise

    def _get_latest_trading_date(self) -> str:
        """获取最新交易日"""
        try:
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT trade_date
                FROM trading_calendar
                WHERE is_trading_day = true AND trade_date <= CURRENT_DATE
                ORDER BY trade_date DESC
                LIMIT 1
            """)

            row = cursor.fetchone()
            cursor.close()
            self.pool_manager.release_connection(conn)

            if row:
                return row[0].strftime('%Y-%m-%d')
            else:
                return datetime.now().strftime('%Y-%m-%d')

        except Exception as e:
            logger.error(f"获取最新交易日失败: {e}")
            return datetime.now().strftime('%Y-%m-%d')
