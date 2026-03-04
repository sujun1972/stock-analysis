# 🏗️ 系统架构文档

## 项目概述

A股AI量化交易系统 - 完整的前后端分离架构

## 技术栈

### Backend（后端）
- **API框架**: FastAPI (高性能异步)
- **数据库**: PostgreSQL 16 + TimescaleDB
- **任务队列**: Celery 5.3 + Redis (异步回测)
- **数据处理**: Pandas, NumPy
- **机器学习**: LightGBM, scikit-learn
- **技术分析**: TA-Lib (可选)
- **数据源**: AkShare, Tushare, yfinance
- **容器化**: Docker + Docker Compose
- **监控**: Flower (Celery任务监控)

### Frontend（前端 - 待实现）
- **框架**: React / Vue / Next.js (待选择)
- **状态管理**: Redux / Zustand / Pinia
- **UI库**: Ant Design / Material-UI
- **图表**: ECharts / Plotly

### Infrastructure（基础设施）
- **容器编排**: Docker Compose
- **数据库**: TimescaleDB (时序数据优化)
- **消息队列**: Redis (Celery broker + result backend)
- **反向代理**: Nginx (可选)
- **缓存**: Redis (共享实例)

---

## 项目结构

```
stock-analysis/
├── backend/                    # FastAPI后端服务
│   ├── app/                   # FastAPI应用
│   │   ├── api/endpoints/    # API端点实现
│   │   │   ├── stocks.py      # 股票列表API
│   │   │   ├── data.py        # 数据下载和查询API
│   │   │   ├── features.py    # 特征工程API
│   │   │   ├── models.py      # 模型训练和预测API
│   │   │   └── backtest.py    # 回测API (支持同步/异步)
│   │   ├── core/             # 核心配置
│   │   │   ├── config.py     # 应用配置
│   │   │   └── migrations.py # 数据库迁移管理器
│   │   ├── tasks/            # Celery异步任务
│   │   │   └── backtest_tasks.py  # 异步回测任务
│   │   ├── models/           # 数据库模型（暂未使用）
│   │   ├── schemas/          # Pydantic数据模型
│   │   ├── services/         # 业务逻辑层
│   │   │   ├── data_service.py
│   │   │   ├── database_service.py
│   │   │   └── feature_service.py
│   │   ├── celery_app.py     # Celery应用配置
│   │   └── main.py           # 应用入口
│   ├── migrations/           # 数据库迁移脚本
│   │   └── V012__add_celery_task_support.sql
│   ├── src/                  # Docker挂载目录 (core/src → /app/src)
│   ├── Dockerfile            # Docker镜像定义
│   ├── requirements.txt      # Backend Python依赖
│   └── README.md
│
├── core/                      # 核心分析代码
│   ├── src/                  # 核心业务逻辑（被Backend挂载）
│   │   ├── database/         # 数据库管理（TimescaleDB）
│   │   ├── features/         # 特征工程
│   │   │   ├── technical_indicators.py
│   │   │   ├── alpha_factors.py
│   │   │   └── feature_transformer.py
│   │   ├── models/           # 机器学习模型
│   │   │   ├── lightgbm_model.py
│   │   │   ├── gru_model.py
│   │   │   └── model_trainer.py
│   │   ├── backtest/         # 回测引擎
│   │   │   ├── backtest_engine.py
│   │   │   ├── strategy.py
│   │   │   └── performance_analyzer.py
│   │   ├── config/           # 配置
│   │   ├── data_fetcher.py   # 数据获取
│   │   └── main.py
│   ├── scripts/              # 辅助脚本
│   │   ├── download_data.py          # CSV数据下载
│   │   ├── download_data_to_db.py    # 数据库数据下载
│   │   └── test_akshare.py           # 数据源测试
│   └── tests/                # 测试脚本
│       ├── test_phase1_data_pipeline.py
│       ├── test_phase2_features.py
│       ├── test_phase3_models.py
│       └── test_phase4_backtest.py
│
├── frontend/                  # 前端服务（待创建）
│   ├── src/
│   │   ├── components/       # React组件
│   │   ├── pages/            # 页面
│   │   ├── services/         # API调用
│   │   └── store/            # 状态管理
│   ├── public/
│   └── package.json
│
├── data/                      # 数据存储
│   ├── timescaledb/          # TimescaleDB数据卷
│   ├── models/               # 训练好的模型
│   ├── results/              # 回测结果
│   └── notebooks/            # Jupyter notebooks
│
├── docs/                      # 项目文档
│   ├── ARCHITECTURE.md       # 本文档（系统架构）
│   ├── DATABASE_USAGE.md     # 数据库使用指南
│   └── FINAL_STRUCTURE.md    # 最终项目结构
│
├── db_init/                   # 数据库初始化脚本
├── docker-compose.yml         # Docker Compose配置
├── .env.example               # 环境变量示例
├── requirements.txt           # Python依赖（本地开发）
├── QUICKSTART.md              # 快速开始指南
├── TROUBLESHOOTING.md         # 故障排除指南
└── README.md                  # 项目README
```

