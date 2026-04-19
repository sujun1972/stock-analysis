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

## 选股策略执行模式

选股策略通过 `StrategyDynamicLoader.run_stock_selection()` 统一执行，**不要在 API 端点中内联实现**：

```python
from app.services.strategy_loader import StrategyDynamicLoader
from app.repositories.strategy_repository import StrategyRepository

repo = StrategyRepository()
strategy_record = repo.get_by_id(strategy_id)
ts_codes = await StrategyDynamicLoader.run_stock_selection(
    strategy_record,
    lookback_days=60,   # 可选，默认 60 天
    top_n=None,         # 可选；None = 返回所有评分>0的股票；可传整数限制数量
)
```

**`GET /api/stocks/list` 支持 `stock_selection_strategy_id` 参数**，在数据库层（`WHERE ts_code IN (...)`）过滤选股结果，无需前端二次过滤。

### 选股策略数据约定

`run_stock_selection()` 在调用 `calculate_scores()` 前已完成系统层数据清洗，**策略代码无需重复处理**：

| 问题 | 系统处理方式 |
|------|------------|
| 周末/节假日行（pivot 后大量 NaN） | 过滤有效股票数 < 10% 的行 |
| 新股/长期停牌覆盖率不足 | 剔除覆盖率 < 50% 的股票列 |
| 短期停牌产生的 NaN | 前向填充（ffill），不引入未来信息 |
| psycopg2 Decimal 类型 | 构建 DataFrame 前统一 astype(float) |
| 同日期重复行 | groupby mean 去重后再 pivot |

策略代码只需关注因子计算逻辑。传入参数的保证：

- `prices`：收盘价矩阵，index=连续交易日，columns=ts_code，值全为 float，无 NaN
- `features`：成交量矩阵，结构与 `prices` 相同，停牌日填 0；策略可用 `features.iloc[-n:].mean()` 计算放量比等量价因子
- `fundamentals`（可选，4 参数策略启用）：原始财报三表快照（见下节）

**评分约定**：`calculate_scores()` 返回的 `pd.Series` 中，评分 `> 0` 的股票才会被选入结果；评分 `<= 0` 或 `-inf` 的股票视为未通过筛选。`top_n` 由策略自身的 `custom_params` 控制，系统层不做截断。

### 策略接入财报数据（fundamentals 参数）

需要用到 income / balancesheet / cashflow 原始字段构造价值/质量因子的策略，在 `calculate_scores` 签名中**添加第 4 参数** `fundamentals`：

```python
def calculate_scores(self, prices, features=None, date=None, fundamentals=None) -> pd.Series:
    if fundamentals is None or fundamentals.empty:
        return pd.Series(0.0, index=prices.columns)
    # 按 ts_code 分组取最近 N 期
    latest = fundamentals.sort_values(['ts_code','end_date'], ascending=[True,False]) \
                         .groupby('ts_code').head(1)
    ...
```

系统层（`run_stock_selection`）通过 `inspect.signature` 检测签名：3 参数老策略走原路径；4 参数策略自动注入由 `fetch_fundamentals_snapshot` 拉取的长格式 DataFrame（默认近 8 期，每期一行）。

**字段前缀**：`inc_*`（income）、`bs_*`（balancesheet）、`cf_*`（cashflow）+ 键 `ts_code, end_date, latest_ann_date`。详见 `app/services/strategy_fundamentals.py` 的 `_COLUMN_LIST`。

**防前视偏差（关键约束）**：`fetch_fundamentals_snapshot` 强制 `ann_date <= as_of_date`（即交易日）。绝不可用 `end_date`（报告期末日）作为过滤条件——未公告的财报对策略不可见。系统用 `prices.index[-1]` 作为锚点。

**共用工具**：`core/src/strategies/_fundamentals_utils.safe_div` 处理 `NaN/None/0` 除法；6 个参考策略（Piotroski / Sloan / FCF / RD / AR / Inventory / QualityMomentum）均在 `core/src/strategies/predefined/` 下，作为模板。

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

## API 错误处理

所有 API 端点必须使用 `@handle_api_errors` 装饰器，禁止手写 `try-except` + `HTTPException` 样板：

```python
from app.api.error_handler import handle_api_errors

@router.get("/items")
@handle_api_errors
async def get_items():
    return ApiResponse.success(data=await service.fetch())
```

装饰器统一处理 `ValueError`/`KeyError`/`PermissionError`/`APIError` 等异常并返回标准 `HTTPException`。

