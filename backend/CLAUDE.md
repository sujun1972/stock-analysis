# Backend 开发指南

## 分层架构规范

Backend 采用严格的三层架构：

```
API Layer (endpoints/)      ← 只处理 HTTP 请求/响应，不写 SQL
    ↓
Service Layer (services/)   ← 只处理业务逻辑，通过 Repository 访问数据库
    ↓
Repository Layer (repositories/) ← 只处理数据持久化
    ↓
Database (TimescaleDB / PostgreSQL)
```

**强制规则**：
- ❌ 禁止在 API 层写 SQL（`text()` + `db.execute()`）
- ❌ 禁止 Service 层直接使用 `DatabaseManager`
- ✅ Service 使用 `asyncio.to_thread()` 调用 Repository 的同步方法
- ✅ API 函数一般不超过 30 行（不含文档注释）

---

## API 响应格式

所有端点必须使用 `ApiResponse`：

```python
from app.models.api_response import ApiResponse

# ✅ 正确
@router.get("/items", response_model=ApiResponse)
async def get_items():
    return ApiResponse.success(data=result)

# ❌ 错误
@router.get("/items", response_model=dict)   # 无法序列化 ApiResponse
async def get_items():
    return {"code": 200, "data": result}     # 直接返回字典
```

**常用方法**：`success()` / `created()` / `warning()` / `bad_request()` / `not_found()` / `internal_error()` / `paginated()`

**NaN/Inf 自动清理**：`ApiResponse` 会自动调用 `sanitize_float_values()`，无需手动处理。

---

## API 权限控制

```python
from app.core.dependencies import get_current_active_user, require_admin

# 公开接口（无需认证）
@router.get("/public")
async def public_endpoint(): ...

# 普通用户（需登录）
@router.get("/user")
async def user_endpoint(current_user: User = Depends(get_current_active_user)): ...

# 管理员（admin / super_admin）
@router.post("/admin")
async def admin_endpoint(current_user: User = Depends(require_admin)): ...
```

**重要**：`HTTPBearer(auto_error=True)` 是默认值，无 Token 时直接返回 401，与端点逻辑无关。对于需要公开访问的端点，必须完全去掉 auth 依赖。

**已公开的端点**（frontend 项目调用，无需登录）：
- `GET /api/features/{code}` — K线/特征数据（含自动同步）
- `GET /api/stocks/{code}/minute` — 分时数据
- `GET /api/stocks/{code}/daily` — 日线数据
- `GET /api/stocks/{code}/quote-panel` — 行情面板
- `GET /api/stocks/{code}/basic-info` — 股票基础信息
- `GET /api/cyq-chips/distribution` — 筹码分布

---

## Repository 开发规范

### 基础结构

```python
from app.repositories.base_repository import BaseRepository

class YourRepository(BaseRepository):
    TABLE_NAME = "your_table"

    def __init__(self, db=None):
        super().__init__(db)

    def get_by_date_range(self, start_date: str, end_date: str, ...) -> List[Dict]:
        """按日期范围查询（start_date/end_date 格式：YYYYMMDD）"""
        query = "SELECT ... FROM %s WHERE trade_date >= %%s AND trade_date <= %%s" % self.TABLE_NAME
        return self.execute_query(query, (start_date, end_date))

    def bulk_upsert(self, df: pd.DataFrame) -> int:
        """批量插入/更新（ON CONFLICT DO UPDATE）"""
        ...

    def get_latest_trade_date(self) -> Optional[str]:
        """返回表中最新 trade_date（YYYYMMDD 格式）"""
        ...
```

### Numpy 类型转换（必须）

psycopg2 无法直接处理 numpy 类型，`bulk_upsert` 中每个字段必须转换：

```python
def to_python_type(value):
    if pd.isna(value):
        return None
    if hasattr(value, 'item'):  # numpy scalar
        return value.item()
    return value

values = [(to_python_type(row['col1']), to_python_type(row['col2'])) for _, row in df.iterrows()]
```

