/**
 * useBreadcrumbs Hook
 *
 * @description
 * 根据当前路由自动生成面包屑数据
 *
 * @features
 * - 自动解析路由路径
 * - 支持动态路由参数
 * - 支持自定义标签映射
 * - 支持图标配置
 */

import { useMemo } from 'react'
import { usePathname } from 'next/navigation'
import type { BreadcrumbItem } from '@/components/ui/breadcrumb'
import {
  Settings,
  Database,
  FileText,
  Activity,
  Users,
  Tag,
  TrendingUp,
  LineChart,
  Sparkles,
  Zap,
  Clock,
  ScrollText,
  Brain,
  Bell,
  Flame,
  ArrowUpCircle,
  RefreshCw,
  PackagePlus,
  PackageMinus,
  TrendingUp as TrendingUpIcon,
  Wrench,
  UserCog,
  Shield,
  ChartBar,
  List
} from 'lucide-react'

// 路由标签映射
const routeLabelMap: Record<string, string> = {
  // 顶级路由
  'users': '用户管理',
  'stocks': '股票管理',
  'strategies': '策略管理',
  'concepts': '概念管理',
  'sentiment': '市场情绪',
  'settings': '系统设置',
  'sync': '数据同步',
  'logs': '日志管理',
  'monitoring': '系统监控',
  'profile': '个人中心',

  // 市场情绪子路由
  'data': '数据管理',
  'dragon-tiger': '龙虎榜',
  'limit-up': '涨停板池',
  'cycle': '情绪周期',
  'ai-analysis': 'AI分析',
  'premarket': '盘前预期',
  'moneyflow-hsgt': '沪深港通资金流向',
  'moneyflow': '个股资金流向（Tushare）',
  'moneyflow-mkt-dc': '大盘资金流向（DC）',
  'moneyflow-ind-dc': '板块资金流向（DC）',
  'moneyflow-stock-dc': '个股资金流向（DC）',

  // 系统设置子路由
  'system': '系统配置',
  'datasource': '数据源设置',
  'ai-config': 'AI配置',
  'prompt-templates': '提示词管理',
  'scheduler': '定时任务',
  'notification-channels': '通知渠道',

  // 数据同步子路由
  'initialize': '数据初始化',
  'new-stocks': '新股列表同步',
  'delisted-stocks': '退市列表同步',
  'realtime': '实时行情同步',

  // 日志管理子路由
  'llm-calls': 'LLM调用日志',

  // 系统监控子路由
  'performance': '性能监控',
  'notifications': '通知监控',

  // 策略管理子路由
  'new': '创建策略',
  'edit': '编辑策略',
  'review': '审核策略',
  'pending-review': '待审核策略',

  // 股票管理子路由
  'stock-concepts': '关联概念',
}

// 路由图标映射
const routeIconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  'users': Users,
  'stocks': LineChart,
  'strategies': TrendingUp,
  'concepts': Tag,
  'sentiment': Zap,
  'settings': Settings,
  'sync': Database,
  'logs': FileText,
  'monitoring': Activity,
  'profile': UserCog,

  // 子路由图标
  'data': ChartBar,
  'dragon-tiger': Flame,
  'limit-up': ArrowUpCircle,
  'cycle': TrendingUp,
  'ai-analysis': Sparkles,
  'premarket': Clock,
  'moneyflow-hsgt': TrendingUp,
  'moneyflow': Activity,
  'moneyflow-mkt-dc': LineChart,
  'moneyflow-ind-dc': ChartBar,
  'moneyflow-stock-dc': TrendingUp,
  'system': Wrench,
  'datasource': Database,
  'ai-config': Sparkles,
  'prompt-templates': FileText,
  'scheduler': Clock,
  'notification-channels': Bell,
  'initialize': RefreshCw,
  'new-stocks': PackagePlus,
  'delisted-stocks': PackageMinus,
  'realtime': TrendingUpIcon,
  'llm-calls': Brain,
  'performance': Activity,
  'notifications': Bell,
  'new': PackagePlus,
  'pending-review': List,
}

/**
 * 获取动态路由参数的显示名称
 */
async function getDynamicLabel(segment: string, prevSegment?: string): Promise<string> {
  // 这里可以根据实际需求从API获取数据
  // 目前返回占位符

  if (prevSegment === 'stocks') {
    // 股票代码
    return `股票 ${segment}`
  }

  if (prevSegment === 'strategies') {
    // 策略ID
    return `策略 #${segment}`
  }

  if (prevSegment === 'prompt-templates') {
    // 提示词模板ID
    return `模板 #${segment}`
  }

  return segment
}

export function useBreadcrumbs(): BreadcrumbItem[] {
  const pathname = usePathname()

  const breadcrumbs = useMemo(() => {
    // 移除开头的斜杠并分割路径
    const segments = pathname.split('/').filter(Boolean)

    // 如果是首页，返回空数组（首页会自动添加）
    if (segments.length === 0) {
      return []
    }

    const items: BreadcrumbItem[] = []
    let currentPath = ''

    segments.forEach((segment, index) => {
      currentPath += `/${segment}`

      // 检查是否是动态路由（通常是ID或代码）
      const isDynamic = /^[0-9a-zA-Z]{1,10}$/.test(segment) &&
                       !routeLabelMap[segment]

      let label = routeLabelMap[segment] || segment
      let icon = routeIconMap[segment]

      // 处理动态路由
      if (isDynamic && index > 0) {
        const prevSegment = segments[index - 1]
        // 这里简化处理，实际项目中可能需要从store或API获取
        if (prevSegment === 'stocks') {
          label = `${segment.toUpperCase()}`
        } else if (prevSegment === 'strategies' || prevSegment === 'prompt-templates') {
          label = `#${segment}`
        }
      }

      items.push({
        label,
        href: currentPath,
        icon,
      })
    })

    // 最后一项不需要链接
    if (items.length > 0) {
      delete items[items.length - 1].href
    }

    return items
  }, [pathname])

  return breadcrumbs
}

/**
 * 带有自定义配置的面包屑 Hook
 */
export function useCustomBreadcrumbs(customItems?: BreadcrumbItem[]): BreadcrumbItem[] {
  const autoBreadcrumbs = useBreadcrumbs()

  return useMemo(() => {
    if (!customItems || customItems.length === 0) {
      return autoBreadcrumbs
    }

    // 如果提供了自定义面包屑，使用自定义的
    return customItems
  }, [autoBreadcrumbs, customItems])
}