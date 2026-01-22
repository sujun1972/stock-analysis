import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

/**
 * 合并 Tailwind CSS 类名的工具函数
 * 使用 clsx 处理条件类名，使用 tailwind-merge 解决类名冲突
 *
 * @param inputs - 类名数组，支持字符串、对象、数组等多种格式
 * @returns 合并后的类名字符串
 *
 * @example
 * cn("px-2 py-1", "bg-red-500")
 * cn("px-2", condition && "bg-blue-500")
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
