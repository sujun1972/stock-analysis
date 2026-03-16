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

## 注意事项
- 保持向后兼容性
- 逐步迁移，避免大规模重构
- 添加必要的单元测试
- 更新相关文档