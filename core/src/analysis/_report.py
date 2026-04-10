"""
因子分析报告数据类

FactorAnalysisReport: 单因子或多因子分析的完整结果载体
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .ic_calculator import ICResult
from .factor_optimizer import OptimizationResult


@dataclass
class FactorAnalysisReport:
    """因子分析完整报告"""
    factor_name: str

    # IC分析结果
    ic_result: Optional[ICResult] = None

    # 分层测试结果
    layering_result: Optional[pd.DataFrame] = None
    layering_summary: Optional[Dict] = None

    # 相关性分析结果（多因子时）
    correlation_matrix: Optional[pd.DataFrame] = None
    high_corr_pairs: Optional[List[Tuple[str, str, float]]] = None

    # 优化结果（多因子时）
    optimization_result: Optional[OptimizationResult] = None

    # 综合评价
    overall_score: Optional[float] = None
    recommendation: Optional[str] = None

    def to_dict(self) -> Dict:
        """转换为字典格式"""
        result = {
            'factor_name': self.factor_name,
        }

        if self.ic_result:
            result['ic_analysis'] = self.ic_result.to_dict()

        if self.layering_result is not None:
            result['layering_test'] = self.layering_result.to_dict()

        if self.layering_summary:
            result['layering_summary'] = self.layering_summary

        if self.correlation_matrix is not None:
            result['correlation_matrix'] = self.correlation_matrix.to_dict()

        if self.high_corr_pairs:
            result['high_correlation_pairs'] = [
                {'factor1': f1, 'factor2': f2, 'correlation': corr}
                for f1, f2, corr in self.high_corr_pairs
            ]

        if self.optimization_result:
            result['optimization'] = self.optimization_result.to_dict()

        if self.overall_score is not None:
            result['overall_score'] = self.overall_score

        if self.recommendation:
            result['recommendation'] = self.recommendation

        return result

    def __str__(self) -> str:
        """格式化输出"""
        lines = [f"\n{'='*60}"]
        lines.append(f"因子分析报告: {self.factor_name}")
        lines.append(f"{'='*60}\n")

        if self.ic_result:
            lines.append("【IC分析】")
            lines.append(str(self.ic_result))
            lines.append("")

        if self.layering_summary:
            lines.append("【分层测试】")
            for key, value in self.layering_summary.items():
                if isinstance(value, (int, float)):
                    lines.append(f"  {key}: {value:.4f}")
                else:
                    lines.append(f"  {key}: {value}")
            lines.append("")

        if self.overall_score is not None:
            lines.append(f"【综合评分】: {self.overall_score:.2f}/100")

        if self.recommendation:
            lines.append(f"【建议】: {self.recommendation}")

        lines.append(f"{'='*60}\n")

        return '\n'.join(lines)
