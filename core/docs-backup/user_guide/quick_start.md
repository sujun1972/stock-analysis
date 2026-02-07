# 快速开始

**Quick Start Guide for Stock-Analysis Core**

**版本**: v3.0.0
**最后更新**: 2026-02-01

---

## 🎯 学习目标

通过本指南，你将在 **30分钟内** 掌握：

- ✅ 获取A股数据
- ✅ 计算Alpha因子和技术指标
- ✅ 训练机器学习模型
- ✅ 运行策略回测
- ✅ 生成可视化报告

---

## ⚡ 5分钟快速体验

### Hello World

```python
from src.providers import DataProviderFactory
from src.features import AlphaFactors
from src.strategies import MomentumStrategy
from src.backtest import BacktestEngine

# 1. 获取数据（平安银行，2024年）
provider = DataProviderFactory.create_provider('akshare')
data = provider.get_daily_data('000001.SZ', '2024-01-01', '2024-12-31')

# 2. 计算特征
alpha = AlphaFactors(data)
features = alpha.calculate_all_alpha_factors()

# 3. 生成信号
strategy = MomentumStrategy('MOM20', {'lookback_period': 20})
signals = strategy.generate_signals(data, features)

# 4. 回测
engine = BacktestEngine(initial_capital=1_000_000)
results = engine.backtest_long_only(signals, data)

# 5. 查看结果
print(f"年化收益率: {results.annualized_return:.2%}")
print(f"夏普比率: {results.sharpe_ratio:.2f}")
print(f"最大回撤: {results.max_drawdown:.2%}")
```

**输出示例**:
```
年化收益率: 18.5%
夏普比率: 1.82
最大回撤: -12.3%
```

---

## 📖 完整教程

### 步骤1: 数据获取

#### 使用AkShare获取数据（免费）

```python
from src.providers import DataProviderFactory

# 创建数据提供者
provider = DataProviderFactory.create_provider('akshare')

# 获取单只股票日线数据
data = provider.get_daily_data(
    stock_code='000001.SZ',  # 平安银行
    start_date='2023-01-01',
    end_date='2023-12-31'
)

# 查看数据
print(data.head())
```

**输出**:
```
   stock_code trade_date   open   high    low  close      volume
0  000001.SZ 2023-01-03  10.20  10.35  10.15  10.28  120000000
1  000001.SZ 2023-01-04  10.30  10.45  10.25  10.42  135000000
...
```

#### 获取多只股票

```python
# 批量获取
stock_codes = ['000001.SZ', '600000.SH', '601318.SH']
data_dict = provider.get_multiple_stocks(
    stock_codes=stock_codes,
    start_date='2023-01-01',
    end_date='2023-12-31'
)

# 遍历结果
for code, df in data_dict.items():
    print(f"{code}: {len(df)} 条数据")
```

#### 保存到数据库

```python
from src.data.database_manager import DatabaseManager

# 创建数据库管理器
db = DatabaseManager()

# 保存数据
db.insert_stock_data(data)

# 查询数据
query_result = db.query_stock_data(
    stock_code='000001.SZ',
    start_date='2023-01-01',
    end_date='2023-12-31'
)
```

---

### 步骤2: 特征计算

#### 计算Alpha因子

```python
from src.features import AlphaFactors

# 创建Alpha因子计算器
alpha = AlphaFactors(data)

# 计算动量因子
momentum = alpha.calculate_momentum_factors()
print(f"动量因子数量: {len(momentum.columns)}")  # 8个因子

# 计算反转因子
reversal = alpha.calculate_reversal_factors()
print(f"反转因子数量: {len(reversal.columns)}")  # 6个因子

# 计算波动率因子
volatility = alpha.calculate_volatility_factors()
print(f"波动率因子数量: {len(volatility.columns)}")  # 12个因子

# 计算所有Alpha因子（125+个）
all_factors = alpha.calculate_all_alpha_factors()
print(f"总Alpha因子数量: {len(all_factors.columns)}")
```

#### 计算技术指标