### LIKE 模式中的 `%` 转义

psycopg2 将查询字符串中的 `%` 视为参数占位符，LIKE 模式须写成 `%%`：

```python
query = "SELECT code FROM stock_daily WHERE code LIKE '%%%.%%'"  # ✅ 匹配 '000001.SZ'
```

### 日期类型不一致处理

`trade_date` 列可能是 `VARCHAR` 或 `DATE` 类型，Repository 层统一转为字符串：

```python
"trade_date": row[0].strftime('%Y%m%d') if hasattr(row[0], 'strftime') else row[0]
```

---

## Service 层规范

```python
class YourService:
    def __init__(self):
        self.repo = YourRepository()    # ✅ 注入 Repository
        # self.db = DatabaseManager()  # ❌ 禁止

    async def get_data(self, start_date, end_date):
        # 日期格式转换（业务逻辑）
        start_fmt = start_date.replace('-', '') if start_date else None
        # 通过 Repository 访问数据库
        items = await asyncio.to_thread(self.repo.get_by_date_range, start_fmt, end_fmt)
        return {"items": items}
```

**DataProviderFactory 正确用法**：

```python
from app.core.config import settings

# ✅ 正确：使用类方法，传入 token
provider = DataProviderFactory.create_provider('tushare', token=settings.TUSHARE_TOKEN)

# ❌ 错误：没有实例方法 get_provider()
self.provider_factory = DataProviderFactory()
provider = self.provider_factory.get_provider('tushare')
```

**`_get_provider()` 惰性初始化模式**（继承 `BaseSyncService` 的 Service 自动拥有）：

```python
def _get_provider(self, max_requests_per_minute=None):
    cache_key = f'_provider_{max_requests_per_minute}'
    cached = getattr(self, cache_key, None)
    if cached:
        return cached
    provider = DataProviderFactory.create_provider('tushare', token=settings.TUSHARE_TOKEN,
                                                    max_requests_per_minute=effective_rpm)
    setattr(self, cache_key, provider)
    return provider
```

⚠️ Service 的 `__init__` **不得**调用 `create_provider()`，必须惰性初始化，否则模块导入时 token 验证失败。

---

## Celery 任务开发

### 基本结构

```python
from app.celery_app import celery_app
from app.tasks.extended_sync_tasks import run_async_in_celery

@celery_app.task(bind=True, name="tasks.sync_your_data")
def sync_your_data_task(self, trade_date=None, start_date=None, end_date=None):
    from app.services.your_service import YourService  # 延迟导入！
    service = YourService()
    return run_async_in_celery(service.sync_data, trade_date=trade_date, ...)
```

**⚠️ 延迟导入（非常重要）**：禁止在任务文件顶层创建 Service 实例。Celery fork worker 继承父进程的连接池，顶层实例化会导致 `connection pool is closed` 错误。

### 全量历史同步任务

```python
@celery_app.task(
    bind=True,
    name="tasks.sync_your_full_history",
    max_retries=0,
    acks_late=False,  # 支持 Redis 续继，worker 重启后不自动重新入队
)
def sync_your_full_history_task(self, start_date=None, concurrency=5):
    ...
```

### run_async_in_celery 原理

1. 关闭继承自父进程的旧事件循环
2. 创建新事件循环
3. 调用 `reset_async_engine()` 重新初始化 SQLAlchemy 异步引擎
4. 运行异步函数

### 常见 Celery 问题排查

