# A股AI量化交易系统（Stock Analysis）

一个功能完整的A股量化交易分析系统，集成数据获取、技术分析、机器学习预测、回测引擎和Web API服务，支持：

- **多数据源支持**：**AkShare**（推荐，免费无限制）、Tushare Pro、yfinance
- **时序数据库**：TimescaleDB（基于PostgreSQL）高性能存储历史行情数据
- **技术分析**：使用 **TA-Lib** 计算60+种技术指标（趋势、动量、波动率、Alpha因子）
- **机器学习**：LightGBM、GRU深度学习模型进行价格预测
- **回测引擎**：完整的策略回测框架，支持多策略组合
- **Web API服务**：FastAPI后端提供RESTful API，支持数据下载、特征计算、模型训练、回测等
- **前端界面**：Next.js 14 + TypeScript + Tailwind CSS 构建的现代化Web界面
- **Docker部署**：一键启动完整服务栈（Frontend + Backend + TimescaleDB）
- **可视化分析**：生成技术指标图表，支持Jupyter Notebook交互式分析

## 📁 项目结构

```
stock-analysis/
├── frontend/            # Next.js前端服务
│   ├── src/
│   │   ├── app/        # Next.js页面（App Router）
│   │   ├── components/ # React组件
│   │   ├── lib/        # API客户端和工具库
│   │   ├── store/      # Zustand状态管理
│   │   └── types/      # TypeScript类型定义
│   ├── Dockerfile
│   └── package.json
│
├── backend/             # FastAPI后端服务
│   ├── app/
│   │   ├── api/        # API路由和端点
│   │   ├── core/       # 核心配置
│   │   ├── services/   # 业务逻辑层
│   │   └── main.py     # FastAPI应用入口
│   ├── Dockerfile
│   └── requirements.txt
│
├── core/               # 核心分析代码
│   ├── src/           # 核心业务逻辑（被Backend挂载使用）
│   │   ├── database/  # 数据库管理（TimescaleDB）
│   │   ├── features/  # 特征工程（技术指标、Alpha因子）
│   │   ├── models/    # 机器学习模型（LightGBM、GRU）
│   │   ├── backtest/  # 回测引擎
│   │   ├── data_fetcher.py
│   │   └── main.py
│   ├── scripts/       # 辅助脚本
│   └── tests/         # 测试脚本
│
├── data/              # 数据存储目录
│   ├── timescaledb/  # 数据库数据卷
│   ├── models/       # 训练好的模型
│   ├── results/      # 回测结果
│   └── notebooks/    # Jupyter notebooks
│
├── docs/             # 项目文档
│   ├── ARCHITECTURE.md
│   └── DATABASE_USAGE.md
│
├── db_init/          # 数据库初始化脚本
├── docker-compose.yml # Docker编排配置
├── requirements.txt  # 本地开发依赖
└── .env             # 环境变量配置（需自行创建）
```

## 🎯 核心模块

### 数据管理层 ([core/src/database/](core/src/database/))
- `db_manager.py`：TimescaleDB连接管理、数据存储和查询
- 支持日线数据、特征数据的高效存储和检索

### 数据获取层 ([core/src/data_fetcher.py](core/src/data_fetcher.py))
- 多数据源支持：AkShare（推荐）、Tushare、yfinance
- 智能缓存和错误重试机制

### 特征工程层 ([core/src/features/](core/src/features/))
- `technical_indicators.py`：60+种技术指标（MA、MACD、RSI、KDJ、布林带、ATR等）
- `alpha_factors.py`：Alpha因子计算
- `feature_transformer.py`：特征标准化和转换

### 机器学习层 ([core/src/models/](core/src/models/))
- `lightgbm_model.py`：基于LightGBM的价格预测模型
- `gru_model.py`：基于GRU的深度学习模型
- `model_trainer.py`：统一的模型训练接口

### 回测引擎 ([core/src/backtest/](core/src/backtest/))
- `backtest_engine.py`：策略回测框架
- `strategy.py`：交易策略定义
- 支持多策略组合和性能评估

### Web API服务 ([backend/](backend/))
- 基于FastAPI的RESTful API
- 提供数据下载、特征计算、模型训练、预测、回测等接口
- 详见 [Backend README](backend/README.md)

### 前端界面 ([frontend/](frontend/))
- 基于Next.js 14和TypeScript的现代化Web界面
- 支持股票列表浏览、数据分析、策略回测等功能
- 详见 [Frontend README](frontend/README.md)

## 🛠️ 技术栈

### 核心技术
- **Python 3.9+**（推荐3.10+）
- **Node.js 20+** - JavaScript运行时
- **FastAPI** - 高性能异步Web框架
- **Next.js 14** - React全栈框架
- **TimescaleDB** - 时序数据库（基于PostgreSQL 16）
- **Docker & Docker Compose** - 容器化部署

### 前端技术
- **TypeScript** - 类型安全的JavaScript
- **Tailwind CSS** - 实用优先的CSS框架
- **Zustand** - 轻量级状态管理
- **Axios** - HTTP客户端
- **Recharts** - React图表库

### 数据处理
- **Pandas** - 数据处理
- **NumPy** - 数值计算
- **PyArrow** - 高性能数据序列化

### 数据源
- **AkShare** - A股数据（推荐，免费无限制）
- **Tushare Pro** - A股数据（需Token，有积分限制）
- **yfinance** - 全球股票数据

### 技术分析
- **TA-Lib** - 60+种技术指标

### 机器学习
- **LightGBM** - 梯度提升树模型
- **scikit-learn** - 机器学习工具集
- **TensorFlow/Keras** - 深度学习（GRU模型）

