# Core 核心代码模块

## 📋 项目概述

**Core** 是A股AI量化交易系统的核心业务逻辑库，提供从数据获取、特征工程、模型训练到回测评估的完整量化交易工具链。

**项目规模**：
- 99个Python模块，约23,774行代码
- 覆盖数据、特征、模型、回测、配置等核心功能
- 完整的单元测试和集成测试体系

---

## 🚀 快速开始

### 安装 Core 模块

```bash
# 进入 core 目录
cd core

# 以开发模式安装（推荐）
pip install -e .

# 或在虚拟环境中安装
python -m venv ../stock_env
source ../stock_env/bin/activate  # Linux/Mac
# 或 ../stock_env/Scripts/activate  # Windows
pip install -e .
```

安装后可以直接导入：
```python
from data_pipeline import DataPipeline
from database.db_manager import DatabaseManager
from models.lightgbm_model import LightGBMStockModel
from backtest.backtest_engine import BacktestEngine
```

---

## 📁 目录结构

```
core/
├── src/                           # 核心业务逻辑代码
│   ├── providers/                 # 数据源提供者
│   │   ├── akshare/              # AkShare数据源（免费，主力）
│   │   ├── tushare/              # Tushare数据源（需Token）
│   │   ├── base_provider.py      # 数据源接口定义
│   │   ├── provider_factory.py   # 数据源工厂
│   │   └── provider_registry.py  # 数据源注册管理
│   │
│   ├── database/                  # 数据库管理模块
│   │   ├── db_manager.py         # 数据库管理器（单例模式）
│   │   ├── connection_pool_manager.py  # 连接池管理
│   │   ├── table_manager.py      # 表结构管理
│   │   ├── data_insert_manager.py # 数据插入管理
│   │   └── data_query_manager.py # 数据查询管理
│   │
│   ├── data/                      # 数据处理模块
│   │   ├── data_cleaner.py       # 数据清洗
│   │   └── stock_filter.py       # 股票筛选
│   │
│   ├── data_pipeline/             # 数据管道模块
│   │   ├── data_loader.py        # 单股票数据加载
│   │   ├── pooled_data_loader.py # 多股票池化加载
│   │   ├── data_splitter.py      # 数据集划分
│   │   ├── feature_engineer.py   # 特征工程
│   │   ├── feature_cache.py      # 特征缓存
│   │   └── pooled_training_pipeline.py  # 池化训练流程
│   │
│   ├── features/                  # 特征工程模块
│   │   ├── technical_indicators.py      # 技术指标（RSI/MACD等）
│   │   ├── indicators_calculator.py     # 指标计算器
│   │   ├── indicators/                  # 指标子模块
│   │   │   ├── base.py                  # 基础指标
│   │   │   ├── trend.py                 # 趋势指标
│   │   │   ├── momentum.py              # 动量指标
│   │   │   ├── volatility.py            # 波动率指标
│   │   │   ├── volume.py                # 成交量指标
│   │   │   └── price_pattern.py         # 价格形态
│   │   │
│   │   ├── alpha_factors.py       # Alpha因子库（125+因子）
│   │   │   # 包含：动量、反转、波动率、成交量、
│   │   │   #      量价关系、技术形态等因子
│   │   │
│   │   ├── feature_transformer.py # 特征转换器
│   │   ├── feature_strategy.py    # 特征策略
│   │   └── storage/               # 特征存储
│   │       ├── base_storage.py    # 存储接口
│   │       ├── csv_storage.py     # CSV存储
│   │       ├── parquet_storage.py # Parquet存储
│   │       └── hdf5_storage.py    # HDF5存储
│   │
│   ├── models/                    # AI模型模块
│   │   ├── lightgbm_model.py     # LightGBM模型（基线）
│   │   ├── gru_model.py          # GRU深度学习模型
│   │   ├── ridge_model.py        # Ridge回归模型
│   │   ├── model_trainer.py      # 模型训练器
│   │   ├── model_evaluator.py    # 模型评估器
│   │   ├── comparison_evaluator.py # 模型对比评估
│   │   └── evaluation/           # 评估子模块
│   │       ├── evaluator.py      # 核心评估器
│   │       ├── metrics/          # 评估指标
│   │       │   ├── calculator.py # 指标计算器
│   │       │   ├── returns.py    # 收益指标
│   │       │   ├── risk.py       # 风险指标
│   │       │   └── correlation.py # 相关性指标
│   │       ├── formatter.py      # 报告格式化
│   │       └── convenience.py    # 便捷函数
│   │
│   ├── backtest/                  # 回测引擎模块
│   │   ├── backtest_engine.py    # 向量化回测引擎
│   │   ├── position_manager.py   # 仓位管理器
│   │   └── performance_analyzer.py # 绩效分析器
│   │
│   ├── config/                    # 配置模块
│   │   ├── settings.py           # 统一配置（Pydantic）
│   │   ├── trading_rules.py      # 交易规则配置
│   │   ├── features.py           # 特征配置
│   │   ├── providers.py          # 数据源配置
│   │   └── pipeline.py           # 管道配置
│   │
│   └── utils/                     # 工具模块
│       ├── logger.py             # 日志工具（Loguru）
│       ├── decorators.py         # 装饰器
│       ├── type_utils.py         # 类型工具
│       └── market_utils.py       # 市场工具
│
├── tests/                         # 测试套件
│   ├── run_tests.py              # 统一测试运行器
│   ├── unit/                     # 单元测试（36个测试模块）
│   │   ├── providers/            # 数据源测试
│   │   ├── features/             # 特征测试
│   │   ├── models/               # 模型测试
│   │   ├── backtest/             # 回测测试
│   │   └── config/               # 配置测试
│   ├── integration/              # 集成测试
│   └── reports/                  # 测试报告输出
│
├── data/                          # 数据存储目录
├── logs/                          # 日志输出目录
├── docs/                          # 文档目录
├── setup.py                       # 安装配置
├── pyproject.toml                # 项目配置
└── README.md                      # 本文档
```