**关键设计**：
- `core/src/` 通过 Docker 挂载到 `backend` 容器的 `/app/src`
- Backend 直接导入 `from src.xxx import yyy`
- 保持代码单一来源（DRY原则）

---

## 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                         用户浏览器                            │
│                     (Future Frontend)                       │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/HTTPS
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                      Backend API                            │
│                     (FastAPI 8000)                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  API Routes                                         │   │
│  │  • /api/stocks      - 股票列表                      │   │
│  │  • /api/data        - 数据管理                      │   │
│  │  • /api/features    - 特征工程                      │   │
│  │  • /api/models      - 模型管理                      │   │
│  │  • /api/backtest    - 回测                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Business Logic (core/src/ via Docker mount)        │   │
│  │  • DatabaseManager  - 数据库操作                    │   │
│  │  • TechnicalIndicators - 技术指标                   │   │
│  │  • AlphaFactors     - Alpha因子                     │   │
│  │  • LightGBMModel    - AI模型                        │   │
│  │  • BacktestEngine   - 回测引擎                      │   │
│  └─────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ PostgreSQL Protocol
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                   TimescaleDB (5432)                        │
│                                                             │
│  Tables:                                                    │
│  • stock_info         - 股票基本信息                        │
│  • stock_daily        - 日线数据 (时序优化)                 │
│  • stock_features     - 技术指标和因子                      │
│  • stock_predictions  - 模型预测结果                        │
│  • backtest_results   - 回测绩效                           │
└─────────────────────────────────────────────────────────────┘

External Data Sources:
┌──────────┐  ┌──────────┐  ┌──────────┐
│ AkShare  │  │ Tushare  │  │ yfinance │
└──────────┘  └──────────┘  └──────────┘
      ↓             ↓             ↓
      └─────────────┴─────────────┘
                    │
                    ↓
              Backend Data
               Downloader
```

---

## 数据流

### 1. 数据下载流程

```
User Request (Frontend)
    ↓
POST /api/data/download
    ↓
Backend creates download task
    ↓
Fetch data from AkShare/Tushare
    ↓
Save to TimescaleDB (stock_daily)
    ↓
Return task status
```

### 2. 特征计算流程

```
User Request
    ↓
POST /api/features/calculate/{code}
    ↓
Load raw data from TimescaleDB
    ↓
Calculate technical indicators (36)
    ↓
Calculate alpha factors (51)
    ↓
Transform features (38)
    ↓
Save to TimescaleDB (stock_features)
    ↓
Return success
```

### 3. 模型训练流程

```
User Request
    ↓
POST /api/models/train
    ↓
Load features from TimescaleDB
    ↓
Prepare training data
    ↓
Train LightGBM/GRU model
    ↓
Evaluate (IC, Rank IC)
    ↓
Save model file
    ↓
Return metrics
```

### 4. 回测流程

```
User Request
    ↓
POST /api/backtest/run
    ↓
Load historical data
    ↓
Generate signals (model predictions)
    ↓
Simulate trading (T+1)
    ↓
Calculate performance metrics
    ↓
Save to TimescaleDB (backtest_results)
    ↓
Return result
```

---

## API设计

### RESTful API规范

**基础URL**: `http://localhost:8000/api`

| 端点 | 方法 | 描述 | 请求参数 | 响应 |
|------|------|------|----------|------|
| `/stocks/list` | GET | 获取股票列表 | market, status, skip, limit | {total, data[]} |
| `/stocks/{code}` | GET | 获取单只股票 | code | {code, name, ...} |
| `/data/daily/{code}` | GET | 获取日线数据 | code, start_date, end_date | {data[]} |
| `/data/download` | POST | 下载数据 | {codes, years} | {task_id} |
| `/features/{code}` | GET | 获取特征 | code, feature_type | {data[]} |
| `/features/calculate/{code}` | POST | 计算特征 | code, feature_types | {status} |
| `/models/train` | POST | 训练模型 | {model_type, codes} | {task_id} |
| `/models/predict/{code}` | GET | 获取预测 | code, model_name | {prediction} |
| `/backtest/run` | POST | 运行回测 | {strategy, params} | {task_id} |
| `/backtest/result/{id}` | GET | 获取回测结果 | task_id | {metrics, curve} |

---

## 数据库设计

### 表结构