```python
from src.features import TechnicalIndicators

# 创建技术指标计算器
tech = TechnicalIndicators(data)

# 添加常用技术指标
tech.add_ma(periods=[5, 10, 20, 60])  # 移动平均线
tech.add_ema(periods=[12, 26])        # 指数移动平均
tech.add_macd()                        # MACD
tech.add_rsi(period=14)                # RSI
tech.add_bollinger_bands()             # 布林带
tech.add_atr(period=14)                # ATR

# 获取结果
data_with_indicators = tech.get_data()
print(f"技术指标数量: {len(data_with_indicators.columns) - len(data.columns)}")
```

#### 使用统一API

```python
from src.api.feature_api import calculate_alpha_factors

# 使用统一API计算特征（推荐）
response = calculate_alpha_factors(
    data=data,
    factor_groups=['momentum', 'reversal', 'volatility', 'volume']
)

if response.is_success():
    features = response.data
    metadata = response.metadata

    print(f"✅ 成功计算 {metadata['n_features']} 个因子")
    print(f"   耗时: {metadata['elapsed_time']:.2f}秒")
else:
    print(f"❌ 计算失败: {response.message}")
```

---

### 步骤3: 模型训练

#### 准备训练数据

```python
from src.models.model_trainer import ModelTrainer, TrainingConfig
import pandas as pd

# 准备特征和目标
X = features  # 特征矩阵
y = data['close'].pct_change(5).shift(-5)  # 未来5日收益率

# 删除NaN
valid_idx = ~(X.isna().any(axis=1) | y.isna())
X = X[valid_idx]
y = y[valid_idx]

print(f"训练样本数: {len(X)}")
```

#### 训练LightGBM模型（推荐）

```python
# 创建训练配置
config = TrainingConfig(
    model_type='lightgbm',
    hyperparameters={
        'n_estimators': 100,
        'learning_rate': 0.05,
        'max_depth': 5,
        'num_leaves': 31
    }
)

# 创建训练器
trainer = ModelTrainer(config)

# 准备数据（自动划分训练/验证/测试集）
prep_response = trainer.prepare_data(
    df=pd.concat([X, y.rename('target')], axis=1),
    feature_cols=X.columns.tolist(),
    target_col='target',
    test_size=0.2,
    valid_size=0.1
)

# 训练
train_response = trainer.train(
    X_train=prep_response.data['X_train'],
    y_train=prep_response.data['y_train'],
    X_valid=prep_response.data['X_valid'],
    y_valid=prep_response.data['y_valid']
)

if train_response.is_success():
    print(f"✅ 训练完成")
    print(f"   训练集 R²: {train_response.metadata['train_r2']:.4f}")
    print(f"   验证集 R²: {train_response.metadata['valid_r2']:.4f}")
```

#### 模型评估

```python
# 在测试集上评估
eval_response = trainer.evaluate(
    X=prep_response.data['X_test'],
    y=prep_response.data['y_test']
)

if eval_response.is_success():
    metrics = eval_response.data
    print(f"\n测试集评估:")
    print(f"  R²: {metrics['r2']:.4f}")
    print(f"  MSE: {metrics['mse']:.6f}")
    print(f"  MAE: {metrics['mae']:.6f}")
    print(f"  IC: {metrics['ic']:.4f}")
```

#### 保存和加载模型

```python
# 保存模型
save_response = trainer.save_model('models/lightgbm_v1.pkl')
print(f"✅ 模型已保存: {save_response.data['path']}")

# 加载模型
load_response = trainer.load_model('models/lightgbm_v1.pkl')
if load_response.is_success():
    print("✅ 模型加载成功")
```

---

### 步骤4: 策略回测

#### 使用内置策略

