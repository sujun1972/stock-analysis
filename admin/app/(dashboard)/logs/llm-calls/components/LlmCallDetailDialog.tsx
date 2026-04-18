/**
 * LLM调用详情弹窗
 * 展示单条调用记录的完整信息，包括基本信息、性能指标、Prompt和Response
 */

'use client'

import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  type LLMCallLog,
  businessTypeMap,
  statusMap,
  providerMap,
} from '@/lib/llm-logs-api'

interface LlmCallDetailDialogProps {
  log: LLMCallLog | null
  open: boolean
  onOpenChange: (open: boolean) => void
  formatDuration: (ms: number | null) => string
  formatCost: (cost: number | null) => string
}

export function LlmCallDetailDialog({
  log,
  open,
  onOpenChange,
  formatDuration,
  formatCost,
}: LlmCallDetailDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle>LLM调用详情</DialogTitle>
          <DialogDescription>
            调用ID: {log?.call_id}
          </DialogDescription>
        </DialogHeader>

        {log && (
          <ScrollArea className="h-[60vh]">
            <div className="space-y-6 pr-4">
              {/* 基本信息 */}
              <div>
                <h3 className="font-semibold mb-3 text-lg">基本信息</h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">业务类型：</span>
                    <span className="ml-2">{businessTypeMap[log.business_type]}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">业务日期：</span>
                    <span className="ml-2">{log.business_date || '-'}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">AI提供商：</span>
                    <Badge variant="outline" className="ml-2">
                      {providerMap[log.provider]}
                    </Badge>
                  </div>
                  <div>
                    <span className="text-gray-500">模型：</span>
                    <span className="ml-2 font-mono text-xs">{log.model_name}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">状态：</span>
                    <Badge variant={log.status === 'success' ? 'default' : 'destructive'} className="ml-2">
                      {statusMap[log.status]?.text}
                    </Badge>
                  </div>
                  <div>
                    <span className="text-gray-500">触发方式：</span>
                    <span className="ml-2">{log.is_scheduled ? '定时任务' : '手动触发'}</span>
                  </div>
                </div>
              </div>

              {/* 性能指标 */}
              <div>
                <h3 className="font-semibold mb-3 text-lg">性能指标</h3>
                <div className="grid grid-cols-3 gap-4">
                  <Card>
                    <CardHeader className="pb-2">
                      <CardDescription>Tokens消耗</CardDescription>
                      <CardTitle className="text-2xl">{log.tokens_total?.toLocaleString() || '-'}</CardTitle>
                    </CardHeader>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardDescription>成本</CardDescription>
                      <CardTitle className="text-2xl">{formatCost(log.cost_estimate)}</CardTitle>
                    </CardHeader>
                  </Card>
                  <Card>
                    <CardHeader className="pb-2">
                      <CardDescription>耗时</CardDescription>
                      <CardTitle className="text-2xl">{formatDuration(log.duration_ms)}</CardTitle>
                    </CardHeader>
                  </Card>
                </div>
              </div>

              {/* 调用参数 */}
              <div>
                <h3 className="font-semibold mb-3 text-lg">调用参数</h3>
                <pre className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg text-xs overflow-auto">
                  {JSON.stringify(log.call_parameters, null, 2)}
                </pre>
              </div>

              {/* 输入Prompt */}
              <div>
                <h3 className="font-semibold mb-3 text-lg">输入Prompt</h3>
                <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg">
                  <p className="text-xs text-gray-500 mb-2">
                    长度: {log.prompt_length} 字符
                  </p>
                  <pre className="text-sm whitespace-pre-wrap max-h-60 overflow-auto">
                    {log.prompt_text}
                  </pre>
                </div>
              </div>

              {/* 输出Response */}
              {log.response_text && (
                <div>
                  <h3 className="font-semibold mb-3 text-lg">输出Response</h3>
                  <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg">
                    <p className="text-xs text-gray-500 mb-2">
                      长度: {log.response_length} 字符
                    </p>
                    <pre className="text-sm whitespace-pre-wrap max-h-60 overflow-auto">
                      {log.response_text}
                    </pre>
                  </div>
                </div>
              )}

              {/* 错误信息 */}
              {log.error_message && (
                <div>
                  <h3 className="font-semibold mb-3 text-lg text-red-600">错误信息</h3>
                  <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg">
                    <p className="text-sm text-red-600 dark:text-red-400">
                      {log.error_message}
                    </p>
                    {log.error_code && (
                      <p className="text-xs text-gray-500 mt-2">
                        错误代码: {log.error_code}
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          </ScrollArea>
        )}
      </DialogContent>
    </Dialog>
  )
}
