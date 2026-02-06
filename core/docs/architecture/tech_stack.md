# 技术栈详解

**Technology Stack in Stock-Analysis Core**

**版本**: v3.0.0
**最后更新**: 2026-02-06

---

## 📚 技术栈概览

### 核心技术栈

```
┌─────────────────────────────────────────────────────┐
│                   Python 3.9+                        │  核心语言
├─────────────────────────────────────────────────────┤
│  数据处理        │  机器学习        │  Web框架        │
│  - Pandas       │  - LightGBM     │  - FastAPI      │
│  - NumPy        │  - PyTorch      │  - Uvicorn      │
│  - TA-Lib       │  - Scikit-learn │  - Pydantic     │
├─────────────────────────────────────────────────────┤
│  数据库          │  缓存            │  任务调度        │
│  - TimescaleDB  │  - Redis        │  - APScheduler  │
│  - PostgreSQL   │  - LRU Cache    │  - Celery*      │
├─────────────────────────────────────────────────────┤
│  监控日志        │  测试            │  部署            │
│  - Loguru       │  - Pytest       │  - Docker       │
│  - Prometheus*  │  - Pytest-cov   │  - Docker Compose│
├─────────────────────────────────────────────────────┤
│  工具库          │  数据源          │  可视化          │
│  - Click        │  - AkShare      │  - Matplotlib   │
│  - Rich         │  - Tushare      │  - Plotly       │
└─────────────────────────────────────────────────────┘

* 表示可选或规划中
```

---

## 🐍 核心语言与运行时

### Python 3.9+

**选择理由**:
- ✅ 丰富的数据科学生态
- ✅ 类型提示支持（Type Hints）
- ✅ 异步编程支持（asyncio）
- ✅ 高性能数值计算库

**关键特性使用**:
```python
# 1. 类型提示
def calculate_alpha(prices: pd.DataFrame) -> pd.Series:
    pass

# 2. dataclasses
from dataclasses import dataclass

@dataclass
class TradeSignal:
    stock_code: str
    signal: int
    timestamp: datetime

# 3. 字典合并（Python 3.9+）
config = base_config | user_config
```

---

## 📊 数据处理层

### 1. Pandas 2.0+

**版本**: 2.0.3
**用途**: DataFrame操作、时间序列分析

**核心功能**:
```python
# 高效的数据操作
df = pd.read_csv('data.csv')
df['returns'] = df['close'].pct_change()
df['ma20'] = df['close'].rolling(20).mean()

# 时间序列重采样
df_daily = df.resample('D').last()

# 分组聚合
grouped = df.groupby('stock_code').agg({
    'close': ['mean', 'std', 'max', 'min']
})
```

**性能优化**:
- ✅ 使用 `pd.eval()` 加速复杂表达式
- ✅ 使用 `category` 类型减少内存
- ✅ 使用 `pyarrow` 后端提升性能

### 2. NumPy 1.24+

**版本**: 1.24.3
**用途**: 数值计算、向量化操作

```python
# 向量化计算
returns = np.diff(prices) / prices[:-1]
sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252)

# 广播机制
normalized = (data - data.mean(axis=0)) / data.std(axis=0)

# 线性代数
correlation_matrix = np.corrcoef(features.T)
```

### 3. TA-Lib

**版本**: 0.4.28
**用途**: 技术指标计算

```python
import talib as ta

# 移动平均
sma = ta.SMA(close, timeperiod=20)
ema = ta.EMA(close, timeperiod=20)

# 动量指标
rsi = ta.RSI(close, timeperiod=14)
macd, signal, hist = ta.MACD(close)

# 波动率指标
upper, middle, lower = ta.BBANDS(close, timeperiod=20)
atr = ta.ATR(high, low, close, timeperiod=14)
```

---

## 🤖 机器学习层

### 1. LightGBM 4.0+

**版本**: 4.0.0
**用途**: 梯度提升树模型、排序模型

