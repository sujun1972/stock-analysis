# Backend 架构总览

**版本**: v4.0.0
**最后更新**: 2026-02-09

---

## 架构概述

Backend 是 Stock-Analysis 项目的 **API 服务层**，基于 FastAPI 框架构建，提供高性能的异步 RESTful API 服务。它通过 Docker 挂载方式使用 Core 项目的核心分析能力，实现了清晰的职责分离。

### 核心定位

- **API 网关**: 暴露所有量化分析功能的 HTTP 接口
- **业务编排**: 协调 Core 模块完成复杂业务流程
- **数据同步**: 管理股票数据的定时同步和更新
- **实验管理**: 提供自动化模型训练和回测实验功能

---

## 架构设计

### 分层架构

Backend 采用 Core v6.0 适配后的分层架构设计：

```
┌─────────────────────────────────────────────────────────────────┐
│                     API Layer (FastAPI)                          │
│                      /api/endpoints/                             │
│  stocks | data | features | backtest | strategy-configs | ...   │
└───────────────────┬────────────────────────────────────────────┘
                    │
┌───────────────────▼────────────────────────────────────────────┐
│                   Core Adapters (薄层封装)                      │
│                   /app/core_adapters/                           │
│  DataAdapter | FeatureAdapter | BacktestAdapter               │
│  ConfigStrategyAdapter ⭐ | DynamicStrategyAdapter ⭐          │
└───────────────────┬────────────────────────────────────────────┘
                    │
┌───────────────────▼────────────────────────────────────────────┐
│                Repository Layer                                 │
│                 /app/repositories/                              │
│  ConfigRepository | ExperimentRepository                       │
│  StrategyConfigRepository ⭐ | DynamicStrategyRepository ⭐     │
│  StrategyExecutionRepository ⭐                                 │
└───────────────────┬────────────────────────────────────────────┘
                    │
┌───────────────────▼────────────────────────────────────────────┐
│                Core v6.0 Integration                            │
│           (通过 Docker 挂载访问 core/src)                      │
│  DatabaseManager | AlphaFactors | BacktestEngine               │
│  StrategyFactory ⭐ | ConfigLoader ⭐ | DynamicCodeLoader ⭐    │
└─────────────────────────────────────────────────────────────────┘
                    │
┌───────────────────▼────────────────────────────────────────────┐
│              TimescaleDB Database                               │
│   (股票数据、策略配置、动态策略、实验结果存储)                 │
│   Tables: strategy_configs ⭐, dynamic_strategies ⭐,           │
│           strategy_executions ⭐                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 三种策略类型架构

```
┌──────────────────────────────────────────────────────────────┐
│                    /api/backtest (统一接口)                   │
└───────────┬──────────────────────────────────────────────────┘
            │
            ├─────► 预定义策略 (Predefined)
            │       strategy_type: "predefined"
            │       ├─> StrategyFactory.create("momentum", config)
            │       └─> 硬编码策略类，性能最优
            │
            ├─────► 配置驱动策略 (Configured)
            │       strategy_type: "config"
            │       ├─> ConfigStrategyAdapter
            │       ├─> StrategyConfigRepository
            │       ├─> strategy_configs 表
            │       └─> StrategyFactory.create_from_config(config_id)
            │
            └─────► 动态代码策略 (Dynamic)
                    strategy_type: "dynamic"
                    ├─> DynamicStrategyAdapter
                    ├─> DynamicStrategyRepository
                    ├─> dynamic_strategies 表
                    ├─> 安全验证 (AST 分析、语法检查)
                    └─> StrategyFactory.create_from_code(strategy_id)
