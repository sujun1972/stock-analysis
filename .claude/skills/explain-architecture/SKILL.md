---
name: explain-architecture
description: 解释项目架构、模块依赖、数据流和技术栈（适合新人入职和项目理解）
user-invocable: true
disable-model-invocation: false
---

# 项目架构解释技能

你是一个架构师和技术导师，负责向新成员清晰地解释 A股AI量化交易系统的架构和设计。

## 任务目标

提供全面的项目架构讲解，包括：

1. **项目概览**
   - 系统定位和核心功能
   - 技术栈选型理由
   - 项目目录结构

2. **架构设计**
   - 前后端分离架构
   - 数据流向
   - 模块划分原则

3. **核心模块详解**
   - Backend (FastAPI)
   - Core (分析引擎)
   - Frontend (Next.js)
   - Database (TimescaleDB)

4. **开发指南**
   - 如何添加新功能
   - 代码规范
   - 最佳实践

## 解释内容

### 第一部分：项目概览

#### 系统定位

```
================================================================================
                    A股AI量化交易系统
================================================================================

这是一个完整的量化交易分析系统，集成以下功能：

✅ 数据获取
   - 从 AkShare 免费获取A股数据
   - 存储到 TimescaleDB 时序数据库
   - 支持增量更新和历史回溯

✅ 特征工程
   - 36个技术指标（MA, RSI, MACD, BOLL等）
   - 51个Alpha因子（动量、波动率、成交量等）
   - 38个特征转换（多时间尺度、OHLC比率等）
   - 总计 125+ 特征

✅ AI模型
   - LightGBM 梯度提升模型
   - GRU 深度学习模型（可选）
   - 模型评估（IC, Rank IC, R²）

✅ 策略回测
   - T+1 交易模拟
   - 完整的绩效分析（夏普比率、最大回撤等）
   - 多种选股策略支持

✅ Web API
   - FastAPI 后端服务
   - RESTful API 设计
   - 异步任务处理

✅ 前端界面
   - Next.js + TypeScript
   - 数据可视化
   - 交互式分析
   - Admin管理后台

✅ 异步任务管理
   - Celery + Redis 分布式任务队列
   - 支持数据同步、AI分析、回测等长时间任务
   - 实时进度跟踪和状态更新
   - 全局任务面板（跨页面持久化）

✅ LLM调用日志
   - 记录所有AI模型调用（DeepSeek/Gemini/OpenAI）
   - Tokens消耗和成本追踪
   - 调用历史和性能分析
   - Admin后台可视化查看
```

#### 技术栈选型

| 技术 | 选择 | 理由 |
|------|------|------|
| **Backend** | FastAPI | 高性能异步、自动生成API文档、类型验证 |
| **Database** | PostgreSQL + TimescaleDB | 时序数据优化、查询速度提升5-120倍 |
| **Frontend** | Next.js 14 | SSR/SSG支持、App Router、开发体验好 |
| **ML框架** | LightGBM | 速度快、内存效率高、适合表格数据 |
| **数据处理** | Pandas + NumPy | 生态成熟、向量化操作高效 |
| **任务队列** | Celery + Redis | 异步任务处理、分布式锁、进度跟踪 |
| **状态管理** | Zustand | React状态管理、任务队列持久化 |
| **部署** | Docker Compose | 一键启动、环境隔离、易于维护 |

### 第二部分：项目结构详解

通过实际查看项目结构来解释：

```bash
# 查看项目根目录
tree -L 2 -I 'node_modules|stock_env|__pycache__|.git|data' /Volumes/MacDriver/stock-analysis
```

**关键目录说明：**

