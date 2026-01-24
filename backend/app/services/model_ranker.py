"""
模型排名和筛选系统
根据多维度指标自动筛选最优模型
"""

from typing import Dict, List, Optional, Any
import numpy as np
from loguru import logger

from src.database.db_manager import DatabaseManager


class ModelRanker:
    """模型排名器"""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()

        # 默认权重配置
        self.default_weights = {
            # 训练指标权重
            'ic': 10.0,              # IC (Information Coefficient)
            'rank_ic': 8.0,          # Rank IC
            'r2': 5.0,               # R² (拟合优度)

            # 回测指标权重
            'annual_return': 5.0,    # 年化收益率
            'sharpe_ratio': 15.0,    # 夏普比率（风险调整后收益）
            'max_drawdown': -10.0,   # 最大回撤（负权重，越小越好）
            'win_rate': 3.0,         # 胜率
            'profit_factor': 5.0,    # 盈亏比
            'calmar_ratio': 8.0,     # Calmar比率
        }

    def calculate_rank_score(
        self,
        train_metrics: Dict,
        backtest_metrics: Dict,
        weights: Optional[Dict] = None
    ) -> float:
        """
        计算综合评分

        评分公式（可自定义权重）:
        score = Σ(wi * normalize(metric_i))

        Args:
            train_metrics: 训练指标 {ic, rank_ic, r2, rmse}
            backtest_metrics: 回测指标 {annual_return, sharpe, max_drawdown, ...}
            weights: 自定义权重（可选）

        Returns:
            综合评分（越高越好）
        """
        w = weights or self.default_weights

        score = 0.0

        # 训练指标
        ic = self._safe_float(train_metrics.get('ic', 0))
        rank_ic = self._safe_float(train_metrics.get('rank_ic', 0))
        r2 = self._safe_float(train_metrics.get('r2', 0))

        score += w.get('ic', 0) * ic
        score += w.get('rank_ic', 0) * rank_ic
        score += w.get('r2', 0) * max(0, r2)  # R²可能为负，取max(0, r2)

        # 回测指标
        annual_return = self._safe_float(backtest_metrics.get('annual_return', 0))
        sharpe_ratio = self._safe_float(backtest_metrics.get('sharpe_ratio', 0))
        max_drawdown = self._safe_float(backtest_metrics.get('max_drawdown', 0))
        win_rate = self._safe_float(backtest_metrics.get('win_rate', 0))
        profit_factor = self._safe_float(backtest_metrics.get('profit_factor', 0))
        calmar_ratio = self._safe_float(backtest_metrics.get('calmar_ratio', 0))

        # 归一化并加权
        score += w.get('annual_return', 0) * (annual_return / 100.0)  # 百分比转小数
        score += w.get('sharpe_ratio', 0) * sharpe_ratio
        score += w.get('max_drawdown', 0) * abs(max_drawdown) / 100.0  # 负权重
        score += w.get('win_rate', 0) * (win_rate / 100.0)
        score += w.get('profit_factor', 0) * profit_factor
        score += w.get('calmar_ratio', 0) * calmar_ratio

        return round(score, 4)

    def _safe_float(self, value: Any) -> float:
        """安全转换为float"""
        try:
            if value is None:
                return 0.0
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    def filter_models(
        self,
        batch_id: int,
        min_sharpe: Optional[float] = None,
        max_drawdown: Optional[float] = None,
        min_annual_return: Optional[float] = None,
        min_win_rate: Optional[float] = None,
        min_ic: Optional[float] = None,
        top_n: Optional[int] = None
    ) -> List[Dict]:
        """
        根据条件筛选模型

        Args:
            batch_id: 批次ID
            min_sharpe: 最低夏普比率阈值
            max_drawdown: 最大回撤阈值（%，如-25表示最多回撤25%）
            min_annual_return: 最低年化收益率（%）
            min_win_rate: 最低胜率（%）
            min_ic: 最低IC值
            top_n: 返回前N个模型

        Returns:
            符合条件的模型列表
        """
        conditions = ["batch_id = %s", "status = 'completed'", "backtest_status = 'completed'"]
        params = [batch_id]

        if min_sharpe is not None:
            conditions.append("(backtest_metrics->>'sharpe_ratio')::FLOAT >= %s")
            params.append(min_sharpe)

        if max_drawdown is not None:
            conditions.append("(backtest_metrics->>'max_drawdown')::FLOAT >= %s")
            params.append(max_drawdown)

        if min_annual_return is not None:
            conditions.append("(backtest_metrics->>'annual_return')::FLOAT >= %s")
            params.append(min_annual_return)

        if min_win_rate is not None:
            conditions.append("(backtest_metrics->>'win_rate')::FLOAT >= %s")
            params.append(min_win_rate)

        if min_ic is not None:
            conditions.append("(train_metrics->>'ic')::FLOAT >= %s")
            params.append(min_ic)

        query = f"""
            SELECT
                id,
                experiment_name,
                model_id,
                config,
                train_metrics,
                backtest_metrics,
                rank_score,
                rank_position
            FROM experiments
            WHERE {' AND '.join(conditions)}
            ORDER BY rank_score DESC NULLS LAST
        """

        if top_n:
            query += f" LIMIT {top_n}"

        results = self.db._execute_query(query, tuple(params))

        models = []
        for row in results:
            models.append({
                'id': row[0],
                'experiment_name': row[1],
                'model_id': row[2],
                'config': row[3],
                'train_metrics': row[4],
                'backtest_metrics': row[5],
                'rank_score': float(row[6]) if row[6] else None,
                'rank_position': row[7]
            })

        return models

    def analyze_parameter_importance(self, batch_id: int) -> Dict[str, float]:
        """
        分析参数重要性
        计算每个参数对模型性能的影响

        Args:
            batch_id: 批次ID

        Returns:
            参数重要性字典 {param_name: importance_score}
        """
        logger.info(f"📊 分析批次 {batch_id} 的参数重要性...")

        # 获取所有完成的实验
        query = """
            SELECT config, rank_score
            FROM experiments
            WHERE batch_id = %s AND status = 'completed' AND rank_score IS NOT NULL
        """

        results = self.db._execute_query(query, (batch_id,))

        if not results:
            logger.warning("没有可用的实验数据")
            return {}

        # 提取参数和评分
        param_values = {}
        scores = []

        for row in results:
            config = row[0]
            score = float(row[1])
            scores.append(score)

            # 提取关键参数
            for key in ['symbol', 'model_type', 'target_period', 'scaler_type', 'balance_samples']:
                if key in config:
                    if key not in param_values:
                        param_values[key] = []
                    param_values[key].append((config[key], score))

        # 计算每个参数与评分的相关性
        importance = {}

        for param_name, values in param_values.items():
            # 分组计算平均得分
            groups = {}
            for val, score in values:
                val_str = str(val)
                if val_str not in groups:
                    groups[val_str] = []
                groups[val_str].append(score)

            # 计算组间方差（ANOVA F-statistic的简化版本）
            group_means = [np.mean(group) for group in groups.values()]
            overall_mean = np.mean(scores)

            # Between-group variance
            bg_var = np.var(group_means)

            # 归一化重要性得分（0-1）
            importance[param_name] = min(1.0, bg_var / (np.var(scores) + 1e-8))

        # 按重要性排序
        importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))

        logger.info(f"✅ 参数重要性: {importance}")
        return importance

    def generate_report(self, batch_id: int) -> Dict:
        """
        生成实验报告

        Args:
            batch_id: 批次ID

        Returns:
            完整的实验报告
        """
        logger.info(f"📝 生成批次 {batch_id} 的报告...")

        report = {
            'batch_id': batch_id,
            'summary': self._get_summary(batch_id),
            'top_models': self.filter_models(batch_id, top_n=10),
            'parameter_importance': self.analyze_parameter_importance(batch_id),
            'performance_distribution': self._get_performance_distribution(batch_id),
            'best_configurations': self._get_best_configurations(batch_id)
        }

        return report

    def _get_summary(self, batch_id: int) -> Dict:
        """获取批次摘要"""

        query = "SELECT * FROM batch_statistics WHERE batch_id = %s"
        result = self.db._execute_query(query, (batch_id,))

        if result:
            row = result[0]
            return {
                'batch_name': row[1],
                'strategy': row[2],
                'status': row[3],
                'total_experiments': row[4],
                'completed_experiments': row[5],
                'failed_experiments': row[6],
                'success_rate_pct': float(row[8]) if row[8] else 0,
                'avg_rank_score': float(row[13]) if row[13] else None,
                'max_rank_score': float(row[14]) if row[14] else None,
                'duration_hours': float(row[12]) if row[12] else None
            }

        return {}

    def _get_performance_distribution(self, batch_id: int) -> Dict:
        """获取性能分布统计"""

        query = """
            SELECT
                COUNT(*) as total,
                AVG((backtest_metrics->>'annual_return')::FLOAT) as avg_return,
                STDDEV((backtest_metrics->>'annual_return')::FLOAT) as std_return,
                AVG((backtest_metrics->>'sharpe_ratio')::FLOAT) as avg_sharpe,
                AVG((backtest_metrics->>'max_drawdown')::FLOAT) as avg_drawdown,
                AVG((train_metrics->>'ic')::FLOAT) as avg_ic
            FROM experiments
            WHERE batch_id = %s AND status = 'completed' AND backtest_status = 'completed'
        """

        result = self.db._execute_query(query, (batch_id,))

        if result and result[0][0]:
            row = result[0]
            return {
                'total_models': row[0],
                'avg_annual_return': round(float(row[1]), 2) if row[1] else None,
                'std_annual_return': round(float(row[2]), 2) if row[2] else None,
                'avg_sharpe_ratio': round(float(row[3]), 2) if row[3] else None,
                'avg_max_drawdown': round(float(row[4]), 2) if row[4] else None,
                'avg_ic': round(float(row[5]), 4) if row[5] else None
            }

        return {}

    def _get_best_configurations(self, batch_id: int) -> Dict:
        """找出最佳配置组合"""

        # 按模型类型分组
        query = """
            SELECT
                config->>'model_type' as model_type,
                AVG(rank_score) as avg_score,
                COUNT(*) as count
            FROM experiments
            WHERE batch_id = %s AND status = 'completed'
            GROUP BY config->>'model_type'
            ORDER BY avg_score DESC
        """

        result = self.db._execute_query(query, (batch_id,))

        best_model_type = result[0] if result else None

        # 按预测周期分组
        query = """
            SELECT
                config->>'target_period' as target_period,
                AVG(rank_score) as avg_score,
                COUNT(*) as count
            FROM experiments
            WHERE batch_id = %s AND status = 'completed'
            GROUP BY config->>'target_period'
            ORDER BY avg_score DESC
        """

        result = self.db._execute_query(query, (batch_id,))

        best_target_period = result[0] if result else None

        return {
            'best_model_type': {
                'model_type': best_model_type[0] if best_model_type else None,
                'avg_score': float(best_model_type[1]) if best_model_type and best_model_type[1] else None,
                'count': best_model_type[2] if best_model_type else 0
            },
            'best_target_period': {
                'target_period': int(best_target_period[0]) if best_target_period and best_target_period[0] else None,
                'avg_score': float(best_target_period[1]) if best_target_period and best_target_period[1] else None,
                'count': best_target_period[2] if best_target_period else 0
            }
        }