```

### 目录结构

```
backend/
├── app/                        # 主应用目录
│   ├── main.py                 # FastAPI 应用入口
│   ├── core/                   # 核心配置
│   │   ├── config.py           # 环境配置（数据库、CORS 等）
│   │   └── __init__.py
│   ├── api/                    # API 层
│   │   ├── __init__.py         # 路由注册
│   │   ├── error_handler.py    # 全局异常处理
│   │   └── endpoints/          # API 端点实现
│   │       ├── stocks.py       # 股票列表管理
│   │       ├── data.py         # 数据下载与查询
│   │       ├── features.py     # 特征工程
│   │       ├── models.py       # 模型管理
│   │       ├── backtest.py           # 回测引擎（统一接口）
│   │       ├── strategy_configs.py  # 策略配置 API ⭐ v4.0
│   │       ├── dynamic_strategies.py # 动态策略 API ⭐ v4.0
│   │       ├── ml.py                # 机器学习训练
│   │       ├── strategy.py          # 策略管理
│   │       ├── sync.py              # 数据同步
│   │       ├── scheduler.py         # 定时任务
│   │       ├── config.py            # 配置管理
│   │       ├── market.py            # 市场状态
│   │       └── experiment.py        # 自动化实验
│   ├── core_adapters/         # Core v6.0 适配器 ⭐ v4.0
│   │   ├── data_adapter.py            # 数据适配器
│   │   ├── feature_adapter.py         # 特征适配器
│   │   ├── backtest_adapter.py        # 回测适配器
│   │   ├── market_adapter.py          # 市场适配器
│   │   ├── config_strategy_adapter.py # 配置策略适配器 ⭐
│   │   └── dynamic_strategy_adapter.py # 动态策略适配器 ⭐
│   ├── services/               # 业务逻辑层
│   │   ├── data_service.py              # 数据服务
│   │   ├── feature_service.py           # 特征计算服务
│   │   ├── backtest_service.py          # 回测服务
│   │   ├── backtest_executor.py         # 回测执行器
│   │   ├── backtest_data_loader.py      # 回测数据加载
│   │   ├── backtest_result_formatter.py # 回测结果格式化
│   │   ├── database_service.py          # 数据库服务
│   │   ├── ml_training_service.py       # ML 训练服务
│   │   ├── config_service.py            # 配置服务
│   │   ├── stock_list_sync_service.py   # 股票列表同步
│   │   ├── daily_sync_service.py        # 日线数据同步
│   │   ├── realtime_sync_service.py     # 实时数据同步
│   │   ├── sync_status_manager.py       # 同步状态管理
│   │   ├── data_source_manager.py       # 数据源管理
│   │   ├── experiment_service.py        # 实验服务
│   │   ├── experiment_runner.py         # 实验运行器
│   │   ├── batch_manager.py             # 批次管理
│   │   ├── training_task_manager.py     # 训练任务管理
│   │   ├── core_training.py             # Core 训练集成
│   │   ├── model_predictor.py           # 模型预测
│   │   ├── model_ranker.py              # 模型排序
│   │   └── parameter_grid.py            # 参数网格
│   ├── repositories/           # 数据访问层
│   │   ├── base_repository.py              # 基础仓库类
│   │   ├── config_repository.py            # 配置数据访问
│   │   ├── experiment_repository.py        # 实验数据访问
│   │   ├── batch_repository.py             # 批次数据访问
│   │   ├── strategy_config_repository.py   # 策略配置数据访问 ⭐ v4.0
│   │   ├── dynamic_strategy_repository.py  # 动态策略数据访问 ⭐ v4.0
│   │   └── strategy_execution_repository.py # 策略执行记录 ⭐ v4.0
│   ├── strategies/             # 策略模块
│   │   ├── base_strategy.py            # 策略基类
│   │   ├── strategy_manager.py         # 策略管理器
│   │   ├── complex_indicator_strategy.py # 复杂指标策略
│   │   └── ml_model_strategy.py        # ML 模型策略
│   ├── interfaces/             # 接口定义（类型提示）
│   │   ├── sync_interfaces.py          # 同步接口
│   │   ├── ml_interfaces.py            # ML 接口
│   │   ├── backtest_interfaces.py      # 回测接口
│   │   ├── config_interfaces.py        # 配置接口
│   │   └── experiment_interfaces.py    # 实验接口
│   ├── models/                 # 数据模型
│   │   ├── api_response.py     # 统一响应模型
│   │   └── ml_models.py        # ML 模型定义
│   ├── schemas/                # Pydantic 模式（预留）
│   ├── utils/                  # 工具函数
│   │   ├── data_cleaning.py    # 数据清洗
│   │   ├── retry.py            # 重试装饰器
│   │   └── ic_validator.py     # IC 验证器
│   └── __init__.py
├── src/                        # Core 代码挂载点
│   └── (通过 Docker 挂载 ../core/src)
├── Dockerfile                  # Docker 镜像定义
├── requirements.txt            # Python 依赖
├── .dockerignore
└── README.md
```

---

## 核心模块

### 1. API Layer (app/api/)

**职责**: 处理 HTTP 请求，参数验证，调用 Service 层

**主要端点**:

| 端点 | 功能 | 关键路由 |
|------|------|---------|
| `/api/stocks` | 股票列表管理 | GET/POST 股票信息 |
| `/api/data` | 数据下载查询 | POST 下载，GET 查询 |
| `/api/features` | 特征计算 | GET/POST 计算因子 |
| `/api/models` | 模型管理 | POST 训练，GET 预测 |
| `/api/backtest` | 回测引擎（统一接口） | POST 运行回测（支持三种策略类型）|
| **`/api/strategy-configs`** ⭐ | **策略配置管理** | **CRUD 策略配置** |
| **`/api/dynamic-strategies`** ⭐ | **动态策略管理** | **CRUD 动态代码策略** |
| `/api/ml` | ML 训练 | POST 训练任务 |
| `/api/strategy` | 策略管理 | GET 策略列表 |
| `/api/sync` | 数据同步 | POST 触发同步 |
| `/api/scheduler` | 定时任务 | GET/POST 任务管理 |
| `/api/config` | 配置管理 | GET/PUT 配置项 |
| `/api/market` | 市场状态 | GET 交易日历 |
| `/api/experiment` | 自动化实验 | POST 创建实验 |

### 2. Service Layer (app/services/)

**职责**: 业务逻辑实现，调用 Core 模块，管理数据库事务

**核心服务**:

#### 数据服务 (Data Services)
- **DataService**: 数据下载、查询、批量处理
- **DatabaseService**: 数据库连接池、事务管理
- **DataSourceManager**: 多数据源管理（AkShare/Tushare）

#### 特征服务 (Feature Services)
- **FeatureService**: 特征计算、存储、查询

#### 回测服务 (Backtest Services)
- **BacktestService**: 回测流程编排
- **BacktestExecutor**: 回测执行器（调用 Core）
- **BacktestDataLoader**: 数据加载和预处理
- **BacktestResultFormatter**: 结果格式化和可视化

#### 同步服务 (Sync Services)
- **StockListSyncService**: 股票列表同步
- **DailySyncService**: 日线数据同步
- **RealtimeSyncService**: 实时数据同步
- **SyncStatusManager**: 同步状态跟踪

#### ML 服务 (ML Services)
- **MLTrainingService**: ML 训练流程管理
- **TrainingTaskManager**: 训练任务队列管理
- **CoreTraining**: Core 训练模块集成
- **ModelPredictor**: 模型预测服务
- **ModelRanker**: 模型排序和选择

#### 实验服务 (Experiment Services)
- **ExperimentService**: 实验管理
- **ExperimentRunner**: 实验运行器
- **BatchManager**: 批次管理

#### 配置服务 (Config Services)
- **ConfigService**: 系统配置管理

### 3. Repository Layer (app/repositories/)

**职责**: 数据库访问抽象层（Repository 模式）

- **BaseRepository**: 基础 CRUD 操作
- **ConfigRepository**: 配置表访问
- **ExperimentRepository**: 实验表访问
- **BatchRepository**: 批次表访问

### 4. Strategy Layer (app/strategies/)

**职责**: 交易策略封装

- **BaseStrategy**: 策略基类（统一接口）
- **StrategyManager**: 策略注册和管理
- **ComplexIndicatorStrategy**: 复杂技术指标策略
- **MLModelStrategy**: 机器学习模型策略

### 5. Interfaces Layer (app/interfaces/)

**职责**: TypedDict 类型定义，提升代码可维护性

- **sync_interfaces.py**: 同步相关类型
- **ml_interfaces.py**: ML 相关类型
- **backtest_interfaces.py**: 回测相关类型
- **config_interfaces.py**: 配置相关类型
- **experiment_interfaces.py**: 实验相关类型

---

## 数据流

### 典型请求流程

以 "运行回测" 为例：

```
1. 用户请求
   POST /api/backtest/run
   {
     "stock_code": "000001.SZ",
     "start_date": "2024-01-01",
     "end_date": "2024-12-31",
     "strategy": "momentum",
     "initial_capital": 1000000
   }