| 问题 | 原因 | 解决 |
|------|------|------|
| 任务状态卡在 `pending` | 信号处理器使用了 `DatabaseManager` 单例（fork 后连接池损坏） | `celery_signals.py` 中信号处理器用 `_get_direct_conn()` 独立 psycopg2 直连 |
| `connection pool is closed` | 顶层 Service 实例化，fork 后继承损坏的连接池 | 将 Service 实例化移入任务函数体（延迟导入） |
| `attached to a different loop` | 复用了绑定到父进程的事件循环 | 使用 `run_async_in_celery` 辅助函数 |
| 活动任务在面板消失但 worker 仍运行 | 未配置 `task_track_started=True` | 在 `celery_app.conf.update()` 中添加此配置 |
| `celery_beat` 报 "Tushare Token 未配置" | `docker-compose.yml` celery_beat 服务缺少 `TUSHARE_TOKEN` | 在 environment 中添加 `TUSHARE_TOKEN=${TUSHARE_TOKEN:-}` |
| 全量同步提交报"已有任务在进行" | Redis lock key 残留（任务被 revoke 或 worker 崩溃） | 端点提交前调用 `release_stale_lock(table_key)` |

**`DatabaseManager` 在 fork worker 中的处理**：
`celery_signals.py` 的 `worker_process_init` 信号在每个 fork worker 启动时调用 `DatabaseManager.reset_instance()`，强制子进程重建连接池。**禁止在 Celery 任务体内调用** `reset_instance()`，否则会关闭 FastAPI 主进程正在使用的连接。

---

## 同步默认日期规范

**禁止** Service 层硬编码 `yesterday`，正确方式：

**方式 A**：Tushare 接口 `trade_date=None` 时自动返回最新交易日 → 直接透传 `None`

**方式 B**：接口要求 `trade_date` 为必需参数 → 从 `TradingCalendarRepository` 查询：

```python
from app.repositories.trading_calendar_repository import TradingCalendarRepository

if not trade_date:
    trade_date = await asyncio.to_thread(self.calendar_repo.get_latest_trading_day)
```

**方式 C**：查询端点（GET）未传日期时，`resolve_default_trade_date()` 返回最近有数据的交易日并回传给前端（前端用于初始化日期选择器）：

```python
async def resolve_default_trade_date(self) -> Optional[str]:
    today = datetime.now().strftime('%Y%m%d')
    has_today = await asyncio.to_thread(self.repo.exists_by_date, today)
    if has_today:
        return f"{today[:4]}-{today[4:6]}-{today[6:8]}"
    latest = await asyncio.to_thread(self.repo.get_latest_trade_date)
    return f"{latest[:4]}-{latest[4:6]}-{latest[6:8]}" if latest else None
```

**前端同步按钮不得传查询筛选日期**：`handleSync` 不传 `trade_date`，让后端自动取最新交易日。

---

## 全量同步策略

Tushare 接口分三类，实现前必须验证：

| 类型 | 特征 | 策略 |
|------|------|------|
| **快照接口** | 不传日期返回全量；传日期返回 0 条 | `strategy='snapshot'`：不传日期，仅 limit/offset 分页 |
| **日期范围接口** | 支持 start_date/end_date，单次有上限 | 按月切片（`by_month`），5并发，Redis Set 续继 |
| **仅支持 trade_date** | 传日期范围报参数错误 | 逐日请求（`by_date` + `date_param='trade_date'`）|
| **仅支持 ts_code** | 无法按日期拉全市场 | 逐只股票请求（`by_ts_code`），5并发，Redis续继 |

**验证步骤**：① 不传日期 → 看是否返回全量；② 传 `start_date/end_date` → 看是否有数据；③ 传单年范围 → 看是否逼近上限

### TushareSyncBase 继承模式