```python
from src.strategies import MomentumStrategy, MeanReversionStrategy
from src.backtest import BacktestEngine

# 创建动量策略
momentum_strategy = MomentumStrategy(
    name='动量策略20日',
    params={
        'lookback_period': 20,
        'entry_threshold': 0.02,  # 涨幅>2%买入
        'exit_threshold': -0.01   # 跌幅>1%卖出
    }
)

# 生成交易信号
signals = momentum_strategy.generate_signals(data, features)

# 创建回测引擎
engine = BacktestEngine(
    initial_capital=1_000_000,  # 初始资金100万
    commission_rate=0.0003,      # 佣金万3
    slippage_rate=0.001          # 滑点0.1%
)

# 运行回测
results = engine.backtest_long_only(signals, data)

# 查看结果
print("\n回测结果:")
print(f"总收益率: {results.total_return:.2%}")
print(f"年化收益率: {results.annualized_return:.2%}")
print(f"夏普比率: {results.sharpe_ratio:.2f}")
print(f"最大回撤: {results.max_drawdown:.2%}")
print(f"胜率: {results.win_rate:.2%}")
print(f"总交易次数: {results.n_trades}")
```

#### 使用机器学习策略

```python
from src.strategies import MLStrategy

# 创建ML策略
ml_strategy = MLStrategy(
    name='LightGBM预测策略',
    params={
        'model': train_response.data['model'],
        'threshold': 0.01  # 预测收益率>1%则买入
    }
)

# 生成信号
ml_signals = ml_strategy.generate_signals(data, features)

# 回测
ml_results = engine.backtest_long_only(ml_signals, data)

print("\nML策略回测结果:")
print(f"年化收益率: {ml_results.annualized_return:.2%}")
print(f"夏普比率: {ml_results.sharpe_ratio:.2f}")
```

#### 多策略对比

```python
from src.backtest import ParallelBacktester

# 创建多个策略
strategies = [
    MomentumStrategy('MOM-10', {'lookback_period': 10}),
    MomentumStrategy('MOM-20', {'lookback_period': 20}),
    MeanReversionStrategy('MR-15', {'lookback_period': 15})
]

# 并行回测
backtester = ParallelBacktester(n_workers=4)
all_results = backtester.run(strategies, data)

# 生成对比报告
report = backtester.generate_comparison_report(all_results)
print("\n策略对比:")
print(report)
```

---

### 步骤5: 可视化分析

#### 生成回测报告

```python
from src.visualization import BacktestVisualizer

# 创建可视化器
viz = BacktestVisualizer(results)

# 绘制净值曲线
viz.plot_equity_curve()

# 绘制回撤曲线
viz.plot_drawdown()

# 绘制月度收益热力图
viz.plot_monthly_returns()

# 生成完整报告（包含所有图表）
viz.generate_full_report(output_path='reports/backtest_report.html')
print("✅ 报告已生成: reports/backtest_report.html")
```

#### 因子分析可视化

```python
from src.visualization import FactorVisualizer
from src.analysis import ICCalculator

# 计算IC
ic_calc = ICCalculator()
ic_results = ic_calc.calculate_ic(features, y)

# 可视化
viz = FactorVisualizer()

# IC柱状图
viz.plot_ic_bar(ic_results)

# IC时间序列
viz.plot_ic_timeseries(ic_results)

# 因子分层收益
viz.plot_quantile_returns(features['MOM_20'], data['close'])
```

---

## 🚀 使用CLI工具

### 完整工作流（命令行）

```bash
# 1. 下载数据
stock-cli download \
  --stock 000001.SZ \
  --start 2023-01-01 \
  --end 2023-12-31 \
  --output data/000001.csv

# 2. 计算特征
stock-cli features \
  --input data/000001.csv \
  --groups momentum,reversal,volatility \
  --output data/features.parquet

# 3. 训练模型
stock-cli train \
  --data data/features.parquet \
  --target return_5d \
  --model lightgbm \
  --output models/lightgbm_v1.pkl

# 4. 运行回测
stock-cli backtest \
  --strategy ml \
  --model models/lightgbm_v1.pkl \
  --data data/000001.csv \
  --output results/backtest.csv

# 5. 生成报告
stock-cli report \
  --input results/backtest.csv \
  --output reports/report.html
```

### 查看帮助

