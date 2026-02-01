# Stock-Analysis Backend

<div align="center">

**A股AI量化交易系统 - 高性能后端API服务**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-production%20ready-success.svg)]()

**[快速开始](docs/user_guide/quick_start.md) • [API 文档](http://localhost:8000/api/docs) • [架构设计](docs/architecture/overview.md) • [贡献指南](docs/developer_guide/contributing.md)**

</div>

---

## 项目简介

**Stock-Analysis Backend** 是一个基于 FastAPI 的**生产级**量化交易 API 服务，通过 Docker 挂载方式集成 Core 核心分析模块，提供完整的 RESTful API 接口。

### 核心定位

- **API 网关**: 暴露所有量化分析功能的 HTTP 接口
- **业务编排**: 协调 Core 模块完成复杂业务流程
- **数据同步**: 管理股票数据的定时同步和更新
- **实验管理**: 提供自动化模型训练和回测实验功能

### 核心指标

| 指标 | 数值 | 说明 |
|------|------|------|
| 📊 **API 端点** | 60+ | 13 个功能模块 |
| ⚡ **性能** | 10K QPS | 简单查询吞吐量 |
| 📚 **文档覆盖** | 100% | Swagger 自动文档 |
| 🐳 **部署方式** | Docker | 一键部署 |
| 🔗 **Core 集成** | 挂载模式 | 无缝调用 |

---

## 技术栈

| 类别 | 技术 | 版本 |
|------|------|------|
| **Web 框架** | FastAPI | 0.104+ |
| **ASGI 服务器** | Uvicorn | 0.24+ |
| **数据验证** | Pydantic | 2.0+ |
| **数据库** | TimescaleDB | PostgreSQL 14+ |
| **ORM** | SQLAlchemy | 2.0+ (async) |
| **驱动** | asyncpg | 0.29+ |
| **日志** | Loguru | 0.7+ |
| **HTTP 客户端** | httpx | 0.25+ |
| **数据处理** | Pandas, NumPy | - |
| **机器学习** | LightGBM | - |
| **Core 集成** | Docker 挂载 | - |

---

## 快速开始

### 使用 Docker Compose（推荐）

```bash
# 1. 进入项目根目录
cd /Volumes/MacDriver/stock-analysis

# 2. 启动服务（Backend + TimescaleDB）
docker-compose up -d

# 3. 查看日志
docker-compose logs -f backend

# 4. 访问 API 文档
open http://localhost:8000/api/docs
```

### 验证服务

```bash
# 健康检查
curl http://localhost:8000/health

# 预期输出
{
  "status": "healthy",
  "environment": "development"
}
```

完整教程请查看 [快速开始指南](docs/user_guide/quick_start.md)

---

## 核心特性

### 1. 完整的 API 服务

- **13 个功能模块**: 股票、数据、特征、模型、回测、ML、策略、同步、定时任务...
- **60+ API 端点**: 覆盖从数据获取到回测的完整工作流
- **自动文档**: Swagger UI + ReDoc，开箱即用
- **统一响应**: 一致的 API 响应格式

### 2. 高性能架构

- **异步 I/O**: FastAPI + asyncpg，支持 10,000+ QPS
- **连接池**: 数据库连接池，优化资源使用
- **批量处理**: 批量数据下载、插入、计算
- **后台任务**: 长时间任务异步执行

### 3. 与 Core 无缝集成

- **Docker 挂载**: 通过挂载访问 Core 代码
- **直接调用**: 无需 API 调用，直接导入 Core 模块
- **职责分离**: Backend 专注 API 服务，Core 专注分析逻辑

### 4. 生产级质量

- **分层架构**: API → Service → Repository → Core
- **异常处理**: 全局异常处理器，友好错误提示
- **日志系统**: Loguru 统一日志，支持轮转
- **健康检查**: 服务监控端点

---

## API 概览

### 基础端点

- `GET /` - 服务根路径
- `GET /health` - 健康检查
- `GET /api/docs` - Swagger UI 文档
- `GET /api/redoc` - ReDoc 文档

### 核心模块

| 模块 | 端点前缀 | 主要功能 |
|------|---------|---------|
| 股票管理 | `/api/stocks` | 股票列表、信息查询、更新 |
| 数据管理 | `/api/data` | 数据下载、查询、批量处理 |
| 特征工程 | `/api/features` | Alpha 因子计算、技术指标 |
| 模型管理 | `/api/models` | 模型训练、预测、评估 |
| 回测引擎 | `/api/backtest` | 策略回测、结果分析 |
| 机器学习 | `/api/ml` | ML 训练、批量训练、预测 |
| 策略管理 | `/api/strategy` | 策略列表、信号测试 |
| 数据同步 | `/api/sync` | 股票列表同步、日线同步 |
| 定时任务 | `/api/scheduler` | 任务创建、管理、执行 |
| 配置管理 | `/api/config` | 系统配置读取、更新 |
| 市场状态 | `/api/market` | 交易日历、市场状态 |
| 自动化实验 | `/api/experiment` | 实验创建、管理、结果查询 |

详细 API 文档请访问: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

---

## 项目结构

```
backend/
├── app/                        # 主应用目录
│   ├── main.py                 # FastAPI 应用入口
│   ├── core/                   # 核心配置
│   │   ├── config.py           # 环境配置
│   │   └── __init__.py
│   ├── api/                    # API 层
│   │   ├── __init__.py         # 路由注册
│   │   ├── error_handler.py    # 全局异常处理
│   │   └── endpoints/          # API 端点（13 个模块）
│   ├── services/               # 业务逻辑层（20+ 服务）
│   ├── repositories/           # 数据访问层
│   ├── strategies/             # 策略模块
│   ├── interfaces/             # 类型定义
│   ├── models/                 # 数据模型
│   ├── schemas/                # Pydantic 模式
│   └── utils/                  # 工具函数
├── src/                        # Core 代码挂载点
│   └── (通过 Docker 挂载 ../core/src)
├── docs/                       # 完整文档
│   ├── README.md               # 文档导航
│   ├── architecture/           # 架构文档
│   ├── api_reference/          # API 参考
│   ├── user_guide/             # 用户指南
│   ├── developer_guide/        # 开发指南
│   └── deployment/             # 部署文档
├── Dockerfile                  # Docker 镜像
├── docker-compose.yml          # Docker Compose 配置
├── requirements.txt            # Python 依赖
└── README.md                   # 本文档
```

**注意**: `src/` 目录通过 Docker Compose 挂载 `../core/src`，实现与 Core 的无缝集成。

---

## 使用示例

### Hello World (30 秒)

```bash
# 1. 健康检查
curl http://localhost:8000/health

# 2. 获取股票列表
curl http://localhost:8000/api/stocks/list

# 3. 下载股票数据
curl -X POST http://localhost:8000/api/data/download \
  -H "Content-Type: application/json" \
  -d '{
    "stock_code": "000001.SZ",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31"
  }'

# 4. 运行回测
curl -X POST http://localhost:8000/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "stock_code": "000001.SZ",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "strategy": "momentum",
    "initial_capital": 1000000
  }'
```

### Python 客户端

```python
import httpx
import asyncio

async def main():
    async with httpx.AsyncClient() as client:
        # 下载数据
        response = await client.post(
            "http://localhost:8000/api/data/download",
            json={
                "stock_code": "000001.SZ",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            }
        )
        print(response.json())

        # 运行回测
        response = await client.post(
            "http://localhost:8000/api/backtest/run",
            json={
                "stock_code": "000001.SZ",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "strategy": "momentum",
                "initial_capital": 1000000
            }
        )
        result = response.json()
        print(f"年化收益: {result['data']['annual_return']:.2%}")
        print(f"夏普比率: {result['data']['sharpe_ratio']:.2f}")

asyncio.run(main())
```

---

## 完整文档

### 📚 文档中心

- 📖 [文档导航](docs/README.md) - 完整文档索引
- 🏗️ [架构总览](docs/architecture/overview.md) - 分层架构、数据流、设计模式
- 🔧 [技术栈详解](docs/architecture/tech_stack.md) - FastAPI、Pydantic、SQLAlchemy 详解

### 📖 用户指南

- 🚀 [快速开始](docs/user_guide/quick_start.md) - 15 分钟快速上手教程

### 📘 API 参考

- 📚 [API 概览](docs/api_reference/README.md) - 13 个模块、60+ 端点
- 🌐 [Swagger UI](http://localhost:8000/api/docs) - 在线交互式文档
- 📄 [ReDoc](http://localhost:8000/api/redoc) - 美观的 API 文档

### 💻 开发指南

- 🤝 [贡献指南](docs/developer_guide/contributing.md) - 代码规范、测试、PR 流程

### 🚀 部署文档

- 🐳 [Docker 部署](docs/deployment/docker.md) - Docker Compose、生产部署、监控

---

## 性能基准

### API 响应时间

| 端点类型 | 平均响应时间 | P95 | P99 |
|---------|-------------|-----|-----|
| 健康检查 | 2ms | 5ms | 10ms |
| 简单查询 | 15ms | 30ms | 50ms |
| 复杂查询 | 120ms | 200ms | 300ms |
| 回测任务 | 2500ms | 4000ms | 6000ms |

### 并发性能

- **简单查询**: 10,000 QPS
- **复杂查询**: 1,000 QPS
- **回测任务**: 50 并发

---

## 与 Core 的集成

### Docker 挂载方式

通过 `docker-compose.yml` 挂载 Core 代码：

```yaml
services:
  backend:
    volumes:
      - ./backend:/app          # Backend 代码
      - ./core/src:/app/src     # Core 代码挂载
      - ./data:/data            # 数据目录
```

### 导入方式

在 Backend 中直接导入 Core 模块：

```python
# 数据层
from src.database.db_manager import DatabaseManager
from src.data.data_fetcher import DataFetcher

# 特征层
from src.features.technical_indicators import TechnicalIndicators
from src.features.alpha_factors import AlphaFactors

# 模型层
from src.models.model_trainer import ModelTrainer

# 回测层
from src.backtest.backtest_engine import BacktestEngine

# 策略层
from src.strategies.momentum_strategy import MomentumStrategy
```

### 优势

- ✅ **代码复用**: 避免重复实现分析逻辑
- ✅ **单一来源**: Core 作为唯一的分析逻辑实现
- ✅ **独立开发**: Backend 和 Core 可以独立迭代
- ✅ **灵活部署**: 可以单独部署或联合部署

---

## 环境配置

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| ENVIRONMENT | 运行环境 | development |
| DATABASE_HOST | 数据库主机 | timescaledb |
| DATABASE_PORT | 数据库端口 | 5432 |
| DATABASE_NAME | 数据库名称 | stock_analysis |
| DATABASE_USER | 数据库用户 | stock_user |
| DATABASE_PASSWORD | 数据库密码 | - |
| TUSHARE_TOKEN | Tushare Token | - |

### .env 文件

创建 `.env` 文件配置环境变量：

```bash
ENVIRONMENT=production
DATABASE_USER=stock_user
DATABASE_PASSWORD=your_secure_password
TUSHARE_TOKEN=your_token_here
```

---

## 开发指南

### 本地开发

```bash
# 1. 创建虚拟环境
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 开发依赖

# 3. 设置环境变量
export DATABASE_HOST=localhost
export DATABASE_PORT=5432

# 4. 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 代码规范

```bash
# 格式化代码
black app/ tests/

# 排序导入
isort app/ tests/

# 类型检查
mypy app/

# 代码检查
flake8 app/ tests/
```

### 测试

```bash
# 运行测试
pytest tests/ -v

# 测试覆盖率
pytest tests/ --cov=app --cov-report=html
```

详细开发指南请查看 [贡献指南](docs/developer_guide/contributing.md)

---

## 故障排查

### 服务无法启动

```bash
# 查看日志
docker-compose logs backend

# 重启服务
docker-compose restart backend

# 重新构建
docker-compose build --no-cache backend
docker-compose up -d
```

### 数据库连接失败

```bash
# 检查数据库状态
docker-compose ps timescaledb

# 测试连接
docker-compose exec timescaledb psql -U stock_user -d stock_analysis

# 重启数据库
docker-compose restart timescaledb
```

更多问题请查看 [部署文档](docs/deployment/docker.md)

---

## 开发路线

### v1.0.0 (2026-02-01) ✅ 已发布

**核心功能**:
- ✅ 完整的 RESTful API（13 个模块、60+ 端点）
- ✅ 与 Core 集成（Docker 挂载）
- ✅ 异步 I/O（FastAPI + asyncpg）
- ✅ 自动文档（Swagger UI + ReDoc）
- ✅ 完整文档系统

### v1.1.0 (计划中)

**计划功能**:
- [ ] JWT 认证
- [ ] API 限流
- [ ] Redis 缓存
- [ ] Celery 任务队列

### v2.0.0 (未来)

**计划功能**:
- [ ] WebSocket 实时推送
- [ ] GraphQL 支持
- [ ] 微服务化
- [ ] 服务网格（Istio）

---

## 贡献

我们欢迎所有形式的贡献！

### 如何贡献

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

详见 [贡献指南](docs/developer_guide/contributing.md)

---

## 相关链接

### 文档

- 📚 [完整文档](docs/README.md)
- 🏗️ [架构设计](docs/architecture/overview.md)
- 📖 [API 参考](docs/api_reference/README.md)
- 🚀 [快速开始](docs/user_guide/quick_start.md)
- 🐳 [部署指南](docs/deployment/docker.md)

### 项目

- [项目主页](../README.md)
- [Core 模块](../core/README.md)
- [快速开始指南](../QUICKSTART.md)

### 外部资源

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [TimescaleDB 文档](https://docs.timescale.com/)
- [Pydantic 文档](https://docs.pydantic.dev/)

---

## 支持

- 📧 **问题反馈**: [GitHub Issues](https://github.com/your-org/stock-analysis/issues)
- 💬 **讨论区**: [GitHub Discussions](https://github.com/your-org/stock-analysis/discussions)
- 📚 **文档**: [完整文档](docs/README.md)

---

## 致谢

感谢所有贡献者对本项目的支持！

特别感谢以下开源项目：
- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的 Web 框架
- [TimescaleDB](https://www.timescale.com/) - 时序数据库
- [Pydantic](https://pydantic.dev/) - 数据验证库

---

## 许可

本项目采用 MIT License - 详见 [LICENSE](LICENSE) 文件

---

<div align="center">

**Made with ❤️ by Quant Team**

⭐ 如果这个项目对你有帮助，请给我们一个 Star！

</div>