```python
class YourService(TushareSyncBase):
    TABLE_KEY = 'your_table'
    FULL_HISTORY_START_DATE = '20180101'
    FULL_HISTORY_PROGRESS_KEY = 'sync:your_table:full_history:progress'  # 类常量

    async def sync_full_history(self, redis_client, start_date=None, concurrency=5,
                                 strategy='by_month', update_state_fn=None,
                                 max_requests_per_minute=0):
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 6000) if cfg else 6000
        provider = self._get_provider(max_requests_per_minute)
        return await self.run_full_sync(
            redis_client=redis_client,
            fetch_fn=provider.get_your_data,
            upsert_fn=self.your_repo.bulk_upsert,
            clean_fn=self._validate_and_clean_data,
            progress_key=self.FULL_HISTORY_PROGRESS_KEY,
            strategy=strategy,
            start_date=start_date,
            full_history_start=self.FULL_HISTORY_START_DATE,
            concurrency=concurrency,
            api_limit=api_limit,
            table_key=self.TABLE_KEY,
        )
```

**`strategy` 由 API 端点从 `sync_configs.full_sync_strategy` 读取后传给 Celery task**，Service 层的默认值只作兜底。

### 全量同步并发数

从 `sync_configs.full_sync_concurrency` 读取，不硬编码：

```python
cfg = await asyncio.to_thread(sync_config_repo.get_by_table_key, 'your_table')
concurrency = concurrency or (cfg.get('full_sync_concurrency') or 5)
```

### 分页 offset 上限保护

```python
MAX_OFFSET = 100_000  # Tushare offset 上限，超过后报"查询数据失败"

offset = 0
while True:
    if offset >= MAX_OFFSET:
        logger.warning(f"offset 已达上限，停止分页")
        break
    df = provider.get_xxx(..., limit=api_limit, offset=offset)
    if df is None or df.empty:
        break
    offset += api_limit
```

### Tushare 频率限制识别

只有包含 `抱歉，您每分钟最多访问` 或 `抱歉，您每小时最多访问` 的错误才是真正的频率限制（需等待 65s）。

`查询数据失败，请确认参数` 是**通用查询失败**，不是频率限制，不应触发 65s 等待。

### 月切片模板

```python
@staticmethod
def _generate_months(start_date: str, end_date: str) -> list:
    import calendar
    start_d = date(int(start_date[:4]), int(start_date[4:6]), int(start_date[6:8]))
    end_d = date(int(end_date[:4]), int(end_date[4:6]), int(end_date[6:8]))
    segments = []
    cur = date(start_d.year, start_d.month, 1)
    while cur <= end_d:
        ms = max(cur, start_d)
        last_day = calendar.monthrange(cur.year, cur.month)[1]
        me = min(date(cur.year, cur.month, last_day), end_d)
        segments.append((ms.strftime('%Y%m%d'), me.strftime('%Y%m%d')))
        cur = date(cur.year + 1, 1, 1) if cur.month == 12 else date(cur.year, cur.month + 1, 1)
    return segments
```

### 财务报表全量同步：逐只股票请求

Tushare 财务接口（`income_vip`、`balancesheet_vip` 等）单次上限 6400~12000 条。全量同步必须按 ts_code 逐只拉取，避免截断。

```python
all_ts_codes = StockBasicRepository().get_listed_ts_codes(status='L')
completed_set = {v.decode() if isinstance(v, bytes) else v for v in redis_client.smembers(PROGRESS_KEY)}
pending = [c for c in all_ts_codes if c not in completed_set]
sem = asyncio.Semaphore(CONCURRENCY)

async def sync_one(ts_code):
    async with sem:
        result = await self.sync_xxx(ts_code=ts_code, start_date=effective_start, end_date=today)
        if result.get("status") != "error":
            redis_client.sadd(PROGRESS_KEY, ts_code)
```

---

## 定时任务（Scheduler）架构

```
backend/app/scheduler/
├── database_scheduler.py   # 数据库驱动的 Celery Beat（每30秒同步配置变更）
├── task_executor.py        # 手动触发任务执行
├── task_metadata.py        # 任务元数据（37个任务，集中维护）
├── task_metadata_service.py
└── cron_parser.py
```

**关键约束**：`scheduled_tasks.module` 必须与 `task_metadata.py` 的 key 完全一致，否则手动执行报 "未找到模块"。

