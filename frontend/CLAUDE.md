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

---

## `/stocks` 页面筛选架构

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
| `sortBy` / `sortOrder` | 排序 | 默认 pct_change desc；支持 `pct_change`/`score_hot_money`/`score_midline`/`score_longterm`，后端 LEFT JOIN 排序 |

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

打开弹窗时，全部 5 个提示词通过 `Promise.all` 并发加载，互不阻塞。新增 Tab 后必须同步更新父页面（`/stocks/page.tsx`、`/analysis/page.tsx`）的 state 和 `HotMoneyViewDialog` props。

**`{{ stock_data_collection }}` 占位符填充**：`build_stock_prompt()` 通过 `allow_generate_data_collection` 参数区分行为：
- `GET /by-key/{key}`（模板预览）：`False`（默认），仅读取已有记录填充，无则留空提示
- `POST /generate`（生成分析）：`True`，若无今日数据收集记录则自动触发生成（带 asyncio.Lock 防并发重复）

**AI 直接生成（各 Tab）**：各 Tab 可通过"AI 分析"按钮调用 `POST /api/stock-ai-analysis/generate`，后端用 `build_stock_prompt()` 构建提示词，调用 AI 服务生成并自动保存，返回 `analysis_text` + `score` 并刷新历史列表。提示词构建逻辑集中在 `build_stock_prompt()`（`prompt_templates.py`），`GET /by-key/{key}` 和 `POST /generate` 共用同一函数，确保一致性。

**JSON 格式分析类型（5 种）**：`hot_money_view`、`midline_industry_expert`、`longterm_value_watcher`、`cio_directive`、`macro_risk_expert` 均要求 AI 返回结构化 JSON。后端通过 `ai_output_parser.parse_ai_json()` + Pydantic 模型（`schemas/ai_analysis_result.py`）解析，失败降级为原始 JSON dict。评分提取优先级：`final_score.score` → `comprehensive_score` → `score`。前端 `StructuredAnalysisContent` 组件统一渲染所有 JSON 类型，`PM_FIELD_LABELS` 映射表将 `probability_metrics` 中的英文 key 转为中文标签；JSON 解析失败时降级为 Markdown 渲染。

**Markdown 渲染**：`HotMoneyViewDialog.tsx` 使用 `react-markdown` + `remark-gfm` 渲染非 JSON 分析文本（如数据收集结果），支持 GFM 表格、标题、列表、代码块等完整 Markdown 语法。`markdownComponents` 常量定义自定义样式，`p` 和 `li` 中额外处理【标签】高亮。

**股票列表评分列**：`/stocks` 页面表格显示三列 AI 评分：游资（`latest_analysis_hot_money.score`）、中线（`latest_analysis_midline.score`）、价值（`latest_analysis_longterm.score`）。后端 `enrich_stock_list_multi()` 通过 `asyncio.gather` 并发批量查询三种类型，一次注入到 `StockInfo` 对象。

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