```
stock-analysis/
│
├── backend/                 # FastAPI 后端服务
│   ├── app/                # FastAPI 应用
│   │   ├── api/endpoints/  # API 路由处理器
│   │   ├── services/       # 业务逻辑层
│   │   └── main.py         # 应用入口
│   └── Dockerfile          # 后端镜像
│
├── core/                    # 核心分析引擎（核心业务逻辑）
│   ├── src/                # 源代码（被 backend 挂载）
│   │   ├── database/       # 数据库管理（TimescaleDB操作）
│   │   ├── data_pipeline/  # 数据流水线
│   │   │   ├── data_loader.py      # 数据加载器
│   │   │   ├── feature_engineer.py # 特征工程
│   │   │   ├── data_cleaner.py     # 数据清洗
│   │   │   ├── data_splitter.py    # 数据分割
│   │   │   └── feature_cache.py    # 特征缓存
│   │   ├── features/       # 特征计算（遗留，被 data_pipeline 替代）
│   │   ├── models/         # AI 模型
│   │   ├── backtest/       # 回测引擎
│   │   └── config/         # 配置管理
│   ├── scripts/            # 辅助脚本
│   └── tests/              # 60+ 单元测试
│
├── frontend/               # Next.js 前端（开发中）
│   ├── src/app/           # App Router 页面
│   ├── src/components/    # React 组件
│   └── src/lib/           # API 客户端
│
├── data/                   # 数据存储
│   ├── timescaledb/       # 数据库数据卷
│   ├── models/            # 训练好的模型
│   └── results/           # 回测结果
│
├── docs/                   # 项目文档
│   ├── ARCHITECTURE.md     # 架构文档
│   └── DATABASE_USAGE.md   # 数据库使用指南
│
└── docker-compose.yml      # 服务编排配置
```

### 第三部分：核心设计原则

#### 1. 代码复用原则

**关键设计：`core/src` 挂载机制**

```yaml
# docker-compose.yml
services:
  backend:
    volumes:
      - ./backend:/app          # Backend 代码
      - ./core/src:/app/src     # 核心代码挂载为 src/
      - ./data:/data            # 数据目录
```

**好处：**
- ✅ 核心代码单一来源（DRY原则）
- ✅ Backend 容器内直接使用 `from src.xxx import yyy`
- ✅ 本地脚本使用 `from core.src.xxx import yyy`
- ✅ 避免代码重复和不一致

#### 2. 模块化设计

**数据流水线模块化：**

```python
# 旧设计（单体）
class DataPipeline:
    def load_data(self): ...
    def engineer_features(self): ...
    def clean_data(self): ...
    def split_data(self): ...

# 新设计（模块化）
DataLoader       # 专注数据加载
FeatureEngineer  # 专注特征工程
DataCleaner      # 专注数据清洗
DataSplitter     # 专注数据分割
FeatureCache     # 专注缓存管理
```

**好处：**
- ✅ 职责单一，易于测试
- ✅ 可独立复用
- ✅ 易于维护和扩展

#### 3. 依赖注入模式

```python
# 推荐的依赖注入方式
class FeatureEngineer:
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}

# 使用时注入配置
engineer = FeatureEngineer(config={'ma_periods': [5, 10, 20]})
```

**好处：**
- ✅ 便于测试（可注入 Mock 对象）
- ✅ 配置灵活
- ✅ 解耦依赖

### 第四部分：数据流详解

```
用户请求 → Backend API → Core模块 → Database
   ↓           ↓            ↓          ↓
Browser   FastAPI      业务逻辑   TimescaleDB
```

#### 完整数据流示例：下载股票数据

```
1. 用户发起请求
   POST /api/data/download
   Body: {"stock_codes": ["000001"], "years": 5}

   ↓

2. Backend 接收请求
   backend/app/api/endpoints/data.py
   - 验证请求参数
   - 创建异步任务
   - 返回 task_id

   ↓

3. Core 模块处理
   core/src/data_fetcher.py
   - 调用 AkShare API
   - 获取原始数据

   ↓

4. 数据存储
   core/src/database/db_manager.py
   - 存储到 TimescaleDB
   - stock_daily 表（时序优化）

   ↓

5. 返回结果
   {"status": "completed", "records": 1234}
```

#### 完整数据流示例：特征计算

```
1. 数据加载
   DataLoader.load_data(code)
   - 从 TimescaleDB 读取日线数据
   - 转换为 Pandas DataFrame

   ↓

2. 特征工程
   FeatureEngineer.calculate_all_features(df)
   - 计算技术指标（36个）
   - 计算 Alpha 因子（51个）
   - 特征转换（38个）

   ↓

3. 数据清洗
   DataCleaner.clean(df)
   - 移除缺失值
   - 截断极端值

   ↓

4. 数据分割
   DataSplitter.split(df)
   - 时间序列分割
   - 特征缩放
   - 样本平衡

   ↓

5. 模型训练/预测
   LightGBMModel.train(X_train, y_train)

   ↓

6. 回测验证
   BacktestEngine.backtest(signals, prices)
```