**优势**:
- ✅ 训练速度快
- ✅ 内存占用小
- ✅ 支持类别特征
- ✅ GPU加速支持
- ✅ **排序优化（Ranking）**⭐ - v3.0 新增

**应用场景**:

#### 1. 回归预测（传统）
```python
import lightgbm as lgb

# 创建数据集
train_data = lgb.Dataset(X_train, label=y_train)

# 训练参数
params = {
    'objective': 'regression',
    'metric': 'rmse',
    'boosting_type': 'gbdt',
    'num_leaves': 31,
    'learning_rate': 0.05,
    'feature_fraction': 0.9,
    'device': 'gpu'  # GPU加速
}

# 训练模型
model = lgb.train(params, train_data, num_boost_round=100)
```

#### 2. 排序模型（v3.0 MLSelector）⭐
```python
from src.models.stock_ranker_trainer import StockRankerTrainer

# 创建排序训练器
trainer = StockRankerTrainer(params={
    'objective': 'lambdarank',
    'metric': 'ndcg',
    'ndcg_eval_at': [5, 10, 20],
    'num_leaves': 31,
    'learning_rate': 0.05,
    'min_data_in_leaf': 20
})

# 训练数据格式: (特征, 标签, 查询组)
# 标签为 5 档评分: 0(极差), 1(差), 2(中等), 3(好), 4(极好)
result = trainer.train(
    X_train=features,  # (N, 125+) 特征矩阵
    y_train=labels,    # (N,) 5档评分
    groups=groups      # 每次查询的样本数
)

# 性能指标
# - 训练速度: < 5 秒 (1000+ 样本)
# - 推理速度: < 100ms (100 只股票)
# - NDCG@10: > 0.85
```

**MLSelector 核心技术**（v3.0）:
- ✅ **LambdaRank 算法**: 专门优化排序问题
- ✅ **NDCG@10 指标**: 评估 Top-10 排序质量
- ✅ **5 档评分系统**: 0-4 分精细化标注
- ✅ **特征工程**: 125+ Alpha 因子 + 60+ 技术指标

### 2. PyTorch 2.0+

**版本**: 2.0.1
**用途**: 深度学习（GRU模型）

```python
import torch
import torch.nn as nn

class GRUModel(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers):
        super().__init__()
        self.gru = nn.GRU(
            input_size,
            hidden_size,
            num_layers,
            batch_first=True
        )
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        out, _ = self.gru(x)
        return self.fc(out[:, -1, :])

# GPU训练
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = GRUModel(input_size=10, hidden_size=64, num_layers=2).to(device)
```

### 3. Scikit-learn 1.3+

**版本**: 1.3.0
**用途**: 传统机器学习、数据预处理

```python
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.linear_model import Ridge

# 数据标准化
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 时间序列交叉验证
tscv = TimeSeriesSplit(n_splits=5)
for train_idx, test_idx in tscv.split(X):
    X_train, X_test = X[train_idx], X[test_idx]

# Ridge回归
model = Ridge(alpha=1.0)
model.fit(X_train, y_train)
```

---

## 💾 数据存储层

### 1. TimescaleDB 2.11+

**版本**: 2.11.0
**用途**: 时序数据存储

**核心特性**:
- ✅ 自动分区（Hypertables）
- ✅ 数据压缩
- ✅ 连续聚合
- ✅ 时间范围查询优化

```sql
-- 创建超表
CREATE TABLE stock_data (
    time TIMESTAMPTZ NOT NULL,
    stock_code VARCHAR(10) NOT NULL,
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC,
    volume BIGINT
);

SELECT create_hypertable('stock_data', 'time',
    chunk_time_interval => INTERVAL '1 month');

-- 创建索引
CREATE INDEX idx_stock_code_time ON stock_data (stock_code, time DESC);

-- 启用压缩
ALTER TABLE stock_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'stock_code'
);

-- 压缩策略
SELECT add_compression_policy('stock_data', INTERVAL '7 days');
```

