# 三层架构回测UI组件

本目录包含三层架构回测系统的所有前端组件。

## 📁 组件清单

### 1. ParametersForm
**文件**: `ParametersForm.tsx`

动态参数表单组件，根据参数定义自动渲染对应的输入控件。

**Props**:
```typescript
interface ParametersFormProps {
  parameters: ParameterDef[]        // 参数定义数组
  values: Record<string, any>       // 当前参数值
  onChange: (values: Record<string, any>) => void  // 值变更回调
}
```

**支持的参数类型**:
- `integer`: 整数（Slider + NumberInput）
- `float`: 浮点数（Slider + NumberInput）
- `boolean`: 布尔值（Switch）
- `select`: 下拉选择（Select）
- `string`: 文本输入（Input）

**使用示例**:
```tsx
import { ParametersForm } from '@/components/three-layer'

const [params, setParams] = useState({})

<ParametersForm
  parameters={[
    {
      name: 'lookback_period',
      label: '回看周期',
      type: 'integer',
      default: 20,
      min_value: 5,
      max_value: 60,
      description: '计算动量的历史天数'
    }
  ]}
  values={params}
  onChange={setParams}
/>
```

---

### 2. ThreeLayerStrategyPanel
**文件**: `ThreeLayerStrategyPanel.tsx`

三层策略配置主面板，包含选股器、入场策略、退出策略三层配置。

**功能**:
- 自动加载可用的策略组件
- 三层策略选择和参数配置
- 回测参数设置（股票池、日期、资金等）
- 策略验证和回测执行
- 结果展示

**使用示例**:
```tsx
import { ThreeLayerStrategyPanel } from '@/components/three-layer'

// 直接使用，无需传入props
<ThreeLayerStrategyPanel />
```

**内部状态**:
```typescript
// 组件列表
selectors: SelectorInfo[]
entries: EntryInfo[]
exits: ExitInfo[]

// 选中的组件ID
selectedSelector: string
selectedEntry: string
selectedExit: string

// 各层参数
selectorParams: Record<string, any>
entryParams: Record<string, any>
exitParams: Record<string, any>

// 回测配置
stockCodes: string
startDate: string
endDate: string
rebalanceFreq: 'D' | 'W' | 'M'
initialCapital: number

// 结果
result: BacktestResult | null
```

---

### 3. BacktestResultView
**文件**: `BacktestResultView.tsx`

回测结果展示组件，包含绩效指标、净值曲线、交易记录。

**Props**:
```typescript
interface BacktestResultViewProps {
  result: BacktestResult  // 回测结果对象
}
```

**展示内容**:
1. 操作按钮（保存、分享、导出）
2. 绩效指标卡片（复用PerformanceMetrics组件）
3. 净值曲线图表（复用EquityCurveChart组件）
4. 交易统计（总次数、胜率、买卖次数）
5. 交易记录表格（支持展开/收起）

**使用示例**:
```tsx
import { BacktestResultView } from '@/components/three-layer'

const [result, setResult] = useState<BacktestResult | null>(null)

{result && result.data && (
  <BacktestResultView result={result} />
)}
```

---

## 🚀 快速开始

### 1. 在页面中使用

最简单的方式是直接使用 `ThreeLayerStrategyPanel`：

```tsx
// app/backtest/three-layer/page.tsx
import { ThreeLayerStrategyPanel } from '@/components/three-layer'

export default function ThreeLayerBacktestPage() {
  return (
    <div className="container">
      <h1>三层架构回测</h1>
      <ThreeLayerStrategyPanel />
    </div>
  )
}
```

### 2. 自定义使用

如果需要更细粒度的控制，可以单独使用各个子组件：

