'use client'

import React from 'react'

/** 将 **加粗** 标记拆分为带 <strong> 的 React 节点数组，避免 dangerouslySetInnerHTML */
export function renderBold(text: string): React.ReactNode {
  const parts = text.split(/\*\*(.+?)\*\*/g)
  return parts.map((part, i) =>
    i % 2 === 1 ? <strong key={i}>{part}</strong> : part,
  )
}

/** 高亮【标签】为蓝色粗体 */
export function highlightTags(text: string): React.ReactNode {
  const parts = text.split(/(【[^】]+】)/g)
  if (parts.length === 1) return text
  return parts.map((part, i) =>
    /^【[^】]+】$/.test(part)
      ? <span key={i} className="font-semibold text-blue-700 dark:text-blue-400">{part}</span>
      : part,
  )
}
