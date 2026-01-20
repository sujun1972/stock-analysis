# 🚀 A股AI量化交易系统 - 快速开始指南

## 📌 系统概述

这是一个功能完整的A股AI量化交易分析系统，集成数据获取、技术分析、机器学习预测、回测引擎和Web API服务。

**核心优势：**
- ✅ **免费数据源**：AkShare（无需Token）
- ✅ **时序数据库**：TimescaleDB高性能存储
- ✅ **Web API**：FastAPI后端RESTful服务
- ✅ **Docker部署**：一键启动完整服务栈
- ✅ **125+特征**：技术指标 + Alpha因子
- ✅ **AI模型**：LightGBM + GRU深度学习
- ✅ **回测引擎**：完整的策略回测框架

---

## 1️⃣ 快速启动（推荐：Docker方式）

### 方式A：Docker Compose（最简单）

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env，设置 DATA_SOURCE=akshare

# 2. 启动完整服务栈
docker-compose up -d

# 3. 查看日志
docker-compose logs -f backend

# 4. 访问API文档
open http://localhost:8000/api/docs
```

**服务说明**：
- **Backend API**: http://localhost:8000
- **API文档**: http://localhost:8000/api/docs
- **TimescaleDB**: localhost:5432

**健康检查**：
```bash
curl http://localhost:8000/health
```

### 方式B：本地开发（适合调试）

```bash
# 1. 进入项目目录
cd /path/to/stock-analysis

# 2. 激活虚拟环境
source stock_env/bin/activate  # macOS/Linux
# 或 stock_env\Scripts\activate  # Windows

# 3. 验证环境
python --version
which python  # 应显示 .../stock_env/bin/python

# 4. 测试AkShare数据源
python core/scripts/test_akshare.py
```

---

## 2️⃣ 验证系统功能

### 方式A：通过API测试

```bash
# 健康检查
curl http://localhost:8000/health

# 获取股票列表
curl http://localhost:8000/api/stocks/list | jq

# 下载股票数据
curl -X POST http://localhost:8000/api/data/download \
  -H "Content-Type: application/json" \
  -d '{"stock_codes": ["000001", "600519"], "years": 5}'
```

### 方式B：运行测试脚本

```bash
# 确保已激活虚拟环境
source stock_env/bin/activate

# 测试所有模块（约2-3分钟）
python core/tests/test_phase1_data_pipeline.py  # 数据管道
python core/tests/test_phase2_features.py       # 特征工程
python core/tests/test_phase3_models.py         # AI模型
python core/tests/test_phase4_backtest.py       # 回测引擎
```

**期望输出：**
```
✅ 所有测试通过！Phase X 运行正常
```

---

## 3️⃣ 实战使用

### 场景1：下载A股历史数据

#### 🆕 方式A：通过API下载（推荐）

```bash
# 1. 确保服务已启动
docker-compose up -d

# 2. 下载指定股票数据
curl -X POST http://localhost:8000/api/data/download \
  -H "Content-Type: application/json" \
  -d '{
    "stock_codes": ["000001", "600519", "000002"],
    "years": 5
  }'

# 3. 查看下载状态
# 返回的 task_id 用于查询进度
curl http://localhost:8000/api/data/download/status/{task_id}

# 4. 查询已下载的数据
curl http://localhost:8000/api/data/daily/000001
```

**优势：**
- ✅ 异步下载，不阻塞
- ✅ 自动存储到TimescaleDB
- ✅ 进度追踪
- ✅ 自动去重和增量更新

#### 方式B：命令行脚本

```bash
# 1. 启动数据库（如使用Docker）
docker-compose up -d timescaledb

# 2. 激活虚拟环境
source stock_env/bin/activate

# 3. 下载到数据库（推荐）
python core/scripts/download_data_to_db.py --years 5 --max-stocks 10

# 4. 下载到CSV（传统方式）
python core/scripts/download_data.py --years 5 --max-stocks 10
```

**数据存储：**
- **数据库**: PostgreSQL + TimescaleDB，查询速度快5-120倍 🚀
- **CSV文件**: `data/raw/daily/{股票代码}.csv`

**详细文档：** [数据库使用指南](docs/DATABASE_USAGE.md)

---

### 场景2：计算技术指标和Alpha因子

#### 方式A：通过API计算

```bash
# 计算指定股票的技术指标
curl -X POST http://localhost:8000/api/features/calculate/000001

# 获取计算结果
curl http://localhost:8000/api/features/000001
```

#### 方式B：Python脚本

```python
# 创建脚本: examples/calculate_features.py

import pandas as pd
from core.src.features.technical_indicators import TechnicalIndicators
from core.src.features.alpha_factors import AlphaFactors

# 加载数据
df = pd.read_csv('data/raw/daily/000001.csv', index_col=0, parse_dates=True)

