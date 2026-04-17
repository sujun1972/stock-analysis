# Admin 项目开发指南

> 本文档专属于 `/admin` 子项目（Next.js 管理后台）。
> 跨项目通用规范请参阅根目录 [CLAUDE.md](../CLAUDE.md)。
> 后端规范请参阅 [backend/CLAUDE.md](../backend/CLAUDE.md)。

## 目录

- [技术栈](#技术栈)
- [面包屑导航](#面包屑导航)
- [任务管理面板](#任务管理面板)
- [数据同步页面异步任务集成模式](#数据同步页面异步任务集成模式)
- [全量同步 + 清空数据按钮（BulkOpsButtons）](#全量同步--清空数据按钮bulkopsbuttons)
- [API 客户端模块化架构](#api-客户端模块化架构)
- [响应式设计规范](#响应式设计规范)
- [DataTable 列样式规范](#datatable-列样式规范)
- [前端页面模块化重构最佳实践](#前端页面模块化重构最佳实践)
- [同步配置页面（sync_configs 表）](#同步配置页面sync_configs-表)
- [定时任务页面架构](#定时任务页面架构)
- [新增数据同步功能前端开发流程](#新增数据同步功能前端开发流程)
- [Prompt 模板管理（策略类型扩展）](#prompt-模板管理策略类型扩展)
- [已移除的 Admin 功能](#已移除的-admin-功能)

---

## 技术栈

- **框架**：Next.js 14（App Router）
- **UI 组件**：shadcn/ui + Tailwind CSS
- **状态管理**：Zustand
- **HTTP 客户端**：axios（封装在 `lib/api/`）
- **图表**：Recharts（折线图）、ECharts（K线等复杂图表）
- **表格**：自定义 `DataTable` 组件
- **Markdown 渲染**：`react-markdown` + `remark-gfm`（`components/common/MarkdownRenderer.tsx`），用于 AI 分析结果展示

---

## 面包屑导航

### 组件位置

- `components/ui/breadcrumb.tsx` — 面包屑 UI 组件
- `hooks/useBreadcrumbs.ts` — 自动生成面包屑的 Hook
- `components/layouts/AdminLayout.tsx` — 在布局层集成面包屑

### 实现特点

- **全局显示**：面包屑在 AdminLayout 布局层自动显示，位于顶部 Header 下方
- **自动生成**：根据当前路由自动生成，支持动态路由参数（股票代码、策略ID等）
- **响应式**：长路径在移动端自动折叠为下拉菜单，保持首页和最后两项可见

### PageHeader 组件

专注于页面标题、描述和操作按钮，不包含面包屑功能。支持 `details` prop：

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

### 面包屑开发注意事项

1. **路由与菜单归属一致**：页面 URL 路径应与所属菜单一致，例如打板专题下的页面应放在 `/boardgame/` 路径下。
2. **`parentOverrides` 机制**：当页面 URL 首段与菜单归属不一致时，在 `useBreadcrumbs.ts` 的 `parentOverrides` 中覆盖父级。
3. **图标与菜单一致**：`routeIconMap` 中的图标必须与 `AdminLayout.tsx` 中对应菜单项图标完全一致。
4. **新增菜单项时**：同步在 `routeLabelMap` 和 `routeIconMap` 中添加路由 segment 映射。

### 父级导航页面

以下父级菜单页面以卡片形式展示子功能入口：

- `/settings` — 系统设置
- `/sync` — 数据同步
- `/logs` — 日志管理
- `/monitoring` — 系统监控
- `/boardgame` — 打板专题
- `/reference-data` — 参考数据
- `/moneyflow` — 资金流向
- `/margin` — 两融数据
- `/features` — 特色数据

---

## 任务管理面板

Admin 项目采用统一的任务管理面板，位于 Header 右侧。

### 架构特点

- **统一入口**：通过 Header 右侧的任务图标访问
- **全局轮询**：Header 组件统一处理（每 5 秒更新状态，每 30 秒同步历史）
- **即时更新**：打开面板或执行任务后立即触发轮询
- **状态管理**：Zustand store 统一管理任务状态

### 相关文件

| 文件 | 说明 |
|------|------|
| `components/TaskPanel.tsx` | 任务面板组件 |
| `components/TaskStatusIcon.tsx` | Header 中的任务图标 |
| `components/layout/Header.tsx` | 全局轮询入口 |
| `stores/task-store.ts` | 任务状态管理（含轮询触发器） |
| `hooks/useTaskPolling.ts` | 任务状态轮询 Hook |
| `hooks/useTaskSync.ts` | 任务历史同步 Hook |

### 手动触发轮询

```typescript
const { triggerPoll } = useTaskStore()

// 执行任务后立即触发轮询
await apiClient.executeTask(taskId)
triggerPoll()  // Header 图标即时更新
```

---

## 数据同步页面异步任务集成模式

**所有数据同步页面必须使用异步任务模式**，不使用同步阻塞模式。

### 标准实现

```typescript
const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
const activeCallbacksRef = useRef<Map<string, any>>(new Map())

// ✅ 从 task store 实时派生——不要用本地 useState(false)
const syncing = isTaskRunning('tasks.your_celery_task_name')

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

### 同步弹窗选日期模式

当同步需要用户指定日期时，同步按钮先打开 Dialog：

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
```

### ⚠️ 不得将查询筛选日期传入同步接口

```typescript
// ❌ 错误：把查询日期传给同步接口
const handleSync = async () => {
  const params: any = {}
  if (tradeDate) params.trade_date = toDateStr(tradeDate)  // ❌
  await yourApi.syncAsync(params)
}

// ✅ 正确：不传日期，让后端从 trading_calendar 自动取最新交易日
const handleSync = async () => {
  const params: any = {}
  if (tsCode) params.ts_code = tsCode  // 可选
  await yourApi.syncAsync(params)
}
```

### 已实现的异步同步页面

所有页面遵循以下标准实践：同步弹窗与查询日期解耦、`isTaskRunning` 派生 `syncing`、`DataTable mobileCard`、左文字右图标统计卡片、`toDateStr` 本地时间安全。

| 页面 | 路由 |
|------|------|
| 定时任务配置 | `/settings/scheduler` |
| 沪深港通资金流向 | `/moneyflow/hsgt` |
| 大盘资金流向 | `/moneyflow/mkt-dc` |
| 板块资金流向 | `/moneyflow/ind-dc` |
| 个股资金流向（Tushare） | `/moneyflow/stock` |
| 个股资金流向（DC） | `/moneyflow/stock-dc` |
| 融资融券交易汇总 | `/margin/summary` |
| 融资融券交易明细 | `/margin/detail` |
| 融资融券标的 | `/margin/secs` |
| 转融资交易汇总 | `/margin/slb-len` |
| 龙虎榜每日明细 | `/boardgame/top-list` |
| 龙虎榜机构明细 | `/boardgame/top-inst` |
| 涨跌停列表 | `/boardgame/limit-list` |
| 连板天梯 | `/boardgame/limit-step` |
| 最强板块统计 | `/boardgame/limit-cpt` |
| 卖方盈利预测 | `/features/report-rc` |
| 个股异常波动 | `/reference-data/stk-shock` |
| 个股严重异常波动 | `/reference-data/stk-high-shock` |
| 交易所重点提示证券 | `/reference-data/stk-alert` |
| 股权质押统计 | `/reference-data/pledge-stat` |
| 股票回购 | `/reference-data/repurchase` |
| 限售股解禁 | `/reference-data/share-float` |
| 股东人数 | `/reference-data/stk-holdernumber` |
| 大宗交易 | `/reference-data/block-trade` |
| 股东增减持 | `/reference-data/stk-holdertrade` |
| 利润表 | `/financial/income` |
| 资产负债表 | `/financial/balancesheet` |
| 现金流量表 | `/financial/cashflow` |
| 业绩预告 | `/financial/forecast` |
| 业绩快报 | `/financial/express` |
| 分红送股 | `/financial/dividend` |
| 财务指标 | `/financial/fina-indicator` |
| 财务审计意见 | `/financial/fina-audit` |
| 主营业务构成 | `/financial/fina-mainbz` |
| 财报披露计划 | `/financial/disclosure-date` |

---

## 全量同步 + 清空数据按钮（BulkOpsButtons）

### 组件与 Hook

- `components/common/BulkOpsButtons.tsx` — 按钮组 UI
- `hooks/useDataBulkOps.ts` — 业务逻辑 Hook

### 使用示例

```tsx
import { useDataBulkOps } from '@/hooks/useDataBulkOps'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'

const {
  handleFullSync, handleClear, fullSyncing, isClearing,
  isClearDialogOpen, setIsClearDialogOpen, cleanup, earliestHistoryDate,
} = useDataBulkOps({
  tableKey: 'daily_basic',
  syncFn: (params) => apiClient.post('/api/daily-basic/sync-async', null, { params }),
  taskName: 'tasks.sync_daily_basic',
  onSuccess: () => loadData(1),
})

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

### 设计要点

- Hook 从 `useConfigStore().dataSource.earliest_history_date` 读取全量同步起始日期
- `handleFullSync` 只传 `start_date`，**不传**页面筛选器当前日期
- 后端用 `CLEARABLE_TABLES` 白名单防止任意表注入，新增数据表时需同步更新 `data_ops.py`
- 若每次普通同步本身就是全量拉取（如 `stock_basic`），不加全量同步按钮

---

## API 客户端模块化架构

### 模块结构

```
lib/api/
├── base.ts           # 基础 API 类和 axios 实例
├── auth.ts           # 认证相关
├── users.ts          # 用户管理
├── stocks.ts         # 股票相关
├── moneyflow.ts      # 资金流向
├── margin.ts         # 融资融券
├── scheduler.ts      # 定时任务
├── celery-tasks.ts   # Celery 任务管理
├── config.ts         # 系统配置
├── sync.ts           # 数据同步
├── extended-data.ts  # 扩展数据
├── monitor.ts        # 系统监控
└── index.ts          # 统一导出
```

### 使用规范

```typescript
// ✅ 新功能开发：从模块导入
import { moneyflowApi, marginApi } from '@/lib/api'

// ✅ 旧代码：向后兼容，继续可用
import { apiClient } from '@/lib/api-client'
```

新功能必须创建独立的模块文件（如 `lib/api/your-api.ts`），继承 `BaseApiClient`，并在 `lib/api/index.ts` 中导出。

---

## 响应式设计规范

### 断点定义

- `sm` (640px): 手机横屏及平板竖屏
- `md` (768px): 平板横屏
- `lg` (1024px): 小屏幕桌面
- `xl` (1280px): 标准桌面

### 设计模式

1. **卡片布局**：`grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4`
2. **按钮组**：移动端用 `DropdownMenu`，桌面端横向排列
3. **统计卡片**：左文字右图标布局（标准）

### 关键注意事项

**日期字符串构建（时区安全）**：
```typescript
// ✅ 正确：使用本地时间，别名 toDateStr
const dateStr = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`

// ❌ 错误：UTC 转换在 UTC+8 时区会偏移 -1 天
const dateStr = date.toISOString().split('T')[0]
```

**ECharts 初始化时序问题**（"Can't get DOM width or height"）：

```tsx
const chartRef = useRef<HTMLDivElement>(null)
const chartInstance = useRef<echarts.ECharts | null>(null)
const [data, setData] = useState<Item[] | null>(null)

useEffect(() => { fetchData().then(setData) }, [key])

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

容器始终存在于 DOM，通过 `height: 0 / 420` 切换显隐（而非条件渲染）。

**HTML 嵌套规范**（避免水合错误）：
```tsx
// ❌ 错误
<p><div className="flex">...</div></p>
// ✅ 正确
<p className="flex">...</p>
```

**空值安全处理**：
```typescript
const formatAmount = (amount: number | null | undefined) => {
  if (amount === null || amount === undefined) return '0.00'
  return amount.toFixed(2)
}
```

**中文输入法（IME）处理**：
```typescript
const isComposing = useRef(false)
<Input
  onChange={(e) => setSearchQuery(e.target.value)}
  onCompositionStart={() => { isComposing.current = true }}
  onCompositionEnd={(e) => {
    isComposing.current = false
    triggerSearch((e.target as HTMLInputElement).value)  // 必须直接调用，不能依赖 useEffect
  }}
/>
```

**日期选择器**：优先使用 `@/components/ui/date-picker`，避免 HTML5 原生 `<input type="date">`。

**前端非股票不跳转规则**：
```typescript
const isStock = (tsCode: string) => {
  const code = tsCode.split('.')[0]
  return !code.startsWith('5') && !code.startsWith('1') && !code.startsWith('821')
}
```

---

## DataTable 列样式规范

```typescript
// ✅ 正确：使用 cellClassName
{ key: 'amount', header: '总成交额', width: 110, cellClassName: 'text-right whitespace-nowrap' }

// ❌ 错误：className 在 DataTable 中无效
{ key: 'amount', className: 'text-right' }
```

**固定宽度表格**：
```tsx
<DataTable
  tableClassName="table-fixed w-full"
  columns={[
    { key: 'name', width: 160, cellClassName: 'whitespace-nowrap' },
    { key: 'reason' }  // 无 width，自动占剩余空间
  ]}
/>
```

**前端 sort 状态异步更新陷阱**：
```typescript
onSort: (key, direction) => {
  const newKey = direction ? key : null
  setSortKey(newKey)       // 异步更新
  setSortDirection(direction)
  loadData(1, newKey, direction)  // 直接传新值，不依赖 state
}
```

---

## 前端页面模块化重构最佳实践

单个页面文件超过 **500 行**时，按以下结构拆分：

```
your-page/
├── page.tsx          # 主页面（编排组合，目标 200-300 行）
├── hooks/
│   ├── index.ts
│   ├── useXxxData.ts    # 数据加载
│   ├── useXxxConfig.ts  # 配置管理
│   └── useXxxActions.ts # 操作逻辑
└── components/
    ├── index.ts
    ├── ControlPanel.tsx
    └── XxxCard.tsx
```

---

## 同步配置页面（sync_configs 表）

同步配置页面（`/settings/sync-config`）基于 `sync_configs` 数据库表驱动。

### 关键文件

| 文件 | 说明 |
|------|------|
| `lib/api/sync-dashboard.ts` | 前端 API 客户端 |
| `app/(dashboard)/settings/sync-config/page.tsx` | 页面 |

### 数据源测试弹窗

每行操作列的 ▶ 按钮打开「数据源配置与测试」弹窗（需 `api_name` 非空），包含两个 Tab：

- **接口配置**：编辑接口名称、文档链接、描述、请求限量、参数约束（ts_code/trade_date/日期范围/特殊参数），保存按钮更新 `sync_configs`
- **接口测试**：显示远程接口 URL（`POST http://api.tushare.pro`），填写测试参数 + limit/offset，发送请求，响应以 JSON 文本显示在终端风格文本框中

后端端点：`POST /api/sync-dashboard/test-datasource`（管理员权限）

### CATEGORY_ORDER 排序

```typescript
const CATEGORY_ORDER = [
  '基础数据', '行情数据', '财务数据', '参考数据',
  '特色数据', '两融及转融通', '资金流向', '打板专题',
]
```

新增分类时同步更新此常量，保持与 `AdminLayout.tsx` 侧边菜单一致。

---

## 定时任务页面架构

定时任务配置页面（`/settings/scheduler`）采用数据库驱动的元数据管理。

### 任务分类排序

1. **基础数据** (100-199)
2. **行情数据** (200-299)
3. **资金流向** (300-399)
4. **特色数据** (400-499)
5. **两融及转融通** (500-599)
6. **打板专题** (550-599)
7. **市场情绪** (600-699)
8. **盘前分析** (700-799)
9. **财务数据** (800-899)
10. **报告通知** (900-999)
11. **系统维护** (1000+)

### TASK_CATEGORIES 常量

`app/(dashboard)/settings/scheduler/page.tsx` 顶部维护 `TASK_CATEGORIES` 常量，新增分类时同步更新。

### DataTable accessor

DataTable 组件使用 `accessor` 函数而非 `render` 来自定义列渲染。

---

## 新增数据同步功能前端开发流程

### 前端 API 客户端（`lib/api/your-api.ts`）

```typescript
import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export class YourApiClient extends BaseApiClient {
  async getData(params?: YourDataParams): Promise<ApiResponse<{
    items: YourData[]
    total: number
    trade_date?: string  // 后端回填的默认日期，用于初始化日期选择器
  }>> {
    return this.get('/api/your-endpoint', { params })
  }

  async syncAsync(params?: any): Promise<ApiResponse<any>> {
    return this.post('/api/your-endpoint/sync-async', {}, { params })
  }
}

export const yourApi = new YourApiClient()
```

在 `lib/api/index.ts` 中导出。

### 前端页面标准结构

```typescript
'use client'

import { useState, useEffect, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { useTaskStore } from '@/stores/task-store'

export default function YourPage() {
  // 从 task store 实时派生——不要用 useState(false)
  const syncing = isTaskRunning('tasks.your_celery_task_name')

  // ... 标准异步任务集成（见上方"数据同步页面异步任务集成模式"）

  return (
    <div className="space-y-6">
      <PageHeader
        title="页面标题"
        actions={
          // 同步按钮放在 PageHeader actions，不放在查询 Card 里
          <Button onClick={handleSync} disabled={syncing}>...</Button>
        }
      />
      {/* 统计卡片 */}
      {/* 查询筛选 Card */}
      {/* 数据表格 Card */}
    </div>
  )
}
```

### 菜单注册

在 `components/layouts/AdminLayout.tsx` 对应菜单组中添加菜单项，并同步更新 `useBreadcrumbs.ts` 的 `routeLabelMap` 和 `routeIconMap`。

---

## 已移除的 Admin 功能

以下功能已从系统中移除（2026-03-25），**不要重新添加**：

- **概念标签管理**（`/concepts`）— 相关表 `concept`、`stock_concept` 已删除
- **股票管理页面**（`/stocks`、`/stocks/[code]`）— 数据和 API 保留，仅移除前端页面
- **数据中心**（`/sync/initialize`、`/sync/extended`）— 数据同步 API 保留，仅移除前端页面
- **市场情绪功能**：大盘情绪指标、涨停板池、龙虎榜查询、情绪周期分析
  - 保留功能：AI 情绪分析、盘前预期管理

### AI 情绪分析数据源（2026-03-25 重构）

| 数据 | 旧表（已删除） | 新表（打板专题） |
|------|--------------|----------------|
| 涨跌停统计 | `limit_up_pool` | `limit_list_d` |
| 连板天梯 | `limit_up_pool.continuous_ladder` | `limit_step` |
| 龙虎榜 | `dragon_tiger_list` | `top_list` |
| 板块统计 | 无 | `limit_cpt_list` |

**FastAPI 路由注意事项**：`/preview-prompt` 路由必须注册在 `/{date}` 通配符路由**之前**，否则会被拦截。

---

## Prompt 模板管理（策略类型扩展）

Admin 的 `/settings/prompt-templates` 页面通过 `BUSINESS_TYPE_LABELS`（`admin/types/prompt-template.ts`）渲染业务类型下拉列表。**新增业务类型时必须同步更新该映射**，否则下拉列表显示 key 而非中文标签。

当前支持的 `business_type`：

| business_type | 说明 |
|---------------|------|
| `strategy_generation` | AI 策略生成（通用，兼容旧版） |
| `strategy_generation_entry` | 入场策略生成 |
| `strategy_generation_exit` | 离场策略生成 |
| `strategy_generation_stock_selection` | 选股策略生成 |
| `stock_data_collection` | 个股数据收集 |
| `hot_money_view` | 顶级游资观点 |
| `midline_industry_expert` | 中线产业趋势专家观点 |
| `longterm_value_watcher` | 长线价值守望者观点 |
| `cio_directive` | 首席投资官（CIO）指令 |
| `macro_risk_expert` | 天眼宏观风险专家 |

**数据库初始化**：
- 策略类型模板：运行 `backend/scripts/migrate_strategy_prompt_templates.py`
- 专家观点模板（游资/中线/长线/CIO）：运行 `backend/scripts/migrate_expert_view_templates.py`
- 宏观风险专家模板：运行 `backend/scripts/migrate_macro_risk_expert_template.py`

**后端查找逻辑**（`ai_service.py`）：`_STRATEGY_TYPE_BUSINESS_TYPE` 字典将 `strategy_type`（`entry`/`exit`/`stock_selection`）映射到 `business_type`，`AIStrategyService._load_db_prompt()` 据此加载对应模板；模板缺失时降级使用 `STRATEGY_TYPE_FRAMEWORKS` 硬编码片段。