**sync/async 自动分流**：`@handle_api_errors` 现在会检测被装饰函数是否协程函数，同步函数自动转发到 `handle_api_errors_sync`，无需显式选择。`@handle_api_errors_sync` 作为语义别名保留。历史 `def` 端点误用 `@handle_api_errors` 会导致 `TypeError: object dict can't be used in 'await' expression`，现已被装饰器自动规避。

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
    FULL_HISTORY_PROGRESS_KEY = 'sync:your_table:full_history:progress'
    FULL_HISTORY_LOCK_KEY = 'sync:your_table:full_history:lock'  # 分布式锁 key

    async def sync_incremental(self, start_date=None, end_date=None,
                                sync_strategy=None, max_requests_per_minute=None):
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        api_limit = (cfg.get('api_limit') or 6000) if cfg else 6000
        if sync_strategy is None:
            sync_strategy = (cfg.get('incremental_sync_strategy') or 'by_date_range') if cfg else 'by_date_range'
        if start_date is None:
            start_date = await self.get_suggested_start_date()
        provider = self._get_provider(max_requests_per_minute)
        return await self.run_incremental_sync(
            fetch_fn=provider.get_your_data,
            upsert_fn=self.your_repo.bulk_upsert,
            clean_fn=None,
            table_key=self.TABLE_KEY,
            date_col='trade_date',
            sync_strategy=sync_strategy,
            start_date=start_date,
            end_date=end_date,
            max_requests_per_minute=max_requests_per_minute,
            api_limit=api_limit,
        )

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

    async def get_suggested_start_date(self):
        """增量同步建议起始：min(今天-default_days, 上次同步结束日)"""
        cfg = await asyncio.to_thread(SyncConfigRepository().get_by_table_key, self.TABLE_KEY)
        default_days = (cfg.get('incremental_default_days') or 7) if cfg else 7
        candidate = (datetime.now() - timedelta(days=default_days)).strftime('%Y%m%d')
        last_end = await asyncio.to_thread(
            self.sync_history_repo.get_last_end_date, self.TABLE_KEY, 'incremental'
        )
        return last_end if (last_end and last_end < candidate) else candidate
```

**`strategy` 由 API 端点从 `sync_configs.full_sync_strategy` 读取后传给 Celery task**，Service 层的默认值只作兜底。

**增量同步 API 端点路由规则**：`POST /api/{table}/sync-async`（无 `code` 参数）从 `sync_configs.incremental_task_name` 读取任务名，通过 `celery_app.send_task(task_name)` 分发，而**不是**硬编码任务名。这确保同步配置页面的"增量同步"按钮执行正确的 Celery 任务。

**增量同步 Celery 任务的无参数处理**：Celery 增量任务被无参数调用时（来自同步配置页面或定时调度），必须调用 `service.sync_incremental()` 而非原始 sync 方法。`sync_incremental()` 从 `sync_configs.incremental_default_days` 读取回看天数，自动计算日期范围。对于特殊接口：

| Tushare 接口约束 | sync_incremental 实现方式 |
|-----------------|------------------------|
| 支持 `start_date`/`end_date` | `run_incremental_sync(sync_strategy='by_date_range')` 自动切片+翻页 |
| 仅支持 `trade_date`（如 cyq_perf） | `run_incremental_sync(sync_strategy='by_date', date_param='trade_date')` 逐日切片 |
| 仅支持 `ann_date`（如 dividend, disclosure_date） | 手动按 ann_date 逐日循环调用底层 sync 方法 |
| 仅支持 `trade_date`（如 ggt_top10） | 从 TradingCalendarRepository 获取交易日列表，逐日请求 |
| `ts_code` 必填（如 fina_audit） | 遍历全部上市股票，逐只请求（5 并发） |

**`FULL_HISTORY_LOCK_KEY`**：各 Service 的类常量，全量同步任务通过 `redis_lock.acquire(YourService.FULL_HISTORY_LOCK_KEY, ...)` 引用，避免在任务文件中重复定义。

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
| `incremental_task_name` | Celery 增量任务名；同步配置页"增量同步"按钮通过此字段路由，不得硬编码 |
| `incremental_default_days` | 增量回看天数；`get_suggested_start_date()` 用此值计算候选起始日，默认 7 |
| `incremental_sync_strategy` | `by_date_range`/`by_ts_code`/`by_date` 等；NULL=由 Service 使用默认值 |

**`FULL_SYNC_REDIS_KEYS`（在 `sync_dashboard.py` 中维护）**：记录各表全量同步的 Redis Set key。新增支持全量续继的表时**必须**同步更新，否则同步配置页面无法查询/清除进度。

**`release_stale_lock(table_key)`**：所有全量同步 API 端点在提交 Celery task 前必须调用，自动清除因任务 revoke 或 worker 崩溃留下的残留 Redis lock。

### 同步端点公共分发器（`api/sync_utils.py`）

无业务参数的标准同步端点（`POST /api/{table}/sync-async` 和 `/sync-full-history`）必须使用 `sync_utils` 的两个分发器，不再手写 `release_stale_lock` + `send_task` + `TaskHistoryHelper.create_task_record` 样板：

```python
from app.api.sync_utils import dispatch_incremental_sync, dispatch_full_history_sync