```bash
# 查看所有命令
stock-cli --help

# 查看特定命令帮助
stock-cli download --help
stock-cli train --help
stock-cli backtest --help
```

---

## 📊 实战示例

### 示例1: 多因子选股策略

```python
from src.strategies import MultiFactorStrategy
from src.backtest import BacktestEngine

# 1. 计算多个因子
factors_dict = {
    'momentum_20': alpha.calculate_momentum(window=20),
    'reversal_5': alpha.calculate_reversal(window=5),
    'volatility_20': alpha.calculate_volatility(window=20),
    'volume_ratio': alpha.calculate_volume_ratio(window=20)
}

# 2. 创建多因子策略
strategy = MultiFactorStrategy(
    name='多因子选股',
    params={
        'factors': factors_dict,
        'weights': [0.3, 0.2, 0.3, 0.2],  # 因子权重
        'top_n': 10  # 选择前10只股票
    }
)

# 3. 回测
signals = strategy.generate_signals(data, factors_dict)
results = engine.backtest_long_only(signals, data)

print(f"多因子策略年化收益: {results.annualized_return:.2%}")
```

### 示例2: 模型集成策略

```python
from src.models import ModelEnsemble
from src.strategies import MLStrategy

# 1. 训练多个模型
models = []
for model_type in ['lightgbm', 'ridge', 'gru']:
    config = TrainingConfig(model_type=model_type)
    trainer = ModelTrainer(config)
    # ... 训练模型
    models.append(trainer.model)

# 2. 创建模型集成
ensemble = ModelEnsemble(
    models=models,
    method='weighted_average',
    weights=[0.5, 0.3, 0.2]
)

# 3. 使用集成模型的策略
ensemble_strategy = MLStrategy(
    name='集成模型策略',
    params={'model': ensemble}
)

# 4. 回测
signals = ensemble_strategy.generate_signals(data, features)
results = engine.backtest_long_only(signals, data)
```

### 示例3: 风险管理

```python
from src.risk import RiskManager, PositionSizer

# 创建风险管理器
risk_manager = RiskManager(
    max_position_size=0.1,      # 单仓位最大10%
    max_total_risk=0.2,         # 总风险敞口20%
    stop_loss=-0.05,            # 止损-5%
    take_profit=0.15            # 止盈+15%
)

# 创建仓位管理器
position_sizer = PositionSizer(
    method='kelly',             # 凯利公式
    max_position=0.1,
    min_position=0.01
)

# 在回测中应用风险管理
engine_with_risk = BacktestEngine(
    initial_capital=1_000_000,
    risk_manager=risk_manager,
    position_sizer=position_sizer
)

results = engine_with_risk.backtest_long_only(signals, data)
```

---

## 🎓 学习路径

### 初级（第1-2周）

1. ✅ 完成本快速开始指南
2. 📖 阅读 [CLI命令指南](CLI_GUIDE.md)
3. 🎨 学习 [可视化指南](VISUALIZATION_GUIDE.md)
4. 📊 练习数据获取和基础分析

### 中级（第3-4周）

1. 🧬 深入学习 [特征配置指南](FEATURE_CONFIG_GUIDE.md)
2. 🤖 掌握 [模型使用指南](MODEL_USAGE_GUIDE.md)
3. 📈 研究 [因子分析指南](FACTOR_ANALYSIS_GUIDE.md)
4. 🔙 精通 [回测使用指南](BACKTEST_USAGE_GUIDE.md)

### 高级（第5-8周）

1. 📊 学习 [数据质量指南](DATA_QUALITY_GUIDE.md)
2. 🤝 掌握 [模型集成指南](ENSEMBLE_GUIDE.md)
3. 🏗️ 理解 [架构设计](../architecture/overview.md)
4. 🎨 学习 [设计模式](../architecture/design_patterns.md)

---

## 💡 最佳实践

### 数据处理

```python
# ✅ 好的实践
from src.data.data_validator import DataValidator

# 验证数据质量
validator = DataValidator()
is_valid, errors = validator.validate(data)

if not is_valid:
    print(f"数据质量问题: {errors}")
    # 清洗数据
    data = validator.clean(data)

# ❌ 避免
# 直接使用未验证的数据进行计算
```

