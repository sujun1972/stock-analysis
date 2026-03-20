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
   - 用法更简洁：
   ```tsx
   <PageHeader
     title="页面标题"
     description="页面描述"
     actions={<Button>操作</Button>}
   />
   ```

#### 父级导航页面
为了支持面包屑的多级导航，已创建以下父级菜单页面：
- `/settings` - 系统设置导航页
- `/sentiment` - 市场情绪导航页
- `/sync` - 数据同步导航页
- `/logs` - 日志管理导航页
- `/monitoring` - 系统监控导航页

这些页面以卡片形式展示子功能入口，解决了中间层级页面点击的问题。

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
- 每个信号处理器创建独立的数据库连接（避免 fork pool worker 共享连接）
- Celery 5.x 中从 `sender.request.id` 获取 task_id

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
   const { addTask, triggerPoll } = useTaskStore()

   const handleSync = async () => {
     const response = await apiClient.syncDataAsync(params)

     if (response.code === 200 && response.data) {
       // 添加到任务存储
       addTask({
         taskId: response.data.celery_task_id,
         taskName: response.data.task_name,
         displayName: response.data.display_name,
         taskType: 'data_sync',
         status: 'running',
         progress: 0,
         startTime: Date.now()
       })

       // 立即触发轮询
       triggerPoll()

       // 延迟刷新数据
       setTimeout(() => loadData().catch(() => {}), 3000)
     }
   }
   ```

**优势**：
- ✅ 异步执行，不阻塞前端
- ✅ 任务在任务面板实时显示
- ✅ Header图标即时更新
- ✅ 任务历史持久化到数据库
- ✅ 统一的用户体验

**已实现的页面**：
- 定时任务配置页面（`/settings/scheduler`）
- 沪深港通资金流向页面（`/data/moneyflow-hsgt`）
- 大盘资金流向页面（`/data/moneyflow-mkt-dc`）
- 板块资金流向页面（`/data/moneyflow-ind-dc`）
- 个股资金流向页面（Tushare）（`/data/moneyflow`）
- 个股资金流向页面（DC）（`/data/moneyflow-stock-dc`）

**注意**：旧的同步阻塞API（如 `/sync`）保留用于向后兼容，但新开发的功能应优先使用异步模式。

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
├── concepts.ts          # 概念板块 API
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

const sentiment = await sentimentApi.getSentimentDaily()
const moneyflow = await moneyflowApi.getMoneyflowMktDc(params)
```

