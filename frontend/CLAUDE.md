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

## 自选股功能（用户股票列表）

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
- **下次关注价格**：`followup_triggers.price_triggers` 中 `break_up` / `break_down` 的 `price`，▲/▼ 标识方向（不可排序）
- **下次关注时间**：`followup_triggers.time_triggers` 中 `expected_date` 最早的一条

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
