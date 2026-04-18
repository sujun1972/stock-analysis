'use client'

export function StatusDot({ status }: { status: string | undefined | null }) {
  if (!status) return <span className="w-2 h-2 rounded-full bg-gray-300 inline-block" />
  const map: Record<string, string> = {
    success: 'bg-green-500',
    running: 'bg-blue-500 animate-pulse',
    pending: 'bg-yellow-400 animate-pulse',
    failure: 'bg-red-500',
  }
  return <span className={`w-2 h-2 rounded-full ${map[status] || 'bg-gray-300'} inline-block`} />
}
