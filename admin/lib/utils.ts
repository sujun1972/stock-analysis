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

/**
 * 格式化数字，添加千分位分隔符
 * @param num - 要格式化的数字
 * @param decimals - 小数位数（默认0）
 * @returns 格式化后的字符串
 */
export function formatNumber(num: number | null | undefined, decimals: number = 0): string {
  if (num === null || num === undefined) return '0'

  const options: Intl.NumberFormatOptions = {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }

  return new Intl.NumberFormat('zh-CN', options).format(num)
}

/**
 * 根据涨跌幅返回对应的文字颜色 class
 * 涨（>0）→ 红色，跌（<0）→ 绿色，平（=0）→ 默认色
 */
export function pctChangeColor(pctChange: number | null | undefined): string {
  if (pctChange === null || pctChange === undefined) return ''
  if (pctChange > 0) return 'text-red-600'
  if (pctChange < 0) return 'text-green-600'
  return ''
}

/**
 * 提取股票纯代码（去除交易所后缀）
 * @example formatStockCode('002475.SZ') → '002475'
 * @example formatStockCode('600666.SH') → '600666'
 * @example formatStockCode('002475') → '002475'
 */
export function formatStockCode(tsCode: string | null | undefined): string {
  if (!tsCode) return ''
  const dotIndex = tsCode.indexOf('.')
  return dotIndex !== -1 ? tsCode.slice(0, dotIndex) : tsCode
}

/**
 * 格式化日期
 * @param dateStr - 日期字符串
 * @param format - 格式类型
 * @returns 格式化后的日期字符串
 */
export function formatDate(dateStr: string | Date | null | undefined, format: string = 'YYYY-MM-DD'): string {
  if (!dateStr) return '-'

  const date = typeof dateStr === 'string' ? new Date(dateStr) : dateStr

  if (isNaN(date.getTime())) return '-'

  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')

  switch (format) {
    case 'YYYY-MM-DD':
      return `${year}-${month}-${day}`
    case 'YYYY/MM/DD':
      return `${year}/${month}/${day}`
    case 'DD/MM/YYYY':
      return `${day}/${month}/${year}`
    case 'MM-DD':
      return `${month}-${day}`
    default:
      return `${year}-${month}-${day}`
  }
}
