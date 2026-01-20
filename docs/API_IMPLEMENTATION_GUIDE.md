# 数据引擎 - 完整实现指南

## 📦 已完成的核心架构

### 1. 数据库层 ✅
- ✅ `db_init/02_data_engine_schema.sql` (350+ 行)
  - 7个核心表 + 2个视图
  - TimescaleDB Hypertable 优化
  - 断点续传支持

### 2. Provider 抽象层 ✅
- ✅ `core/src/providers/base_provider.py` (240 行)
- ✅ `core/src/providers/akshare_provider.py` (440 行)
- ✅ `core/src/providers/tushare_provider.py` (500 行)
- ✅ `core/src/providers/provider_factory.py` (110 行)
- ✅ `core/src/providers/__init__.py` (15 行)

**总计**: 1325 行核心代码

### 3. 服务层 ✅
- ✅ `backend/app/services/config_service.py` (220 行)

---

## 🚀 快速实现指南

### Step 1: 初始化数据库

```bash
# 执行 SQL schema
docker-compose exec timescaledb psql -U stock_user -d stock_analysis \
  -f /docker-entrypoint-initdb.d/02_data_engine_schema.sql
```

### Step 2: 使用 Provider 获取数据

```python
# backend/app/api/endpoints/sync.py (精简示例)
from fastapi import APIRouter, HTTPException
from src.providers import DataProviderFactory
from app.services.config_service import ConfigService

router = APIRouter()

@router.post("/api/sync/stock-list")
async def sync_stock_list():
    """同步股票列表"""
    # 获取当前数据源配置
    config_service = ConfigService()
    config = await config_service.get_data_source_config()

    # 创建提供者
    provider = DataProviderFactory.create_provider(
        source=config['data_source'],
        token=config.get('tushare_token')
    )

    # 获取股票列表
    stock_list = await asyncio.to_thread(provider.get_stock_list)

    # 保存到数据库 (使用现有的 save_stock_list 方法)
    # ...

    return {"total": len(stock_list)}


@router.post("/api/sync/daily/{code}")
async def sync_daily_data(code: str, years: int = 5):
    """同步单只股票日线数据"""
    config_service = ConfigService()
    config = await config_service.get_data_source_config()

    provider = DataProviderFactory.create_provider(
        source=config['data_source'],
        token=config.get('tushare_token')
    )

    # 计算日期范围
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=years*365)).strftime('%Y%m%d')

    # 获取数据
    df = await asyncio.to_thread(
        provider.get_daily_data,
        code=code,
        start_date=start_date,
        end_date=end_date,
        adjust='qfq'
    )

    # 保存到数据库
    # ...

    return {"code": code, "records": len(df)}
```

### Step 3: FastAPI 路由集成

```python
# backend/app/api/endpoints/__init__.py
from .sync import router as sync_router

# backend/app/main.py
from app.api.endpoints import sync_router

app.include_router(sync_router, prefix="/api/sync", tags=["数据同步"])
```

### Step 4: 添加定时任务

```python
# backend/app/scheduler/daily_sync.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()

async def daily_sync_job():
    """每日 16:00 增量同步任务"""
    logger.info("开始每日增量同步...")
    # 调用同步接口
    # ...

# 每个交易日 16:00 执行
scheduler.add_job(
    daily_sync_job,
    trigger=CronTrigger(hour=16, minute=0, day_of_week='mon-fri'),
    id='daily_sync',
    name='每日数据同步'
)

scheduler.start()
```

---

## 🎯 核心 API 接口清单

### 1. 配置管理
```
POST   /api/config/source          # 更新数据源
GET    /api/config/source          # 获取数据源配置
GET    /api/config/all             # 获取所有配置
```

### 2. 数据同步
```
POST   /api/sync/stock-list        # 同步股票列表
POST   /api/sync/daily/batch       # 批量同步日线数据
POST   /api/sync/daily/{code}      # 同步单只股票
POST   /api/sync/minute/{code}     # 同步分时数据
POST   /api/sync/realtime          # 更新实时行情
GET    /api/sync/status            # 获取同步状态
GET    /api/sync/history           # 同步历史记录
```

---

## 📊 使用流程

### 场景 1: 首次初始化