### 第五部分：数据库设计

通过查询实际数据库结构来解释：

```bash
# 查看所有表
docker-compose exec timescaledb psql -U stock_user -d stock_analysis -c "
SELECT tablename, schemaname
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
"

# 查看 stock_daily 表结构
docker-compose exec timescaledb psql -U stock_user -d stock_analysis -c "
\d stock_daily
"
```

**核心表说明：**

| 表名 | 用途 | 时序优化 | 索引 |
|------|------|----------|------|
| `stock_info` | 股票基本信息 | ❌ | code (PK) |
| `stock_daily` | 日线数据 | ✅ | (code, date) |
| `stock_features` | 特征数据 | ✅ | (code, date, type) |
| `llm_call_logs` | LLM调用日志 | ✅ | (call_id, start_time) |
| `llm_pricing_config` | LLM定价配置 | ❌ | (provider, model) |

**TimescaleDB 优化：**

```sql
-- 创建 Hypertable（时序优化表）
SELECT create_hypertable('stock_daily', 'date');

-- 效果：
-- - 自动分区管理
-- - 查询速度提升 5-120 倍
-- - 支持时间范围高效查询
```

### 第六部分：API 设计原则

阅读实际 API 代码来解释：

```bash
# 查看 API 端点定义
cat backend/app/api/endpoints/stocks.py | head -50
```

**RESTful 设计规范：**

| HTTP方法 | 端点 | 用途 | 示例 |
|---------|------|------|------|
| GET | `/api/stocks/list` | 获取列表 | 分页、过滤 |
| GET | `/api/stocks/{code}` | 获取单个 | 返回详情 |
| POST | `/api/data/download` | 创建资源 | 异步任务 |
| PUT | `/api/stocks/{code}` | 更新资源 | 完整更新 |
| DELETE | `/api/stocks/{code}` | 删除资源 | 软删除 |

**响应格式统一：**

```json
// 成功响应
{
  "status": "success",
  "data": { ... },
  "message": "操作成功"
}

// 错误响应
{
  "status": "error",
  "error": "ValidationError",
  "message": "股票代码格式不正确",
  "details": { ... }
}

// 分页响应
{
  "total": 3500,
  "page": 1,
  "page_size": 20,
  "data": [ ... ]
}
```

### 第七部分：异步任务管理系统

#### 系统架构

```
Admin Frontend (React)
    ↓ (提交任务)
Backend API (FastAPI)
    ↓ (创建 Celery 任务)
Celery Worker
    ↓ (执行任务)
Redis (任务队列 + 结果存储)
    ↓ (轮询状态)
Frontend 任务轮询器 (useTaskPolling)
    ↓ (更新 UI)
Zustand Store (全局状态)
```

#### 核心组件

**后端：**
- `backend/app/celery_app.py` - Celery 应用配置
- `backend/app/tasks/sync_tasks.py` - 数据同步任务
- `backend/app/tasks/sentiment_tasks.py` - 情绪数据任务
- `backend/app/tasks/ai_strategy_tasks.py` - AI策略生成任务
- `backend/app/tasks/backtest_tasks.py` - 回测任务

**前端（Admin）：**
- `admin/stores/task-store.ts` - Zustand 任务状态管理
- `admin/hooks/use-task-polling.ts` - 全局任务轮询 Hook
- `admin/components/TaskStatusIcon.tsx` - 头部任务图标
- `admin/components/TaskPanel.tsx` - 任务面板

#### 工作流程示例：日线数据同步

```typescript
// 1. 用户点击"同步"按钮
const handleDailySync = async () => {
  // 调用 API 启动异步任务
  const response = await apiClient.syncDailyBatch({
    start_date: '2024-01-01',
    end_date: '2024-12-31'
  })

  // 2. 获取 task_id
  const { task_id, display_name } = response.data

  // 3. 添加到全局任务队列
  addTaskToQueue(task_id, 'sync.daily_batch', display_name, 'sync')

  // 4. 显示 Toast 提示
  toast.success('任务已启动', {
    description: '日线数据批量同步任务已在后台执行'
  })
}

// 5. useTaskPolling 自动轮询任务状态（每3秒）
pollTaskStatus(task_id)
  ↓
GET /api/sentiment/sync/status/{task_id}
  ↓
返回: { status: 'PROGRESS', progress: 45, ... }
  ↓
更新 Zustand Store
  ↓
TaskStatusIcon 显示进度（旋转图标 + 徽章数量）
  ↓
任务完成后显示 Toast 通知
  ↓
3秒后自动从任务列表移除
```

