# Frontend 开发指南

Frontend 是面向普通用户的 Next.js 应用（与 Admin 管理后台分开部署）。

## 技术栈

- **框架**: Next.js (App Router)
- **状态管理**: Zustand（`stores/`）
- **API 调用**: 领域模块 `frontend/src/lib/api/`（stocks、strategies、backtest、sync、system），向后兼容 `frontend/src/lib/api-client.ts`
- **类型定义**: `frontend/src/types/`
- **图表工具**: `frontend/src/components/chart-utils.ts`（指标设置持久化、格式化函数）

### API 调用规范

新代码推荐按领域导入：
```typescript
import { getStockList } from '@/lib/api/stocks'
import { runAsyncBacktest } from '@/lib/api/backtest'
```

旧代码可继续使用 `apiClient` 单例（薄代理，零开销）：
```typescript
import { apiClient } from '@/lib/api-client'
```

**禁止直接 `import axios from 'axios'`**，统一使用 `@/lib/api/axios-instance` 中的共享实例（含 Token 自动刷新、请求队列）。

---

## 字体与排版约定

- **字体栈**：拉丁字符走 Inter（[layout.tsx](src/app/layout.tsx) 用 `next/font/google` 自托管 + 子集化），中文**故意不打包**字体，落到系统栈（macOS PingFang SC / Windows Microsoft YaHei / Linux Noto CJK SC）。Tailwind `font-sans` 已在 [tailwind.config.ts](tailwind.config.ts) 配置完整 fallback 链。
- **不要为中文打包 Noto Sans SC / 思源黑体等 webfont**：CJK 子集化后仍 1-3MB，会显著拖慢首屏；浏览器内置中文字体已能满足绝大多数场景。
- **OpenType 特性**：[globals.css](src/app/globals.css) 在 body 上启用 `cv11`（单层 a）+ `ss01`（曲线风格统一），勿随意改动。
- **数字列必须加 `tabular-nums`**：股票列表、评分、价格、涨跌幅、ROC/EY、CIO 日期等所有数字单元格必须用 `tabular-nums` 等宽数字，否则静默刷新时数字宽度变化会导致表格列抖动。新增数字列时同步加。

---

## 语义色与过渡时长 token

所有"情感色"（涨红、跌绿、关注黄、信息蓝）走 CSS 变量 + Tailwind utility，禁止在业务文件手写 `text-red-600 dark:text-red-400` 表达涨跌——后者在深色模式对比度不足 WCAG AA（4.5:1）。

| Utility | 含义 | 用途示例 |
|---------|------|----------|
| `text-positive` / `bg-positive-soft` | A 股涨红 | `pct_change > 0`、`break_up` 触发价、ROC ≥30% |
| `text-negative` / `bg-negative-soft` | A 股跌绿 | `pct_change < 0`、`break_down` 触发价、亏损 |
| `text-warning` / `bg-warning-soft` | 关注黄 | ROC 15~30%、安全边际 30~100%、PE 异常（亏损/>500） |
| `text-info` | 信息蓝 | 排序激活、次要提示；业务 primary 仍用 `text-primary` |
| `bg-score-low` / `bg-score-mid` / `bg-score-high` | AI 评分单色相紫罗兰 (270°) | 仅 ScoreBadge 用：4-6 浅紫 outline / 6-8 中紫实底 / ≥8 深紫实底 |
| `duration-fast` (120ms) / `duration-normal` (200ms) / `duration-slow` (320ms) | 过渡时长分档 | `transition-colors duration-fast` 等 |

token 定义在 [globals.css](src/app/globals.css) 的 `:root` / `.dark` 里，深色模式已单独升阶至 red-300 / green-400 / yellow-300 级亮度以保证对比度。K 线红涨绿跌的 `#ef4444` / `#22c55e` 是 ECharts 专用常量不走此体系（见 useEChartsTheme）。

**评分色阶为何是紫罗兰单色相**（`--score-low/-mid/-high` 全部 270°）：① 主色 `primary` 是 221° 蓝（链接/CTA），评分用蓝会与 CTA 撞色；② 灰背景在多个状态间堆叠会让表格"脏"；③ 紫罗兰 270° 与红 (0°)/绿 (142°)/蓝 (221°) 三色色相距均 ≥49°，不与任何业务语义冲突。亮度递进 88%→58%→38% 形成"高分扎眼、低分隐形"的金字塔视觉权重。禁止把 score-* 与 positive/negative 混用；非情感语境的装饰色（如 Tab badge 蓝）保留 Tailwind 原色阶。

**迁移规则**：新加的涨跌/状态色一律用语义 token；改到老文件时顺手替换（低风险、一致）。非情感语境的装饰色（如 Tab badge 的蓝色徽章）保留原 Tailwind 色阶即可。

---

## 共享 UI 工具（shared/）

[src/components/shared/](src/components/shared/) 集中放跨页面复用的轻量组件。新增前先看有没有能复用的；需要再扩展时加到 [index.ts](src/components/shared/index.ts) 统一导出。

| 组件 | 用途 |
|------|------|
| `ScoreBadge` | AI 评分徽章（`table` / `card` variant + tooltip 色盲辅助） |
| `SortIndicator` | 表头排序方向箭头（lucide ChevronUp/Down 封装；禁止再手写内联 SVG） |
| `ErrorDetailCollapsible` | 可折叠结构化错误卡片 + 一键复制（取代 `JSON.stringify(errors)` 原样展示） |
| `Skeleton` + `StockTableSkeleton` / `StockCardSkeleton` / `AnalysisHistorySkeleton` | 首次加载骨架屏预设 |
| `MetricCard` / `LoadingSpinner` / `ConfirmDialog` / `SortableTableHead` | 其他通用原子 |

**CSS 工具类**（[globals.css](src/app/globals.css)）：
- `.scrollbar-thin` — 6px 细滚动条，窄屏 Tab / 长列表必用
- `.scroll-shadow-x` — 横向滚动容器两侧渐变遮罩，提示"可左右滑动"。用法：外层包 `<div class="scroll-shadow-x">`，内层 `<div class="overflow-x-auto">`；父容器底色非 `--background` 时用 inline `style={{ '--scroll-shadow-bg': 'hsl(var(--card))' }}` 覆盖
- `.focus-ring` / `.focus-ring-red` — 键盘焦点环（见 a11y 章节）

**图表容器宽度约束**：所有 ECharts 包装器外层必须 `min-w-0 max-w-full overflow-hidden`，图表 `<div ref={chartRef}>` 本身加 `min-w-0 max-w-full`——防止 flex 布局下 ECharts 自测宽度把父容器撑溢出屏幕（移动端常见）。

---

## 根布局分叉：全站 Shell vs 认证页 Shell

Root `app/layout.tsx` **不**直接渲染顶栏/导航/页脚；而是套一层 [AppShell](src/components/AppShell.tsx)（client component）根据 `usePathname()` 分叉：

- 匹配 `AUTH_ROUTE_PREFIXES`（`/login` `/register` `/forgot-password` `/reset-password`，含子路径）→ 仅渲染 `{children}` + 全局 `<Toaster />`，认证页自带沉浸式布局（[AuthLayout](src/components/auth/AuthLayout.tsx)：桌面左右分屏品牌区+表单区，lg 断点切换）
- 其他路由 → 渲染完整 shell：蓝色 Header（含 `StockSearch` / `ThemeToggle` / `MobileNav`）+ `DesktopNav` + `<main>` + Footer

**新增认证类页面（注册邀请码、账户验证等）**：
1. 加到 `AppShell.tsx` 的 `AUTH_ROUTE_PREFIXES` 白名单
2. 页面组件用 `<AuthLayout title=".." subtitle=".." footer={...}>` 包裹 —— 不要自己写全屏背景/logo/品牌区，那些逻辑集中在 AuthLayout 里
3. 不要在认证页再套 `<Card>`——AuthLayout 右侧表单区已有 `max-w-md` 容器和标题槽，表单直接丢到 `children` 即可；需要强视觉分组时（如成功态提示）才用 `rounded-xl border bg-card` 卡片

**禁止**为认证页新增"把根 Shell 隐藏"的路由组（`(auth)/layout.tsx`）—— Next.js route group 的嵌套 layout 依然会继承根 layout，没有逃逸通道；只能靠根 layout 自己按 pathname 分叉。

---

## Toast 通知约定

全项目统一使用 **sonner** 呈现 toast；`<Toaster position="top-right" richColors closeButton theme="system" />` 挂在 [layout.tsx](src/app/layout.tsx) 的 `ThemeProvider` 内，自动跟随深浅主题。

**两种调用形态**（都落到同一个 sonner 实例，可自由混用）：