# 计算技术指标
ti = TechnicalIndicators()
df_with_ti = ti.calculate_all(df)
print(f"技术指标数量: {len([c for c in df_with_ti.columns if c not in df.columns])}")

# 计算Alpha因子
af = AlphaFactors()
df_with_features = af.calculate_all(df_with_ti)
print(f"总特征数量: {len([c for c in df_with_features.columns if c not in df.columns])}")

# 保存
df_with_features.to_csv('data/features/000001_features.csv')
```

运行：
```bash
python examples/calculate_features.py
```

---

### 场景3：训练选股模型

```python
# 创建脚本: examples/train_model.py

import pandas as pd
from src.models.model_trainer import train_stock_model

# 加载特征数据
df = pd.read_csv('data/features/000001_features.csv', index_col=0, parse_dates=True)

# 创建目标：未来5日收益率
df['target'] = df['close'].pct_change(5).shift(-5)

# 定义特征（排除目标和原始价格列）
exclude_cols = ['open', 'high', 'low', 'close', 'vol', 'target']
feature_cols = [col for col in df.columns if col not in exclude_cols]

# 训练模型
trainer, metrics = train_stock_model(
    df=df.dropna(),
    feature_cols=feature_cols,
    target_col='target',
    model_type='lightgbm',
    model_params={
        'learning_rate': 0.05,
        'n_estimators': 500,
        'num_leaves': 31
    },
    save_path='models/saved/my_stock_model'
)

# 查看结果
print(f"\nIC: {metrics['ic']:.4f}")
print(f"Rank IC: {metrics['rank_ic']:.4f}")
print(f"Long-Short Return: {metrics['long_short_return']:.4f}")
```

运行：
```bash
python examples/train_model.py
```

**期望输出：**
```
IC: 0.7500+  （相关性强）
Rank IC: 0.7500+
Long-Short Return: 0.03+  （3%以上）
```

---

### 场景4：运行策略回测

```python
# 创建脚本: examples/run_backtest.py

import pandas as pd
import numpy as np
from src.backtest.backtest_engine import BacktestEngine
from src.backtest.performance_analyzer import PerformanceAnalyzer

# 模拟信号数据（实际使用时应该是模型预测）
dates = pd.date_range('2023-01-01', periods=252, freq='D')
stocks = ['600000', '600036', '601318', '000001', '000002']

# 随机信号（示例）
signals = pd.DataFrame(
    np.random.randn(252, 5),
    index=dates,
    columns=stocks
)

# 模拟价格数据
prices = pd.DataFrame(
    np.random.uniform(10, 20, (252, 5)),
    index=dates,
    columns=stocks
)

# 创建回测引擎
engine = BacktestEngine(
    initial_capital=1000000,  # 100万
    verbose=True
)

# 运行回测
results = engine.backtest_long_only(
    signals=signals,
    prices=prices,
    top_n=3,               # 每期选3只
    holding_period=10,     # 持仓10天
    rebalance_freq='W'     # 每周调仓
)

# 绩效分析
analyzer = PerformanceAnalyzer(
    returns=results['daily_returns'],
    risk_free_rate=0.03,
    periods_per_year=252
)

metrics = analyzer.calculate_all_metrics(verbose=True)
```

运行：
```bash
python examples/run_backtest.py
```

**期望输出：**
```
============================================================
策略绩效分析
============================================================

收益指标:
  年化收益率:          XX.XX%

风险指标:
  最大回撤:            -X.XX%

风险调整收益:
  夏普比率:            X.XXXX

交易统计:
  胜率:                XX.XX%
```

---

## 4️⃣ 项目结构速查

```
stock-analysis/
├── backend/                    # FastAPI后端服务
│   ├── app/
│   │   ├── api/endpoints/     # API端点
│   │   ├── services/          # 业务逻辑层
│   │   └── main.py            # FastAPI应用入口
│   ├── Dockerfile
│   └── requirements.txt
│
├── core/                       # 核心分析代码
│   ├── src/                   # 核心业务逻辑
│   │   ├── database/          # TimescaleDB管理
│   │   ├── features/          # 特征工程
│   │   │   ├── technical_indicators.py  # 技术指标
│   │   │   ├── alpha_factors.py         # Alpha因子
│   │   │   └── feature_transformer.py   # 特征转换
│   │   ├── models/            # 机器学习模型
│   │   │   ├── lightgbm_model.py       # LightGBM
│   │   │   ├── gru_model.py            # GRU深度学习
│   │   │   └── model_trainer.py        # 训练器
│   │   ├── backtest/          # 回测引擎
│   │   │   ├── backtest_engine.py      # T+1回测
│   │   │   ├── performance_analyzer.py # 绩效分析
│   │   │   └── strategy.py             # 策略定义
│   │   ├── config/            # 配置
│   │   ├── data/              # 数据处理
│   │   └── data_fetcher.py    # 数据获取
│   ├── scripts/               # 辅助脚本
│   │   ├── download_data.py          # CSV下载
│   │   ├── download_data_to_db.py    # 数据库下载
│   │   └── test_akshare.py           # 数据源测试
│   └── tests/                 # 测试脚本
│
├── data/                       # 数据存储
│   ├── timescaledb/           # 数据库数据卷
│   ├── models/                # 训练好的模型
│   ├── results/               # 回测结果
│   └── notebooks/             # Jupyter notebooks
│
├── docs/                       # 项目文档
├── db_init/                    # 数据库初始化
├── stock_env/                  # 虚拟环境
├── docker-compose.yml          # Docker编排
├── requirements.txt            # Python依赖
└── .env                        # 环境配置
```

---

## 5️⃣ 常见问题

### Q1: Docker服务启动失败？

```bash
# 检查Docker是否运行
docker ps

