export function formatDuration(ms: number | null): string {
  if (!ms) return '-'
  if (ms < 60000) return `${(ms / 1000).toFixed(0)}s`
  if (ms < 3600000) return `${(ms / 60000).toFixed(1)}m`
  return `${(ms / 3600000).toFixed(1)}h`
}

export function formatDate(iso: string | null): string {
  if (!iso) return '-'
  const d = new Date(iso)
  const now = new Date()
  const diffH = (now.getTime() - d.getTime()) / 3600000
  if (diffH < 24) return `${diffH.toFixed(0)}h 前`
  if (diffH < 168) return `${(diffH / 24).toFixed(0)}d 前`
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