```tsx
// 新代码推荐：直接用 sonner 的语义 API
import { toast } from 'sonner'
toast.success('添加成功')
toast.error('删除失败', { description: err.message })
toast.loading('生成中...', { id: taskId })  // 再用 toast.success(..., { id: taskId }) 原位替换

// 历史调用点（148+ 处）：shadcn 风格 { title, description, variant }
import { useToast } from '@/hooks/use-toast'
const { toast } = useToast()
toast({ title: '已保存', description: '参数已持久化' })
toast({ title: '失败', description: err.message, variant: 'destructive' })
```

[use-toast.ts](src/hooks/use-toast.ts) 是 **sonner 的薄包装层**（非 shadcn reducer）——`variant: "destructive"` → `sonner.error`，`variant: "success"` → `sonner.success`（后者是历史遗留值，保留兼容）；`title + description` 都有时 title 做主文本、description 做副标题。

**禁止**手写 `fixed top-4 right-4 bg-green-600` / `bg-red-600` 之类硬编码 toast JSX，也不要用 `window.alert` 做成功/失败提示。破坏性操作的二次确认（删除列表等）可继续用原生 `window.confirm`。

---

## 无障碍（a11y）约定

- **键盘焦点环**：所有手写 `<button>` / `<a>` 必须带焦点环。用 [globals.css](src/app/globals.css) 预设的 `.focus-ring`（蓝环，默认）或 `.focus-ring-red`（删除类操作用红环），不要再手写 `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-*-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-900` 这串长类名。shadcn `Button` / `TabsTrigger` 等基础组件已内置焦点环，无需再叠加。
- **统一用 `focus-visible` 而非 `focus`**：键盘导航时才显示环，鼠标点击不显示（避免视觉噪音）。
- **`aria-label` 动态化**：列表中重复按钮（排序、复选框、操作菜单）必须带上"本条记录的标识"让屏幕阅读器能区分，如 `选中 ${stock.name}（${stock.code}）`、`${stock.name} 操作菜单`。排序按钮按当前状态动态生成，如 `按涨跌幅排序，当前降序，优先级第 1`。
- **`prefers-reduced-motion`**：[globals.css](src/app/globals.css) 全局把 `animation-duration` / `transition-duration` 降到 `0.01ms !important`——**不是 0**，因为 Radix 等库依赖 `animationend` / `transitionend` 事件驱动 `data-state=open/closed` 切换。写新动画时直接用 `animate-*` / `transition-*` 即可，无需自行判断系统偏好。
- **手写 `<button>` 都要写 `type="button"`**：避免在 `<form>` 里意外触发 submit。
- **嵌套 interactive 元素是 a11y 反模式**：不要在 `<button>` 里再放 `<button>` 或 `role="button"` 的 `<span>`（ErrorDetailCollapsible 早期踩过坑——Tab 键两次触发、屏幕阅读器重复朗读）。需要同层两个交互时用平级 `<div class="flex">` + 两个 `<button>`。
- **sonner Toaster 默认已挂 `aria-live="polite"`**，无需额外配置；但 toast 文案应是完整句子而非碎片（便于屏幕阅读器朗读）。
- **全局快捷键 ⌘K / Ctrl+K** 由 [stock-search.tsx](src/components/stock-search.tsx) 监听 `document.keydown` 聚焦搜索框（Linear/Notion/GitHub 惯例）；placeholder 根据 `navigator.platform` 自动显示对应按键提示。新增全局快捷键时遵循同一模式：挂 `document` 而非特定 input，检测 `document.activeElement === targetEl` 避免自打断。

---

用户可在 `/stocks` 页面管理自选股列表，`/analysis` 页面单股加入自选。**双轨架构**：
- **已登录**：多列表（最多 20 个），数据存后端 `user_stock_lists` / `user_stock_list_items`
- **未登录**：单一隐式列表"自选股"（最多 500 只），数据存 localStorage（`useLocalWatchlistStore`，key `local-watchlist:v1`）
- **登录瞬间自动合并**：`useLoginWatchlistSync` hook 检测 `isAuthenticated` 由 false→true 转变（`prevAuthRef` 锁基线 + `mergedRef` 防重入），把本地代码合并到后端"自选股"列表（缺则创建），清空 localStorage；失败回滚标志位允许重试。两个页面 `/stocks` 和 `/analysis` 都挂这个 hook，新增需要"自选股"的页面也照挂

`/stocks` 页用 `?list=local`（字面量）标记本地视图，与 `?list=<number>`（后端列表 ID）共享 URL state；`activeListId` 是联合类型 `number | 'local' | null`，在 fetchStocks 中 `isLocalActive=true` 走 `ts_codes=` 直查路径绕过分页。`AddToListDialog` 内部按 `isAuthenticated` 双分支：登录态写后端 + 显示 added/skipped 摘要，未登录态写 localStorage（带上限提示）。

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

- Zustand Store：
  - `frontend/src/stores/stock-list-store.ts` — 后端列表元数据（无持久化，登录态拉取）
  - `frontend/src/stores/local-watchlist-store.ts` — 未登录本地自选股（localStorage 持久化）
- 共享 hook：`frontend/src/hooks/useLoginWatchlistSync.ts` — 登录瞬间合并；调用方传 `onResult` 回调自渲 toast
- 主页面：`frontend/src/app/stocks/page.tsx`
- 提取组件：`frontend/src/app/stocks/components/`（`AddToListDialog`、`RenameListDialog`、`StockTableRow`）
- API 方法：`frontend/src/lib/api/stocks.ts`（`getUserStockLists`, `createStockList`, `renameStockList`, `deleteStockList`, `getStockListItems`, `addStocksToList`, `removeStocksFromList`）
- 类型定义：`frontend/src/types/stock.ts`（`StockList`, `StockListItem`）

---

## 股票代码规范

### ts_code 转换（`toTsCode()`）

`stocks/page.tsx` 中的 `toTsCode()` 将纯数字代码转换为带交易所后缀的格式：

| 代码前缀 | 交易所 | 示例 |
|---------|--------|------|
| `6xxxxx` | 上交所（`.SH`） | `600000.SH` |
| `4xxxxx` / `8xxxxx` | 北交所（`.BJ`） | `430047.BJ` |
| 其他 | 深交所（`.SZ`） | `000001.SZ` |

### 股票列表请求规范

**所有股票列表请求必须传 `list_status: 'L'`，过滤退市股票。**

`stock_basic` 表同步时保留所有状态的股票（L/D/P），backend API 默认不过滤，需由调用方显式指定。

涉及文件：
- `frontend/src/components/stock-search.tsx` — 搜索框
- `frontend/src/hooks/useStockFilter.ts` — 股票筛选 hook
- `frontend/src/app/stocks/page.tsx` — 股票列表页
- `frontend/src/lib/api-client.ts` 中的 `getStock()` — 单股精确查询

---

## `stock_realtime` 表 JOIN 注意

`stock_realtime` 主键是 `code`（纯数字，如 `000001`），**不是** `ts_code`。需要关联行情数据时，必须通过 `stock_basic` 桥接：

```sql
LEFT JOIN stock_basic sb ON sb.ts_code = your_table.ts_code
LEFT JOIN stock_realtime sr ON sr.code = sb.code   -- ✅ 正确
-- LEFT JOIN stock_realtime sr ON sr.ts_code = ... -- ❌ 该列不存在
```

**`pre_close` 会为 0**：`stock_realtime.pre_close` 在行情增量回补延迟时常常是 `0.000`，直接显示会得到空值。展示"昨收"的前端组件必须做兜底 —— 用 `latest_price - change_amount` 推算（参考 [analysis/page.tsx](src/app/analysis/page.tsx) 的 `resolvePreClose`）。修数据源时也别急着删这个 fallback，回补时效性不可控。

---

## API 响应格式

Backend 统一使用 `ApiResponse` 格式：

```typescript
// 检查成功
if (response?.code === 200) {
  const data = response.data
}

// 分页数据
const { items, total, page, page_size } = response.data

// ❌ 错误写法
if (response.success) { ... }       // 无 success 字段
const items = response.data.data    // 无双重嵌套
const total = response.meta.total   // meta 在 data 下，不在顶层
```

**`apiClient.get<T>()` / `apiGet<T>()` 的 T 是 envelope 内层**——`apiGet` 返回类型已经是 `ApiResponse<T> = { code, data: T, ... }`，调用时只传 `T = { items: ... }`，**不要再嵌一层 `{ code, data: ... }`**：

```typescript
// ✅ 正确
apiClient.get<{ items: MoneyflowItem[] }>(url).then(res => res.data?.items)

// ❌ 错误：T 又包一层 envelope，res.data 类型变成 { items },
//    res.data.items 推断成 undefined（编译错误 TS2339）
apiClient.get<{ code: number; data: { items: MoneyflowItem[] } }>(url)
```