### 2. Redis 7.0+

**版本**: 7.0.12
**用途**: 缓存、会话存储

```python
import redis

# 连接Redis
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# 特征缓存
r.setex('features:000001.SZ', 3600, pickle.dumps(features))
cached_features = pickle.loads(r.get('features:000001.SZ'))

# 发布/订阅
r.publish('backtest_channel', json.dumps(result))
```

---

## 🌐 Web框架层

### 1. FastAPI 0.103+

**版本**: 0.103.0
**用途**: RESTful API开发

**优势**:
- ✅ 自动API文档（Swagger/ReDoc）
- ✅ 类型验证（Pydantic）
- ✅ 异步支持（asyncio）
- ✅ 高性能（基于Starlette）

```python
from fastapi import FastAPI, Query
from pydantic import BaseModel

app = FastAPI(title="Stock Analysis API")

class BacktestRequest(BaseModel):
    stock_codes: List[str]
    start_date: str
    end_date: str
    strategy: str

@app.post("/api/backtest")
async def run_backtest(request: BacktestRequest):
    result = await backtest_service.run(
        request.stock_codes,
        request.start_date,
        request.end_date,
        request.strategy
    )
    return {"status": "success", "data": result}

# 自动生成API文档: http://localhost:8000/docs
```

### 2. Pydantic 2.0+

**版本**: 2.3.0
**用途**: 数据验证、配置管理

```python
from pydantic import BaseModel, Field, validator

class BacktestConfig(BaseModel):
    initial_capital: float = Field(gt=0, description="初始资金")
    commission_rate: float = Field(ge=0, le=0.01, description="手续费率")
    start_date: str = Field(pattern=r'\d{4}-\d{2}-\d{2}')

    @validator('start_date')
    def validate_date(cls, v):
        datetime.strptime(v, '%Y-%m-%d')
        return v

# 自动类型验证
config = BacktestConfig(
    initial_capital=1000000,
    commission_rate=0.0003,
    start_date='2023-01-01'
)
```

---

## 🔧 工具库层

### 1. Click 8.1+

**版本**: 8.1.7
**用途**: CLI命令行工具

```python
import click

@click.group()
def cli():
    """Stock-CLI 命令行工具"""
    pass

@cli.command()
@click.option('--codes', '-c', multiple=True, required=True)
@click.option('--start-date', '-s', required=True)
def download(codes, start_date):
    """下载股票数据"""
    for code in codes:
        click.echo(f"Downloading {code}...")
        download_stock_data(code, start_date)
    click.secho("✓ Download completed", fg='green')

if __name__ == '__main__':
    cli()
```

### 2. Loguru 0.7+

**版本**: 0.7.0
**用途**: 日志管理

```python
from loguru import logger

# 配置日志
logger.add(
    "logs/stock_analysis_{time}.log",
    rotation="1 day",
    retention="30 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)

# 使用日志
logger.info("Starting backtest for {}", stock_code)
logger.warning("Low data quality detected")
logger.error("Failed to fetch data: {}", error)

# 上下文绑定
with logger.contextualize(stock_code="000001.SZ"):
    logger.info("Processing data")  # 自动包含stock_code
```

### 3. Rich 13.5+

**版本**: 13.5.2
**用途**: 终端美化输出

```python
from rich.console import Console
from rich.table import Table
from rich.progress import track

console = Console()

# 美化表格
table = Table(title="Backtest Results")
table.add_column("Stock", style="cyan")
table.add_column("Return", style="magenta")
table.add_column("Sharpe", style="green")
table.add_row("000001.SZ", "15.2%", "1.85")
console.print(table)

# 进度条
for stock in track(stock_codes, description="Processing..."):
    process_stock(stock)
```

---

## 🧪 测试层

### 1. Pytest 7.4+

**版本**: 7.4.0
**用途**: 单元测试、集成测试

