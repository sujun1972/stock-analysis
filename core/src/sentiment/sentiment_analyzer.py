"""
综合情绪分析器

整合情绪周期计算和游资分析，提供全面的市场情绪分析报告。
"""

from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger

from ..database.connection_pool_manager import ConnectionPoolManager
from .cycle_calculator import SentimentCycleCalculator
from .hot_money_classifier import HotMoneyClassifier
from .models import DragonTigerAnalysis


class SentimentAnalyzer:
    """综合情绪分析器"""

    def __init__(self, pool_manager: ConnectionPoolManager):
        """
        初始化

        Args:
            pool_manager: 数据库连接池管理器
        """
        self.pool_manager = pool_manager
        self.cycle_calculator = SentimentCycleCalculator(pool_manager)
        self.hot_money_classifier = HotMoneyClassifier(pool_manager)

    def analyze_daily_sentiment(
        self,
        trade_date: str,
        save_to_db: bool = True
    ) -> DragonTigerAnalysis:
        """
        综合分析每日市场情绪

        Args:
            trade_date: 交易日期
            save_to_db: 是否保存到数据库

        Returns:
            龙虎榜深度分析结果
        """
        try:
            logger.info(f"开始综合分析 {trade_date} 市场情绪...")

            # 1. 计算情绪周期
            cycle_result = self.cycle_calculator.calculate_cycle_stage(trade_date)
            if save_to_db:
                self.cycle_calculator.save_cycle_data(cycle_result.cycle_data)

            # 2. 更新席位统计
            self.hot_money_classifier.update_seat_statistics(trade_date)

            # 3. 机构分析
            institution_analysis = self._analyze_institution(trade_date)

            # 4. 顶级游资分析
            top_tier_analysis = self._analyze_top_tier_hot_money(trade_date)

            # 5. 散户大本营分析
            retail_base_analysis = self._analyze_retail_base(trade_date)

            # 6. 游资活跃度分析
            hot_money_activity = self._analyze_hot_money_activity(trade_date)

            # 7. 市场特征分析
            market_characteristics = self._analyze_market_characteristics(
                cycle_result.cycle_data,
                institution_analysis,
                top_tier_analysis
            )

            # 8. 构建分析结果
            analysis = DragonTigerAnalysis(
                trade_date=trade_date,
                institution_top_stocks=institution_analysis['top_stocks'],
                institution_total_buy=institution_analysis['total_buy'],
                institution_total_sell=institution_analysis['total_sell'],
                institution_net_buy=institution_analysis['net_buy'],
                institution_stock_count=institution_analysis['stock_count'],
                top_tier_hot_money_stocks=top_tier_analysis['top_stocks'],
                top_tier_total_buy=top_tier_analysis['total_buy'],
                top_tier_appearance_count=top_tier_analysis['appearance_count'],
                retail_base_stocks=retail_base_analysis['stocks'],
                retail_base_total_buy=retail_base_analysis['total_buy'],
                hot_money_activity=hot_money_activity,
                market_characteristics=market_characteristics
            )

            logger.success(f"{trade_date} 市场情绪综合分析完成")

            return analysis

        except Exception as e:
            logger.error(f"综合分析市场情绪失败: {e}")
            raise

    def _analyze_institution(self, trade_date: str) -> Dict:
        """分析机构动向"""
        try:
            # 获取机构净买入排行
            top_stocks = self.hot_money_classifier.get_institution_top_stocks(
                trade_date,
                limit=10
            )

            # 统计机构总买卖金额
            total_buy = sum(stock['net_buy_amount'] for stock in top_stocks if stock['net_buy_amount'] > 0)
            total_sell = sum(abs(stock['net_buy_amount']) for stock in top_stocks if stock['net_buy_amount'] < 0)
            net_buy = total_buy - total_sell

            return {
                'top_stocks': top_stocks[:3],  # 只返回前3
                'total_buy': total_buy,
                'total_sell': total_sell,
                'net_buy': net_buy,
                'stock_count': len(top_stocks)
            }

        except Exception as e:
            logger.error(f"分析机构动向失败: {e}")
            return {
                'top_stocks': [],
                'total_buy': 0.0,
                'total_sell': 0.0,
                'net_buy': 0.0,
                'stock_count': 0
            }

    def _analyze_top_tier_hot_money(self, trade_date: str) -> Dict:
        """分析顶级游资动向"""
        try:
            # 获取顶级游资打板排行
            top_stocks = self.hot_money_classifier.get_hot_money_limit_up_stocks(
                trade_date,
                seat_type='top_tier',
                limit=10
            )

            # 统计总买入金额
            total_buy = sum(stock['total_buy_amount'] for stock in top_stocks)

            # 统计顶级游资出现次数
            appearance_count = sum(stock['hot_money_count'] for stock in top_stocks)

            return {
                'top_stocks': top_stocks,
                'total_buy': total_buy,
                'appearance_count': appearance_count
            }

        except Exception as e:
            logger.error(f"分析顶级游资动向失败: {e}")
            return {
                'top_stocks': [],
                'total_buy': 0.0,
                'appearance_count': 0
            }

    def _analyze_retail_base(self, trade_date: str) -> Dict:
        """分析散户大本营动向"""
        try:
            # 获取散户大本营操作的股票
            retail_stocks = self.hot_money_classifier.get_hot_money_limit_up_stocks(
                trade_date,
                seat_type='retail_base',
                limit=10
            )

            # 统计总买入金额
            total_buy = sum(stock['total_buy_amount'] for stock in retail_stocks)

            return {
                'stocks': retail_stocks,
                'total_buy': total_buy
            }

        except Exception as e:
            logger.error(f"分析散户大本营失败: {e}")
            return {
                'stocks': [],
                'total_buy': 0.0
            }

    def _analyze_hot_money_activity(self, trade_date: str) -> Dict:
        """分析游资活跃度"""
        try:
            # 获取龙虎榜席位分类统计
            classified_result = self.hot_money_classifier.classify_dragon_tiger_seats(trade_date)

            statistics = classified_result['statistics']

            return {
                'top_tier_count': statistics.get('top_tier_count', 0),
                'top_tier_buy_amount': statistics.get('top_tier_buy_amount', 0.0),
                'institution_count': statistics.get('institution_count', 0),
                'institution_buy_amount': statistics.get('institution_buy_amount', 0.0),
                'retail_base_count': statistics.get('retail_base_count', 0),
                'famous_count': statistics.get('famous_count', 0),
                'total_records': statistics.get('total_records', 0)
            }

        except Exception as e:
            logger.error(f"分析游资活跃度失败: {e}")
            return {}

    def _analyze_market_characteristics(
        self,
        cycle_data,
        institution_analysis: Dict,
        top_tier_analysis: Dict
    ) -> Dict:
        """分析市场特征"""
        characteristics = {
            'cycle_stage': cycle_data.cycle_stage_cn,
            'money_making_index': cycle_data.money_making_index,
            'sentiment_score': cycle_data.sentiment_score,
            'confidence': cycle_data.confidence_score,
            'features': []
        }

        # 机构特征
        if institution_analysis['net_buy'] > 100000000:  # 1亿
            characteristics['features'].append('机构大举买入')
        elif institution_analysis['net_buy'] < -50000000:  # -5000万
            characteristics['features'].append('机构净卖出')

        # 游资特征
        if top_tier_analysis['appearance_count'] >= 10:
            characteristics['features'].append('顶级游资活跃')
        if top_tier_analysis['total_buy'] > 200000000:  # 2亿
            characteristics['features'].append('游资大举扫货')

        # 情绪特征
        if cycle_data.money_making_index >= 80:
            characteristics['features'].append('超强赚钱效应')
        elif cycle_data.money_making_index <= 30:
            characteristics['features'].append('赚钱效应差')

        # 连板特征
        if cycle_data.max_continuous_days >= 7:
            characteristics['features'].append('超级连板')

        # 炸板特征
        if cycle_data.blast_rate > 0.5:
            characteristics['features'].append('炸板频繁')

        if not characteristics['features']:
            characteristics['features'].append('常规行情')

        return characteristics

    def get_market_hotspots(self, trade_date: str, limit: int = 5) -> List[Dict]:
        """
        识别市场热点板块

        Args:
            trade_date: 交易日期
            limit: 返回数量

        Returns:
            热点板块列表
        """
        try:
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            # 查询涨停板池中的股票（按板块统计）
            cursor.execute("""
                SELECT limit_up_stocks
                FROM limit_up_pool
                WHERE trade_date = %s
            """, (trade_date,))

            row = cursor.fetchone()
            cursor.close()
            self.pool_manager.release_connection(conn)

            if not row or not row[0]:
                return []

            limit_up_stocks = row[0]

            # TODO: 这里需要对接股票信息表获取板块信息
            # 简化版本：返回涨停股票前N个
            hotspots = []
            for stock in limit_up_stocks[:limit]:
                hotspots.append({
                    'stock_code': stock.get('code'),
                    'stock_name': stock.get('name'),
                    'continuous_days': stock.get('days', 0),
                    'reason': stock.get('reason', '')
                })

            return hotspots

        except Exception as e:
            logger.error(f"识别市场热点失败: {e}")
            return []

    def generate_sentiment_report(self, trade_date: str) -> Dict:
        """
        生成完整的情绪分析报告

        Args:
            trade_date: 交易日期

        Returns:
            完整报告字典
        """
        try:
            # 1. 综合分析
            analysis = self.analyze_daily_sentiment(trade_date, save_to_db=True)

            # 2. 获取情绪周期数据
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    cycle_stage_cn, money_making_index, sentiment_score,
                    confidence_score, stage_duration_days, analysis_result
                FROM market_sentiment_cycle
                WHERE trade_date = %s
            """, (trade_date,))

            row = cursor.fetchone()
            cursor.close()
            self.pool_manager.release_connection(conn)

            if not row:
                raise ValueError(f"{trade_date} 无情绪周期数据")

            # 3. 构建报告
            report = {
                'trade_date': trade_date,
                'summary': {
                    'cycle_stage': row[0],
                    'money_making_index': float(row[1]),
                    'sentiment_score': float(row[2]),
                    'confidence': float(row[3]),
                    'stage_duration': row[4]
                },
                'institution': {
                    'top_stocks': analysis.institution_top_stocks,
                    'net_buy': analysis.institution_net_buy,
                    'stock_count': analysis.institution_stock_count
                },
                'hot_money': {
                    'top_tier_stocks': analysis.top_tier_hot_money_stocks,
                    'total_buy': analysis.top_tier_total_buy,
                    'appearance_count': analysis.top_tier_appearance_count
                },
                'retail_base': {
                    'stocks': analysis.retail_base_stocks,
                    'total_buy': analysis.retail_base_total_buy
                },
                'activity': analysis.hot_money_activity,
                'characteristics': analysis.market_characteristics,
                'analysis_detail': row[5] if row[5] else {}
            }

            return report

        except Exception as e:
            logger.error(f"生成情绪分析报告失败: {e}")
            raise
