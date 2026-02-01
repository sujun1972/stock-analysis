# Stock-Analysis Core

<div align="center">

**A股AI量化交易系统核心模块**

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Test Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen.svg)]()
[![Status](https://img.shields.io/badge/status-production%20ready-success.svg)]()

**[快速开始](#快速开始) • [核心特性](#核心特性) • [文档](#完整文档) • [示例](#使用示例)**

</div>

---

## 项目简介

**Stock-Analysis Core** 是一个**生产级**的A股量化交易系统核心框架，提供从数据获取、特征工程、策略开发到回测验证的完整解决方案。

### 核心指标

| 指标 | 数值 | 说明 |
|------|------|------|
| 📊 **代码规模** | 147,936行 | 源码67K + 测试80K |
| ✅ **测试覆盖率** | 90%+ | 3,200+测试用例 |
| 🧬 **Alpha因子** | 125+ | 动量、反转、波动率等 |
| 📈 **技术指标** | 60+ | 趋势、动量、波动率 |
| 🚀 **性能提升** | 35x | 向量化计算加速 |
| 📚 **文档完整度** | 95% | Google Style文档 |

### 项目亮点

- ✅ **生产级质量**: 90%+测试覆盖率、95%文档覆盖率、统一异常处理
- ⚡ **高性能**: 向量化计算35倍加速、GPU训练15-20倍提速
- 🧪 **完整测试**: 3,200+测试用例（单元+集成+性能测试）
- 🔧 **易于扩展**: 统一API、Response格式、30+自定义异常类
- 📦 **开箱即用**: Docker一键部署、CLI工具、6种配置模板

---

## 快速开始

### 安装

```bash
# 1. 克隆项目
git clone https://github.com/your-org/stock-analysis.git
cd stock-analysis/core

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置初始化
stock-cli init
```

### Hello World (30秒上手)

```python
from src.providers import DataProviderFactory
from src.features import AlphaFactors, TechnicalIndicators
from src.strategies import MomentumStrategy
from src.backtest import BacktestEngine

# 1. 获取数据
provider = DataProviderFactory.create_provider('akshare')
prices = provider.get_daily_data('000001.SZ', '2024-01-01', '2024-12-31')

# 2. 计算特征
alpha = AlphaFactors(prices)
features = alpha.calculate_all_alpha_factors()  # 125+因子

tech = TechnicalIndicators(prices)
tech.add_all_indicators()  # 60+技术指标

# 3. 生成信号
strategy = MomentumStrategy('MOM20', {'lookback_period': 20})
signals = strategy.generate_signals(prices, features)

# 4. 回测验证
engine = BacktestEngine(initial_capital=1_000_000)
results = engine.backtest_long_only(signals, prices)

# 5. 查看结果
print(f"年化收益率: {results.annualized_return:.2%}")
print(f"夏普比率: {results.sharpe_ratio:.2f}")
print(f"最大回撤: {results.max_drawdown:.2%}")
```

### CLI工具快速上手

```bash
# 下载数据
stock-cli download --stock 000001.SZ --start 2024-01-01

# 计算特征
stock-cli features --stock 000001.SZ --output features.parquet

# 训练模型
stock-cli train --data features.parquet --target return_5d --model lightgbm

# 运行回测
stock-cli backtest --strategy momentum --stock 000001.SZ

# 生成可视化
stock-cli visualize --type backtest --input results.csv
```

---

## 核心特性

### 1. 数据管理

- **多数据源**: AkShare（免费推荐）、Tushare Pro
- **时序数据库**: TimescaleDB自动分区，10-100倍查询加速
- **数据质量**: 6种验证器 + 7种缺失值处理 + 4种异常检测
- **高可用**: 智能重试、断路器、断点续传、自动降级

### 2. 特征工程

- **125+ Alpha因子**: 动量、反转、波动率、成交量、量价关系
- **60+ 技术指标**: 趋势、动量、波动率、成交量指标
- **性能优化**: 35倍向量化加速、LRU缓存、Copy-on-Write
- **灵活存储**: CSV/Parquet/HDF5多后端

### 3. 机器学习

- **3种核心模型**: LightGBM（推荐）、GRU深度学习、Ridge基线
- **GPU加速**: 训练速度提升15-20倍
- **模型集成**: 加权平均、投票法、Stacking
- **完整评估**: 20+指标（收益、风险、IC、准确性）

### 4. 交易策略

- **5种经典策略**: 动量、均值回归、多因子、机器学习、组合
- **统一框架**: 所有策略继承BaseStrategy，易于扩展
- **信号融合**: 阈值、排名、趋势、组合信号

### 5. 回测引擎

- **并行回测**: 多策略同时回测，3-8倍性能提升
- **向量化**: 1000只股票×250天仅需2秒
- **真实成本**: 佣金、印花税、4种滑点模型
- **A股规则**: T+1、涨跌停、交易时间完整支持

### 6. 风险管理

- **风险指标**: VaR、CVaR、最大回撤、压力测试
- **仓位管理**: 固定比例、风险平价、凯利公式、动态调整
- **实时监控**: 自动风控检查、超限告警

---

## 完整文档

### 用户指南

- 📖 [架构分析](ARCHITECTURE_ANALYSIS.md) - 系统架构深度解析
- 🗺️ [开发路线图](DEVELOPMENT_ROADMAP.md) - 版本历史与未来规划
- 🔧 [重构计划](REFACTORING_PLAN.md) - 代码质量提升计划

### 专题文档

- 🎨 [可视化指南](docs/VISUALIZATION_GUIDE.md) - 30+图表使用说明
- 🧬 [特征配置指南](docs/FEATURE_CONFIG_GUIDE.md) - 因子计算配置
- 🤖 [模型使用指南](docs/MODEL_USAGE_GUIDE.md) - 模型训练与评估
- 📋 [配置模板指南](docs/TEMPLATES_GUIDE.md) - 6种配置模板说明

### API参考

- 📘 [数据层API](src/data/) - 数据获取、存储、质量检查
- 🧪 [特征层API](src/features/) - 因子计算、技术指标
- 🧠 [模型层API](src/models/) - 模型训练、评估、集成
- 📊 [策略层API](src/strategies/) - 策略开发、信号生成
- 🔙 [回测层API](src/backtest/) - 回测引擎、性能分析

---

## 使用示例

### 完整交易工作流

```python
from src.api.feature_api import calculate_alpha_factors
from src.models.model_trainer import ModelTrainer, TrainingConfig
from src.strategies import MLStrategy
from src.backtest import BacktestEngine

# 1. 计算特征（使用统一API）
response = calculate_alpha_factors(
    data=prices_df,
    factor_groups=['momentum', 'reversal', 'volatility']
)
if response.is_success():
    features = response.data
    print(f"计算了 {response.metadata['n_features']} 个因子")

# 2. 训练模型（统一Response格式）
config = TrainingConfig(model_type='lightgbm')
trainer = ModelTrainer(config)

# 准备数据
prep_response = trainer.prepare_data(
    df=features,
    feature_cols=feature_names,
    target_col='return_5d'
)

# 训练
train_response = trainer.train(
    X_train=prep_response.data['X_train'],
    y_train=prep_response.data['y_train'],
    X_valid=prep_response.data['X_valid'],
    y_valid=prep_response.data['y_valid']
)

# 评估
eval_response = trainer.evaluate(
    X=prep_response.data['X_test'],
    y=prep_response.data['y_test']
)
print(f"测试集 R²: {eval_response.data['r2']:.4f}")

# 3. 策略回测
strategy = MLStrategy('ML策略', {'model': train_response.data['model']})
signals = strategy.generate_signals(prices, features)

engine = BacktestEngine(initial_capital=1_000_000)
results = engine.backtest_long_only(signals, prices)
```

### 因子分析示例

```python
from src.analysis import ICCalculator, FactorAnalyzer, LayeringTest

# IC分析
ic_calc = ICCalculator()
ic_results = ic_calc.calculate_ic(factors, returns)
print(f"平均IC: {ic_results['mean_ic']:.4f}")

# 分层回测
layering = LayeringTest(n_quantiles=10)
layer_results = layering.run(factors['MOM_20'], prices)
layering.plot_results()  # 生成分层收益图

# 因子优化
analyzer = FactorAnalyzer()
best_factors = analyzer.select_best_factors(
    factors, returns,
    method='forward',  # 前向逐步选择
    max_factors=20
)
```

### 并行回测示例

```python
from src.backtest import ParallelBacktester

# 创建多个策略
strategies = [
    MomentumStrategy('MOM-20', {'lookback': 20}),
    MomentumStrategy('MOM-10', {'lookback': 10}),
    MeanReversionStrategy('MR-15', {'lookback': 15})
]

# 并行回测（3-8倍加速）
backtester = ParallelBacktester(n_workers=4)
results = backtester.run(strategies, prices_df)

# 生成对比报告
report = backtester.generate_comparison_report(results)
print(report)
```

---

## 性能基准

### 特征计算性能

| 场景 | 数据规模 | 耗时 | 性能 |
|------|---------|------|------|
| Alpha因子 | 1000股×250天 | ~1秒 | 35倍加速 |
| 技术指标 | 1000股×250天 | ~0.5秒 | 向量化 |
| IC计算 | 500股×1000天 | ~3秒 | 11倍加速 |

### 回测性能

| 场景 | 数据规模 | 耗时 |
|------|---------|------|
| 单策略回测 | 1000股×250天 | ~2秒 |
| 并行回测（4策略） | 1000股×250天 | ~3秒 |
| 市场中性回测 | 500股×250天 | ~5秒 |

### 模型训练性能

| 模型 | 样本数 | CPU耗时 | GPU耗时 | 加速比 |
|------|--------|---------|---------|--------|
| LightGBM | 100万 | ~10秒 | ~1秒 | 10x |
| GRU | 50万 | ~60秒 | ~3秒 | 20x |

---

## 测试

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行单元测试
pytest tests/unit/ -v

# 运行集成测试
pytest tests/integration/ -v

# 运行性能测试
cd tests/performance && python run_benchmarks.py

# 测试覆盖率
pytest tests/ --cov=src --cov-report=html
```

### 测试统计

- **单元测试**: 3,200+个
- **集成测试**: 24个端到端测试
- **性能测试**: 31个基准测试
- **测试覆盖率**: 90%+

---

## 贡献指南

我们欢迎所有形式的贡献！

### 如何贡献

1. Fork项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开Pull Request

### 代码规范

- 遵循PEP 8规范
- 使用类型提示（Type Hints）
- 编写完整的文档字符串（Google Style）
- 添加单元测试
- 测试覆盖率≥90%

---

## 技术栈

| 类别 | 技术 |
|------|------|
| **语言** | Python 3.9+ |
| **数据处理** | Pandas 2.0+, NumPy 1.24+ |
| **机器学习** | LightGBM 4.0+, PyTorch 2.0+, Scikit-learn |
| **数据库** | TimescaleDB (PostgreSQL 14+) |
| **技术分析** | TA-Lib 0.4+ |
| **配置管理** | Pydantic 2.0+ |
| **日志系统** | Loguru |
| **测试框架** | Pytest 7.4+ |
| **CLI工具** | Click, Rich |

---

## License

本项目采用 MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 支持

- 📧 **问题反馈**: [GitHub Issues](https://github.com/your-org/stock-analysis/issues)
- 💬 **讨论区**: [GitHub Discussions](https://github.com/your-org/stock-analysis/discussions)
- 📚 **文档**: [完整文档](https://stock-analysis.readthedocs.io/)

---

## 致谢

感谢所有贡献者对本项目的支持！

特别感谢以下开源项目：
- [AkShare](https://github.com/akfamily/akshare) - 免费开源的金融数据接口库
- [LightGBM](https://github.com/microsoft/LightGBM) - 高性能梯度提升框架
- [Pandas](https://github.com/pandas-dev/pandas) - 强大的数据分析工具

---

<div align="center">

**Made with ❤️ by Quant Team**

⭐ 如果这个项目对你有帮助，请给我们一个Star！

</div>