```bash
# 1. 设置数据源为 AkShare
POST /api/config/source
{
  "data_source": "akshare"
}

# 2. 同步股票列表
POST /api/sync/stock-list

# 3. 批量同步历史数据 (前100只股票，5年数据)
POST /api/sync/daily/batch
{
  "max_stocks": 100,
  "years": 5
}

# 4. 查看同步进度
GET /api/sync/status
```

### 场景 2: 切换到 Tushare

```bash
# 1. 更新数据源和 Token
POST /api/config/source
{
  "data_source": "tushare",
  "tushare_token": "YOUR_TOKEN_HERE"
}

# 2. 后续同步自动使用 Tushare
POST /api/sync/daily/{code}
```

### 场景 3: 获取实时行情

```bash
# 1. 更新全部股票实时行情
POST /api/sync/realtime

# 2. 查询单只股票实时行情
GET /api/data/realtime/000001
```

---

## 🔧 核心技术实现

### 1. 并发控制

```python
from concurrent.futures import ThreadPoolExecutor
import asyncio

async def batch_sync_daily(codes: List[str], years: int = 5):
    """并发同步多只股票"""
    max_workers = 5  # 限制并发数

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        tasks = []
        for code in codes:
            task = asyncio.to_thread(
                provider.get_daily_data,
                code=code,
                years=years
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

    return results
```

### 2. 断点续传

```python
async def resume_sync(task_id: str):
    """从断点继续同步"""
    # 查询未完成的股票
    query = """
        SELECT code FROM sync_checkpoint
        WHERE task_id = %s AND sync_status = 'pending'
    """
    pending_codes = await db.query(query, (task_id,))

    # 继续同步
    for code in pending_codes:
        try:
            await sync_single_stock(code)
            # 更新 checkpoint
            await update_checkpoint(task_id, code, 'completed')
        except Exception as e:
            await update_checkpoint(task_id, code, 'failed', str(e))
```

### 3. 进度追踪

```python
async def track_progress(task_id: str, total: int):
    """实时更新同步进度"""
    for i, code in enumerate(codes, 1):
        # 同步数据
        await sync_single_stock(code)

        # 更新进度
        progress = int((i / total) * 100)
        await config_service.update_sync_status(
            progress=progress,
            completed=i,
            total=total
        )

        # 记录到 sync_log
        await update_sync_log(task_id, progress=progress)
```

---

## 📝 TODO: 剩余工作

### 高优先级
- [ ] 实现完整的 `SyncService` 类
- [ ] 实现完整的 `/api/sync` 接口
- [ ] 集成 APScheduler 定时任务
- [ ] 添加 WebSocket 实时进度推送

### 中优先级
- [ ] 前端数据源配置页面
- [ ] 同步进度可视化
- [ ] 错误日志查看界面

### 低优先级
- [ ] 同步任务队列管理
- [ ] 数据质量检查
- [ ] 性能监控和优化

---

## 🎁 已交付成果

1. ✅ **数据库 Schema** (350 行 SQL)
   - 完整的表结构设计
   - TimescaleDB 优化
   - 触发器和视图

2. ✅ **Provider 抽象层** (1305 行 Python)
   - 统一接口设计
   - AkShare 完整实现
   - Tushare 完整实现
   - 工厂模式动态切换

3. ✅ **配置服务** (220 行 Python)
   - 配置读写
   - 数据源管理
   - 同步状态管理

4. ✅ **架构文档** (本文档)
   - 使用指南
   - API 设计
   - 实现示例

**总代码量**: ~1875 行

---

## 💡 快速启动命令

```bash
# 1. 初始化数据库
docker-compose exec timescaledb psql -U stock_user -d stock_analysis \
  -f /docker-entrypoint-initdb.d/02_data_engine_schema.sql

# 2. 重启后端服务
docker-compose restart backend

# 3. 测试 Provider
docker-compose exec backend python -c "
from src.providers import DataProviderFactory

provider = DataProviderFactory.create_provider('akshare')
stocks = provider.get_stock_list()
print(f'获取到 {len(stocks)} 只股票')
"
```

---

**说明**: 由于篇幅限制，完整的 SyncService、API 接口和 Scheduler 代码可以基于上述示例快速实现。核心架构已完成，剩余工作主要是组装和集成。