**核心指标**（v3.0）:
- ✅ **总测试用例**: 3,200+
- ✅ **测试覆盖率**: 90%+
- ✅ **三层架构测试**: 385 用例（100% 通过）
- ✅ **MLSelector 测试**: 120+ 用例（100% 通过）
- ✅ **并行测试**: 支持 pytest-xdist 多核加速

```python
import pytest

class TestAlphaFactors:
    @pytest.fixture
    def sample_data(self):
        return pd.DataFrame({
            'close': [100, 102, 101, 103, 105],
            'volume': [1000, 1100, 900, 1200, 1300]
        })

    def test_momentum_factor(self, sample_data):
        momentum = calculate_momentum(sample_data)
        assert not momentum.isna().any()
        assert len(momentum) == len(sample_data)

    @pytest.mark.parametrize("window", [5, 10, 20])
    def test_different_windows(self, sample_data, window):
        result = calculate_ma(sample_data, window)
        assert len(result) == len(sample_data)
```

#### v3.0 新增测试模块

**三层架构测试** (`tests/unit/strategies/three_layer/`):
```python
# 选股器测试
class TestMLSelector:
    def test_multi_factor_weighted(self):
        """测试多因子加权选股"""
        selector = MLSelector(params={
            'mode': 'multi_factor_weighted',
            'features': 'momentum_20d,rsi_14d',
            'top_n': 50
        })
        result = selector.select_stocks(prices, date='2023-01-01')
        assert len(result) == 50

    def test_lightgbm_ranker(self):
        """测试 LightGBM 排序模型"""
        selector = MLSelector(params={
            'mode': 'lightgbm_ranker',
            'model_path': './models/test_ranker.pkl',
            'top_n': 50
        })
        result = selector.select_stocks(prices, date='2023-01-01')
        assert len(result) == 50

# 集成测试
class TestThreeLayerIntegration:
    def test_full_workflow(self):
        """测试完整三层工作流"""
        composer = StrategyComposer(
            selector=MLSelector(params={'mode': 'multi_factor_weighted', 'top_n': 50}),
            entry=ImmediateEntry(),
            exit_strategy=FixedStopLossExit(params={'stop_loss_pct': -5.0}),
            rebalance_freq='W'
        )
        result = backtest_engine.backtest_three_layer(
            composer.selector, composer.entry, composer.exit,
            prices, start_date='2023-01-01', end_date='2023-12-31'
        )
        assert result['total_return'] is not None
```

**性能基准测试** (`tests/performance/`):
```python
@pytest.mark.benchmark
def test_ml_selector_performance():
    """MLSelector 性能基准测试"""
    selector = MLSelector(params={
        'mode': 'multi_factor_weighted',
        'features': 'momentum_20d,rsi_14d,volatility_20d',
        'top_n': 50
    })

    start = time.time()
    result = selector.select_stocks(prices, date='2023-01-01')
    elapsed = time.time() - start

    # 性能要求: < 50ms (20只股票)
    assert elapsed < 0.05, f"MLSelector too slow: {elapsed:.3f}s"
```

### 2. Pytest-cov

**用途**: 测试覆盖率报告

```bash
# 运行测试并生成覆盖率报告
pytest --cov=src --cov-report=html --cov-report=term

# 输出示例（v3.0）
---------- coverage: platform darwin, python 3.9.17 -----------
Name                                  Stmts   Miss  Cover
---------------------------------------------------------
src/data/__init__.py                      5      0   100%
src/features/alpha_factors/              450     23    95%
src/features/technical_indicators.py     350     18    95%
src/strategies/three_layer/              800     45    94%
src/strategies/three_layer/selectors/    450     25    94%
src/models/lightgbm_model.py             180     18    90%
src/models/stock_ranker_trainer.py       200     12    94%
---------------------------------------------------------
TOTAL                                   3200    288    91%
```

### 3. Pytest-xdist（并行测试）