---

## 🎯 核心功能详解

### 1. 数据获取与存储 (`providers/` + `database/`)

#### 1.1 多数据源支持

**AkShare数据源**（免费，主力）：
```python
from providers.akshare import AkShareProvider

provider = AkShareProvider()
# 获取历史K线数据
data = provider.get_stock_hist(
    symbol='000001',
    start_date='20240101',
    end_date='20241231'
)
```

**Tushare数据源**（需Token）：
```python
from providers.tushare import TushareProvider

provider = TushareProvider(token='your_token')
data = provider.get_daily_data('000001.SZ', '20240101', '20241231')
```

**数据源特性**：
- 统一的接口设计（`BaseDataProvider`）
- 工厂模式切换数据源
- 自动重试机制
- 请求限流保护

#### 1.2 TimescaleDB存储

```python
from database.db_manager import DatabaseManager

db = DatabaseManager.get_instance()

# 插入数据
db.insert_data('stock_daily', df, conflict_action='update')

# 查询数据
data = db.query_stock_data(
    symbol='000001',
    start_date='2024-01-01',
    end_date='2024-12-31'
)
```

**数据库特性**：
- 单例模式连接池管理
- 自动创建超表（TimescaleDB）
- 批量插入优化
- 事务支持
- 连接池监控

---

### 2. 特征工程 (`features/`)

#### 2.1 技术指标计算（60+指标）

**趋势指标**：
- SMA、EMA、WMA（移动平均）
- MACD（指数平滑异同移动平均线）
- ADX（平均趋向指标）
- CCI（顺势指标）

**动量指标**：
- RSI（相对强弱指数）
- KDJ（随机指标）
- ROC（变动率）
- Williams %R

**波动率指标**：
- Bollinger Bands（布林带）
- ATR（真实波幅）
- Keltner Channels
- Historical Volatility

**成交量指标**：
- OBV（能量潮）
- Volume Ratio
- VWAP（成交量加权平均价）
- Money Flow