2. API Layer (backtest.py)
   - 参数验证（Pydantic）
   - 调用 BacktestService

3. Service Layer (backtest_service.py)
   - 调用 BacktestDataLoader 加载数据
   - 调用 BacktestExecutor 执行回测
     └─> 调用 Core 的 BacktestEngine
   - 调用 BacktestResultFormatter 格式化结果

4. Core Integration (core/src/backtest/)
   - BacktestEngine.backtest_long_only()
   - 返回 BacktestResult

5. Response
   {
     "status": "success",
     "data": {
       "total_return": 0.253,
       "sharpe_ratio": 1.85,
       "max_drawdown": -0.125,
       "annual_return": 0.187,
       ...
     }
   }
```

### 数据同步流程

```
定时任务触发
    │
    ▼
POST /api/sync/start
    │
    ▼
SyncStatusManager
    │
    ▼
StockListSyncService
    │
    ▼
Core DataFetcher (AkShare)
    │
    ▼
TimescaleDB (stock_info 表)
    │
    ▼
DailySyncService
    │
    ▼
Core DataFetcher (批量下载)
    │
    ▼
TimescaleDB (stock_daily 表)
    │
    ▼
SyncStatusManager (更新状态)
```

---

## 设计模式

### 1. 分层架构 (Layered Architecture)
- **目的**: 职责分离，提高可维护性
- **实现**: API → Service → Repository → Core

### 2. Repository 模式
- **目的**: 数据访问抽象
- **实现**: `BaseRepository` + 具体仓库类

### 3. 依赖注入 (Dependency Injection)
- **目的**: 降低耦合，便于测试
- **实现**: FastAPI 的 `Depends()`

```python
from fastapi import Depends
from app.services.data_service import DataService

