'use client'

import { useEffect } from 'react'
import { usePathname, useSearchParams } from 'next/navigation'
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
 * 1. 自动检测路由变化并显示进度条
 * 2. 拦截所有内部链接点击事件
 * 3. 监听浏览器前进/后退
 * 4. 自动拦截 API 请求（/api/ 路径）
 *
 * @returns null - 不渲染任何可见元素
 */
export function ProgressBar() {
  const pathname = usePathname()
  const searchParams = useSearchParams()

  // 监听路由变化，完成进度条
  useEffect(() => {
    NProgress.done()
  }, [pathname, searchParams])

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

    /**
     * 拦截 fetch 请求
     * 为 API 调用显示进度条
     * 注意：这里的拦截是补充 api-client.ts 中的拦截器
     * 主要用于未经过 axios 的直接 fetch 调用
     */
    const originalFetch = window.fetch
    window.fetch = function(...args) {
      const [resource] = args

      // 只对 API 请求显示进度条
      if (typeof resource === 'string' && resource.includes('/api/')) {
        NProgress.start()

        return originalFetch.apply(this, args as Parameters<typeof fetch>)
          .then(response => {
            NProgress.done()
            return response
          })
          .catch(error => {
            NProgress.done()
            throw error
          })
      }

      return originalFetch.apply(this, args as Parameters<typeof fetch>)
    }

    return () => {
      document.removeEventListener('click', handleLinkClick, true)
      document.removeEventListener('submit', handleFormSubmit, true)
      window.removeEventListener('popstate', handlePopState)
      window.fetch = originalFetch
    }
  }, [])

  return null
}