**使用示例**：
```python
from features.technical_indicators import TechnicalIndicators

ti = TechnicalIndicators(df)
df = ti.add_all_indicators()  # 添加所有指标

# 或单独添加
df = ti.add_moving_averages([5, 10, 20, 60])
df = ti.add_rsi(period=14)
df = ti.add_macd()
```

#### 2.2 Alpha因子库（125+因子）

**Alpha因子分类**：

1. **动量因子**（Momentum）：
   - 短期动量（5/10/20日）
   - 长期动量（60/120日）
   - 加速动量
   - 相对强度

2. **反转因子**（Reversal）：
   - 日内反转
   - 隔夜反转
   - 周反转
   - 均值回归

3. **波动率因子**（Volatility）：
   - 历史波动率
   - 已实现波动率
   - 下行波动率
   - 波动率偏度

4. **成交量因子**（Volume）：
   - 成交量变化率
   - 量价相关性
   - 成交额比率
   - 换手率

5. **量价关系因子**（Price-Volume）：
   - VWAP偏离度
   - 量价背离
   - 资金流向
   - 大单比例

6. **技术形态因子**（Technical Pattern）：
   - 突破因子
   - 支撑/阻力位
   - 形态识别
   - K线组合

**使用示例**：
```python
from features.alpha_factors import AlphaFactors

calculator = AlphaFactors()

# 计算所有因子
all_factors = calculator.calculate_all_factors(df)

# 计算特定类别
momentum_factors = calculator.calculate_momentum_factors(df)
reversal_factors = calculator.calculate_reversal_factors(df)
```

#### 2.3 特征缓存与存储

```python
from features.storage import ParquetStorage, HDF5Storage

# Parquet存储（推荐）
storage = ParquetStorage(base_path='/data/features')
storage.save_features('000001', features_df)
features = storage.load_features('000001')

# HDF5存储（大数据集）
storage = HDF5Storage(base_path='/data/features')
storage.save_features('000001', features_df, compression='gzip')
```

---

### 3. AI模型训练 (`models/`)

#### 3.1 LightGBM模型（主力模型）

```python
from models.lightgbm_model import LightGBMStockModel

model = LightGBMStockModel(
    objective='regression',
    num_leaves=15,
    learning_rate=0.05,
    n_estimators=500
)

# 训练
model.train(X_train, y_train, X_valid, y_valid)

# 预测
predictions = model.predict(X_test)

# 特征重要性
importance_df = model.get_feature_importance()
```

**模型特性**：
- 适用于表格数据
- 快速训练和预测
- 特征重要性分析
- 支持Early Stopping
- GPU加速支持

#### 3.2 GRU深度学习模型

```python
from models.gru_model import GRUStockModel

model = GRUStockModel(
    input_dim=125,
    hidden_dim=64,
    num_layers=2,
    output_dim=1,
    dropout=0.2
)

# 训练
model.train(X_train, y_train, epochs=100, batch_size=32)

# 预测
predictions = model.predict(X_test)
```

**适用场景**：
- 时间序列数据
- 长期依赖关系
- 序列到序列预测

#### 3.3 模型评估与对比

```python
from models.model_evaluator import ModelEvaluator
from models.comparison_evaluator import ComparisonEvaluator

# 单模型评估
evaluator = ModelEvaluator()
metrics = evaluator.evaluate(
    y_true=y_test,
    y_pred=predictions,
    prices=prices_test
)

# 多模型对比
comparator = ComparisonEvaluator()
comparison_report = comparator.compare_models(
    models={
        'LightGBM': lgb_model,
        'GRU': gru_model,
        'Ridge': ridge_model
    },
    X_test=X_test,
    y_test=y_test
)
```

**评估指标**：
- **收益指标**：年化收益率、累计收益、超额收益
- **风险指标**：最大回撤、夏普比率、索提诺比率、Calmar比率
- **相关性指标**：IC（信息系数）、RankIC、ICIR
- **准确性指标**：RMSE、MAE、R²

---

### 4. 回测引擎 (`backtest/`)

#### 4.1 向量化回测

