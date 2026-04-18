'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { PromptTemplate } from '@/types/prompt-template'

interface VersionHistoryProps {
  template: PromptTemplate
}

export function VersionHistory({ template }: VersionHistoryProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">统计信息</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-muted-foreground">使用次数</span>
          <span className="font-semibold">{template.usage_count || 0}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">成功率</span>
          <span className="font-semibold">
            {template.success_rate ? `${(template.success_rate * 100).toFixed(1)}%` : '-'}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">平均Token</span>
          <span className="font-semibold">{template.avg_tokens_used || '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">创建时间</span>
          <span className="text-xs">{new Date(template.created_at).toLocaleString('zh-CN')}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-muted-foreground">更新时间</span>
          <span className="text-xs">{new Date(template.updated_at).toLocaleString('zh-CN')}</span>
        </div>
      </CardContent>
    </Card>
  )
}
