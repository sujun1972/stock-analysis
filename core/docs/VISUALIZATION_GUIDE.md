# 可视化工具使用指南

Stock-Analysis Core 可视化工具提供强大的图表生成和HTML报告功能，帮助您直观地分析回测结果和因子表现。

---

## 目录

- [功能概览](#功能概览)
- [快速开始](#快速开始)
- [回测结果可视化](#回测结果可视化)
- [因子分析可视化](#因子分析可视化)
- [相关性分析可视化](#相关性分析可视化)
- [HTML报告生成](#html报告生成)
- [CLI命令使用](#cli命令使用)
- [进阶使用](#进阶使用)
- [配色主题](#配色主题)
- [常见问题](#常见问题)

---

## 功能概览

### 核心功能

1. **回测结果可视化**
   - 净值曲线
   - 回撤分析（回撤曲线、水下曲线）
   - 收益分布（直方图、月度热力图）
   - 滚动指标（夏普比率、波动率）
   - 持仓分析（持仓热力图、换手率）

2. **因子分析可视化**
   - IC时间序列
   - IC分布直方图
   - IC衰减曲线
   - 因子分层收益
   - 多空组合表现
   - 多因子IC对比

3. **相关性分析可视化**
   - 相关性热力图
   - 相关性网络图
   - 因子聚类树状图
   - VIF分析
   - 滚动相关性

4. **HTML报告生成**
   - 完整的回测报告
   - 完整的因子分析报告
   - 美观的现代化UI
   - 交互式Plotly图表
   - 支持暗色主题

---

## 快速开始

### 安装依赖

```bash
pip install plotly kaleido jinja2 scipy
```

### 基础示例

```python
from visualization import BacktestVisualizer, HTMLReportGenerator
import pandas as pd
import numpy as np

# 创建可视化器
viz = BacktestVisualizer()

# 准备数据
dates = pd.date_range('2023-01-01', periods=252, freq='D')
equity_curve = pd.Series(
    np.cumprod(1 + np.random.randn(252) * 0.01 + 0.0003),
    index=dates
)

# 生成净值曲线图
fig = viz.plot_equity_curve(equity_curve, save_path="equity.html")

# 生成完整HTML报告
report_gen = HTMLReportGenerator()
report_gen.generate_backtest_report(
    equity_curve=equity_curve,
    returns=equity_curve.pct_change().dropna(),
    strategy_name="我的策略",
    output_path="backtest_report.html"
)
```

---

## 回测结果可视化

### 1. 净值曲线

```python
from visualization import BacktestVisualizer

viz = BacktestVisualizer()

# 基础净值曲线
fig = viz.plot_equity_curve(
    equity_curve=my_equity,
    title="策略净值曲线",
    save_path="equity.html"
)

# 带基准的净值曲线
fig = viz.plot_equity_curve(
    equity_curve=my_equity,
    benchmark_curve=benchmark_equity,
    title="策略 vs 基准",
    save_path="equity_vs_benchmark.html"
)
```

**特点**:
- 自动添加图例
- 鼠标悬停显示详细数值
- 支持缩放和拖拽
- 自动日期格式化

### 2. 回撤分析

```python
# 回撤曲线
fig = viz.plot_drawdown(
    equity_curve=my_equity,
    save_path="drawdown.html"
)

# 水下曲线（标注Top5最大回撤期）
fig = viz.plot_underwater(
    equity_curve=my_equity,
    save_path="underwater.html"
)
```

**特点**:
- 自动标注最大回撤点
- 高亮显示Top5回撤期
- 填充区域显示更直观

### 3. 收益分布

```python
# 收益分布直方图
fig = viz.plot_returns_distribution(
    returns=my_returns,
    save_path="returns_dist.html"
)

# 月度收益热力图
fig = viz.plot_monthly_returns_heatmap(
    returns=my_returns,
    save_path="monthly_heatmap.html"
)
```

**特点**:
- 显示统计指标（均值、标准差、偏度、峰度）
- 红绿配色（正负收益）
- 月度热力图跨年显示

### 4. 滚动指标

```python
# 滚动夏普比率和波动率
fig = viz.plot_rolling_metrics(
    returns=my_returns,
    window=60,  # 60日滚动窗口
    save_path="rolling_metrics.html"
)
```

### 5. 持仓分析

```python
# 持仓热力图（Top20股票）
fig = viz.plot_position_heatmap(
    positions=my_positions,  # DataFrame: 日期 × 股票代码
    top_n=20,
    save_path="position_heatmap.html"
)

# 换手率曲线
fig = viz.plot_turnover_rate(
    positions=my_positions,
    save_path="turnover.html"
)
```

---

## 因子分析可视化

### 1. IC时间序列

```python
from visualization import FactorVisualizer

factor_viz = FactorVisualizer()

# IC时间序列
fig = factor_viz.plot_ic_time_series(
    ic_series=my_ic,
    title="MOM_20因子IC分析",
    save_path="ic_series.html"
)

# Rank IC时间序列
fig = factor_viz.plot_rank_ic_time_series(
    rank_ic_series=my_rank_ic,
    save_path="rank_ic.html"
)
```

**特点**:
- 自动计算IC统计指标（均值、IR比率、IC>0占比）
- 正负IC使用不同颜色
- 显示IC均值线

### 2. IC分布

```python
# IC分布直方图（含正态分布拟合）
fig = factor_viz.plot_ic_histogram(
    ic_series=my_ic,
    save_path="ic_dist.html"
)
```

### 3. IC衰减分析

```python
# IC衰减曲线
ic_decay = pd.Series([0.05, 0.04, 0.03, 0.025, 0.02], index=[1, 2, 3, 4, 5])
fig = factor_viz.plot_ic_decay(
    ic_decay=ic_decay,
    save_path="ic_decay.html"
)
```

### 4. 因子分层收益

```python
# 分层收益条形图
quantile_returns = pd.DataFrame({
    'mean_return': [0.001, 0.002, 0.003, 0.004, 0.005]
}, index=['Q1', 'Q2', 'Q3', 'Q4', 'Q5'])

fig = factor_viz.plot_quantile_returns(
    quantile_returns=quantile_returns,
    save_path="quantile_returns.html"
)

# 分层累计收益曲线
fig = factor_viz.plot_quantile_cumulative_returns(
    quantile_cum_returns=my_quantile_cum,  # DataFrame: 日期 × 分组
    save_path="quantile_cum_returns.html"
)
```

**特点**:
- 自动检测单调性
- 标注单调性检验结果
- 多分组颜色自动区分

### 5. 多空组合表现

```python
# 多空组合净值曲线
fig = factor_viz.plot_long_short_performance(
    long_short_returns=my_long_short,
    save_path="long_short.html"
)
```

**特点**:
- 自动计算总收益、年化收益、夏普比率
- 显示统计信息标注

### 6. 多因子IC对比

```python
# 批量IC对比箱线图
ic_dict = {
    'MOM_20': mom_ic,
    'MOM_60': mom60_ic,
    'REV_5': rev_ic,
}

fig = factor_viz.plot_batch_ic_comparison(
    ic_dict=ic_dict,
    save_path="batch_ic.html"
)
```

---

## 相关性分析可视化

### 1. 相关性热力图

```python
from visualization import CorrelationVisualizer

corr_viz = CorrelationVisualizer()

# 基础热力图
fig = corr_viz.plot_correlation_heatmap(
    correlation_matrix=my_corr_matrix,
    save_path="corr_heatmap.html"
)

# 带聚类的热力图
fig = corr_viz.plot_correlation_heatmap(
    correlation_matrix=my_corr_matrix,
    cluster=True,  # 层次聚类排序
    save_path="corr_heatmap_clustered.html"
)
```

### 2. 相关性网络图

```python
# 网络图（只显示相关性>0.5的连接）
fig = corr_viz.plot_correlation_network(
    correlation_matrix=my_corr_matrix,
    threshold=0.5,
    save_path="corr_network.html"
)
```

**特点**:
- 圆形布局
- 连接宽度表示相关性强度
- 正相关（绿色）、负相关（红色）

### 3. 因子聚类树状图

```python
# 层次聚类树状图
fig = corr_viz.plot_factor_clustering(
    correlation_matrix=my_corr_matrix,
    save_path="clustering.html"
)
```

### 4. VIF分析

```python
# VIF分析条形图
vif_df = pd.DataFrame({
    'factor': ['因子A', '因子B', '因子C'],
    'VIF': [2.5, 8.3, 15.6]
})

fig = corr_viz.plot_vif_analysis(
    vif_df=vif_df,
    threshold=10.0,  # VIF阈值
    save_path="vif_analysis.html"
)
```

**特点**:
- 自动判断多重共线性
- 超过阈值的因子标红
- 显示警告信息

### 5. 滚动相关性

```python
# 两因子滚动相关性
fig = corr_viz.plot_rolling_correlation(
    factor1=factor1_series,
    factor2=factor2_series,
    window=60,
    save_path="rolling_corr.html"
)
```

---

## HTML报告生成

### 回测报告

```python
from visualization.report_generator import HTMLReportGenerator

report_gen = HTMLReportGenerator()

report_gen.generate_backtest_report(
    equity_curve=my_equity,
    returns=my_returns,
    positions=my_positions,  # 可选
    benchmark_curve=benchmark_equity,  # 可选
    benchmark_returns=benchmark_returns,  # 可选
    metrics={  # 可选
        '总收益率': '45.2%',
        '夏普比率': '1.85',
        '最大回撤': '-12.3%',
    },
    strategy_name="动量策略",
    output_path="reports/momentum_backtest.html"
)
```

**报告内容**:
1. 核心指标卡片
2. 净值曲线
3. 累计收益
4. 回撤分析（回撤曲线 + 水下曲线）
5. 收益分析（分布 + 月度热力图）
6. 滚动指标（夏普 + 波动率）
7. 持仓分析（热力图 + 换手率）

### 因子报告

```python
report_gen.generate_factor_report(
    factor_name="MOM_20",
    ic_series=my_ic,
    quantile_returns=my_quantile_ret,  # 可选
    quantile_cum_returns=my_quantile_cum,  # 可选
    long_short_returns=my_long_short,  # 可选
    metrics={  # 可选
        'IC均值': '0.025',
        'IR比率': '0.52',
        'IC>0占比': '62.5%',
    },
    output_path="reports/mom20_analysis.html"
)
```

**报告内容**:
1. 核心指标卡片
2. IC分析（时间序列 + 分布）
3. 分层回测（分组收益 + 累计收益）
4. 多空组合表现

---

## CLI命令使用

### 1. visualize backtest 命令

生成回测可视化报告（从CSV/JSON文件）

```bash
# 基础用法
stock-cli visualize backtest \\
    --data backtest_result.csv \\
    --output report.html

# 完整用法
stock-cli visualize backtest \\
    --data my_strategy.json \\
    --output visual_report.html \\
    --strategy-name "我的动量策略" \\
    --theme dark_theme
```

**数据文件格式**:

CSV示例（backtest_result.csv）:
```csv
date,equity,returns,benchmark_equity,benchmark_returns,pos_000001,pos_600000,...
2023-01-01,1.0,0.0,1.0,0.0,0.05,0.03,...
2023-01-02,1.005,0.005,1.002,0.002,0.06,0.04,...
...
```

JSON示例（backtest_result.json）:
```json
{
  "equity": [...],
  "returns": [...],
  "benchmark_equity": [...],
  ...
}
```

### 2. visualize factor 命令

生成因子分析可视化报告

```bash
# 基础用法（仅IC）
stock-cli visualize factor \\
    --ic-data ic_result.csv \\
    --output factor_report.html \\
    --factor-name MOM_20

# 完整用法（含分层回测）
stock-cli visualize factor \\
    --ic-data ic_result.csv \\
    --quantile-data quantile_result.csv \\
    --output report.html \\
    --factor-name "动量因子" \\
    --theme dark_theme
```

**数据文件格式**:

IC数据（ic_result.csv）:
```csv
date,ic
2023-01-01,0.025
2023-01-02,0.032
...
```

分层数据（quantile_result.csv）:
```csv
quantile,mean_return
Q1,0.001
Q2,0.002
Q3,0.003
Q4,0.004
Q5,0.005
```

### 3. backtest命令中的可视化选项

```bash
# 添加 --visualize 标志生成可视化报告
stock-cli backtest \\
    --strategy momentum \\
    --start 2023-01-01 \\
    --end 2024-12-31 \\
    --visualize \\
    --output momentum_visual.html
```

---

## 进阶使用

### 1. 自定义图表样式

```python
from visualization import BacktestVisualizer

# 创建自定义样式的可视化器
viz = BacktestVisualizer()

# 创建自定义图表
fig = viz.create_figure(
    title="自定义标题",
    x_label="时间",
    y_label="净值",
    width=1200,
    height=600
)

# 添加自定义轨迹
fig = viz.add_trace(
    fig,
    x=my_dates,
    y=my_values,
    name="我的曲线",
    color="#FF5733",
    mode="lines+markers"
)

# 保存
viz.save_figure(fig, "custom.html")
```

### 2. 批量生成图表

```python
from pathlib import Path

viz = BacktestVisualizer()
output_dir = Path("charts")
output_dir.mkdir(exist_ok=True)

# 批量生成
charts = {
    "equity": lambda: viz.plot_equity_curve(equity, save_path=output_dir / "equity.html"),
    "drawdown": lambda: viz.plot_drawdown(equity, save_path=output_dir / "drawdown.html"),
    "returns": lambda: viz.plot_returns_distribution(returns, save_path=output_dir / "returns.html"),
}

for name, func in charts.items():
    print(f"生成 {name}...")
    func()
```

### 3. 组合多个子图

```python
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# 创建2x2子图
fig = make_subplots(
    rows=2, cols=2,
    subplot_titles=("净值曲线", "回撤曲线", "收益分布", "滚动夏普")
)

# 添加子图数据
fig.add_trace(go.Scatter(x=dates, y=equity, name="净值"), row=1, col=1)
fig.add_trace(go.Scatter(x=dates, y=drawdown, name="回撤"), row=1, col=2)
fig.add_trace(go.Histogram(x=returns, name="收益"), row=2, col=1)
fig.add_trace(go.Scatter(x=dates, y=rolling_sharpe, name="夏普"), row=2, col=2)

fig.update_layout(height=800, showlegend=False)
fig.write_html("combined.html")
```

### 4. 导出静态图片

```python
# 需要安装 kaleido: pip install kaleido

fig = viz.plot_equity_curve(equity)

# 导出PNG
viz.save_figure(fig, "equity.png", format="png", width=1200, height=600)

# 导出PDF
viz.save_figure(fig, "equity.pdf", format="pdf")

# 导出SVG
viz.save_figure(fig, "equity.svg", format="svg")
```

---

## 配色主题

### 默认主题（default_theme）

```python
viz = BacktestVisualizer(theme="default_theme")
```

**配色**:
- 主色: #1f77b4（蓝色）
- 基准: #ff7f0e（橙色）
- 多头: #2ca02c（绿色）
- 空头: #d62728（红色）
- 正收益: #28a745
- 负收益: #dc3545

### 暗色主题（dark_theme）

```python
viz = BacktestVisualizer(theme="dark_theme")
```

**配色**:
- 背景: #31363b（深灰）
- 文字: #eff0f1（浅色）
- 主色: #3daee9
- 基准: #fdbc4b

### 自定义主题

编辑 [src/visualization/config/themes.yaml](../src/visualization/config/themes.yaml):

```yaml
my_theme:
  colors:
    primary: "#your_color"
    benchmark: "#your_color"
    long: "#your_color"
    short: "#your_color"
    positive: "#your_color"
    negative: "#your_color"
    neutral: "#your_color"

  style:
    figure_size: [12, 6]
    dpi: 100
    font_family: "sans-serif"
    title_size: 14
    label_size: 12
    legend_size: 10
```

然后使用:

```python
viz = BacktestVisualizer(theme="my_theme")
```

---

## 常见问题

### 1. 图表显示乱码？

**问题**: 中文字符显示为方块

**解决**:
```python
# 安装中文字体
# macOS: 系统自带
# Windows: SimHei, Microsoft YaHei
# Linux: sudo apt-get install fonts-wqy-zenhei

# 在themes.yaml中设置
style:
  font_family: "Microsoft YaHei"  # Windows
  font_family: "PingFang SC"      # macOS
  font_family: "WenQuanYi Zen Hei"  # Linux
```

### 2. 生成图表太慢？

**优化建议**:
- 减少数据点数量（重采样）
- 使用较小的图表尺寸
- 导出HTML而非PNG（PNG需要渲染）

```python
# 重采样
equity_weekly = equity.resample('W').last()

# 减小尺寸
fig = viz.create_figure(width=800, height=400)
```

### 3. HTML文件太大？

**解决**:
- Plotly默认使用CDN（约2MB）
- 包含内联JS会更大（约5MB）
- 建议保持默认CDN模式

### 4. 无法导出PNG？

**问题**: `ValueError: Image export requires kaleido`

**解决**:
```bash
pip install kaleido
```

### 5. 图表交互不工作？

**问题**: HTML打开后无法缩放/悬停

**解决**: 确保Plotly CDN可访问，或使用离线模式：

```python
import plotly.io as pio
pio.renderers.default = "browser"
```

### 6. 报告生成失败？

**常见原因**:
- 数据格式不匹配（检查索引是否为日期）
- 缺少必需列（equity/returns）
- 数据包含NaN（使用`.dropna()`清理）

**调试**:
```python
# 检查数据格式
print(equity.head())
print(equity.index)
print(equity.dtypes)

# 清理NaN
equity = equity.dropna()
returns = returns.dropna()
```

---

## 更多示例

完整示例请查看:
- [examples/07_factor_analysis_example.py](../examples/07_factor_analysis_example.py)
- [examples/visualization_demo.py](../examples/visualization_demo.py)（待创建）

---

## 反馈与贡献

如有问题或建议，请提交Issue或Pull Request到项目仓库。

---

**文档版本**: v1.0
**更新日期**: 2026-01-31
**作者**: Quant Team
