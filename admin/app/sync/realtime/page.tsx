'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import AdminLayout from '@/components/layouts/AdminLayout'
import { apiClient } from '@/lib/api-client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface SyncStatus {
  status: string
  last_sync_date: string
  progress: number
  total: number
  completed: number
}

interface DataSourceConfig {
  data_source: string
  realtime_data_source: string
  tushare_token: string
}

export default function RealtimeSyncPage() {
  const router = useRouter()
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null)
  const [dataSource, setDataSource] = useState<DataSourceConfig | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [updateMode, setUpdateMode] = useState<'full' | 'incremental'>('incremental')
  const [batchSize, setBatchSize] = useState(100)

  useEffect(() => {
    loadSyncStatus()
    loadDataSource()
  }, [])

  const loadSyncStatus = async () => {
    try {
      const response = await apiClient.getSyncStatus()
      if (response.data) {
        setSyncStatus(response.data)
      }
    } catch (err) {
      console.error('Failed to load sync status:', err)
    }
  }

  const loadDataSource = async () => {
    try {
      const response = await apiClient.getDataSourceConfig()
      if (response.data) {
        setDataSource(response.data)
      }
    } catch (err) {
      console.error('Failed to load data source config:', err)
    }
  }

  const handleSync = async () => {
    try {
      setIsLoading(true)
      setError(null)
      setSuccessMessage(null)

      const params = updateMode === 'incremental'
        ? { update_oldest: true, batch_size: batchSize }
        : {}

      const response = await apiClient.syncRealtimeQuotes(params)

      if (response.data) {
        const { total, batch_size: actualBatchSize, update_mode, updated_at } = response.data
        const modeText = update_mode === 'oldest_first' ? '渐进式更新' : '全量更新'
        setSuccessMessage(`${modeText}成功！共 ${total} 只股票，批次大小: ${actualBatchSize}，更新时间: ${updated_at}`)
      }

      await loadSyncStatus()
      setTimeout(() => setSuccessMessage(null), 5000)
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || '获取实时行情失败'
      setError(errorMessage)
      console.error('Sync error:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
      case 'completed': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
      case 'failed': return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'running': return '同步中'
      case 'completed': return '已完成'
      case 'failed': return '失败'
      default: return '空闲'
    }
  }

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* 返回按钮 */}
        <button
        onClick={() => router.back()}
        className="text-blue-600 dark:text-blue-400 hover:underline flex items-center"
      >
        ← 返回同步管理
      </button>

      {/* 页面标题 */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          实时行情同步
        </h1>
        <p className="text-gray-600 dark:text-gray-300 mt-2">
          获取最新的实时行情快照，包括当前价格、涨跌幅、成交量等关键指标
        </p>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      {/* 成功提示 */}
      {successMessage && (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
          <p className="text-green-800 dark:text-green-200">{successMessage}</p>
        </div>
      )}

      {/* 当前同步状态 */}
      <Card>
        <CardHeader>
          <CardTitle>当前同步状态</CardTitle>
        </CardHeader>
        <CardContent>
        {syncStatus ? (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">状态</div>
              <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(syncStatus.status)}`}>
                {getStatusText(syncStatus.status)}
              </span>
            </div>
            <div>
              <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">最后同步</div>
              <div className="font-medium text-gray-900 dark:text-white">
                {syncStatus.last_sync_date || '未同步'}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">股票总数</div>
              <div className="font-medium text-gray-900 dark:text-white">
                {syncStatus.total || 0}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">完成率</div>
              <div className="font-medium text-gray-900 dark:text-white">
                {syncStatus.progress}%
              </div>
            </div>
          </div>
        ) : (
          <div className="text-gray-600 dark:text-gray-400">加载状态中...</div>
        )}
        </CardContent>
      </Card>

      {/* 同步操作 */}
      <Card>
        <CardHeader>
          <CardTitle>获取实时行情</CardTitle>
        </CardHeader>
        <CardContent>
        <div className="space-y-4">
          {/* 更新模式选择 */}
          <div className="space-y-3">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">更新模式</label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <label className={`flex items-start p-4 border-2 rounded-lg cursor-pointer transition-colors ${
                updateMode === 'incremental'
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                  : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
              }`}>
                <input
                  type="radio"
                  name="updateMode"
                  value="incremental"
                  checked={updateMode === 'incremental'}
                  onChange={() => setUpdateMode('incremental')}
                  className="mt-1 mr-3"
                />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900 dark:text-white">渐进式更新</span>
                    <span className="px-2 py-0.5 text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200 rounded">
                      推荐
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    优先更新最旧的数据，每次更新{batchSize}只股票
                  </p>
                  <div className="mt-2 text-xs text-gray-500">
                    <p>• 耗时短（约{Math.ceil(batchSize * 0.3 / 60)}分钟）</p>
                    <p>• 可重复执行，逐步覆盖全部股票</p>
                    <p>• 适合定时任务</p>
                  </div>
                </div>
              </label>

              <label className={`flex items-start p-4 border-2 rounded-lg cursor-pointer transition-colors ${
                updateMode === 'full'
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                  : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
              }`}>
                <input
                  type="radio"
                  name="updateMode"
                  value="full"
                  checked={updateMode === 'full'}
                  onChange={() => setUpdateMode('full')}
                  className="mt-1 mr-3"
                />
                <div className="flex-1">
                  <div className="font-medium text-gray-900 dark:text-white">全量更新</div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    一次性更新所有股票的实时行情
                  </p>
                  <div className="mt-2 text-xs text-gray-500">
                    <p>• 耗时长（3-5分钟）</p>
                    <p>• 容易超时</p>
                    <p>• 仅建议在交易时段使用</p>
                  </div>
                </div>
              </label>
            </div>
          </div>

          {/* 批次大小设置（仅渐进式更新） */}
          {updateMode === 'incremental' && (
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">批次大小</label>
              <select
                value={batchSize}
                onChange={(e) => setBatchSize(Number(e.target.value))}
                className="w-full md:w-48 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
              >
                <option value={50}>50只（约0.5分钟）</option>
                <option value={100}>100只（约1分钟）</option>
                <option value={200}>200只（约2分钟）</option>
                <option value={500}>500只（约3分钟）</option>
              </select>
            </div>
          )}

          {/* AkShare 数据源警告 */}
          {dataSource?.realtime_data_source?.toLowerCase() === 'akshare' && updateMode === 'full' && (
            <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3">
              <p className="text-sm text-yellow-800 dark:text-yellow-300">
                <strong>AkShare全量更新说明：</strong>需要分批次爬取东方财富网数据，
                <strong>耗时约3-5分钟</strong>（共58个批次）。网络不稳定时可能会失败。
                建议使用<strong>渐进式更新</strong>或在<strong>交易时段（9:30-15:00）</strong>使用。
              </p>
            </div>
          )}

          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
            <p className="text-sm text-blue-800 dark:text-blue-300">
              <strong>实时性说明：</strong>实时行情数据通常有 <strong>3-5 秒的延迟</strong>，非 Level-2 高频数据。
              适用于监控市场整体情况和快速筛选热门股票。
            </p>
          </div>

          <button
            onClick={handleSync}
            disabled={isLoading}
            className="btn-primary w-full md:w-auto disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? '更新中...' : `开始${updateMode === 'incremental' ? '渐进式' : '全量'}更新`}
          </button>
        </div>
        </CardContent>
      </Card>

      {/* 数据说明 */}
      <Card className="bg-gray-50 dark:bg-gray-800">
        <CardHeader>
          <CardTitle className="text-lg">数据说明</CardTitle>
        </CardHeader>
        <CardContent>
        <div className="space-y-2 text-sm text-gray-700 dark:text-gray-300">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <strong>数据内容：</strong>
              <ul className="list-disc list-inside mt-1 space-y-1">
                <li>股票代码、名称</li>
                <li>最新价格</li>
                <li>涨跌额、涨跌幅</li>
                <li>今日开盘价、收盘价</li>
                <li>今日最高价、最低价</li>
                <li>成交量、成交额</li>
                <li>换手率、市盈率</li>
                <li>总市值、流通市值</li>
                <li>振幅、量比</li>
              </ul>
            </div>
            <div>
              <strong>数据用途：</strong>
              <ul className="list-disc list-inside mt-1 space-y-1">
                <li>市场整体监控</li>
                <li>热门股票筛选</li>
                <li>涨跌幅排行</li>
                <li>异动股票捕捉</li>
                <li>实时选股条件筛选</li>
                <li>盘中监控和提醒</li>
                <li>成交量异常分析</li>
                <li>资金流向监控</li>
              </ul>
            </div>
          </div>
        </div>
        </CardContent>
      </Card>

      {/* 应用场景 */}
      <Card className="bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800">
        <CardHeader>
          <CardTitle className="text-lg text-purple-900 dark:text-purple-200">典型应用场景</CardTitle>
        </CardHeader>
        <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-purple-800 dark:text-purple-300">
          <div>
            <strong>场景 1: 市场概览</strong>
            <p className="mt-1">快速了解当前市场的整体涨跌情况，识别市场热点板块和个股。</p>
          </div>
          <div>
            <strong>场景 2: 实时选股</strong>
            <p className="mt-1">根据涨跌幅、成交量、换手率等指标，实时筛选符合条件的股票。</p>
          </div>
          <div>
            <strong>场景 3: 异动监控</strong>
            <p className="mt-1">监控成交量放大、价格急涨急跌等异常情况，及时捕捉交易机会。</p>
          </div>
          <div>
            <strong>场景 4: 盘中提醒</strong>
            <p className="mt-1">设置价格或涨跌幅阈值，盘中自动监控并发送提醒通知。</p>
          </div>
        </div>
        </CardContent>
      </Card>

      {/* 注意事项 */}
      <Card className="bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800">
        <CardHeader>
          <CardTitle className="text-lg text-yellow-900 dark:text-yellow-200">注意事项</CardTitle>
        </CardHeader>
        <CardContent>
        <ul className="space-y-2 text-sm text-yellow-800 dark:text-yellow-300">
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>实时行情数据<strong>仅在交易时间段（9:30-15:00）有效</strong>，非交易时段显示前一交易日收盘数据</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>数据通常有 <strong>3-5 秒延迟</strong>，不适用于高频交易或精确的短线操作</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>实时行情数据<strong>暂未保存到数据库</strong>，当前版本仅用于实时查询和筛选</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>请勿<strong>频繁刷新</strong>（建议间隔至少 5-10 秒），避免触发 API 限流</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>部分数据源对<strong>实时行情接口有调用频率限制</strong>，请合理使用</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>数据源可在<a href="/settings" className="underline">系统设置</a>中切换（AkShare 或 Tushare）</span>
          </li>
          </ul>
        </CardContent>
      </Card>

      {/* 交易时间提示 */}
      <Card className="bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800">
        <CardHeader>
          <CardTitle className="text-lg text-green-900 dark:text-green-200">A股交易时间</CardTitle>
        </CardHeader>
        <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-green-800 dark:text-green-300">
          <div>
            <strong>上午交易时段（集合竞价）</strong>
            <p className="mt-1">09:15 - 09:25（集合竞价）</p>
            <p>09:25 - 09:30（集合竞价撮合）</p>
          </div>
          <div>
            <strong>上午交易时段（连续竞价）</strong>
            <p className="mt-1">09:30 - 11:30</p>
          </div>
          <div>
            <strong>下午交易时段（连续竞价）</strong>
            <p className="mt-1">13:00 - 15:00</p>
          </div>
          <div>
            <strong>尾盘集合竞价（深圳）</strong>
            <p className="mt-1">14:57 - 15:00</p>
          </div>
        </div>
        <p className="text-xs text-green-700 dark:text-green-400 mt-3">
          * 非交易时段获取的数据为前一交易日的收盘数据
        </p>
        </CardContent>
      </Card>
      </div>
    </AdminLayout>
  )
}
