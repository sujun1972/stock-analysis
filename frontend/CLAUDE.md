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
| `text-warning` / `bg-warning-soft` | 关注黄 | ROC 15~30%、安全边际 30~100%、评分 6-8 |
| `text-info` | 信息蓝 | 排序激活、次要提示；业务 primary 仍用 `text-primary` |
| `duration-fast` (120ms) / `duration-normal` (200ms) / `duration-slow` (320ms) | 过渡时长分档 | `transition-colors duration-fast` 等 |

token 定义在 [globals.css](src/app/globals.css) 的 `:root` / `.dark` 里，深色模式已单独升阶至 red-300 / green-400 / yellow-300 级亮度以保证对比度。K 线红涨绿跌的 `#ef4444` / `#22c55e` 是 ECharts 专用常量不走此体系（见 useEChartsTheme）。

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

**主题联动（`useEChartsTheme`）**：所有 ECharts 实例组件（`EChartsStockChart` / `MinuteChart` / `BacktestKLineChart` / `EquityCurveChart` / `ai-lab/*` / `analysis` 筹码图）统一使用 [useEChartsTheme](src/hooks/useEChartsTheme.ts) 跟随 `next-themes` 的深浅主题。约定：

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

`HotMoneyViewDialog` 在 <sm（手机）将 Radix `<DialogContent>` 覆盖为从底部滑入的全屏页，≥sm 保持居中弹窗。不引入新组件，全部靠 Tailwind `max-sm:` 变体叠加覆盖 `DialogContent` 基础类：

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

`/stocks` 桌面表格列多（15 列）且密，用户可自定义显示哪些列。实现集中在：

- [useStockTableColumns.ts](src/app/stocks/hooks/useStockTableColumns.ts) — `COLUMN_CONFIGS` 列定义单一数据源（id / label / default / group） + localStorage 持久化 hook（`stocks:visible-columns:v1`）。新增列在此追加一行即可；股票名/操作列为结构性必要，不在此声明，由 page.tsx 直接硬渲染
- [ColumnVisibilityMenu.tsx](src/app/stocks/components/ColumnVisibilityMenu.tsx) — 下拉菜单组件，嵌在筛选器卡片 Header 右侧（与"清除全部"同列），`<lg` 只显图标避免窄屏挤压；`onSelect={(e) => e.preventDefault()}` 让 CheckboxItem 切换后不关闭菜单，支持连续切换多列
- `page.tsx` `<thead>` 和 [StockTableRow.tsx](src/app/stocks/components/StockTableRow.tsx) `<tbody>` 按 `isVisible(id)` 条件渲染 `<th>` / `<td>`，两处列顺序必须保持一致（错位会导致数据对不齐）
- 移动端 `StockCard` 卡片视图不受影响，列选择不适用

默认隐藏：关注价格 / 关注时间（CIO 复查触发器，使用频率低）。默认可见其余 10 列。新增列时默认可见性以"日常常用"为准。

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

### AI 分析弹窗（`HotMoneyViewDialog`）

共享组件位于 `frontend/src/components/stocks/HotMoneyViewDialog.tsx`，在股票列表页（`/stocks`）和分析页（`/analysis`）复用。通过"AI 分析"按钮触发。

弹窗内含 **5 个 Tab**，各自独立管理历史记录和状态：

| Tab | analysis_type | 提示词 key |
|-----|--------------|------------|
| 游资观点 | `hot_money_view` | `top_speculative_investor_v1` |
| 数据收集 | `stock_data_collection` | `stock_data_collection_v1` |
| 中线专家 | `midline_industry_expert` | `midline_industry_expert_v1` |
| 价值守望 | `longterm_value_watcher` | `longterm_value_watcher_v1` |
| CIO 指令 | `cio_directive` | `cio_directive_v1` |

每个 Tab 功能：通过"AI 分析"按钮一键生成并自动保存、查看/翻页历史分析记录、编辑/删除已有记录（仅记录创建者）、折叠展示提示词（复制按钮在提示词区域内）。弹窗内无手动输入/保存区域，所有分析均通过后端 AI 生成。

**一键分析按钮**：弹窗底部 Footer 的「一键分析」按钮调用 `POST /api/stock-ai-analysis/generate-multi`，并行生成游资/中线/价值 3 个专家 + CIO 综合决策。完成后通过 `refreshKey` 机制触发所有 Tab 自动刷新历史。各 Tab 内的单独"AI 分析"按钮仍保留，可单独重新生成某个专家。