```python
from backtest.backtest_engine import BacktestEngine

engine = BacktestEngine(
    initial_capital=1_000_000,
    commission_rate=0.0003,
    stamp_tax_rate=0.001,
    slippage=0.001
)

# 执行回测
result = engine.backtest_long_only(
    signals=signals_df,
    prices=prices_df,
    position_size=0.1  # 每次交易占总资金10%
)

# 获取回测指标
metrics = engine.get_performance_metrics()
```

**回测特性**：
- **A股交易规则**：T+1交易、涨跌停限制
- **真实交易成本**：佣金、印花税、滑点
- **仓位管理**：最大持仓、分批建仓
- **风险控制**：止损、止盈、最大回撤限制

#### 4.2 绩效分析

```python
from backtest.performance_analyzer import PerformanceAnalyzer

analyzer = PerformanceAnalyzer(portfolio_values, benchmark_values)

# 生成完整报告
report = analyzer.generate_full_report()

# 绘制净值曲线
analyzer.plot_equity_curve(save_path='equity_curve.png')

# 绘制回撤图
analyzer.plot_drawdown(save_path='drawdown.png')
```

**输出指标**：
- 总收益率、年化收益率
- 最大回撤、最长回撤期
- 夏普比率、卡尔马比率
- 胜率、盈亏比
- Alpha、Beta

---

### 5. 数据管道 (`data_pipeline/`)

#### 5.1 完整训练流程

```python
from data_pipeline.pooled_training_pipeline import PooledTrainingPipeline

pipeline = PooledTrainingPipeline(scaler_type='robust')

# 加载多股票数据
X_train, y_train, X_valid, y_valid, X_test, y_test = \
    pipeline.load_and_prepare_data(
        symbol_list=['000001', '000002', '600000'],
        start_date='20220101',
        end_date='20241231',
        target_period=10
    )

# 训练模型
lgb_model = pipeline.train_lightgbm(X_train, y_train, X_valid, y_valid)

# 评估模型
metrics = pipeline.evaluate_on_test_set(lgb_model, X_test, y_test)
```

#### 5.2 特征缓存加速

```python
from data_pipeline.feature_cache import FeatureCache

cache = FeatureCache(cache_dir='/data/pipeline_cache')

# 使用缓存
features = cache.get_or_compute(
    key='000001_20240101_20241231',
    compute_fn=lambda: compute_features('000001')
)
```

**性能优化**：
- LRU缓存机制
- 多线程安全
- 自动过期管理
- 命中率统计

---

### 6. 配置管理 (`config/`)

#### 6.1 统一配置（Pydantic）

```python
from config.settings import get_settings

settings = get_settings()

# 数据库配置
db_config = settings.database
print(db_config.host, db_config.port)

# 数据源配置
if settings.data_source.has_tushare:
    use_tushare = True

# 路径配置
models_path = settings.paths.get_models_path()
cache_path = settings.paths.get_cache_path()
```

**配置来源**：
1. 环境变量（优先级最高）
2. `.env`文件
3. 默认值

#### 6.2 交易规则配置

```python
from config.trading_rules import TradingCosts, PriceLimitRules

# 计算交易成本
buy_cost = TradingCosts.calculate_buy_cost(
    amount=10000,
    stock_code='600000'
)

# 检查涨跌停
is_limit_up = PriceLimitRules.is_limit_up(
    current_price=10.00,
    prev_close=9.09,
    stock_type='ST'
)
```

---

### 7. 测试体系 (`tests/`)

#### 7.1 运行测试

```bash
# 交互式菜单
python core/tests/run_tests.py

# 运行所有测试
python core/tests/run_tests.py --all

# 只运行单元测试
python core/tests/run_tests.py --unit

# 只运行集成测试
python core/tests/run_tests.py --integration

# 生成覆盖率报告
python core/tests/run_tests.py --coverage

# 快速测试（排除慢速测试）
python core/tests/run_tests.py --fast
```

#### 7.2 测试覆盖

**单元测试**（36个测试模块）：
- 数据源测试（AkShare、Tushare）
- 数据库管理测试
- 特征计算测试
- 模型训练测试
- 回测引擎测试
- 配置模块测试

