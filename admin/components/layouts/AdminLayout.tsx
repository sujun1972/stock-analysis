/**
 * 管理后台主布局组件
 *
 * 功能特性：
 * - 响应式侧边栏（大屏折叠为图标，小屏滑入滑出）
 * - 两级菜单导航（支持子菜单展开/收起）
 * - 智能菜单展开：根据当前路径自动展开所属菜单
 * - 路由响应式：切换页面时自动更新菜单展开状态
 * - 小屏幕点击菜单自动收起
 * - 收起状态下显示悬浮提示
 * - 侧边栏状态持久化（localStorage）
 *
 * @author Admin Team
 * @since 2026-03-03
 * @updated 2026-03-11 优化菜单自动展开逻辑，调整菜单结构
 */

'use client'

import { ReactNode, useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import {
  Settings,
  Database,
  FileText,
  Activity,
  LayoutDashboard,
  ChevronRight,
  ChevronDown,
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
  DollarSign,
  BarChart3,
  Wallet,
  ListOrdered,
  Building2,
  Star
} from 'lucide-react'
import { Header } from '@/components/layout/Header'
import { useSidebarStore } from '@/stores/sidebar-store'
import { cn } from '@/lib/utils'
import { Breadcrumb } from '@/components/ui/breadcrumb'
import { useBreadcrumbs } from '@/hooks/useBreadcrumbs'

interface AdminLayoutProps {
  children: ReactNode
}

interface NavItem {
  name: string
  href?: string
  icon: any
  children?: NavItem[]
}

const navItems: NavItem[] = [
  {
    name: '控制台',
    href: '/',
    icon: LayoutDashboard
  },
  {
    name: '用户管理',
    href: '/users',
    icon: Users
  },
  {
    name: '股票管理',
    href: '/stocks',
    icon: LineChart
  },
  {
    name: '策略管理',
    href: '/strategies',
    icon: TrendingUp
  },
  {
    name: '概念管理',
    href: '/concepts',
    icon: Tag
  },
  {
    name: '市场情绪',
    icon: Zap,
    children: [
      {
        name: '情绪数据',
        href: '/sentiment/data',
        icon: Activity
      },
      {
        name: '龙虎榜',
        href: '/sentiment/dragon-tiger',
        icon: Flame
      },
      {
        name: '涨停板池',
        href: '/sentiment/limit-up',
        icon: ArrowUpCircle
      },
      {
        name: '情绪周期',
        href: '/sentiment/cycle',
        icon: TrendingUp
      },
      {
        name: 'AI分析',
        href: '/sentiment/ai-analysis',
        icon: Sparkles
      },
      {
        name: '盘前预期',
        href: '/sentiment/premarket',
        icon: Clock
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
        name: '数据源设置',
        href: '/settings/datasource',
        icon: Database
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
        name: '通知渠道',
        href: '/settings/notification-channels',
        icon: Bell
      }
    ]
  },
  {
    name: '资金流向',
    icon: DollarSign,
    children: [
      {
        name: '沪深港通资金流向',
        href: '/data/moneyflow-hsgt',
        icon: TrendingUp
      },
      {
        name: '个股资金流向（Tushare）',
        href: '/data/moneyflow',
        icon: Activity
      },
      {
        name: '大盘资金流向（DC）',
        href: '/data/moneyflow-mkt-dc',
        icon: LineChart
      },
      {
        name: '板块资金流向（DC）',
        href: '/data/moneyflow-ind-dc',
        icon: BarChart3
      },
      {
        name: '个股资金流向（DC）',
        href: '/data/moneyflow-stock-dc',
        icon: TrendingUpIcon
      }
    ]
  },
  {
    name: '两融数据',
    icon: Wallet,
    children: [
      {
        name: '融资融券交易汇总',
        href: '/data/margin',
        icon: BarChart3
      },
      {
        name: '融资融券交易明细',
        href: '/data/margin-detail',
        icon: FileText
      },
      {
        name: '融资融券标的（盘前更新）',
        href: '/data/margin-secs',
        icon: Activity
      },
      {
        name: '转融资交易汇总',
        href: '/data/slb-len',
        icon: TrendingUp
      }
    ]
  },
  {
    name: '打板专题',
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
      }
    ]
  },
  {
    name: '特色数据',
    icon: Star,
    children: [
      {
        name: '卖方盈利预测',
        href: '/features/report-rc',
        icon: TrendingUp
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
        name: '股东人数',
        href: '/reference-data/stk-holdernumber',
        icon: Users
      },
      {
        name: '大宗交易',
        href: '/reference-data/block-trade',
        icon: Building2
      },
      {
        name: '股东增减持',
        href: '/reference-data/stk-holdertrade',
        icon: Users
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
      }
    ]
  },
  {
    name: '数据中心',
    icon: Database,
    children: [
      {
        name: '数据初始化',
        href: '/sync/initialize',
        icon: RefreshCw
      },
      {
        name: '新股列表同步',
        href: '/sync/new-stocks',
        icon: PackagePlus
      },
      {
        name: '退市列表同步',
        href: '/sync/delisted-stocks',
        icon: PackageMinus
      },
      {
        name: '实时行情同步',
        href: '/sync/realtime',
        icon: TrendingUpIcon
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

export default function AdminLayout({ children }: AdminLayoutProps) {
  const pathname = usePathname()
  const router = useRouter()
  const { isCollapsed, setCollapsed } = useSidebarStore()
  const breadcrumbs = useBreadcrumbs()

  /**
   * 根据当前路径自动计算应该展开的菜单
   * 返回包含当前活跃页面的父菜单名称数组
   *
   * @returns 需要展开的菜单名称数组
   */
  const getInitialOpenMenus = (): string[] => {
    const openMenus: string[] = []
    navItems.forEach(item => {
      if (item.children) {
        const hasActiveChild = item.children.some(
          child => child.href && pathname.startsWith(child.href)
        )
        if (hasActiveChild) {
          openMenus.push(item.name)
        }
      }
    })
    return openMenus
  }

  const [openMenus, setOpenMenus] = useState<string[]>(() => getInitialOpenMenus())

  /**
   * 预加载关键页面
   * 在组件挂载后预加载用户最常访问的页面，提升导航体验
   */
  useEffect(() => {
    // 预加载关键页面（最常访问的页面）
    const criticalPages = [
      '/strategies',
      '/stocks',
      '/sentiment/data',
      '/sync',
      '/users',
    ]

    // 延迟预加载，避免影响当前页面加载
    const timer = setTimeout(() => {
      criticalPages.forEach(page => {
        router.prefetch(page)
      })
    }, 1000)

    return () => clearTimeout(timer)
  }, [router])

  /**
   * 监听路径变化，自动展开/收起对应的菜单
   * 确保当前页面所属的菜单始终展开，其他菜单自动收起
   */
  useEffect(() => {
    const activeMenus = getInitialOpenMenus()
    setOpenMenus(activeMenus)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname])

  /**
   * 判断菜单项是否处于激活状态
   * 对于有子菜单的项，检查子菜单是否有激活项
   *
   * 改进：避免短路径匹配长路径的问题（如 /data/margin 匹配 /data/margin-detail）
   */
  const isActive = (item: NavItem) => {
    if (item.href) {
      if (item.href === '/') {
        return pathname === '/'
      }
      // 精确匹配或者匹配后面跟着 / 的路径
      return pathname === item.href || pathname.startsWith(item.href + '/')
    }
    // 如果有子菜单，检查子菜单是否有激活项
    if (item.children) {
      return item.children.some(child => {
        if (!child.href) return false
        if (child.href === '/') return pathname === '/'
        return pathname === child.href || pathname.startsWith(child.href + '/')
      })
    }
    return false
  }

  /**
   * 切换子菜单的展开/收起状态
   */
  const toggleMenu = (menuName: string) => {
    setOpenMenus(prev =>
      prev.includes(menuName)
        ? prev.filter(name => name !== menuName)
        : [...prev, menuName]
    )
  }

  /**
   * 小屏幕点击菜单项后自动收起侧边栏
   * 检测窗口宽度，小于 768px（md breakpoint）时自动收起
   */
  const handleMenuClick = () => {
    if (window.innerWidth < 768) {
      setCollapsed(true)
    }
  }

  return (
    <div className="flex h-screen bg-gray-100 dark:bg-gray-900 overflow-hidden">
      {/* 侧边栏 - 大屏幕折叠，小屏幕滑出 */}
      <aside
        className={cn(
          "bg-gray-900 text-white flex flex-col transition-all duration-300",
          // 大屏幕 (md+): 相对定位，收起时显示图标，展开时显示全部
          "md:relative md:flex",
          isCollapsed ? "md:w-20 md:overflow-visible" : "md:w-64",
          // 小屏幕: 固定定位，从左侧滑入/滑出
          "fixed left-0 top-0 h-full z-40 w-64",
          isCollapsed ? "md:translate-x-0 -translate-x-full" : "translate-x-0"
        )}
      >
        {/* Logo */}
        <div className={cn(
          "p-6 border-b border-gray-800 transition-all",
          isCollapsed && "md:p-4"
        )}>
          {/* 大屏幕收起时显示简化 Logo，小屏幕始终显示完整 Logo */}
          <div className={cn(
            isCollapsed && "hidden md:flex items-center justify-center"
          )}>
            {isCollapsed && (
              <div className="w-10 h-10 rounded-lg bg-gradient-to-r from-blue-400 to-purple-500 flex items-center justify-center">
                <span className="text-white font-bold text-lg">SA</span>
              </div>
            )}
          </div>

          <div className={cn(
            isCollapsed && "md:hidden"
          )}>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
              管理后台
            </h1>
            <p className="text-xs text-gray-400 mt-1">Stock Analysis Admin</p>
          </div>
        </div>

        {/* 导航菜单 */}
        <nav className={cn(
          "flex-1 p-4 space-y-1 overflow-y-auto scrollbar-hide",
          isCollapsed && "md:p-2 md:overflow-visible"
        )}>
          {navItems.map((item) => {
            const Icon = item.icon
            const active = isActive(item)
            const isOpen = openMenus.includes(item.name)

            // 有子菜单的项
            if (item.children) {
              return (
                <div key={item.name} className="relative menu-item-with-submenu">
                  {/* 父菜单项 */}
                  <button
                    onClick={() => toggleMenu(item.name)}
                    className={cn(
                      "w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all",
                      active
                        ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/50'
                        : 'text-gray-300 hover:bg-gray-800 hover:text-white',
                      isCollapsed && "md:px-2 md:justify-center"
                    )}
                    title={isCollapsed ? item.name : undefined}
                  >
                    <Icon className={cn(
                      "w-5 h-5 flex-shrink-0",
                      isCollapsed && "md:w-6 md:h-6"
                    )} />
                    <span className={cn(
                      "font-medium flex-1 text-left",
                      isCollapsed && "md:hidden"
                    )}>
                      {item.name}
                    </span>
                    {!isCollapsed && (
                      <ChevronDown className={cn(
                        "w-4 h-4 transition-transform",
                        isOpen && "rotate-180"
                      )} />
                    )}
                  </button>

                  {/* 收起时的悬浮子菜单 - 仅大屏幕 */}
                  {isCollapsed && item.children && (
                    <div className="submenu-dropdown absolute left-full top-0 ml-2 bg-gray-800 rounded-lg z-[100] min-w-[200px] py-1 shadow-xl border border-gray-700 opacity-0 invisible transition-all duration-200">
                      <div className={cn(
                        "px-3 py-2 text-xs font-semibold border-b border-gray-700 flex items-center gap-2",
                        active ? "text-blue-400" : "text-gray-400"
                      )}>
                        <Icon className="w-3 h-3" />
                        {item.name}
                      </div>
                      <div className="py-1">
                        {item.children.map((child) => {
                          const ChildIcon = child.icon
                          const childActive = child.href && (pathname === child.href || pathname.startsWith(child.href + '/'))
                          return (
                            <Link
                              key={child.href}
                              href={child.href!}
                              onClick={handleMenuClick}
                              className={cn(
                                "flex items-center gap-3 px-4 py-2.5 text-sm transition-colors",
                                childActive
                                  ? 'bg-blue-600 text-white'
                                  : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                              )}
                            >
                              <ChildIcon className="w-4 h-4" />
                              <span>{child.name}</span>
                            </Link>
                          )
                        })}
                      </div>
                    </div>
                  )}

                  {/* 子菜单项 - 仅展开状态显示 */}
                  {!isCollapsed && isOpen && (
                    <div className="mt-1 ml-4 space-y-1">
                      {item.children.map((child) => {
                        const ChildIcon = child.icon
                        const childActive = child.href && (pathname === child.href || pathname.startsWith(child.href + '/'))
                        return (
                          <Link
                            key={child.href}
                            href={child.href!}
                            onClick={handleMenuClick}
                            className={cn(
                              "flex items-center gap-3 px-4 py-2 rounded-lg transition-all text-sm",
                              childActive
                                ? 'text-blue-400 hover:bg-gray-800'
                                : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                            )}
                          >
                            <ChildIcon className="w-4 h-4" />
                            <span className="font-medium">{child.name}</span>
                            {childActive && <ChevronRight className="w-3 h-3 ml-auto" />}
                          </Link>
                        )
                      })}
                    </div>
                  )}

                  {/* 小屏幕展开显示子菜单 */}
                  {isCollapsed && isOpen && (
                    <div className="md:hidden mt-1 ml-4 space-y-1">
                      {item.children.map((child) => {
                        const ChildIcon = child.icon
                        const childActive = child.href && (pathname === child.href || pathname.startsWith(child.href + '/'))
                        return (
                          <Link
                            key={child.href}
                            href={child.href!}
                            onClick={handleMenuClick}
                            className={cn(
                              "flex items-center gap-3 px-4 py-2 rounded-lg transition-all text-sm",
                              childActive
                                ? 'text-blue-400 hover:bg-gray-800'
                                : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                            )}
                          >
                            <ChildIcon className="w-4 h-4" />
                            <span className="font-medium">{child.name}</span>
                            {childActive && <ChevronRight className="w-3 h-3 ml-auto" />}
                          </Link>
                        )
                      })}
                    </div>
                  )}
                </div>
              )
            }

            // 普通菜单项（无子菜单）
            return (
              <Link
                key={item.href}
                href={item.href!}
                onClick={handleMenuClick}
                className={cn(
                  "flex items-center gap-3 px-4 py-3 rounded-lg transition-all group relative",
                  active
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/50'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white',
                  isCollapsed && "md:px-2 md:justify-center"
                )}
                title={isCollapsed ? item.name : undefined}
              >
                <Icon className={cn("w-5 h-5", isCollapsed && "md:w-6 md:h-6")} />
                <span className={cn(
                  "font-medium",
                  isCollapsed && "md:hidden"
                )}>
                  {item.name}
                </span>
                {active && !isCollapsed && <ChevronRight className="w-4 h-4 ml-auto" />}

                {/* 收起时的悬浮提示 - 仅大屏幕 */}
                {isCollapsed && (
                  <div className="hidden md:block absolute left-full ml-2 px-3 py-2 bg-gray-800 text-white text-sm rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
                    {item.name}
                  </div>
                )}
              </Link>
            )
          })}
        </nav>

        {/* 底部信息 */}
        {!isCollapsed && (
          <div className="p-4 border-t border-gray-800">
            <div className="text-xs text-gray-400 space-y-1">
              <p>版本: v1.0.0</p>
              <p>© 2026 Stock Analysis</p>
            </div>
          </div>
        )}
      </aside>

      {/* 遮罩层 - 仅小屏幕且侧边栏展开时显示 */}
      {!isCollapsed && (
        <div
          className="md:hidden fixed inset-0 bg-black/50 z-30"
          onClick={() => useSidebarStore.getState().setCollapsed(true)}
        />
      )}

      {/* 主内容区 */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* 顶部 Header */}
        <Header />

        {/* 面包屑导航 - 在Header下方，内容区上方 */}
        {breadcrumbs.length > 0 && (
          <div className="px-8 py-3 border-b bg-white dark:bg-gray-900">
            <Breadcrumb items={breadcrumbs} />
          </div>
        )}

        {/* 页面内容 */}
        <div className="flex-1 overflow-auto p-8">
          {children}
        </div>
      </main>
    </div>
  )
}
