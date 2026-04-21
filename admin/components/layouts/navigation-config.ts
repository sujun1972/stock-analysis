import {
  type LucideIcon,
  Settings,
  Database,
  FileText,
  Activity,
  LayoutDashboard,
  Users,
  TrendingUp,
  LineChart,
  Sparkles,
  Zap,
  Clock,
  ScrollText,
  Newspaper,
  Tv,
  Brain,
  Bell,
  Flame,
  PackagePlus,
  Wrench,
  DollarSign,
  BarChart3,
  PieChart,
  PauseCircle,
  Wallet,
  ListOrdered,
  Building2,
  Star,
  Calendar,
  Layers,
  AlertTriangle,
  CalendarDays
} from 'lucide-react'

export interface NavItem {
  name: string
  href?: string
  icon: LucideIcon
  children?: NavItem[]
}

export const navItems: NavItem[] = [
  {
    name: '控制台',
    href: '/',
    icon: LayoutDashboard
  },
  {
    name: '基础数据',
    icon: Layers,
    children: [
      {
        name: '股票列表',
        href: '/data/stock-list',
        icon: Database
      },
      {
        name: '交易日历',
        href: '/data/trade-cal',
        icon: CalendarDays
      },
      {
        name: 'ST股票列表',
        href: '/data/stock-st',
        icon: AlertTriangle
      },
      {
        name: 'IPO新股列表',
        href: '/sync/new-stocks',
        icon: PackagePlus
      }
    ]
  },
  {
    name: '行情数据',
    href: '/market',
    icon: TrendingUp,
    children: [
      {
        name: '股票日线数据',
        href: '/market/daily',
        icon: LineChart
      },
      {
        name: '复权因子',
        href: '/market/adj-factor',
        icon: Database
      },
      {
        name: '每日指标',
        href: '/market/daily-basic',
        icon: BarChart3
      },
      {
        name: '每日涨跌停价格',
        href: '/market/stk-limit-d',
        icon: TrendingUp
      },
      {
        name: '每日停复牘信息',
        href: '/market/suspend',
        icon: PauseCircle
      },
      {
        name: '沪深股通十大成交股',
        href: '/market/hsgt-top10',
        icon: TrendingUp
      },
      {
        name: '港股通十大成交股',
        href: '/market/ggt-top10',
        icon: TrendingUp
      },
      {
        name: '港股通每日成交统计',
        href: '/market/ggt-daily',
        icon: TrendingUp
      },
      {
        name: '港股通每月成交统计',
        href: '/market/ggt-monthly',
        icon: TrendingUp
      }
    ]
  },
  {
    name: '财务数据',
    href: '/financial',
    icon: FileText,
    children: [
      {
        name: '利润表',
        href: '/financial/income',
        icon: TrendingUp
      },
      {
        name: '资产负债表',
        href: '/financial/balancesheet',
        icon: DollarSign
      },
      {
        name: '现金流量表',
        href: '/financial/cashflow',
        icon: Activity
      },
      {
        name: '业绩预告',
        href: '/financial/forecast',
        icon: TrendingUp
      },
      {
        name: '业绩快报',
        href: '/financial/express',
        icon: TrendingUp
      },
      {
        name: '分红送股',
        href: '/financial/dividend',
        icon: DollarSign
      },
      {
        name: '财务指标',
        href: '/financial/fina-indicator',
        icon: TrendingUp
      },
      {
        name: '审计意见',
        href: '/financial/fina-audit',
        icon: TrendingUp
      },
      {
        name: '主营业务构成',
        href: '/financial/fina-mainbz',
        icon: PieChart
      },
      {
        name: '财报披露计划',
        href: '/financial/disclosure-date',
        icon: Calendar
      }
    ]
  },
  {
    name: '参考数据',
    href: '/reference-data',
    icon: FileText,
    children: [
      {
        name: '个股异常波动',
        href: '/reference-data/stk-shock',
        icon: FileText
      },
      {
        name: '个股严重异常波动',
        href: '/reference-data/stk-high-shock',
        icon: FileText
      },
      {
        name: '交易所重点提示证券',
        href: '/reference-data/stk-alert',
        icon: FileText
      },
      {
        name: '股权质押统计',
        href: '/reference-data/pledge-stat',
        icon: TrendingUp
      },
      {
        name: '股票回购',
        href: '/reference-data/repurchase',
        icon: FileText
      },
      {
        name: '限售股解禁',
        href: '/reference-data/share-float',
        icon: FileText
      },
      {
        name: '大宗交易',
        href: '/reference-data/block-trade',
        icon: Building2
      },
      {
        name: '股东人数',
        href: '/reference-data/stk-holdernumber',
        icon: Users
      },
      {
        name: '股东增减持',
        href: '/reference-data/stk-holdertrade',
        icon: Users
      }
    ]
  },
  {
    name: '特色数据',
    href: '/features',
    icon: Star,
    children: [
      {
        name: '卖方盈利预测',
        href: '/features/report-rc',
        icon: TrendingUp
      },
      {
        name: '每日筹码及胜率',
        href: '/features/cyq-perf',
        icon: BarChart3
      },
      {
        name: '每日筹码分布',
        href: '/features/cyq-chips',
        icon: PieChart
      },
      {
        name: '中央结算系统持股汇总',
        href: '/features/ccass-hold',
        icon: Database
      },
      {
        name: '中央结算系统持股明细',
        href: '/features/ccass-hold-detail',
        icon: Database
      },
      {
        name: '北向资金持股',
        href: '/features/hk-hold',
        icon: TrendingUp
      },
      {
        name: '股票开盘集合竞价',
        href: '/features/stk-auction-o',
        icon: Clock
      },
      {
        name: '股票收盘集合竞价',
        href: '/features/stk-auction-c',
        icon: TrendingUp
      },
      {
        name: '神奇九转指标',
        href: '/features/stk-nineturn',
        icon: Activity
      },
      {
        name: 'AH股比价',
        href: '/features/stk-ah-comparison',
        icon: TrendingUp
      },
      {
        name: '机构调研表',
        href: '/features/stk-surv',
        icon: Users
      },
      {
        name: '券商每月荐股',
        href: '/features/broker-recommend',
        icon: TrendingUp
      }
    ]
  },
  {
    name: '两融数据',
    icon: Wallet,
    href: '/margin',
    children: [
      {
        name: '融资融券交易汇总',
        href: '/margin/summary',
        icon: BarChart3
      },
      {
        name: '融资融券交易明细',
        href: '/margin/detail',
        icon: FileText
      },
      {
        name: '融资融券标的（盘前）',
        href: '/margin/secs',
        icon: Activity
      },
      {
        name: '转融资交易汇总',
        href: '/margin/slb-len',
        icon: TrendingUp
      }
    ]
  },
  {
    name: '资金流向',
    icon: DollarSign,
    href: '/moneyflow',
    children: [
      {
        name: '个股资金流向',
        href: '/moneyflow/stock',
        icon: Activity
      },
      {
        name: '个股资金流向（DC）',
        href: '/moneyflow/stock-dc',
        icon: TrendingUp
      },
      {
        name: '板块资金流向（DC）',
        href: '/moneyflow/ind-dc',
        icon: BarChart3
      },
      {
        name: '大盘资金流向（DC）',
        href: '/moneyflow/mkt-dc',
        icon: LineChart
      },
      {
        name: '沪深港通资金流向',
        href: '/moneyflow/hsgt',
        icon: TrendingUp
      }
    ]
  },
  {
    name: '打板专题',
    href: '/boardgame',
    icon: ListOrdered,
    children: [
      {
        name: '龙虎榜每日明细',
        href: '/boardgame/top-list',
        icon: Flame
      },
      {
        name: '龙虎榜机构明细',
        href: '/boardgame/top-inst',
        icon: Building2
      },
      {
        name: '涨跌停列表',
        href: '/boardgame/limit-list',
        icon: TrendingUp
      },
      {
        name: '连板天梯',
        href: '/boardgame/limit-step',
        icon: TrendingUp
      },
      {
        name: '最强板块统计',
        href: '/boardgame/limit-cpt',
        icon: TrendingUp
      },
      {
        name: '东方财富概念板块',
        href: '/boardgame/dc-index',
        icon: BarChart3
      },
      {
        name: '东方财富板块成分',
        href: '/boardgame/dc-member',
        icon: Layers
      },
      {
        name: '东财概念板块行情',
        href: '/boardgame/dc-daily',
        icon: LineChart
      }
    ]
  },
  {
    name: '新闻公告',
    href: '/news-anns',
    icon: Bell,
    children: [
      {
        name: '公司公告',
        href: '/news-anns/stock-anns',
        icon: ScrollText
      },
      {
        name: '财经快讯',
        href: '/news-anns/news-flash',
        icon: Newspaper
      },
      {
        name: '新闻联播',
        href: '/news-anns/cctv-news',
        icon: Tv
      },
      {
        name: '宏观经济指标',
        href: '/news-anns/macro-indicators',
        icon: BarChart3
      }
    ]
  },
  {
    name: '用户管理',
    href: '/users',
    icon: Users
  },
  {
    name: '策略管理',
    href: '/strategies',
    icon: TrendingUp
  },
  {
    name: '市场情绪',
    icon: Zap,
    children: [
      {
        name: 'AI分析',
        href: '/sentiment/ai-analysis',
        icon: Sparkles
      },
      {
        name: '盘前预期',
        href: '/sentiment/premarket',
        icon: Clock
      },
      {
        name: 'AI分析记录',
        href: '/sentiment/stock-ai-analysis',
        icon: Brain
      }
    ]
  },
  {
    name: '系统设置',
    icon: Settings,
    children: [
      {
        name: '系统配置',
        href: '/settings/system',
        icon: Wrench
      },
      {
        name: 'AI 配置',
        href: '/settings/ai-config',
        icon: Sparkles
      },
      {
        name: '提示词管理',
        href: '/settings/prompt-templates',
        icon: FileText
      },
      {
        name: '定时任务',
        href: '/settings/scheduler',
        icon: Clock
      },
      {
        name: '同步配置',
        href: '/settings/sync-config',
        icon: Database
      },
      {
        name: '通知渠道',
        href: '/settings/notification-channels',
        icon: Bell
      }
    ]
  },
  {
    name: '日志管理',
    icon: FileText,
    children: [
      {
        name: '系统日志',
        href: '/logs/system',
        icon: ScrollText
      },
      {
        name: 'LLM调用日志',
        href: '/logs/llm-calls',
        icon: Brain
      }
    ]
  },
  {
    name: '系统监控',
    icon: Activity,
    children: [
      {
        name: '性能监控',
        href: '/monitoring/performance',
        icon: Activity
      },
      {
        name: '通知监控',
        href: '/monitoring/notifications',
        icon: Bell
      }
    ]
  },
]
