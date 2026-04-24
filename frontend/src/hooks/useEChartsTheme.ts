'use client'

import { useMemo } from 'react'
import { useTheme } from 'next-themes'

export type ChartPalette = Readonly<{
  background: string
  tooltipBg: string
  tooltipBorder: string
  tooltipText: string
  axisPointerLine: string
  divider: string
  loadingMask: string
  loadingText: string
}>

const LIGHT_PALETTE: ChartPalette = Object.freeze({
  background: '#ffffff',
  tooltipBg: '#ffffff',
  tooltipBorder: '#ccc',
  tooltipText: '#000',
  axisPointerLine: '#999',
  divider: '#ccc',
  loadingMask: 'rgba(255, 255, 255, 0.8)',
  loadingText: '#000',
})

const DARK_PALETTE: ChartPalette = Object.freeze({
  background: 'transparent',
  tooltipBg: 'rgba(30, 41, 59, 0.95)',
  tooltipBorder: '#475569',
  tooltipText: '#e5e7eb',
  axisPointerLine: '#64748b',
  divider: '#334155',
  loadingMask: 'rgba(15, 23, 42, 0.7)',
  loadingText: '#e5e7eb',
})

/**
 * ECharts 主题联动 hook
 *
 * 返回：
 * - `echartsTheme`：传给 `echarts.init(el, theme)` 的主题名（dark / undefined）
 * - `theme`：字符串（'light' | 'dark'），稳定引用，适合作为 effect 依赖触发重建
 * - `palette`：跟随主题切换的颜色常量，**单例** —— 同主题下每次渲染返回同一对象，
 *   把它放到 effect deps 不会因父组件重渲染而误触发。
 *
 * 约定：消费组件用 `theme` 作为 dispose effect 的依赖先销毁旧 instance，下一轮
 * setOption 时再以新主题重建；K 线红涨/绿跌等业务色不走 palette，继续硬编码。
 */
export function useEChartsTheme(): {
  theme: 'light' | 'dark'
  echartsTheme: 'dark' | undefined
  palette: ChartPalette
} {
  const { resolvedTheme } = useTheme()
  // SSR / 首渲染 resolvedTheme 可能为 undefined，退回 light
  const theme: 'light' | 'dark' = resolvedTheme === 'dark' ? 'dark' : 'light'

  const palette = useMemo(
    () => (theme === 'dark' ? DARK_PALETTE : LIGHT_PALETTE),
    [theme],
  )

  return {
    theme,
    echartsTheme: theme === 'dark' ? 'dark' : undefined,
    palette,
  }
}