**批量 AI 分析（异步 + 轮询）**：`/stocks` 页面选中多只股票后，浮动操作栏中的「批量 AI 分析」按钮（`BatchAnalysisDialog`）调用 `POST /api/stock-ai-analysis/batch` 提交 Celery 任务，拿到 `celery_task_id` 后每 3 秒 `GET /api/stock-ai-analysis/batch/{id}` 轮询进度。关闭弹窗不中断任务。`stocks/page.tsx` 另一层常驻轮询 `GET /api/stock-ai-analysis/batch/active/ts-codes`，登录用户每 3 秒拉一次"分析中"ts_code 集合，`StockTableRow` 的 `isAnalyzing=true` 时把"AI 分析"按钮替换为旋转图标（刷新页面后仍能恢复展示）。股票从"分析中"列表移除时自动 `fetchStocks(true)` 拉最新评分。

打开弹窗时，全部 5 个提示词通过 `Promise.all` 并发加载，互不阻塞。新增 Tab 后必须同步更新父页面（`/stocks/page.tsx`、`/analysis/page.tsx`）的 state 和 `HotMoneyViewDialog` props。

**`{{ stock_data_collection }}` 占位符填充**：`build_stock_prompt()` 通过 `allow_generate_data_collection` 参数区分行为：
- `GET /by-key/{key}`（模板预览）：`False`（默认），仅读取已有记录填充，无则留空提示
- `POST /generate`（生成分析）：`True`，若无今日数据收集记录则自动触发生成（带 asyncio.Lock 防并发重复）

**AI 直接生成（各 Tab）**：各 Tab 可通过"AI 分析"按钮调用 `POST /api/stock-ai-analysis/generate`，后端用 `build_stock_prompt()` 构建提示词，调用 AI 服务生成并自动保存，返回 `analysis_text` + `score` 并刷新历史列表。提示词构建逻辑集中在 `build_stock_prompt()`（`prompt_templates.py`），`GET /by-key/{key}` 和 `POST /generate` 共用同一函数，确保一致性。

**JSON 格式分析类型（5 种）**：`hot_money_view`、`midline_industry_expert`、`longterm_value_watcher`、`cio_directive`、`macro_risk_expert` 均要求 AI 返回结构化 JSON。后端通过 `ai_output_parser.parse_ai_json()` + Pydantic 模型（`schemas/ai_analysis_result.py`）解析，失败降级为原始 JSON dict。评分提取优先级：`final_score.score` → `comprehensive_score` → `score`。

**前端 `StructuredAnalysisContent` 渲染架构**（`HotMoneyViewDialog.tsx`）：
- 按 `analysisType` 查表 `SECTION_CONFIGS[type]`，每个专家声明自己的 section 列表（顶层 JSON key + 中文标题 + 子字段 key→label 映射）。扩展新专家时只需追加一个配置项。
- `GenericSection` 组件统一渲染"标题 + 条目列表"；`FieldValue` 组件递归处理字符串 / 数组（`catalysts` 等） / 嵌套对象（`next_day_scenarios` 三档的 `{probability, trigger_condition}`）。
- `final_score` 统一渲染：新 schema `bull_factors`/`bear_factors`/`key_quote`，向后兼容旧 `pros`/`cons`。
- 顶层 `risk_warning` 字段（新游资 schema 独立字段）单独红色区块渲染。
- 旧 schema 字段 `probability_metrics` / `dimensions` / `trading_strategy` 保留兜底渲染，仅当当前 analysisType 的 SECTION_CONFIGS 声明的 key 全部缺失时降级。
- `PM_FIELD_LABELS` 映射表仅用于旧 schema `probability_metrics` 兜底（新 schema 不再用此字段）。
- JSON 解析失败时降级为 `MarkdownContent`（react-markdown + GFM）。

**Markdown 渲染**：`HotMoneyViewDialog.tsx` 使用 `react-markdown` + `remark-gfm` 渲染非 JSON 分析文本（如数据收集结果），支持 GFM 表格、标题、列表、代码块等完整 Markdown 语法。`markdownComponents` 常量定义自定义样式，`p` 和 `li` 中额外处理【标签】高亮。

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