# 查看服务状态
docker-compose ps

# 查看错误日志
docker-compose logs backend
docker-compose logs timescaledb

# 重启服务
docker-compose restart
```

### Q2: API访问失败？

```bash
# 检查服务是否启动
curl http://localhost:8000/health

# 如果返回连接错误，检查容器状态
docker-compose ps

# 重启backend服务
docker-compose restart backend
```

### Q3: 虚拟环境激活失败？

```bash
# 确保在项目根目录
pwd  # 应显示 .../stock-analysis

# 检查虚拟环境是否存在
ls stock_env/bin/activate

# 如果不存在，重新创建
python3 -m venv stock_env
source stock_env/bin/activate
pip install -r requirements.txt
```

### Q4: 模块导入失败？

```bash
# 确保使用正确的路径
# 旧路径（错误）: from src.xxx import yyy
# 新路径（正确）: from core.src.xxx import yyy

# 或在容器内直接使用
# from src.xxx import yyy  # 容器内已挂载
```

### Q5: TA-Lib安装失败？

```bash
# macOS
brew install ta-lib
pip install TA-Lib

# Ubuntu/Debian
sudo apt-get install ta-lib
pip install TA-Lib

# Windows: 下载预编译包
# https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
```

### Q6: 数据库连接失败？

```bash
# 检查数据库是否启动
docker-compose ps timescaledb

# 查看数据库日志
docker-compose logs timescaledb

# 测试连接
docker-compose exec timescaledb psql -U stock_user -d stock_analysis
```

---

## 6️⃣ 性能基准

### 系统测试结果

| 模块 | 指标 | 数值 |
|------|------|------|
| **Phase 1: 数据** | 过滤率 | 33.33% |
| | 清洗率 | 8% |
| **Phase 2: 特征** | 技术指标 | 36个 |
| | Alpha因子 | 51个 |
| | 总特征 | 125个 |
| **Phase 3: 模型** | IC | 0.79 |
| | Rank IC | 0.78 |
| | R² | 0.86 |
| **Phase 4: 回测** | 年化收益 | 107% |
| | 夏普比率 | 12.85 |
| | 最大回撤 | -1.34% |
| | 胜率 | 70.92% |

---

## 7️⃣ 下一步

### 学习路径

1. ✅ **运行测试**：熟悉系统各模块
2. ✅ **下载数据**：获取真实A股数据
3. ✅ **计算特征**：理解特征工程
4. ✅ **训练模型**：尝试不同参数
5. ✅ **回测验证**：评估策略效果
6. 🔜 **参数优化**：调整选股数量、持仓期等
7. 🔜 **因子研究**：开发自定义因子
8. 🔜 **集成LLM**：新闻情感分析

### 进阶功能

- [ ] GRU时序模型（需安装PyTorch）
- [ ] 多空策略（需融券权限）
- [ ] 实盘接入（EasyTrader）
- [ ] 可视化界面（Streamlit）

---

## ⚠️ 重要提示

**本系统仅供学习研究，不构成投资建议！**

- 历史业绩 ≠ 未来收益
- 回测结果可能存在过拟合
- 实盘交易请谨慎

---

## 📞 获取帮助

### 文档资源

- **[README.md](README.md)** - 主要项目文档
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - 故障排除指南
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - 系统架构
- **[docs/DATABASE_USAGE.md](docs/DATABASE_USAGE.md)** - 数据库使用
- **[backend/README.md](backend/README.md)** - Backend API文档
- **[core/README.md](core/README.md)** - 核心代码文档

### 快速链接

- **API文档**: http://localhost:8000/api/docs (启动服务后访问)
- **测试脚本**: `core/tests/` 目录
- **辅助脚本**: `core/scripts/` 目录
- **配置文件**: `core/src/config/`

### Docker命令速查

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f backend

# 进入容器
docker-compose exec backend bash
```

---

**祝交易顺利！📈**
