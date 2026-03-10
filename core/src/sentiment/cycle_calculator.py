"""
情绪周期计算引擎

负责计算每日市场情绪周期阶段，包括：
- 赚钱效应指数计算
- 情绪周期阶段判断（冰点/启动/发酵/退潮）
- 置信度评估
- 趋势分析
"""

import json
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from loguru import logger

from ..database.connection_pool_manager import ConnectionPoolManager
from .models import SentimentCycle, CycleCalculationResult
from .config import (
    CycleThresholds,
    MONEY_MAKING_INDEX_WEIGHTS,
    NORMALIZATION_PARAMS,
    get_cycle_stage_cn
)


class SentimentCycleCalculator:
    """情绪周期计算引擎"""

    def __init__(self, pool_manager: ConnectionPoolManager):
        """
        初始化

        Args:
            pool_manager: 数据库连接池管理器
        """
        self.pool_manager = pool_manager
        self.thresholds = CycleThresholds()

    def calculate_cycle_stage(self, trade_date: str) -> CycleCalculationResult:
        """
        计算指定日期的情绪周期阶段

        Args:
            trade_date: 交易日期 (YYYY-MM-DD)

        Returns:
            情绪周期计算结果
        """
        try:
            logger.info(f"开始计算 {trade_date} 的情绪周期...")

            # 1. 获取当日和前一日数据
            current_data = self._get_sentiment_data(trade_date)
            previous_data = self._get_previous_sentiment_data(trade_date)

            if not current_data:
                raise ValueError(f"{trade_date} 无情绪数据")

            # 2. 计算赚钱效应指数
            money_making_index = self._calculate_money_making_index(current_data)

            # 3. 计算连板增长率
            continuous_growth_rate = self._calculate_continuous_growth_rate(
                current_data.get('max_continuous_days', 0),
                previous_data.get('max_continuous_days', 0) if previous_data else 0
            )

            # 4. 计算成交额变化率
            amount_change_rate = self._calculate_amount_change_rate(
                current_data.get('total_amount', 0),
                previous_data.get('total_amount', 0) if previous_data else 0
            )

            # 5. 判断情绪周期阶段
            indicators = {
                'limit_up_count': current_data.get('limit_up_count', 0),
                'limit_down_count': current_data.get('limit_down_count', 0),
                'limit_ratio': current_data.get('limit_ratio', 0),
                'blast_rate': current_data.get('blast_rate', 0),
                'max_continuous_days': current_data.get('max_continuous_days', 0),
                'continuous_growth_rate': continuous_growth_rate,
                'amount_change_rate': amount_change_rate,
                'money_making_index': money_making_index
            }

            cycle_stage, confidence_score = self._determine_cycle_stage(indicators)

            # 6. 获取前一阶段信息
            previous_cycle = self._get_previous_cycle(trade_date)
            previous_stage = previous_cycle.get('cycle_stage') if previous_cycle else None
            stage_duration_days = self._calculate_stage_duration(
                cycle_stage,
                previous_stage,
                previous_cycle.get('stage_duration_days', 0) if previous_cycle else 0
            )
            stage_change_date = trade_date if cycle_stage != previous_stage else (
                previous_cycle.get('stage_change_date') if previous_cycle else trade_date
            )

            # 7. 生成分析报告
            analysis_result = self._generate_analysis_report(indicators, cycle_stage)

            # 8. 构建情绪周期数据
            cycle_data = SentimentCycle(
                trade_date=trade_date,
                cycle_stage=cycle_stage,
                cycle_stage_cn=get_cycle_stage_cn(cycle_stage),
                confidence_score=confidence_score,
                limit_up_count=current_data.get('limit_up_count', 0),
                limit_down_count=current_data.get('limit_down_count', 0),
                limit_ratio=current_data.get('limit_ratio', 0),
                blast_count=current_data.get('blast_count', 0),
                blast_rate=current_data.get('blast_rate', 0),
                max_continuous_days=current_data.get('max_continuous_days', 0),
                max_continuous_count=current_data.get('max_continuous_count', 0),
                continuous_growth_rate=continuous_growth_rate,
                money_making_index=money_making_index,
                sentiment_score=self._calculate_sentiment_score(indicators),
                stage_duration_days=stage_duration_days,
                previous_stage=previous_stage,
                stage_change_date=stage_change_date,
                total_stocks=current_data.get('total_stocks', 0),
                rise_count=current_data.get('rise_count', 0),
                fall_count=current_data.get('fall_count', 0),
                rise_fall_ratio=current_data.get('rise_fall_ratio', 0),
                total_amount=current_data.get('total_amount', 0),
                amount_change_rate=amount_change_rate,
                analysis_result=analysis_result
            )

            # 9. 计算详情
            calculation_details = {
                'indicators': indicators,
                'money_making_breakdown': {
                    'limit_up_score': self._normalize_limit_up_score(indicators['limit_up_count']),
                    'ratio_score': self._normalize_ratio_score(indicators['limit_ratio']),
                    'continuous_score': self._normalize_continuous_score(indicators['max_continuous_days']),
                    'blast_score': self._normalize_blast_score(indicators['blast_rate'])
                }
            }

            result = CycleCalculationResult(
                trade_date=trade_date,
                cycle_data=cycle_data,
                calculation_details=calculation_details,
                warnings=self._check_warnings(indicators)
            )

            logger.success(
                f"{trade_date} 情绪周期计算完成: {cycle_data.cycle_stage_cn} "
                f"(赚钱效应: {money_making_index:.1f}分)"
            )

            return result

        except Exception as e:
            logger.error(f"计算情绪周期失败: {e}")
            raise

    def _get_sentiment_data(self, trade_date: str) -> Optional[Dict]:
        """获取指定日期的情绪数据"""
        try:
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            # 查询大盘数据
            cursor.execute("""
                SELECT total_amount
                FROM market_sentiment_daily
                WHERE trade_date = %s
            """, (trade_date,))

            row = cursor.fetchone()
            total_amount = float(row[0]) if row and row[0] else 0.0

            # 查询涨停板池数据
            cursor.execute("""
                SELECT
                    limit_up_count, limit_down_count, blast_count, blast_rate,
                    max_continuous_days, max_continuous_count,
                    total_stocks, rise_count, fall_count, rise_fall_ratio
                FROM limit_up_pool
                WHERE trade_date = %s
            """, (trade_date,))

            row = cursor.fetchone()
            cursor.close()
            self.pool_manager.release_connection(conn)

            if not row:
                return None

            # 计算涨停/跌停比
            limit_up_count = row[0] or 0
            limit_down_count = row[1] or 0
            limit_ratio = limit_up_count / limit_down_count if limit_down_count > 0 else (
                10.0 if limit_up_count > 0 else 0.0
            )

            return {
                'limit_up_count': limit_up_count,
                'limit_down_count': limit_down_count,
                'blast_count': row[2] or 0,
                'blast_rate': float(row[3]) if row[3] else 0.0,
                'max_continuous_days': row[4] or 0,
                'max_continuous_count': row[5] or 0,
                'total_stocks': row[6] or 0,
                'rise_count': row[7] or 0,
                'fall_count': row[8] or 0,
                'rise_fall_ratio': float(row[9]) if row[9] else 0.0,
                'total_amount': total_amount,
                'limit_ratio': limit_ratio
            }

        except Exception as e:
            logger.error(f"获取情绪数据失败: {e}")
            return None

    def _get_previous_sentiment_data(self, trade_date: str) -> Optional[Dict]:
        """获取前一交易日的情绪数据"""
        try:
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            # 查询前一交易日
            cursor.execute("""
                SELECT trade_date
                FROM trading_calendar
                WHERE trade_date < %s AND is_trading_day = true
                ORDER BY trade_date DESC
                LIMIT 1
            """, (trade_date,))

            row = cursor.fetchone()
            cursor.close()
            self.pool_manager.release_connection(conn)

            if not row:
                return None

            previous_date = row[0].strftime('%Y-%m-%d')
            return self._get_sentiment_data(previous_date)

        except Exception as e:
            logger.error(f"获取前一日情绪数据失败: {e}")
            return None

    def _get_previous_cycle(self, trade_date: str) -> Optional[Dict]:
        """获取前一日的情绪周期数据"""
        try:
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    cycle_stage, stage_duration_days, stage_change_date
                FROM market_sentiment_cycle
                WHERE trade_date < %s
                ORDER BY trade_date DESC
                LIMIT 1
            """, (trade_date,))

            row = cursor.fetchone()
            cursor.close()
            self.pool_manager.release_connection(conn)

            if not row:
                return None

            return {
                'cycle_stage': row[0],
                'stage_duration_days': row[1],
                'stage_change_date': row[2].strftime('%Y-%m-%d') if row[2] else None
            }

        except Exception as e:
            logger.error(f"获取前一日周期数据失败: {e}")
            return None

    def _calculate_money_making_index(self, data: Dict) -> float:
        """
        计算赚钱效应指数 (0-100分)

        权重分配:
        - 涨停数: 30%
        - 涨跌比: 25%
        - 连板高度: 25%
        - 炸板率: 20%
        """
        weights = MONEY_MAKING_INDEX_WEIGHTS

        # 1. 涨停数得分 (0-30分)
        limit_up_score = self._normalize_limit_up_score(data.get('limit_up_count', 0))

        # 2. 涨跌比得分 (0-25分)
        ratio_score = self._normalize_ratio_score(data.get('limit_ratio', 0))

        # 3. 连板高度得分 (0-25分)
        continuous_score = self._normalize_continuous_score(data.get('max_continuous_days', 0))

        # 4. 炸板率得分 (0-20分, 炸板率越低得分越高)
        blast_score = self._normalize_blast_score(data.get('blast_rate', 0))

        total_score = limit_up_score + ratio_score + continuous_score + blast_score

        return round(min(100.0, max(0.0, total_score)), 2)

    def _normalize_limit_up_score(self, limit_up_count: int) -> float:
        """归一化涨停数得分"""
        max_count = NORMALIZATION_PARAMS['limit_up_count_max']
        weight = MONEY_MAKING_INDEX_WEIGHTS['limit_up_count']
        return min(limit_up_count / max_count, 1.0) * weight * 100

    def _normalize_ratio_score(self, limit_ratio: float) -> float:
        """归一化涨跌比得分"""
        max_ratio = NORMALIZATION_PARAMS['limit_ratio_max']
        weight = MONEY_MAKING_INDEX_WEIGHTS['limit_ratio']
        return min(limit_ratio / max_ratio, 1.0) * weight * 100

    def _normalize_continuous_score(self, continuous_days: int) -> float:
        """归一化连板高度得分"""
        max_days = NORMALIZATION_PARAMS['continuous_days_max']
        weight = MONEY_MAKING_INDEX_WEIGHTS['continuous_height']
        return min(continuous_days / max_days, 1.0) * weight * 100

    def _normalize_blast_score(self, blast_rate: float) -> float:
        """归一化炸板率得分（炸板率越低得分越高）"""
        weight = MONEY_MAKING_INDEX_WEIGHTS['blast_rate']
        return max(0.0, (1.0 - blast_rate)) * weight * 100

    def _calculate_continuous_growth_rate(
        self,
        current_days: int,
        previous_days: int
    ) -> float:
        """计算连板高度增长率"""
        if previous_days == 0:
            return 0.0 if current_days == 0 else 1.0

        return round((current_days - previous_days) / previous_days, 4)

    def _calculate_amount_change_rate(
        self,
        current_amount: float,
        previous_amount: float
    ) -> float:
        """计算成交额变化率"""
        if previous_amount == 0:
            return 0.0

        return round((current_amount - previous_amount) / previous_amount, 4)

    def _calculate_sentiment_score(self, indicators: Dict) -> float:
        """
        计算综合情绪得分 (0-100分)

        综合考虑:
        - 赚钱效应指数: 50%
        - 涨跌家数比: 30%
        - 成交额变化: 20%
        """
        money_making_score = indicators['money_making_index'] * 0.5

        # 涨跌家数比得分
        limit_ratio = indicators['limit_ratio']
        ratio_score = min(limit_ratio / 5.0, 1.0) * 30

        # 成交额变化得分（放大或萎缩）
        amount_change = indicators['amount_change_rate']
        amount_score = 20 if amount_change > 0 else max(0, 20 * (1 + amount_change))

        total = money_making_score + ratio_score + amount_score

        return round(min(100.0, max(0.0, total)), 2)

    def _determine_cycle_stage(self, indicators: Dict) -> Tuple[str, float]:
        """
        判断情绪周期阶段

        Returns:
            (cycle_stage, confidence_score) 元组
        """
        limit_up_count = indicators['limit_up_count']
        limit_down_count = indicators['limit_down_count']
        limit_ratio = indicators['limit_ratio']
        blast_rate = indicators['blast_rate']
        max_continuous_days = indicators['max_continuous_days']
        continuous_growth_rate = indicators['continuous_growth_rate']
        money_making_index = indicators['money_making_index']

        scores = {
            'freezing': 0,
            'starting': 0,
            'fermenting': 0,
            'retreating': 0
        }

        # === 冰点期判断 ===
        freezing_threshold = self.thresholds.FREEZING
        if limit_down_count >= freezing_threshold['limit_down_count_min']:
            scores['freezing'] += 30
        if limit_ratio < freezing_threshold['limit_ratio_max']:
            scores['freezing'] += 25
        if blast_rate > freezing_threshold['blast_rate_min']:
            scores['freezing'] += 25
        if money_making_index < freezing_threshold['money_making_index_max']:
            scores['freezing'] += 20

        # === 启动期判断 ===
        starting_threshold = self.thresholds.STARTING
        if limit_up_count >= starting_threshold['limit_up_count_min']:
            scores['starting'] += 30
        if limit_ratio > starting_threshold['limit_ratio_min']:
            scores['starting'] += 25
        if blast_rate < starting_threshold['blast_rate_max']:
            scores['starting'] += 20
        if (starting_threshold['money_making_index_min'] <= money_making_index
            <= starting_threshold['money_making_index_max']):
            scores['starting'] += 15
        if continuous_growth_rate > 0:  # 连板高度开始增长
            scores['starting'] += 10

        # === 发酵期判断 ===
        fermenting_threshold = self.thresholds.FERMENTING
        if limit_up_count >= fermenting_threshold['limit_up_count_min']:
            scores['fermenting'] += 30
        if limit_ratio > fermenting_threshold['limit_ratio_min']:
            scores['fermenting'] += 25
        if max_continuous_days >= fermenting_threshold['max_continuous_days_min']:
            scores['fermenting'] += 25
        if blast_rate < fermenting_threshold['blast_rate_max']:
            scores['fermenting'] += 10
        if money_making_index >= fermenting_threshold['money_making_index_min']:
            scores['fermenting'] += 10

        # === 退潮期判断 ===
        retreating_threshold = self.thresholds.RETREATING
        if blast_rate > retreating_threshold['blast_rate_min']:
            scores['retreating'] += 35
        if continuous_growth_rate < 0:  # 连板高度下降
            scores['retreating'] += 30
        if (retreating_threshold['money_making_index_min'] <= money_making_index
            <= retreating_threshold['money_making_index_max']):
            scores['retreating'] += 20
        if indicators['amount_change_rate'] < 0:  # 成交额萎缩
            scores['retreating'] += 15

        # 选择得分最高的阶段
        cycle_stage = max(scores, key=scores.get)
        confidence_score = round(min(scores[cycle_stage], 100.0), 2)

        return cycle_stage, confidence_score

    def _calculate_stage_duration(
        self,
        current_stage: str,
        previous_stage: Optional[str],
        previous_duration: int
    ) -> int:
        """计算阶段持续天数"""
        if previous_stage is None or current_stage != previous_stage:
            return 1  # 新阶段开始
        else:
            return previous_duration + 1  # 延续前一阶段

    def _generate_analysis_report(self, indicators: Dict, cycle_stage: str) -> Dict:
        """生成分析报告"""
        report = {
            'stage_reason': self._get_stage_reason(indicators, cycle_stage),
            'key_indicators': self._get_key_indicators(indicators),
            'market_characteristics': self._get_market_characteristics(indicators),
            'risk_warning': self._get_risk_warning(cycle_stage, indicators)
        }

        return report

    def _get_stage_reason(self, indicators: Dict, cycle_stage: str) -> str:
        """获取阶段判断原因"""
        reasons = {
            'freezing': f"跌停家数{indicators['limit_down_count']}家，涨跌比{indicators['limit_ratio']:.2f}，炸板率{indicators['blast_rate']*100:.1f}%，市场情绪极度低迷",
            'starting': f"涨停家数{indicators['limit_up_count']}家，涨跌比{indicators['limit_ratio']:.2f}，连板高度开始回升，市场情绪逐步回暖",
            'fermenting': f"涨停家数{indicators['limit_up_count']}家，涨跌比{indicators['limit_ratio']:.2f}，最高连板{indicators['max_continuous_days']}天，市场情绪火热",
            'retreating': f"炸板率{indicators['blast_rate']*100:.1f}%，连板高度下降{abs(indicators['continuous_growth_rate'])*100:.1f}%，市场情绪开始降温"
        }

        return reasons.get(cycle_stage, '数据不足')

    def _get_key_indicators(self, indicators: Dict) -> Dict:
        """获取关键指标评价"""
        return {
            'limit_up_strength': self._evaluate_strength(indicators['limit_up_count'], 20, 40),
            'continuous_height': self._evaluate_strength(indicators['max_continuous_days'], 3, 5),
            'blast_pressure': self._evaluate_pressure(indicators['blast_rate'], 0.4, 0.6),
            'money_making_effect': self._evaluate_strength(indicators['money_making_index'], 50, 70)
        }

    def _evaluate_strength(self, value: float, medium_threshold: float, high_threshold: float) -> str:
        """评估强度（高/中/低）"""
        if value >= high_threshold:
            return '高'
        elif value >= medium_threshold:
            return '中'
        else:
            return '低'

    def _evaluate_pressure(self, value: float, low_threshold: float, high_threshold: float) -> str:
        """评估压力（高/中/低）"""
        if value >= high_threshold:
            return '高'
        elif value >= low_threshold:
            return '中'
        else:
            return '低'

    def _get_market_characteristics(self, indicators: Dict) -> List[str]:
        """获取市场特征标签"""
        characteristics = []

        if indicators['limit_up_count'] >= 50:
            characteristics.append('涨停潮')
        if indicators['max_continuous_days'] >= 7:
            characteristics.append('超级连板')
        if indicators['blast_rate'] > 0.5:
            characteristics.append('炸板频繁')
        if indicators['limit_ratio'] > 5:
            characteristics.append('极强赚钱效应')
        if indicators['amount_change_rate'] > 0.2:
            characteristics.append('成交放量')
        if indicators['amount_change_rate'] < -0.2:
            characteristics.append('成交萎缩')

        return characteristics if characteristics else ['常规行情']

    def _get_risk_warning(self, cycle_stage: str, indicators: Dict) -> str:
        """获取风险提示"""
        warnings = {
            'freezing': '市场情绪低迷，建议控制仓位，等待企稳信号',
            'starting': '市场情绪回暖，可适度参与，注意板块轮动',
            'fermenting': '市场情绪火热，注意追高风险，及时止盈',
            'retreating': '市场情绪降温，注意仓位管理，警惕回调风险'
        }

        base_warning = warnings.get(cycle_stage, '')

        # 额外风险提示
        if indicators['blast_rate'] > 0.6:
            base_warning += '；炸板率过高，板块分化严重'
        if indicators['money_making_index'] < 30:
            base_warning += '；赚钱效应差，不建议追涨'

        return base_warning

    def _check_warnings(self, indicators: Dict) -> List[str]:
        """检查异常情况"""
        warnings = []

        if indicators['limit_down_count'] > 100:
            warnings.append('跌停家数异常偏高')
        if indicators['blast_rate'] > 0.8:
            warnings.append('炸板率异常偏高')
        if indicators['limit_up_count'] > 150:
            warnings.append('涨停家数异常偏高，数据可能异常')

        return warnings

    def save_cycle_data(self, cycle_data: SentimentCycle):
        """
        保存情绪周期数据到数据库

        Args:
            cycle_data: 情绪周期数据
        """
        try:
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO market_sentiment_cycle (
                    trade_date, cycle_stage, cycle_stage_cn, confidence_score,
                    limit_up_count, limit_down_count, limit_ratio,
                    blast_count, blast_rate,
                    max_continuous_days, max_continuous_count, continuous_growth_rate,
                    money_making_index, sentiment_score,
                    stage_duration_days, previous_stage, stage_change_date,
                    total_stocks, rise_count, fall_count, rise_fall_ratio,
                    total_amount, amount_change_rate, analysis_result
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s
                )
                ON CONFLICT (trade_date) DO UPDATE SET
                    cycle_stage = EXCLUDED.cycle_stage,
                    cycle_stage_cn = EXCLUDED.cycle_stage_cn,
                    confidence_score = EXCLUDED.confidence_score,
                    limit_up_count = EXCLUDED.limit_up_count,
                    limit_down_count = EXCLUDED.limit_down_count,
                    limit_ratio = EXCLUDED.limit_ratio,
                    blast_count = EXCLUDED.blast_count,
                    blast_rate = EXCLUDED.blast_rate,
                    max_continuous_days = EXCLUDED.max_continuous_days,
                    max_continuous_count = EXCLUDED.max_continuous_count,
                    continuous_growth_rate = EXCLUDED.continuous_growth_rate,
                    money_making_index = EXCLUDED.money_making_index,
                    sentiment_score = EXCLUDED.sentiment_score,
                    stage_duration_days = EXCLUDED.stage_duration_days,
                    previous_stage = EXCLUDED.previous_stage,
                    stage_change_date = EXCLUDED.stage_change_date,
                    total_stocks = EXCLUDED.total_stocks,
                    rise_count = EXCLUDED.rise_count,
                    fall_count = EXCLUDED.fall_count,
                    rise_fall_ratio = EXCLUDED.rise_fall_ratio,
                    total_amount = EXCLUDED.total_amount,
                    amount_change_rate = EXCLUDED.amount_change_rate,
                    analysis_result = EXCLUDED.analysis_result,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                cycle_data.trade_date,
                cycle_data.cycle_stage,
                cycle_data.cycle_stage_cn,
                cycle_data.confidence_score,
                cycle_data.limit_up_count,
                cycle_data.limit_down_count,
                cycle_data.limit_ratio,
                cycle_data.blast_count,
                cycle_data.blast_rate,
                cycle_data.max_continuous_days,
                cycle_data.max_continuous_count,
                cycle_data.continuous_growth_rate,
                cycle_data.money_making_index,
                cycle_data.sentiment_score,
                cycle_data.stage_duration_days,
                cycle_data.previous_stage,
                cycle_data.stage_change_date,
                cycle_data.total_stocks,
                cycle_data.rise_count,
                cycle_data.fall_count,
                cycle_data.rise_fall_ratio,
                cycle_data.total_amount,
                cycle_data.amount_change_rate,
                json.dumps(cycle_data.analysis_result, ensure_ascii=False)
            ))

            conn.commit()
            cursor.close()
            self.pool_manager.release_connection(conn)

            logger.success(f"{cycle_data.trade_date} 情绪周期数据已保存")

        except Exception as e:
            logger.error(f"保存情绪周期数据失败: {e}")
            raise