**版本**: 3.3.1
**用途**: 多核并行测试加速

```bash
# 使用 4 个 CPU 核心并行测试
pytest -n 4 tests/

# 性能对比
# 单核运行: 120 秒
# 4核并行: 35 秒（提升 3.4 倍）
```

---

## 🐳 部署层

### 1. Docker 24.0+

**用途**: 容器化部署

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 运行应用
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0"]
```

### 2. Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  timescaledb:
    image: timescale/timescaledb:latest-pg15
    environment:
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - timescale_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  backend:
    build: ./core
    depends_on:
      - timescaledb
      - redis
    environment:
      DATABASE_URL: postgresql://postgres:password@timescaledb:5432/stock_analysis
      REDIS_URL: redis://redis:6379
    ports:
      - "8000:8000"

volumes:
  timescale_data:
```

---

## 📊 技术选型对比

### 数据库选型

| 数据库 | 优势 | 劣势 | 适用场景 |
|--------|------|------|---------|
| **TimescaleDB** | ✅ 时序优化<br>✅ SQL标准<br>✅ 自动分区 | ❌ 单机扩展有限 | ✅ 时序数据<br>✅ 中小规模 |
| InfluxDB | ✅ 高性能写入 | ❌ SQL支持弱 | ❌ 不适合本项目 |
| MongoDB | ✅ 灵活schema | ❌ 时序查询慢 | ❌ 不适合本项目 |

### 机器学习框架对比

| 框架 | 优势 | 劣势 | 选择理由 | v3.0应用 |
|------|------|------|---------|---------|
| **LightGBM** | ✅ 速度快<br>✅ 内存小<br>✅ GPU支持<br>✅ **排序优化**⭐ | ❌ 调参复杂 | ✅ 表格数据首选<br>✅ 排序任务首选 | ✅ MLSelector 排序模型 |
| **PyTorch** | ✅ 灵活性高<br>✅ 动态图 | ❌ 部署复杂 | ✅ 序列数据首选 | ✅ GRU 深度学习 |
| XGBoost | ✅ 准确率高 | ❌ 速度慢<br>❌ 排序支持弱 | ❌ 性能不如LightGBM | ❌ 未使用 |
| TensorFlow | ✅ 生态完善 | ❌ 学习曲线陡 | ❌ 过于重量级 | ❌ 未使用 |

### 选股算法对比（v3.0 新增）

| 算法 | 类型 | 训练时间 | 推理时间 | 适用场景 |
|------|------|---------|---------|---------|
| **多因子加权** | 启发式 | 无需训练 | <15ms | ✅ 快速原型 |
| **LightGBM Ranker** | 机器学习 | <5秒 | <100ms | ✅ 生产环境⭐ |
| 深度排序网络 | 深度学习 | ~300秒 | ~500ms | ❌ 成本高 |
| 强化学习 | RL | ~3600秒 | ~1000ms | ❌ 不稳定 |

---

## 🔮 技术演进规划

### 短期（2026 Q2-Q3）

- 📋 引入 Apache Arrow（列式存储）
- 📋 升级到 Pandas 2.1+（性能提升）
- 📋 集成 Prometheus（监控）

### 中期（2026 Q4-2027 H1）

- 📋 引入 Ray（分布式计算）
- 📋 引入 MLflow（模型管理）
- 📋 Kubernetes部署

### 长期（2027 H2+）

- 📋 Spark集成（大数据处理）
- 📋 Kafka集成（实时数据流）
- 📋 微服务架构

---

## 📚 相关文档

- 🏗️ [架构总览详解](overview.md)
- 🎨 [设计模式详解](design_patterns.md)
- ⚡ [性能优化分析](performance.md)

---

**文档版本**: v3.0.0
**维护团队**: Quant Team
**最后更新**: 2026-02-06
**v3.0 核心技术**: LightGBM Ranking + MLSelector + 3,200+ 测试用例