**数字格式化**（永远不要直接用 `.toFixed()`）：

```typescript
const safeFormatNumber = (value: any, decimals: number = 2): string => {
  if (value === null || value === undefined || value === '') return '-'
  const num = typeof value === 'number' ? value : parseFloat(value)
  return isNaN(num) ? '-' : num.toFixed(decimals)
}
```

---

## ECharts K 线图（`EChartsStockChart`）

**懒加载机制**（向左滑动自动加载更早历史）：
- 触发条件：`dataZoom.start < 20%`
- 请求参数：以当前最早日期前一天为 `end_date`，每批 500 条
- 自动续载：`has_more=true` 时延 200ms 继续加载
- 关键 Ref：`allDataRef`/`isLoadingRef` 避免闭包读取过期 state

**K 线图数据来源（`GET /api/features/{code}`）**：
- 后端在返回前自动检测数据完整性并按需触发同步
- 短代码自动补全：纯数字 `000001` → `000001.SZ`
- 同步后清除 Redis 缓存：`cache.delete_pattern(f"daily_data:*{ts_code}*")`

**主图 y 轴 / 筹码图对齐**（关键约束）：
- 主图 y 轴永远 `min/max` 锁定到 dataZoom 视图内 `[low*0.97, high*1.03]`，不依赖 ECharts 的 `scale` 自动算法（避免视图内出现大片空白 + 筹码图无法垂直对齐）
- dataZoom 缩放事件中必须同步更新主图 yAxis 的 min/max（否则缩放后 y 范围与 K 线脱节）
- 筹码图 yAxis 用 `category` 类型，但不直接用真实档位价格做 data —— 而是按主图 [loBound, hiBound] 等距生成 N 档骨架（N=`MAIN_CHART_HEIGHT/5`，每档 ≥5px），把真实数据档累加到最近骨架档。这样筹码 category 范围 = 主图 value 范围，同价格在两图 y 像素位置完全对齐

**筹码分布嵌入主图右侧**（同花顺/东财/通达信标准布局）：
- 主图 grid `right: '26%'`（hasChips 时）/ `'8%'`（不带），副图 grid right 必须与主图同步，否则跨面板垂直十字线 x 错位
- 筹码 grid `left: '75%', right: '6%'`，与主图同 `top` 同 `height`
- 筹码 xAxis 是独立 `value` 类型（占比%），不能挂到 `axisPointer.link`/`tooltip.link` 的 xAxisIndex `'all'`，必须显式列出常规面板索引
- 筹码 series 用一维 `value: percent`（与 category yAxis 配对）；染色按"价格 < refPrice×0.99=绿（盈利）/> ×1.01=红（亏损）/±1%=黄（接近现价）"

**hover 联动按日期切换筹码图**：
- 监听 `chart.on('updateAxisPointer')`，从 `evt.axesInfo` 找 `axisDim==='x'` 的 value 解出 dateKey
- 用三态判断：`bucket && bucket.length > 0`（有数据切换）/ `bucket && bucket.length === 0` 或 `dateKey ∈ fetchedRanges`（已确认无数据，badge 显示"无数据"，清空筹码图但不发请求）/ 都不是（badge 显示"加载中"+ 触发 `onChipsDateMiss`）
- 父组件按需拉取的窗口策略：以 date 为中心 ±45 天，防抖 300ms，区间覆盖检查避免重复请求；拉取完成后若 date 仍不在新数据中，**显式 `setChipsHistory.set(date, [])`** 写入空数组哨兵 → 子组件下次再 hover 同一天直接走"无数据"分支
- `fetchedChipsRanges` 必须是 React state（不是 ref）通过 prop 传给子组件，否则子组件感知不到"已确认无数据"
- 数据到达后子组件 effect 重跑时检查 `hoverDateRef.current`（鼠标停留位置），若新数据命中则自动 `refreshChipsPanel`，避免"鼠标没动 → 图不更新"死局

**indicator 单选 + 设置弹窗**：
- MACD/KDJ/RSI 在底部 Tab 单选切换（`enforceSingleIndicator()` 强制三者互斥），设置弹窗只放成交量 / BOLL / 筹码分布开关
- `localStorage` 用 `{ ...DEFAULT_INDICATORS, ...JSON.parse(saved) }` 兜底新增字段（如 `chips`），保证旧用户数据兼容
- **`switchIndicator` 不要在 `setState(updater)` 的 updater 函数里同步调父组件回调**——updater 在 React render/commit 阶段执行，同步触发父 setState 会报 "Cannot update a component (StockPriceCard) while rendering a different component (EChartsStockChart)"。已有的 `switchIndicator` 用 `queueMicrotask` 把 `onIndicatorsChange` 派发推到 commit 之后，新增类似的"子状态变更需要回流父组件"模式时照抄

**面板内嵌图例浮层（取代 ECharts 内置 legend）**（同花顺/东财/富途看盘软件惯例）：
- 主图 / 成交量 / MACD / KDJ / RSI 每个面板左上角驻留一个 `graphic` group（id 形如 `legend-main` / `legend-volume` / `legend-indicator`），由 `rect` 半透明背板 + 多个独立 `text` 元素组合渲染。**不用 ECharts 富文本 `rich`**——某些版本下段间距/字色丢失。`segStyles` 表 + `parseRichText('{tag|text}')` 解析自定义标签
- 数值随 `chart.on('updateAxisPointer')` 实时刷新：从 `evt.axesInfo` 解出 `hoverIdx`（category 轴是日期字符串 → `dates.indexOf` 反查），变化时 `chart.setOption({ graphic: { elements: buildLegendGraphics(idx) } })`。鼠标离开图表 hoverIdx 回落到最新一根
- ECharts `legend` 数组保留为空 `[]`（不能删字段否则切换 BOLL 显隐时会残留旧图例），主图 `top` 直接接 `TOP_PADDING`，无需为 legend 预留高度
- 切换 indicator Tab / 缩放等会触发 `setOption` 重建 graphic 时，`replaceMerge` 数组**必须包含 `'graphic'`**（已在主 `setOption` 三个分支都加上），否则旧面板的浮层会残留
- 段宽度估算用 ASCII 0.6em / CJK 1.0em 近似（避免引入 canvas measureText）；浅色背景 `rgba(255,255,255,0.85)`、深色 `rgba(17,24,39,0.85)`，提供足够对比度让文字可读但不遮挡 K 线

**Y 轴刻度对齐 / 副图边界刻度**（避免长尾浮点 + 相邻面板边界刻度重叠）：
- 主图 `[loBound, hiBound]` 计算时按 `range` 量级 floor/ceil 到 nice step（≥100 用 2 元、≥10 用 1 元、≥1 用 0.05 元），把 `51.0899` 对齐成 `51`；筹码图也按同一 step 选择目标显示价（`labelInterval` 函数过滤），保持两图刻度同步
- 主图所有 `axisLabel.formatter` 强制 `Number(value).toFixed(2)` 避免默认浮点尾数；副图（成交量除外，走 `formatVolume`）也统一 2 位小数
- 副图 `axisLabel` 必须 `showMinLabel: false, showMaxLabel: false` 隐藏顶/底边界刻度——否则成交量底部 `500.00万` 会与 KDJ 顶部 `100.00` 重叠（PANEL_GAP=8px 留缝不够），主图 `BOTTOM_PADDING=28` 给 X 轴日期标签预留空间
- KDJ/RSI 固定 `min: 0 / max: 100` + `interval: 25` 强制刻度 `0/25/50/75/100`。**用 `interval` 不能用 `splitNumber`**——后者是建议值，会被 ECharts nice scale 重写

**装饰参考线**：
- 主图现价水平虚线（贯穿绘图区，让用户瞬间定位当前价位）：`markLine` 用 `[起点, 终点]` 两点段（`coord: [dates[0], close]` → `coord: [dates[-1], close]`），单 yAxis line 会被 ECharts 截断到数据范围而非 x 轴整段
- MACD 0 轴参考线：`markLine: { data: [{ yAxis: 0 }] }`，DIF/DEA 上穿/下穿 0 轴是中长期多空分水岭
- dataZoom 缩放后 hover 切换日期时，现价线 markLine 必须按相同 `[起点, 终点]` 模式重建（在 `dataZoom` 事件回调里），否则缩放区间外现价线会消失

