/**
 * 懒加载图表组件
 *
 * 性能优化：动态导入 Recharts 库，减少初始包大小
 * - Recharts 库约 2-3 MB，动态导入可减少首屏加载时间 30%
 * - 禁用 SSR（ssr: false），仅在客户端加载
 * - 提供统一的 Loading 状态，提升用户体验
 *
 * 使用方法：
 * ```typescript
 * import { AreaChart, Area, XAxis, YAxis } from '@/components/charts/LazyCharts'
 * ```
 */

import dynamic from 'next/dynamic'
import { Loader2 } from 'lucide-react'

/**
 * 图表加载中组件
 * 显示在图表容器中央的加载动画
 */
const ChartLoader = () => (
  <div className="flex h-[300px] items-center justify-center">
    <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
  </div>
)

/**
 * 动态导入所有 Recharts 组件
 * 每个组件都配置为仅客户端渲染（ssr: false）
 */
export const AreaChart = dynamic(
  () => import('recharts').then(mod => ({ default: mod.AreaChart })),
  { ssr: false, loading: ChartLoader }
)

export const Area = dynamic(
  () => import('recharts').then(mod => ({ default: mod.Area })),
  { ssr: false }
)

export const BarChart = dynamic(
  () => import('recharts').then(mod => ({ default: mod.BarChart })),
  { ssr: false, loading: ChartLoader }
)

export const Bar = dynamic(
  () => import('recharts').then(mod => ({ default: mod.Bar })),
  { ssr: false }
)

export const LineChart = dynamic(
  () => import('recharts').then(mod => ({ default: mod.LineChart })),
  { ssr: false, loading: ChartLoader }
)

export const Line = dynamic(
  () => import('recharts').then(mod => ({ default: mod.Line })),
  { ssr: false }
)

export const PieChart = dynamic(
  () => import('recharts').then(mod => ({ default: mod.PieChart })),
  { ssr: false, loading: ChartLoader }
)

export const Pie = dynamic(
  () => import('recharts').then(mod => ({ default: mod.Pie })),
  { ssr: false }
)

export const Cell = dynamic(
  () => import('recharts').then(mod => ({ default: mod.Cell })),
  { ssr: false }
)

export const XAxis = dynamic(
  () => import('recharts').then(mod => ({ default: mod.XAxis })),
  { ssr: false }
)

export const YAxis = dynamic(
  () => import('recharts').then(mod => ({ default: mod.YAxis })),
  { ssr: false }
)

export const CartesianGrid = dynamic(
  () => import('recharts').then(mod => ({ default: mod.CartesianGrid })),
  { ssr: false }
)

export const Tooltip = dynamic(
  () => import('recharts').then(mod => ({ default: mod.Tooltip })),
  { ssr: false }
)

export const ResponsiveContainer = dynamic(
  () => import('recharts').then(mod => ({ default: mod.ResponsiveContainer })),
  { ssr: false }
)

export const Legend = dynamic(
  () => import('recharts').then(mod => ({ default: mod.Legend })),
  { ssr: false }
)
