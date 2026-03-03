import { redirect } from 'next/navigation'

/**
 * 系统设置默认页面 - 重定向到数据源设置
 */
export default function SettingsPage() {
  redirect('/settings/datasource')
}
