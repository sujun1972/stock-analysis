"""
模型排名和筛选系统（重构版）
根据多维度指标自动筛选最优模型
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

import numpy as np
from loguru import logger

from app.repositories.experiment_repository import ExperimentRepository

if TYPE_CHECKING:
    from src.database.db_manager import DatabaseManager


class ModelRanker:
    """模型排名器"""

    def __init__(self, db=None):
        """
        初始化模型排名器

        Args:
            db: DatabaseManager 实例（可选，传递给 Repository）
        """
        self.experiment_repo = ExperimentRepository(db)

        # 默认权重配置
        self.default_weights = {
            # 训练指标权重
            "ic": 10.0,  # IC (Information Coefficient)
            "rank_ic": 8.0,  # Rank IC
            "r2": 5.0,  # R² (拟合优度)
            # 回测指标权重
            "annual_return": 5.0,  # 年化收益率
            "sharpe_ratio": 15.0,  # 夏普比率（风险调整后收益）
            "max_drawdown": -10.0,  # 最大回撤（负权重，越小越好）
            "win_rate": 3.0,  # 胜率
            "profit_factor": 5.0,  # 盈亏比
            "calmar_ratio": 8.0,  # Calmar比率
        }

    def calculate_rank_score(
        self, train_metrics: Dict, backtest_metrics: Dict, weights: Optional[Dict] = None
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
        ic = self._safe_float(train_metrics.get("ic", 0))
        rank_ic = self._safe_float(train_metrics.get("rank_ic", 0))
        r2 = self._safe_float(train_metrics.get("r2", 0))

        score += w.get("ic", 0) * ic
        score += w.get("rank_ic", 0) * rank_ic
        score += w.get("r2", 0) * max(0, r2)  # R²可能为负，取max(0, r2)

        # 回测指标
        annual_return = self._safe_float(backtest_metrics.get("annual_return", 0))
        sharpe_ratio = self._safe_float(backtest_metrics.get("sharpe_ratio", 0))
        max_drawdown = self._safe_float(backtest_metrics.get("max_drawdown", 0))
        win_rate = self._safe_float(backtest_metrics.get("win_rate", 0))
        profit_factor = self._safe_float(backtest_metrics.get("profit_factor", 0))
        calmar_ratio = self._safe_float(backtest_metrics.get("calmar_ratio", 0))

        # 归一化并加权
        score += w.get("annual_return", 0) * (annual_return / 100.0)  # 百分比转小数
        score += w.get("sharpe_ratio", 0) * sharpe_ratio
        score += w.get("max_drawdown", 0) * abs(max_drawdown) / 100.0  # 负权重
        score += w.get("win_rate", 0) * (win_rate / 100.0)
        score += w.get("profit_factor", 0) * profit_factor
        score += w.get("calmar_ratio", 0) * calmar_ratio

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
        top_n: Optional[int] = None,
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
        # 使用 Repository 筛选实验
        experiments = self.experiment_repo.filter_experiments_by_metrics(
            batch_id=batch_id,
            min_sharpe=min_sharpe,
            max_drawdown=max_drawdown,
            min_annual_return=min_annual_return,
            min_win_rate=min_win_rate,
            min_ic=min_ic,
            top_n=top_n,
        )

        models = []
        for exp in experiments:
            # 提取回测指标（扁平化字段，便于前端直接使用）
            backtest_metrics = exp['backtest_metrics'] or {}

            # 转换为百分比（前端期望百分比格式，如 2.78 表示 2.78%）
            annual_return_pct = None
            if backtest_metrics.get("annualized_return") is not None:
                annual_return_pct = backtest_metrics["annualized_return"] * 100

            max_drawdown_pct = None
            if backtest_metrics.get("max_drawdown") is not None:
                max_drawdown_pct = backtest_metrics["max_drawdown"] * 100

            models.append(
                {
                    "experiment_id": exp['id'],  # 使用 experiment_id 作为主键
                    "experiment_name": exp['experiment_name'],
                    "model_id": exp['model_id'],
                    "config": exp['config'],
                    "train_metrics": exp['train_metrics'],
                    "backtest_metrics": backtest_metrics,
                    "rank_score": exp['rank_score'],
                    "rank_position": exp['rank_position'],
                    # 扁平化回测指标（前端直接访问，百分比格式）
                    "annual_return": annual_return_pct,  # 百分比（如 2.78 表示 2.78%）
                    "sharpe_ratio": backtest_metrics.get("sharpe_ratio"),  # 比率（不需转换）
                    "max_drawdown": max_drawdown_pct,  # 百分比（如 -30.13 表示 -30.13%）
                    "win_rate": backtest_metrics.get("win_rate"),  # 小数（前端会自行转换）
                    "calmar_ratio": backtest_metrics.get("calmar_ratio"),  # 比率（不需转换）
                }
            )

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

        # 获取所有完成的实验（使用 Repository）
        experiments = self.experiment_repo.get_experiments_with_rank_scores(batch_id)

        if not experiments:
            logger.warning("没有可用的实验数据")
            return {}

        # 提取参数和评分
        param_values = {}
        scores = []

        for exp in experiments:
            config = exp['config']
            score = exp['rank_score']
            scores.append(score)

            # 提取关键参数
            for key in ["symbol", "model_type", "target_period", "scaler_type", "balance_samples"]:
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
            np.mean(scores)

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
            "batch_id": batch_id,
            "summary": self._get_summary(batch_id),
            "top_models": self.filter_models(batch_id, top_n=10),
            "parameter_importance": self.analyze_parameter_importance(batch_id),
            "performance_distribution": self._get_performance_distribution(batch_id),
            "best_configurations": self._get_best_configurations(batch_id),
        }

        return report

    def _get_summary(self, batch_id: int) -> Dict:
        """
        获取批次摘要

        注意：batch_statistics 可能是视图或表，暂时保留直接查询
        TODO: 如果需要，可创建 BatchRepository 来管理此查询
        """
        from app.services.batch_manager import BatchManager

        batch_manager = BatchManager()
        batch_info = batch_manager.get_batch_info(batch_id)

        if batch_info:
            return {
                "batch_name": batch_info.get("batch_name"),
                "strategy": batch_info.get("strategy"),
                "status": batch_info.get("status"),
                "total_experiments": batch_info.get("total_experiments"),
                "completed_experiments": batch_info.get("completed"),
                "failed_experiments": batch_info.get("failed"),
                "success_rate_pct": batch_info.get("success_rate", 0),
                "avg_rank_score": batch_info.get("avg_rank_score"),
                "max_rank_score": batch_info.get("max_rank_score"),
                "duration_hours": batch_info.get("duration_hours"),
            }

        return {}

    def _get_performance_distribution(self, batch_id: int) -> Dict:
        """获取性能分布统计（使用 Repository）"""
        return self.experiment_repo.get_performance_statistics(batch_id)

    def _get_best_configurations(self, batch_id: int) -> Dict:
        """找出最佳配置组合（使用 Repository）"""

        # 按模型类型分组
        model_types = self.experiment_repo.get_best_configurations_by_model_type(batch_id)
        best_model_type = model_types[0] if model_types else None

        # 按预测周期分组
        target_periods = self.experiment_repo.get_best_configurations_by_target_period(batch_id)
        best_target_period = target_periods[0] if target_periods else None

        return {
            "best_model_type": {
                "model_type": best_model_type['model_type'] if best_model_type else None,
                "avg_score": best_model_type['avg_score'] if best_model_type else None,
                "count": best_model_type['count'] if best_model_type else 0,
            },
            "best_target_period": {
                "target_period": best_target_period['target_period'] if best_target_period else None,
                "avg_score": best_target_period['avg_score'] if best_target_period else None,
                "count": best_target_period['count'] if best_target_period else 0,
            },
        }


class ModelSelector:
    """
    模型选择器
    提供多种策略选择最优模型组合
    """

    def __init__(self, db_manager: Optional["DatabaseManager"] = None):
        from src.database.db_manager import DatabaseManager
        self.db = db_manager or DatabaseManager()
        self.ranker = ModelRanker(db_manager)

    def select_diverse_portfolio(
        self, batch_id: int, n_models: int = 5, diversity_weight: float = 0.3
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
            best_score = -float("inf")
            best_idx = 0

            for idx, candidate in enumerate(remaining):
                # 性能得分
                performance_score = candidate["rank_score"] or 0

                # 多样性得分（与已选模型的差异）
                diversity_score = self._calculate_diversity(candidate, selected)

                # 综合得分
                combined_score = (
                    1 - diversity_weight
                ) * performance_score + diversity_weight * diversity_score * 100  # 缩放到相同量级

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
            if candidate["config"].get("model_type") != selected["config"].get("model_type"):
                diff += 1

            # 股票不同 +1
            if candidate["config"].get("symbol") != selected["config"].get("symbol"):
                diff += 1

            # 预测周期不同 +0.5
            if candidate["config"].get("target_period") != selected["config"].get("target_period"):
                diff += 0.5

            # Scaler类型不同 +0.3
            if candidate["config"].get("scaler_type") != selected["config"].get("scaler_type"):
                diff += 0.3

            differences.append(diff)

        return np.mean(differences) / 3.8  # 归一化到0-1
