# Claude Development Guide

## 开发环境启动

使用以下命令启动完整的开发环境：

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

这个命令会：
1. 使用基础配置文件 `docker-compose.yml`
2. 加载开发环境覆盖配置 `docker-compose.dev.yml`
3. 在后台运行容器 (`-d`)
4. 重新构建镜像 (`--build`)

## 项目结构

- `/admin` - 管理后台前端项目 (Next.js)
- `/backend` - 后端API服务 (FastAPI)
- `/core` - 核心业务逻辑
- `/db_init` - 数据库初始化脚本

## Frontend 自选股功能（用户股票列表）

已登录用户可在 `/stocks` 页面管理自选股列表。未登录用户不可见任何列表相关 UI。

### 数据库表
- `user_stock_lists`：列表元数据（`id, user_id, name, description, timestamps`），UNIQUE(user_id, name)
- `user_stock_list_items`：成分股（`id, list_id, ts_code, added_at`），UNIQUE(list_id, ts_code)，CASCADE 删除
- 迁移脚本：`db_init/migrations/095_create_user_stock_lists.sql`

### 后端文件
- Repository：`backend/app/repositories/user_stock_list_repository.py`
- Service：`backend/app/services/user_stock_list_service.py`
- API：`backend/app/api/endpoints/user_stock_lists.py`（路由前缀 `/user-stock-lists`）
- 限制：每用户最多 20 个列表，每列表最多 500 只股票

### API 端点（需登录 Token）
```
GET    /api/user-stock-lists              获取我的所有列表
POST   /api/user-stock-lists              创建列表
PUT    /api/user-stock-lists/{id}         重命名/修改描述
DELETE /api/user-stock-lists/{id}         删除列表（级联删除成分股）
GET    /api/user-stock-lists/{id}/items   获取列表股票（含行情）
GET    /api/user-stock-lists/{id}/ts-codes  仅返回 ts_code 列表（轻量）
POST   /api/user-stock-lists/{id}/items   批量添加股票
DELETE /api/user-stock-lists/{id}/items   批量移除股票（body: {ts_codes:[...]}）
```

### 前端文件
- Zustand Store：`frontend/src/stores/stock-list-store.ts`（无持久化，服务端存储）
- 主页面：`frontend/src/app/stocks/page.tsx`（`AddToListDialog`, `RenameListDialog`）
- API 方法：`frontend/src/lib/api-client.ts`（`getUserStockLists`, `createStockList`, `renameStockList`, `deleteStockList`, `getStockListItems`, `addStocksToList`, `removeStocksFromList`）
- 类型定义：`frontend/src/types/stock.ts`（`StockList`, `StockListItem`）

### ⚠️ stock_realtime 表的 JOIN 注意事项
`stock_realtime` 表的主键是 `code`（纯数字代码，如 `000001`），**不是** `ts_code`。
在需要关联行情数据时，必须先通过 `stock_basic` 桥接：

```sql
LEFT JOIN stock_basic sb ON sb.ts_code = {your_table}.ts_code
LEFT JOIN stock_realtime sr ON sr.code = sb.code   -- ✅ 正确
-- LEFT JOIN stock_realtime sr ON sr.ts_code = ... -- ❌ 错误，该列不存在
```

### 前端 ts_code 转换
`stocks/page.tsx` 中的 `toTsCode()` 将纯数字代码转换为带交易所后缀的格式：
- `6xxxxx` → `.SH`（上交所）
- `4xxxxx` / `8xxxxx` → `.BJ`（北交所）
- 其他 → `.SZ`（深交所）

## 已移除功能

以下功能已从系统中移除（2026-03-25）：

1. **概念标签管理**
   - 概念板块管理页面（`/concepts`）
   - 股票概念关联功能
   - 概念筛选功能
   - 相关数据库表：`concept`、`stock_concept`
   - 相关API：`/api/concepts/*`、`/api/stocks/**/concepts`
   - 相关Repository：`ConceptRepository`
   - 相关Service：`ConceptSyncService`

2. **股票管理页面**
   - 股票列表管理页面（`/stocks`）
   - 股票详情页面（`/stocks/[code]`）
   - 注：股票相关API和数据保留，仅移除前端页面

3. **数据中心**
   - 数据初始化页面（`/sync/initialize`）
   - 数据中心导航页面（`/sync`）
   - 扩展数据页面（`/sync/extended`）
   - 注：数据同步API和功能保留，仅移除前端页面

## Admin 项目新增功能

### 面包屑导航

已为 Admin 项目添加了全局面包屑导航功能：

#### 组件位置
- `/admin/components/ui/breadcrumb.tsx` - 面包屑UI组件
- `/admin/hooks/useBreadcrumbs.ts` - 自动生成面包屑的Hook
- `/admin/components/layouts/AdminLayout.tsx` - 在布局层集成面包屑

#### 实现特点

1. **全局显示**：
   - 面包屑在 AdminLayout 布局层自动显示
   - 位置：顶部 Header 下方，页面内容上方
   - 所有页面自动拥有面包屑导航

2. **自动生成**：
   - 根据当前路由自动生成面包屑
   - 智能识别路由层级关系
   - 支持动态路由参数（如股票代码、策略ID等）

3. **响应式设计**：
   - 长路径在移动端自动折叠
   - 中间项折叠为下拉菜单
   - 保持首页和最后两项可见

4. **PageHeader 组件**：
   - 现在专注于页面标题、描述和操作按钮
   - 不再包含面包屑功能
   - 支持 `details` prop：传入 ReactNode，标题旁会出现 ⓘ 图标，点击以 Popover 展示补充信息（如接口名称、文档链接）
   - 用法更简洁：
   ```tsx
   <PageHeader
     title="页面标题"
     description="页面描述"
     actions={<Button>操作</Button>}
     details={<>
       <div>接口：your_api</div>
       <a href="https://tushare.pro/document/2?doc_id=xxx" target="_blank" rel="noopener noreferrer">查看文档</a>
     </>}
   />
   ```

#### 父级导航页面
为了支持面包屑的多级导航，已创建以下父级菜单页面：
- `/settings` - 系统设置导航页
- `/sync` - 数据同步导航页
- `/logs` - 日志管理导航页
- `/monitoring` - 系统监控导航页
- `/boardgame` - 打板专题导航页
- `/reference-data` - 参考数据导航页（个股异常波动等）
- `/moneyflow` - 资金流向导航页（个股/板块/大盘/沪深港通）
- `/margin` - 两融数据导航页（融资融券汇总/明细/标的/转融资）
- `/features` - 特色数据导航页（筹码分布/北向持股/集合竞价/技术指标/机构调研等）

这些页面以卡片形式展示子功能入口，解决了中间层级页面点击的问题。

#### 面包屑开发注意事项

1. **路由与菜单归属一致**：页面的 URL 路径应与其所属菜单一致。例如打板专题下的页面应放在 `/boardgame/` 路径下，而非 `/data/`。

2. **`parentOverrides` 机制**：当页面 URL 首段与菜单归属不一致时，在 `useBreadcrumbs.ts` 的 `parentOverrides` 中按完整路径覆盖父级显示名称和图标。目前资金流向（`/moneyflow/*`）和两融数据（`/margin/*`）已迁移到独立路由，不再需要 override。

3. **图标与菜单一致**：`routeIconMap` 中的图标必须与 `AdminLayout.tsx` 中对应菜单项的图标完全一致。

4. **新增菜单项时**：同步在 `routeLabelMap` 和 `routeIconMap` 中添加对应的路由 segment 映射。

**注意**：市场情绪相关功能已精简（2026-03-25），移除了以下功能：
- 市场情绪数据管理（大盘情绪指标）
- 涨停板池（连板天梯、炸板统计）
- 龙虎榜数据查询
- 情绪周期分析

保留功能：AI 情绪分析、盘前预期管理

#### AI 情绪分析数据源（2026-03-25 重构）

AI 情绪分析的数据来源已从已删除的旧表迁移至打板专题数据表：

| 数据 | 旧表（已删除） | 新表（打板专题） |
|------|--------------|----------------|
| 涨跌停统计 | `limit_up_pool` | `limit_list_d` |
| 连板天梯 | `limit_up_pool.continuous_ladder` | `limit_step` |
| 龙虎榜 | `dragon_tiger_list` | `top_list` |
| 板块统计 | 无 | `limit_cpt_list` |
| 大盘指数 | `market_sentiment_daily` | 无（已移除，不影响分析质量） |

**关键实现**：`SentimentAIAnalysisService._fetch_sentiment_data()` 和 `_build_prompt()` 是单一数据源，同时供 Celery 定时任务和 `GET /api/sentiment/ai-analysis/preview-prompt` 端点调用，避免逻辑重复。

**FastAPI 路由注意事项**：`/preview-prompt` 路由必须注册在 `/{date}` 通配符路由**之前**，否则会被拦截。参见 `backend/app/api/endpoints/sentiment/ai_analysis.py`。

### 任务管理面板

Admin项目采用统一的任务管理面板，位于Header右侧：

#### 特点
- **统一入口**：通过Header右侧的任务图标访问
- **全局轮询**：Header组件统一处理轮询（每5秒更新状态，每30秒同步历史）
- **即时更新**：打开面板或执行任务后立即触发轮询，无需等待定时周期
- **任务分组**：按任务类型（数据同步、AI分析、策略回测等）分组显示
- **进度显示**：支持显示任务进度条
- **状态管理**：使用Zustand store统一管理任务状态
- **错误提示**：显示失败任务的错误信息
- **数据持久化**：任务历史记录存储在数据库中，支持历史查询和统计

#### 任务历史持久化架构

**数据库表结构** (`celery_task_history`):
- 记录所有 Celery 任务的执行历史
- 包含任务状态、开始时间、完成时间、耗时、结果、错误信息等
- 支持任务分组、用户关联、进度跟踪

**自动更新机制** (Celery 信号):
- `task_prerun`: 任务开始时记录 `started_at`，状态改为 `running`
- `task_success`: 任务成功时记录 `completed_at`、`duration_ms`、`result`
- `task_failure`: 任务失败时记录 `error`、`duration_ms`
- `task_revoked`: 任务被撤销时标记为失败

**时间处理**:
- 数据库存储本地时间 (`datetime.now()`)
- API 返回 UTC 格式 (ISO 8601 + Z 后缀，如 `2026-03-18T16:52:54Z`)
- 前端浏览器自动转换为本地时间显示

**注意事项**:
- 使用 `started_at` 而非 `created_at` 计算任务耗时
- 每个信号处理器使用**独立的 psycopg2 直连**（`_get_direct_conn()`），不使用 `DatabaseManager` 单例 — 因为 fork pool worker 继承了父进程的连接池，该池在 fork 后已损坏，使用单例会导致 UPDATE 静默失败（任务状态卡在 `pending`）
- Celery 5.x 中从 `sender.request.id` 获取 task_id
- `celery_signals.py` 中每次信号触发时新建 psycopg2 直连，用完立即关闭，不影响业务连接池

#### 轮询机制

**全局轮询架构**：
- Header 组件启用两个全局 Hook：
  - `useTaskPolling(true, 5000)` - 每5秒轮询活动任务状态
  - `useTaskSync(true, 30000)` - 每30秒同步后端任务历史
- TaskPanel 和其他组件不做重复轮询，避免多余的 API 调用

**手动触发机制**：
- `useTaskPolling` 将轮询函数注册到 `task-store`
- 其他组件可通过 `triggerPoll()` 手动触发一次轮询
- 应用场景：
  - 打开任务面板时立即获取最新状态
  - 执行任务后立即更新 Header 图标

**示例代码**：
```typescript
const { triggerPoll } = useTaskStore()

// 执行任务后立即触发轮询
await apiClient.executeTask(taskId)
triggerPoll()  // Header 图标即时更新
```

#### 相关文件
- `/admin/components/TaskPanel.tsx` - 任务面板组件
- `/admin/components/TaskStatusIcon.tsx` - Header中的任务图标
- `/admin/components/layout/Header.tsx` - 全局轮询入口
- `/admin/stores/task-store.ts` - 任务状态管理（包含轮询触发器）
- `/admin/hooks/useTaskPolling.ts` - 任务状态轮询Hook
- `/admin/hooks/useTaskSync.ts` - 任务历史同步Hook
- `/backend/app/celery_signals.py` - Celery信号处理器（自动更新任务历史）
- `/backend/app/api/endpoints/celery_tasks.py` - 任务历史API
- `/backend/app/models/celery_task_history.py` - 任务历史模型
- `/db_init/migrations/007_create_celery_task_history.sql` - 数据库迁移

#### 数据同步页面异步任务集成模式

为了提供一致的用户体验，**所有数据同步页面应该使用异步任务模式**，而不是同步阻塞模式。

**实现步骤**：

1. **后端API**：创建异步执行端点（如 `/sync-async`）
   ```python
   @router.post("/sync-async")
   async def sync_data_async(...):
       # 提交Celery任务
       celery_task = your_task.apply_async(kwargs={...})

       # 记录到celery_task_history表
       await asyncio.to_thread(db_manager._execute_update, ...)

       return ApiResponse.success(data={
           "celery_task_id": celery_task.id,
           "task_name": "tasks.your_task",
           "display_name": "任务显示名称",
           "status": "pending"
       })
   ```

2. **前端API客户端**：添加异步执行方法
   ```typescript
   async syncDataAsync(params?: any): Promise<ApiResponse<{
     celery_task_id: string
     task_name: string
     display_name: string
     status: string
   }>>
   ```

3. **前端页面**：使用任务存储和轮询机制
   ```typescript
   const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
   const activeCallbacksRef = useRef<Map<string, any>>(new Map())

   // 从 task store 实时派生同步状态——不要用本地 useState(false)
   // 只要后台 Celery 任务仍在运行，syncing 为 true，按钮保持禁用
   const syncing = isTaskRunning('tasks.your_celery_task_name')

   const handleSync = async () => {
     const response = await apiClient.syncDataAsync(params)

     if (response.code === 200 && response.data) {
       const taskId = response.data.celery_task_id

       addTask({
         taskId,
         taskName: response.data.task_name,
         displayName: response.data.display_name,
         taskType: 'data_sync',
         status: 'running',
         progress: 0,
         startTime: Date.now()
       })

       // 注册完成回调，任务完成后自动刷新数据
       const completionCallback = (task: any) => {
         if (task.status === 'success') {
           loadData().catch(() => {})
           toast.success('数据同步完成')
         }
         unregisterCompletionCallback(taskId, completionCallback)
         activeCallbacksRef.current.delete(taskId)
       }
       activeCallbacksRef.current.set(taskId, completionCallback)
       registerCompletionCallback(taskId, completionCallback)

       triggerPoll()
     }
   }

   // 组件卸载时清理未完成的回调
   useEffect(() => {
     return () => {
       const callbacks = activeCallbacksRef.current
       callbacks.forEach((callback, taskId) => {
         unregisterCompletionCallback(taskId, callback)
       })
       callbacks.clear()
     }
   }, [])
   ```

**优势**：
- ✅ 异步执行，不阻塞前端
- ✅ 任务在任务面板实时显示
- ✅ Header图标即时更新
- ✅ 任务历史持久化到数据库
- ✅ 统一的用户体验

**同步弹窗选日期模式**（当同步需要用户指定日期时）：

同步按钮不直接调用 API，而是打开 Dialog 让用户选择日期（可留空），确认后再提交任务：

```typescript
const [syncDialogOpen, setSyncDialogOpen] = useState(false)
const [syncDate, setSyncDate] = useState<Date | undefined>(undefined)

// 按钮只负责打开弹窗
<Button onClick={() => setSyncDialogOpen(true)} disabled={syncing}>同步数据</Button>

// 弹窗内确认后才提交
const handleSyncConfirm = async () => {
  setSyncDialogOpen(false)
  const syncDateStr = syncDate
    ? `${syncDate.getFullYear()}-${String(syncDate.getMonth() + 1).padStart(2, '0')}-${String(syncDate.getDate()).padStart(2, '0')}`
    : undefined
  const response = await api.syncAsync(syncDateStr ? { trade_date: syncDateStr } : {})
  // ... 提交任务逻辑
}

<Dialog open={syncDialogOpen} onOpenChange={setSyncDialogOpen}>
  <DialogContent className="sm:max-w-[400px]">
    <DialogHeader>
      <DialogTitle>同步数据</DialogTitle>
      <DialogDescription>选择同步日期（留空则同步最新交易日数据）。</DialogDescription>
    </DialogHeader>
    <div className="py-4">
      <label className="text-sm font-medium mb-2 block">交易日期（可选）</label>
      <DatePicker date={syncDate} onDateChange={setSyncDate} placeholder="留空同步最新交易日" />
    </div>
    <DialogFooter>
      <Button variant="outline" onClick={() => setSyncDialogOpen(false)}>取消</Button>
      <Button onClick={handleSyncConfirm} disabled={syncing}>确认同步</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

**适用场景**：积分消耗较高、同步范围影响较大、用户需要精确控制同步日期的页面。

**已实现的页面**（所有页面均遵循上述异步模式标准实践：同步弹窗与查询日期解耦、`isTaskRunning` 派生 `syncing`、`DataTable mobileCard`、左文字右图标统计卡片、`toDateStr` 本地时间安全）：

| 页面 | 路由 | 特殊说明 |
|------|------|---------|
| 定时任务配置 | `/settings/scheduler` | |
| 沪深港通资金流向 | `/moneyflow/hsgt` | 趋势图用 LineChart |
| 大盘资金流向 | `/moneyflow/mkt-dc` | 数据单位亿元 |
| 板块资金流向 | `/moneyflow/ind-dc` | "全部"同步依次提交行业/概念/地域三任务；TOP 20 图表 |
| 个股资金流向（Tushare） | `/moneyflow/stock` | 数据单位万元 |
| 个股资金流向（DC） | `/moneyflow/stock-dc` | 数据单位亿元 |
| 融资融券交易汇总 | `/margin/summary` | |
| 融资融券交易明细 | `/margin/detail` | ETF名称从 margin_secs 回退；ETF不可点击跳转 |
| 融资融券标的 | `/margin/secs` | isStock 排除5/1/821前缀 |
| 转融资交易汇总 | `/margin/slb-len` | |
| 龙虎榜每日明细 | `/boardgame/top-list` | |
| 龙虎榜机构明细 | `/boardgame/top-inst` | |
| 涨跌停列表 | `/boardgame/limit-list` | |
| 连板天梯 | `/boardgame/limit-step` | |
| 最强板块统计 | `/boardgame/limit-cpt` | |
| 卖方盈利预测 | `/features/report-rc` | |
| 个股异常波动 | `/reference-data/stk-shock` | |
| 个股严重异常波动 | `/reference-data/stk-high-shock` | |
| 交易所重点提示证券 | `/reference-data/stk-alert` | |
| 股权质押统计 | `/reference-data/pledge-stat` | |
| 股票回购 | `/reference-data/repurchase` | syncStartDate/syncEndDate 独立 |
| 限售股解禁 | `/reference-data/share-float` | |
| 股东人数 | `/reference-data/stk-holdernumber` | |
| 大宗交易 | `/reference-data/block-trade` | |
| 股东增减持 | `/reference-data/stk-holdertrade` | syncStartDate/syncEndDate 独立 |
| 利润表 | `/financial/income` | 同步接口需 YYYYMMDD 格式，查询需 YYYY-MM-DD |
| 资产负债表 | `/financial/balancesheet` | 同上 |
| 现金流量表 | `/financial/cashflow` | period 用 DatePicker |
| 业绩预告 | `/financial/forecast` | 含 syncForecastType 选项 |
| 业绩快报 | `/financial/express` | 所有日期字段用 Date \| undefined + DatePicker |
| 分红送股 | `/financial/dividend` | |
| 财务指标 | `/financial/fina-indicator` | 含 syncPeriod 选项 |
| 财务审计意见 | `/financial/fina-audit` | ts_code 为同步必填项 |
| 主营业务构成 | `/financial/fina-mainbz` | 含 type 选项 |
| 财报披露计划 | `/financial/disclosure-date` | |
| 筹码分布 | `/features/cyq-chips` | 2000积分/次，单次最大1000行 |
| 每日筹码及胜率 | `/features/cyq-perf` | 2000积分/次，含获利比例/成本分布 |
| CCASS持股汇总 | `/features/ccass-hold` | 5000积分/次 |
| CCASS持股明细 | `/features/ccass-hold-detail` | 8000积分/次；同步需至少填写一个条件 |
| 沪深港股通持股明细 | `/features/hk-hold` | 2000积分/次；2024-08-20起季度披露 |
| 股票开盘集合竞价 | `/features/stk-auction-o` | 需股票分钟权限，单次最大10000行 |
| 股票收盘集合竞价 | `/features/stk-auction-c` | 需股票分钟权限，单次最大10000行 |
| 神奇九转指标 | `/features/stk-nineturn` | 6000积分/次；数据从2023年起；30天默认日期范围 |
| AH股比价 | `/features/stk-ah-comparison` | 5000积分/次；数据从2025-08-12起 |
| 机构调研表 | `/features/stk-surv` | 5000积分/次；单次最大100行；支持接待方式/机构类型筛选 |
| 券商每月荐股 | `/features/broker-recommend` | 6000积分/次；每月1-3日更新；同步弹窗选月度 |
| 股票日线数据 | `/market/daily` | 120积分/次；未复权数据（daily接口不支持adj参数）；全市场同步自动推算下一待补交易日；统计接口仅初始化时调用一次 |
| 每日停复牌信息 | `/market/suspend` | |
| 每日涨跌停价格 | `/market/stk-limit-d` | 2000积分/次；每交易日8:40更新 |
| 沪深股通十大成交股 | `/market/hsgt-top10` | 同步不传 tsCode/marketType |
| 港股通十大成交股 | `/market/ggt-top10` | 17个字段 |
| 港股通每日成交统计 | `/market/ggt-daily` | 2000积分/次；数据从2014年起 |
| 港股通每月成交统计 | `/market/ggt-monthly` | 5000积分/次；同步弹窗选月份 |
| 复权因子 | `/market/adj-factor` | 2000积分/次；支持单只历史或单日全市场查询 |
| 每日指标 | `/market/daily-basic` | 2000积分/次；17个核心指标 |
| 新股列表 | `/sync/new-stocks` | 独立 `new_stocks` 表；增量同步弹窗选天数（默认90天）；全量同步90天/片×5并发（new_share 单次上限2000条） |
| ST股票列表 | `/data/stock-st` | 全量同步特殊处理（2交易日/批，10并发） |
| 股票列表 | `/data/stock-list` | 17个字段；同步全状态 |
| 东方财富板块成分 | `/boardgame/dc-member` | 6000积分/次；板块名称从 dc_index 注入 |
| 东方财富板块数据 | `/boardgame/dc-index` | 6000积分/次；leading_stock 规避 PG 保留字；"全部"同步消耗18000积分 |
| 东财概念板块行情 | `/boardgame/dc-daily` | 6000积分/次；名称从 dc_index 注入 |
| 交易日历 | `/data/trade-cal` | 2000积分/次；支持7个交易所 |

**注意**：旧的同步阻塞API（如 `/sync`）保留用于向后兼容，但新开发的功能应优先使用异步模式。

### 全量同步 + 清空数据按钮（BulkOpsButtons）

所有数据页面统一提供"全量同步"和"清空数据"两个辅助按钮，使用通用组件和 Hook 实现。

#### 组件与 Hook

- `admin/components/common/BulkOpsButtons.tsx` — 按钮组 UI（全量同步 + 清空确认弹窗）
- `admin/hooks/useDataBulkOps.ts` — 业务逻辑 Hook（读取系统配置、提交任务、清空表）
- `backend/app/api/endpoints/data_ops.py` — 后端清空接口（白名单机制，`POST /api/data-ops/clear/{table_key}`）

#### 页面使用示例

```tsx
import { useDataBulkOps } from '@/hooks/useDataBulkOps'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { apiClient } from '@/lib/api-client'

