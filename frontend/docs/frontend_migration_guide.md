# Frontend 适配 Backend v4.0 迁移指南

**文档版本**: v1.0.0
**创建日期**: 2026-02-09
**适用版本**: Frontend v1.0.0 → v2.0.0 (适配 Backend v4.0.0)
**预计工作量**: 6-7 个工作日

---

## 📋 目录

- [迁移概述](#迁移概述)
- [核心问题总结](#核心问题总结)
- [详细差异分析](#详细差异分析)
- [必需的更新清单](#必需的更新清单)
- [实施计划](#实施计划)
- [测试要点](#测试要点)
- [风险和注意事项](#风险和注意事项)

---

## 迁移概述

### 背景

Backend 在 v4.0.0 版本完成了重大架构升级（Core v6.0 适配），核心变化：

1. ❌ **移除 Three Layer 架构**
   - 删除了所有 `/api/three-layer/*` 端点
   - 返回 `410 Gone` 状态码

2. ✅ **引入统一策略系统**
   - 预定义策略（Predefined Strategies）
   - 配置驱动策略（Config-based Strategies）
   - 动态代码策略（Dynamic Code Strategies）

3. ✅ **新增统一回测接口**
   - `/api/backtest` 支持所有策略类型
   - 更简洁的请求参数结构

### 迁移目标

- 移除/重构三层架构相关代码（558 行 + 7 个组件）
- 集成新的策略配置和动态策略 API（25+ 个新方法）
- 重构回测页面，支持三种策略类型
- 新增策略管理页面（2 个新页面）

### 影响范围

| 影响项 | 详情 | 优先级 |
|-------|------|--------|
| **API 客户端** | 需新增 25+ 个方法 | **P0** |
| **类型定义** | 需新增 4+ 个核心类型 | **P0** |
| **页面路由** | 2 个页面失效，需新增 2 个页面 | **P0** |
| **组件库** | 7 个组件废弃，需新增 5+ 个组件 | **P1** |
| **测试用例** | 需更新 API 和组件测试 | **P1** |

---

## 核心问题总结

### ❌ 已废弃的 API（立即失效）

| Frontend 调用 | Backend 状态 | 影响页面 |
|--------------|-------------|---------|
| `threeLayerApi.getSelectors()` | ❌ 已移除 (410) | `/backtest/three-layer` |
| `threeLayerApi.getEntries()` | ❌ 已移除 (410) | `/backtest/three-layer` |
| `threeLayerApi.getExits()` | ❌ 已移除 (410) | `/backtest/three-layer` |
| `threeLayerApi.validateStrategy()` | ❌ 已移除 (410) | `/backtest/three-layer` |
| `threeLayerApi.runBacktest()` | ❌ 已移除 (410) | `/backtest/three-layer` |

### 📁 受影响的文件

#### 需要删除的文件
- `src/lib/three-layer-api.ts` (403 行)
- `src/lib/three-layer-types.ts` (155 行)
- `src/components/three-layer/` (7 个组件，约 800+ 行)

#### 需要重构的文件
- `src/app/backtest/three-layer/page.tsx`
- `src/app/backtest/page.tsx`
- `src/lib/api-client.ts`

#### 需要新增的文件
- `src/types/strategy.ts`
- `src/app/strategies/configs/page.tsx`
- `src/app/strategies/dynamic/page.tsx`
- `src/components/strategies/*` (5+ 个新组件)

---

## 详细差异分析

### 1. API 端点差异

#### Backend 新增 API（Frontend 未使用）

##### 策略配置 API

| 端点 | 方法 | 功能 | Frontend 状态 |
|-----|------|------|--------------|
| `/api/strategy-configs/types` | GET | 获取可用策略类型 | ❌ 未集成 |
| `/api/strategy-configs` | POST | 创建策略配置 | ❌ 未集成 |
| `/api/strategy-configs` | GET | 获取配置列表 | ❌ 未集成 |
| `/api/strategy-configs/{id}` | GET | 获取配置详情 | ❌ 未集成 |
| `/api/strategy-configs/{id}` | PUT | 更新配置 | ❌ 未集成 |
| `/api/strategy-configs/{id}` | DELETE | 删除配置 | ❌ 未集成 |
| `/api/strategy-configs/{id}/test` | POST | 测试配置 | ❌ 未集成 |
| `/api/strategy-configs/validate` | POST | 验证配置参数 | ❌ 未集成 |

##### 动态策略 API

| 端点 | 方法 | 功能 | Frontend 状态 |
|-----|------|------|--------------|
| `/api/dynamic-strategies` | POST | 创建动态策略 | ❌ 未集成 |
| `/api/dynamic-strategies` | GET | 获取动态策略列表 | ❌ 未集成 |
| `/api/dynamic-strategies/{id}` | GET | 获取动态策略详情 | ❌ 未集成 |
| `/api/dynamic-strategies/{id}` | PUT | 更新动态策略 | ❌ 未集成 |
| `/api/dynamic-strategies/{id}` | DELETE | 删除动态策略 | ❌ 未集成 |
| `/api/dynamic-strategies/{id}/code` | GET | 获取策略代码 | ❌ 未集成 |
| `/api/dynamic-strategies/{id}/test` | POST | 测试动态策略 | ❌ 未集成 |
| `/api/dynamic-strategies/{id}/validate` | POST | 验证策略代码 | ❌ 未集成 |
| `/api/dynamic-strategies/statistics` | GET | 获取策略统计信息 | ❌ 未集成 |

##### 统一回测 API

| 端点 | 方法 | 功能 | Frontend 状态 |
|-----|------|------|--------------|
| `/api/backtest` | POST | 统一回测接口（支持三种策略类型） | ⚠️ 部分集成 |

### 2. 回测 API 参数变化

#### 旧方式（Three Layer，已废弃）❌

```typescript
// src/lib/three-layer-api.ts
await threeLayerApi.runBacktest({
  selector: {
    id: 'momentum',
    params: { lookback_period: 20, top_n: 50 }
  },
  entry: {
    id: 'immediate',
    params: {}
  },
  exit: {
    id: 'fixed_stop_loss',
    params: { stop_loss_pct: 0.05, take_profit_pct: 0.10 }
  },
  stock_pool: ['000001.SZ', '600000.SH'],
  start_date: '2023-01-01',
  end_date: '2023-12-31',
  initial_capital: 1000000
})
```

#### 新方式（统一回测接口）✅

**方式 1: 预定义策略**

```typescript
await apiClient.runUnifiedBacktest({
  strategy_type: 'predefined',
  strategy_name: 'momentum',
  strategy_config: {
    lookback_period: 20,
    threshold: 0.10,
    top_n: 50
  },
  stock_pool: ['000001.SZ', '600000.SH'],
  start_date: '2023-01-01',
  end_date: '2023-12-31',
  initial_capital: 1000000
})
```

**方式 2: 配置驱动策略**

```typescript
// 1. 先创建策略配置
const configResult = await apiClient.createStrategyConfig({
  strategy_type: 'momentum',
  name: '我的动量策略',
  config: {
    lookback_period: 20,
    threshold: 0.10,
    top_n: 50
  },
  description: '优化后的动量策略'
})

// 2. 使用配置 ID 运行回测
await apiClient.runUnifiedBacktest({
  strategy_type: 'config',
  strategy_id: configResult.data.config_id,
  stock_pool: ['000001.SZ', '600000.SH'],
  start_date: '2023-01-01',
  end_date: '2023-12-31',
  initial_capital: 1000000
})
```

**方式 3: 动态代码策略**

```typescript
// 1. 创建动态策略
const strategyResult = await apiClient.createDynamicStrategy({
  strategy_name: 'my_custom_strategy',
  display_name: '我的自定义策略',
  class_name: 'MyCustomStrategy',
  generated_code: `
from core.strategies.base_strategy import BaseStrategy

class MyCustomStrategy(BaseStrategy):
    def generate_signals(self, prices, features=None, volumes=None, **kwargs):
        # 自定义逻辑
        pass
  `,
  description: '基于特定指标的自定义策略'
})

// 2. 使用动态策略运行回测
await apiClient.runUnifiedBacktest({
  strategy_type: 'dynamic',
  strategy_id: strategyResult.data.strategy_id,
  stock_pool: ['000001.SZ', '600000.SH'],
  start_date: '2023-01-01',
  end_date: '2023-12-31',
  initial_capital: 1000000
})
```

### 3. 数据类型差异

#### Frontend 缺少的类型定义

需要新增到 `src/types/strategy.ts`:

```typescript
// 策略类型元数据
export interface StrategyTypeMeta {
  type: string
  name: string
  description: string
  category?: string
  risk_level?: string
  default_params: Record<string, any>
  param_schema: {
    [key: string]: {
      type: 'integer' | 'float' | 'boolean' | 'string' | 'select'
      min?: number
      max?: number
      step?: number
      options?: Array<{ value: any; label: string }>
      description?: string
      default: any
    }
  }
}

// 策略配置
export interface StrategyConfig {
  id: number
  strategy_type: string
  name: string
  description?: string
  config: Record<string, any>
  is_active: boolean
  created_at: string
  updated_at: string
  created_by?: string
  tags?: string[]
}

// 动态策略
export interface DynamicStrategy {
  id: number
  strategy_name: string
  display_name: string
  class_name: string
  description?: string
  generated_code: string
  code_hash?: string
  validation_status: 'pending' | 'passed' | 'failed' | 'warning'
  validation_errors?: Array<{ type: string; message: string }>
  validation_warnings?: Array<{ type: string; message: string }>
  test_status?: 'untested' | 'passed' | 'failed'
  test_results?: any
  is_enabled: boolean
  created_at: string
  updated_at: string
  created_by?: string
  version?: number
  parent_id?: number
}

// 统一回测请求
export interface BacktestRequest {
  strategy_type: 'predefined' | 'config' | 'dynamic'
  strategy_name?: string
  strategy_id?: number
  strategy_config?: Record<string, any>
  stock_pool: string[]
  start_date: string
  end_date: string
  initial_capital?: number
  rebalance_freq?: 'D' | 'W' | 'M'
}

// 策略执行记录
export interface StrategyExecution {
  id: number
  strategy_id: number
  execution_type: 'backtest' | 'live_trading' | 'paper_trading'
  execution_params: any
  status: 'pending' | 'running' | 'completed' | 'failed'
  result?: any
  metrics?: any
  error_message?: string
  execution_duration_ms?: number
  started_at?: string
  completed_at?: string
  created_at: string
}
```

---

## 必需的更新清单

### P0 - 紧急（立即失效，1-2 天）

#### ✅ 任务 1: 更新 API 客户端

**文件**: `src/lib/api-client.ts`

需要新增以下方法：

```typescript
class ApiClient {
  // ========== 策略配置 API ==========

  async getStrategyTypes(): Promise<ApiResponse<StrategyTypeMeta[]>> {
    const response = await axiosInstance.get('/api/strategy-configs/types')
    return response.data
  }

  async createStrategyConfig(data: {
    strategy_type: string
    name: string
    config: Record<string, any>
    description?: string
  }): Promise<ApiResponse<{ config_id: number }>> {
    const response = await axiosInstance.post('/api/strategy-configs', data)
    return response.data
  }

  async getStrategyConfigs(params?: {
    strategy_type?: string
    is_active?: boolean
    page?: number
    page_size?: number
  }): Promise<ApiResponse<PaginatedResponse<StrategyConfig>>> {
    const response = await axiosInstance.get('/api/strategy-configs', { params })
    return response.data
  }

  async getStrategyConfig(id: number): Promise<ApiResponse<StrategyConfig>> {
    const response = await axiosInstance.get(`/api/strategy-configs/${id}`)
    return response.data
  }

  async updateStrategyConfig(id: number, data: {
    name?: string
    config?: Record<string, any>
    description?: string
    is_active?: boolean
  }): Promise<ApiResponse<{ config_id: number }>> {
    const response = await axiosInstance.put(`/api/strategy-configs/${id}`, data)
    return response.data
  }

  async deleteStrategyConfig(id: number): Promise<ApiResponse<void>> {
    const response = await axiosInstance.delete(`/api/strategy-configs/${id}`)
    return response.data
  }

  async testStrategyConfig(id: number): Promise<ApiResponse<{
    success: boolean
    message: string
  }>> {
    const response = await axiosInstance.post(`/api/strategy-configs/${id}/test`)
    return response.data
  }

  async validateStrategyConfig(data: {
    strategy_type: string
    config: Record<string, any>
  }): Promise<ApiResponse<{
    is_valid: boolean
    errors: string[]
    warnings: string[]
  }>> {
    const response = await axiosInstance.post('/api/strategy-configs/validate', data)
    return response.data
  }

  // ========== 动态策略 API ==========

  async createDynamicStrategy(data: {
    strategy_name: string
    display_name: string
    class_name: string
    generated_code: string
    description?: string
  }): Promise<ApiResponse<{ strategy_id: number }>> {
    const response = await axiosInstance.post('/api/dynamic-strategies', data)
    return response.data
  }

  async getDynamicStrategies(params?: {
    validation_status?: string
    is_enabled?: boolean
    page?: number
    page_size?: number
  }): Promise<ApiResponse<PaginatedResponse<DynamicStrategy>>> {
    const response = await axiosInstance.get('/api/dynamic-strategies', { params })
    return response.data
  }

  async getDynamicStrategy(id: number): Promise<ApiResponse<DynamicStrategy>> {
    const response = await axiosInstance.get(`/api/dynamic-strategies/${id}`)
    return response.data
  }

  async getDynamicStrategyCode(id: number): Promise<ApiResponse<{
    strategy_name: string
    code: string
  }>> {
    const response = await axiosInstance.get(`/api/dynamic-strategies/${id}/code`)
    return response.data
  }

  async updateDynamicStrategy(id: number, data: {
    display_name?: string
    generated_code?: string
    description?: string
    is_enabled?: boolean
  }): Promise<ApiResponse<{ strategy_id: number }>> {
    const response = await axiosInstance.put(`/api/dynamic-strategies/${id}`, data)
    return response.data
  }

  async deleteDynamicStrategy(id: number): Promise<ApiResponse<void>> {
    const response = await axiosInstance.delete(`/api/dynamic-strategies/${id}`)
    return response.data
  }

  async testDynamicStrategy(id: number): Promise<ApiResponse<{
    success: boolean
    message: string
  }>> {
    const response = await axiosInstance.post(`/api/dynamic-strategies/${id}/test`)
    return response.data
  }

  async validateDynamicStrategy(id: number): Promise<ApiResponse<{
    is_valid: boolean
    errors: string[]
    warnings: string[]
  }>> {
    const response = await axiosInstance.post(`/api/dynamic-strategies/${id}/validate`)
    return response.data
  }

  // ========== 统一回测 API ==========

  async runUnifiedBacktest(params: BacktestRequest): Promise<ApiResponse<any>> {
    const response = await axiosInstance.post('/api/backtest', params)
    return response.data
  }

  // 向后兼容：标记旧方法为废弃
  /** @deprecated 使用 runUnifiedBacktest 代替 */
  async runBacktest(params: {
    symbols: string | string[]
    start_date: string
    end_date: string
    initial_cash?: number
    strategy_id?: string
    strategy_params?: Record<string, any>
  }): Promise<ApiResponse<any>> {
    // 转换为新格式
    return this.runUnifiedBacktest({
      strategy_type: 'predefined',
      strategy_name: params.strategy_id || 'momentum',
      strategy_config: params.strategy_params || {},
      stock_pool: Array.isArray(params.symbols) ? params.symbols : [params.symbols],
      start_date: params.start_date,
      end_date: params.end_date,
      initial_capital: params.initial_cash
    })
  }
}
```

#### ✅ 任务 2: 新增类型定义

**新建文件**: `src/types/strategy.ts`

将上述"数据类型差异"部分的类型定义复制到此文件。

**更新文件**: `src/types/index.ts`

```typescript
export * from './stock'
export * from './strategy'
```

#### ✅ 任务 3: 临时禁用三层架构页面

**文件**: `src/app/backtest/three-layer/page.tsx`

```typescript
import { Metadata } from 'next'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { AlertCircle, ArrowRight } from 'lucide-react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'

export const metadata: Metadata = {
  title: '三层架构回测（已升级） | Stock Analysis',
  description: '此功能已升级为新的统一策略系统',
}

export default function ThreeLayerBacktestPage() {
  return (
    <div className="container mx-auto py-12 px-4 max-w-4xl">
      <Alert variant="destructive" className="mb-6">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>功能已升级</AlertTitle>
        <AlertDescription>
          三层架构回测功能已升级为更强大的统一策略系统，支持预定义策略、配置驱动策略和动态代码策略。
        </AlertDescription>
      </Alert>

      <div className="space-y-6 bg-card rounded-lg border p-6">
        <h1 className="text-3xl font-bold">策略系统升级说明</h1>

        <div className="space-y-4">
          <p className="text-muted-foreground">
            Backend v4.0 引入了全新的统一策略系统，提供更灵活、更强大的策略管理能力。
          </p>

          <div className="space-y-3">
            <h3 className="font-semibold text-lg">新功能亮点</h3>
            <ul className="list-disc list-inside space-y-2 text-muted-foreground">
              <li><strong>预定义策略</strong>: 开箱即用的经典策略（动量、均值回归、多因子）</li>
              <li><strong>配置驱动策略</strong>: 保存和复用自定义参数配置</li>
              <li><strong>动态代码策略</strong>: 编写完全自定义的策略代码</li>
              <li><strong>统一回测接口</strong>: 所有策略类型使用相同的回测流程</li>
            </ul>
          </div>

          <div className="space-y-3">
            <h3 className="font-semibold text-lg">迁移指南</h3>
            <p className="text-muted-foreground">
              原有的三层架构（选股器 + 入场策略 + 退出策略）已整合为统一的策略配置。
              您可以使用预定义策略快速开始，或创建自定义策略配置。
            </p>
          </div>

          <div className="flex gap-4 pt-4">
            <Button asChild>
              <Link href="/backtest">
                前往新版回测页面 <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link href="/strategies">
                查看策略中心
              </Link>
            </Button>
          </div>
        </div>
      </div>

      <div className="mt-8 p-4 bg-muted rounded-lg">
        <h3 className="font-semibold mb-2">需要帮助？</h3>
        <p className="text-sm text-muted-foreground">
          查看 <Link href="/docs/migration" className="text-primary underline">迁移指南</Link> 了解详细的升级说明和示例代码。
        </p>
      </div>
    </div>
  )
}
```

---

### P1 - 高优先级（核心功能，2-3 天）

#### ✅ 任务 4: 重构回测页面

**文件**: `src/app/backtest/page.tsx`

```typescript
'use client'

import { useState, useEffect } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useToast } from '@/hooks/use-toast'
import { apiClient } from '@/lib/api-client'
import type { StrategyTypeMeta, StrategyConfig, DynamicStrategy, BacktestRequest } from '@/types/strategy'
import { StrategyConfigEditor } from '@/components/strategies/StrategyConfigEditor'
import { StockPoolSelector } from '@/components/backtest/StockPoolSelector'
import { DateRangeSelector } from '@/components/backtest/DateRangeSelector'
import { BacktestResultView } from '@/components/backtest/BacktestResultView'
import { Loader2 } from 'lucide-react'

export default function BacktestPage() {
  const [strategySource, setStrategySource] = useState<'predefined' | 'config' | 'dynamic'>('predefined')
  const [strategyTypes, setStrategyTypes] = useState<StrategyTypeMeta[]>([])
  const [strategyConfigs, setStrategyConfigs] = useState<StrategyConfig[]>([])
  const [dynamicStrategies, setDynamicStrategies] = useState<DynamicStrategy[]>([])

  const [selectedStrategyType, setSelectedStrategyType] = useState<string>('')
  const [selectedConfigId, setSelectedConfigId] = useState<number | undefined>()
  const [selectedDynamicId, setSelectedDynamicId] = useState<number | undefined>()
  const [strategyConfig, setStrategyConfig] = useState<Record<string, any>>({})

  const [stockPool, setStockPool] = useState<string[]>([])
  const [dateRange, setDateRange] = useState({ start: '', end: '' })
  const [initialCapital, setInitialCapital] = useState(1000000)

  const [isRunning, setIsRunning] = useState(false)
  const [result, setResult] = useState<any>(null)

  const { toast } = useToast()

  // 加载策略类型
  useEffect(() => {
    loadStrategyTypes()
  }, [])

  // 根据策略来源加载数据
  useEffect(() => {
    if (strategySource === 'config') {
      loadStrategyConfigs()
    } else if (strategySource === 'dynamic') {
      loadDynamicStrategies()
    }
  }, [strategySource])

  const loadStrategyTypes = async () => {
    try {
      const response = await apiClient.getStrategyTypes()
      if (response.success && response.data) {
        setStrategyTypes(response.data)
        if (response.data.length > 0) {
          setSelectedStrategyType(response.data[0].type)
          setStrategyConfig(response.data[0].default_params)
        }
      }
    } catch (error) {
      toast({
        title: '加载失败',
        description: '无法加载策略类型列表',
        variant: 'destructive'
      })
    }
  }

  const loadStrategyConfigs = async () => {
    try {
      const response = await apiClient.getStrategyConfigs({ is_active: true })
      if (response.success && response.data) {
        setStrategyConfigs(response.data.items)
      }
    } catch (error) {
      toast({
        title: '加载失败',
        description: '无法加载策略配置列表',
        variant: 'destructive'
      })
    }
  }

  const loadDynamicStrategies = async () => {
    try {
      const response = await apiClient.getDynamicStrategies({ is_enabled: true })
      if (response.success && response.data) {
        setDynamicStrategies(response.data.items)
      }
    } catch (error) {
      toast({
        title: '加载失败',
        description: '无法加载动态策略列表',
        variant: 'destructive'
      })
    }
  }

  const handleRunBacktest = async () => {
    // 验证参数
    if (stockPool.length === 0) {
      toast({
        title: '参数错误',
        description: '请至少选择一只股票',
        variant: 'destructive'
      })
      return
    }

    if (!dateRange.start || !dateRange.end) {
      toast({
        title: '参数错误',
        description: '请选择回测日期范围',
        variant: 'destructive'
      })
      return
    }

    // 构建请求参数
    const request: BacktestRequest = {
      strategy_type: strategySource,
      stock_pool: stockPool,
      start_date: dateRange.start,
      end_date: dateRange.end,
      initial_capital: initialCapital
    }

    if (strategySource === 'predefined') {
      request.strategy_name = selectedStrategyType
      request.strategy_config = strategyConfig
    } else if (strategySource === 'config') {
      request.strategy_id = selectedConfigId
    } else if (strategySource === 'dynamic') {
      request.strategy_id = selectedDynamicId
    }

    // 运行回测
    setIsRunning(true)
    try {
      const response = await apiClient.runUnifiedBacktest(request)
      if (response.success) {
        setResult(response.data)
        toast({
          title: '回测完成',
          description: '策略回测已完成，查看结果'
        })
      } else {
        toast({
          title: '回测失败',
          description: response.error || '未知错误',
          variant: 'destructive'
        })
      }
    } catch (error: any) {
      toast({
        title: '回测失败',
        description: error.message || '网络错误',
        variant: 'destructive'
      })
    } finally {
      setIsRunning(false)
    }
  }

  const currentStrategyType = strategyTypes.find(t => t.type === selectedStrategyType)

  return (
    <div className="container mx-auto py-6 px-4 max-w-7xl">
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">策略回测</h1>
          <p className="text-muted-foreground mt-2">
            选择策略类型，配置参数，运行回测分析
          </p>
        </div>

        <Tabs value={strategySource} onValueChange={(v: any) => setStrategySource(v)}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="predefined">预定义策略</TabsTrigger>
            <TabsTrigger value="config">我的配置</TabsTrigger>
            <TabsTrigger value="dynamic">动态策略</TabsTrigger>
          </TabsList>

          {/* 预定义策略 */}
          <TabsContent value="predefined" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>选择策略类型</CardTitle>
                <CardDescription>
                  选择一个预定义策略并配置参数
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Select value={selectedStrategyType} onValueChange={setSelectedStrategyType}>
                  <SelectTrigger>
                    <SelectValue placeholder="选择策略" />
                  </SelectTrigger>
                  <SelectContent>
                    {strategyTypes.map(type => (
                      <SelectItem key={type.type} value={type.type}>
                        {type.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {currentStrategyType && (
                  <div className="space-y-4">
                    <div className="p-4 bg-muted rounded-lg">
                      <p className="text-sm text-muted-foreground">
                        {currentStrategyType.description}
                      </p>
                    </div>

                    <StrategyConfigEditor
                      strategyType={selectedStrategyType}
                      config={strategyConfig}
                      schema={currentStrategyType.param_schema}
                      onChange={setStrategyConfig}
                    />
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* 策略配置 */}
          <TabsContent value="config" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>选择策略配置</CardTitle>
                <CardDescription>
                  使用之前保存的策略配置
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Select
                  value={selectedConfigId?.toString()}
                  onValueChange={(v) => setSelectedConfigId(parseInt(v))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="选择配置" />
                  </SelectTrigger>
                  <SelectContent>
                    {strategyConfigs.map(config => (
                      <SelectItem key={config.id} value={config.id.toString()}>
                        {config.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </CardContent>
            </Card>
          </TabsContent>

          {/* 动态策略 */}
          <TabsContent value="dynamic" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>选择动态策略</CardTitle>
                <CardDescription>
                  使用自定义代码策略
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Select
                  value={selectedDynamicId?.toString()}
                  onValueChange={(v) => setSelectedDynamicId(parseInt(v))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="选择策略" />
                  </SelectTrigger>
                  <SelectContent>
                    {dynamicStrategies.map(strategy => (
                      <SelectItem key={strategy.id} value={strategy.id.toString()}>
                        {strategy.display_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* 回测参数 */}
        <Card>
          <CardHeader>
            <CardTitle>回测参数</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <StockPoolSelector value={stockPool} onChange={setStockPool} />
            <DateRangeSelector value={dateRange} onChange={setDateRange} />
            <div>
              <label className="text-sm font-medium">初始资金</label>
              <input
                type="number"
                value={initialCapital}
                onChange={(e) => setInitialCapital(parseInt(e.target.value))}
                className="w-full mt-1 px-3 py-2 border rounded-md"
              />
            </div>
          </CardContent>
        </Card>

        {/* 运行回测按钮 */}
        <Button
          onClick={handleRunBacktest}
          disabled={isRunning}
          className="w-full"
          size="lg"
        >
          {isRunning && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {isRunning ? '回测中...' : '运行回测'}
        </Button>

        {/* 回测结果 */}
        {result && <BacktestResultView result={result} />}
      </div>
    </div>
  )
}
```

#### ✅ 任务 5: 新增策略管理页面

**新建文件**: `src/app/strategies/configs/page.tsx`

**新建文件**: `src/app/strategies/dynamic/page.tsx`

（详细代码见实施方案附录 A）

#### ✅ 任务 6: 新增策略相关组件

**新建目录**: `src/components/strategies/`

需要创建的组件：
- `StrategyTypeSelector.tsx` - 策略类型选择器
- `StrategyConfigEditor.tsx` - 策略配置编辑器（动态表单）
- `DynamicStrategyCodeEditor.tsx` - 代码编辑器（Monaco Editor）
- `StrategyValidationResult.tsx` - 验证结果展示
- `StrategyCard.tsx` - 策略卡片组件

（详细代码见实施方案附录 B）

---

### P2 - 中优先级（可选增强，按需实施）

#### ✅ 任务 7: AI 策略生成功能

如果 Backend 实现了 AI 策略生成 API，可新增：

**新建文件**: `src/app/strategies/ai-generator/page.tsx`

**新建组件**: `src/components/strategies/AIStrategyGenerator.tsx`

（详细说明见 Backend 文档：`backend/docs/planning/ai_strategy_generation.md`）

---

## 实施计划

### 第 1 阶段: 紧急修复（1-2 天）

**目标**: 修复三层架构 API 失效问题，避免用户报错

| 任务 | 工作量 | 负责人 | 优先级 |
|-----|--------|--------|--------|
| 更新 `api-client.ts` | 0.5 天 | 前端 | P0 |
| 新增 `types/strategy.ts` | 0.5 天 | 前端 | P0 |
| 禁用三层架构页面 | 0.5 天 | 前端 | P0 |
| 基础测试 | 0.5 天 | 测试 | P0 |

**交付物**:
- ✅ API 客户端支持新接口
- ✅ 类型定义完整
- ✅ 三层架构页面显示升级提示

### 第 2 阶段: 核心功能迁移（2-3 天）

**目标**: 实现新策略系统的核心功能

| 任务 | 工作量 | 负责人 | 优先级 |
|-----|--------|--------|--------|
| 策略配置编辑器组件 | 1 天 | 前端 | P1 |
| 重构回测页面 | 1 天 | 前端 | P1 |
| 策略配置管理页面 | 0.5 天 | 前端 | P1 |
| 动态策略管理页面 | 1 天 | 前端 | P1 |
| 集成测试 | 0.5 天 | 测试 | P1 |

**交付物**:
- ✅ 回测页面支持三种策略类型
- ✅ 策略配置 CRUD 功能
- ✅ 动态策略管理功能

### 第 3 阶段: 体验优化（1-2 天）

**目标**: 完善 UI/UX 和错误处理

| 任务 | 工作量 | 负责人 | 优先级 |
|-----|--------|--------|--------|
| UI/UX 优化 | 0.5 天 | 前端/设计 | P1 |
| 错误处理完善 | 0.5 天 | 前端 | P1 |
| 性能优化 | 0.5 天 | 前端 | P2 |
| 文档更新 | 0.5 天 | 技术写作 | P1 |
| 端到端测试 | 0.5 天 | 测试 | P1 |

**交付物**:
- ✅ 流畅的用户体验
- ✅ 完善的错误提示
- ✅ 更新的用户文档

### 第 4 阶段: 可选增强（按需实施）

| 任务 | 工作量 | 负责人 | 优先级 |
|-----|--------|--------|--------|
| AI 策略生成 UI | 2 天 | 前端 | P2 |
| 策略版本管理 | 1 天 | 前端 | P2 |
| 策略性能对比 | 1 天 | 前端 | P2 |

---

## 测试要点

### 1. API 集成测试

```typescript
// tests/api/strategy-configs.test.ts
import { apiClient } from '@/lib/api-client'

describe('Strategy Configs API', () => {
  test('获取策略类型列表', async () => {
    const response = await apiClient.getStrategyTypes()
    expect(response.success).toBe(true)
    expect(response.data).toBeInstanceOf(Array)
    expect(response.data![0]).toHaveProperty('type')
    expect(response.data![0]).toHaveProperty('default_params')
    expect(response.data![0]).toHaveProperty('param_schema')
  })

  test('创建策略配置', async () => {
    const result = await apiClient.createStrategyConfig({
      strategy_type: 'momentum',
      name: '测试动量策略',
      config: { lookback_period: 20, threshold: 0.1, top_n: 50 },
      description: '测试用配置'
    })
    expect(result.success).toBe(true)
    expect(result.data).toHaveProperty('config_id')
  })

  test('获取策略配置列表', async () => {
    const response = await apiClient.getStrategyConfigs()
    expect(response.success).toBe(true)
    expect(response.data).toHaveProperty('items')
    expect(response.data!.items).toBeInstanceOf(Array)
  })

  test('运行统一回测 - 预定义策略', async () => {
    const result = await apiClient.runUnifiedBacktest({
      strategy_type: 'predefined',
      strategy_name: 'momentum',
      strategy_config: { lookback_period: 20, threshold: 0.1, top_n: 50 },
      stock_pool: ['000001.SZ', '600000.SH'],
      start_date: '2024-01-01',
      end_date: '2024-12-31',
      initial_capital: 1000000
    })
    expect(result.success).toBe(true)
    expect(result.data).toHaveProperty('metrics')
  })

  test('运行统一回测 - 配置驱动策略', async () => {
    // 先创建配置
    const configResult = await apiClient.createStrategyConfig({
      strategy_type: 'momentum',
      name: '回测用配置',
      config: { lookback_period: 20 }
    })

    // 使用配置运行回测
    const result = await apiClient.runUnifiedBacktest({
      strategy_type: 'config',
      strategy_id: configResult.data!.config_id,
      stock_pool: ['000001.SZ'],
      start_date: '2024-01-01',
      end_date: '2024-12-31'
    })
    expect(result.success).toBe(true)
  })
})
```

### 2. 组件单元测试

```typescript
// tests/components/StrategyConfigEditor.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { StrategyConfigEditor } from '@/components/strategies/StrategyConfigEditor'

describe('StrategyConfigEditor', () => {
  const mockSchema = {
    lookback_period: {
      type: 'integer' as const,
      min: 5,
      max: 60,
      default: 20,
      description: '回看周期'
    },
    threshold: {
      type: 'float' as const,
      min: 0,
      max: 1,
      step: 0.01,
      default: 0.1,
      description: '阈值'
    },
    enabled: {
      type: 'boolean' as const,
      default: true,
      description: '是否启用'
    }
  }

  test('根据 schema 动态渲染表单', () => {
    render(
      <StrategyConfigEditor
        strategyType="momentum"
        config={{}}
        schema={mockSchema}
        onChange={() => {}}
      />
    )

    expect(screen.getByLabelText(/回看周期/)).toBeInTheDocument()
    expect(screen.getByLabelText(/阈值/)).toBeInTheDocument()
    expect(screen.getByLabelText(/是否启用/)).toBeInTheDocument()
  })

  test('数值输入受 min/max 限制', () => {
    const handleChange = jest.fn()
    render(
      <StrategyConfigEditor
        strategyType="momentum"
        config={{ lookback_period: 20 }}
        schema={mockSchema}
        onChange={handleChange}
      />
    )

    const input = screen.getByLabelText(/回看周期/) as HTMLInputElement

    // 超出最大值
    fireEvent.change(input, { target: { value: '100' } })
    expect(handleChange).not.toHaveBeenCalledWith({ lookback_period: 100 })

    // 合法值
    fireEvent.change(input, { target: { value: '30' } })
    expect(handleChange).toHaveBeenCalledWith({ lookback_period: 30 })
  })

  test('布尔值使用开关组件', () => {
    render(
      <StrategyConfigEditor
        strategyType="momentum"
        config={{ enabled: true }}
        schema={mockSchema}
        onChange={() => {}}
      />
    )

    const switchElement = screen.getByRole('switch')
    expect(switchElement).toBeInTheDocument()
    expect(switchElement).toBeChecked()
  })
})
```

### 3. 端到端测试

```typescript
// e2e/backtest.spec.ts
import { test, expect } from '@playwright/test'

test.describe('回测功能', () => {
  test('使用预定义策略运行回测', async ({ page }) => {
    await page.goto('/backtest')

    // 选择预定义策略
    await page.click('text=预定义策略')
    await page.click('[data-testid="strategy-selector"]')
    await page.click('text=动量策略')

    // 配置参数
    await page.fill('[name="lookback_period"]', '20')
    await page.fill('[name="threshold"]', '0.1')

    // 选择股票
    await page.click('[data-testid="stock-pool-selector"]')
    await page.click('text=000001.SZ')
    await page.click('text=600000.SH')

    // 选择日期
    await page.fill('[name="start_date"]', '2024-01-01')
    await page.fill('[name="end_date"]', '2024-12-31')

    // 运行回测
    await page.click('text=运行回测')

    // 等待结果
    await expect(page.locator('text=回测完成')).toBeVisible({ timeout: 60000 })

    // 验证结果展示
    await expect(page.locator('[data-testid="backtest-metrics"]')).toBeVisible()
    await expect(page.locator('text=年化收益')).toBeVisible()
    await expect(page.locator('text=夏普比率')).toBeVisible()
  })

  test('创建并使用策略配置', async ({ page }) => {
    // 创建策略配置
    await page.goto('/strategies/configs')
    await page.click('text=新建配置')

    await page.fill('[name="name"]', '我的动量策略')
    await page.click('[name="strategy_type"]')
    await page.click('text=动量策略')
    await page.fill('[name="lookback_period"]', '30')
    await page.click('text=保存')

    await expect(page.locator('text=创建成功')).toBeVisible()

    // 使用配置运行回测
    await page.goto('/backtest')
    await page.click('text=我的配置')
    await page.click('[data-testid="config-selector"]')
    await page.click('text=我的动量策略')

    // 其他回测参数...
    await page.click('text=运行回测')

    await expect(page.locator('text=回测完成')).toBeVisible({ timeout: 60000 })
  })
})
```

---

## 风险和注意事项

### 1. 向后兼容性

**问题**: 三层架构 API 已完全移除，无法平滑迁移

**解决方案**:
- ✅ 保留旧的 `runBacktest` 方法，标记为 `@deprecated`
- ✅ 内部调用新接口，减少其他页面的改动
- ✅ 在三层架构页面显示清晰的升级提示和迁移指南

### 2. 数据迁移

**问题**: 用户可能有保存的三层架构策略配置

**解决方案**:
- 如果数据量不大，提供手动迁移指南
- 如果数据量大，编写迁移脚本：
  ```typescript
  // 迁移示例：将三层配置转换为预定义策略配置
  async function migrateThreeLayerConfigs() {
    // 1. 读取旧配置（如果有保存在 localStorage）
    const oldConfigs = JSON.parse(localStorage.getItem('three_layer_configs') || '[]')

    // 2. 转换为新格式
    for (const oldConfig of oldConfigs) {
      const newConfig = {
        strategy_type: mapSelectorToStrategyType(oldConfig.selector.id),
        name: `迁移 - ${oldConfig.name}`,
        config: {
          ...oldConfig.selector.params,
          // 合并 entry/exit 参数到 config
          ...oldConfig.exit.params
        },
        description: '从三层架构自动迁移'
      }

      // 3. 创建新配置
      await apiClient.createStrategyConfig(newConfig)
    }

    // 4. 清除旧配置
    localStorage.removeItem('three_layer_configs')
  }

  function mapSelectorToStrategyType(selectorId: string): string {
    const mapping: Record<string, string> = {
      'momentum': 'momentum',
      'value': 'mean_reversion',
      'quality': 'multi_factor'
    }
    return mapping[selectorId] || 'momentum'
  }
  ```

### 3. 用户体验

**问题**: 策略选择流程变更较大，用户可能困惑

**解决方案**:
- ✅ 添加引导提示（Tooltip、帮助文档）
- ✅ 提供策略对比表，说明新旧对应关系：
  ```
  | 旧组合 | 新策略 |
  |-------|--------|
  | 动量选股器 + 立即入场 + 止损退出 | momentum 预定义策略 |
  | 价值选股器 + 立即入场 + 止损退出 | mean_reversion 预定义策略 |
  | 自定义组合 | 创建动态代码策略 |
  ```
- ✅ 添加"快速开始"视频或交互式教程

### 4. 性能优化

**问题**: Monaco Editor 体积较大（~2MB）

**解决方案**:
```typescript
// 使用动态导入
import dynamic from 'next/dynamic'

const DynamicStrategyCodeEditor = dynamic(
  () => import('@/components/strategies/DynamicStrategyCodeEditor'),
  {
    ssr: false,
    loading: () => <div>加载编辑器...</div>
  }
)
```

**问题**: 策略列表数量可能很大

**解决方案**:
- ✅ 实现分页和搜索功能
- ✅ 使用虚拟滚动（如 `react-window`）
- ✅ 添加筛选和排序功能

### 5. 安全性

**问题**: 动态代码策略存在安全风险

**解决方案**:
- ✅ 前端清晰展示代码验证结果（错误/警告）
- ✅ 添加"沙箱测试"按钮，让用户在保存前测试
- ✅ 显示安全警告：
  ```tsx
  <Alert variant="warning">
    <AlertTitle>安全提示</AlertTitle>
    <AlertDescription>
      动态代码策略会在服务器上执行。请确保代码来自可信来源，
      不要运行未经验证的代码。所有代码都会经过安全检查。
    </AlertDescription>
  </Alert>
  ```

### 6. 错误处理

**问题**: 新 API 可能返回不同的错误格式

**解决方案**:
```typescript
// 统一错误处理
async function handleApiCall<T>(
  apiCall: () => Promise<ApiResponse<T>>,
  errorMessage: string
): Promise<T | null> {
  try {
    const response = await apiCall()
    if (response.success && response.data) {
      return response.data
    } else {
      toast({
        title: '操作失败',
        description: response.error || errorMessage,
        variant: 'destructive'
      })
      return null
    }
  } catch (error: any) {
    toast({
      title: '网络错误',
      description: error.message || '无法连接到服务器',
      variant: 'destructive'
    })
    return null
  }
}
```

---

## 参考文档

### Backend 文档
- [Backend v3 → v4 迁移指南](/Volumes/MacDriver/stock-analysis/backend/docs/migration/v3_to_v4.md)
- [Backend API 参考文档](/Volumes/MacDriver/stock-analysis/backend/docs/api_reference/README.md)
- [Backend README](/Volumes/MacDriver/stock-analysis/backend/docs/README.md)

### Core 文档
- [Core v6.0 策略系统文档](/Volumes/MacDriver/stock-analysis/core/docs/architecture/strategy_system.md)
- [Core API 文档](/Volumes/MacDriver/stock-analysis/core/docs/README.md)

### 规划文档
- [AI 策略生成规划](/Volumes/MacDriver/stock-analysis/backend/docs/planning/ai_strategy_generation.md)
- [策略配置管理规划](/Volumes/MacDriver/stock-analysis/backend/docs/planning/strategy_config_management.md)

---

## 附录

### 附录 A: 页面完整代码示例

详见单独的代码文件：
- `examples/strategies-configs-page.tsx`
- `examples/strategies-dynamic-page.tsx`

### 附录 B: 组件完整代码示例

详见单独的代码文件：
- `examples/StrategyConfigEditor.tsx`
- `examples/DynamicStrategyCodeEditor.tsx`
- `examples/StrategyValidationResult.tsx`

---

## 总结

Frontend 项目需要**立即**进行更新以适配 Backend v4.0.0 的重大架构变化。

### 核心工作量

| 阶段 | 任务 | 工作量 |
|-----|------|--------|
| **P0 紧急** | API + 类型 + 禁用旧功能 | 1.5 天 |
| **P1 核心** | 组件 + 页面重构 | 3.5 天 |
| **P1 测试** | 测试和优化 | 1.5 天 |
| **总计** | P0 + P1 | **6-7 天** |

### 关键里程碑

- **Day 2**: 三层架构页面已禁用，不再报错 ✅
- **Day 4**: 回测页面支持预定义策略 ✅
- **Day 6**: 策略管理功能完整 ✅
- **Day 7**: 测试通过，可以发布 ✅

### 建议实施顺序

1. **第一阶段（1-2天）**: 紧急修复，禁用旧功能，避免用户报错
2. **第二阶段（2-3天）**: 核心功能迁移，支持新策略系统
3. **第三阶段（1-2天）**: 体验优化和全面测试

---

**文档维护**: Frontend Team
**最后更新**: 2026-02-09
**文档状态**: ✅ 已完成，可执行