@router.post("/sync-async")
@handle_api_errors
async def sync_async(current_user: User = Depends(require_admin)):
    return await dispatch_incremental_sync(
        table_key='daily_basic',
        display_name='每日指标增量同步',
        fallback_task_name='tasks.sync_daily_basic_incremental',
        user_id=current_user.id,
        source='daily_basic_page',
    )

@router.post("/sync-full-history")
@handle_api_errors
async def sync_full_history(concurrency: Optional[int] = Query(None), current_user: User = Depends(require_admin)):
    return await dispatch_full_history_sync(
        table_key='daily_basic',
        display_name='每日指标全量历史同步',
        task_name='tasks.sync_daily_basic_full_history',
        user_id=current_user.id,
        source='daily_basic_page',
        concurrency=concurrency,
        default_concurrency=8,
    )
```

需要传业务参数（如 `ts_code`、`trade_date`）的端点仍保留手写实现（参考 `adj_factor.py`）。

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
quotes = stock_quote_cache.get_quotes_sync(ts_codes)
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

## 数据表字段格式说明

| 表 | 字段 | 格式 | 说明 |
|----|------|------|------|
| `stock_daily` | `code` | `000002.SZ` | ts_code 格式，非纯数字 |
| `stock_daily` | `date` | `DATE`（YYYY-MM-DD） | Repository 日期参数须用 YYYY-MM-DD |
| `stock_basic` | `code` | `000002` | 纯6位数字 |
| `stock_basic` | `ts_code` | `000002.SZ` | 完整格式 |
| `moneyflow_stock_dc` | `net_amount` | 万元 | 非元，格式化时注意换算 |
| `stk_holdernumber` | `end_date` | YYYYMMDD | 同一季报可能有多条（精确日期不同），按 `end_date[:6]`（YYYYMM）去重 |
| `hk_hold` | `code` | `90000` | 港交所原始代码，**不是** A 股代码；按 A 股查询须用 `ts_code` 字段 |
| `daily_basic` | `total_mv` | 万元 | 市值单位为万元，≥1万万即≥1亿，格式化用 `_fmt_wan` |

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
- [ ] Tushare Provider 添加 `get_your_data()` 方法（用 `_query` + `_build_params`，**必须包含 `limit`/`offset` 参数**以支持 `run_incremental_sync` 翻页）
- [ ] `sync_configs` 表登记（`105_create_sync_configs.sql` 追加并重新执行）
- [ ] `FULL_SYNC_REDIS_KEYS` 更新（`sync_dashboard.py`）
- [ ] `celery_worker` 重启并验证任务注册
- [ ] 增量同步 API 端点路由：读 `sync_configs.incremental_task_name`，用 `celery_app.send_task(task_name)` 分发（不硬编码任务名）
- [ ] Service 实现 `sync_incremental()`、`sync_full_history()`、`get_suggested_start_date()` 三个方法
- [ ] Service 定义 `FULL_HISTORY_LOCK_KEY` 类常量，全量任务通过类引用（`YourService.FULL_HISTORY_LOCK_KEY`）
- [ ] `sync_configs` 表填写 `incremental_task_name`、`incremental_default_days`、`incremental_sync_strategy`
- [ ] 同步完成后必须记录 `sync_history`（TushareSyncBase 自动记录；其他 Service 手动调用 `sync_history_repo.create()` / `.complete()`）
- [ ] 若新表被分析功能依赖，在 `analysis_cache_service.py` 的 `ANALYSIS_DEPENDENCIES` 中注册

---

## AI 分析输出解析（ai_output_parser + Pydantic 模型）

AI 返回的 JSON 通过统一的解析管道处理，替代各 Service 中分散的正则提取。

**解析流程**：`ai_output_parser.parse_ai_json(response, ModelClass)` → 提取 JSON 文本 → Pydantic 校验 → 失败降级为 `parse_ai_json_or_dict()` 原始 dict。

**Pydantic 模型**（`schemas/ai_analysis_result.py`）：

| 模型 | 使用场景 | 调用位置 |
|------|---------|---------|
| `SentimentAnalysisResult` | 市场情绪分析 | `sentiment_ai_analysis_service._parse_ai_response()` |
| `CollisionAnalysisResult` | 盘前碰撞分析 | `premarket_analysis_service._parse_collision_response()` |
| `StockExpertAnalysisResult` | 个股专家（游资/中线/长线/CIO/宏观风险） | `stock_ai_analysis._extract_json_and_score()` |

**评分提取**：`StockExpertAnalysisResult.extract_score()` 按优先级查找 `final_score.score` → `comprehensive_score` → `score`。

**多专家并行分析**：`POST /api/stock-ai-analysis/generate-multi` 通过 `asyncio.gather` 并行调用多个专家，数据收集只做一次（`build_stock_prompt` 缓存）。可选 `include_cio=true` 串联 CIO Agent 综合决策。`_DEFAULT_TEMPLATE_KEYS`（`stock_ai_analysis.py`）维护 `analysis_type → template_key` 映射。

**CIO Agent 模式**（Phase 3）：当 `analysis_type == "cio_directive"` 时，自动走 LangChain Agent 路径（而非普通 LLM 调用）：
- **Agent Service**：`services/cio_agent_service.py` — 使用 `langchain.agents.create_agent()` 创建 LangGraph Agent。**不维护任何 prompt 模板**，`run_agent()` 必传 `system_prompt` / `user_prompt`，由调用方通过 `build_stock_prompt()` 渲染数据库 `cio_directive_v1` 模板得到。
- **Tool 定义**：`services/langchain_tools.py` — 7 个 `@tool` 装饰的异步函数，各对应 `StockDataCollectionService` 的一个 `_get_xxx()` 方法
- **工作方式**：Agent 根据其他专家结论和自身判断，有选择地调用工具查询数据，而非一次性收集全部 9 维数据
- **约束**：`max_iterations=5`（LangGraph `recursion_limit=11`），超时 120 秒
- **兼容性**：非 CIO 类型分析不受影响，保持原有直接调用方式

**CIO 专家输出注入契约**（`/generate-multi` 的 `include_cio=true` 路径）：
- 前置专家完成后，端点把每个专家的**完整 `analysis_text`（不截断）**通过 `build_stock_prompt(expert_outputs={...})` 注入 CIO 模板的占位符。映射关系：

  | 前置专家 `analysis_type` | CIO 模板占位符 |
  |--------------------------|---------------|
  | `hot_money_view` | `{{ hot_money_summary }}` |
  | `midline_industry_expert` | `{{ midline_summary }}` |
  | `longterm_value_watcher` | `{{ longterm_summary }}` |

- 共享常量：`prompt_templates.EXPERT_OUTPUT_PLACEHOLDERS`（占位符列表）、`stock_ai_analysis._EXPERT_TYPE_TO_CIO_PLACEHOLDER`（映射）。新增 CIO 占位符必须同步两处。
- `build_stock_prompt` 在 `expert_outputs=None` 或某占位符未提供时，渲染为"（本次未提供该专家结论）"，避免 LLM 看到原始 `{{ ... }}` 语法。
- `/generate` 单 CIO 路径不传 `expert_outputs`，Agent 完全依靠工具自查。
- `llm_call_logs` 与 `stock_ai_analysis.prompt_text` 均记录**完整渲染后的 prompt**（system + user），便于回溯 CIO 实际输入；不再写形如 `[CIO Agent] ts_code=...` 的占位日志。
- **共用 helper**：`stock_ai_analysis._prepare_cio_prompt()` 集中"渲染模板 + 组装 provider 配置 + 拼 full_prompt"三步，两个 CIO 调用点都走它。

---

## 分析结果缓存（AnalysisCacheService）

基于 `sync_history` 的依赖检测，避免底层数据未变时重复计算分析结果。

**核心文件**：`services/analysis_cache_service.py`

**原理**：
1. 缓存写入时，记录依赖表的 `MAX(completed_at)` 时间戳
2. 缓存读取时，比较当前依赖表时间戳与缓存中的时间戳
3. 一致 → 命中缓存；不一致 → 重新计算

**使用方式**：

```python
from app.services.analysis_cache_service import get_analysis_cache_service

cache = get_analysis_cache_service()

# 读取缓存（依赖表未变更则返回数据，否则返回 None）
result = await cache.get_cached('features', {'code': '000001.SZ', ...})

# 写入缓存
await cache.set_cached('features', {'code': '000001.SZ', ...}, result_data)
```

**依赖映射**（`ANALYSIS_DEPENDENCIES`）：每个分析类型声明依赖的 `sync_configs.table_key` 列表，新增同步表时须同步更新。

**`sync_history` 覆盖要求**：所有 61 个同步表的同步操作必须记录 `sync_history`，否则缓存失效检测不准确。当前覆盖方式：
- `TushareSyncBase.run_incremental_sync()` — 自动记录（需 Service 定义 `self.sync_history_repo`）
- `BaseSyncService._sync_data_template()` — 自动记录（当 Service 没有 `sync_history_repo` 属性时）
- 独立 Service（`StockListSyncService`、`NewStockService`、`TradingCalendarService`）— 手动记录

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