**tooltip 仅回测模式启用**：
- 浮层已显示 OHLC + 涨跌幅 + MA + BOLL + 成交量 + MACD/KDJ/RSI 当前值，再弹 tooltip 浮窗会重复 + 遮挡视图。`tooltip.show` 仅在 `hasEquityData`（回测）时为 true，专门显示权益曲线总资产/持仓/现金
- **但 `trigger: 'axis'` 必须保留**——`updateAxisPointer` 事件依赖它触发，否则浮层无法跟随 hover 刷新。`axisPointer.label.show: false` 隐藏 X 轴日期 pill，避免与浮层日期重复

**快速时间窗（1M/3M/6M/1Y/All）**：底部工具栏右侧，按钮 onClick 用 `chart.dispatchAction({ type: 'dataZoom', start, end })` + 同步 `currentDataZoomRef`。`All` 视图触发 `requestAnimationFrame(() => loadMoreData())` 续载更早历史。交易日折算用 22/66/132/252（约月/季/半年/年）

**主题联动（`useEChartsTheme`）**：所有 ECharts 实例组件（`EChartsStockChart` / `MinuteChart` / `BacktestKLineChart` / `EquityCurveChart` / `ai-lab/*`）统一使用 [useEChartsTheme](src/hooks/useEChartsTheme.ts) 跟随 `next-themes` 的深浅主题。约定：

1. 从 hook 取 `{ theme, echartsTheme, palette }`。`theme` 是稳定字符串 `'light' | 'dark'`；`palette` 是单例 frozen 对象（不会因父组件重渲染触发引用变化）。
2. 用 **独立 useEffect + `[theme]` 依赖**先 `dispose()` 旧 instance 并置 `null`，下一轮渲染时主 effect 会以新主题重新 `echarts.init(el, echartsTheme)`——ECharts 不支持热切主题，只能重建。
3. 主 effect 的 deps 要加 `theme`（触发重建）和 `palette`（如果有消费）、`echartsTheme`；禁止自己临时 `getChartPalette(theme)` 拿 palette，那样会每次渲染返回新对象从而污染 deps。
4. `palette` 只覆盖业务组件必须手动引用的颜色：`background` / `tooltipBg` / `tooltipBorder` / `tooltipText` / `axisPointerLine` / `divider` / `loadingMask` / `loadingText`。axis / splitLine 等由 ECharts 内建 `'dark'` 主题自动处理。
5. K 线红涨/绿跌（`#ef4444` / `#22c55e`）是 A 股业务约定，不走 palette，两种主题下保持一致。

新增 ECharts 组件时照抄任意一个已迁移文件的模式即可；**禁止直接 `echarts.init(el)` 不传主题**，否则深色模式会白底。

---

## `/stocks` 页面筛选架构

### 响应式视图（桌面表格 / 移动卡片）

`/stocks` 同时维护两套视图，共用同一份 `displayedStocks` / `selectedCodes` / `sortKeys` / 静默刷新 / 批量分析轮询状态：

- **桌面（≥md）**：`hidden md:block` 渲染 `<StockTableRow>` 表格（15+ 列）+ 顶部 Card 内联筛选器
- **移动（<md）**：`md:hidden` 渲染 `<StockCard>` 卡片列表 + 顶部"筛选 (N)" 按钮触发 `<Sheet side="bottom">` 抽屉（Radix Dialog）
- **浮动操作栏**：桌面居中胶囊（`md:bottom-6 md:left-1/2`）、移动全宽吸底（`bottom-0 left-0 right-0`）+ `env(safe-area-inset-bottom)` 避开 iOS home indicator；≤sm 按钮仅显示图标，≥sm 显示图标+文字

**筛选器 JSX 复用**：`filtersGrid` 是组件内一个 JSX 变量，同时被桌面 `<Card>` 和移动 `<Sheet>` 引用——新增筛选字段只写一处即可两端生效。`activeFilterCount` 聚合 market / industry / concept / strategy / list 五个源，驱动移动端按钮徽章。

新增响应式页面时遵循同一约定：**不引入新响应式库**，只用 Tailwind `hidden md:block` / `md:hidden`；抽屉一律使用项目已有的 shadcn `<Sheet>`（基于 Radix Dialog）；禁止为"桌面/移动"分别维护两份业务状态。

### 弹窗响应式（Dialog → 移动端全屏 Sheet）

需要承载长内容的 Radix `<DialogContent>`，在 <sm（手机）覆盖为从底部滑入的全屏页，≥sm 保持居中弹窗。不引入新组件，全部靠 Tailwind `max-sm:` 变体叠加覆盖 `DialogContent` 基础类：

- 定位：`max-sm:inset-0 max-sm:left-0 max-sm:top-0 max-sm:translate-x-0 max-sm:translate-y-0`（抵消基础类的 `left-[50%] top-[50%] translate-*-[50%]`）
- 尺寸：`max-sm:h-[100dvh] max-sm:max-h-[100dvh] max-sm:w-screen max-sm:max-w-none`（`100dvh` 避开 iOS 地址栏动态高度）
- 外观：`max-sm:rounded-none max-sm:border-0`
- 动画：`max-sm:data-[state=open]:slide-in-from-bottom max-sm:data-[state=closed]:slide-out-to-bottom`（tailwindcss-animate 已提供）
- 内边距：根 `p-0 gap-0`，Header/Footer/内容区各自控制 `px-4`，便于 Footer `max-sm:fixed bottom-0` 吸底时贴齐视口边

吸底 Footer 必须带 `max-sm:pb-[calc(env(safe-area-inset-bottom)+0.75rem)]` 避开 iOS home indicator；滚动内容区给 `pb-24` 为吸底 Footer 预留空间。

### 细滚动条工具类（`.scrollbar-thin`）

[globals.css](src/app/globals.css) 定义的全局工具类，供窄屏横向滚动 Tab、弹窗内长列表使用。覆盖 Firefox (`scrollbar-width: thin`) + WebKit (`::-webkit-scrollbar` 6px)，自带深色模式配色。新增"内容可能溢出的容器"时直接 `className="overflow-x-auto scrollbar-thin"` 即可，不要再手写滚动条样式。

### 卡片列表页的移动端响应式约定

`/my-strategies` / `/strategies` / `/my-backtests` / `/ai-lab` 等"标题栏 + 筛选 + 卡片/表格列表 + 分页"型页面的常见溢出点和修复模式，新页面按此照抄即可：

1. **页面标题栏**（`<h1> + 副标题 + 主操作按钮`）：`flex-col sm:flex-row sm:items-center sm:justify-between gap-4`。h1 字号 `text-2xl sm:text-3xl`，副标题 `text-sm sm:text-base`。主操作按钮手机端 `w-full` 独占一行，桌面 `sm:w-auto sm:shrink-0` 回到右上。
2. **多列 Tab / 分段控件**（如 `grid-cols-5` 状态 Tab）：超过 3 列时在手机会挤烂。解决方式二选一——**(a)** 包 `overflow-x-auto scrollbar-thin -mx-4 px-4 sm:mx-0 sm:px-0`，`TabsList` 改 `inline-flex w-max sm:grid sm:w-full sm:grid-cols-N`，每个 `TabsTrigger` 加 `whitespace-nowrap`；**(b)** 列数 ≤3 时每个 trigger 加 `min-w-0` + `<span className="truncate">` 包文字、图标和 Badge 加 `shrink-0`。
3. **卡片 Footer 按钮组**（`StrategyCard` 等）：`flex flex-wrap gap-2`，用 `order-1` / `sm:order-2` 在手机端把视觉优先级最高的按钮（如"回测"）提到第一行整行 `w-full`、次要按钮组（代码 + 克隆/编辑/删除）用 `order-2 sm:order-1` 放第二行——桌面 `sm:order-*` 再交换回来恢复"代码 / 回测 / 图标" 原顺序。不要用双份 DOM + `hidden md:block` 实现同一组按钮的顺序差异。
4. **全宽列表卡片**（`StrategyListCard`、`BacktestHistoryContent` 单条 Card 等，含图标 + 信息区 + 操作区）：断点选 **`lg`** 而非 `sm`，因为平板也塞不下一排 5 个按钮。外层 `flex flex-col lg:flex-row`，主区（图标 + 信息）`flex-1 min-w-0`，操作区在手机端加 `border-t -mx-4 px-4 lg:border-t-0 lg:mx-0 lg:px-0` 做视觉分隔。
5. **超宽表格**（≥12 列，如 AI 实验舱模型仓库）：外包 `overflow-x-auto scrollbar-thin`，`<Table>` 加 `min-w-[1200px]` 强制保留桌面列宽——手机端横向滑动查看完整数据，不牺牲任何列。桌面用户无感知。
6. **分页栏**：`flex-col sm:flex-row sm:items-center sm:justify-between gap-3`——手机端"显示 X-Y 条"独占一行，按钮组 `justify-end` 换到下方靠右。
7. **Badge / 标签行**：长用户名 / 类别 / tag 必须加 `max-w-[140px~180px] truncate` + `title={...}` 悬停完整，否则英文长串或 AI 生成长标签会撑破父容器。Badge 里带图标的用 `<Icon className="shrink-0" /> <span className="truncate">...</span>` 组合。
8. **数字列加 `tabular-nums`**：统计徽章、分页计数、评分、日期等所有数字必须用等宽数字（项目全局规范，见"字体与排版约定"）。

