'use client'

import { useState } from 'react'
import { toast } from 'sonner'
import { apiClient } from '@/lib/api-client'
import logger from '@/lib/logger'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PageHeader } from '@/components/common/PageHeader'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { DatePicker } from '@/components/ui/date-picker'
import { format, subDays } from '@/lib/date-utils'
import { addTaskToQueue } from '@/hooks/use-task-polling'

export default function InitializePage() {

  // ========== 情绪数据批量同步相关状态 ==========
  const [sentimentSyncing, setSentimentSyncing] = useState(false)
  const [sentimentError, setSentimentError] = useState<string | null>(null)
  const [sentimentSuccess, setSentimentSuccess] = useState<string | null>(null)

  // 情绪数据同步日期范围
  const [sentimentStartDate, setSentimentStartDate] = useState<Date>(() => subDays(new Date(), 7))
  const [sentimentEndDate, setSentimentEndDate] = useState<Date>(new Date())

  // 情绪数据批量同步
  const handleSentimentBatchSync = async () => {
    try {
      setSentimentSyncing(true)
      setSentimentError(null)
      setSentimentSuccess(null)

      const formattedStartDate = format(sentimentStartDate, 'yyyy-MM-dd')
      const formattedEndDate = format(sentimentEndDate, 'yyyy-MM-dd')

      const res = await apiClient.syncSentimentBatch({
        start_date: formattedStartDate,
        end_date: formattedEndDate
      }) as any

      if (res.code === 200 && res.data?.task_id) {
        const { task_id, display_name } = res.data

        // 添加到全局任务队列
        addTaskToQueue(task_id, 'sentiment.batch_sync', display_name, 'sentiment')

        toast.success('任务已启动', {
          description: '情绪数据批量同步任务已在后台执行，您可以在右上角查看进度',
          duration: 5000
        })

        setSentimentSuccess('同步任务已启动，请在右上角任务图标查看进度')
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || '启动同步任务失败'
      setSentimentError(errorMessage)
      toast.error('启动任务失败', { description: errorMessage })
      logger.error('Sentiment batch sync error', err)
    } finally {
      setSentimentSyncing(false)
    }
  }

  return (
        <div className="space-y-6">
      {/* 页面标题 */}
      <PageHeader
        title="数据初始化"
        description="系统首次使用时的必要步骤，请按顺序完成以下初始化操作"
      />

      {/* 使用建议 */}
      <Card className="bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
        <CardHeader>
          <CardTitle className="text-lg text-blue-900 dark:text-blue-200">
            使用建议
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm text-blue-800 dark:text-blue-300">
            <li className="flex items-start">
              <span className="mr-2">•</span>
              <span>股票列表同步已迁移到"基础数据 &gt; 股票列表"页面</span>
            </li>
            <li className="flex items-start">
              <span className="mr-2">•</span>
              <span>日线数据同步已迁移到"行情数据 &gt; 股票日线数据"页面</span>
            </li>
            <li className="flex items-start">
              <span className="mr-2">•</span>
              <span>首次使用建议选择较短时间范围（如3天或1周）进行测试</span>
            </li>
            <li className="flex items-start">
              <span className="mr-2">•</span>
              <span>大批量同步建议在非交易时段进行，避免影响数据源性能</span>
            </li>
          </ul>
        </CardContent>
      </Card>

      {/* ========== 情绪数据批量同步 ========== */}
      <Card className="border-2 border-orange-200 dark:border-orange-800">
        <CardHeader>
          <div className="flex items-center">
            <div className="flex items-center justify-center w-10 h-10 rounded-full bg-orange-600 text-white font-bold mr-3">
              1
            </div>
            <CardTitle className="text-xl">
              情绪数据批量同步
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-gray-600 dark:text-gray-400">
            批量同步历史日期的市场情绪数据（大盘指数、涨停板池、龙虎榜）
          </p>

          {/* 错误提示 */}
          {sentimentError && (
            <Alert className="bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800">
              <AlertDescription className="text-red-800 dark:text-red-200">
                {sentimentError}
              </AlertDescription>
            </Alert>
          )}

          {/* 成功提示 */}
          {sentimentSuccess && (
            <Alert className="bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800">
              <AlertDescription className="text-green-800 dark:text-green-200">
                {sentimentSuccess}
              </AlertDescription>
            </Alert>
          )}

          {/* 同步参数配置 */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">同步日期范围</h3>

            {/* 日期范围选择 */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>起始日期</Label>
                <DatePicker
                  date={sentimentStartDate}
                  onDateChange={(date) => date && setSentimentStartDate(date)}
                  placeholder="选择起始日期"
                  disabled={sentimentSyncing}
                />
              </div>
              <div className="space-y-2">
                <Label>结束日期</Label>
                <DatePicker
                  date={sentimentEndDate}
                  onDateChange={(date) => date && setSentimentEndDate(date)}
                  placeholder="选择结束日期"
                  disabled={sentimentSyncing}
                />
              </div>
            </div>

            {/* 日期范围提示 */}
            <Alert className="bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800">
              <AlertDescription className="text-sm text-orange-800 dark:text-orange-300">
                <strong>当前选择：</strong>从 {format(sentimentStartDate, 'yyyy年MM月dd日')} 至 {format(sentimentEndDate, 'yyyy年MM月dd日')}
                <br />
                <strong>提示：</strong>系统会自动跳过非交易日，只同步交易日的情绪数据
              </AlertDescription>
            </Alert>
          </div>

          {/* 开始同步按钮 */}
          <Button
            onClick={handleSentimentBatchSync}
            disabled={sentimentSyncing}
            className="w-full md:w-auto"
          >
            {sentimentSyncing ? '同步中...' : '开始批量同步'}
          </Button>

          {/* 数据说明 */}
          <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
            <details className="text-sm">
              <summary className="cursor-pointer font-medium text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white">
                查看数据说明
              </summary>
              <div className="mt-3 space-y-3 text-sm text-gray-600 dark:text-gray-400">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
                  <div>
                    <strong className="block mb-2 text-gray-700 dark:text-gray-300">数据内容：</strong>
                    <ul className="list-disc list-inside space-y-1.5">
                      <li>大盘指数（上证、深成、创业板）</li>
                      <li>涨停板池（涨停、炸板、连板）</li>
                      <li>龙虎榜（机构、游资席位）</li>
                      <li>市场情绪指标</li>
                    </ul>
                  </div>
                  <div>
                    <strong className="block mb-2 text-gray-700 dark:text-gray-300">注意事项：</strong>
                    <ul className="list-disc list-inside space-y-1.5">
                      <li>仅同步交易日数据</li>
                      <li>建议按需同步近期数据</li>
                      <li>同步完成后可在&ldquo;情绪数据&rdquo;页面查看</li>
                      <li>注意数据源API限流</li>
                    </ul>
                  </div>
                </div>
              </div>
            </details>
          </div>
        </CardContent>
      </Card>

      {/* 注意事项 */}
      <Card className="bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800">
        <CardHeader>
          <CardTitle className="text-lg text-yellow-900 dark:text-yellow-200">
            重要提示
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm text-yellow-800 dark:text-yellow-300">
            <li className="flex items-start">
              <span className="mr-2">•</span>
              <span>数据源可在系统设置中切换（AkShare 或 Tushare）</span>
            </li>
            <li className="flex items-start">
              <span className="mr-2">•</span>
              <span>完成初始化后，建议配置定时任务实现数据自动更新</span>
            </li>
            <li className="flex items-start">
              <span className="mr-2">•</span>
              <span>如遇到大量失败，建议减小日期范围或稍后重试</span>
            </li>
            <li className="flex items-start">
              <span className="mr-2">•</span>
              <span>系统会自动检查数据完整性，已有完整数据的股票会被跳过</span>
            </li>
          </ul>
        </CardContent>
      </Card>
      </div>
  )
}
