"""
HTML报告生成器

生成完整的回测报告和因子分析报告。
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
from jinja2 import Template
from loguru import logger

from .backtest_visualizer import BacktestVisualizer
from .factor_visualizer import FactorVisualizer
from .correlation_visualizer import CorrelationVisualizer


class HTMLReportGenerator:
    """HTML报告生成器"""

    def __init__(self, theme: str = "default_theme"):
        """
        初始化报告生成器

        Args:
            theme: 可视化主题
        """
        self.theme = theme
        self.backtest_viz = BacktestVisualizer(theme)
        self.factor_viz = FactorVisualizer(theme)
        self.corr_viz = CorrelationVisualizer(theme)

    def generate_backtest_report(
        self,
        equity_curve: pd.Series,
        returns: pd.Series,
        positions: Optional[pd.DataFrame] = None,
        benchmark_curve: Optional[pd.Series] = None,
        benchmark_returns: Optional[pd.Series] = None,
        metrics: Optional[Dict[str, Any]] = None,
        strategy_name: str = "策略",
        output_path: str = "backtest_report.html",
    ) -> None:
        """
        生成完整的回测HTML报告

        Args:
            equity_curve: 策略净值曲线
            returns: 策略收益率序列
            positions: 持仓DataFrame（可选）
            benchmark_curve: 基准净值曲线（可选）
            benchmark_returns: 基准收益率序列（可选）
            metrics: 性能指标字典（可选）
            strategy_name: 策略名称
            output_path: 输出路径
        """
        logger.info(f"Generating backtest report for {strategy_name}")

        # 生成所有图表（转为HTML字符串）
        charts = {}

        # 1. 净值曲线
        fig = self.backtest_viz.plot_equity_curve(
            equity_curve, benchmark_curve, title=f"{strategy_name} - 净值曲线"
        )
        charts["equity_curve"] = fig.to_html(
            include_plotlyjs=False, div_id="equity-curve"
        )

        # 2. 累计收益率
        fig = self.backtest_viz.plot_cumulative_returns(
            returns, benchmark_returns, title=f"{strategy_name} - 累计收益率"
        )
        charts["cumulative_returns"] = fig.to_html(
            include_plotlyjs=False, div_id="cumulative-returns"
        )

        # 3. 回撤曲线
        fig = self.backtest_viz.plot_drawdown(
            equity_curve, title=f"{strategy_name} - 回撤分析"
        )
        charts["drawdown"] = fig.to_html(
            include_plotlyjs=False, div_id="drawdown"
        )

        # 4. 水下曲线
        fig = self.backtest_viz.plot_underwater(
            equity_curve, title=f"{strategy_name} - 回撤期分析"
        )
        charts["underwater"] = fig.to_html(
            include_plotlyjs=False, div_id="underwater"
        )

        # 5. 收益分布
        fig = self.backtest_viz.plot_returns_distribution(
            returns, title=f"{strategy_name} - 收益分布"
        )
        charts["returns_dist"] = fig.to_html(
            include_plotlyjs=False, div_id="returns-dist"
        )

        # 6. 月度收益热力图
        fig = self.backtest_viz.plot_monthly_returns_heatmap(
            returns, title=f"{strategy_name} - 月度收益热力图"
        )
        charts["monthly_heatmap"] = fig.to_html(
            include_plotlyjs=False, div_id="monthly-heatmap"
        )

        # 7. 滚动指标
        fig = self.backtest_viz.plot_rolling_metrics(
            returns, window=60, title=f"{strategy_name} - 滚动指标"
        )
        charts["rolling_metrics"] = fig.to_html(
            include_plotlyjs=False, div_id="rolling-metrics"
        )

        # 8. 持仓分析（如果提供）
        if positions is not None:
            fig = self.backtest_viz.plot_position_heatmap(
                positions, title=f"{strategy_name} - 持仓热力图", top_n=15
            )
            charts["position_heatmap"] = fig.to_html(
                include_plotlyjs=False, div_id="position-heatmap"
            )

            fig = self.backtest_viz.plot_turnover_rate(
                positions, title=f"{strategy_name} - 换手率"
            )
            charts["turnover"] = fig.to_html(
                include_plotlyjs=False, div_id="turnover"
            )

        # 生成HTML
        html_content = self._render_backtest_template(
            strategy_name=strategy_name,
            charts=charts,
            metrics=metrics or {},
            start_date=equity_curve.index[0],
            end_date=equity_curve.index[-1],
        )

        # 保存文件
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html_content, encoding="utf-8")

        logger.info(f"Backtest report saved to {output_path}")

    def generate_factor_report(
        self,
        factor_name: str,
        ic_series: pd.Series,
        quantile_returns: Optional[pd.DataFrame] = None,
        quantile_cum_returns: Optional[pd.DataFrame] = None,
        long_short_returns: Optional[pd.Series] = None,
        factor_data: Optional[pd.DataFrame] = None,
        metrics: Optional[Dict[str, Any]] = None,
        output_path: str = "factor_report.html",
    ) -> None:
        """
        生成因子分析HTML报告

        Args:
            factor_name: 因子名称
            ic_series: IC序列
            quantile_returns: 分层收益DataFrame（可选）
            quantile_cum_returns: 分层累计收益DataFrame（可选）
            long_short_returns: 多空组合收益序列（可选）
            factor_data: 因子原始数据（可选）
            metrics: 因子统计指标（可选）
            output_path: 输出路径
        """
        logger.info(f"Generating factor report for {factor_name}")

        # 生成所有图表
        charts = {}

        # 1. IC时间序列
        fig = self.factor_viz.plot_ic_time_series(
            ic_series, title=f"{factor_name} - IC时间序列"
        )
        charts["ic_time_series"] = fig.to_html(
            include_plotlyjs=False, div_id="ic-time-series"
        )

        # 2. IC分布
        fig = self.factor_viz.plot_ic_histogram(
            ic_series, title=f"{factor_name} - IC分布"
        )
        charts["ic_histogram"] = fig.to_html(
            include_plotlyjs=False, div_id="ic-histogram"
        )

        # 3. 分层收益（如果提供）
        if quantile_returns is not None:
            fig = self.factor_viz.plot_quantile_returns(
                quantile_returns, title=f"{factor_name} - 分层收益"
            )
            charts["quantile_returns"] = fig.to_html(
                include_plotlyjs=False, div_id="quantile-returns"
            )

        # 4. 分层累计收益（如果提供）
        if quantile_cum_returns is not None:
            fig = self.factor_viz.plot_quantile_cumulative_returns(
                quantile_cum_returns, title=f"{factor_name} - 分层累计收益"
            )
            charts["quantile_cum_returns"] = fig.to_html(
                include_plotlyjs=False, div_id="quantile-cum-returns"
            )

        # 5. 多空组合表现（如果提供）
        if long_short_returns is not None:
            fig = self.factor_viz.plot_long_short_performance(
                long_short_returns, title=f"{factor_name} - 多空组合表现"
            )
            charts["long_short"] = fig.to_html(
                include_plotlyjs=False, div_id="long-short"
            )

        # 生成HTML
        html_content = self._render_factor_template(
            factor_name=factor_name,
            charts=charts,
            metrics=metrics or {},
            start_date=ic_series.index[0],
            end_date=ic_series.index[-1],
        )

        # 保存文件
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html_content, encoding="utf-8")

        logger.info(f"Factor report saved to {output_path}")

    def _render_backtest_template(
        self,
        strategy_name: str,
        charts: Dict[str, str],
        metrics: Dict[str, Any],
        start_date: Any,
        end_date: Any,
    ) -> str:
        """
        渲染回测报告模板

        Args:
            strategy_name: 策略名称
            charts: 图表HTML字典
            metrics: 指标字典
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            HTML内容
        """
        template_str = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>回测报告 - {{ strategy_name }}</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px 0;
            margin-bottom: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        h1 {
            text-align: center;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .report-info {
            text-align: center;
            font-size: 1.1em;
            opacity: 0.9;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .metric-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .metric-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }
        .metric-label {
            font-size: 0.9em;
            color: #666;
            margin-bottom: 5px;
        }
        .metric-value {
            font-size: 1.8em;
            font-weight: bold;
            color: #667eea;
        }
        .metric-value.positive {
            color: #28a745;
        }
        .metric-value.negative {
            color: #dc3545;
        }
        .chart-container {
            background: white;
            padding: 20px;
            margin-bottom: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        .section-title {
            font-size: 1.5em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
            color: #667eea;
        }
        footer {
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 回测报告</h1>
            <div class="report-info">
                <p><strong>策略名称:</strong> {{ strategy_name }}</p>
                <p><strong>回测区间:</strong> {{ start_date }} ~ {{ end_date }}</p>
                <p><strong>生成时间:</strong> {{ generation_time }}</p>
            </div>
        </header>

        {% if metrics %}
        <section>
            <h2 class="section-title">核心指标</h2>
            <div class="metrics-grid">
                {% for key, value in metrics.items() %}
                <div class="metric-card">
                    <div class="metric-label">{{ key }}</div>
                    <div class="metric-value {% if 'return' in key|lower or 'sharpe' in key|lower %}{% if value > 0 %}positive{% else %}negative{% endif %}{% endif %}">
                        {{ value }}
                    </div>
                </div>
                {% endfor %}
            </div>
        </section>
        {% endif %}

        <section>
            <h2 class="section-title">净值曲线</h2>
            <div class="chart-container">
                {{ charts.equity_curve|safe }}
            </div>
        </section>

        <section>
            <h2 class="section-title">累计收益</h2>
            <div class="chart-container">
                {{ charts.cumulative_returns|safe }}
            </div>
        </section>

        <section>
            <h2 class="section-title">回撤分析</h2>
            <div class="chart-container">
                {{ charts.drawdown|safe }}
            </div>
            <div class="chart-container">
                {{ charts.underwater|safe }}
            </div>
        </section>

        <section>
            <h2 class="section-title">收益分析</h2>
            <div class="chart-container">
                {{ charts.returns_dist|safe }}
            </div>
            <div class="chart-container">
                {{ charts.monthly_heatmap|safe }}
            </div>
        </section>

        <section>
            <h2 class="section-title">滚动指标</h2>
            <div class="chart-container">
                {{ charts.rolling_metrics|safe }}
            </div>
        </section>

        {% if charts.position_heatmap %}
        <section>
            <h2 class="section-title">持仓分析</h2>
            <div class="chart-container">
                {{ charts.position_heatmap|safe }}
            </div>
            <div class="chart-container">
                {{ charts.turnover|safe }}
            </div>
        </section>
        {% endif %}

        <footer>
            <p>© 2026 Stock Analysis Core | Generated by HTMLReportGenerator</p>
        </footer>
    </div>
</body>
</html>
        """

        template = Template(template_str)
        return template.render(
            strategy_name=strategy_name,
            charts=charts,
            metrics=metrics,
            start_date=start_date,
            end_date=end_date,
            generation_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def _render_factor_template(
        self,
        factor_name: str,
        charts: Dict[str, str],
        metrics: Dict[str, Any],
        start_date: Any,
        end_date: Any,
    ) -> str:
        """
        渲染因子报告模板

        Args:
            factor_name: 因子名称
            charts: 图表HTML字典
            metrics: 指标字典
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            HTML内容
        """
        template_str = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>因子分析报告 - {{ factor_name }}</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        header {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 30px 0;
            margin-bottom: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        h1 {
            text-align: center;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .report-info {
            text-align: center;
            font-size: 1.1em;
            opacity: 0.9;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .metric-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .metric-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }
        .metric-label {
            font-size: 0.9em;
            color: #666;
            margin-bottom: 5px;
        }
        .metric-value {
            font-size: 1.8em;
            font-weight: bold;
            color: #f5576c;
        }
        .chart-container {
            background: white;
            padding: 20px;
            margin-bottom: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        .section-title {
            font-size: 1.5em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #f5576c;
            color: #f5576c;
        }
        footer {
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔍 因子分析报告</h1>
            <div class="report-info">
                <p><strong>因子名称:</strong> {{ factor_name }}</p>
                <p><strong>分析区间:</strong> {{ start_date }} ~ {{ end_date }}</p>
                <p><strong>生成时间:</strong> {{ generation_time }}</p>
            </div>
        </header>

        {% if metrics %}
        <section>
            <h2 class="section-title">核心指标</h2>
            <div class="metrics-grid">
                {% for key, value in metrics.items() %}
                <div class="metric-card">
                    <div class="metric-label">{{ key }}</div>
                    <div class="metric-value">{{ value }}</div>
                </div>
                {% endfor %}
            </div>
        </section>
        {% endif %}

        <section>
            <h2 class="section-title">IC分析</h2>
            <div class="chart-container">
                {{ charts.ic_time_series|safe }}
            </div>
            <div class="chart-container">
                {{ charts.ic_histogram|safe }}
            </div>
        </section>

        {% if charts.quantile_returns %}
        <section>
            <h2 class="section-title">分层回测</h2>
            <div class="chart-container">
                {{ charts.quantile_returns|safe }}
            </div>
            {% if charts.quantile_cum_returns %}
            <div class="chart-container">
                {{ charts.quantile_cum_returns|safe }}
            </div>
            {% endif %}
        </section>
        {% endif %}

        {% if charts.long_short %}
        <section>
            <h2 class="section-title">多空组合</h2>
            <div class="chart-container">
                {{ charts.long_short|safe }}
            </div>
        </section>
        {% endif %}

        <footer>
            <p>© 2026 Stock Analysis Core | Generated by HTMLReportGenerator</p>
        </footer>
    </div>
</body>
</html>
        """

        template = Template(template_str)
        return template.render(
            factor_name=factor_name,
            charts=charts,
            metrics=metrics,
            start_date=start_date,
            end_date=end_date,
            generation_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