禁止的反模式：
- 手机端用固定 `w-[150px]` / `w-[180px]` 的 Select / Input 宽度（断点下退化成 `w-full`）。
- 卡片标题行用 `flex items-center gap-2` 但不加 `flex-wrap`——长标题会挤没验证状态 Badge。
- Flex 子项不加 `min-w-0`——`min-width: auto` 的默认值会让子项拒绝收缩，导致父容器溢出而不是内部 `truncate` 生效。
- 手机端保留桌面的 `justify-between` 双列布局——应先 `flex-col`，再在 `sm:` / `lg:` 断点恢复横排。

### 加载状态三档约定（骨架屏 / 区域 spinner / 按钮 spinner）

大列表类页面的 loading 按"首次 vs 二次"分档，其他场景按尺寸分档，避免首屏空白闪烁和排序翻页时的 CLS：

1. **大列表首次加载**：用 [Skeleton.tsx](src/components/shared/Skeleton.tsx) 的预设骨架屏（`StockTableSkeleton` / `StockCardSkeleton` / `AnalysisHistorySkeleton`），结构与真实行/卡片的列宽对齐。页面维护 `isFirstLoad` state，在 `finally` 里 `setIsFirstLoad(false)`（幂等、React 自动 bail-out，不需再套 ref 去重）。
2. **大列表二次 loading**（排序 / 翻页 / 筛选变动）：退化为 `<Loader2 className="h-4 w-4 animate-spin" />` 小图标 + "加载中..." 文字，不再铺骨架屏，避免把现有数据整屏替换。
3. **按钮内 loading**：始终用 `<Loader2 className="h-3/3.5 w-3/3.5 animate-spin" />`（按钮字号决定尺寸）。禁止在按钮里嵌 `<LoadingSpinner />`，那是区域级组件。

新增骨架屏时放在 [Skeleton.tsx](src/components/shared/Skeleton.tsx) 并按 `hidden md:block` / `md:hidden` 自带响应式（和 `/stocks` 桌面表格/移动卡片双视图一致），调用方无需再包断点判断。基础 `Skeleton` 原子组件是 `animate-pulse + bg-gray-200 dark:bg-gray-800 + rounded-md`，自带深色模式。静默刷新（`fetchStocks(silent=true)`）不触发任何 loading UI——保持当前行集合不抖动是该路径的核心约束。

### SSR 安全：客户端独占值的渲染约定

SSR 阶段 `window` / `navigator` / `localStorage` 都不可用。若组件在首次渲染时读取这些值，服务端和客户端首帧会输出不一致的 HTML，React 抛 **hydration mismatch** 警告（可能伴随样式抖动）。

**反例**：`const isMac = typeof navigator !== 'undefined' && /Mac/.test(navigator.platform)` — 服务端 `isMac=false`，客户端 `isMac=true`，两边 placeholder 文案不同即爆。`localStorage.getItem(...)` 同理。

**正确模式**：首帧用与服务端一致的"安全默认值" + `useEffect` 里 mount 后再读取客户端值并 `setState`：

```tsx
const [isMac, setIsMac] = useState(false)  // SSR 安全默认
useEffect(() => {
  setIsMac(/Mac|iPod|iPhone|iPad/.test(navigator.platform))
}, [])
```

适用场景：平台探测（`navigator.platform`）、用户偏好（`localStorage`）、屏幕尺寸（`window.innerWidth`）、当前主题主动查询（优先用 `next-themes` 的 `useTheme` hook 而非 `document.documentElement.classList`）。

**`localStorage` 持久化 hook 模板**（参考 [useStockTableColumns.ts](src/app/stocks/hooks/useStockTableColumns.ts)）：初始 state 用工厂函数 `useState(getDefaults)` 给 SSR 默认值；`useEffect` 里读 localStorage，存在且解析合法则覆盖；`try/catch` 包裹 `localStorage` 读写（隐私模式/配额爆时静默降级）；存储 key 带版本号 `feature:name:v1`，schema 破坏性变更时 bump 即可丢弃旧数据；读取时用 `KNOWN_IDS` 白名单过滤已废弃 id，保证向前兼容。

### 表格列可见性（`/stocks` 表）

`/stocks` 桌面表格列多（16 列）且密，用户可自定义显示哪些列。实现集中在：

- [useStockTableColumns.ts](src/app/stocks/hooks/useStockTableColumns.ts) — `COLUMN_CONFIGS` 列定义单一数据源（id / label / default / group） + localStorage 持久化 hook（`stocks:visible-columns:v3`）。新增列在此追加一行即可；股票名为结构性必要不在此声明，由 page.tsx 直接硬渲染
- [ColumnVisibilityMenu.tsx](src/app/stocks/components/ColumnVisibilityMenu.tsx) — 下拉菜单组件，嵌在筛选器卡片 Header 右侧（与"清除全部"同列），`<lg` 只显图标避免窄屏挤压；`onSelect={(e) => e.preventDefault()}` 让 CheckboxItem 切换后不关闭菜单，支持连续切换多列
- `page.tsx` `<thead>` 和 [StockTableRow.tsx](src/app/stocks/components/StockTableRow.tsx) `<tbody>` 按 `isVisible(id)` 条件渲染 `<th>` / `<td>`，两处列顺序必须保持一致（错位会导致数据对不齐）
- 移动端 `StockCard` 卡片视图不受影响，列选择不适用

**默认显示策略**：行情 4 列（最新价 / 涨跌幅 / 成交额 / 换手率） + 估值 2 列（总市值 / PE-TTM） + CIO 综合评分 + 价值度量 3 列（ROC / 收益率 / 安全边际）= 10 列。**默认隐藏**：游资 / 中线 / 价值 三个 sub-component 评分（避免首屏徽章扎堆，需要时手动开启）、CIO 报告日期、关注价格 / 关注时间（CIO 复查触发器，使用频率低）。

**列定义破坏性变更须 bump `STORAGE_KEY` 版本号**（v1→v2→v3 …）。直接 bump 让所有用户回到最新默认视图，避免老用户落到"半新半旧"的视图。bump 时不需要写 migration——读取 storage 时按 `KNOWN_IDS` 白名单过滤已废弃 id，新加列对老 storage 数据自动隐藏。

### 染色规则（涨跌红绿）

`/stocks` 表格 + 移动卡片**只对"方向性"指标染红绿**：股票名 / 最新价 / 涨跌幅。**禁止**对成交额 / 换手率 / 总市值 / PE-TTM 染色——这些是"活跃度/估值"指标，不携带方向语义（10 亿成交额可能伴随上涨也可能伴随下跌），强行染色会赋予不存在的语义、误导用户。同花顺/东方财富/富途/雪球等主流软件均遵守此约定。

价值度量列（ROC / 收益率 / 安全边际）**可以**染红绿——它们是"对投资者有利/不利"的方向性判断（正收益率 = 红利好）。

### 数字格式化共享 utils（`format-utils.ts`）

[stocks/components/format-utils.ts](src/app/stocks/components/format-utils.ts) 集中桌面 `StockTableRow` 与移动 `StockCard` 共用的金额/市值/PE 格式化函数：`fmtAmount`（元 → 亿/万）/ `fmtMarketCap`（万元 → 亿/万）/ `fmtPE`（负值 → "亏损" warn / >500 → ">500" warn / 正常 → 1 位小数）。新加股票列表数字字段时必须复用，避免单位/警戒值在两端漂移。返回 `{ text, tone }` 让调用方按 tone 选 className（normal/muted/warn）。

### SortHeaderButton 占位 indicator 模式

可排序表头的方向箭头**槽位始终保留 12px**：未激活渲染淡灰双向 `ArrowUpDown`，激活渲染主色单向 `ChevronUp/Down`。这样切换排序状态时按钮宽度恒定，避免列宽抖动；同时给可排序列一个视觉提示。新加可排序列时直接用 `<SortHeaderButton ... />`，不要再手写排序图标占位。

### 筛选器与 URL 状态

所有筛选条件、分页、排序均同步到 URL（`router.replace` + `{ scroll: false }`），刷新页面状态保留。

