# Admin 项目重构技能

## 概述
此技能用于重构和优化 admin 项目的代码质量、性能和可维护性。

## 重构策略

### 1. API 客户端模块化
将大型 api-client.ts 文件拆分为独立模块：
- `lib/api/base.ts` - 基础配置和拦截器
- `lib/api/auth.ts` - 认证相关
- `lib/api/stocks.ts` - 股票相关
- `lib/api/strategies.ts` - 策略相关
- `lib/api/users.ts` - 用户管理
- `lib/api/index.ts` - 统一导出

### 2. 常量管理
创建 `lib/constants.ts` 统一管理：
- 颜色映射（STRATEGY_TYPE_COLORS 等）
- 标签映射（STRATEGY_TYPE_LABELS 等）
- 配置常量（PAGINATION、API_CONFIG 等）
- 验证规则（VALIDATION_RULES）

### 3. 通用组件提取
- `components/common/DataTable.tsx` - 通用数据表格
- `hooks/use-api-call.ts` - API 调用 Hook
- `hooks/queries/` - React Query hooks

### 4. React Query 优化
替换 useState + useEffect 模式：
```typescript
// 旧方式
const [data, setData] = useState([])
useEffect(() => { fetchData().then(setData) }, [])

// 新方式
const { data, isLoading } = useQuery({
  queryKey: ['data'],
  queryFn: fetchData
})
```

### 5. 页面模块化重构（新增）
当页面文件超过 500 行时，采用 Hooks + Components 架构拆分：

**目录结构**：
```
page/
├── page.tsx              # 主页面（200-300行，编排和组合）
├── hooks/                # 自定义 Hooks
│   ├── index.ts         # 统一导出
│   ├── useXxxFilters.ts # 筛选和分页
│   ├── useXxxDialogs.ts # 对话框管理
│   ├── useXxxForm.ts    # 表单管理和验证
│   └── useXxxActions.ts # 操作逻辑
└── components/           # 子组件
    ├── index.ts         # 统一导出
    ├── XxxFilters.tsx   # 筛选控件
    ├── XxxTable.tsx     # 表格组件
    ├── XxxCard.tsx      # 卡片组件
    └── XxxDialog.tsx    # 对话框组件
```

**拆分原则**：
- 每个 Hook 只负责一个功能域（筛选/对话框/表单/操作）
- 每个 Component 只负责一个 UI 模块
- 主页面只负责组合和编排
- 通过 props 传递依赖，避免全局状态

**重构收益**：
- 主页面代码减少 70%+
- 文件行数控制在 50-200 行
- 代码可复用、易测试、好维护

## 使用示例

### 使用新 API 客户端
```typescript
import { stockApi } from '@/lib/api'
const stocks = await stockApi.getStockList()
```

### 使用通用组件
```typescript
import { DataTable } from '@/components/common/DataTable'
import { STRATEGY_TYPE_COLORS } from '@/lib/constants'
```

### 使用 React Query Hooks
```typescript
import { useStockList } from '@/hooks/queries/use-stocks'
const { data, isLoading } = useStockList({ page: 1 })
```

### 页面模块化重构示例
```typescript
// hooks/useUserFilters.ts
export function useUserFilters() {
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  // ... 筛选逻辑
  return { search, setSearch, page, setPage, queryParams }
}

// components/UserFilters.tsx
export function UserFilters({ search, setSearch, onSearch }) {
  return <Input value={search} onChange={e => setSearch(e.target.value)} />
}

// page.tsx (主页面)
export default function UsersPage() {
  const { search, setSearch, queryParams } = useUserFilters()
  const { data, isLoading } = useUserList(queryParams)

  return (
    <div>
      <UserFilters search={search} setSearch={setSearch} />
      <DataTable data={data} loading={isLoading} />
    </div>
  )
}
```

## 已完成的重构示例
- ✅ **用户管理页面** (`/users`)：959 行 → 278 行（↓ 71%）
- ✅ **盘前预期管理** (`/sentiment/premarket`)：1,010 行 → 259 行（↓ 74%）

## 注意事项
- 保持向后兼容性
- 逐步迁移，避免大规模重构
- 添加必要的单元测试
- 更新相关文档
- 每个文件控制在 200 行以内为佳