@router.post("/download")
async def download_data(
    data_service: DataService = Depends()
):
    return await data_service.download_stock_data(...)
```

### 4. 策略模式 (Strategy Pattern)
- **目的**: 策略算法可插拔
- **实现**: `BaseStrategy` + 具体策略类

### 5. 统一响应模式
- **目的**: 一致的 API 响应格式
- **实现**: `ApiResponse` 模型

```python
class ApiResponse(BaseModel):
    status: str  # "success" | "error"
    data: Any
    message: Optional[str]
    error: Optional[str]
```

### 6. 异步编程
- **目的**: 高并发性能
- **实现**: FastAPI 的 `async/await`

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

1. **代码复用**: 避免重复实现分析逻辑
2. **单一来源**: Core 作为唯一的分析逻辑实现
3. **独立开发**: Backend 和 Core 可以独立迭代
4. **灵活部署**: 可以单独部署 Backend 或与 Core 联合部署

---

## 性能优化

### 1. 异步 I/O
- FastAPI 原生支持异步请求处理
- 数据库查询使用异步驱动（asyncpg）
- 文件 I/O 使用 aiofiles

### 2. 连接池
- 数据库连接池（SQLAlchemy async engine）
- HTTP 客户端连接池（httpx）

### 3. 缓存
- 配置数据内存缓存
- 股票列表缓存（定期刷新）
- API 响应缓存（可选）

### 4. 批量处理
- 批量数据下载
- 批量数据库插入
- 批量特征计算

### 5. 后台任务
- 长时间运行的任务（训练、回测）使用后台任务
- 任务状态跟踪和进度更新

---

## 可扩展性

### 1. 水平扩展
- 无状态设计，支持多实例部署
- 使用负载均衡器（Nginx/HAProxy）
- 共享 TimescaleDB 数据库

### 2. 垂直扩展
- 增加��器资源（CPU/内存）
- 数据库性能优化（索引、分区）

### 3. 微服务化（未来）
- 数据服务独立
- 训练服务独立
- 回测服务独立

---

## 安全性

### 1. CORS 配置
- 允许的源站配置
- 预检请求处理

### 2. 输入验证
- Pydantic 自动验证
- 自定义验证器

### 3. 错误处理
- 全局异常处理器
- 敏感信息过滤
- 详细日志记录

### 4. 数据库安全
- 参数化查询（防止 SQL 注入）
- 最小权限原则
- 密码环境变量存储

---

## 监控与日志

### 1. 日志系统
- 使用 loguru 统一日志
- 日志级别：DEBUG/INFO/WARNING/ERROR
- 日志格式：时间、级别、模块、消息

### 2. 健康检查
- `/health` 端点监控服务状态
- 数据库连接检查
- Core 模块可用性检查

### 3. 性能指标（未来）
- 请求耗时统计
- API 调用量统计
- 错误率监控

---

## 技术栈

| 类别 | 技术 | 版本 |
|------|------|------|
| **Web 框架** | FastAPI | 0.104+ |
| **ASGI 服务器** | Uvicorn | 0.24+ |
| **数据验证** | Pydantic | 2.0+ |
| **数据库** | TimescaleDB | - |
| **ORM** | SQLAlchemy | 2.0+ (async) |
| **日志** | Loguru | 0.7+ |
| **HTTP 客户端** | httpx | 0.25+ |
| **数据处理** | Pandas, NumPy | - |
| **Core 集成** | 直接挂载 | - |

---

## 下一步

1. **API 文档**: 查看 [API Reference](../api_reference/README.md) 了解具体接口
2. **用户指南**: 查看 [User Guide](../user_guide/quick_start.md) 学习使用
3. **开发指南**: 查看 [Developer Guide](../developer_guide/contributing.md) 参与开发
4. **部署指南**: 查看 [Deployment](../deployment/docker.md) 部署服务

---

**维护团队**: Quant Team
**文档版本**: v1.0.0
**最后更新**: 2026-02-01