| URL 参数 | 含义 | 说明 |
|----------|------|------|
| `market` | 市场筛选 | `SSE`=上海主板, `SZSE`=深圳主板，创业板/科创板/北交所直接对应 `stock_basic.market` |
| `industry` | 行业筛选 | 对应 `stock_basic.industry` 字段 |
| `concept` | 东方财富板块 | ts_code（如 `BK0714.DC`），通过 `dc_member` JOIN 筛选成分股 |
| `stock_selection_strategy_id` | 选股策略 ID | 后端执行策略后 WHERE IN 过滤 |
| `list` | 自选列表 ID | 后端 WHERE IN 子查询过滤，与其他条件可叠加 |
| `page` / `pageSize` | 分页 | 默认 page=1, pageSize=20 |
| `filters` | 筛选器折叠态 | 仅桌面端生效；`filters=collapsed` 表示折叠（缺省=展开）。折叠时顶部渲染激活筛选 chip 列表，点 `×` 单独清除；右上角"清除全部"批量清理 5 个维度并合并为单次 `router.replace` |
| `sort` | 多列排序 | 格式 `key:order,key:order,...`，优先级从前到后递减；缺省时退化为默认 `pct_change:desc`。支持的 key：`pct_change` / `score_hot_money` / `score_midline` / `score_longterm` / `cio_score` / `cio_last_date` / `cio_followup_time` / `code`。后端按白名单（`SORT_SPECS`，见 [stock_list.py](../backend/app/api/endpoints/stock_list.py)）拼 LEFT JOIN + ORDER BY，相同子查询（如 cio_* 三列）共享 `join_group` 只 JOIN 一次；`sb.code` 自动追加为兜底排序保分页稳定。`cio_last_date` 按 `stock_ai_analysis.created_at` 排（日期维度），`cio_score` 按最新 CIO 报告 `score`，`cio_followup_time` 从 `followup_triggers.time_triggers` JSONB 数组里用 `jsonb_array_elements` 提取最小 `expected_date::date` 排。**交互**：表头普通点击=该列单列切换（desc → asc → 默认）；**Shift+点击**=追加为次级排序键，已存在则循环 desc → asc → 移除；多列时表头标签右侧显示优先级数字角标。**兼容**：旧 `sortBy` / `sortOrder` 单列参数仍接受（`/stocks` 页面初始化时自动转换为 `sort`，旧书签不丢失），新代码请只用 `sort` |

**关键约束**：
- 市场筛选中，上海主板/深圳主板在 DB 中均存为 `market='主板'`，通过 `exchange` 字段区分（`SSE`/`SZSE`）
- 自选列表作为普通筛选条件，走同一个 `/api/stocks/list` 端点，**不是**独立的列表视图
- `activeListId` 直接从 URL 读取，不存 Zustand store
- 所有分页操作通过 `goToPage()` 同步 URL

**⚠️ 两套参数必须保持同步**：`fetchStocks`（加载列表页）和 `handleSelectAllFiltered`（全选所有筛选结果）使用相同的筛选条件，任何新增筛选参数必须同时添加到两处。`handleSelectAllFiltered` 调用 `GET /api/stocks/codes/filtered`，该端点支持与 `/api/stocks/list` 相同的所有筛选参数（含 `user_stock_list_id`）。

### AI 分析摘要注入（`include_analysis`）

`/api/stocks/list` 支持 `include_analysis=true` 参数，后端会批量查询每只股票的最新游资分析（`hot_money_view`），并将摘要注入每个股票对象的 `latest_analysis` 字段：

```typescript
// StockInfo.latest_analysis（无记录时为 null）
{ id: number; score: number | null; version: number; created_at: string }
```

`stocks/page.tsx` 每次加载列表时固定传入此参数，`score` 着色规则：≥8 红色，≥6 黄色，其余灰色。

### 个股分析页 `/analysis` 的 AI 决策板块

`/analysis` 页面所有 AI 内容（4 专家 JSON + CIO + 数据收集 Markdown）都以**主页卡片**形式串联展示：每张卡头部内嵌"日期翻页器 + 编辑 / 删除 / 源代码 / 复盘"工具栏，触发分析的"重新分析 / 一键分析 / 生成数据"按钮也在卡内。**没有 AI 分析弹窗**——曾经的 `HotMoneyViewDialog`（标题栏"提示词"按钮触发的 5 Tab 综合视图）已整体下线。新增"AI 类"维度直接加主页卡。

**核心数据模型：AI 分析的逻辑标的是"交易日"**。同 `(ts_code, analysis_type)` 在同一交易日下可能有多个版本（重新生成 / 改提示词 / 切模型），不同交易日各自独立编号。后端 `stock_ai_analysis` 表的 `version` 列在 `(ts_code, analysis_type)` 范围内全局递增（跨日跳号），**不要直接展示给用户**——前端用 `groupRecordsByTradeDate` 分组后按同日 `created_at` ASC 重新编号 `displayVersion 1..N`。卡片头部用 `<TradeDateVersionPager>` 表达两层导航：日历选交易日 + 同日内 `< vX/N >` 翻版本。后端表已支持该模型（`trade_date` 字段、`/api/stock-ai-analysis/list?trade_date=` 端点），无需后端改动；新增专家类型沿用 `useAnalysisHistory` 即可天然继承日历翻页能力。

页面纵向流（仅登录态显示 ③④⑤）：
1. **行情卡**（`QuotePanel`）— 最新价 / OHLC / 振幅 / 换手 / 成交 / 公司规模 chip。**纯盘口数据**，与 AI 解耦。
2. **估值数据卡**（`ValuationCard`）— PE / PB / PS / 股息率（`daily_basic`）+ ROC / EY / 安全边际（`stock_value_metrics`）+ 快照日期。**公开数据，未登录可见**。
3. **AI 决策摘要卡**（`ExpertSummaryCard`）— 4 列等宽：CIO / 游资 / 中线 / 价值；每列 = 评分 + rating + key_quote（`line-clamp-2`）+ ▲/▼ 因子计数；顶部"一键分析"按钮。点专家列滚到对应详情卡。
4. **CIO 综合决策卡**（`CioDecisionCard`，默认折叠）— 头部 collapse 按钮 + `TradeDateVersionPager` + `RecordActionToolbar`（源代码 / 编辑 / 删除）；展开后：multi_dimension_scan 三栏 / cross_dimension_analysis / core_drivers + core_risks 双栏 / rating_and_action 高亮卡（按 action 关键词配色）/ followup_triggers。**两套空态分支**：`!current` → "尚未生成"（真没记录）；`!parsed` → "内容解析失败"（有记录但 JSON 不合法）+ 翻页器 / 查看源代码 / 删除按钮，让用户能定位 LLM 原始输出并清理污染版本。后端写库前已强校验合法 JSON（见 backend/CLAUDE.md），新数据不会再走 `!parsed`，但保留兜底应对历史遗留畸形记录。
5. **三专家详情卡**（`ExpertDetailCard`，嵌入 Tab）— 游资 / 中线 / 价值；每个 Tab 内部含 `原报告 N | 复盘 M` 子段控件 + `TradeDateVersionPager` + `RecordActionToolbar`（源代码 / 编辑 / 复盘 / 删除）。Tab 右上角"重新分析"按钮（单专家）。
6. **数据收集卡**（`DataCollectionCard`，默认折叠）— "AI 看到的原料"；非 JSON、无评分、无复盘。

**主页 → 卡内组件统一通过 `tsCode` 驱动自身历史拉取**（不再依赖父级 `latestByExpert` prop 注入；保留 `latestByExpert` 仅供 `ExpertSummaryCard` 派生）。父页传 `refreshKey` 触发外部刷新，卡内通过 `onChange` 回调反向通知父页 bump `expertsRefreshKey` 以同步摘要卡。

共享渲染组件全部在 [components/stocks/analysis/](src/components/stocks/analysis/)：

