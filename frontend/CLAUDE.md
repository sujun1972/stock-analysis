# Frontend 开发指南

Frontend 是面向普通用户的 Next.js 应用（与 Admin 管理后台分开部署）。

## 技术栈

- **框架**: Next.js (App Router)
- **状态管理**: Zustand（`stores/`）
- **API 调用**: `frontend/src/lib/api-client.ts`
- **类型定义**: `frontend/src/types/`

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
- 主页面：`frontend/src/app/stocks/page.tsx`（`AddToListDialog`, `RenameListDialog`）
- API 方法：`frontend/src/lib/api-client.ts`（`getUserStockLists`, `createStockList`, `renameStockList`, `deleteStockList`, `getStockListItems`, `addStocksToList`, `removeStocksFromList`）
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

## 已移除功能（2026-03-25）

以下功能已从 frontend 中移除，勿再添加相关代码：

1. **概念标签管理**
   - 概念板块管理页面（`/concepts`）
   - 股票概念关联功能、概念筛选功能
   - 相关 API：`/api/concepts/*`、`/api/stocks/**/concepts`

2. **股票管理页面**
   - 股票列表管理页面（`/stocks`）— 已移除前端页面
   - 股票详情页面（`/stocks/[code]`）— 已移除前端页面
   - 注：股票相关 API 和数据保留

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