```tsx
import { useState, useEffect } from 'react'
import { threeLayerApi } from '@/lib/three-layer'
import { ParametersForm, BacktestResultView } from '@/components/three-layer'

export default function CustomBacktest() {
  const [selectors, setSelectors] = useState([])
  const [selectedId, setSelectedId] = useState('')
  const [params, setParams] = useState({})
  const [result, setResult] = useState(null)

  // 加载选股器列表
  useEffect(() => {
    threeLayerApi.getSelectors().then(setSelectors)
  }, [])

  // 获取选中选股器的参数定义
  const selectedSelector = selectors.find(s => s.id === selectedId)

  return (
    <div>
      {/* 选择选股器 */}
      <select value={selectedId} onChange={e => setSelectedId(e.target.value)}>
        {selectors.map(s => (
          <option key={s.id} value={s.id}>{s.name}</option>
        ))}
      </select>

      {/* 参数表单 */}
      {selectedSelector && (
        <ParametersForm
          parameters={selectedSelector.parameters}
          values={params}
          onChange={setParams}
        />
      )}

      {/* 结果展示 */}
      {result && <BacktestResultView result={result} />}
    </div>
  )
}
```

---

## 🎨 样式定制

所有组件使用 Tailwind CSS 和 Radix UI，支持暗色模式。

### 主题色
- Primary: 主要操作按钮、选中状态
- Muted: 辅助信息、说明文字
- Destructive: 错误提示

### 响应式断点
- `md:`: 768px+（平板及以上）
- `lg:`: 1024px+（桌面）

---

## 📦 依赖

### UI组件
- `@radix-ui/react-select` - 下拉选择
- `@radix-ui/react-switch` - 开关按钮
- `@radix-ui/react-slider` - 滑块
- `@radix-ui/react-dialog` - 对话框
- `lucide-react` - 图标库

### 数据可视化
- `echarts` - 图表库（通过EquityCurveChart组件）

### API通信
- `axios` - HTTP客户端（已封装在three-layer-api.ts）

---

## 🔌 API集成

组件通过 `@/lib/three-layer-api` 与后端通信：

```typescript
import { threeLayerApi } from '@/lib/three-layer'

// 获取选股器列表
const selectors = await threeLayerApi.getSelectors()

// 获取入场策略列表
const entries = await threeLayerApi.getEntries()

// 获取退出策略列表
const exits = await threeLayerApi.getExits()

// 并行获取所有组件
const { selectors, entries, exits } = await threeLayerApi.getAllComponents()

// 验证策略配置
const validation = await threeLayerApi.validateStrategy(config)

// 运行回测
const result = await threeLayerApi.runBacktest(config)
```

---

## 🧪 测试

### 单元测试
```bash
npm test
```

### E2E测试
```bash
# 启动开发服务器
npm run dev

# 访问页面
open http://localhost:3000/backtest/three-layer
```

---

## 📝 类型定义

所有类型定义位于 `@/lib/three-layer-types.ts`：

- `SelectorInfo` - 选股器信息
- `EntryInfo` - 入场策略信息
- `ExitInfo` - 退出策略信息
- `ParameterDef` - 参数定义
- `StrategyConfig` - 策略配置
- `BacktestResult` - 回测结果
- `ValidationResult` - 验证结果

---

## 🐛 故障排除

### 1. 组件列表加载失败
**原因**: 后端服务未启动或API地址配置错误

**解决**:
```bash
# 检查环境变量
cat .env.local

# 应包含
NEXT_PUBLIC_API_URL=http://localhost:8000

# 检查后端服务
curl http://localhost:8000/api/three-layer/selectors
```

### 2. 参数表单不显示
**原因**: 未选择策略或参数定义为空数组

**解决**: 确保已选择策略且该策略有参数定义

### 3. 回测失败
**原因**: 参数验证失败或后端错误

**解决**:
1. 点击"验证策略"按钮检查配置
2. 查看浏览器控制台错误信息
3. 查看后端日志

---

## 🤝 贡献

欢迎提交问题和改进建议！

---

**维护者**: Claude Code
**最后更新**: 2026-02-07