const {
  handleFullSync,
  handleClear,
  fullSyncing,
  isClearing,
  isClearDialogOpen,
  setIsClearDialogOpen,
  cleanup,
  earliestHistoryDate,
} = useDataBulkOps({
  tableKey: 'daily_basic',                                     // data_ops 白名单中的 key
  syncFn: (params) => apiClient.post('/api/daily-basic/sync-async', null, { params }),
  taskName: 'tasks.sync_daily_basic',                          // 用于 isTaskRunning 派生状态
  onSuccess: () => loadData(1),
})

// 在 useEffect cleanup 中调用
useEffect(() => { return () => cleanup() }, [])

// 放在 PageHeader actions 中
<BulkOpsButtons
  onFullSync={handleFullSync}
  onClearConfirm={handleClear}
  isClearDialogOpen={isClearDialogOpen}
  setIsClearDialogOpen={setIsClearDialogOpen}
  fullSyncing={fullSyncing}
  isClearing={isClearing}
  earliestHistoryDate={earliestHistoryDate}
  tableName="每日指标"
/>
```

#### 设计要点

- **全量同步日期**：Hook 从 `useConfigStore().dataSource.earliest_history_date` 读取，格式 `YYYY-MM-DD`，转为 `YYYYMMDD` 后以 `start_date` 参数传给 `syncFn`（不传 `end_date`，由后端同步到今天）
- **不传查询日期**：`handleFullSync` 内部只传 `start_date`，绝不传页面筛选器当前的日期，防止全量同步变为重复同步旧日期
- **清空接口**：后端统一用白名单 `CLEARABLE_TABLES` 映射 `table_key → 实际表名`，防止任意表注入；新增数据表时需同步更新 `data_ops.py` 中的白名单
- **哪些页面不需要全量同步按钮**：若每次普通同步本身就是全量拉取（如 `stock_basic`/`stock_list`，Tushare 接口无增量模式），则不加全量同步按钮，避免语义重复
- **哪些页面需要全量同步按钮**：有历史数据积累需求、且 Tushare 支持按日期范围查询的接口（如 ST 股票、每日指标、交易日历等）

#### `stock_st` 全量同步的特殊处理

Tushare `stock_st` 接口单次最多返回 1000 条，且不支持 offset 分页，只能按日期范围查询。全量同步时采用：

- **2 交易日为一批**：每次请求覆盖 2 个交易日，约 200-400 条，远低于 1000 上限
- **10 并发**：`asyncio.Semaphore(CONCURRENCY)` 控制并发，每批完成后立即 `bulk_upsert` 写库
- **跳过非交易日**：通过 `TradingCalendarRepository.get_trading_days_between()` 获取交易日列表，避免空请求
- 参数常量 `CHUNK_DAYS = 2`、`CONCURRENCY = 10` 定义在 `stock_st_service.py` 顶部，便于调整

### 板块名称注入（DcIndexRepository.get_board_name_map）

`dc_member`、`dc_daily` 等表只存 `ts_code`，不存板块名称。需要显示名称时，从 `dc_index` 最新一天的数据中查询映射，在 Service 层并发注入，**不做跨表 JOIN**。

**方法位置**：`DcIndexRepository.get_board_name_map()` — `backend/app/repositories/dc_index_repository.py`

**使用方式**（在 Service 层 `asyncio.gather` 中并发获取）：
```python
from app.repositories.dc_index_repository import DcIndexRepository

class YourService:
    def __init__(self):
        self.dc_index_repo = DcIndexRepository()

    async def get_data(self, ...):
        items, total, board_name_map = await asyncio.gather(
            asyncio.to_thread(self.repo.get_by_date_range, ...),
            asyncio.to_thread(self.repo.get_total_count, ...),
            asyncio.to_thread(self.dc_index_repo.get_board_name_map)
        )
        for item in items:
            item['board_name'] = board_name_map.get(item['ts_code'], '')
```

**前端展示**：合并名称+代码，无名称时降级显示纯代码：
```typescript
accessor: (row) => row.board_name ? `${row.board_name}[${row.ts_code}]` : row.ts_code
```

**已接入的 Service**：`DcMemberService`、`DcDailyService`

---

### 股票行情缓存（StockQuoteCache）

**位置**：`backend/app/services/stock_quote_cache.py`

当页面需要展示股票名称、价格、涨跌幅等行情信息，但数据表中只有 `ts_code` 时，使用 `StockQuoteCache` 注入行情数据，避免跨表 JOIN。

**使用方式（异步 Service）**：
```python
from app.services.stock_quote_cache import stock_quote_cache

# 批量获取行情（在异步 Service 方法中调用）
ts_codes = list(dict.fromkeys(item['ts_code'] for item in items))
quotes = await stock_quote_cache.get_quotes_batch(ts_codes)
for item in items:
    item['name'] = quotes.get(item['ts_code'], {}).get('name', '')
```

**使用方式（同步 Service，通过 `asyncio.to_thread` 调用）**：

当 Service 方法是同步方法（被 `asyncio.to_thread` 调用），无法使用 `await`，改用 `_repo.get_quotes()` 同步接口：

```python
from app.services.stock_quote_cache import stock_quote_cache

# 同步 Service 方法内（不能 await）
ts_codes = list(dict.fromkeys(item['ts_code'] for item in items))
quotes = stock_quote_cache._repo.get_quotes(ts_codes)  # 同步调用私有 _repo
for item in items:
    item['name'] = quotes.get(item['ts_code'], {}).get('name', '')
```

**已接入的同步 Service**：`MoneyflowService`（`get_moneyflow_data`、`get_top_stocks`）

**缓存字段**（`get_quotes_batch` 返回）：
```
name, latest_price, pct_change, change_amount, open, high, low, pre_close,
volume, amount, turnover, amplitude, trade_time, price（latest_price 的旧名兼容别名）
```

⚠️ **缓存扩容后需手动刷新 Redis**：若修改了 `_QuoteRepository.get_quotes()` 查询字段，旧缓存条目（字段不全）仍会被返回，需手动清空：
```bash
docker-compose exec redis redis-cli KEYS "stock:quote:*" | xargs docker-compose exec -T redis redis-cli DEL
```

**缓存策略**：
- 数据来源：`stock_basic`（名称）LEFT JOIN `stock_realtime`（实时行情全量字段）
- Redis key：`stock:quote:{ts_code}`
- TTL：交易时间（09:30-11:30 / 13:00-15:00 工作日）= 60s，非交易时间 = 3600s
- 降级：Redis 不可用时直接查数据库

**已接入的 Service**：
- `TopInstService.get_top_inst_data()` — 龙虎榜机构明细
- `MarginDetailService.get_margin_detail_data()` — 融资融券交易明细（含 ETF 名称回退）

#### ETF/基金名称回退（margin_secs）

`StockQuoteCache` 只查 `stock_basic`，不含 ETF/基金。当数据表（如 `margin_detail`）中存在 ETF 标的时，需两步注入名称：

```python
# Service 层（异步）
from app.repositories.margin_secs_repository import MarginSecsRepository

ts_codes = list(dict.fromkeys(item['ts_code'] for item in data))
quotes = await asyncio.to_thread(stock_quote_cache._repo.get_quotes, ts_codes)
# 找出无名称代码，从 margin_secs 补充
missing_codes = [code for code in ts_codes if not quotes.get(code, {}).get('name')]
etf_name_map = await asyncio.to_thread(self.margin_secs_repo.get_name_map, missing_codes) if missing_codes else {}
for item in data:
    name = quotes.get(item['ts_code'], {}).get('name', '')
    if not name:
        name = etf_name_map.get(item['ts_code'], '') or item.get('name', '')
    item['name'] = name
```

**前端非股票不跳转规则**：以下前缀不显示点击样式，不响应跳转：
- `5xxxxx`：上海 ETF/基金
- `1xxxxx`：深圳 ETF/基金
- `821xxx`：北交所债券（如 `821001.BJ` 24京资01）

```typescript
const isStock = (tsCode: string) => {
  const code = tsCode.split('.')[0]
  return !code.startsWith('5') && !code.startsWith('1') && !code.startsWith('821')
}
```

### 股票代码自动补全（resolve_ts_code）

用户输入纯数字代码（如 `000001`），后端自动补全为完整 ts_code（如 `000001.SZ`）。

**使用方式**（在 API 端点中）：
```python
from app.services.stock_quote_cache import stock_quote_cache

resolved_ts_code = await stock_quote_cache.resolve_ts_code(ts_code) if ts_code else None
result = await service.get_data(ts_code=resolved_ts_code, ...)
```

**规则**：输入含 `.` → 直接返回（转大写）；纯数字 → 查 `stock_basic.code` 补全后缀；查不到 → 返回 `None`

**缓存策略**：Redis key `stock:code_map:{pure_code}`，TTL 86400s（交易所后缀极少变化）

**已接入的端点**：
- `GET /api/top-inst` — 龙虎榜机构明细

**前端规范**：只需将 Input placeholder 改为 `如 000001 或 000001.SZ`，无需其他改动。详见 `.claude/skills/stock-code-resolve.md`。

### 同步默认日期规范

**Service 层 sync 方法不得硬编码 `yesterday`**。当 `trade_date=None` 时，根据 Tushare 接口特性选择以下两种正确方式之一：

#### 方式 A：`trade_date` 为可选参数的接口（透传 None）

部分 Tushare 接口（如 `limit_step`、`limit_list_d`）在 `trade_date=None` 时会自动返回最新交易日数据，直接透传 `None` 即可：

```python
if not trade_date:
    logger.info("未指定日期，由 Tushare 返回最新交易日数据")  # ✅ 透传 None
```

#### 方式 B：`trade_date` 为必需参数的接口（从 trading_calendar 取最新交易日）

部分 Tushare 接口（如 `top_list`、`top_inst`）的 `trade_date` 是必需参数，传 `None` 不会返回最新日期，必须从 `TradingCalendarRepository` 查询最新交易日：

```python
from app.repositories.trading_calendar_repository import TradingCalendarRepository

class YourService:
    def __init__(self):
        self.calendar_repo = TradingCalendarRepository()

    async def sync_data(self, trade_date=None):
        if not trade_date:
            trade_date = await asyncio.to_thread(
                self.calendar_repo.get_latest_trading_day
            )
            logger.info(f"未指定日期，使用最新交易日: {trade_date}")  # ✅
```

**错误写法（禁止）**：
```python
if not trade_date:
    yesterday = datetime.now() - timedelta(days=1)
    trade_date = yesterday.strftime('%Y%m%d')  # ❌ 硬编码昨天，非交易日/节假日会同步到错误日期
```

**判断依据**：查看 `core/src/providers/tushare/provider.py` 中对应方法的参数签名，若 `trade_date` 标注为必需参数（无默认值），则使用方式 B。

**已修复文件**：`top_list_service.py`、`top_inst_service.py`（已于 2026-03-25 修复，使用方式 B）

#### 方式 C：查询端点默认日期解析（`resolve_default_trade_date`）

**同步端点**使用方式 A/B 获取最新数据；**查询端点**（`GET /api/xxx`）在用户未传日期时，应自动查询最近有数据的交易日并**回传给前端**，让日期选择器自动回填。

```python
# Service 层：优先今天，否则回退到表中最新交易日，返回 YYYY-MM-DD 格式
async def resolve_default_trade_date(self) -> Optional[str]:
    today = datetime.now().strftime('%Y%m%d')
    has_today = await asyncio.to_thread(self.repo.exists_by_date, today)
    if has_today:
        return f"{today[:4]}-{today[4:6]}-{today[6:8]}"
    latest = await asyncio.to_thread(self.repo.get_latest_trade_date)
    if latest:
        return f"{latest[:4]}-{latest[4:6]}-{latest[6:8]}"
    return None

# API 端点：未传日期时调用，解析后用于查询并回传
resolved_date = await service.resolve_default_trade_date()
result = await service.get_data(...)
result['trade_date'] = resolved_date  # 前端读取后回填日期选择器
```

```typescript
// 前端：回填日期选择器（避免 UTC 偏移，使用 T00:00:00 本地时间构造）
if (!tradeDate && response.data.trade_date) {
  setTradeDate(new Date(response.data.trade_date + 'T00:00:00'))
}
```

**已实现**：`top_list_service.py`、`top_inst_service.py`、`limit_step_service.py`、`moneyflow_service.py`

#### 前端同步：不得将查询筛选日期传入同步接口

同步按钮的 `handleSync` **不得**将当前查询筛选日期（如 `tradeDate`）传给 `syncXxxAsync`。

**原因**：用户日期选择器通常停留在上次查询的日期（如 20260325），传入后会覆盖后端的"取最新交易日"逻辑，导致重复同步旧日期而非增量同步最新交易日。

```typescript
// ❌ 错误：把查询日期传给同步接口
const handleSync = async () => {
  const params: any = {}
  if (tradeDate) params.trade_date = toDateStr(tradeDate)  // ❌
  await moneyflowApi.syncMoneyflowAsync(params)
}

// ✅ 正确：不传日期，让后端从 trading_calendar 自动取最新交易日
const handleSync = async () => {
  const params: any = {}
  // 不传 trade_date，后端会通过 calendar_repo.get_latest_trading_day() 自动确定日期
  if (tsCode) params.ts_code = tsCode  // 可选：按股票筛选
  await moneyflowApi.syncMoneyflowAsync(params)
}
```

**例外**：若用户在页面上显式选择了"同步指定日期"的功能（区别于查询筛选），可以传入。但这需要单独的"指定日期同步"控件，不能复用查询日期选择器。

### 新增数据同步功能开发流程

当需要添加新的 Tushare 数据同步功能时，请按照以下标准流程进行开发：

#### 1. 数据库层
**文件位置**：`db_init/migrations/`

创建数据库迁移脚本：
```sql
-- 示例：030_create_your_table.sql
CREATE TABLE IF NOT EXISTS your_table (
    trade_date VARCHAR(8) NOT NULL,
    -- 其他字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (trade_date)
);

CREATE INDEX idx_your_table_date ON your_table(trade_date);
COMMENT ON TABLE your_table IS 'Tushare接口说明';
```

执行迁移：
```bash
docker-compose exec -T timescaledb psql -U stock_user -d stock_analysis < db_init/migrations/030_create_your_table.sql
```

#### 2. Repository 层
**文件位置**：`backend/app/repositories/your_repository.py`

继承 `BaseRepository` 并实现标准方法：
```python
from app.repositories.base_repository import BaseRepository

class YourRepository(BaseRepository):
    TABLE_NAME = "your_table"

    def __init__(self, db=None):
        super().__init__(db)

    def get_by_date_range(self, start_date, end_date, limit=None):
        # 实现日期范围查询

    def get_statistics(self, start_date=None, end_date=None):
        # 实现统计查询

    def bulk_upsert(self, df):
        # 实现批量插入/更新（ON CONFLICT DO UPDATE）
```

**注册 Repository**：在 `backend/app/repositories/__init__.py` 中导出

#### 3. Service 层
**文件位置**：`backend/app/services/your_service.py`

实现业务逻辑和 Tushare 数据同步：
```python
from app.repositories import YourRepository
from core.src.providers import DataProviderFactory

class YourService:
    def __init__(self):
        self.your_repo = YourRepository()

    def _get_provider(self):
        """获取 Tushare 数据提供者"""
        from app.core.config import settings
        # ⚠️ DataProviderFactory 是纯静态类，使用类方法 create_provider，不要实例化后调用 get_provider
        return DataProviderFactory.create_provider('tushare', token=settings.TUSHARE_TOKEN)

    async def sync_data(self, trade_date=None, start_date=None, end_date=None):
        # 1. 获取 Tushare 数据（使用 provider 封装方法，不要直接调用 provider.pro.xxx）
        provider = self._get_provider()
        df = await asyncio.to_thread(provider.get_your_data, ...)

        # 2. 数据验证和清洗
        df = self._validate_and_clean_data(df)

        # 3. 批量插入数据库
        records = await asyncio.to_thread(self.your_repo.bulk_upsert, df)

        return {"status": "success", "records": records}
```

**⚠️ DataProviderFactory 常见错误**：
```python
# ❌ 错误：DataProviderFactory 没有实例方法 get_provider()
self.provider_factory = DataProviderFactory()
provider = self.provider_factory.get_provider('tushare')  # AttributeError

# ❌ 错误：不传 token，Tushare 会报 "Token 未配置"
DataProviderFactory.create_provider('tushare')

# ✅ 正确：使用类方法，传入 token
from app.core.config import settings
DataProviderFactory.create_provider('tushare', token=settings.TUSHARE_TOKEN)
```

#### 4. Celery 任务
**文件位置**：`backend/app/tasks/your_tasks.py`

创建异步任务：
```python
from app.celery_app import celery_app
from app.tasks.extended_sync_tasks import run_async_in_celery
from app.services.your_service import YourService