### 可视化
- **Matplotlib** - 静态图表
- **Seaborn** - 统计可视化
- **Plotly** - 交互式图表

### 开发工具
- **Jupyter** - 交互式分析
- **loguru** - 日志记录
- **python-dotenv** - 环境变量管理

## 📦 依赖安装

### 系统依赖

**macOS**:
```bash
# 安装TA-Lib
brew install ta-lib

# 安装PostgreSQL客户端（可选）
brew install postgresql
```

**Ubuntu/Debian**:
```bash
# 安装TA-Lib
sudo apt-get install ta-lib

# 安装PostgreSQL开发库
sudo apt-get install libpq-dev
```

### Python依赖

根目录的 `requirements.txt` 包含本地开发所需的全部依赖：

```bash
# 创建虚拟环境
python3 -m venv stock_env

# 激活虚拟环境
source stock_env/bin/activate  # macOS/Linux
# 或 stock_env\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

主要依赖包括：
- pandas, numpy, pyarrow
- akshare, tushare, yfinance
- TA-Lib, scikit-learn, lightgbm
- matplotlib, seaborn, plotly
- jupyter, python-dotenv

## ⚙️ 配置环境变量

### 1. 创建 .env 文件

```bash
cp .env.example .env
```

### 2. 编辑配置

[.env.example](.env.example) 提供了所有可配置项的示例：

```ini
# 数据源配置（推荐使用akshare，免费无限制）
DATA_SOURCE=akshare  # 可选: akshare, tushare, yfinance

# Tushare Token（仅使用tushare时需要）
TUSHARE_TOKEN=your_tushare_token_here

# DeepSeek AI（可选，用于AI分析）
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

**推荐配置**：
- 使用 **AkShare** 作为主数据源（`DATA_SOURCE=akshare`）
- 无需任何Token，完全免费
- 如需使用Tushare，请到 [tushare.pro](https://tushare.pro/) 注册获取Token

> **注意**: `.env` 文件已在 `.gitignore` 中，不会被提交到Git仓库

## 🚀 快速开始

### 方式一：Docker 部署（推荐）

**最简单的方式，一键启动完整服务栈**

```bash
# 1. 克隆项目
git clone <repository-url>
cd stock-analysis

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，设置 DATA_SOURCE=akshare（推荐）

# 3. 启动服务
docker-compose up -d

# 4. 查看日志
docker-compose logs -f backend

# 5. 访问服务
open http://localhost:3000        # 前端界面
open http://localhost:8000/api/docs  # API文档
```

**服务说明**：
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API文档**: http://localhost:8000/api/docs
- **TimescaleDB**: localhost:5432

**常用命令**：
```bash
# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看服务状态
docker-compose ps

# 进入后端容器
docker-compose exec backend bash
```

### 方式二：本地开发

**适合需要修改核心代码或调试的场景**

#### 1. 安装依赖

```bash
# 创建并激活虚拟环境
python3 -m venv stock_env
source stock_env/bin/activate

# 安装依赖
pip install -r requirements.txt
```

#### 2. 启动数据库（可选）

如果需要使用数据库功能：

```bash
# 只启动数据库服务
docker-compose up -d timescaledb

# 或使用本地PostgreSQL + TimescaleDB扩展
```

#### 3. 运行核心代码

**测试AkShare数据源**：
```bash
python core/scripts/test_akshare.py
```

**下载股票数据到数据库**：
```bash
python core/scripts/download_data_to_db.py --years 5 --max-stocks 50
```

**运行技术分析**：
```bash
python core/src/main.py
```

**启动Jupyter Notebook**：
```bash
./core/scripts/start_jupyter.sh
# 或
jupyter notebook
```

#### 4. 运行Backend（本地开发模式）

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📊 使用示例

### 通过API获取数据

```bash
# 健康检查
curl http://localhost:8000/health

# 获取股票列表
curl http://localhost:8000/api/stocks/list | jq

# 下载股票数据
curl -X POST http://localhost:8000/api/data/download \
  -H "Content-Type: application/json" \
  -d '{"stock_codes": ["000001", "600519"], "years": 5}'

# 计算技术指标
curl -X POST http://localhost:8000/api/features/calculate/000001

# 查看API文档（浏览器）
open http://localhost:8000/api/docs
```

### 通过Python脚本

```python
# 数据获取示例
from core.src.data_fetcher import DataFetcher

fetcher = DataFetcher(source='akshare')
df = fetcher.fetch_data('000001', days=365)
print(df.head())

# 技术指标计算
from core.src.features.technical_indicators import TechnicalIndicators

ti = TechnicalIndicators()
df_with_features = ti.calculate_all(df)
print(df_with_features.columns)
```

### 查看结果

所有分析结果保存在 `data/` 目录：
- `data/results/` - 回测结果和图表
- `data/models/` - 训练好的模型
- `data/notebooks/` - Jupyter分析笔记

## 📚 相关文档

- **[QUICKSTART.md](QUICKSTART.md)** - 快速开始指南
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - 常见问题和故障排除
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - 系统架构文档
- **[docs/DATABASE_USAGE.md](docs/DATABASE_USAGE.md)** - 数据库使用指南
- **[frontend/README.md](frontend/README.md)** - Frontend前端文档
- **[backend/README.md](backend/README.md)** - Backend服务文档
- **[core/README.md](core/README.md)** - 核心代码文档

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## ⚠️ 免责声明

- 本项目仅供**学习和研究**使用
- 代码中的任何技术指标、信号、预测结果**不构成任何投资建议**
- 使用本项目进行实际交易的风险由用户自行承担
- 作者不对使用本项目导致的任何损失负责

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

**开发者**: [Your Name]
**最后更新**: 2026-01-20