**集成测试**：
- 端到端数据流测试
- 多模块协作测试
- 性能压力测试

---

## 🔄 与Backend的关系

```
core/src/  →  Docker挂载  →  /app/src (容器内)
                              ↓
                    backend/app/services/
                    (调用 from src.xxx)
```

**Backend不复制代码，而是通过Docker挂载访问core/src/**

Docker配置示例：
```yaml
services:
  backend:
    volumes:
      - ./core/src:/app/src  # 挂载核心代码
```

**优势**：
- ✅ 代码单一来源
- ✅ 本地和容器共享同一份代码
- ✅ 修改立即生效
- ✅ 避免重复和不一致

---

## 📝 开发指南

### 添加新功能模块

```python
# 在 core/src/mymodule/ 创建新模块
core/src/mymodule/
├── __init__.py
├── processor.py
└── utils.py

# Backend中使用
from src.mymodule.processor import MyProcessor
```

### 添加新的技术指标

```python
# 在 features/indicators/ 添加指标
from .base import BaseIndicator

class MyIndicator(BaseIndicator):
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        # 计算逻辑
        return df
```

### 添加新的Alpha因子

```python
# 在 features/alpha_factors.py 添加因子
class AlphaFactors:
    def calculate_my_factor(self, df: pd.DataFrame) -> pd.Series:
        """我的自定义因子"""
        return df['close'].rolling(20).mean() / df['close'] - 1
```

---

## 🚫 注意事项

1. **不要**在项目根目录创建`src/`目录
   - 核心代码在`core/src/`
   - 根目录的`src/`会被`.gitignore`忽略（Docker临时目录）

2. **不要**复制core/src到backend
   - 使用Docker挂载，不是复制

3. **保持**代码单一来源
   - 所有核心逻辑修改都在`core/src/`

4. **使用**统一日志系统
   - 导入：`from src.utils.logger import get_logger`
   - 不要使用`print()`

5. **遵循**类型提示规范
   - 所有函数添加类型提示
   - 使用`Optional[]`、`List[]`等

---

## 📊 性能优化建议

### 数据加载优化
- 使用Parquet格式存储特征（比CSV快10倍）
- 启用特征缓存（减少重复计算）
- 分批加载大数据集

### 特征计算优化
- 向量化计算（避免循环）
- 使用Numba加速关键函数
- 缓存中间结果

### 模型训练优化
- 池化训练（多股票数据共享）
- GPU加速（LightGBM、PyTorch）
- 早停策略（避免过拟合）

---

## 📚 相关文档

- [项目架构文档](../docs/ARCHITECTURE.md)
- [数据库使用指南](../docs/DATABASE_USAGE.md)
- [Backend README](../backend/README.md)
- [项目根目录 README](../README.md)

---

## 🛠️ 技术栈

**数据处理**：
- Pandas 2.0+ (数据处理)
- NumPy 1.24+ (数值计算)
- TA-Lib 0.4+ (技术指标)

**机器学习**：
- LightGBM 4.0+ (梯度提升模型)
- PyTorch 2.0+ (深度学习)
- Scikit-learn 1.3+ (预处理和评估)

**数据库**：
- TimescaleDB (时序数据库)
- psycopg2 (PostgreSQL驱动)

**数据源**：
- AkShare 1.11+ (免费数据源)
- Tushare Pro (专业数据源)

**工具**：
- Loguru (日志)
- Pydantic (配置管理)
- Pytest (测试框架)

---

## 📈 版本历史

**v2.0.0** (2026-01-29)
- ✨ 重构完整架构，模块化设计
- ✨ 新增125+ Alpha因子库
- ✨ 新增向量化回测引擎
- ✨ 新增池化训练Pipeline
- ✨ 统一配置管理（Pydantic）
- ✨ 完整的测试体系

**v1.0.0** (2025-12)
- 🎉 初始版本发布

---

**最后更新**: 2026-01-29
**维护者**: Stock Analysis Team
