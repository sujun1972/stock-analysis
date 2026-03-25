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
  List,
  BarChart3,
  PieChart,
  PauseCircle,
  Wallet,
  DollarSign,
  ListOrdered,
  Building2,
  Star,
  Calendar,
  Layers,
  AlertTriangle,
  CalendarDays
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
  'boardgame': '打板专题',
  'features': '特色数据',
  'market': '行情数据',
  'financial': '财务数据',
  'reference-data': '参考数据',

  // 市场情绪子路由
  'data': '基础数据',
  'dragon-tiger': '龙虎榜',
  'limit-up': '涨停板池',
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

  // 打板专题子路由
  'top-list': '龙虎榜每日明细',
  'top-inst': '龙虎榜机构明细',
  'limit-list': '涨跌停列表',
  'limit-step': '连板天梯',
  'limit-cpt': '最强板块统计',

  // 基础数据子路由
  'stock-list': '股票列表',
  'stock-st': 'ST股票列表',
  'trade-cal': '交易日历',
  'dc-index': '东方财富概念板块',
  'dc-member': '东方财富板块成分',
  'dc-daily': '东财概念板块行情',
  'margin': '融资融券交易汇总',
  'margin-detail': '融资融券交易明细',
  'margin-secs': '融资融券标的（盘前）',
  'slb-len': '转融资交易汇总',

  // 行情数据子路由
  'daily': '股票日线数据',
  'adj-factor': '复权因子',
  'daily-basic': '每日指标',
  'stk-limit-d': '每日涨跌停价格',
  'suspend': '每日停复牌信息',
  'hsgt-top10': '沪深股通十大成交股',
  'ggt-top10': '港股通十大成交股',
  'ggt-daily': '港股通每日成交统计',
  'ggt-monthly': '港股通每月成交统计',

  // 财务数据子路由
  'income': '利润表',
  'balancesheet': '资产负债表',
  'cashflow': '现金流量表',
  'forecast': '业绩预告',
  'express': '业绩快报',
  'dividend': '分红送股',
  'fina-indicator': '财务指标',
  'fina-audit': '审计意见',
  'fina-mainbz': '主营业务构成',
  'disclosure-date': '财报披露计划',

  // 参考数据子路由
  'stk-shock': '个股异常波动',
  'stk-high-shock': '个股严重异常波动',
  'stk-alert': '交易所重点提示证券',
  'pledge-stat': '股权质押统计',
  'repurchase': '股票回购',
  'share-float': '限售股解禁',
  'block-trade': '大宗交易',
  'stk-holdernumber': '股东人数',
  'stk-holdertrade': '股东增减持',

  // 特色数据子路由
  'report-rc': '卖方盈利预测',
  'cyq-perf': '每日筹码及胜率',
  'cyq-chips': '每日筹码分布',
  'ccass-hold': '中央结算系统持股汇总',
  'ccass-hold-detail': '中央结算系统持股明细',
  'hk-hold': '北向资金持股',
  'stk-auction-o': '股票开盘集合竞价',
  'stk-auction-c': '股票收盘集合竞价',
  'stk-nineturn': '神奇九转指标',
  'stk-ah-comparison': 'AH股比价',
  'stk-surv': '机构调研表',
  'broker-recommend': '券商每月荐股',
}