**新增任务**：
1. 在 `task_metadata.py` 中添加元数据
2. 在 `celery_app.py` 中 import 任务模块
3. 在 `scheduler.py` API 中登记（可选）
4. 重启 `celery_worker` 容器

---

## sync_configs 表要点（后端侧）

| 字段 | 说明 |
|------|------|
| `full_sync_task_name` | Celery 全量任务名；为 NULL 则同步配置页不显示"全量"按钮 |
| `full_sync_strategy` | `by_month`/`by_ts_code`/`snapshot`/`by_date`/`by_quarter`；禁止填 `NULL` 或 `'none'` |
| `api_limit` | 接口单次请求上限，用于分页循环 |
| `max_requests_per_minute` | NULL=继承全局；0=不限速；正整数=覆盖全局 |
| `incremental_sync_strategy` | NULL=接口默认逻辑 |

**`FULL_SYNC_REDIS_KEYS`（在 `sync_dashboard.py` 中维护）**：记录各表全量同步的 Redis Set key。新增支持全量续继的表时**必须**同步更新，否则同步配置页面无法查询/清除进度。

**`release_stale_lock(table_key)`**：所有全量同步 API 端点在提交 Celery task 前必须调用，自动清除因任务 revoke 或 worker 崩溃留下的残留 Redis lock。

---

## StockQuoteCache

当数据表只有 `ts_code`，需展示股票名称/行情时，使用 `StockQuoteCache` 注入，避免跨表 JOIN。

```python
from app.services.stock_quote_cache import stock_quote_cache

# 异步 Service（可 await）
ts_codes = list(dict.fromkeys(item['ts_code'] for item in items))
quotes = await stock_quote_cache.get_quotes_batch(ts_codes)
for item in items:
    item['name'] = quotes.get(item['ts_code'], {}).get('name', '')

# 同步 Service（被 asyncio.to_thread 调用，不能 await）
quotes = stock_quote_cache._repo.get_quotes(ts_codes)
```

**缓存字段**：name, latest_price, pct_change, change_amount, open, high, low, pre_close, volume, amount, turnover, amplitude, trade_time

**ETF 名称回退**：`StockQuoteCache` 只查 `stock_basic`，ETF/基金需从 `MarginSecsRepository.get_name_map()` 补充。

**`stock_basic` JOIN `stock_realtime` 注意**：`stock_realtime` 主键是 `code`（纯数字），不是 `ts_code`：
```sql
LEFT JOIN stock_basic sb ON sb.ts_code = your_table.ts_code
LEFT JOIN stock_realtime sr ON sr.code = sb.code   -- ✅ 正确
```

---

## 股票代码自动补全

```python
from app.services.stock_quote_cache import stock_quote_cache

resolved_ts_code = await stock_quote_cache.resolve_ts_code(ts_code) if ts_code else None
```

规则：含 `.` → 转大写直接返回；纯数字 → 查 `stock_basic.code` 补全后缀；查不到 → 返回 `None`

---

## 板块名称注入

`dc_member`、`dc_daily` 表只存 `ts_code`，不存名称。在 Service 层 `asyncio.gather` 中并发注入：

```python
from app.repositories.dc_index_repository import DcIndexRepository

items, total, board_name_map = await asyncio.gather(
    asyncio.to_thread(self.repo.get_by_date_range, ...),
    asyncio.to_thread(self.repo.get_total_count, ...),
    asyncio.to_thread(self.dc_index_repo.get_board_name_map)
)
for item in items:
    item['board_name'] = board_name_map.get(item['ts_code'], '')
```

---

## 数据库连接池

系统有三套独立连接池，**总上限必须低于 PostgreSQL `max_connections`**：

| 连接池 | 默认上限 |
|--------|---------|
| SQLAlchemy 同步引擎 | pool_size=5 + max_overflow=10 = **15** |
| SQLAlchemy 异步引擎 | pool_size=5 + max_overflow=10 = **15** |
| psycopg2（Core 模块） | min=2, max=20 = **20** |
| **合计** | **≈50** |

