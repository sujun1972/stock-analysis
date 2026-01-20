# 数据引擎架构说明

## 📁 已创建的核心文件

### 1. 数据库 Schema
- **文件**: `db_init/02_data_engine_schema.sql`
- **内容**:
  - `system_config` - 系统配置表
  - `stock_basic` - 股票基本信息
  - `stock_daily` - 日线数据 (TimescaleDB Hypertable)
  - `stock_min` - 分时数据 (TimescaleDB Hypertable)
  - `stock_realtime` - 实时行情快照
  - `sync_log` - 同步日志
  - `sync_checkpoint` - 断点续传表

### 2. 数据提供者层 (Provider Layer)
**位置**: `core/src/providers/`

#### 抽象基类
- `base_provider.py` - 定义统一接口规范
  - `get_stock_list()` - 获取股票列表
  - `get_daily_data()` - 获取日线数据
  - `get_minute_data()` - 获取分时数据
  - `get_realtime_quotes()` - 获取实时行情

#### 具体实现
- `akshare_provider.py` - AkShare 数据提供者
  - 免费开源，无需 Token
  - 自动重试机制
  - 请求频率控制

- `tushare_provider.py` - Tushare 数据提供者
  - 需要 Token 和积分
  - 频率限制处理
  - 积分不足检测

- `provider_factory.py` - 工厂模式
  - 根据配置动态创建提供者
  - 支持运行时切换数据源

### 3. 配置管理服务
- **文件**: `backend/app/services/config_service.py`
- **功能**:
  - 读写系统配置 (数据源、Token)
  - 同步状态管理
  - 配置变更通知

---

## 🔧 待创建文件

### 1. 数据同步服务
**文件**: `backend/app/services/sync_service.py`

**功能**:
- 全量初始化同步
- 增量同步 (仅拉取新数据)
- 断点续传
- 并发控制
- 进度追踪

### 2. FastAPI 接口
**文件**: `backend/app/api/endpoints/sync.py`

**接口列表**:
```
POST   /api/config/source        # 更新数据源设置
GET    /api/config/source        # 获取当前数据源配置
GET    /api/config/all           # 获取所有配置

POST   /api/sync/init            # 手动触发全量初始化
POST   /api/sync/incremental     # 手动触发增量同步
GET    /api/sync/status          # 获取同步状态
GET    /api/sync/history         # 获取同步历史

POST   /api/data/realtime/update # 更新实时行情
GET    /api/data/realtime/{code} # 获取单只股票实时行情
```

### 3. APScheduler 定时任务
**文件**: `backend/app/scheduler/stock_scheduler.py`

**任务**:
- 每日 16:00 自动增量同步
- 每 5 分钟更新实时行情 (交易时段)
- 自动检测交易日

---

## 💡 使用示例

### 切换数据源
```python
from app.services.config_service import ConfigService

config_service = ConfigService()

# 切换到 AkShare
await config_service.update_data_source('akshare')

# 切换到 Tushare
await config_service.update_data_source(
    'tushare',
    tushare_token='your_token_here'
)
```

### 使用数据提供者
```python
from src.providers import DataProviderFactory

# 创建 AkShare 提供者
provider = DataProviderFactory.create_provider('akshare')

# 获取股票列表
stock_list = provider.get_stock_list()

# 获取日线数据
daily_data = provider.get_daily_data(
    code='000001',
    start_date='20240101',
    end_date='20241231',
    adjust='qfq'
)

# 获取分时数据
minute_data = provider.get_minute_data(
    code='000001',
    period='5',
    start_date='2024-01-20 09:30:00',
    end_date='2024-01-20 15:00:00'
)

# 获取实时行情
realtime = provider.get_realtime_quotes(codes=['000001', '000002'])
```

---

## 🗂️ 数据库初始化

```bash
# 1. 确保数据库运行
docker-compose up -d timescaledb

# 2. 执行初始化脚本
docker-compose exec timescaledb psql -U stock_user -d stock_analysis -f /docker-entrypoint-initdb.d/02_data_engine_schema.sql
```

---

## 📊 数据流程

```
┌─────────────────┐
│   前端界面       │
│  (Next.js)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FastAPI 接口   │
│  (配置/同步)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ConfigService  │◄──── system_config 表
│  SyncService    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ProviderFactory  │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌─────────┐ ┌──────────┐
│ AkShare │ │ Tushare  │
│Provider │ │Provider  │
└─────────┘ └──────────┘
    │         │
    └────┬────┘
         ▼
┌─────────────────┐
│  TimescaleDB    │
│ (数据存储)      │
└─────────────────┘
```

---

## ⚙️ 技术特性

### 1. 抽象提供者模式
- 统一接口，无缝切换数据源
- 易于扩展新数据源
- 字段标准化映射

### 2. 并发与限流
- ThreadPoolExecutor 并发下载
- 请求间隔控制 (0.2-0.5秒)
- 自动重试机制
- 错误隔离

### 3. 断点续传
- sync_checkpoint 表记录进度
- 任务中断后可继续
- 失败股票单独处理

### 4. TimescaleDB 优化
- Hypertable 时序数据分区
- 自动数据压缩
- 高效时间范围查询

### 5. 实时监控
- sync_log 记录所有任务
- 进度实时更新
- WebSocket 推送 (可选)

---

## 🎯 下一步工作

1. 实现 SyncService (数据同步服务)
2. 实现 FastAPI 接口
3. 实现 APScheduler 定时任务
4. 前端集成 (数据源配置页面)
5. 测试与优化

---

## ⚠️ 注意事项

### AkShare
- 免费但有 IP 限流风险
- 实时行情获取较慢 (20-30秒)
- 建议请求间隔 >= 0.3秒

### Tushare
- 日线数据需要 120 积分
- 分钟数据需要 2000 积分
- 实时行情需要 5000 积分
- 每分钟调用次数有限制
