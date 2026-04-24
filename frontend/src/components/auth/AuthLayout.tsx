'use client'

import Link from 'next/link'
import { TrendingUp, LineChart, Sparkles, ShieldCheck } from 'lucide-react'
import { ThemeToggle } from '@/components/theme-toggle'

interface AuthLayoutProps {
  title: string
  subtitle?: string
  children: React.ReactNode
  footer?: React.ReactNode
}

const HIGHLIGHTS = [
  {
    icon: LineChart,
    title: 'AI 量化分析',
    desc: '5 位 AI 专家协同决策，覆盖游资、中线、价值、宏观与 CIO 指令',
  },
  {
    icon: Sparkles,
    title: '策略回测',
    desc: '分钟级 K 线引擎，一键验证买卖点、胜率、收益曲线',
  },
  {
    icon: ShieldCheck,
    title: '全景数据',
    desc: '覆盖行情、财报、筹码、舆情、宏观指标，专家决策有据可查',
  },
]

/**
 * 认证页专用沉浸式布局：桌面 lg:grid-cols-2 左右分屏（左品牌区/右表单），<lg 单列。
 * 与全站 AppShell 并列使用——AppShell 已针对 /login /register /forgot-password 等路由跳过顶栏/导航/页脚。
 */
export function AuthLayout({ title, subtitle, children, footer }: AuthLayoutProps) {
  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-background">
      <aside className="relative hidden lg:flex flex-col justify-between overflow-hidden bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-700 text-white p-10 xl:p-14">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-40"
          style={{
            background:
              'radial-gradient(circle at 20% 20%, rgba(255,255,255,0.25), transparent 40%), radial-gradient(circle at 80% 60%, rgba(168,85,247,0.35), transparent 45%)',
          }}
        />
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-[0.08]"
          style={{
            backgroundImage:
              'linear-gradient(rgba(255,255,255,1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,1) 1px, transparent 1px)',
            backgroundSize: '36px 36px',
          }}
        />

        <div className="relative">
          <Link href="/" className="inline-flex items-center gap-2.5 group">
            <span className="inline-flex items-center justify-center w-10 h-10 rounded-xl bg-white/15 backdrop-blur-sm ring-1 ring-white/20 group-hover:bg-white/25 transition-colors">
              <TrendingUp className="h-5 w-5" />
            </span>
            <span className="text-lg font-semibold tracking-tight">A股AI量化交易系统</span>
          </Link>
        </div>

        <div className="relative space-y-10">
          <div className="space-y-3 max-w-md">
            <h2 className="text-3xl xl:text-4xl font-bold leading-tight">
              让每一次交易，
              <br />
              都有数据与 AI 托底。
            </h2>
            <p className="text-sm xl:text-base text-white/75 leading-relaxed">
              量化因子 + 多专家 AI 协同 + 全市场舆情，重塑散户的决策链条。
            </p>
          </div>

          <ul className="space-y-5 max-w-md">
            {HIGHLIGHTS.map(({ icon: Icon, title: t, desc }) => (
              <li key={t} className="flex gap-3.5">
                <span className="mt-0.5 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white/12 ring-1 ring-white/15">
                  <Icon className="h-4 w-4" />
                </span>
                <div className="min-w-0">
                  <p className="text-sm font-semibold">{t}</p>
                  <p className="text-xs text-white/70 mt-0.5 leading-relaxed">{desc}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>

        <div className="relative text-xs text-white/60">
          &copy; 2026 A股AI量化交易系统 · 仅供学习研究，不构成投资建议
        </div>
      </aside>

      <main className="relative flex flex-col min-h-screen">
        <div className="flex items-center justify-between px-5 sm:px-8 py-4">
          <Link
            href="/"
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors focus-ring rounded-md px-1 py-0.5"
          >
            <span className="inline-flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 text-white lg:hidden">
              <TrendingUp className="h-4 w-4" />
            </span>
            <span className="lg:inline">返回首页</span>
          </Link>
          <ThemeToggle />
        </div>

        <div className="flex-1 flex items-center justify-center px-5 sm:px-8 pb-8">
          <div className="w-full max-w-md">
            {/* 移动端品牌头（桌面左栏已展示，此处 lg:hidden） */}
            <div className="lg:hidden text-center mb-8">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 mb-3 shadow-lg shadow-blue-500/20">
                <TrendingUp className="h-7 w-7 text-white" />
              </div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                A股AI量化交易系统
              </h1>
            </div>

            <div className="mb-6 space-y-1.5">
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">{title}</h1>
              {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
            </div>

            {children}

            {footer && <div className="mt-6">{footer}</div>}
          </div>
        </div>

        <div className="px-5 sm:px-8 pb-6 text-center text-xs text-muted-foreground">
          继续即表示您同意我们的
          <Link href="/terms" className="underline underline-offset-2 hover:text-foreground mx-1">
            服务条款
          </Link>
          与
          <Link href="/privacy" className="underline underline-offset-2 hover:text-foreground ml-1">
            隐私政策
          </Link>
        </div>
      </main>
    </div>
  )
}