`max_connections=200` 已通过 `ALTER SYSTEM` 持久化。调整连接池大小修改 `backend/app/core/database.py` 中的 `_POOL_SIZE` / `_MAX_OVERFLOW` 常量。

---

## TimescaleDB 查询注意

`stock_daily` 是 TimescaleDB hypertable（6M+ 行，557+ chunks），以下查询触发全表扫描（>10s），**禁止**：
- `COUNT(DISTINCT code)` — 跨所有 chunk
- `DISTINCT ON (code) ORDER BY date DESC`

**正确做法（< 10ms）**：
1. `MAX(trade_date)` 从 `trading_calendar` 取最近交易日（索引，< 1ms）
2. `WHERE date = %s` 查 `stock_daily`（命中 `idx_stock_daily_date`，< 5ms）
3. 总数用 `SELECT COUNT(*) FROM stock_basic WHERE list_status = 'L'`（< 1ms）

---

## 新增数据同步功能检查清单

- [ ] 数据库迁移脚本已创建并执行（`db_init/migrations/`）
- [ ] Repository 实现 `get_by_date_range`、`get_statistics`、`bulk_upsert`、`exists_by_date`
- [ ] Repository 在 `repositories/__init__.py` 中导出
- [ ] Service 实现同步和查询逻辑，无直接 SQL
- [ ] Celery 任务使用 `run_async_in_celery`，Service 在函数体内延迟导入
- [ ] 全量历史任务加 `acks_late=False`
- [ ] 任务元数据添加到 `task_metadata.py`
- [ ] API 端点包含查询、统计、异步同步（至少3个）
- [ ] 全量同步端点提交前调用 `release_stale_lock(table_key)`
- [ ] Tushare Provider 添加 `get_your_data()` 方法（用 `_query` + `_build_params`）
- [ ] `sync_configs` 表登记（`105_create_sync_configs.sql` 追加并重新执行）
- [ ] `FULL_SYNC_REDIS_KEYS` 更新（`sync_dashboard.py`）
- [ ] `celery_worker` 重启并验证任务注册
- [ ] 增量同步 API 端点处理 "无参数触发" 情况（`effective_start = await self.get_suggested_start_date()`）

---

## 通知系统

多渠道推送（Email、Telegram Bot、站内消息）。

**核心组件**：
- `notification_service.py` — 用户配置管理、订阅查询
- `email_sender.py` / `telegram_sender.py` — 渠道发送器
- `template_renderer.py` — Jinja2 模板（数据库驱动）
- `notification_tasks.py` — Celery 异步任务

**触发方式**：

```python
from app.tasks.notification_tasks import schedule_report_notification_task

schedule_report_notification_task.delay(
    report_type='sentiment_report',
    trade_date='2026-03-15',
    report_data={...}
)
```

**添加新报告类型**：
1. 在 `user_notification_settings` 添加订阅字段
2. 在 `notification_templates` 创建模板（Email/Telegram/站内消息）
3. 更新 `NotificationService.get_subscribers()` 的 `subscription_field_map`
4. 在报告生成服务中触发 `schedule_report_notification_task`

**监控 API**：`/api/notification-monitoring`（仅超级管理员）

---

## 模块化拆分规范

当 API 端点文件 > 500 行时，拆分为包结构：

```
endpoints/your_module/
├── __init__.py      # 路由聚合（include_router）
├── schemas.py       # Pydantic 模型
├── query.py         # 查询类端点
├── sync.py          # 同步类端点
└── analysis.py      # 分析类端点
```

Service 层 > 500 行时拆分为：

```
services/your_module/
├── __init__.py              # 聚合服务（向后兼容委托）
├── your_query_service.py    # 查询逻辑
├── your_sync_service.py     # 同步逻辑
└── your_analysis_service.py # 分析逻辑
```