@celery_app.task(bind=True, name="tasks.sync_your_data")
def sync_your_data_task(self, trade_date=None, start_date=None, end_date=None):
    service = YourService()
    result = run_async_in_celery(
        service.sync_data,
        trade_date=trade_date,
        start_date=start_date,
        end_date=end_date
    )
    return result
```

**注册任务**：
1. 在 `backend/app/celery_app.py` 中导入任务模块
2. 在 `backend/app/scheduler/task_metadata.py` 中添加任务元数据：
```python
'tasks.sync_your_data': {
    'task': 'tasks.sync_your_data',
    'name': '任务显示名称',
    'category': '任务分类',  # 如：基础数据、扩展数据、两融及转融通
    'display_order': 500,  # 排序号
    'points_consumption': 2000  # Tushare积分消耗
}
```

#### 5. API 端点
**文件位置**：`backend/app/api/endpoints/your_endpoint.py`

实现 REST API 端点（至少包含以下4个）：
```python
from fastapi import APIRouter, Query, Depends
from app.services.your_service import YourService
from app.services import TaskHistoryHelper

router = APIRouter()

@router.get("")
async def get_data(start_date=None, end_date=None, limit=30):
    """查询数据"""
    service = YourService()
    result = await service.get_data(start_date, end_date, limit)
    return ApiResponse.success(data=result)

@router.get("/statistics")
async def get_statistics(start_date=None, end_date=None):
    """获取统计信息"""
    service = YourService()
    result = await service.get_statistics(start_date, end_date)
    return ApiResponse.success(data=result)

@router.get("/latest")
async def get_latest():
    """获取最新数据"""
    service = YourService()
    result = await service.get_latest_data()
    return ApiResponse.success(data=result)

@router.post("/sync-async")
async def sync_async(
    trade_date=None,
    start_date=None,
    end_date=None,
    current_user: User = Depends(require_admin)
):
    """异步同步数据（使用 Celery）"""
    from app.tasks.your_tasks import sync_your_data_task

    # 日期格式转换（YYYY-MM-DD -> YYYYMMDD）
    trade_date_fmt = trade_date.replace('-', '') if trade_date else None

    # 提交 Celery 任务
    celery_task = sync_your_data_task.apply_async(
        kwargs={'trade_date': trade_date_fmt, ...}
    )

    # 使用 TaskHistoryHelper 创建任务历史记录
    helper = TaskHistoryHelper()
    task_data = await helper.create_task_record(
        celery_task_id=celery_task.id,
        task_name='tasks.sync_your_data',
        display_name='任务显示名称',
        task_type='data_sync',
        user_id=current_user.id,
        task_params={...},
        source='your_page'
    )

    return ApiResponse.success(data=task_data, message="任务已提交")
```

**注册路由**：在 `backend/app/api/__init__.py` 中添加：
```python
from .endpoints import your_endpoint
router.include_router(your_endpoint.router, prefix="/your-endpoint", tags=["标签名称"])
```

#### 6. Tushare Provider
**文件位置**：`core/src/providers/tushare/provider.py`

添加数据获取方法：
```python
def get_your_data(self, trade_date=None, start_date=None, end_date=None):
    """获取数据"""
    df = self.api_client.query(
        'your_tushare_api',
        trade_date=trade_date,
        start_date=start_date,
        end_date=end_date
    )
    return df
```

#### 7. 前端 API 客户端
**文件位置**：`admin/lib/api/your-api.ts`

创建模块化 API 客户端：
```typescript
import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface YourDataParams {
  start_date?: string
  end_date?: string
  limit?: number
}

export interface YourData {
  trade_date: string
  // 其他字段
}

export class YourApiClient extends BaseApiClient {
  async getData(params?: YourDataParams): Promise<ApiResponse<{
    items: YourData[]
    total: number
    trade_date?: string  // 后端 resolve_default_trade_date 回填的默认日期，前端用于初始化日期选择器
  }>> {
    return this.get('/api/your-endpoint', { params })
  }

  async getStatistics(params?: {
    start_date?: string
    end_date?: string
    trade_date?: string  // 支持单日筛选
  }): Promise<ApiResponse<any>> {
    return this.get('/api/your-endpoint/statistics', { params })
  }

  async syncAsync(params): Promise<ApiResponse<any>> {
    return this.post('/api/your-endpoint/sync-async', {}, { params })
  }
}

export const yourApi = new YourApiClient()
```

**注册 API**：在 `admin/lib/api/index.ts` 中导出

#### 8. 前端页面
**文件位置**：`admin/app/(dashboard)/data/your-page/page.tsx`

创建数据展示页面（标准结构）：
```typescript
'use client'

import { useState, useEffect, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { toast } from 'sonner'
import { RefreshCw } from 'lucide-react'
import { yourApi } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'

export default function YourPage() {
  const [data, setData] = useState([])
  const [statistics, setStatistics] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [startDate, setStartDate] = useState(undefined)
  const [endDate, setEndDate] = useState(undefined)
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  // 从 task store 实时派生——不要用 useState(false)
  const syncing = isTaskRunning('tasks.your_celery_task_name')

  const loadData = async () => {
    // 加载数据逻辑
  }

  const handleSync = async () => {
    const response = await yourApi.syncAsync(params)

    if (response.code === 200 && response.data) {
      const taskId = response.data.celery_task_id
      addTask({
        taskId,
        taskName: response.data.task_name,
        displayName: response.data.display_name,
        taskType: 'data_sync',
        status: 'running',
        progress: 0,
        startTime: Date.now()
      })

      const completionCallback = (task: any) => {
        if (task.status === 'success') {
          loadData().catch(() => {})
          toast.success('数据同步完成')
        }
        unregisterCompletionCallback(taskId, completionCallback)
        activeCallbacksRef.current.delete(taskId)
      }
      activeCallbacksRef.current.set(taskId, completionCallback)
      registerCompletionCallback(taskId, completionCallback)

      triggerPoll()
    }
  }

  useEffect(() => {
    return () => {
      const callbacks = activeCallbacksRef.current
      callbacks.forEach((callback, taskId) => {
        unregisterCompletionCallback(taskId, callback)
      })
      callbacks.clear()
    }
  }, [])

  // 表格列定义
  const columns: Column<YourData>[] = [...]

  return (
    <div className="space-y-6">
      <PageHeader
        title="页面标题"
        description="页面描述"
        actions={
          // 同步按钮放在 PageHeader actions，不放在查询 Card 里
          <Button onClick={handleSync} disabled={syncing}>
            {syncing ? (
              <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
            ) : (
              <><RefreshCw className="h-4 w-4 mr-1" />同步数据</>
            )}
          </Button>
        }
      />

      {/* 统计卡片 */}
      {statistics && <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* 统计卡片内容 */}
      </div>}

      {/* 筛选和操作区域（只放查询相关控件，不放同步按钮） */}
      <Card>
        <CardHeader><CardTitle>数据查询</CardTitle></CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <DatePicker date={startDate} onDateChange={setStartDate} />
            <DatePicker date={endDate} onDateChange={setEndDate} />
            <Button onClick={loadData}>查询</Button>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <CardContent>
          <DataTable columns={columns} data={data} loading={isLoading} />
        </CardContent>
      </Card>
    </div>
  )
}
```

#### 9. 菜单注册
**文件位置**：`admin/components/layouts/AdminLayout.tsx`

在相应的菜单组中添加菜单项：
```typescript
{
  name: '菜单显示名称',
  href: '/data/your-page',
  icon: YourIcon
}
```

#### 10. 重启 Celery Worker
新增任务后，必须重启 Celery Worker 才能识别：
```bash
docker-compose restart celery_worker
```

验证任务注册：
```bash
docker-compose logs celery_worker | grep "tasks.sync_your_data"
```

#### 开发检查清单

- [ ] 数据库迁移脚本已创建并执行
- [ ] Repository 层实现了标准方法（get_by_date_range, get_statistics, bulk_upsert）
- [ ] Service 层实现了数据同步和查询逻辑
- [ ] Celery 任务已创建并使用 `run_async_in_celery`
- [ ] 任务元数据已添加到 `task_metadata.py`
- [ ] API 端点包含查询、统计、最新、异步同步4个接口
- [ ] API 异步同步端点使用 `TaskHistoryHelper` 创建任务历史
- [ ] Tushare Provider 添加了数据获取方法
- [ ] 前端 API 客户端已创建并导出，`getData` 返回类型包含 `trade_date?`（用于日期回填）
- [ ] 前端页面实现了数据展示、筛选、同步功能
- [ ] 菜单项已添加到 AdminLayout
- [ ] Celery Worker 已重启并验证任务注册成功
- [ ] 所有代码遵循项目三层架构（Repository → Service → API）
- [ ] 日期格式正确处理（数据库 YYYYMMDD ↔ API/前端 YYYY-MM-DD）

### API 客户端模块化架构

Admin 项目采用模块化的 API 客户端架构（2024-03-20 重构完成）：

#### 架构概述
将原有的 2,133 行单一 `api-client.ts` 文件拆分为 15+ 个功能专门的模块文件，提升代码可维护性和开发体验。

#### 模块列表
```
lib/api/
├── base.ts              # 基础 API 类和 axios 实例
├── auth.ts              # 认证相关 API
├── users.ts             # 用户管理 API
├── stocks.ts            # 股票相关 API
├── strategies.ts        # 策略管理 API
├── sentiment.ts         # 市场情绪 API
├── moneyflow.ts         # 资金流向 API
├── margin.ts            # 融资融券 API
├── scheduler.ts         # 定时任务 API
├── celery-tasks.ts      # Celery 任务管理 API
├── config.ts            # 系统配置 API
├── sync.ts              # 数据同步 API
├── extended-data.ts     # 扩展数据 API
├── monitor.ts           # 系统监控 API
├── index.ts             # 统一导出
└── MIGRATION.md         # 迁移指南
```

#### 使用方式

**新代码（推荐）**：
```typescript
// 从专门的模块导入
import { sentimentApi, moneyflowApi, marginApi } from '@/lib/api'

const calendar = await sentimentApi.getTradingCalendar({ year: 2024 })
const moneyflow = await moneyflowApi.getMoneyflowMktDc(params)
```

**旧代码（向后兼容）**：
```typescript
// 继续使用统一的 apiClient 对象
import { apiClient } from '@/lib/api-client'