class ModelSelector:
    """
    模型选择器
    提供多种策略选择最优模型组合
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()
        self.ranker = ModelRanker(db_manager)

    def select_diverse_portfolio(
        self,
        batch_id: int,
        n_models: int = 5,
        diversity_weight: float = 0.3
    ) -> List[Dict]:
        """
        选择多样化的模型组合
        平衡性能和多样性

        Args:
            batch_id: 批次ID
            n_models: 选择模型数量
            diversity_weight: 多样性权重（0-1）

        Returns:
            模型列表
        """
        # 获取所有候选模型
        candidates = self.ranker.filter_models(batch_id, top_n=50)

        if len(candidates) <= n_models:
            return candidates

        # 初始化：选择评分最高的模型
        selected = [candidates[0]]
        remaining = candidates[1:]

        # 贪心选择：每次选择与已选模型差异最大且评分高的模型
        while len(selected) < n_models and remaining:
            best_score = -float('inf')
            best_idx = 0

            for idx, candidate in enumerate(remaining):
                # 性能得分
                performance_score = candidate['rank_score'] or 0

                # 多样性得分（与已选模型的差异）
                diversity_score = self._calculate_diversity(candidate, selected)

                # 综合得分
                combined_score = (
                    (1 - diversity_weight) * performance_score +
                    diversity_weight * diversity_score * 100  # 缩放到相同量级
                )

                if combined_score > best_score:
                    best_score = combined_score
                    best_idx = idx

            selected.append(remaining.pop(best_idx))

        return selected

    def _calculate_diversity(self, candidate: Dict, selected_models: List[Dict]) -> float:
        """计算候选模型与已选模型的平均差异度"""

        if not selected_models:
            return 1.0

        differences = []

        for selected in selected_models:
            diff = 0

            # 模型类型不同 +1
            if candidate['config'].get('model_type') != selected['config'].get('model_type'):
                diff += 1

            # 股票不同 +1
            if candidate['config'].get('symbol') != selected['config'].get('symbol'):
                diff += 1

            # 预测周期不同 +0.5
            if candidate['config'].get('target_period') != selected['config'].get('target_period'):
                diff += 0.5

            # Scaler类型不同 +0.3
            if candidate['config'].get('scaler_type') != selected['config'].get('scaler_type'):
                diff += 0.3

            differences.append(diff)

        return np.mean(differences) / 3.8  # 归一化到0-1
