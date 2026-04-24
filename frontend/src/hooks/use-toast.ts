"use client"

// 薄包装层：兼容 shadcn useToast 的 `toast({ title, description, variant })` 调用形态，
// 底层走 sonner。全项目 148+ 处调用无需改动；`variant: "destructive"` → sonner.error。
// 新代码推荐直接 `import { toast } from 'sonner'` 使用 toast.success / toast.error 等语义方法。

import * as React from "react"
import { toast as sonnerToast } from "sonner"

// "success" 是历史遗留（shadcn 原本只有 default/destructive，但代码中混入了 success），一并映射到 sonner.success
type ToastVariant = "default" | "destructive" | "success"

type Toast = {
  title?: React.ReactNode
  description?: React.ReactNode
  variant?: ToastVariant
  action?: React.ReactNode
  duration?: number
}

type ToastReturn = {
  id: string | number
  dismiss: () => void
  update: (props: Toast) => void
}

// 把 shadcn 的 { title, description } 语义映射为 sonner 的 (message, { description }):
// 只有 title 时用 title 当主文本；只有 description 时 description 当主文本；两者都有才作为副标题。
function emit(props: Toast, id?: string | number): string | number {
  const { title, description, variant, action, duration } = props
  const content = (title ?? description ?? "") as React.ReactNode
  const payload = {
    description: title && description ? description : undefined,
    action,
    duration,
    id,
  }
  if (variant === "destructive") return sonnerToast.error(content, payload)
  if (variant === "success") return sonnerToast.success(content, payload)
  return sonnerToast(content, payload)
}

function toast(props: Toast): ToastReturn {
  const id = emit(props)
  return {
    id,
    dismiss: () => sonnerToast.dismiss(id),
    update: (next) => {
      emit(next, id)
    },
  }
}

function useToast() {
  return React.useMemo(
    () => ({
      toast,
      dismiss: (toastId?: string | number) => sonnerToast.dismiss(toastId),
    }),
    []
  )
}

export { useToast, toast }