**旧代码（向后兼容）**：
```typescript
// 继续使用统一的 apiClient 对象
import { apiClient } from '@/lib/api-client'

const sentiment = await apiClient.getSentimentDaily()
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
   import type { SentimentListParams } from '@/lib/api/sentiment'
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
1. **基础数据** (100-199) - 股票列表、新股、退市等
2. **行情数据** (200-299) - 日K、分钟K、实时行情
3. **扩展数据** (300-399) - 每日指标、资金流向、融资融券等
4. **资金流向** (400-499) - 各类资金流向专项任务
5. **两融及转融通** (500-599) - 融资融券相关任务
6. **市场情绪** (600-699) - 情绪抓取、AI分析
7. **盘前分析** (700-799) - 盘前数据同步和分析
8. **质量监控** (800-899) - 数据质量检查和报告
9. **报告通知** (900-999) - 邮件、Telegram通知
10. **系统维护** (1000+) - 系统级维护任务

#### 积分消耗管理
- 高消耗任务（>=1000积分）使用黄色徽章高亮显示
- 普通任务使用灰色徽章
- 未设置积分的任务不显示徽章
- 用户可在编辑对话框中修改积分值

#### 元数据同步
- **后端**: `task_executor.py` 中的 `TASK_MAPPING` 定义任务元数据
- **数据库**: 迁移脚本初始化元数据，作为单一数据源
- **前端**: 直接从API响应中读取元数据，无需硬编码映射

注意：
- DataTable 组件使用 `accessor` 函数而非 `render` 来自定义列渲染
- 新增任务时，优先在数据库中设置元数据，确保排序和分类正确

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

### 资金流向数据

#### 沪深港通资金流向
- **API端点**: `/api/moneyflow-hsgt`
- **前端页面**: `/admin/app/(dashboard)/data/moneyflow-hsgt/page.tsx`
- **数据内容**: 沪股通、深股通、港股通(上海)、港股通(深圳)的每日资金流向
- **特点**: 支持2026年及以后的最新数据，替代了仅支持到2025年的北向资金持股明细(hk_hold)
- **积分消耗**: 2000积分/次（Tushare Pro接口）
- **页面功能**:
  - 统计卡片：北向资金均值、累计净流入、北向最大流入、南向最大流出
  - 趋势图表：北向和南向资金流向可视化
  - 日期筛选：使用弹出式日历选择器（`@/components/ui/date-picker`）
  - 数据单位：统一使用亿元（原始数据为百万元）
  - 响应式布局：
    - 桌面端：表格视图，简化列头
    - 移动端：卡片视图，垂直堆叠展示，斑马纹背景，淡蓝色交互反馈

#### 大盘资金流向（DC）
- **API端点**: `/api/moneyflow-mkt-dc`
- **前端页面**: `/admin/app/(dashboard)/data/moneyflow-mkt-dc/page.tsx`
- **数据内容**: 东方财富大盘资金流向，包含上证/深证指数及主力资金（超大单、大单、中单、小单）流入流出情况
- **积分消耗**: 120积分/次（试用），6000积分/次（正式）
- **页面功能**:
  - 统计卡片：主力资金均值、累计净流入、最大净流入、超大单均值
  - 趋势图表：主力资金净流入可视化
  - 日期筛选：支持自定义日期范围查询
  - 数据单位：统一使用亿元（原始数据为元）
  - 异步同步：支持后台任务执行，实时显示进度
  - 响应式布局：
    - 桌面端：完整表格视图，显示所有资金流向指标
    - 移动端：卡片视图，垂直堆叠展示核心指标

#### 板块资金流向（DC）
- **API端点**: `/api/moneyflow-ind-dc`
- **前端页面**: `/admin/app/(dashboard)/data/moneyflow-ind-dc/page.tsx`
- **数据内容**: 东方财富板块资金流向，包含行业、概念、地域板块的主力资金流入流出情况
- **积分消耗**: 6000积分/次（Tushare Pro接口）
- **页面功能**:
  - 统计卡片：主力资金均值、累计净流入、最大净流入、超大单均值
  - 趋势图表：TOP 10板块资金流向可视化（主力净流入、超大单、大单）
  - 筛选器：支持日期范围和板块类型（行业/概念/地域）筛选
  - 数据单位：统一使用亿元（原始数据为元）
  - 异步同步：支持后台任务执行，实时显示进度
  - 响应式布局：
    - 桌面端：完整表格视图，显示所有资金流向指标和排名
    - 移动端：卡片视图，垂直堆叠展示核心指标

#### 个股资金流向（Tushare）
- **API端点**: `/api/moneyflow`
- **前端页面**: `/admin/app/(dashboard)/data/moneyflow/page.tsx`
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
- **前端页面**: `/admin/app/(dashboard)/data/moneyflow-stock-dc/page.tsx`
- **数据内容**: 东方财富个股资金流向，包含个股主力资金（超大单、大单、中单、小单）流入流出情况
- **积分消耗**: 5000积分/次（Tushare Pro接口）
- **页面功能**:
  - 统计卡片：主力资金均值、累计净流入、最大净流入、统计股票数
  - 趋势图表：TOP 20个股资金流向可视化（主力净流入、超大单、大单）
  - 筛选器：支持股票代码和日期范围筛选
  - 数据单位：统一使用亿元（原始数据为万元）
  - 异步同步：支持后台任务执行，实时显示进度
  - 响应式布局：
    - 桌面端：完整表格视图，显示所有资金流向指标
    - 移动端：卡片视图，垂直堆叠展示核心指标

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

5. **扩展数据**
   - `DailyBasicRepository` - 每日指标数据（换手率、市盈率、市净率等）
   - `HkHoldRepository` - 北向资金持股数据
   - `StkLimitRepository` - 涨跌停价格数据
   - `BlockTradeRepository` - 大宗交易数据
   - `ConceptRepository` - 概念板块和股票关系管理

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

9. **市场情绪** （✨ 新增于 2026-03-20）
   - `MarketSentimentRepository` - 大盘情绪数据（上证/深证/创业板指数）
   - `LimitUpPoolRepository` - 涨停板情绪池（连板天梯、炸板数据）
   - `DragonTigerListRepository` - 龙虎榜数据（机构席位、游资动向）
   - `SentimentCycleRepository` - 情绪周期数据（赚钱效应指数）
   - `SentimentAiAnalysisRepository` - AI情绪分析结果

10. **股票数据**
   - `StockDailyRepository` - 股票日线数据（支持回测数据加载）
   - `StockBasicRepository` - 股票基础信息（代码、名称、市场、行业等）

11. **用户管理**
   - `UserQuotaRepository` - 用户配额管理（配额重置、配额查询、使用量统计）

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

6. **完整的异常处理**
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
- ✅ `ConceptRepository` - 概念板块和股票关系管理
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
- ✅ `concepts.py` - 5个端点（概念列表、详情、股票查询、概念更新）
- ✅ `stocks.py` - 概念过滤功能
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

**待创建的 Repository**（优先级较低）：
- `AdjFactorRepository` - 复权因子数据
- `SuspendRepository` - 停复牌信息
- `PremarketRepository` - 盘前数据

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

**重构收益**：
- 消除了约 **250 行重复代码**（7 个文件 × 35 行/文件）
- 移除 7 处 `DatabaseManager` 直接使用
- 移除 7 处 `INSERT INTO celery_task_history` SQL 语句
- 统一任务历史记录创建逻辑，便于维护

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

**拆分示例 1** (sentiment 模块重构):
```
# 重构前
endpoints/sentiment.py (1018行) - 单一文件

# 重构后
endpoints/sentiment/
├── __init__.py          # 路由聚合
├── schemas.py           # Pydantic 数据模型
├── query.py             # 查询类端点
├── sync.py              # 同步类端点
├── cycle.py             # 情绪周期端点
└── ai_analysis.py       # AI分析端点
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
from . import query, sync, cycle, ai_analysis

router = APIRouter()

# 注册子路由
router.include_router(query.router, tags=["sentiment-query"])
router.include_router(sync.router, tags=["sentiment-sync"])
router.include_router(cycle.router, prefix="/cycle", tags=["sentiment-cycle"])
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

**第二阶段（近期）**:
1. `TradingCalendarRepository` - 交易日历
2. 市场情绪相关 Repository（5个）:
   - `MarketSentimentRepository`
   - `LimitUpPoolRepository`
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

**问题：性能较慢**
- [ ] 检查是否使用批量操作（而非循环单条插入）
- [ ] 检查查询是否添加了适当的索引
- [ ] 检查是否有不必要的 N+1 查询
- [ ] 考虑使用数据库查询日志分析慢查询