#### 关键特性

**1. 分布式锁（防止并发执行）**
```python
# backend/app/tasks/sync_tasks.py
with redis_lock.acquire(lock_key, timeout=3600, blocking=False):
    if not acquired:
        return {"status": "locked", "message": "已有同步任务正在进行"}
    # 执行任务...
```

**2. 进度报告**
```python
# 每10只股票更新一次进度
self.update_state(
    state='PROGRESS',
    meta={
        'current': i + 1,
        'total': total,
        'percent': percent,
        'status': f'同步中... ({i + 1}/{total})'
    }
)
```

**3. 任务自动发现与恢复**
```typescript
// admin/hooks/use-task-polling.ts
// 应用启动时恢复正在执行的任务
async function restoreActiveTasks(silent = false) {
  const response = await apiClient.get('/api/sentiment/tasks/active')

  tasks.forEach((task) => {
    if (!taskStore.tasks.has(task.task_id)) {
      taskStore.addTask(task)
      // 发现新任务时通知用户
      if (silent) {
        toast.info('检测到新任务', { description: task.display_name })
      }
    }
  })

  startPolling()
}

// 定期检查后端新任务（如定时任务启动）
startTaskDiscovery() // 每30秒检查一次
```

**4. 跨页面持久化**
- 使用 Zustand Store 管理全局状态
- 任务轮询在 Layout 层级运行
- 用户切换页面时任务继续执行和显示

**5. 任务分类**
```typescript
type TaskType = 'sync' | 'sentiment' | 'ai_analysis' | 'backtest' | 'premarket'

// 每种类型有不同的图标和颜色
getTaskTypeIcon(type: TaskType) {
  switch (type) {
    case 'sync': return <DatabaseIcon />
    case 'sentiment': return <ActivityIcon />
    case 'ai_analysis': return <BrainCircuitIcon />
    case 'backtest': return <TrendingUpIcon />
    ...
  }
}
```

#### Docker Compose 配置

```yaml
# Celery Worker（执行任务）
celery_worker:
  command: celery -A app.celery_app worker --loglevel=info --concurrency=2
  environment:
    - PYTHONPATH=/app/core:/app
  volumes:
    - ./backend/app:/app/app:rw
    - ./core:/app/core:ro

# Celery Beat（定时任务调度）
celery_beat:
  command: celery -A app.celery_app beat --loglevel=info

# Flower（任务监控面板）
flower:
  command: celery -A app.celery_app flower --port=5555
  ports:
    - "5555:5555"
```

### 第八部分：开发工作流

#### 添加新功能的标准流程

**场景：添加新的技术指标 ATR (平均真实波幅)**

```
1. 修改核心代码
   📝 编辑: core/src/data_pipeline/feature_engineer.py

   def calculate_atr(self, df, period=14):
       """计算 ATR 指标"""
       # 实现代码...

2. 添加单元测试
   📝 编辑: core/tests/test_feature_engineer.py

   def test_calculate_atr(self):
       # 测试代码...

3. 运行测试验证
   🧪 python3 core/tests/test_feature_engineer.py

4. 更新 API（如需要）
   📝 编辑: backend/app/api/endpoints/features.py

5. 提交代码
   📤 git commit -m "feat: add ATR indicator"

6. 更新文档
   📝 更新 README.md 和相关文档
```

#### 调试技巧

```python
# 1. 使用 loguru 日志
from loguru import logger

logger.debug(f"数据形状: {df.shape}")
logger.info(f"特征数量: {len(feature_cols)}")
logger.warning(f"缺失值: {df.isna().sum()}")
logger.error(f"计算失败: {e}")

# 2. 数据检查点
print(df.head())
print(df.describe())
print(df.info())

# 3. 性能分析
import time
start = time.time()
# ... 操作 ...
print(f"耗时: {time.time() - start:.2f}s")
```

### 第九部分：常见问题解答

**Q1: 为什么要用 TimescaleDB 而不是普通 PostgreSQL？**

A: TimescaleDB 是 PostgreSQL 的时序扩展，对时间序列数据进行了优化：
- 自动分区管理（按时间）
- 查询速度提升 5-120 倍
- 支持连续聚合（实时统计）
- 完全兼容 PostgreSQL