#### 1. stock_info (股票基本信息)
```sql
CREATE TABLE stock_info (
    code VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100),
    market VARCHAR(20),
    list_date DATE,
    industry VARCHAR(100),
    area VARCHAR(100),
    status VARCHAR(20)
);
```

#### 2. stock_daily (日线数据 - 时序优化)
```sql
CREATE TABLE stock_daily (
    code VARCHAR(20),
    date DATE,
    open DECIMAL(10,2),
    high DECIMAL(10,2),
    low DECIMAL(10,2),
    close DECIMAL(10,2),
    volume BIGINT,
    PRIMARY KEY (code, date)
);

-- TimescaleDB时序优化
SELECT create_hypertable('stock_daily', 'date');
```

#### 3. stock_features (特征数据)
```sql
CREATE TABLE stock_features (
    code VARCHAR(20),
    date DATE,
    feature_type VARCHAR(50),
    feature_data JSONB,
    PRIMARY KEY (code, date, feature_type)
);
```

详见：[DATABASE_USAGE.md](DATABASE_USAGE.md)

---

## 部署架构

### Development（开发环境）

```bash
# 启动所有服务
docker-compose up -d

# 服务列表
- backend:     http://localhost:8000
- timescaledb: localhost:5432
- frontend:    http://localhost:3000 (待实现)
```

### Production（生产环境）

```
Internet
    ↓
Nginx (80/443)
    ↓
    ├── / → Frontend (React SPA)
    └── /api → Backend (FastAPI)
             ↓
        TimescaleDB
```

**生产环境配置：**
1. Nginx反向代理
2. HTTPS证书（Let's Encrypt）
3. 环境变量加密
4. 数据库备份
5. 日志收集
6. 监控告警

---

## 安全考虑

### 1. API安全
- [ ] JWT认证
- [ ] CORS配置
- [ ] API限流
- [ ] 输入验证

### 2. 数据库安全
- [x] 强密码
- [x] 网络隔离
- [ ] SSL连接
- [x] 备份策略

### 3. Docker安全
- [x] 非root用户
- [x] 资源限制
- [ ] 镜像扫描
- [ ] 网络隔离

---

## 性能优化

### Backend
- [ ] 数据库连接池
- [ ] Redis缓存
- [ ] 异步任务队列（Celery）
- [x] TimescaleDB时序优化

### Frontend
- [ ] 代码分割
- [ ] 懒加载
- [ ] CDN静态资源
- [ ] Service Worker缓存

---

## 开发流程

### 1. 添加新API端点

```bash
# 1. 创建endpoint
vim backend/app/api/endpoints/my_feature.py

# 2. 注册路由
vim backend/app/api/__init__.py

# 3. 重启服务
docker-compose restart backend

# 4. 测试
curl http://localhost:8000/api/my-feature/test
```

### 2. 添加数据库表

```bash
# 1. 修改数据库初始化脚本
vim core/src/database/db_manager.py

# 2. 重新初始化
python -c "from core.src.database.db_manager import DatabaseManager; db = DatabaseManager(); db.init_database()"
```

### 3. 前后端联调

```bash
# 1. 启动backend
docker-compose up -d backend

# 2. 启动frontend (开发服务器)
cd frontend
npm run dev

# 3. 前端调用API
fetch('http://localhost:8000/api/stocks/list')
```

---

## 监控和日志

### Backend日志
```bash
# 查看backend日志
docker-compose logs -f backend

# 进入backend容器
docker exec -it stock_backend bash
```

### 数据库日志
```bash
# 查看数据库日志
docker-compose logs -f timescaledb

# 连接数据库
docker exec -it stock_timescaledb psql -U stock_user -d stock_analysis
```

---

## 未来规划

### Phase 1: Backend完善 ✅
- [x] FastAPI基础架构
- [x] Docker容器化
- [ ] 集成旧代码到API
- [ ] 单元测试

### Phase 2: Frontend开发 🔜
- [ ] 选择前端框架
- [ ] 设计UI/UX
- [ ] 实现主要页面
- [ ] 前后端联调

### Phase 3: 功能增强 🔜
- [ ] 用户认证系统
- [ ] 实时数据推送（WebSocket）
- [ ] 策略回测可视化
- [ ] 模型训练监控

### Phase 4: 生产部署 🔜
- [ ] CI/CD流水线
- [ ] 生产环境部署
- [ ] 性能优化
- [ ] 监控告警

---

## 相关文档

- [快速开始指南](../QUICKSTART.md)
- [故障排除指南](../TROUBLESHOOTING.md)
- [数据库使用指南](DATABASE_USAGE.md)
- [Backend README](../backend/README.md)
- [Core README](../core/README.md)

---

**最后更新：** 2026-01-20

**系统状态：** ✅ Backend已部署，Frontend待开发