const calendar = await apiClient.getTradingCalendar({ year: 2024 })
```

#### 关键特性
- ✅ **100% 向后兼容** - 现有代码无需修改
- ✅ **模块化架构** - 每个模块 < 220 行，易于维护
- ✅ **完整类型定义** - 每个模块都有 TypeScript 类型
- ✅ **统一基础类** - 所有 API 继承自 `BaseApiClient`
- ✅ **单例模式** - 每个模块提供单例实例

#### 开发规范
1. **新功能开发**：优先使用新的模块化 API
2. **修改现有代码**：可选择性迁移，不强制要求
3. **导入类型**：从对应模块导入类型定义
   ```typescript
   import type { TradingCalendarParams } from '@/lib/api/sentiment'
   ```

详细信息请查看：`admin/lib/api/MIGRATION.md`

### 响应式设计规范

Admin项目全面支持移动端访问，采用移动优先的响应式设计：

#### 断点定义
- `sm` (640px): 手机横屏及平板竖屏
- `md` (768px): 平板横屏
- `lg` (1024px): 小屏幕桌面
- `xl` (1280px): 标准桌面
- `2xl` (1536px): 大屏幕桌面

#### DataTable 组件分页优化
- **移动端（<640px）**：
  - 垂直3行布局：显示信息、分页控制、快速跳转
  - 页数>7时显示紧凑页码指示器："第 X / Y 页"
  - 上下页按钮仅显示图标，无文字
  - 智能过滤超过总数的分页选项
- **桌面端（≥640px）**：
  - 水平布局，完整分页控制
  - 显示首页、上一页、页码、下一页、末页按钮
  - 页数>10时显示快速跳转输入框

#### 页面响应式设计模式
1. **卡片布局**：使用 `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3` 等自适应网格
2. **文字大小**：移动端使用 `text-xs`，桌面端使用 `text-sm` 或更大
3. **按钮组**：
   - 桌面端：完整按钮组横向排列
   - 移动端：使用下拉菜单（DropdownMenu）整合操作
4. **表单控件**：移动端使用 `w-full` 确保全宽显示
5. **导航模式**：
   - 移动端：卡片式导航或底部标签栏
   - 桌面端：传统标签页或侧边栏
6. **移动端数据展示最佳实践**（参考沪深港通页面）：
   - 自定义移动端视图，不依赖DataTable的mobileCard
   - 使用 `divide-y` 分割线区分数据行
   - 斑马纹背景：偶数行白色/深灰，奇数行浅灰/更深灰
   - 交互反馈：`hover:bg-blue-50` 和 `active:bg-blue-100`（淡蓝色）
   - 每行数据添加适当padding（`p-4`）
   - 数据项垂直堆叠，每项单独一行
   - 独立的移动端分页控件

#### 关键优化技巧
- 使用 `truncate` 和 `line-clamp-*` 处理文本溢出
- 使用 `flex-wrap` 防止元素挤压变形
- 使用 `break-all` 处理长URL或代码的换行
- 移动端优先使用垂直布局（`flex-col`）
- 合理使用 `hidden sm:block` 和 `block sm:hidden` 控制元素显示
- 图表组件响应式：
  - 设置 `minWidth` 防止过度压缩
  - X轴标签旋转45度避免重叠（`angle={-45}`）
  - 调整 margin 为标签预留空间（`bottom: 40`）
  - 使用 `overflow-x-auto` 允许横向滚动
- **ECharts 初始化时序问题**（"Can't get DOM width or height"）：
  ECharts 在 `init()` 时读取容器 `clientHeight`，若容器尚未布局（高度为 0）会导致图表空白。
  解决方案：**两步 useEffect + requestAnimationFrame**
  ```tsx
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstance = useRef<echarts.ECharts | null>(null)
  const [data, setData] = useState<Item[] | null>(null)

  // Step 1：获取数据 → 触发 data state 更新
  useEffect(() => {
    fetchData().then(setData)
  }, [key])

  // Step 2：data 变化后渲染图表（此时 React 已更新 DOM 高度）
  // 再用 requestAnimationFrame 延一帧确保浏览器完成布局
  useEffect(() => {
    if (!data || !chartRef.current) return
    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current)
    }
    requestAnimationFrame(() => {
      chartInstance.current!.setOption({ ... })
      chartInstance.current!.resize()
    })
  }, [data])

  // 窗口 resize + 组件卸载清理（合并为一个 useEffect）
  useEffect(() => {
    const onResize = () => chartInstance.current?.resize()
    window.addEventListener('resize', onResize)
    return () => {
      window.removeEventListener('resize', onResize)
      chartInstance.current?.dispose()
      chartInstance.current = null
    }
  }, [])
  ```
  **关键**：容器始终存在于 DOM，通过 `height: 0 / 420` 切换显隐（而非条件渲染），避免 `clientHeight=0`。
  参见 `frontend/src/app/analysis/page.tsx` 中的 `ChipsDistributionCard` 组件。
- 日期选择器：
  - 优先使用 `@/components/ui/date-picker`（弹出式日历）
  - 避免使用HTML5原生 `<input type="date">`
  - 日期控件对齐：使用 `items-end` 让按钮与输入框底部对齐
- **HTML 嵌套规范**（避免水合错误）：
  - `<p>` 标签内不能包含块级元素（如 `<div>`）
  - 需要在 `<p>` 内使用 flex 布局时，直接在 `<p>` 上添加 `flex` 类
  - 错误示例：`<p><div className="flex">...</div></p>`
  - 正确示例：`<p className="flex">...</p>`
  - 适用于所有渲染为 `<p>` 的组件（如 `CardDescription`）
- **空值安全处理**（避免运行时错误）：
  - 格式化函数必须处理 `null` 和 `undefined`：
    ```typescript
    const formatAmount = (amount: number | null | undefined) => {
      if (amount === null || amount === undefined) return '0.00'
      return amount.toFixed(2)
    }
    ```
  - 条件判断使用空值合并运算符 `??`：
    ```typescript
    <span className={(value ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'}>
    ```
  - 统计数据显示添加默认值：
    ```typescript
    板块数: {statistics.sector_count ?? 0}
    ```
- **中文输入法（IME）处理**：带搜索功能的输入框必须处理 IME 合成状态，否则每个拼音字母都会触发请求：
  ```typescript
  const isComposing = useRef(false)
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const triggerSearch = useCallback((query: string) => {
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
    if (query.length < 1) { /* 清空结果 */ return }
    searchTimerRef.current = setTimeout(() => { /* 发请求 */ }, 300)
  }, [])

  // onChange 正常更新 state（保证输入框显示拼音），但 useEffect 里跳过合成中状态
  useEffect(() => {
    if (!isComposing.current) triggerSearch(searchQuery)
  }, [searchQuery, triggerSearch])

  // compositionend 时直接用最终值触发搜索（state 可能未变化，不能依赖 useEffect）
  <Input
    onChange={(e) => setSearchQuery(e.target.value)}
    onCompositionStart={() => { isComposing.current = true }}
    onCompositionEnd={(e) => {
      isComposing.current = false
      triggerSearch((e.target as HTMLInputElement).value)
    }}
  />
  ```
  **关键点**：`compositionend` 后必须直接调用搜索函数，不能依赖 `useEffect` — 因为选字后 `onChange` 触发时 state 值可能与之前相同，`useEffect` 不会重新执行。

### 定时任务页面架构
定时任务配置页面（`/settings/scheduler`）采用数据库驱动的元数据管理：

#### 数据库表结构
`scheduled_tasks` 表包含以下元数据字段：
- `display_name` (VARCHAR 100) - 任务显示名称（如"每日股票列表"）
- `category` (VARCHAR 50) - 任务分类（如"基础数据"、"扩展数据"）
- `display_order` (INTEGER) - 显示排序号（100-999，数字越小越靠前）
- `points_consumption` (INTEGER, nullable) - Tushare积分消耗（如2000、6000）

#### 任务分类和排序
任务按以下类别排序：
1. **基础数据** (100-199) - 股票列表、新股、ST股票、交易日历、东财板块等
2. **行情数据** (200-299) - 日K、复权因子、每日指标、涨跌停价格、停复牌、港股通等
3. **资金流向** (300-399) - 个股/大盘/板块/沪深港通各类资金流向
4. **两融及转融通** (500-599) - 融资融券汇总、明细、标的、转融资
5. **特色数据** (400-499) - 筹码分布、CCASS持股、集合竞价、神奇九转、机构调研等
6. **打板专题** (550-599) - 龙虎榜、涨跌停列表、连板天梯、东财板块行情等
7. **财务数据** (800-899) - 利润表、资产负债表、现金流量表、业绩预告/快报、财务指标等
8. **参考数据** - 异常波动、股权质押、回购、解禁、大宗交易等
9. **市场情绪** (600-699) - 情绪抓取、AI分析
10. **盘前分析** (700-799) - 盘前数据同步和分析
11. **质量监控** - 数据质量检查和报告
12. **报告通知** (900-999) - 邮件、Telegram通知
13. **系统维护** (1000+) - 系统级维护任务

**注意**："扩展数据"分类已移除（2026-04-02），原有任务已归入对应分类。

#### 积分消耗管理
- 高消耗任务（>=1000积分）使用黄色徽章高亮显示
- 普通任务使用灰色徽章
- 未设置积分的任务不显示徽章
- 用户可在编辑对话框中修改积分值

#### 元数据同步
- **后端**: `task_executor.py` 中的 `TASK_MAPPING` 定义任务元数据
- **数据库**: 迁移脚本初始化元数据，作为单一数据源
- **前端**: 直接从API响应中读取元数据，无需硬编码映射

**关键约束：`scheduled_tasks.module` 必须与 `task_metadata.py` 的 key 完全一致**

调度器通过 `module` 字段在 `task_metadata.py` 中查找对应的 Celery 任务名。`module` 与 key 不一致会导致手动执行时报 "未找到模块" 错误，或定时触发时执行旧的/废弃任务逻辑。

新增任务时，数据库的 `module` 值必须与 `task_metadata.py` 新增的 key 完全相同：
```sql
-- module 必须与 task_metadata.py 中的 key 完全一致
INSERT INTO scheduled_tasks (task_name, module, ...) VALUES ('tasks.sync_your_task', 'tasks.sync_your_task', ...);
```

#### 前端分类列表（TASK_CATEGORIES）
`admin/app/(dashboard)/settings/scheduler/page.tsx` 顶部维护一个 `TASK_CATEGORIES` 常量，筛选下拉和编辑弹窗共用同一份列表，筛选时在前面插入"全部"（`FILTER_CATEGORIES`）。

**新增分类时**，需同步更新该常量，否则新分类不会出现在筛选和编辑弹窗的选项中。

注意：
- DataTable 组件使用 `accessor` 函数而非 `render` 来自定义列渲染
- 新增任务时，优先在数据库中设置元数据，确保排序和分类正确

### DataTable 列样式规范

**`cellClassName` vs `className`**：
- `cellClassName`：作用于 `<td>` 单元格（行数据），用于控制单元格文字对齐、换行等
- `headerClassName`：作用于 `<th>` 表头，用于控制表头样式
- `className` 字段在 DataTable 中无效，不要使用

```typescript
// ✅ 正确
{
  key: 'amount',
  header: '总成交额',
  width: 110,
  cellClassName: 'text-right whitespace-nowrap'  // 作用于 <td>
}

// ❌ 错误：className 不生效
{
  key: 'amount',
  className: 'text-right'  // 无效，DataTable 不读取此字段
}
```

**固定宽度表格（防止列换行）**：

在 `table-fixed` 模式下，设置 `width` 的列固定不变，无 `width` 的列自动占剩余空间：

```tsx
<DataTable
  tableClassName="table-fixed w-full"
  columns={[
    { key: 'name', width: 160, cellClassName: 'whitespace-nowrap' },  // 固定 160px
    { key: 'reason', /* 无 width */ }  // 自动占剩余宽度，内容会截断
  ]}
/>
```

**后端排序 SQL 注入防护**：

排序字段必须使用白名单校验，禁止直接拼接用户传入的字段名：

```python
# Repository 层
SORTABLE_COLUMNS = {'pct_change', 'turnover_rate', 'amount', 'net_amount'}

if sort_by and sort_by in self.SORTABLE_COLUMNS:
    order_clause = f"ORDER BY {sort_by} {order} NULLS LAST"
else:
    order_clause = "ORDER BY trade_date DESC"  # 默认排序
```

前端 sort 状态的异步更新陷阱——`setState` 后立即调用 `loadData()` 时会读到旧值，必须通过参数传入新值绕过：

```typescript
onSort: (key, direction) => {
  const newKey = direction ? key : null
  setSortKey(newKey)          // 异步更新，此时 sortKey 仍是旧值
  setSortDirection(direction)
  loadData(1, newKey, direction)  // 直接传新值，不依赖 state
}
```

**日期字符串构建（时区安全）**：

`date.toISOString()` 会转为 UTC，在 UTC+8 时区会导致日期偏移 -1 天。应使用本地时间方法：

```typescript
// ✅ 正确：使用本地时间
const dateStr = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`

// ❌ 错误：UTC 转换导致日期偏移
const dateStr = date.toISOString().split('T')[0]
```

### 前端页面模块化重构最佳实践

当单个页面文件超过 **500 行**时，应考虑模块化重构，提升代码可维护性和复用性。

#### 重构策略

采用 **Hooks + Components** 架构：

```
page/
├── page.tsx              # 主页面（编排和组合）
├── hooks/                # 自定义 Hooks
│   ├── index.ts         # 统一导出
│   ├── useXxxData.ts    # 数据加载和管理
│   ├── useXxxConfig.ts  # 配置管理
│   └── useXxxActions.ts # 操作逻辑
└── components/           # 子组件
    ├── index.ts         # 统一导出
    ├── ControlPanel.tsx # 控制面板
    ├── XxxTab.tsx       # 标签页组件
    └── XxxCard.tsx      # 卡片组件
```

#### 拆分原则

1. **单一职责原则 (SRP)**
   - 每个 Hook 只负责一个功能域（数据/配置/操作）
   - 每个 Component 只负责一个 UI 模块
   - 主页面只负责组合和编排

2. **依赖注入**
   - 通过 props 传递依赖，便于测试
   - 避免组件内部直接访问全局状态

3. **组件组合**
   - 通过组合而非继承实现功能复用
   - 使用 `children` 和 `render props` 模式

#### 实施步骤

**第一步：提取自定义 Hooks**

将状态管理和副作用逻辑提取为 Hooks：

```typescript
// hooks/useXxxData.ts
export function useXxxData() {
  const [data, setData] = useState(null)
  const [isLoading, setIsLoading] = useState(false)

  const loadData = useCallback(async () => {
    setIsLoading(true)
    try {
      const result = await apiClient.get('/api/xxx')
      setData(result.data)
    } finally {
      setIsLoading(false)
    }
  }, [])

  return { data, isLoading, loadData }
}
```

**第二步：拆分子组件**

按功能模块拆分为独立组件：

```typescript
// components/ControlPanel.tsx
interface ControlPanelProps {
  date: Date
  onDateChange: (date: Date) => void
  onSync: () => void
  isSyncing: boolean
}

export function ControlPanel({ date, onDateChange, onSync, isSyncing }: ControlPanelProps) {
  return (
    <Card>
      {/* 控制面板 UI */}
    </Card>
  )
}
```

**第三步：重构主页面**

主页面简化为组合和编排：

```typescript
// page.tsx
import { useXxxData, useXxxActions } from './hooks'
import { ControlPanel, XxxTab } from './components'

export default function XxxPage() {
  const { data, isLoading, loadData } = useXxxData()
  const { handleSync, isSyncing } = useXxxActions()

  return (
    <div>
      <ControlPanel
        date={date}
        onDateChange={setDate}
        onSync={handleSync}
        isSyncing={isSyncing}
      />
      <XxxTab data={data} isLoading={isLoading} />
    </div>
  )
}
```

#### 重构收益

| 指标 | 重构前 | 重构后 | 改善 |
|------|--------|--------|------|
| 主页面行数 | 1000+行 | 200-300行 | ↓ 70-80% |
| 最大函数行数 | 500+行 | 50-100行 | ↓ 80-90% |
| 文件数量 | 1个庞大文件 | 10-15个专门文件 | ✅ 模块化 |
| 代码复用 | 低 | 高 | ✅ Hooks和组件可复用 |
| 可测试性 | 低 | 高 | ✅ 独立测试 |

#### 参考示例

**盘前预期管理系统** (`/sentiment/premarket`)：
- 原始文件：1,010 行
- 重构后主页面：259 行（↓ 74%）
- 3个自定义 Hooks（253 行）
- 7个子组件（794 行）

**用户管理页面** (`/users`)：
- 原始文件：959 行
- 重构后主页面：278 行（↓ 71%）
- 4个自定义 Hooks（336 行）：
  - `useUserFilters` - 筛选和分页管理
  - `useUserDialogs` - 对话框状态管理
  - `useUserForm` - 表单数据和验证
  - `useUserActions` - 用户操作逻辑
- 8个子组件（853 行）：
  - `UserFilters` - 搜索和筛选控件
  - `UserTableColumns` - 表格列定义
  - `UserMobileCard` - 移动端卡片视图
  - `UserActions` - 操作下拉菜单
  - `CreateUserDialog` - 创建用户对话框
  - `EditUserDialog` - 编辑用户对话框
  - `DeleteUserDialog` - 删除确认对话框
  - `UserDetailDialog` - 用户详情对话框

## 常用命令

### 查看容器状态
```bash
docker-compose ps
```

### 查看日志
```bash
docker-compose logs -f [service_name]
```

### 重启服务
```bash
docker-compose restart [service_name]
```

### 停止所有服务
```bash
docker-compose down
```

## 数据质量保证

### 数据验证器
项目实现了完整的数据验证体系：
- **位置**: `/core/src/data/validators/`
- **功能**: 自动验证和修复Tushare扩展数据
- **支持的数据类型**: daily_basic, moneyflow, moneyflow_hsgt, margin_detail, stk_limit, adj_factor

### 股票基础数据同步

#### 股票列表同步（包含退市股票）
股票列表同步会自动获取所有状态的股票，包括：
- **上市股票** (`list_status='L'`) - 正常交易的股票
- **退市股票** (`list_status='D'`) - 已退市的股票
- **暂停上市** (`list_status='P'`) - 暂停上市的股票

#### 股票日线数据同步

**功能位置**：
- **前端页面**：`/admin/app/(dashboard)/market/daily/page.tsx`
- **前端 API**：`/admin/lib/api/stock-daily.ts`
- **后端 API**：`/backend/app/api/endpoints/stock_daily.py`
- **后端 Service**：`/backend/app/services/stock_daily_service.py`（唯一同步入口）
- **Celery 任务**：`/backend/app/tasks/sync_tasks.py`

**⚠️ `stock_daily` 表只存完整 ts_code**：`stock_daily` 表的 `code` 列统一使用完整格式（如 `000001.SZ`），**不存**纯数字代码（如 `000001`）。所有查询和同步操作必须使用完整 ts_code。

**⚠️ TimescaleDB 性能注意**：`stock_daily` 是 TimescaleDB hypertable（6M+ 行，557+ chunks），以下查询会触发全表扫描（10+ 秒），禁止使用：
- `COUNT(DISTINCT code)` — 跨所有 chunk 扫描
- `DISTINCT ON (code) ORDER BY date DESC` — 需要排序扫描所有 chunk

**正确做法（< 10ms）**：
1. 从 `trading_calendar` 用索引 `MAX(trade_date)` 定位最近交易日（< 1ms）
2. 用精确日期 `WHERE date = %s` 查 `stock_daily`（命中 `idx_stock_daily_date` 索引，< 5ms）
3. 分页总数用 `SELECT COUNT(*) FROM stock_basic WHERE list_status = 'L'`（约5500行，< 1ms）

**同步模式**：
1. **单只股票模式**（`sync_daily_single_task`）：
   - 指定股票代码（如 `000001.SZ`）
   - 支持自定义日期范围或年数（默认 5 年）
   - 使用 Tushare `daily` 接口按日期范围查询
   - 积分消耗：120 积分/次

2. **全市场单日模式**（`sync_daily_single_task`，不传 code）：
   - 不指定股票代码（留空）
   - 自动推算目标交易日：先从本地 `stock_daily` 找已有数据最新日期（至少100条），再从 `trade_cal` 找下一个交易日，避免重复同步
   - 无本地数据时回退到 `trade_cal` 最新交易日
   - 积分消耗：120 积分/次（单个交易日）

3. **全市场近N日增量模式**（`sync_daily_recent_all_task`）：
   - 对所有上市股票同步最近 N 个交易日（默认7日）
   - 适合每日定时增量更新
   - 使用 `TradingCalendarRepository` 确定日期范围

4. **全量历史模式**（`sync_daily_full_history_task`，可中断续继）：
   - 对所有上市股票同步自 2021-01-01 起的完整历史
   - 进度通过 Redis Set 记录（key: `sync:daily:full_history:progress`）
   - 中断后再次触发自动跳过已完成股票
   - 8 并发，批量 50 只，约 11 分钟完成 ~5500 只

**数据接口**：
- 使用 Tushare `pro.daily()` 接口，返回**未复权**数据
- ⚠️ **`daily` 接口不支持 `adj` 复权参数**（复权需用 `pro_bar` 接口）；传入 `adj` 会被静默忽略
- 数据字段：ts_code、开、高、低、收、成交量、成交额、涨跌幅、换手率等

**注意事项**：
- 已从数据初始化页面（`/sync/initialize`）迁移至行情数据菜单（`/market/daily`）
- 支持异步同步（Celery 任务），实时显示进度
- 支持分页查询（30 条/页）
- 包含统计卡片：股票数量、记录总数、最新交易日（3张，无平均涨跌幅）
- 统计接口在页面初始化时调用一次，不随每次分页/查询重复调用

**数据库表结构** (`stock_basic` 表已扩展，2026-03-25更新)：
- **基础字段**（原有7个）：code, name, ts_code, market, exchange, area, industry
- **Tushare新增字段**（2026-03-25新增10个）：
  - `fullname` VARCHAR(100) - 股票全称
  - `enname` VARCHAR(200) - 英文全称
  - `cnspell` VARCHAR(100) - 拼音缩写
  - `curr_type` VARCHAR(10) - 货币代码（CNY/HKD/USD）
  - `list_date` DATE - 上市日期
  - `delist_date` DATE - 退市日期
  - `is_hs` VARCHAR(2) - 沪深港通标志（S/H/N）
  - `act_name` VARCHAR(200) - 实际控制人名称
  - `act_ent_type` VARCHAR(100) - 实际控制人企业性质
  - `status` VARCHAR(10) - 存续状态（L-存续/D-终止）
- **总计17个字段**，完整对齐Tushare stock_basic接口输出

**关键实现**：
- **Tushare 接口**: `stock_basic(exchange='', list_status='', fields='...')` 获取全量17个字段
- **数据转换**: `TushareDataConverter.convert_stock_list()` 处理字段映射和类型转换
- **数据插入**: `DataInsertManager.save_stock_list()` 使用 UPSERT 语义（ON CONFLICT UPDATE）
- **日期处理**: 修复 numpy.datetime64 转换问题，确保 PostgreSQL DATE 类型兼容
- **自动更新**: 每日股票列表同步会自动更新 `stock_basic` 表中的股票状态
- **无需单独任务**: 退市股票数据由基础同步自动处理，无需额外的退市同步任务

**为什么不需要单独的退市同步任务**：
1. 退市事件相对较少，不需要高频更新
2. 基础股票列表同步已包含所有状态的股票
3. 避免代码重复和维护成本
4. `stock_basic` 表统一管理所有股票的状态变更

#### frontend 股票列表查询规范

**所有 frontend 项目的股票列表请求必须传 `list_status: 'L'`，过滤退市股票。**

`stock_basic` 表同步时保留了所有状态的股票（L/D/P），backend API 默认不过滤，需由调用方显式指定。

涉及文件：
- `frontend/src/components/stock-search.tsx` — 搜索框
- `frontend/src/hooks/useStockFilter.ts` — 股票筛选 hook
- `frontend/src/app/stocks/page.tsx` — 股票列表页
- `frontend/src/lib/api-client.ts` 中的 `getStock()` — 单股精确查询

**注意**：admin 项目的 `/data/stock-list` 页面有独立的上市状态筛选器，允许用户主动查看退市股票，不受此规范约束。

### 资金流向数据

#### 沪深港通资金流向
- **API端点**: `/api/moneyflow-hsgt`
- **前端页面**: `/admin/app/(dashboard)/moneyflow/hsgt/page.tsx`
- **数据内容**: 沪股通、深股通、港股通(上海)、港股通(深圳)的每日资金流向
- **特点**: 支持2026年及以后的最新数据，替代了仅支持到2025年的北向资金持股明细(hk_hold)
- **积分消耗**: 2000积分/次（Tushare Pro接口）
- **页面功能**（2026-03-27 全面优化）:
  - 统计卡片：左文字右图标布局，北向资金均值、累计净流入、北向最大流入、南向最大流出（均带补充说明文字）
  - 趋势图表：北向/南向资金流向折线图（LineChart，dot=false）
  - 筛选器：日期范围查询，同步弹窗与查询日期解耦
  - 数据单位：统一使用亿元（原始数据为百万元）
  - 同步弹窗：点击同步弹出 Dialog 选择日期范围（留空同步最新交易日）
  - `syncing` 从 `isTaskRunning('tasks.sync_moneyflow_hsgt')` 派生，不用本地 boolean
  - 模块化 API：使用 `moneyflowApi.getMoneyflowHsgt` / `syncMoneyflowHsgtAsync`
  - 响应式布局：统一使用 DataTable `mobileCard` prop，移动端卡片含北向/南向双区块

#### 大盘资金流向（DC）
- **API端点**: `/api/moneyflow-mkt-dc`
- **前端页面**: `/admin/app/(dashboard)/moneyflow/mkt-dc/page.tsx`
- **数据内容**: 东方财富大盘资金流向，包含上证/深证指数及主力资金（超大单、大单、中单、小单）流入流出情况
- **积分消耗**: 120积分/次（试用），6000积分/次（正式）
- **页面功能**（2026-03-27 全面优化）:
  - 统计卡片：左文字右图标布局，显示主力均值、最大净流入、超大单均值、累计净流入（带补充说明文字）
  - 趋势图表：主力资金净流入折线图（正序时序，dot=false）
  - 筛选器：日期范围查询，默认加载全部最新数据
  - 数据单位：统一使用亿元（后端 Service 层已转换）
  - 同步弹窗：点击同步弹出 Dialog 选择日期范围（不预填查询日期），让后端自动取最新交易日
  - `syncing` 从 `isTaskRunning('tasks.sync_moneyflow_mkt_dc')` 派生，不用本地 boolean
  - 响应式布局：统一使用 DataTable `mobileCard` prop，移动端卡片含上证/深证涨跌幅行

#### 板块资金流向（DC）
- **API端点**: `/api/moneyflow-ind-dc`
- **前端页面**: `/admin/app/(dashboard)/moneyflow/ind-dc/page.tsx`
- **数据内容**: 东方财富板块资金流向，包含行业、概念、地域板块的主力资金流入流出情况
- **积分消耗**: 6000积分/次（Tushare Pro接口），"全部"同步消耗约 18000 积分（行业+概念+地域三个任务）
- **页面功能**（2026-03-27 全面优化）:
  - 统计卡片：左文字右图标布局，显示板块数、主力资金均值、最大净流入、超大单均值
  - 趋势图表：TOP 20 板块资金流向（调用 `/latest` 接口，不依赖查询筛选）
  - 筛选器：单日交易日期 + 板块类型，默认自动加载最近有数据的交易日并回填
  - 后端排序：net_amount/pct_change/buy_elg_amount/buy_lg_amount/buy_md_amount/buy_sm_amount/rank 白名单防注入
  - 分页查询（100条/页），page/page_size 参数，向后兼容旧 limit/offset
  - 同步弹窗：点击"同步数据"弹出 Dialog，用户可选日期（留空同步最新交易日）和板块类型；选"全部"依次提交三个任务
  - `syncing` 从 `isTaskRunning('tasks.sync_moneyflow_ind_dc')` 派生，不用本地 boolean
  - 数据单位：统一使用亿元（原始数据为元）
  - 响应式布局：
    - 桌面端：完整表格视图，显示所有资金流向指标和排名
    - 移动端：卡片视图，hover/active 反馈

#### 个股资金流向（Tushare）
- **API端点**: `/api/moneyflow`
- **前端页面**: `/admin/app/(dashboard)/moneyflow/stock/page.tsx`
- **数据内容**: Tushare标准个股资金流向，基于主动买卖单统计，包含小单/中单/大单/特大单的买卖量和买卖额
- **数据源**: Tushare `pro.moneyflow()` 接口
- **积分消耗**: 2000积分/次（高消耗）
- **单次限制**: 最大6000行
- **数据起始**: 2010年
- **页面功能**:
  - 统计卡片：净流入均值、累计净流入、最大净流入、统计股票数
  - 趋势图表：TOP 20个股资金流向可视化（净流入、特大单、大单）
  - 筛选器：支持股票代码和日期范围筛选
  - 数据单位：万元
  - 异步同步：支持后台任务执行，实时显示进度
  - 响应式布局：桌面端表格视图，移动端卡片视图
- **数据库表**: `moneyflow` (trade_date 使用 VARCHAR(8) 存储 YYYYMMDD 格式)
- **同步特点**: 不依赖 stock_daily 表，直接通过日期参数获取所有股票数据
- **与 DC 版本区别**:
  - Tushare 标准版：买卖量/额分别记录，数据更详细
  - DC 版本：净流入为核心指标，数据来源东方财富

#### 个股资金流向（DC）
- **API端点**: `/api/moneyflow-stock-dc`
- **前端页面**: `/admin/app/(dashboard)/moneyflow/stock-dc/page.tsx`
- **数据内容**: 东方财富个股资金流向，包含个股主力资金（超大单、大单、中单、小单）流入流出情况
- **积分消耗**: 5000积分/次（Tushare Pro接口）
- **页面功能**（2026-03-27 全面优化）:
  - 统计卡片：左文字右图标布局，显示统计股票数、主力均值、最大净流入、超大单均值
  - 趋势图表：TOP 20个股资金流向可视化（主力净流入、超大单、大单）
  - 筛选器：单日交易日期 + 股票代码，默认自动加载最近有数据的交易日并回填日期选择器
  - 后端排序：net_amount/pct_change/buy_elg_amount/buy_lg_amount/buy_md_amount/buy_sm_amount 白名单防注入
  - 分页查询（100条/页），asyncio 分页偏移
  - 同步弹窗：点击"同步数据"弹出 Dialog，用户可选择日期（可留空同步最新交易日）
  - 股票列合并名称+纯代码可点击跳转分析页面
  - 数据单位：统一使用亿元（原始数据为万元）
  - `syncing` 从 `isTaskRunning('tasks.sync_moneyflow_stock_dc')` 派生，不用本地 boolean
  - 响应式布局：桌面端表格视图，移动端卡片视图（hover/active 反馈）

### 数据库连接池规划

系统有三套独立的连接池，**总上限必须低于 PostgreSQL `max_connections`**：

| 连接池 | 配置文件 | 默认上限 |
|--------|----------|---------|
| SQLAlchemy 同步引擎 | `backend/app/core/database.py` | pool_size=5, max_overflow=10 → **15** |
| SQLAlchemy 异步引擎 | `backend/app/core/database.py` | pool_size=5, max_overflow=10 → **15** |
| psycopg2（Core 模块）| `core/src/database/connection_pool_manager.py` | min=2, max=20 → **20** |
| **三套合计** | | **≈50** |
| PostgreSQL max_connections | `ALTER SYSTEM SET max_connections=200` | **200** |

**⚠️ 注意**：不要随意调大连接池（尤其是 psycopg2 的 max_conn），三套合计若超过 `max_connections` 会触发 `FATAL: sorry, too many clients already`，health check 进入死循环。

`max_connections=200` 已通过 `ALTER SYSTEM` 持久化到 PostgreSQL，重启后自动生效（无需修改 docker-compose.yml）。

如需调整连接池大小，修改 `backend/app/core/database.py` 中的 `_POOL_SIZE` / `_MAX_OVERFLOW` 常量即可同时更新三处引擎。

### 性能优化
1. **批量插入**: 使用PostgreSQL COPY协议，性能提升10倍
2. **数据压缩**: TimescaleDB自动压缩，节省60%存储
3. **查询缓存**: Redis缓存热点数据，命中率80%
4. **索引优化**: 针对高频查询创建专门索引

### 服务位置
- **性能优化器**: `/backend/app/services/performance_optimizer.py`
- **缓存服务**: `/backend/app/services/cache_service.py`
- **数据质量服务**: `/backend/app/services/data_quality_service.py`
- **回测编排服务**: `/backend/app/services/backtest_orchestration_service.py`

## Backend 架构规范

### 分层架构

Backend 项目采用清晰的三层架构，确保代码的可维护性和可测试性：

```
┌─────────────────────────────────────────┐
│  API Layer (endpoints/)                 │
│  - 路由定义                              │
│  - 参数验证 (Pydantic)                   │
│  - 错误处理                              │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  Schema Layer (schemas/)                │
│  - Pydantic 模型定义                     │
│  - 数据验证规则                          │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  Service Layer (services/)              │
│  - 业务逻辑编排                          │
│  - 数据处理和转换                        │
│  - 第三方服务调用                        │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  Repository Layer (repositories/)       │
│  - 数据库访问                            │
│  - ORM 操作封装                          │
└─────────────────────────────────────────┘
```

### 核心原则

1. **单一职责**：每个层只负责自己的职责
   - API 层：只处理 HTTP 请求/响应
   - Schema 层：只定义数据模型和验证规则
   - Service 层：只处理业务逻辑
   - Repository 层：只处理数据持久化

2. **依赖注入**：服务层通过构造函数注入依赖
   ```python
   class BacktestOrchestrationService:
       def __init__(self):
           self.data_adapter = DataAdapter()
           self.strategy_repo = StrategyRepository()
   ```

3. **可测试性**：服务层可独立测试，无需启动 FastAPI
   ```python
   # 单元测试示例
   service = BacktestOrchestrationService()
   result = service.execute_backtest(params)
   assert result['metrics']['sharpe_ratio'] > 1.0
   ```

### 回测模块架构示例

以回测功能为例，展示如何应用分层架构：

**Schema 层** (`/backend/app/schemas/backtest_schemas.py`):
```python
class BacktestExecutionParams(BaseModel):
    """回测执行参数"""
    strategy_id: int
    stock_pool: List[str]
    start_date: str
    end_date: str
    initial_capital: float = 1000000.0
    # ... 其他参数
```

**Service 层** (`/backend/app/services/backtest_orchestration_service.py`):
```python
class BacktestOrchestrationService:
    """回测编排服务 - 协调整个回测流程"""

    def execute_backtest(self, params: BacktestExecutionParams) -> Dict:
        # 1. 加载策略
        strategy = self._load_strategy(params)
        # 2. 加载数据
        market_data = self._load_market_data(...)
        # 3. 执行回测
        result = self._run_backtest_engine(...)
        # 4. 返回结果
        return formatted_result
```

**API 层** (`/backend/app/api/endpoints/backtest.py`):
```python
@router.post("")
async def run_backtest(params: BacktestExecutionParams):
    # 1. 创建服务实例
    service = BacktestOrchestrationService()
    # 2. 调用服务层
    result = service.execute_backtest(params)
    # 3. 返回响应
    return ApiResponse.success(data=result)
```

### Repository 层架构

Repository 层负责所有数据库访问操作，为 Service 层提供简洁的数据访问接口。

#### 已实现的 Repository

1. **资金流向 - Tushare标准**
   - `MoneyflowRepository` - 个股资金流向（小单/中单/大单/特大单）

2. **资金流向 - 沪深港通**
   - `MoneyflowHsgtRepository` - 沪股通/深股通/港股通/北向南向资金

3. **资金流向 - 东方财富DC**
   - `MoneyflowMktDcRepository` - 大盘资金流向（上证/深证指数）
   - `MoneyflowIndDcRepository` - 板块资金流向（行业/概念/地域）
   - `MoneyflowStockDcRepository` - 个股资金流向（主力资金净流入）

4. **融资融券**
   - `MarginRepository` - 融资融券交易汇总（按交易所统计）
   - `MarginDetailRepository` - 融资融券交易明细（个股级别）
   - `MarginSecsRepository` - 融资融券标的（盘前更新，包括ETF）

5. **扩展数据**
   - `DailyBasicRepository` - 每日指标数据（换手率、市盈率、市净率等）
   - `HkHoldRepository` - 北向资金持股数据
   - `StkLimitRepository` - 涨跌停价格数据
   - `SuspendRepository` - 每日停复牌信息（停牌时间段、停复牌类型，支持分页查询）**（✨ 新增于 2026-03-24）**
   - `StkLimitDRepository` - 每日涨跌停价格（昨收价、涨停价、跌停价，每交易日8:40更新）**（✨ 新增于 2026-03-24）**
   - `AdjFactorRepository` - 复权因子（股票复权因子数据，盘前9:15~20分更新，支持单只股票历史查询）**（✨ 新增于 2026-03-24）**

6. **策略和回测**
   - `StrategyRepository` - 统一策略管理
   - `StrategyConfigRepository` - 策略配置（旧架构）
   - `DynamicStrategyRepository` - 动态策略（旧架构）
   - `StrategyExecutionRepository` - 策略执行历史
   - `ExperimentRepository` - 实验管理（✨ 2026-03-20 增强：新增批量创建、池化训练实验创建、排名更新等 5 个方法）
   - `BatchRepository` - 批次管理（✨ 2026-03-20 增强：新增创建批次、增加计数器等 2 个方法）
   - `StockDailyRepository` - 股票日线数据（支持回测数据加载）

7. **配置和同步**
   - `ConfigRepository` - 系统配置管理
   - `SyncLogRepository` - 同步日志管理（sync_log 表）

8. **任务管理和交易日历** （✨ 新增于 2026-03-20）
   - `CeleryTaskHistoryRepository` - Celery 任务历史记录管理
   - `ScheduledTaskRepository` - 定时任务配置管理
   - `TaskExecutionHistoryRepository` - 定时任务执行历史管理（task_execution_history 表）
   - `TradingCalendarRepository` - 交易日历数据管理

9. **市场情绪** （✨ 新增于 2026-03-20，精简于 2026-03-25）
   - `SentimentAiAnalysisRepository` - AI情绪分析结果

   **已移除的 Repository**（2026-03-25）：
   - ~~`MarketSentimentRepository`~~ - 大盘情绪数据
   - ~~`LimitUpPoolRepository`~~ - 涨停板情绪池
   - ~~`DragonTigerListRepository`~~ - 龙虎榜数据
   - ~~`SentimentCycleRepository`~~ - 情绪周期数据

10. **股票数据**
   - `StockDailyRepository` - 股票日线数据（支持回测数据加载）
   - `StockBasicRepository` - 股票基础信息（代码、名称、市场、行业等）

11. **用户管理**
   - `UserQuotaRepository` - 用户配额管理（配额重置、配额查询、使用量统计）

12. **打板专题** （✨ 新增于 2026-03-21）
   - `TopListRepository` - 龙虎榜每日明细（涨跌幅偏离值达7%、连续涨跌等上榜股票及席位信息）
   - `TopInstRepository` - 龙虎榜机构明细（营业部名称、买卖类型、买入额、卖出额、净成交额等）
   - `LimitListRepository` - 涨跌停列表（每日涨停、跌停股票统计，包含涨停原因、连板数等）
   - `LimitStepRepository` - 连板天梯（每日连板个数晋级的股票，用于分析强势热度）
   - `LimitCptRepository` - 最强板块统计（每天涨停股票最多的概念板块，分析板块轮动和资金动向）

13. **特色数据** （✨ 新增于 2026-03-21，更新于 2026-03-23）
   - `ReportRcRepository` - 卖方盈利预测数据（券商研报盈利预测、评级、目标价等）
   - `CcassHoldRepository` - 中央结算系统持股汇总（港股通持股数据，包括持股数量、持股比例等，5000积分/次）
   - `CcassHoldDetailRepository` - 中央结算系统持股明细（CCASS参与者持股明细，机构席位持股数据，8000积分/次）
   - `HkHoldRepository` - 沪深港股通持股明细（北向资金持股数据，沪股通/深股通/港股通持股情况，2000积分/次）**（✨ 新增于 2026-03-23，注意：2024年8月20日起改为季度披露）**
   - `StkAuctionORepository` - 股票开盘集合竞价（开盘9:30集合竞价数据，需要股票分钟权限，支持分页查询）**（✨ 新增于 2026-03-23）**
   - `StkAuctionCRepository` - 股票收盘集合竞价（收盘15:00集合竞价数据，需要股票分钟权限，支持分页查询）**（✨ 新增于 2026-03-23）**
   - `StkNineturnRepository` - 神奇九转指标（基于技术分析的趋势反转指标，识别连续9天特定走势，6000积分/次，2023年起，涉及分钟数据）**（✨ 新增于 2026-03-23）**
   - `StkAhComparisonRepository` - AH股比价（AH股价格比价数据，包括溢价率、比价等，5000积分/次，2025-08-12起）**（✨ 新增于 2026-03-23）**
   - `StkSurvRepository` - 机构调研表（上市公司机构调研记录，包括调研日期、参与机构、接待方式、接待地点等，5000积分/次，单次最大100行）**（✨ 新增于 2026-03-23）**
   - `BrokerRecommendRepository` - 券商每月荐股（券商月度金股推荐数据，每月1-3日更新，6000积分/次，单次最大1000行）**（✨ 新增于 2026-03-23）**

14. **参考数据** （✨ 新增于 2026-03-21，更新于 2026-03-22）
   - `StkShockRepository` - 个股异常波动（根据证券交易所交易规则，记录每日股票交易异常波动情况）
   - `StkHighShockRepository` - 个股严重异常波动（交易所每日发布的股票交易严重异常波动情况）
   - `StkAlertRepository` - 交易所重点提示证券（记录交易所每日发布的重点提示证券信息）
   - `PledgeStatRepository` - 股权质押统计（股票质押次数、质押数量、质押比例等统计数据）
   - `RepurchaseRepository` - 股票回购（上市公司回购股票数据，包括回购公告、进度、数量、金额、价格区间等）
   - `ShareFloatRepository` - 限售股解禁（股票限售股解禁数据，包括公告日期、解禁日期、解禁数量、解禁比例、股东名称等）
   - `StkHolderNumberRepository` - 股东人数（上市公司股东户数数据，包括股票代码、公告日期、截止日期、股东户数等，600积分/次）
   - `BlockTradeRepository` - 大宗交易（股票大宗交易数据，包括成交价、成交量、成交金额、买卖方营业部等，300积分/次）
   - `StkHoldertradeRepository` - 股东增减持（上市公司股东增减持数据，包括股东名称、增减持类型、变动数量、变动比例、均价等，2000积分/次）

15. **财务数据** （✨ 新增于 2026-03-22）
   - `BalancesheetRepository` - 资产负债表（上市公司资产负债表数据，包括总资产、负债、所有者权益等科目，2000积分/次）
   - `IncomeRepository` - 利润表（上市公司利润表数据，包括营业收入、营业成本、净利润等科目，2000积分/次）
   - `CashflowRepository` - 现金流量表（上市公司现金流量表数据，包括经营、投资、筹资活动现金流，2000积分/次）
   - `ForecastRepository` - 业绩预告（上市公司业绩预告数据，包括预告类型、净利润变动幅度、预告值、变动原因等，2000积分/次）
   - `ExpressRepository` - 业绩快报（上市公司业绩快报数据，包括营业收入、利润、资产、每股收益、净资产收益率、同比增长率等，2000积分/次）
   - `DividendRepository` - 分红送股（上市公司分红送股数据，包括股利分配方案、实施进度、除权除息日等，2000积分/次）
   - `FinaIndicatorRepository` - 财务指标（上市公司财务指标数据，包括150+财务指标：EPS、ROE、毛利率、资产负债率等，2000积分/次，每次最多100条）
   - `FinaAuditRepository` - 财务审计意见（上市公司定期财务审计意见数据，包括审计结果、审计费用、会计事务所、签字会计师等，500积分/次）
   - `FinaMainbzRepository` - 主营业务构成（上市公司主营业务构成数据，按产品/地区/行业分类，包括主营收入、利润、成本等，2000积分/次）
   - `DisclosureDateRepository` - 财报披露计划（上市公司财报披露计划日期，包括预计披露日期、实际披露日期等，500积分/次）

#### Repository 开发规范

**强制规则**：

1. **禁止在 API 层写 SQL**
   ```python
   # ❌ 错误示例
   @router.get("/data")
   def get_data(db: Session = Depends(get_db)):
       result = db.execute(text("SELECT..."))  # ❌ 在 API 层操作数据库
   ```

2. **禁止 Service 层直接使用 DatabaseManager**
   ```python
   # ❌ 错误示例
   class MyService:
       def __init__(self):
           self.db = DatabaseManager()  # ❌ 应使用 Repository
   ```

3. **强制使用三层架构**
   ```
   API Layer (endpoints/)         ← 只处理 HTTP 请求/响应
     ↓ 调用
   Service Layer (services/)      ← 只处理业务逻辑
     ↓ 调用
   Repository Layer (repositories/) ← 只处理数据访问
     ↓ 访问
   Database
   ```

**创建新 Repository 的标准**：

1. **继承 BaseRepository**
   ```python
   from app.repositories.base_repository import BaseRepository

   class YourRepository(BaseRepository):
       TABLE_NAME = "your_table_name"

       def __init__(self, db=None):
           super().__init__(db)
           logger.debug("✓ YourRepository initialized")
   ```

2. **实现标准方法**
   ```python
   class XxxRepository(BaseRepository):
       # 查询操作
       def get_by_date_range(start_date, end_date, **filters) -> List[Dict]
       def get_statistics(start_date, end_date) -> Dict
       def get_latest_trade_date() -> Optional[str]
       def get_by_trade_date(trade_date) -> List[Dict]

       # 写入操作
       def bulk_upsert(df: pd.DataFrame) -> int
       def delete_by_date_range(start_date, end_date) -> int

       # 数据验证
       def exists_by_date(trade_date) -> bool
       def get_record_count(start_date, end_date) -> int
   ```

3. **添加完整文档注释**
   ```python
   def get_by_date_range(
       self,
       start_date: str,
       end_date: str,
       ts_code: Optional[str] = None
   ) -> List[Dict]:
       """
       按日期范围查询数据

       Args:
           start_date: 开始日期，格式：YYYYMMDD
           end_date: 结束日期，格式：YYYYMMDD
           ts_code: 股票代码（可选）

       Returns:
           数据列表

       Examples:
           >>> repo = YourRepository()
           >>> data = repo.get_by_date_range('20240101', '20240131')
       """
   ```

4. **使用参数化查询**
   ```python
   # ✅ 正确：使用参数化查询
   query = "SELECT * FROM table WHERE trade_date >= %s AND trade_date <= %s"
   result = self.execute_query(query, (start_date, end_date))

   # ❌ 错误：字符串拼接（SQL 注入风险）
   query = f"SELECT * FROM table WHERE trade_date >= '{start_date}'"
   ```

   **⚠️ psycopg2 中 LIKE 模式的 `%` 转义**：psycopg2 在解析查询字符串时将 `%` 视为参数占位符的前缀，即使是硬编码在查询字符串中的 `%` 也会被处理。在查询字符串（非参数元组）中使用 `LIKE` 模式时，必须将 `%` 写成 `%%`：
   ```python
   # ✅ 正确：%% 被 psycopg2 转义为 %，最终 SQL 为 LIKE '%.%'
   query = "SELECT code FROM stock_daily WHERE code LIKE '%%.%%'"
   cursor.execute(query, params)

   # ❌ 错误：% 会被 psycopg2 解释为参数占位符，导致格式错误
   query = "SELECT code FROM stock_daily WHERE code LIKE '%.%'"
   cursor.execute(query, params)
   ```

5. **实现 UPSERT 语义**
   ```python
   def bulk_upsert(self, df: pd.DataFrame) -> int:
       """批量插入/更新数据"""
       query = f"""
           INSERT INTO {self.TABLE_NAME} (col1, col2, col3)
           VALUES (%s, %s, %s)
           ON CONFLICT (unique_key)
           DO UPDATE SET
               col2 = EXCLUDED.col2,
               col3 = EXCLUDED.col3,
               updated_at = NOW()
       """
   ```

6. **Numpy类型转换（重要！）**
   ```python
   def bulk_upsert(self, df: pd.DataFrame) -> int:
       """批量插入/更新数据"""
       if df is None or df.empty:
           return 0

       # 辅助函数：将pandas/numpy类型转换为Python原生类型
       def to_python_type(value):
           """
           将pandas/numpy类型转换为Python原生类型

           ⚠️ 关键问题：psycopg2无法直接处理numpy类型（numpy.int64, numpy.float64等）
           必须转换为Python原生类型（int, float, None）
           否则会报错：can't adapt type 'numpy.int64' 或 integer out of range
           """
           if pd.isna(value):
               return None
           # 转换numpy整数类型为Python int
           if isinstance(value, (pd.Int64Dtype, int)) or hasattr(value, 'item'):
               try:
                   return int(value)
               except (ValueError, TypeError):
                   return None
           # 转换numpy浮点类型为Python float
           if isinstance(value, float) or (hasattr(value, 'dtype') and 'float' in str(value.dtype)):
               return float(value)
           return value

       # 准备插入数据（对每个字段应用类型转换）
       values = []
       for _, row in df.iterrows():
           values.append((
               to_python_type(row.get('col1')),
               to_python_type(row.get('col2')),
               to_python_type(row.get('col3')),
           ))

       # 执行批量插入
       count = self.execute_batch(query, values)
       return count
   ```

   **常见错误和解决方案**：
   - ❌ 错误：直接使用 `df.where(pd.notnull(df), None)` - 仍保留numpy类型
   - ❌ 错误：直接使用 `row.get('field')` - 返回numpy类型（如numpy.int64）
   - ✅ 正确：使用 `to_python_type()` 转换所有字段值
   - ✅ 正确：检查 `pd.isna()` 处理NULL值
   - ✅ 正确：使用 `int(value)` 和 `float(value)` 转换numpy类型

7. **完整的异常处理**
   ```python
   try:
       result = self.execute_query(query, params)
       return result
   except PsycopgDatabaseError as e:
       logger.error(f"查询失败: {e}")
       raise QueryError(
           "数据查询失败",
           error_code="YOUR_QUERY_FAILED",
           reason=str(e)
       )
   ```

**使用示例**：

```python
from app.repositories import MoneyflowRepository

# 初始化
repo = MoneyflowRepository()

# 查询数据
data = repo.get_by_date_range('20240101', '20240131', ts_code='000001.SZ')

# 获取统计
stats = repo.get_statistics('20240101', '20240131')
print(f"平均净流入: {stats['avg_net_amount']}")

# 获取排名
top20 = repo.get_top_by_net_amount('20240115', limit=20)

# 批量插入（UPSERT）
import pandas as pd
df = pd.DataFrame({...})
count = repo.bulk_upsert(df)
```

**设计原则**：

- ✅ Repository 只负责数据访问，不包含业务逻辑
- ✅ 使用 `ON CONFLICT DO UPDATE` 实现 UPSERT 语义
- ✅ 返回类型化的字典，便于 Service 层使用
- ✅ 支持可选参数，提供灵活的查询能力
- ✅ 完整的异常处理（`QueryError`, `DatabaseError`）
- ✅ 继承 `BaseRepository`，复用 SQL 注入防护
- ✅ 使用类型提示（Type Hints）
- ✅ 添加 Examples 示例代码

**BaseRepository 新增方法**（✨ 2026-03-20）：

为支持批次管理器和训练任务管理器的重构，在 `BaseRepository` 中新增了以下通用方法：

1. **execute_query_returning()** - 执行带 RETURNING 子句的查询
   - 用途：INSERT/UPDATE 操作需要返回新插入/更新的记录 ID
   - 示例：
   ```python
   result = repo.execute_query_returning(
       "INSERT INTO table (col1) VALUES (%s) RETURNING id", (value,)
   )
   new_id = result[0][0]
   ```

2. **execute_batch()** - 批量执行语句
   - 用途：批量插入/更新多条记录，提高性能
   - 使用 `cursor.executemany()` 实现
   - 示例：
   ```python
   values = [(1, 'a'), (2, 'b'), (3, 'c')]
   count = repo.execute_batch(
       "INSERT INTO table (id, name) VALUES (%s, %s)", values
   )
   ```

这些方法已被 `BatchRepository` 和 `ExperimentRepository` 使用，用于批次创建、实验批量插入等操作。

### 股票数据服务模块（Stock Services）

股票数据服务已从单一的 `DataDownloadService` 重构为模块化的专门服务，符合单一职责原则。

#### 服务架构

**模块位置**：`backend/app/services/stock/`

**核心服务**：

1. **StockListService** - 股票列表管理
   - 下载和更新股票列表
   - 自动市场分类（使用 `MarketClassifier` 工具）
   - 股票信息查询（带缓存）
   - 市场分布统计

2. **DailyDataService** - 日线数据管理
   - 下载单只股票日线数据
   - 统一数据格式转换（使用 `DataTransformer` 工具）
   - 增量更新支持
   - 数据覆盖情况查询

3. **BatchDownloadService** - 批量下载编排
   - 串行下载（带延迟，避免限流）
   - 并发下载（高性能模式）
   - 增量批量更新
   - 智能模式选择

4. **DataValidationService** - 数据验证
   - 单只/批量股票数据验证
   - 数据质量报告生成
   - 缺失数据识别
   - 过期数据检测
   - 质量分数计算和改进建议

**工具类**（`backend/app/utils/`）：

1. **MarketClassifier** - 市场分类工具
   - 根据股票代码自动判断市场类型
   - 支持上海主板、科创板、深圳主板、创业板、北交所
   - 提供过滤、统计、验证等功能

2. **DataTransformer** - 数据转换工具
   - 统一日线数据和股票列表格式转换
   - 列名映射（中文 → 英文）
   - 日期格式标准化
   - 数据类型转换和验证

#### 使用示例

```python
from app.services.stock import (
    StockListService,
    DailyDataService,
    BatchDownloadService,
    DataValidationService
)

# 股票列表下载
stock_list_service = StockListService()
result = await stock_list_service.download_and_save()

# 单只股票下载
daily_data_service = DailyDataService()
count = await daily_data_service.download_and_save('000001', years=5)

# 批量下载
batch_service = BatchDownloadService()
result = await batch_service.download_batch_concurrent(max_concurrent=20)

# 数据验证
validation_service = DataValidationService()
report = await validation_service.get_data_quality_report()
print(f"数据质量分数: {report['quality_score']}/100")
```

#### 重构收益

| 指标 | 重构前 | 重构后 | 改善 |
|------|--------|--------|------|
| **服务类数量** | 1个庞大类 | 4个专门类 + 2个工具类 | 模块化 ✅ |
| **单一职责** | 5个混合职责 | 每个类1个职责 | 符合SRP ✅ |
| **DatabaseManager** | 直接使用 | 完全移除 | 架构合规 ✅ |
| **akshare直接调用** | 有 | 移除 | 统一Provider ✅ |
| **数据转换逻辑** | 分散在Service | 集中在工具类 | 代码复用 ✅ |
| **可测试性** | 低（依赖多） | 高（独立模块） | 易测试 ✅ |

#### 废弃说明

`DataDownloadService` 已标记为废弃（`@deprecated`），计划于 2026年9月 移除。现有代码继续工作，但会显示废弃警告。建议迁移到新的专门服务。

### Service 层重构最佳实践

Service 层应避免直接使用 `DatabaseManager` 或编写 SQL，而是通过 Repository 层访问数据库。

**重构前的反模式**：
```python
class MarginService:
    def __init__(self):
        self.db_manager = DatabaseManager()  # ❌ 直接使用 DB

    async def _insert_margin_data(self, df):
        insert_query = """INSERT INTO..."""  # ❌ 在 Service 写 SQL
        await asyncio.to_thread(
            self.db_manager._execute_update, ...
        )
```

**重构后的正确模式**：
```python
class MarginService:
    def __init__(self):
        self.margin_repo = MarginRepository()  # ✅ 使用 Repository

    async def sync_margin(self, params):
        # 1. 从 Tushare 获取数据
        df = await self._fetch_from_tushare(params)

        # 2. 数据验证和清洗
        df = self._validate_and_clean_data(df)

        # 3. 通过 Repository 保存
        records = await asyncio.to_thread(
            self.margin_repo.bulk_upsert, df
        )  # ✅ SQL 在 Repository

        return {"status": "success", "records": records}
```

**重构检查清单**：
1. ✅ Service 构造函数中注入 Repository 实例
2. ✅ 移除所有 `DatabaseManager` 的使用
3. ✅ 移除所有手写的 SQL 语句
4. ✅ 使用 `asyncio.to_thread()` 调用 Repository 的同步方法
5. ✅ 保持 Service 层专注于业务逻辑编排

**Facade 服务依赖注入最佳实践** （✨ 2026-03-20）：

在重构后，某些 Service 已经迁移到 Repository 模式，不再需要 `db` 参数。在 Facade 服务中初始化子服务时，需要注意区分：

```python
# ✅ 正确示例
class ExperimentService:
    def __init__(self, db=None):
        # BatchManager 已使用 Repository，无需 db
        self.batch_manager = BatchManager()

        # ExperimentRunner 仍需要 db
        self.experiment_runner = ExperimentRunner(db)
        self.experiment_repo = ExperimentRepository(db)

# ❌ 错误示例（会导致 TypeError）
class ExperimentService:
    def __init__(self, db=None):
        self.batch_manager = BatchManager(db)  # ❌ BatchManager 不接受 db
```

**已迁移到 Repository 模式的服务**（无需 db 参数）：
- `BatchManager` - 使用 `BatchRepository` + `ExperimentRepository`
- `TrainingTaskManager` - 使用 `ExperimentRepository`

**仍需要 db 参数的服务**：
- `ExperimentRunner`
- `ModelPredictor`
- `ExperimentRepository`
- 大部分其他 Service 类

**已重构的 Service**：
- **股票数据服务（Stock Services）**：
  - `StockListService` - 股票列表管理服务
  - `DailyDataService` - 日线数据管理服务
  - `BatchDownloadService` - 批量下载编排服务
  - `DataValidationService` - 数据验证服务
- **资金流向服务**：
  - `MoneyflowService` - 个股资金流向服务（Tushare标准）
  - `MoneyflowHsgtService` - 沪深港通资金流向服务
  - `MoneyflowMktDcService` - 大盘资金流向服务（东财DC）
  - `MoneyflowIndDcService` - 板块资金流向服务（东财DC）
  - `MoneyflowStockDcService` - 个股资金流向服务（东财DC）
- **融资融券服务**：
  - `MarginService` - 融资融券交易汇总服务
  - `MarginDetailService` - 融资融券交易明细服务
  - `MarginSecsService` - 融资融券标的服务（盘前更新）
- **扩展数据服务**：
  - `DailyBasicService` - 每日指标服务
  - `BlockTradeService` - 大宗交易服务
  - `StkLimitService` - 涨跌停价格服务
  - `HkHoldService` - 北向资金持股服务
- **配置和同步服务**：
  - `SyncStatusManager` - 同步状态管理服务
- **回测历史服务**：
  - `BacktestHistoryService` - 回测历史管理服务
- **定时任务管理服务** （✨ 2026-03-20 重构完成）：
  - `ScheduledTaskService` - 定时任务配置和执行管理服务（已使用 TaskExecutionHistoryRepository）
- **回测和实验服务** （✨ 新增于 2026-03-20）：
  - `BacktestDataLoader` - 回测数据加载服务（已使用 StockDailyRepository）
  - `ExperimentRunner` - 实验运行器（已使用 ExperimentRepository）
  - `ModelRanker` - 模型排名器（已使用 ExperimentRepository）
  - `ModelPredictor` - 模型预测器（已使用 ExperimentRepository）
- **批次和训练任务管理服务** （✨ 2026-03-20 重构完成）：
  - `BatchManager` - 批次管理器（已使用 BatchRepository + ExperimentRepository，移除 4 处直接 SQL）
  - `TrainingTaskManager` - 训练任务管理器（已使用 ExperimentRepository，移除 3 处直接 SQL）
- **任务历史记录辅助服务** （✨ 新增于 2026-03-20）：
  - `TaskHistoryHelper` - 统一的 Celery 任务历史记录创建服务

**已创建的扩展数据 Repository**：
- ✅ `DailyBasicRepository` - 每日指标数据
- ✅ `HkHoldRepository` - 北向资金持股数据
- ✅ `StkLimitRepository` - 涨跌停价格数据
- ✅ `BlockTradeRepository` - 大宗交易数据
- ✅ `SyncLogRepository` - 同步日志管理（sync_log 表）
- ✅ `StockDailyRepository` - 股票日线数据（2026-03-20 新增）
- ✅ `StockBasicRepository` - 股票基础信息（2026-03-20 新增）
- ✅ `TaskExecutionHistoryRepository` - 定时任务执行历史（2026-03-20 新增）
- ✅ `UserQuotaRepository` - 用户配额管理（2026-03-20 新增）

**已重构的 API 端点**：
- ✅ `extended_data.py` - 7个端点全部重构完成：
  - `GET /daily-basic/{ts_code}` - 使用 DailyBasicService
  - `GET /moneyflow/{ts_code}` - 使用 MoneyflowService
  - `GET /hk-hold` - 使用 HkHoldService
  - `GET /margin/{ts_code}` - 使用 MarginDetailService
  - `GET /limit-prices` - 使用 StkLimitService
  - `GET /block-trade` - 使用 BlockTradeService
  - `GET /stats/summary` - 并发调用多个 Service（使用 asyncio.gather）
- ✅ `moneyflow.py` - 3个端点（查询、同步、排名），使用 MoneyflowService
- ✅ `moneyflow_hsgt.py` - 3个端点（查询、同步、最新），使用 MoneyflowHsgtService
- ✅ `moneyflow_mkt_dc.py` - 3个端点（查询、同步、最新），使用 MoneyflowMktDcService
- ✅ `moneyflow_ind_dc.py` - 3个端点（查询、同步、最新），使用 MoneyflowIndDcService
- ✅ `moneyflow_stock_dc.py` - 3个端点（查询、同步、排名），使用 MoneyflowStockDcService
- ✅ `backtest_history.py` - 3个端点（用户回测历史、详情、删除），使用 BacktestHistoryService
- ✅ `profile.py` - 用户配额管理端点，使用 UserQuotaRepository（移除存储过程直接调用）
- ✅ `scheduler.py` - 11个端点全部重构完成（✨ 2026-03-20）：
  - `GET /tasks` - 获取所有定时任务列表
  - `GET /tasks/{id}` - 获取任务详情
  - `POST /tasks` - 创建定时任务
  - `PUT /tasks/{id}` - 更新定时任务
  - `DELETE /tasks/{id}` - 删除定时任务
  - `POST /tasks/{id}/toggle` - 切换任务启用状态
  - `GET /tasks/{id}/history` - 获取任务执行历史
  - `GET /history/recent` - 获取最近执行历史
  - `POST /tasks/{id}/execute` - 手动执行任务
  - `GET /tasks/{id}/status` - 获取任务执行状态
  - `POST /validate-cron` - 验证Cron表达式
  - **重构成果**：从 898 行减少到 426 行（↓ 53%），移除所有直接 SQL（15 处）
- ✅ `execution.py` (回测模块) - 股票名称查询重构完成（✨ 2026-03-20）：
  - 移除直接 SQL 查询（22行 → 3行，↓ 86%）
  - 使用 StockBasicRepository.get_stock_names() 批量查询
  - 消除 SQL 注入风险

### Repository 层扩展 - StockBasic 和 TaskExecutionHistory（✨ 2026-03-20）

#### 背景
为了完成 API 层和 Service 层的架构清洁工作，新增了两个核心 Repository：
1. `StockBasicRepository` - 解决回测模块中股票名称查询的直接 SQL 问题
2. `TaskExecutionHistoryRepository` - 解决定时任务服务中的 4 处 TODO 和直接 SQL 查询

#### StockBasicRepository

**功能**：
- 批量获取股票名称映射（核心功能）
- 按代码、市场、行业查询股票信息
- 股票列表查询和统计

**关键方法**：
```python
def get_stock_names(codes: List[str]) -> Dict[str, str]
    """批量获取股票名称映射（使用 PostgreSQL ANY 操作符）"""

def get_by_code(code: str) -> Optional[Dict]
    """按股票代码查询单条记录"""

def count_by_status(status: str) -> int
    """按状态统计股票数量"""
```

**应用场景**：
- 回测模块：为交易记录添加股票名称
- 股票列表页面：查询和过滤股票
- 数据验证：检查股票代码是否存在

#### TaskExecutionHistoryRepository

**功能**：
- 创建和更新任务执行历史记录
- 按任务ID/任务名称查询执行历史
- 获取任务执行统计（成功率、平均耗时等）
- 清理过期历史记录

**关键方法**：
```python
def create(execution_data: Dict) -> int
    """创建任务执行历史记录"""

def get_by_task_id(task_id: int, limit: int) -> List[Dict]
    """按任务ID查询执行历史"""

def get_statistics_by_task_id(task_id: int, days: int) -> Dict
    """获取任务执行统计（成功率、平均耗时）"""
```

**应用场景**：
- 定时任务管理：查询任务执行历史
- 任务统计分析：计算成功率、平均耗时
- 系统监控：识别失败任务

#### 数据格式兼容性处理

**问题**：DatabaseManager 的 `_execute_query()` 返回 `List[Tuple]`，而不是 `List[Dict]`

**解决方案**：添加 `_row_to_dict()` 辅助方法统一转换格式

```python
def _row_to_dict(self, row: tuple) -> Dict:
    """将查询结果行转换为字典"""
    return {
        'id': row[0],
        'code': row[1],
        'name': row[2],
        ...
    }
```

**应用位置**：
- StockBasicRepository: 8个查询方法
- TaskExecutionHistoryRepository: 6个查询方法

#### 重构成果

| 模块 | 重构前 | 重构后 | 改善 |
|------|--------|--------|------|
| execution.py | 22行直接SQL | 3行Repository调用 | ↓ 86% |
| scheduled_task_service.py | 4处TODO + 4处直接SQL | 0处TODO，全Repository | ✅ 100% |
| 新增Repository | 0 | 2（共 982 行） | ✅ 扩展 |
| SQL注入风险 | 字符串拼接 | 参数化查询 | ✅ 消除 |

### 任务历史记录统一管理（✨ 2026-03-20）

#### TaskHistoryHelper 辅助服务

为了消除代码重复，创建了统一的 `TaskHistoryHelper` 服务类，封装 Celery 任务历史记录的创建逻辑。

**使用场景**：
所有异步同步任务（`/sync-async` 端点）都应使用 `TaskHistoryHelper` 创建任务历史记录。

**使用示例**：
```python
from app.services import TaskHistoryHelper

# 提交 Celery 任务
celery_task = sync_moneyflow_task.apply_async(kwargs={...})

# 使用 TaskHistoryHelper 创建任务历史记录
helper = TaskHistoryHelper()
task_data = await helper.create_task_record(
    celery_task_id=celery_task.id,
    task_name='tasks.sync_moneyflow',
    display_name='个股资金流向（Tushare）',
    task_type='data_sync',
    user_id=current_user.id,
    task_params={
        'ts_code': ts_code,
        'trade_date': trade_date_formatted,
        ...
    },
    source='moneyflow_page'
)

return ApiResponse.success(data=task_data, ...)
```

**已迁移的 API 端点**（✨ 2026-03-20）：
- ✅ `moneyflow.py` - 个股资金流向（Tushare）
- ✅ `moneyflow_hsgt.py` - 沪深港通资金流向
- ✅ `moneyflow_mkt_dc.py` - 大盘资金流向（DC）
- ✅ `moneyflow_ind_dc.py` - 板块资金流向（DC）
- ✅ `moneyflow_stock_dc.py` - 个股资金流向（DC）
- ✅ `margin.py` - 融资融券交易汇总
- ✅ `margin_detail.py` - 融资融券交易明细
- ✅ `margin_secs.py` - 融资融券标的（盘前更新）

**重构收益**：
- 消除了约 **280 行重复代码**（8 个文件 × 35 行/文件）
- 移除 8 处 `DatabaseManager` 直接使用
- 移除 8 处 `INSERT INTO celery_task_history` SQL 语句
- 统一任务历史记录创建逻辑，便于维护

**关键修复**（✨ 2026-03-20）：
- 修复 `CeleryTaskHistoryRepository.create_task_history` 使用错误的数据库操作方法
- 将 `execute_query()` 改为 `execute_query_returning()` 用于 INSERT RETURNING 语句
- 此修复解决了任务历史记录无法持久化的问题，确保前端任务轮询和自动刷新正常工作

**重构完成度**（✅ 2026-03-20 全部完成）：
1. **高优先级**：配置和同步相关服务（✅ 已完成）
   - `SystemConfigService` - 已使用 ConfigRepository
   - `DataSourceConfigService` - 已使用 ConfigRepository
   - `SyncStatusManager` - 已使用 ConfigRepository + SyncLogRepository
2. **中优先级**：数据同步和扩展数据服务（✅ 已完成）
   - 资金流向、融资融券、每日指标等服务已全部重构
3. **中高优先级**：回测和机器学习相关服务（✅ 已完成）
   - `BacktestDataLoader` - 已使用 StockDailyRepository（移除 DatabaseManager）
   - `ExperimentRunner` - 已使用 ExperimentRepository（移除 3 处直接 SQL）
   - `ModelRanker` - 已使用 ExperimentRepository（移除 6 处直接 SQL）
   - `ModelPredictor` - 已使用 ExperimentRepository（移除 1 处直接 SQL）
   - `profile.py` API - 已使用 UserQuotaRepository（移除存储过程直接调用）
4. **批次和训练任务管理**（✅ 2026-03-20 完成）：
   - `BatchManager` - 已使用 BatchRepository + ExperimentRepository（移除 4 处直接 SQL）
   - `TrainingTaskManager` - 已使用 ExperimentRepository（移除 3 处直接 SQL）

**Service 层重构总结**：
- ✅ **已完全消除违规**：所有 Service 层不再包含直接 SQL 操作
- ✅ **架构合规**：Service 层完全通过 Repository 层访问数据库
- ✅ **代码质量**：代码行数减少约 18%，可维护性显著提升
- ⚠️ **已废弃文件**：`data_service.py` 已标记废弃，计划于 2026年9月 移除

### 新增功能开发流程

1. **定义 Schema**：在 `schemas/` 中定义请求/响应模型
2. **创建 Repository**（如需要）：在 `repositories/` 中实现数据访问层
3. **实现 Service**：在 `services/` 中实现业务逻辑
4. **添加 API**：在 `api/endpoints/` 中定义路由
5. **编写测试**：在 `tests/` 中添加单元测试

### API 层重构最佳实践

当 API 端点包含直接 SQL 查询时，应重构为使用 Service + Repository 层。

#### 重构模式 1：简单查询（直接使用 Repository）

适用于：纯数据查询，无复杂业务逻辑

**重构前的反模式**：
```python
# ❌ 42行代码，直接写 SQL
@router.get("/daily-basic/{ts_code}")
def get_daily_basic(ts_code: str, db: Session = Depends(get_db)):
    query_str = """
        SELECT ts_code, trade_date, close, turnover_rate, ...
        FROM daily_basic
        WHERE ts_code = :ts_code
        ORDER BY trade_date DESC LIMIT :limit
    """
    params = {"ts_code": ts_code, "limit": limit}
    result = db.execute(text(query_str), params)
    rows = result.fetchall()
    data = [dict(row._mapping) for row in rows]  # 手动转换
    return {"code": 0, "data": data, ...}
```

**重构后的正确模式**：
```python
# ✅ 10行代码，调用 Repository
@router.get("/daily-basic/{ts_code}")
def get_daily_basic(ts_code: str, start_date: Optional[date] = None, ...):
    repo = DailyBasicRepository()
    items = repo.get_by_code_and_date_range(
        ts_code, start_date_str, end_date_str, limit
    )
    return ApiResponse.success(data={"items": items, "count": len(items)})
```

#### 重构模式 2：复杂业务逻辑（Service + Repository）

适用于：包含数据转换、统计分析、多表查询等业务逻辑

**重构前的反模式**：
```python
# ❌ API 层包含业务逻辑
@router.get("/moneyflow")
async def get_moneyflow(
    ts_code: Optional[str] = None,
    start_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    # 1. 查询数据（SQL）
    query = text("SELECT ... FROM moneyflow WHERE ...")
    result = db.execute(query, params)
    items = [dict(row) for row in result]

    # 2. 查询统计（SQL）
    stats_query = text("SELECT AVG(...), MAX(...) FROM moneyflow WHERE ...")
    stats_result = db.execute(stats_query, params)
    statistics = dict(stats_result.fetchone())

    # 3. 日期格式转换（业务逻辑）
    for item in items:
        item['trade_date'] = format_date(item['trade_date'])

    # 4. 单位换算（业务逻辑）
    for item in items:
        item['net_mf_amount'] = item['net_mf_amount'] / 10000  # 万元

    return {"items": items, "statistics": statistics}
```

**重构后的正确模式**：

```python
# API 层 - 只处理 HTTP
@router.get("/moneyflow")
async def get_moneyflow(
    ts_code: Optional[str] = None,
    start_date: Optional[str] = None,
    limit: int = 30
):
    service = MoneyflowService()
    result = await service.get_moneyflow_data(ts_code, start_date, limit)
    return ApiResponse.success(data=result)

# Service 层 - 只处理业务逻辑
class MoneyflowService:
    def __init__(self):
        self.moneyflow_repo = MoneyflowRepository()

    async def get_moneyflow_data(self, ts_code, start_date, limit):
        # 1. 日期格式转换（业务逻辑）
        start_date_fmt = start_date.replace('-', '') if start_date else None

        # 2. 获取数据（通过 Repository）
        items = self.moneyflow_repo.get_by_date_range(
            start_date=start_date_fmt,
            ts_code=ts_code,
            limit=limit
        )

        # 3. 获取统计（通过 Repository）
        statistics = self.moneyflow_repo.get_statistics(
            start_date=start_date_fmt,
            ts_code=ts_code
        )

        # 4. 单位换算（业务逻辑）
        for item in items:
            item['net_mf_amount'] = item['net_mf_amount'] / 10000

        return {
            "items": items,
            "statistics": statistics,
            "total": len(items)
        }

# Repository 层 - 只处理数据访问
class MoneyflowRepository(BaseRepository):
    def get_by_date_range(self, start_date, ts_code, limit):
        query = """
            SELECT trade_date, ts_code, net_mf_amount, ...
            FROM moneyflow
            WHERE trade_date >= %s AND ts_code = %s
            ORDER BY trade_date DESC
            LIMIT %s
        """
        return self.execute_query(query, (start_date, ts_code, limit))
```

**重构收益**：
- ✅ 代码行数减少 40-70%
- ✅ SQL 集中在 Repository，便于维护和测试
- ✅ 业务逻辑集中在 Service，便于复用
- ✅ API 层代码减少到 5-10 行
- ✅ 参数化查询，防止 SQL 注入
- ✅ 统一的错误处理和日志记录
- ✅ Service 和 Repository 可被多个端点复用
- ✅ 易于编写单元测试

**实际重构案例（资金流向模块）**：

| 文件 | 重构前 | 重构后 | 减少比例 |
|------|--------|--------|----------|
| moneyflow.py | 409行 | 237行 | ↓ 42% |
| moneyflow_hsgt.py | 342行 | 213行 | ↓ 38% |
| moneyflow_mkt_dc.py | 370行 | 154行 | ↓ 58% |
| moneyflow_ind_dc.py | 418行 | 146行 | ↓ 65% |
| moneyflow_stock_dc.py | 387行 | 140行 | ↓ 64% |
| **总计** | **1926行** | **890行** | **↓ 54%** |

重构成果：
- 创建 5 个 Service 类，封装业务逻辑
- 移除 API 层所有 SQL 查询（约 800 行）
- 移除所有数据库依赖 (`db: Session`)
- 统一使用 `asyncio.to_thread()` 调用 Repository

### 注意事项

- ✅ API 层应保持简洁（一般不超过50行/端点）
- ✅ 复杂业务逻辑应放在 Service 层
- ✅ Service 层方法应拆分为小的私有方法
- ✅ 使用 Pydantic 模型进行参数验证
- ✅ 使用 `ApiResponse.success()` 返回统一格式
- ❌ 避免在 API 层直接访问数据库（使用 Repository）
- ❌ 避免在 API 层编写 SQL 查询
- ❌ 避免在 Service 层处理 HTTP 相关逻辑

### 模块化拆分最佳实践

当单个 API 端点文件超过 500 行时，应考虑按功能模块拆分为包结构：

**拆分示例 1** (sentiment 模块重构，已精简):
```
# 重构前
endpoints/sentiment.py (1018行) - 单一文件

# 重构后（2026-03-25精简版）
endpoints/sentiment/
├── __init__.py          # 路由聚合
├── query.py             # 查询类端点（交易日历）
├── sync.py              # 同步类端点
└── ai_analysis.py       # AI分析端点

注：已移除 cycle.py（情绪周期）和大量市场情绪相关端点
```

**拆分示例 2** (backtest 模块重构):
```
# 重构前
endpoints/backtest.py (2360行) - 单一文件

# 重构后
endpoints/backtest/
├── __init__.py          # 路由聚合
├── schemas.py           # Pydantic 数据模型
├── execution.py         # 核心回测执行
├── metrics.py           # 指标计算
├── parallel.py          # 并行回测
├── optimization.py      # 参数优化
├── analysis.py          # 成本和交易分析
└── async_backtest.py    # 异步回测
```

**重构收益** (以 backtest 为例):
- 单文件行数：2360行 → 最大950行 (↓60%)
- 代码组织：1个混合文件 → 8个专门模块
- 最大函数：915行 → 约100行/端点 (↓89%)
- 可维护性：显著提升，功能定位更快速

**拆分原则**：
1. **按功能域划分**：查询、同步、分析等不同功能分到不同文件
2. **Schema 独立**：所有 Pydantic 模型集中在 `schemas.py`
3. **路由聚合**：在 `__init__.py` 中统一注册子路由
4. **向后兼容**：确保 API 路径和响应格式保持不变

**路由注册示例** (`__init__.py`):
```python
from fastapi import APIRouter
from . import query, sync, ai_analysis

router = APIRouter()

# 注册子路由
router.include_router(query.router, tags=["sentiment-query"])
router.include_router(sync.router, tags=["sentiment-sync"])
router.include_router(ai_analysis.router, prefix="/ai-analysis", tags=["sentiment-ai"])
```

**优势**：
- 更好的代码组织和可维护性
- 降低单个文件的复杂度
- 便于并行开发和代码审查
- 符合单一职责原则

### Scheduler 模块架构

定时任务调度模块采用模块化架构，提供数据库驱动的动态任务调度：

**模块结构**：
```
backend/app/scheduler/
├── __init__.py                # 统一导出
├── database_scheduler.py      # 数据库驱动的 Celery Beat 调度器
├── task_executor.py           # 任务执行器（手动触发）
├── task_metadata.py           # 任务元数据配置（集中管理）
├── task_metadata_service.py   # 元数据管理服务
└── cron_parser.py             # Cron 表达式解析器
```

**核心组件**：

1. **task_metadata.py** - 任务元数据配置
   - 存储所有任务的完整元数据（37个任务）
   - 包含任务名称、描述、分类、显示顺序、积分消耗等
   - 作为单一数据源，便于维护和扩展

2. **task_metadata_service.py** - 元数据管理服务
   - 封装任务元数据访问逻辑
   - 提供查询、过滤、合并参数等12个方法
   - 隐藏实现细节，便于单元测试

3. **cron_parser.py** - Cron 解析器
   - 独立的 Cron 表达式解析模块
   - 可复用、可独立测试
   - 支持表达式验证和错误处理

4. **database_scheduler.py** - 数据库调度器
   - 从数据库动态加载任务配置
   - 每30秒自动同步配置变更
   - 支持启用/禁用任务、修改 Cron 表达式

5. **task_executor.py** - 任务执行器
   - 手动触发任务执行
   - 查询任务状态
   - 取消任务

**使用示例**：

```python
# 导入服务
from app.scheduler import TaskMetadataService

# 获取任务友好名称
service = TaskMetadataService()
display_name = service.get_friendly_name('sentiment', 'default_name')

# 合并任务参数（自动过滤元数据字段）
params = service.merge_task_params('sentiment', {'custom': 'value', 'priority': 1})
# 结果: {'custom': 'value'}  # priority 被过滤
```

**新增任务流程**：

1. 在 `task_metadata.py` 中添加任务配置：
```python
TASK_MAPPING = {
    'your_module.your_task': {
        'task': 'tasks.your_celery_task_name',
        'name': '任务显示名称',
        'description': '任务描述',
        'category': '任务分类',
        'display_order': 100
    }
}
```

2. 其他模块自动识别新任务，无需修改其他代码

**向后兼容性**：
- TaskExecutor 保留 `TASK_MAPPING` 属性访问（通过 `@property`）
- 现有代码无需修改即可使用

### Service 层模块化拆分（Scheduler 服务）

**背景**：`ScheduledTaskService` 原有 918 行代码，包含 8 个混合职责，不符合单一职责原则。

**重构架构**：

```
backend/app/
├── schemas/
│   └── scheduler_schemas.py        # Pydantic 数据模型（143 行）
└── services/
    ├── scheduler/                  # 新模块化架构
    │   ├── __init__.py            # 聚合服务，向后兼容（106 行）
    │   ├── cron_service.py        # Cron 工具（115 行）
    │   ├── task_config_service.py # 任务配置 CRUD（502 行）
    │   ├── task_history_service.py # 执行历史查询（139 行）
    │   └── task_execution_service.py # 任务执行和状态（231 行）
    └── scheduled_task_service.py  # 废弃（已标记，计划 2026年9月移除）
```

**职责划分**：

1. **CronService** - Cron 表达式工具
   - Cron 表达式验证
   - 计算下次执行时间
   - 日期格式化工具

2. **TaskConfigService** - 任务配置 CRUD
   - 任务配置的增删改查
   - 任务启用/禁用
   - 分类排序管理

3. **TaskHistoryService** - 执行历史查询
   - 查询任务执行历史
   - 格式化历史数据
   - 关联任务配置信息

4. **TaskExecutionService** - 任务执行和状态
   - 手动执行定时任务
   - 查询任务执行状态
   - 记录执行历史（双表写入）

5. **ScheduledTaskService** - 统一聚合服务
   - 聚合所有子服务
   - 向后兼容旧代码
   - 委托模式实现

**使用方式**：

```python
# 方式 1：使用专门的服务类（推荐）
from app.services.scheduler import TaskConfigService, CronService

config_service = TaskConfigService()
tasks = await config_service.get_all_tasks()

cron_service = CronService()
is_valid = cron_service.validate_cron_expression("0 9 * * *")

# 方式 2：使用统一服务（向后兼容）
from app.services.scheduler import ScheduledTaskService

service = ScheduledTaskService()
tasks = await service.get_all_tasks()
```

**重构成果**：

| 指标 | 重构前 | 重构后 | 改善 |
|------|--------|--------|------|
| 文件数量 | 1 个庞大文件 | 6 个专门文件 | ✅ 模块化 |
| 最大文件行数 | 918 行 | 502 行 | ↓ 45% |
| 单一职责 | 8 个混合职责 | 5 个独立职责 | ✅ 符合 SRP |
| 代码复用 | 重复代码多 | 共享 CronService | ✅ DRY |
| 可测试性 | 低（依赖多） | 高（独立模块） | ✅ 易测试 |
| Schema 层 | 无（混在代码中） | 独立 Schema | ✅ 分层清晰 |

**拆分原则**：
1. **单一职责**：每个服务类只负责一个明确的功能域
2. **依赖注入**：服务间通过构造函数注入依赖
3. **Schema 分离**：Pydantic 模型独立到 schemas 层
4. **向后兼容**：聚合服务使用委托模式，旧代码无需修改
5. **废弃管理**：清晰标记废弃文件，提供迁移指南

### Extended Sync Service 模块化重构（数据同步服务）

扩展数据同步服务已从 788 行的单一文件重构为按数据分类划分的模块化架构。

**重构前的问题**：
- ❌ 单一类包含 30 个方法，违反单一职责原则
- ❌ 混合了 8 种不同数据类型的同步逻辑
- ❌ 大量重复的 `_insert_xxx` 方法（10 个类似方法）

**模块结构**：
```
services/extended_sync/
├── __init__.py                      # 统一导出和聚合服务
├── common.py                        # 公共组件（枚举、数据类）
├── base_sync_service.py             # 基础同步服务（模板方法）
├── basic_data_sync.py               # 基础数据同步
├── moneyflow_sync.py                # 资金流向同步
├── margin_sync.py                   # 两融数据同步
├── reference_data_sync.py           # 参考数据同步
└── REFACTORING_SUMMARY.md           # 重构文档
```

**按数据分类划分**（符合定时任务分类标准）：

1. **基础数据** (`BasicDataSyncService`)
   - daily_basic, stk_limit, adj_factor, suspend

2. **资金流向** (`MoneyflowSyncService`)
   - moneyflow（Tushare标准）
   - moneyflow_hsgt（沪深港通）
   - moneyflow_mkt_dc（大盘，东方财富）
   - moneyflow_ind_dc（板块，东方财富）
   - moneyflow_stock_dc（个股，东方财富）

3. **两融数据** (`MarginSyncService`)
   - margin_detail（融资融券交易明细）

4. **参考数据** (`ReferenceDataSyncService`)
   - block_trade（大宗交易）

**预留扩展分类**：
- 行情数据 (`MarketDataSyncService`)
- 财务数据 (`FinancialDataSyncService`)
- 特色数据 (`SpecialDataSyncService`)
- 打板数据 (`LimitUpSyncService`)

**使用方式**：

```python
# 方式 1：使用专门的服务类（推荐）
from app.services.extended_sync import moneyflow_sync_service

result = await moneyflow_sync_service.sync_moneyflow_hsgt(
    start_date='20240301',
    end_date='20240315'
)

# 方式 2：使用聚合服务（向后兼容）
from app.services.extended_sync import extended_sync_service

result = await extended_sync_service.sync_moneyflow_hsgt(
    start_date='20240301',
    end_date='20240315'
)

# 方式 3：旧路径（显示警告，但仍可用）
from app.services.extended_sync_service import extended_sync_service

# ⚠️ 会显示 DeprecationWarning
result = await extended_sync_service.sync_moneyflow_hsgt(...)
```

**重构成果**：

| 指标 | 重构前 | 重构后 | 改善 |
|------|--------|--------|------|
| 最大文件行数 | 788行 | 257行 | ↓ 67% |
| 方法数/类 | 30个/1个类 | 5-8个/类 | ✅ 单一职责 |
| 文件数量 | 1个庞大文件 | 7个专门文件 | ✅ 模块化 |
| 代码重复 | 高（10个重复方法） | 低 | ✅ DRY原则 |
| 可测试性 | 低（依赖多） | 高（独立模块） | ✅ 易测试 |

**设计模式**：
1. **模板方法模式**：`BaseSyncService._sync_data_template()` 定义统一的同步流程
2. **策略模式**：通过传入不同的 `fetch_method` 和 `insert_method` 实现不同策略
3. **依赖注入**：各服务类在构造函数中注入 Repository 依赖

**向后兼容**：
- ✅ 100% 向后兼容，所有现有代码无需修改
- ✅ 11个受影响的文件（6个Tasks + 5个API）继续正常工作
- ✅ 旧文件已标记废弃，计划 2026年9月 移除

## 开发提示

1. 修改代码后，前端项目（admin）会自动热重载
2. 后端项目（FastAPI）在开发模式下也支持自动重载
3. 数据库使用 TimescaleDB，端口默认为 5432
4. 数据同步时会自动进行质量验证和修复

## Celery 异步任务开发指南

### 事件循环冲突问题

在 Celery fork pool worker 中运行异步代码时，可能会遇到 **"attached to a different loop"** 错误。

**根本原因**：
1. 全局的 `async_engine` 和 `AsyncSessionLocal` 在主进程中创建，绑定到主进程的事件循环
2. Celery fork pool worker 继承了这些对象，但事件循环已经不是当前循环
3. 即使创建新的事件循环，旧的数据库引擎仍然绑定到旧循环

**解决方案**：
使用 `run_async_in_celery` 辅助函数（位于 `/backend/app/tasks/extended_sync_tasks.py`）

**run_async_in_celery 的工作原理**：
1. 关闭继承自父进程的旧事件循环
2. 创建新的事件循环
3. 调用 `reset_async_engine()` 重新初始化数据库引擎（绑定到新循环）
4. 运行异步函数
5. 清理资源

### 创建新的 Celery 任务

1. **任务定义**（位于 `/backend/app/tasks/`）:
```python
from app.celery_app import celery_app
from app.tasks.extended_sync_tasks import run_async_in_celery
from loguru import logger

@celery_app.task(bind=True, name="tasks.your_task_name")
def your_task(self, param1: str, param2: int):
    """任务描述"""
    try:
        logger.info(f"开始执行任务: param1={param1}, param2={param2}")

        # 使用辅助函数运行异步代码
        service = YourService()
        result = run_async_in_celery(
            service.your_async_method,
            param1=param1,
            param2=param2
        )

        return result

    except Exception as e:
        logger.error(f"任务执行失败: {e}")
        raise
```

2. **注册任务**（在 `/backend/app/celery_app.py`）:
```python
try:
    from app.tasks import your_tasks
    logger.info(f"✅ 已加载您的任务模块")
except Exception as e:
    logger.error(f"❌ 加载任务模块失败: {e}")
```

3. **添加到任务映射**（在 `/backend/app/scheduler/task_executor.py`）:
```python
TASK_MAPPING = {
    'your_module.your_task': {
        'task': 'tasks.your_task_name',
        'name': '任务显示名称',
        'default_params': {'param1': 'default_value'}
    }
}
```

### 常见问题和解决方案

**问题1: "attached to a different loop" 或 "Event loop is closed" 错误**
- **原因**: Celery fork pool worker 中复用了绑定到父进程的事件循环
- **解决**: 使用 `run_async_in_celery` 辅助函数（已自动处理）

**问题2: 任务状态未更新到数据库**
- **原因**: Celery 信号未正确触发或数据库连接共享
- **解决**: 检查 `/backend/app/celery_signals.py` 是否正确导入

**问题3: 任务耗时计算不准确**
- **原因**: 使用 `created_at` 而非 `started_at` 计算耗时
- **解决**: 确保使用 `started_at` 作为计算起点

**问题4: 前端显示时间不正确**
- **原因**: 时区处理问题
- **解决**: API 返回时添加 'Z' 后缀标记 UTC 时间，前端自动转换

## 任务管理模块重构（2026-03-20）

### 重构概述

完成了 Celery 任务历史和定时任务配置模块的全面重构，遵循三层架构原则。

### 新增组件

#### Repository 层
1. **CeleryTaskHistoryRepository** ([celery_task_history_repository.py](backend/app/repositories/celery_task_history_repository.py:1))
   - 管理 `celery_task_history` 表的数据访问
   - 提供任务查询、创建、更新、删除、统计等 12 个方法
   - 支持活跃任务查询、僵尸任务清理、用户权限验证

2. **ScheduledTaskRepository** ([scheduled_task_repository.py](backend/app/repositories/scheduled_task_repository.py:1))
   - 管理 `scheduled_tasks` 表的数据访问
   - 提供任务配置 CRUD、启用/禁用、元数据批量更新等 15 个方法
   - 支持按模块、分类查询，任务运行状态更新

#### Service 层
1. **CeleryTaskHistoryService** ([celery_task_history_service.py](backend/app/services/celery_task_history_service.py:1))
   - 封装任务历史管理的业务逻辑
   - 处理时间格式转换（数据库本地时间 ↔ API UTC 时间）
   - 提供组合查询方法（任务列表 + 统计信息）

### 重构成果

#### API 层重构
- **文件**: [celery_tasks.py](backend/app/api/endpoints/celery_tasks.py:1)
- **重构前**: 725 行（包含 ~200 行直接 SQL）
- **重构后**: 492 行（移除所有直接 SQL）
- **代码减少**: **32%** ⬇️
- **改进**:
  - 移除所有 `text()` + `db.execute()` 反模式
  - 使用 `CeleryTaskHistoryService` 处理业务逻辑
  - API 函数平均行数从 60 行降至 20 行
  - 完整的权限校验和错误处理

#### 调度器重构
- **文件**: [database_scheduler.py](backend/app/scheduler/database_scheduler.py:1)
- **重构前**: 使用 `DatabaseManager` + 直接 SQL
- **重构后**: 使用 `ScheduledTaskRepository`
- **改进**:
  - 移除 `from src.database.db_manager import DatabaseManager`
  - 移除 `db._execute_query()` 调用
  - 符合三层架构原则
  - 便于单元测试和维护

### 重构对比

| 模块 | 重构前 | 重构后 | 改进 |
|------|--------|--------|------|
| celery_tasks.py | 725 行，200+ 行 SQL | 492 行，0 行 SQL | ↓ 32% |
| database_scheduler.py | 直接 SQL | Repository 层 | ✅ 架构合规 |
| 数据访问 | 分散在多个文件 | 集中在 Repository | ✅ 统一管理 |
| 业务逻辑 | 混合在 API 层 | Service 层独立 | ✅ 职责清晰 |

### 设计亮点

1. **时间格式统一处理**
   - Service 层统一处理 datetime → UTC ISO 8601 转换
   - 前端自动转换为本地时间显示
   - 避免时区混乱问题

2. **组合查询优化**
   - `get_task_list_with_statistics()` 并发查询列表和统计
   - 减少 API 调用次数
   - 提升前端性能

3. **完整的 CRUD 支持**
   - Repository 提供标准 CRUD 方法
   - Service 层添加业务逻辑（如权限校验）
   - API 层保持简洁（10-20 行）

4. **僵尸任务清理**
   - 自动识别超时未完成的任务
   - 支持用户级隔离
   - 批量标记为失败状态

### 使用示例

#### 查询任务历史
```python
# Service 层
service = CeleryTaskHistoryService()
tasks, total = await service.get_recent_history(
    user_id=1,
    limit=50,
    status='success'
)

# Repository 层
repo = CeleryTaskHistoryRepository()
active_tasks = repo.get_active_tasks(user_id=1)
stats = repo.get_statistics(user_id=1)
```

#### 更新定时任务配置
```python
# Repository 层
repo = ScheduledTaskRepository()
repo.update_task_config(
    task_name='daily_sentiment_sync',
    cron_expression='0 10 * * *',
    enabled=True
)
```

### 向后兼容性

- ✅ API 端点路径保持不变
- ✅ 响应格式完全兼容
- ✅ 前端代码无需修改
- ✅ Celery 信号机制不受影响

### 后续计划

根据优先级，接下来将重构以下模块：

**注意**：市场情绪相关 Repository 已移除（2026-03-25），以下为剩余待重构模块：

**第二阶段（近期）**:
1. ~~`TradingCalendarRepository`~~ - 交易日历（已完成）
2. ~~市场情绪相关 Repository（5个）~~ - 已移除功能
   - `DragonTigerListRepository`
   - `SentimentCycleRepository`
   - `SentimentAiAnalysisRepository`

**第三阶段（后续）**:
- 回测和机器学习相关 Service 的重构
- 移除所有剩余的直接 SQL 操作

---

## Repository 层开发检查清单

### 新增 Repository 检查清单

在创建新的 Repository 时，请确认以下事项：

**基础结构**：
- [ ] 继承 `BaseRepository`
- [ ] 定义 `TABLE_NAME` 类常量
- [ ] 实现 `__init__` 方法并调用 `super().__init__(db)`
- [ ] 添加类级别文档注释

**标准方法**：
- [ ] 实现 `get_by_date_range()` - 按日期范围查询
- [ ] 实现 `get_statistics()` - 获取统计信息
- [ ] 实现 `get_latest_trade_date()` - 获取最新交易日期
- [ ] 实现 `bulk_upsert()` - 批量插入/更新（UPSERT）
- [ ] 实现 `delete_by_date_range()` - 按日期范围删除
- [ ] 实现 `exists_by_date()` - 检查数据是否存在
- [ ] 实现 `get_record_count()` - 获取记录数

**代码质量**：
- [ ] 所有方法都有完整的文档注释（Args, Returns, Examples）
- [ ] 使用类型提示（Type Hints）
- [ ] 使用参数化查询（避免 SQL 注入）
- [ ] 实现完整的异常处理（`QueryError`, `DatabaseError`）
- [ ] 添加日志记录（`logger.debug`, `logger.error`）
- [ ] 每个方法至少有一个 Example 示例

**SQL 查询**：
- [ ] 使用 `%s` 占位符进行参数绑定
- [ ] 避免字符串拼接用户输入
- [ ] 使用 `ON CONFLICT DO UPDATE` 实现 UPSERT
- [ ] 为常用查询添加适当的 `ORDER BY` 和 `LIMIT`

**导出注册**：
- [ ] 在 `repositories/__init__.py` 中导入新 Repository
- [ ] 在 `__all__` 列表中添加新 Repository 名称
- [ ] 添加适当的分类注释

### 重构 Service 检查清单

在重构现有 Service 使用 Repository 时，请确认：

**移除直接数据库访问**：
- [ ] 移除 `from src.database.db_manager import DatabaseManager`
- [ ] 移除 `self.db_manager = DatabaseManager()`
- [ ] 移除所有手写的 SQL 语句（`INSERT`, `SELECT`, `UPDATE`, `DELETE`）
- [ ] 移除 `self.db_manager._execute_query()` 调用
- [ ] 移除 `self.db_manager._execute_update()` 调用

**使用 Repository**：
- [ ] 导入对应的 Repository（`from app.repositories import XxxRepository`）
- [ ] 在 `__init__` 中注入 Repository 实例
- [ ] 使用 `asyncio.to_thread()` 调用 Repository 的同步方法
- [ ] 保持 Service 方法为 `async` 函数

**业务逻辑保留**：
- [ ] 日期格式转换逻辑保留在 Service
- [ ] 单位换算逻辑保留在 Service
- [ ] 数据聚合和排序逻辑保留在 Service
- [ ] 第三方服务调用（Tushare）保留在 Service
- [ ] 数据验证和清洗逻辑保留在 Service

**示例对比**：
```python
# ❌ 重构前
class MarginService:
    def __init__(self):
        self.db_manager = DatabaseManager()

    async def get_data(self):
        query = "SELECT * FROM margin WHERE ..."
        result = await asyncio.to_thread(
            self.db_manager._execute_query, query, params
        )

# ✅ 重构后
class MarginService:
    def __init__(self):
        self.margin_repo = MarginRepository()

    async def get_data(self):
        result = await asyncio.to_thread(
            self.margin_repo.get_by_date_range, start_date, end_date
        )
```

### 重构 API 检查清单

在重构 API endpoint 时，请确认：

**移除直接数据库访问**：
- [ ] 移除 `from sqlalchemy import text`
- [ ] 移除 `db: Session = Depends(get_db)` 参数
- [ ] 移除所有 `text()` 包裹的 SQL 语句
- [ ] 移除 `db.execute()` 调用
- [ ] 移除手动数据转换逻辑（`[dict(row) for row in result]`）

**使用 Service 或 Repository**：
- [ ] 简单查询：直接使用 Repository
- [ ] 复杂业务：创建对应的 Service 类
- [ ] 导入对应的 Service/Repository
- [ ] 在函数内创建 Service/Repository 实例
- [ ] 调用 Service/Repository 方法获取数据

**API 层简化**：
- [ ] API 函数不超过 30 行（不含文档注释）
- [ ] 只包含参数验证（由 Pydantic 自动完成）
- [ ] 只包含调用 Service/Repository
- [ ] 使用 `ApiResponse.success()` 返回统一格式
- [ ] 移除业务逻辑（日期转换、单位换算等）

**示例对比**：
```python
# ❌ 重构前（50行）
@router.get("/moneyflow")
async def get_moneyflow(
    ts_code: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = text("SELECT ... FROM moneyflow WHERE ...")
    result = db.execute(query, params)
    items = [dict(row) for row in result]
    # 统计查询...
    # 数据转换...
    return {"items": items, "statistics": stats}

# ✅ 重构后（8行）
@router.get("/moneyflow")
async def get_moneyflow(ts_code: Optional[str] = None):
    service = MoneyflowService()
    result = await service.get_moneyflow_data(ts_code)
    return ApiResponse.success(data=result)
```

### 新功能开发检查清单

开发新功能时，请按以下顺序开发，并确认每个步骤：

**1. Schema 层**：
- [ ] 在 `schemas/` 中创建 Pydantic 模型
- [ ] 定义请求参数模型（继承 `BaseModel`）
- [ ] 定义响应数据模型
- [ ] 添加数据验证规则（`Field` 约束）

**2. Repository 层**（如需要）：
- [ ] 评估是否需要新的 Repository（或复用现有）
- [ ] 按照 "新增 Repository 检查清单" 创建
- [ ] 在 `repositories/__init__.py` 中导出

**3. Service 层**：
- [ ] 在 `services/` 中创建 Service 类
- [ ] 在 `__init__` 中注入 Repository 依赖
- [ ] 实现业务逻辑方法（`async` 函数）
- [ ] 使用 `asyncio.to_thread()` 调用 Repository
- [ ] 添加完整的文档注释和类型提示

**4. API 层**：
- [ ] 在 `api/endpoints/` 中创建路由
- [ ] 使用 Pydantic 模型进行参数验证
- [ ] 调用 Service 层方法
- [ ] 使用 `ApiResponse.success()` 返回统一格式
- [ ] 添加 API 文档注释（FastAPI 自动生成 OpenAPI）

**5. 测试**：
- [ ] 编写 Repository 单元测试
- [ ] 编写 Service 单元测试
- [ ] 编写 API 集成测试
- [ ] 测试异常情况和边界条件

### 代码审查检查清单

提交代码前，请自查：

**架构合规性**：
- [ ] 没有在 API 层写 SQL
- [ ] 没有在 Service 层使用 `DatabaseManager`
- [ ] 所有数据库访问都通过 Repository
- [ ] API -> Service -> Repository 分层清晰

**代码质量**：
- [ ] 所有方法都有类型提示
- [ ] 所有方法都有文档注释
- [ ] 使用参数化查询（无 SQL 注入风险）
- [ ] 完整的异常处理和日志记录
- [ ] 没有硬编码的魔法数字或字符串

**性能考虑**：
- [ ] 使用 `bulk_upsert()` 进行批量插入
- [ ] 避免 N+1 查询问题
- [ ] 为高频查询添加索引（数据库层）
- [ ] 考虑使用缓存（对于静态或低频变更数据）

**安全性**：
- [ ] 所有用户输入都经过验证（Pydantic）
- [ ] 使用参数化查询防止 SQL 注入
- [ ] 敏感信息（密码、Token）不记录在日志中
- [ ] API 端点添加适当的权限验证（`require_admin`, `get_current_user`）

### 常见问题快速排查

**问题：API 返回 500 错误**
- [ ] 检查 Service 是否正确注入 Repository
- [ ] 检查 Repository 方法签名是否正确
- [ ] 检查是否使用 `asyncio.to_thread()` 调用同步方法
- [ ] 查看日志查找具体错误信息

**问题：数据没有插入数据库**
- [ ] 检查 `bulk_upsert()` 是否返回非零值
- [ ] 检查数据库连接是否正常
- [ ] 检查是否有唯一键冲突
- [ ] 检查 DataFrame 是否包含必需列

**问题：查询结果为空**
- [ ] 检查日期格式（YYYYMMDD vs YYYY-MM-DD）
- [ ] 检查表名是否正确（`TABLE_NAME` 常量）
- [ ] 检查 WHERE 条件是否过于严格
- [ ] 使用 `get_record_count()` 验证数据是否存在
- [ ] 检查日期参数是否为 None（Service 层应提供默认值 `'19900101'` / `'29991231'`）

**问题：日期类型不一致**
- [ ] 数据库表的 `trade_date` 列类型可能不同：
  - `VARCHAR` 类型 → 返回字符串（如 `margin` 表）
  - `DATE` 类型 → 返回 `datetime.date` 对象（如 `margin_detail` 表）
- [ ] Repository 层应统一转换为字符串：
  ```python
  "trade_date": row[0].strftime('%Y%m%d') if hasattr(row[0], 'strftime') else row[0]
  ```
- [ ] Service 层应处理可能的 `datetime.date` 对象：
  ```python
  if isinstance(date_value, date):
      date_str = date_value.strftime('%Y%m%d')
  ```

**问题：API 返回 401（无认证 Token 时）**

FastAPI 使用 `HTTPBearer(auto_error=True)`（默认值），只要请求头没有 `Authorization: Bearer <token>`，在进入 endpoint 之前就直接返回 401。即使将 `require_admin` 改为 `get_current_active_user` 也无济于事——只要依赖链里有 `HTTPBearer()`，无 token 请求一律 401。

**对于需要公开访问的 endpoint（前端无需登录即可调用）**：
```python
# ❌ 错误：无 token 请求会收到 401
@router.get("/public-data")
async def get_data(current_user: User = Depends(get_current_active_user)):
    ...

# ✅ 正确：完全去掉 auth 依赖
@router.get("/public-data")
async def get_data():
    ...
```

已公开的 endpoint（`frontend` 项目调用，无需登录）：
- `GET /api/features/{code}` — 特征数据（含自动同步，见下方说明）
- `GET /api/stocks/{code}/minute` — 分时数据（含数据源回退）
- `GET /api/stocks/{code}/daily` — 日线数据
- `GET /api/stocks/{code}/quote-panel` — 行情面板（实时行情 + 每日指标，分析页使用）
- `GET /api/stocks/{code}/basic-info` — 股票完整基础信息（含 Tushare 扩展字段，分析页使用）
- `GET /api/cyq-chips/distribution?ts_code=xxx` — 筹码分布（含自动同步，分析页使用）

#### `GET /api/features/{code}` 自动同步机制（2026-04-01）

K 线图数据来自该接口，后端在返回前自动检测数据完整性并按需触发同步：

| 场景 | 判断条件 | 动作 |
|------|----------|------|
| 首次加载（无数据） | `df.empty` 且 `end_dt` 为空或 ≤ 30天前 | 全量同步 5 年 |
| 懒加载历史为空 | `df.empty` 且 `end_dt` 超过 30 天前 | 扩展同步（max(years_back, 10) 年）|
| 最新数据不完整 | 库中最新日期 < `trade_cal` 最新交易日 | 增量同步（仅补缺失区间） |

**短代码解析**：frontend 可能传入纯数字代码（如 `000001`），接口内部调用 `stock_quote_cache.resolve_ts_code(code)` 解析为完整 ts_code（如 `000001.SZ`）再查询 `stock_daily`（该表只存完整 ts_code）。

**同步实现**：所有三种同步均使用 `StockDailyService.sync_single_stock(code=ts_code, ...)` — 不再使用 `DailySyncService`。增量同步通过传入 `start_date`/`end_date` 日期范围实现，无需单独的 `sync_incremental` 方法。

**缓存失效**：每次同步后必须调用 `cache.delete_pattern(f"daily_data:*{ts_code}*")` 清除 Redis，否则 `DataAdapter` 返回的仍是旧数据（`sync_single_stock` 绕过了 `DataAdapter`，不自动失效缓存）。注意缓存键需使用完整 `ts_code`，而非原始 `code`。

#### EChartsStockChart 懒加载机制（2026-04-01）

K 线图支持向左滑动时自动加载更早历史数据（`frontend/src/components/EChartsStockChart.tsx`）：

- **触发条件**：`dataZoom.start < 20%`（视图左端在数据总量 20% 以内）
- **请求参数**：以当前最早日期的前一天为 `end_date`，每批 500 条
- **视图锁定**：记录锚点日期，新数据合并后重算 `dataZoom` 百分比，防止视图跳位
- **自动续载**：加载完成后若 `has_more=true` 且视图仍在左端，自动调度下一批（200ms 延迟），无需用户再次滑动
- **关键 Ref**：`allDataRef`/`isLoadingRef` 避免 `useCallback` 闭包读取到过期 state；`currentDataZoomRef` 传递锚点位置给自动续载逻辑

**问题：Tushare 分时数据报 "Invalid date format"**

`core/src/providers/base_provider.py` 的 `normalize_date()` 仅接受 `YYYYMMDD`（8位纯数字）格式。传入带时分秒的字符串（如 `"2026-03-29 09:30:00"`）去掉分隔符后变成 17 位，会直接抛出 `ValueError`。

```python
# ❌ 错误：带时间的字符串
start_date = datetime.now().strftime("%Y-%m-%d 09:30:00")  # → "20260329 09:30:00" → ValueError

# ✅ 正确：纯日期 YYYYMMDD
start_date = date_range["start"]  # 已经是 "20260329" 格式
end_date = datetime.now().strftime("%Y%m%d")
```

涉及文件：`backend/app/services/realtime_sync_service.py` 的 `sync_minute_data()`。

**问题：Celery 任务状态卡在 `pending`（`started_at` 为 NULL，状态不变 `running`）**
- **原因**：Celery 信号处理器（`task_prerun_handler` 等）使用了 `DatabaseManager` 单例，而 fork pool worker 继承了父进程已损坏的连接池，导致 UPDATE 静默失败
- **解决**：`celery_signals.py` 中的所有信号处理器必须使用 `_get_direct_conn()` 创建独立 psycopg2 直连，避免依赖单例连接池
- **手动修复卡住的记录**：`UPDATE celery_task_history SET status='failure', error='stuck' WHERE status='pending' AND created_at < NOW() - INTERVAL '1 hour'`

**问题：执行日线批量同步后后端大量接口返回 500，日志报 `connection pool exhausted`**
- **原因**：`sync_daily_full_history_task` / `sync_daily_recent_all_task` 在任务体内调用了 `DatabaseManager.reset_instance()`，该方法会调用 `closeall()` 关闭 psycopg2 连接池的**所有连接**（包括 FastAPI 主进程正在使用的）。关闭后 Repository 再取连接时连接池已耗尽。
- **解决**：**禁止在 Celery 任务体内调用 `DatabaseManager.reset_instance()`**。该方法仅用于测试环境。psycopg2 同步连接池在 Celery worker 中可直接复用，不需要重置；SQLAlchemy 异步引擎的重置由 `run_async_in_celery()` 负责（仅针对 async 任务）。
- **涉及文件**：`backend/app/tasks/sync_tasks.py`

**问题：性能较慢**
- [ ] 检查是否使用批量操作（而非循环单条插入）
- [ ] 检查查询是否添加了适当的索引
- [ ] 检查是否有不必要的 N+1 查询
- [ ] 考虑使用数据库查询日志分析慢查询