- `text-utils.tsx` / `markdown.tsx` — `renderBold` / `highlightTags` / `MarkdownContent` / `markdownComponents`
- `sections.tsx` — `ScoreBadge` / `ProsConsList` / `FieldValue` / `GenericSection` / `FollowupTriggersSection`
- `StructuredAnalysisContent.tsx` — JSON 结构化渲染入口；支持 `hideFinalScore` / `hideTitleHeader` props（主页详情卡已自渲染头部和评分时用）
- `section-configs.ts` — `SECTION_CONFIGS` / `PM_FIELD_LABELS` / `JSON_ANALYSIS_TYPES`
- `expert-meta.ts` — 4 专家身份元数据（key / analysisType / templateKey / 中文名 / 副标题 / 图标 / colorVar / borderClass）+ `safeParseJSON` / `extractScore` / `extractKeyQuote` / `extractRating` / `extractBullBearCount` / `scoreToneClass`
- `trade-date-utils.ts` — 历史记录的"交易日 + 同日多版本"分组工具（`groupRecordsByTradeDate` / `normalizeTradeDate` / `parseTradeDateToDate` / `formatDateToTradeDate`）
- `useAnalysisHistory.ts` — 历史翻页 hook：返回 `{records, total, groups, selectedTradeDate, setSelectedTradeDate, versions, versionIndex, goNewerVersion, goOlderVersion, current, refresh, remove, update, loading}`，内部按 `(tsCode, analysisType)` 拉 `/api/stock-ai-analysis/history?limit=50` 后用 `groupRecordsByTradeDate` 分组。`refreshKey` 自增触发外部重拉，`enabled=false` 时跳过（`ExpertDetailCard` 的非激活 Tab 用此节流）。**锚定 effect 只依赖 `groups`，不依赖 `selectedTradeDate / versionIndex`**——否则用户手动切日期/版本会触发回锚循环（`Maximum update depth exceeded`）；用户选择通过 functional updater 读最新状态。**编辑后按 `lastViewedIdRef` 锚回原记录所在交易日 + 版本**。
- `RecordActions.tsx` — 4 个内嵌操作组件：`TradeDateVersionPager`（日期 pill 弹 [Calendar](src/components/ui/calendar.tsx) Popover 选交易日 + 同日多版本时显示 `< vX/N >` 翻页）、`RecordActionToolbar`（源代码 / 编辑 / 复盘 / 删除 4 图标按钮，按 tone 配色）、`DeleteConfirmDialog`、`EditAnalysisDialog`、`ViewSourceDialog`。**新增分析维度时只需在新组件里挂 `useAnalysisHistory` + 这几个工具，不必再为复盘 / 编辑 / 删除写一份 state**。
- `ExpertSummaryCard.tsx` / `CioDecisionCard.tsx` / `ExpertDetailCard.tsx` / `DataCollectionCard.tsx` — 四张主页卡

**专家身份色 token（`--expert-*`）**：CIO 紫 / 游资 橙 / 中线 蓝 / 价值 金，定义在 [globals.css](src/app/globals.css)，Tailwind 暴露为 `text-expert-cio` / `border-l-expert-hot-money` 等。**身份色仅用于"哪位专家说的"染色**（卡片左 border / 头部图标 / key_quote 背景）；评分高低仍走 `score-*`（紫罗兰单色相，见"语义色与过渡时长 token"），涨跌仍走 `positive` / `negative`，三套色阶不混用。数据收集卡是"原料"非"专家观点"，不戴身份色，标题图标用 `text-muted-foreground`。

**与现有派生数据的复用**：4 专家最新数据由统一的 `useEffect` + `Promise.all` 拉取，`expertsRefreshKey` 自增触发重拉；摘要卡 / CIO 卡 / 详情卡 / 数据卡都共享这个 key。

### 数据收集卡（`DataCollectionCard`）— "非 LLM 大文本类"主页卡范式

数据收集（`stock_data_collection`）和 4 位专家走的是同一张表（`stock_ai_analysis`）、同一套 `useAnalysisHistory` + `RecordActions` + `TradeDateVersionPager`，但有几条决定 UI 形态的关键差异，给后续添加"非评分类"维度（如新闻摘要、研报汇总等）时照抄：

| 维度 | 4 位专家卡 | 数据收集卡 |
|------|---------|---------|
| 输出格式 | JSON（`StructuredAnalysisContent` 结构化渲染） | **Markdown + YAML**（`MarkdownContent` 渲染） |
| 评分 / `key_quote` | 有 | **无**（卡头不显示评分槽位） |
| 默认展开 | 摘要卡总是显示，CIO / 详情卡按情况 | **默认折叠**（5k-15k 字的 Markdown 不该默认占屏；展开才渲染 body，省 DOM） |
| 触发方式 | `POST /api/stock-ai-analysis/generate-multi`（异步 Celery，`useMultiAnalysisTask`） | `apiClient.collectStockData(tsCode, name)`（**同步 1-3 秒，不走 LLM / Celery**，按钮内 spinner 即可） |
| 是否复盘 | 游资 / 中线 / 价值 有 | **无**（数据是事实，不"复盘"） |
| 一键分析覆盖 | ✓ | ✓（`expertsRefreshKey` bump 时跟着刷新） |

实现要点：
- **空态 + 满态两套 JSX**——空态时 header 一行（图标 + "尚未生成" + 生成按钮），跳过翻页器和工具栏；满态时按"折叠卡 + 折叠后才挂 MarkdownContent"组织，避免空数据时还渲染翻页空槽位。
- **`generateButton` JSX 抽常量**，空态和满态两处复用，避免重复定义。
- **错误/成功消息条**：折叠头下方 / 空态 header 下方分别一处 `genMsg`，两处样式同 `text-emerald-600` / `text-red-500`，操作完 2-3 秒人眼能看到即可，不做 toast。

### 跨入口任务状态同步：`useMultiAnalysisTask`

**AI 分析任务（异步 + 轮询）**：批量与单只一键共用 Celery 任务 `tasks.batch_ai_analysis`（后端用 `task_type` 区分，前端协议完全一致），两处入口：

- `/stocks` 浮动操作栏「批量 AI 分析」（`BatchAnalysisDialog`）：调 `POST /api/stock-ai-analysis/batch` 提交一组 ts_codes，拿 `celery_task_id` 后 3s 轮询 `GET /batch/{id}`。关闭弹窗不中断任务。
- `/analysis` 主页「一键分析」按钮（`ExpertSummaryCard` Header）：调 `POST /api/stock-ai-analysis/generate-multi`（单只 + concurrency=1），同样异步返回 `celery_task_id`，3s 轮询 `GET /batch/{id}`。提交前先调 `GET /active/by-ts-code/{ts_code}` 查活跃任务，命中则续轮询不重复提交。
- `/stocks` 另一层常驻轮询 `GET /batch/active/ts-codes` 拿"分析中"ts_code 集合（**覆盖批量 + 单只一键两类 task_type**）；`StockTableRow` 的 `isAnalyzing=true` 时把"AI 分析"按钮换为旋转图标，刷新页面后仍能恢复。股票从"分析中"列表移除时自动 `fetchStocks(true)` 拉最新评分。

**`useMultiAnalysisTask` hook**（[hooks/useMultiAnalysisTask.ts](src/hooks/useMultiAnalysisTask.ts)）封装"提交 → 轮询 → 探活 → 终态收尾"完整生命周期。`/analysis` 主页 `enableProbe=true`，mount 后每 3s 探一次活跃任务，与 `/stocks` 批量分析的状态同步——用户从 `/stocks` 触发批量分析后跳到 `/analysis` 看某只股，按钮自动是"分析中"态。终态后必须**再补拉一次** `GET /batch/{id}` 兜底 metadata.items 抢跑（见 backend/CLAUDE.md 同名陷阱）。新增"基于活跃 Celery 任务做 UI 状态恢复"的入口时优先复用此 hook。

**禁止把"分析中"状态做成短轮询闪烁**：探活 effect 不要把 `taskId` 列入 `useEffect` deps（每次 setTaskId 都触发 effect 重建 → cleanup 误清状态导致按钮文字闪烁）；用 ref 读最新 taskId。同理切股票/失能时清状态的 effect 不能"挂载即清"，必须用 `lastTsCodeRef` 比较"上一次实际生效的 tsCode"，仅在真切到不同值时清 —— 否则 `loadStockInfo` 完成那一拍 `basicInfo?.ts_code` 从 undefined 变为有值，会把刚由探活设上的状态误清。`useMultiAnalysisTask` 已封装这两条约束，参考它实现类似 hook。

### AI 生成接口

**`{{ stock_data_collection }}` 占位符填充**：`build_stock_prompt()` 通过 `allow_generate_data_collection` 参数区分行为：
- `GET /by-key/{key}`（模板预览）：`False`（默认），仅读取已有记录填充，无则留空提示
- `POST /generate`（生成分析）：`True`，若无今日数据收集记录则自动触发生成（带 asyncio.Lock 防并发重复）

**单专家"重新分析"**：`ExpertDetailCard` Tab 头的"重新分析"按钮调用 `POST /api/stock-ai-analysis/generate`，后端用 `build_stock_prompt()` 构建提示词，调用 AI 服务生成并自动保存，返回 `analysis_text` + `score` 并刷新历史列表。提示词构建逻辑集中在 `build_stock_prompt()`（`prompt_templates.py`），`GET /by-key/{key}` 和 `POST /generate` 共用同一函数，确保一致性。