**Q2: 为什么 Backend 要挂载 core/src？**

A:
- 避免代码重复
- 核心逻辑统一维护
- Backend 专注于 API 服务
- 本地脚本和 API 使用同一份代码

**Q3: 如何理解依赖注入模式？**

A:
```python
# 不推荐：硬编码依赖
class FeatureEngineer:
    def __init__(self):
        self.db = DatabaseManager()  # 硬编码

# 推荐：注入依赖
class FeatureEngineer:
    def __init__(self, db=None):
        self.db = db or DatabaseManager()  # 可注入
```

**Q4: 特征缓存如何工作？**

A:
```python
# FeatureCache 自动检测配置变化
cache = FeatureCache()

# 第一次计算，保存缓存
df_features = engineer.calculate_all(df)
cache.save(stock_code, df_features, config)

# 第二次，如果配置未变，直接加载缓存
df_cached = cache.load(stock_code, config)  # 秒级返回

# 如果配置改变（如新增指标），缓存自动失效
```

### 第十部分：性能优化策略

#### 1. 数据库查询优化

```python
# ❌ 不好：N+1 查询
for code in stock_codes:
    df = db.query(f"SELECT * FROM stock_daily WHERE code = '{code}'")

# ✅ 好：批量查询
codes_str = "','".join(stock_codes)
df = db.query(f"SELECT * FROM stock_daily WHERE code IN ('{codes_str}')")
```

#### 2. 向量化计算

```python
# ❌ 不好：循环计算
returns = []
for i in range(len(df)):
    ret = df['close'].iloc[i] / df['close'].iloc[i-1] - 1
    returns.append(ret)

# ✅ 好：向量化
returns = df['close'].pct_change()
# 速度提升 10-100 倍
```

#### 3. 缓存策略

```python
# 使用 FeatureCache
# - 避免重复计算
# - 特征版本管理
# - 自动失效机制
```

### 第十一部分：学习路径建议

**对于新人：**

```
第1周：熟悉项目
├─ 阅读 README.md 和 QUICKSTART.md
├─ 运行测试脚本验证环境
├─ 理解项目目录结构
└─ 运行 /explain-architecture 技能（本技能）

第2周：理解数据流
├─ 下载数据（/download-stock-data）
├─ 计算特征（/calculate-features）
├─ 查看数据库（/db-health-check）
└─ 运行回测（/quick-backtest）

第3周：代码深入
├─ 阅读核心模块源码
├─ 运行单元测试（/run-all-tests）
├─ 修改参数重新测试
└─ 尝试添加小功能

第4周：独立开发
├─ 添加新的技术指标
├─ 实现新的 API 端点
├─ 优化性能
└─ 编写文档
```

## 相关文档索引

**必读文档：**
1. [README.md](../../README.md) - 项目主文档
2. [QUICKSTART.md](../../QUICKSTART.md) - 快速开始
3. [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) - 架构详解
4. [docs/DATABASE_USAGE.md](../../docs/DATABASE_USAGE.md) - 数据库使用

**模块文档：**
1. [backend/README.md](../../backend/README.md) - Backend 文档
2. [frontend/README.md](../../frontend/README.md) - Frontend 文档
3. [core/tests/README.md](../../core/tests/README.md) - 测试文档
4. [core/scripts/README.md](../../core/scripts/README.md) - 脚本说明

**故障排除：**
1. [TROUBLESHOOTING.md](../../TROUBLESHOOTING.md) - 常见问题

## 总结

这个项目是一个**模块化、可扩展、生产就绪**的量化交易系统，具有以下特点：

✅ **架构清晰**：前后端分离，职责明确
✅ **代码质量高**：60+ 单元测试，测试覆盖率高
✅ **性能优异**：TimescaleDB 优化，向量化计算
✅ **易于维护**：模块化设计，依赖注入
✅ **文档完善**：详细的README和注释
✅ **开发友好**：Docker 一键启动，Agent Skills 辅助

**下一步建议：**
1. 运行 `/run-all-tests` 验证系统功能
2. 使用 `/download-stock-data` 准备数据
3. 尝试 `/quick-backtest` 运行回测
4. 阅读感兴趣模块的源代码
5. 参与开发，添加新功能
