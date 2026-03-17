'use client'

import { useEffect } from 'react'
import { usePathname } from 'next/navigation'
import NProgress from 'nprogress'

/**
 * 配置 NProgress 进度条
 * @see https://github.com/rstacruz/nprogress
 */
NProgress.configure({
  minimum: 0.3,        // 进度条最小值
  easing: 'ease',       // 动画缓动函数
  speed: 200,           // 动画速度(ms)
  showSpinner: false,   // 不显示旋转图标
  trickleSpeed: 200,    // 自动递增速度
  parent: 'body',       // 进度条父元素
})

/**
 * 全局页面加载进度条组件
 *
 * 功能特性:
 * 1. 自动检测页面路由变化并显示进度条
 * 2. 拦截所有内部链接点击事件
 * 3. 监听浏览器前进/后退
 *
 * 注意：仅在页面跳转时显示，不包括 API 请求和查询参数变化
 *
 * @returns null - 不渲染任何可见元素
 */
export function ProgressBar() {
  const pathname = usePathname()

  // 监听路由变化，完成进度条（仅路径变化，不包括查询参数）
  useEffect(() => {
    NProgress.done()
  }, [pathname])

  // 设置全局事件监听器
  useEffect(() => {
    /**
     * 处理链接点击事件
     * 在页面跳转前启动进度条
     */
    const handleLinkClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      const link = target.closest('a')

      if (link) {
        const href = link.getAttribute('href')
        // 只处理内部链接，排除外部链接和协议链接
        if (href && href.startsWith('/') && !href.startsWith('//')) {
          // 跳过锚点链接
          if (href.startsWith('#')) {
            return
          }

          // 只在跳转到不同页面时显示进度条
          const currentPath = window.location.pathname + window.location.search
          if (href !== currentPath) {
            NProgress.start()
          }
        }
      }
    }

    /**
     * 处理表单提交
     * 表单提交通常会导致页面跳转
     */
    const handleFormSubmit = () => {
      NProgress.start()
    }

    /**
     * 处理浏览器前进/后退
     * 使用浏览器导航时也需要显示进度条
     */
    const handlePopState = () => {
      NProgress.start()
    }

    // 添加事件监听器
    document.addEventListener('click', handleLinkClick, true)
    document.addEventListener('submit', handleFormSubmit, true)
    window.addEventListener('popstate', handlePopState)

    // 清理函数
    return () => {
      document.removeEventListener('click', handleLinkClick, true)
      document.removeEventListener('submit', handleFormSubmit, true)
      window.removeEventListener('popstate', handlePopState)
    }
  }, [])

  return null
}