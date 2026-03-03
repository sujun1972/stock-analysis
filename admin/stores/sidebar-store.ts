/**
 * 侧边栏状态管理 Store
 *
 * 功能：
 * - 管理侧边栏的展开/收起状态
 * - 持久化保存状态到 localStorage
 * - 支持大屏幕（折叠为图标）和小屏幕（滑入/滑出）两种模式
 *
 * @author Admin Team
 * @since 2026-03-03
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface SidebarState {
  /** 侧边栏是否收起 */
  isCollapsed: boolean
  /** 切换侧边栏展开/收起状态 */
  toggleSidebar: () => void
  /** 设置侧边栏展开/收起状态 */
  setCollapsed: (collapsed: boolean) => void
}

export const useSidebarStore = create<SidebarState>()(
  persist(
    (set) => ({
      isCollapsed: false,
      toggleSidebar: () => set((state) => ({ isCollapsed: !state.isCollapsed })),
      setCollapsed: (collapsed) => set({ isCollapsed: collapsed }),
    }),
    {
      name: 'sidebar-storage',
    }
  )
)