// 路由图标映射（与 AdminLayout.tsx 菜单配置保持一致）
const routeIconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  // 顶级路由
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
  'boardgame': ListOrdered,   // 打板专题
  'market': TrendingUpIcon,   // 行情数据
  'financial': FileText,      // 财务数据
  'reference-data': FileText, // 参考数据
  'features': Star,           // 特色数据
  'data': Layers,             // 基础数据（默认，具体路径由 parentOverrides 覆盖）

  // 市场情绪子路由
  'ai-analysis': Sparkles,
  'premarket': Clock,

  // 系统设置子路由
  'system': Wrench,
  'datasource': Database,
  'ai-config': Sparkles,
  'prompt-templates': FileText,
  'scheduler': Clock,
  'notification-channels': Bell,

  // 日志管理子路由
  'llm-calls': Brain,
  'system-logs': ScrollText,

  // 系统监控子路由
  'performance': Activity,
  'notifications': Bell,

  // 数据同步子路由
  'initialize': RefreshCw,
  'new-stocks': PackagePlus,
  'delisted-stocks': PackageMinus,
  'realtime': RefreshCw,

  // 策略管理子路由
  'new': PackagePlus,
  'pending-review': List,

  // 打板专题子路由（对照菜单）
  'top-list': Flame,
  'top-inst': Building2,
  'limit-list': TrendingUp,
  'limit-step': TrendingUp,
  'limit-cpt': TrendingUp,
  'dc-index': BarChart3,
  'dc-member': Layers,
  'dc-daily': LineChart,

  // 基础数据子路由
  'stock-list': Database,
  'stock-st': AlertTriangle,
  'trade-cal': CalendarDays,

  // 行情数据子路由（对照菜单）
  'daily': LineChart,
  'adj-factor': Database,
  'daily-basic': BarChart3,
  'stk-limit-d': TrendingUpIcon,
  'suspend': PauseCircle,
  'hsgt-top10': TrendingUpIcon,
  'ggt-top10': TrendingUpIcon,
  'ggt-daily': TrendingUpIcon,
  'ggt-monthly': TrendingUpIcon,

  // 财务数据子路由（对照菜单）
  'income': TrendingUp,
  'balancesheet': DollarSign,
  'cashflow': Activity,
  'forecast': TrendingUp,
  'express': TrendingUp,
  'dividend': DollarSign,
  'fina-indicator': TrendingUp,
  'fina-audit': TrendingUp,
  'fina-mainbz': PieChart,
  'disclosure-date': Calendar,

  // 参考数据子路由（对照菜单）
  'stk-shock': FileText,
  'stk-high-shock': FileText,
  'stk-alert': FileText,
  'pledge-stat': TrendingUp,
  'repurchase': FileText,
  'share-float': FileText,
  'block-trade': Building2,
  'stk-holdernumber': Users,
  'stk-holdertrade': Users,

  // 特色数据子路由（对照菜单）
  'report-rc': TrendingUp,
  'cyq-perf': BarChart3,
  'cyq-chips': PieChart,
  'ccass-hold': Database,
  'ccass-hold-detail': Database,
  'hk-hold': TrendingUp,
  'stk-auction-o': Clock,
  'stk-auction-c': TrendingUp,
  'stk-nineturn': Activity,
  'stk-ah-comparison': TrendingUp,
  'stk-surv': Users,
  'broker-recommend': TrendingUpIcon,

  // 两融数据子路由（对照菜单）
  'margin': BarChart3,
  'margin-detail': FileText,
  'margin-secs': Activity,
  'slb-len': TrendingUp,

  // 资金流向子路由（对照菜单）
  'moneyflow': Activity,
  'moneyflow-stock-dc': TrendingUpIcon,
  'moneyflow-ind-dc': BarChart3,
  'moneyflow-mkt-dc': LineChart,
  'moneyflow-hsgt': TrendingUp,

  // 其他
  'dragon-tiger': Flame,
  'limit-up': ArrowUpCircle,
  'cycle': TrendingUp,
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

    // 某些页面的 URL 父级 segment 与菜单归属不一致，需要按完整 pathname 覆盖
    // 例如 /data/dc-daily 在打板专题菜单下，但 URL 首段是 data
    const parentOverrides: Record<string, { label: string; icon: React.ComponentType<{ className?: string }> }> = {
      // 两融数据下的 /data/* 页面
      '/data/margin':          { label: '两融数据', icon: Wallet },
      '/data/margin-detail':   { label: '两融数据', icon: Wallet },
      '/data/margin-secs':     { label: '两融数据', icon: Wallet },
      '/data/slb-len':         { label: '两融数据', icon: Wallet },
      // 资金流向下的 /data/* 页面
      '/data/moneyflow':          { label: '资金流向', icon: DollarSign },
      '/data/moneyflow-stock-dc': { label: '资金流向', icon: DollarSign },
      '/data/moneyflow-ind-dc':   { label: '资金流向', icon: DollarSign },
      '/data/moneyflow-mkt-dc':   { label: '资金流向', icon: DollarSign },
      '/data/moneyflow-hsgt':     { label: '资金流向', icon: DollarSign },
    }

    segments.forEach((segment, index) => {
      currentPath += `/${segment}`

      // 检查是否是动态路由（通常是ID或代码）
      const isDynamic = /^[0-9a-zA-Z]{1,10}$/.test(segment) &&
                       !routeLabelMap[segment]

      let label = routeLabelMap[segment] || segment
      let icon = routeIconMap[segment]

      // 对父级 segment（index=0）按完整 pathname 做覆盖
      if (index === 0 && parentOverrides[pathname]) {
        const override = parentOverrides[pathname]
        label = override.label
        if (override.icon) icon = override.icon
      }

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