### 特征计算

```python
# ✅ 好的实践
# 使用统一API，自动处理异常
response = calculate_alpha_factors(data, factor_groups=['momentum'])
if response.is_success():
    features = response.data
else:
    logger.error(f"特征计算失败: {response.message}")

# ❌ 避免
# 直接调用底层函数，不处理异常
features = AlphaFactors(data).calculate_momentum_factors()  # 可能抛出异常
```

### 模型训练

```python
# ✅ 好的实践
# 使用配置文件
config = TrainingConfig.from_yaml('configs/lightgbm_config.yaml')
trainer = ModelTrainer(config)

# 记录实验
trainer.enable_mlflow_tracking()

# 交叉验证
cv_results = trainer.cross_validate(X, y, cv=5)

# ❌ 避免
# 硬编码参数，无法复现
model = LightGBM(n_estimators=100, learning_rate=0.05)  # 参数散落各处
```

---

## ❓ 常见问题

### Q1: 如何获取更多股票数据？

```python
# 获取沪深300成分股
from src.utils.stock_utils import get_index_components

hs300 = get_index_components('000300.SH')  # 沪深300
print(f"沪深300成分股数量: {len(hs300)}")

# 批量下载
for code in hs300:
    data = provider.get_daily_data(code, '2023-01-01', '2023-12-31')
    db.insert_stock_data(data)
```

### Q2: 如何处理缺失数据？

```python
from src.data.data_cleaner import DataCleaner

cleaner = DataCleaner()

# 前向填充
data_filled = cleaner.forward_fill(data)

# 线性插值
data_interpolated = cleaner.interpolate(data, method='linear')

# 删除缺失值
data_dropped = cleaner.drop_missing(data, threshold=0.1)
```

### Q3: 如何加速特征计算？

```python
# 方法1: 使用并行计算
from src.features import AlphaFactors

alpha = AlphaFactors(data, n_jobs=4)  # 使用4个CPU核心
features = alpha.calculate_all_alpha_factors()

# 方法2: 使用缓存
from functools import lru_cache

@lru_cache(maxsize=128)
def cached_features(stock_code, start_date):
    return calculate_features(stock_code, start_date)
```

### Q4: 如何评估策略的稳定性？

```python
from src.analysis import RollingBacktest

# 滚动回测
roller = RollingBacktest(
    window_size=252,  # 1年窗口
    step_size=63      # 每季度滚动
)

rolling_results = roller.run(strategy, data)

# 绘制滚动收益率
roller.plot_rolling_returns(rolling_results)
```

---

## 📚 更多资源

### 示例代码

完整示例代码位于：
- [examples/](examples/) - 17个完整工作流示例
- `scripts/` - 实用脚本
- `notebooks/` - Jupyter教程

### 文档导航

- 📖 [完整文档](../README.md)
- 🏗️ [系统架构](../architecture/overview.md)
- 🗺️ [开发路线图](../ROADMAP.md)

### 获取帮助

- 📧 [GitHub Issues](https://github.com/your-org/stock-analysis/issues)
- 💬 [Discussions](https://github.com/your-org/stock-analysis/discussions)
- 📚 [API文档](https://stock-analysis.readthedocs.io/)

---

## 🎉 下一步

恭喜！你已经掌握了Stock-Analysis Core的基础使用。

建议接下来：

1. 🔧 熟练掌握 [CLI工具](CLI_GUIDE.md)
2. 📊 深入学习 [数据质量管理](DATA_QUALITY_GUIDE.md)
3. 🧬 探索更多 [Alpha因子](FACTOR_ANALYSIS_GUIDE.md)
4. 🤖 优化 [模型性能](MODEL_USAGE_GUIDE.md)
5. 💼 开发自己的交易策略

---

**文档版本**: v3.0.0
**维护团队**: Quant Team
**最后更新**: 2026-02-01