**JSON 格式分析类型（5 种）**：`hot_money_view`、`midline_industry_expert`、`longterm_value_watcher`、`cio_directive`、`macro_risk_expert` 均要求 AI 返回结构化 JSON。后端通过 `ai_output_parser.parse_ai_json()` + Pydantic 模型（`schemas/ai_analysis_result.py`）解析，失败降级为原始 JSON dict。评分提取优先级：`final_score.score` → `comprehensive_score` → `score`。

**前端 `StructuredAnalysisContent` 渲染架构**（位于 [components/stocks/analysis/](src/components/stocks/analysis/)）：
- 按 `analysisType` 查表 `SECTION_CONFIGS[type]`，每个专家声明自己的 section 列表（顶层 JSON key + 中文标题 + 子字段 key→label 映射）。扩展新专家时只需追加一个配置项。
- `GenericSection` 组件统一渲染"标题 + 条目列表"；`FieldValue` 组件递归处理字符串 / 数组（`catalysts` 等） / 嵌套对象（`next_day_scenarios` 三档的 `{probability, trigger_condition}`）。
- `final_score` 统一渲染：新 schema `bull_factors`/`bear_factors`/`key_quote`，向后兼容旧 `pros`/`cons`。
- 顶层 `risk_warning` 字段（新游资 schema 独立字段）单独红色区块渲染。
- 旧 schema 字段 `probability_metrics` / `dimensions` / `trading_strategy` 保留兜底渲染，仅当当前 analysisType 的 SECTION_CONFIGS 声明的 key 全部缺失时降级。
- `PM_FIELD_LABELS` 映射表仅用于旧 schema `probability_metrics` 兜底（新 schema 不再用此字段）。
- JSON 解析失败时降级为 `MarkdownContent`（react-markdown + GFM）。
- `hideFinalScore` / `hideTitleHeader` props：主页 `ExpertDetailCard` 已在卡片头部独立渲染评分 + 标题，正文里隐藏。弹窗内调用时不传这两 props，保持原行为。

**Markdown 渲染**：`MarkdownContent`（在 `components/stocks/analysis/markdown.tsx`）使用 `react-markdown` + `remark-gfm` 渲染非 JSON 分析文本（如数据收集结果），支持 GFM 表格、标题、列表、代码块等完整 Markdown 语法。`markdownComponents` 常量定义自定义样式，`p` 和 `li` 中额外处理【标签】高亮。

**股票列表评分列 + CIO 列**：`/stocks` 页面表格按顺序显示 4 列 AI 评分 + CIO 报告日期 + CIO 复查触发器（价格 / 时间两列分开）：
- 评分列：游资（`latest_analysis_hot_money.score`）、中线（`latest_analysis_midline.score`）、价值（`latest_analysis_longterm.score`）、**CIO评分**（`latest_analysis_cio.score`）
- **CIO日期**：`latest_analysis_cio.created_at` 截取前 10 位
- **关注价格**：`followup_triggers.price_triggers` 中 `break_up` / `break_down` 的 `price`，▲/▼ 标识方向（不可排序）
- **关注时间**：`followup_triggers.time_triggers` 中 `expected_date` 最早的一条

后端 `enrich_stock_list_multi()` 通过 `asyncio.gather` 并发批量查询四种 analysis_type，一次注入到 `StockInfo`；CIO 记录额外注入 `followup_triggers`。`ScoreCell` 组件统一渲染评分色阶（≥8 红/≥6 黄/其余灰），4 列评分共享同一个组件，新增专家类型只需追加 `latest_analysis_xxx` 字段 + 在 `StockTableRow` 的 map 数组里加一项。

**股票列表静默刷新（`fetchStocks(silent=true)`）**：自动刷新（交易时段每 3s、分析中标志移除后）只更新当前已显示行，不改变行集合/顺序/`totalStocks`。实现：从 `useStockStore.getState().stocks` 取当前显示的 `ts_code`s，调 `GET /api/stocks/list?ts_codes=...,...&include_analysis=true`（新增的 `ts_codes` IN 过滤跳过分页/排序/筛选），按 `code` Map 原位合并回存量数组。避免用户翻到第 N 页或改变排序后被异步刷新重置到默认视图。

`stock_ai_analysis` 表通过 `analysis_type` 字段区分类型，后端 `ALLOWED_ANALYSIS_TYPES` 枚举控制允许写入的类型——**新增分析类型时必须同时更新后端 Service 中的 `ALLOWED_ANALYSIS_TYPES`**，以及 `_JSON_ANALYSIS_TYPES`（`stock_ai_analysis.py`）、`admin/types/prompt-template.ts` 中的 `BUSINESS_TYPES` 和 `BUSINESS_TYPE_LABELS`。

后端 API（均需登录）：
- `POST /api/stock-ai-analysis/generate` — 单个专家 AI 生成并保存
- `POST /api/stock-ai-analysis/generate-multi` — 多专家并行生成（`analysis_types` 列表 + `include_cio` 可选 CIO 综合决策）
- `POST /api/stock-ai-analysis/` — 保存新记录（版本自动递增）
- `GET  /api/stock-ai-analysis/latest` — 获取最新一条
- `GET  /api/stock-ai-analysis/history` — 分页获取所有历史
- `PUT  /api/stock-ai-analysis/{id}` — 修改（仅创建者，403 无权限）
- `DELETE /api/stock-ai-analysis/{id}` — 删除（仅创建者，403 无权限）

### 东方财富板块筛选（LazyConceptSelect）

组件位于 `frontend/src/components/stocks/LazyConceptSelect.tsx`，支持三种板块类型切换：
- **概念板块**：东方财富概念（如"新能源车"）
- **行业板块**：东方财富行业分类
- **地域板块**：东方财富地域板块

后端端点 `/api/stocks/list/concepts` 的 `idx_type` 参数控制板块类型，组件内部维护 Tab 状态，切换时重置列表和搜索框。

---

## 已移除功能（2026-03-25）

以下功能已从 frontend 中移除，勿再添加相关代码：

1. **概念标签管理**
   - 概念板块管理页面（`/concepts`）
   - 股票概念关联功能、概念筛选功能
   - 相关 API：`/api/concepts/*`、`/api/stocks/**/concepts`

2. **股票详情页面**
   - 股票详情页面（`/stocks/[code]`）— 已移除前端页面
   - 注：股票列表页 `/stocks` 仍存在；股票相关 API 和数据保留

3. **数据中心**
   - 数据初始化页面（`/sync/initialize`）
   - 数据中心导航页面（`/sync`）
   - 扩展数据页面（`/sync/extended`）
   - 注：数据同步 API 和功能保留

---

## 策略系统

### 创建入口（两条路径）

| 路径 | 说明 |
|------|------|
| `/strategies/create/ai` | AI 全自动生成：选类型 → 描述需求 → 提交异步任务 → 自动验证 → 自动保存 |
| `/strategies/create` | 手动创建：选策略类型（入场/离场/选股）→ 填写代码 → 手动保存 |

策略列表页（`/strategies`）有三个 Tab：入场策略、离场策略、选股策略。**选股策略卡片**不显示回测按钮和风险等级，替换为"查看选股结果"链接（跳转 `/stocks?stock_selection_strategy_id={id}`）。

### AI 生成流程（`/strategies/create/ai`）

`AIGenerationTaskContext` 管理后台异步任务状态。页面生命周期：
1. 提交 → `apiClient.generateStrategyAsync({ strategy_type })` → 获得 `task_id`
2. `addTask(task_id, provider)` 加入监控，`phase` 切换到 `generating`
3. `currentTask.status === 'SUCCESS'` → `getTaskResult()` 取结果 → 自动 `validateStrategy()` → `phase: validating`
4. 验证通过 → 自动 `createStrategy({ strategy_type })` → 跳转列表

**策略类型** 在提交时必须传给后端（`strategy_type` 字段），后端据此选择对应的数据库 prompt 模板（见 admin CLAUDE.md "Prompt 模板管理"）。

---

## 通知系统（用户侧）

- **通知设置**：`/settings/notifications` — 用户配置订阅偏好、渠道（Email/Telegram）
- **通知中心**：`/notifications` — 查看站内消息、标记已读
- **未读角标**：`NotificationBadge` — 30 秒轮询未读数量

**API 端点**（路由前缀 `/api/notifications`，需认证）：

| 端点 | 方法 | 描述 |
|------|------|------|
| `/settings` | GET/PUT | 获取/更新用户通知配置 |
| `/in-app` | GET | 获取站内消息列表 |
| `/in-app/{id}/read` | POST | 标记消息为已读 |
| `/in-app/read-all` | POST | 全部标记为已读 |
| `/unread-count` | GET | 获取未读消息数量 |
