'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { toast } from 'sonner'
import {
  RefreshCw, Database, ChevronDown, ChevronRight,
  XCircle, Loader2, RotateCcw, Zap, Settings, KeyRound, Clock, Play
} from 'lucide-react'

import { PageHeader } from '@/components/common/PageHeader'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '@/components/ui/select'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle
} from '@/components/ui/dialog'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { syncDashboardApi, type SyncOverviewItem, type CategoryStat, type SyncConfigUpdate, type ScheduleUpdate, type SyncStrategy, type ApiParams } from '@/lib/api/sync-dashboard'
import { apiClient } from '@/lib/api-client'
import { useTaskStore } from '@/stores/task-store'
import { useConfigStore } from '@/stores/config-store'
import Link from 'next/link'

const STRATEGY_LABELS: Record<string, string> = {
  by_ts_code: '逐只股票',
  by_date: '按日切片',
  by_week: '按周切片',
  by_month: '按月切片',
  by_quarter: '按季度切片',
  snapshot: '快照',
  none: '无全量',
}

const STRATEGY_OPTIONS = [
  { value: 'by_ts_code', label: '逐只股票' },
  { value: 'by_date', label: '按日切片' },
  { value: 'by_week', label: '按周切片' },
  { value: 'by_month', label: '按月切片' },
  { value: 'by_quarter', label: '按季度切片' },
  { value: 'snapshot', label: '快照' },
  { value: 'none', label: '无全量' },
]

// 增量同步策略选项（比全量策略更精简）
const INCREMENTAL_STRATEGY_OPTIONS = [
  { value: 'by_ts_code', label: '逐只股票' },
  { value: 'by_date_range', label: '按时间段' },
  { value: 'by_date', label: '逐日切片' },
  { value: 'snapshot', label: '快照' },
  { value: 'none', label: '无' },
]

const CATEGORY_ORDER = [
  '基础数据', '行情数据', '财务数据', '参考数据',
  '特色数据', '两融及转融通', '资金流向', '打板专题',
]

function formatDuration(ms: number | null): string {
  if (!ms) return '-'
  if (ms < 60000) return `${(ms / 1000).toFixed(0)}s`
  if (ms < 3600000) return `${(ms / 60000).toFixed(1)}m`
  return `${(ms / 3600000).toFixed(1)}h`
}

function formatDate(iso: string | null): string {
  if (!iso) return '-'
  const d = new Date(iso)
  const now = new Date()
  const diffH = (now.getTime() - d.getTime()) / 3600000
  if (diffH < 24) return `${diffH.toFixed(0)}h 前`
  if (diffH < 168) return `${(diffH / 24).toFixed(0)}d 前`
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function StatusDot({ status }: { status: string | undefined | null }) {
  if (!status) return <span className="w-2 h-2 rounded-full bg-gray-300 inline-block" />
  const map: Record<string, string> = {
    success: 'bg-green-500',
    running: 'bg-blue-500 animate-pulse',
    pending: 'bg-yellow-400 animate-pulse',
    failure: 'bg-red-500',
  }
  return <span className={`w-2 h-2 rounded-full ${map[status] || 'bg-gray-300'} inline-block`} />
}

function TestDatasourceDialog({
  item,
  open,
  onOpenChange,
  onSaved,
}: {
  item: SyncOverviewItem | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onSaved: () => void
}) {
  // 接口信息编辑表单
  const [configForm, setConfigForm] = useState<SyncConfigUpdate>({})
  const [isSaving, setIsSaving] = useState(false)

  // 测试参数
  const [testParams, setTestParams] = useState<Record<string, string>>({})
  const [limit, setLimit] = useState(5)
  const [offset, setOffset] = useState(0)
  const [isTesting, setIsTesting] = useState(false)
  const [responseText, setResponseText] = useState('')

  // 打开弹窗时重置状态
  useEffect(() => {
    if (open && item) {
      setConfigForm({
        api_name: item.api_name,
        description: item.description,
        doc_url: item.doc_url,
        api_limit: item.api_limit ?? 2000,
        api_params: item.api_params ?? { ts_code: 'none', trade_date: 'none', start_date: false, end_date: false },
      })
      const initParams: Record<string, string> = {}
      const ap = item.api_params
      if (ap) {
        if (ap.ts_code !== 'none') initParams.ts_code = ''
        if (ap.trade_date !== 'none') initParams.trade_date = ''
        if (ap.start_date) initParams.start_date = ''
        if (ap.end_date) initParams.end_date = ''
        if (ap.special_params) {
          Object.keys(ap.special_params).forEach(k => { initParams[k] = '' })
        }
      }
      setTestParams(initParams)
      setLimit(5)
      setOffset(0)
      setResponseText('')
    }
  }, [open, item])

  const handleSave = async () => {
    if (!item) return
    setIsSaving(true)
    try {
      const resp = await syncDashboardApi.updateConfig(item.table_key, configForm)
      if (resp.code === 200) {
        toast.success('接口配置已保存')
        onSaved()
      } else {
        toast.error(resp.message || '保存失败')
      }
    } catch {
      toast.error('保存失败，请重试')
    } finally {
      setIsSaving(false)
    }
  }

  const handleTest = async () => {
    const apiName = (configForm.api_name ?? item?.api_name ?? '').trim()
    if (!apiName) {
      setResponseText('错误：接口名称不能为空')
      return
    }
    setIsTesting(true)
    setResponseText('')
    try {
      const resp = await syncDashboardApi.testDatasource({
        api_name: apiName,
        params: testParams,
        limit,
        offset,
      })
      if (resp.code === 200 && resp.data) {
        const d = resp.data
        const header = `// ${resp.message}\n// 字段: ${d.columns.join(', ')}\n// 参数: ${JSON.stringify(d.params)}\n\n`
        setResponseText(header + JSON.stringify(d.rows, null, 2))
      } else {
        setResponseText(`错误 (${resp.code}): ${resp.message || '未知错误'}`)
      }
    } catch (err: any) {
      setResponseText(`请求异常: ${err.message || '未知错误'}`)
    } finally {
      setIsTesting(false)
    }
  }

  const editApiParams = configForm.api_params as ApiParams | undefined
  const apiName = configForm.api_name ?? item?.api_name ?? ''

  // 构建请求体预览
  const buildRequestBody = () => {
    const fields: Record<string, string> = {}
    for (const [k, v] of Object.entries(testParams)) {
      if (v) fields[k] = v
    }
    return {
      api_name: apiName,
      token: '***',
      params: { ...fields, limit, offset: offset || undefined },
      fields: '',
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[760px] max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Database className="h-4 w-4" />
            数据源配置与测试
          </DialogTitle>
          <DialogDescription>
            {item?.display_name}（{item?.table_key}）
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="config" className="flex-1 min-h-0">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="config">接口配置</TabsTrigger>
            <TabsTrigger value="test">接口测试</TabsTrigger>
          </TabsList>

          {/* ===== Tab 1: 接口配置 ===== */}
          <TabsContent value="config" className="overflow-y-auto max-h-[calc(90vh-200px)] space-y-4 py-2">
            <div className="text-xs font-medium text-gray-500 uppercase tracking-wide border-b pb-1">接口信息</div>
            <div className="grid grid-cols-4 items-center gap-3">
              <Label className="text-right text-sm">接口名称</Label>
              <Input
                className="col-span-3 font-mono text-sm" placeholder="如 income_vip"
                value={configForm.api_name ?? ''}
                onChange={e => setConfigForm(prev => ({ ...prev, api_name: e.target.value || null }))}
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-3">
              <Label className="text-right text-sm">文档链接</Label>
              <div className="col-span-3 flex items-center gap-2">
                <Input
                  className="flex-1 text-sm" placeholder="https://tushare.pro/document/..."
                  value={configForm.doc_url ?? ''}
                  onChange={e => setConfigForm(prev => ({ ...prev, doc_url: e.target.value || null }))}
                />
                {configForm.doc_url && (
                  <a href={configForm.doc_url} target="_blank" rel="noopener noreferrer"
                    className="text-blue-500 hover:underline text-xs whitespace-nowrap">打开</a>
                )}
              </div>
            </div>
            <div className="grid grid-cols-4 items-start gap-3">
              <Label className="text-right text-sm pt-2">描述</Label>
              <textarea
                className="col-span-3 min-h-[50px] rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 resize-none"
                placeholder="数据说明"
                value={configForm.description ?? ''}
                onChange={e => setConfigForm(prev => ({ ...prev, description: e.target.value || null }))}
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-3">
              <Label className="text-right text-sm">请求限量</Label>
              <div className="col-span-3 flex items-center gap-2">
                <Input
                  type="number" min={100} step={100} className="w-28 text-sm"
                  placeholder="2000"
                  value={configForm.api_limit ?? ''}
                  onChange={e => setConfigForm(prev => ({ ...prev, api_limit: e.target.value === '' ? null : Number(e.target.value) }))}
                />
                <span className="text-xs text-gray-400">条/次</span>
              </div>
            </div>

            <div className="text-xs font-medium text-gray-500 uppercase tracking-wide border-b pb-1 pt-2">接口参数约束</div>
            <div className="grid grid-cols-4 items-center gap-3">
              <Label className="text-right text-sm">ts_code</Label>
              <Select
                value={editApiParams?.ts_code ?? 'none'}
                onValueChange={v => setConfigForm(prev => ({
                  ...prev,
                  api_params: { ...prev.api_params as ApiParams, ts_code: v as ApiParams['ts_code'] }
                }))}
              >
                <SelectTrigger className="col-span-3"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">不支持</SelectItem>
                  <SelectItem value="optional">可选</SelectItem>
                  <SelectItem value="required">必填（或至少传一个）</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-4 items-center gap-3">
              <Label className="text-right text-sm">trade_date</Label>
              <Select
                value={editApiParams?.trade_date ?? 'none'}
                onValueChange={v => setConfigForm(prev => ({
                  ...prev,
                  api_params: { ...prev.api_params as ApiParams, trade_date: v as ApiParams['trade_date'] }
                }))}
              >
                <SelectTrigger className="col-span-3"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">不支持</SelectItem>
                  <SelectItem value="optional">可选</SelectItem>
                  <SelectItem value="required">必填</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-4 items-center gap-3">
              <Label className="text-right text-sm">日期范围</Label>
              <div className="col-span-3 flex items-center gap-2">
                <Switch
                  checked={editApiParams?.start_date ?? false}
                  onCheckedChange={v => setConfigForm(prev => ({
                    ...prev,
                    api_params: { ...prev.api_params as ApiParams, start_date: v, end_date: v }
                  }))}
                />
                <span className="text-sm text-gray-500">
                  {editApiParams?.start_date ? '支持 start_date / end_date' : '不支持'}
                </span>
              </div>
            </div>
            {editApiParams?.special_params && Object.keys(editApiParams.special_params).length > 0 && (
              <div className="grid grid-cols-4 items-start gap-3">
                <Label className="text-right text-sm pt-1">特殊参数</Label>
                <div className="col-span-3 text-xs text-gray-500 space-y-0.5">
                  {Object.entries(editApiParams.special_params).map(([k, v]) => (
                    <div key={k}><span className="font-mono text-gray-600">{k}</span>: {v}</div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex justify-end pt-2">
              <Button size="sm" onClick={handleSave} disabled={isSaving}>
                {isSaving ? '保存中...' : '保存配置'}
              </Button>
            </div>
          </TabsContent>

          {/* ===== Tab 2: 接口测试 ===== */}
          <TabsContent value="test" className="overflow-y-auto max-h-[calc(90vh-200px)] space-y-4 py-2">
            {/* 远程接口信息 */}
            <div className="rounded-md bg-gray-50 border p-3 space-y-1">
              <div className="flex items-center gap-2 text-sm">
                <Badge variant="secondary" className="font-mono text-xs">POST</Badge>
                <code className="text-blue-600 text-xs">http://api.tushare.pro</code>
              </div>
              <div className="text-xs text-gray-500 font-mono">
                api_name: <span className="text-gray-800">{apiName || '(未配置)'}</span>
              </div>
            </div>

            {/* 参数表单 */}
            <div className="text-xs font-medium text-gray-500 uppercase tracking-wide border-b pb-1">请求参数</div>

            {editApiParams?.ts_code !== 'none' && (
              <div className="grid grid-cols-4 items-center gap-3">
                <Label className="text-right text-sm">
                  ts_code
                  {editApiParams?.ts_code === 'required' && <span className="text-red-500 ml-0.5">*</span>}
                </Label>
                <Input
                  className="col-span-3 font-mono text-sm" placeholder="如 000001.SZ"
                  value={testParams.ts_code ?? ''}
                  onChange={e => setTestParams(p => ({ ...p, ts_code: e.target.value }))}
                />
              </div>
            )}

            {editApiParams?.trade_date !== 'none' && (
              <div className="grid grid-cols-4 items-center gap-3">
                <Label className="text-right text-sm">
                  trade_date
                  {editApiParams?.trade_date === 'required' && <span className="text-red-500 ml-0.5">*</span>}
                </Label>
                <Input
                  className="col-span-3 font-mono text-sm" placeholder="如 20260414"
                  value={testParams.trade_date ?? ''}
                  onChange={e => setTestParams(p => ({ ...p, trade_date: e.target.value }))}
                />
              </div>
            )}

            {editApiParams?.start_date && (
              <div className="grid grid-cols-4 items-center gap-3">
                <Label className="text-right text-sm">start_date</Label>
                <Input
                  className="col-span-3 font-mono text-sm" placeholder="如 20260401"
                  value={testParams.start_date ?? ''}
                  onChange={e => setTestParams(p => ({ ...p, start_date: e.target.value }))}
                />
              </div>
            )}

            {editApiParams?.end_date && (
              <div className="grid grid-cols-4 items-center gap-3">
                <Label className="text-right text-sm">end_date</Label>
                <Input
                  className="col-span-3 font-mono text-sm" placeholder="如 20260414"
                  value={testParams.end_date ?? ''}
                  onChange={e => setTestParams(p => ({ ...p, end_date: e.target.value }))}
                />
              </div>
            )}

            {editApiParams?.special_params && Object.entries(editApiParams.special_params).map(([key, desc]) => (
              <div key={key} className="grid grid-cols-4 items-center gap-3">
                <Label className="text-right text-sm">
                  {key}
                  {desc?.includes('必填') && <span className="text-red-500 ml-0.5">*</span>}
                </Label>
                <div className="col-span-3">
                  <Input
                    className="font-mono text-sm" placeholder={desc}
                    value={testParams[key] ?? ''}
                    onChange={e => setTestParams(p => ({ ...p, [key]: e.target.value }))}
                  />
                  <p className="text-xs text-gray-400 mt-0.5">{desc}</p>
                </div>
              </div>
            ))}

            <div className="grid grid-cols-4 items-center gap-3">
              <Label className="text-right text-sm">limit</Label>
              <div className="col-span-3 flex items-center gap-3">
                <Input
                  type="number" min={1} className="w-24 text-sm"
                  value={limit}
                  onChange={e => setLimit(Math.max(1, Number(e.target.value) || 5))}
                />
                <Label className="text-sm">offset</Label>
                <Input
                  type="number" min={0} className="w-24 text-sm"
                  value={offset}
                  onChange={e => setOffset(Math.max(0, Number(e.target.value) || 0))}
                />
              </div>
            </div>

            {/* 请求体预览 */}
            <details className="text-xs">
              <summary className="cursor-pointer text-gray-400 hover:text-gray-600">请求体预览 (JSON)</summary>
              <pre className="mt-1 p-2 bg-gray-50 border rounded text-[11px] font-mono overflow-auto max-h-[120px]">
                {JSON.stringify(buildRequestBody(), null, 2)}
              </pre>
            </details>

            {/* 发起测试 */}
            <div className="flex justify-end">
              <Button onClick={handleTest} disabled={isTesting || !apiName}>
                {isTesting ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : <Play className="w-4 h-4 mr-1" />}
                {isTesting ? '请求中...' : '发送请求'}
              </Button>
            </div>

            {/* 响应结果 */}
            <div className="text-xs font-medium text-gray-500 uppercase tracking-wide border-b pb-1">响应结果</div>
            <textarea
              readOnly
              className="w-full h-[300px] rounded-md border bg-gray-900 text-green-400 px-3 py-2 text-xs font-mono resize-y focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              value={responseText || '// 点击「发送请求」查看结果'}
              placeholder="// 点击「发送请求」查看结果"
            />
          </TabsContent>
        </Tabs>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>关闭</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function SyncRow({
  item,
  onSync,
  onClearProgress,
  onEdit,
  onTest,
}: {
  item: SyncOverviewItem
  onSync: (item: SyncOverviewItem, type: 'incremental' | 'full') => void
  onClearProgress: (item: SyncOverviewItem) => void
  onEdit: (item: SyncOverviewItem) => void
  onTest: (item: SyncOverviewItem) => void
}) {
  const isTaskRunning = useTaskStore(state => state.isTaskRunning)
  const incTask = item.last_incremental
  const fullTask = item.last_full_sync
  const progress = item.redis_progress
  const hasFullSync = !!item.full_sync_task_name
  // 增量和全量共用同一任务（基础数据类），没有独立全量路由
  const isSharedTask = hasFullSync && item.full_sync_task_name === item.incremental_task_name
  const isIncrSyncing = item.incremental_task_name ? isTaskRunning(item.incremental_task_name) : false
  const isFullSyncing = item.full_sync_task_name ? isTaskRunning(item.full_sync_task_name) : false

  return (
    <div className="grid grid-cols-12 gap-2 items-center py-2.5 px-3 border-b border-gray-100 hover:bg-gray-50 text-sm">
      {/* 名称 */}
      <div className="col-span-3 min-w-0">
        <div className="flex items-center gap-1.5">
          {item.page_url ? (
            <Link href={item.page_url} className="font-medium text-blue-600 hover:underline truncate">
              {item.display_name}
            </Link>
          ) : (
            <span className="font-medium truncate">{item.display_name}</span>
          )}
          {item.passive_sync_enabled && (
            <Zap className="w-3 h-3 text-yellow-500 flex-shrink-0" aria-label="已启用被动同步" />
          )}
        </div>
        {item.last_data_date && (
          <div className="text-xs text-gray-400 mt-0.5">
            数据至 {item.last_data_date.replace(/^(\d{4})(\d{2})(\d{2})$/, '$1-$2-$3')}
          </div>
        )}
      </div>

      {/* 增量同步状态 */}
      <div className="col-span-3 min-w-0">
        <div className="flex items-center gap-1.5">
          <StatusDot status={incTask?.status} />
          <span className="text-gray-500 text-xs truncate">
            {incTask ? formatDate(incTask.completed_at || incTask.started_at) : '从未同步'}
            {incTask?.duration_ms && (
              <span className="ml-1 text-gray-400">({formatDuration(incTask.duration_ms)})</span>
            )}
          </span>
          {incTask?.status === 'failure' && (
            <XCircle className="w-3 h-3 text-red-500 flex-shrink-0" aria-label={incTask.error || '未知错误'} />
          )}
        </div>
        {item.incremental_schedule?.enabled && item.incremental_schedule.cron_expression && (
          <div className="flex items-center gap-1 mt-0.5">
            <Clock className="w-3 h-3 text-blue-400 flex-shrink-0" />
            <span className="text-[11px] text-blue-500 font-mono">{item.incremental_schedule.cron_expression}</span>
          </div>
        )}
      </div>

      {/* 全量同步状态 */}
      <div className="col-span-2 flex items-center gap-1.5 min-w-0">
        {hasFullSync ? (
          <>
            <StatusDot status={isSharedTask ? incTask?.status : fullTask?.status} />
            <span className="text-gray-500 text-xs truncate" title={isSharedTask ? '共用增量任务，以最早日期为起点全量同步' : undefined}>
              {isSharedTask
                ? (incTask ? formatDate(incTask.completed_at || incTask.started_at) : '从未同步')
                : (fullTask ? formatDate(fullTask.completed_at || fullTask.started_at) : '从未同步')
              }
            </span>
            {!isSharedTask && progress && (
              <Badge
                variant="outline"
                className="text-xs py-0 px-1 text-orange-600 border-orange-300 cursor-default"
                title={`Redis中有 ${progress.completed_count} 条进度记录，下次全量同步将续继`}
              >
                续继 {progress.completed_count}
              </Badge>
            )}
          </>
        ) : (
          <span className="text-gray-400 text-xs">
            {item.full_sync_strategy === 'snapshot' ? '快照' : '-'}
          </span>
        )}
      </div>

      {/* 策略 + 接口参数 */}
      <div className="col-span-2 text-xs text-gray-400">
        {item.full_sync_strategy && item.full_sync_strategy !== 'none'
          ? STRATEGY_LABELS[item.full_sync_strategy] : ''}
        {item.api_name ? (
          <div className="text-gray-300 truncate" title={item.api_name}>{item.api_name}</div>
        ) : null}
        {item.api_params && (
          <div className="flex flex-wrap gap-0.5 mt-0.5">
            {item.api_params.ts_code !== 'none' && (
              <span className={`px-1 rounded text-[10px] ${
                item.api_params.ts_code === 'required' ? 'bg-red-100 text-red-600' : 'bg-gray-100 text-gray-500'
              }`} title={item.api_params.ts_code === 'required' ? 'ts_code 必填或至少传一个' : 'ts_code 可选'}>
                code{item.api_params.ts_code === 'required' ? '*' : ''}
              </span>
            )}
            {item.api_params.trade_date !== 'none' && (
              <span className={`px-1 rounded text-[10px] ${
                item.api_params.trade_date === 'required' ? 'bg-red-100 text-red-600' : 'bg-gray-100 text-gray-500'
              }`} title={item.api_params.trade_date === 'required' ? 'trade_date 必填' : 'trade_date 可选'}>
                日期{item.api_params.trade_date === 'required' ? '*' : ''}
              </span>
            )}
            {item.api_params.start_date && (
              <span className="px-1 rounded text-[10px] bg-green-50 text-green-600" title="支持 start_date/end_date 日期范围查询">
                范围
              </span>
            )}
            {item.api_params.special_params?.month && (
              <span className="px-1 rounded text-[10px] bg-purple-100 text-purple-600" title="month 必填 (YYYYMM)">
                月*
              </span>
            )}
          </div>
        )}
      </div>

      {/* 操作按钮 */}
      <div className="col-span-2 flex items-center justify-end gap-1">
        {item.incremental_task_name && (
          <Button size="sm" variant="outline" className="h-6 px-2 text-xs"
            disabled={isIncrSyncing} onClick={() => onSync(item, 'incremental')}>
            {isIncrSyncing ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
            <span className="ml-1 hidden lg:inline">增量</span>
          </Button>
        )}
        {hasFullSync && (
          <Button size="sm" variant="outline"
            className="h-6 px-2 text-xs border-orange-200 text-orange-700 hover:bg-orange-50"
            disabled={isFullSyncing} onClick={() => onSync(item, 'full')}>
            {isFullSyncing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Database className="w-3 h-3" />}
            <span className="ml-1 hidden lg:inline">全量</span>
          </Button>
        )}
        {progress && (
          <Button size="sm" variant="ghost" className="h-6 px-1.5 text-gray-400 hover:text-red-500"
            onClick={() => onClearProgress(item)}>
            <RotateCcw className="w-3 h-3" />
          </Button>
        )}
        {item.api_name && (
          <Button size="sm" variant="ghost" className="h-6 px-1.5 text-gray-400 hover:text-green-600"
            title="测试接口" onClick={() => onTest(item)}>
            <Play className="w-3 h-3" />
          </Button>
        )}
        <Button size="sm" variant="ghost" className="h-6 px-1.5 text-gray-400 hover:text-blue-600"
          onClick={() => onEdit(item)}>
          <Settings className="w-3 h-3" />
        </Button>
      </div>
    </div>
  )
}

function CategorySection({
  category, items, onSync, onClearProgress, onEdit, onTest,
}: {
  category: string
  items: SyncOverviewItem[]
  onSync: (item: SyncOverviewItem, type: 'incremental' | 'full') => void
  onClearProgress: (item: SyncOverviewItem) => void
  onEdit: (item: SyncOverviewItem) => void
  onTest: (item: SyncOverviewItem) => void
}) {
  const [expanded, setExpanded] = useState(true)
  const failureCount = items.filter(
    i => i.last_incremental?.status === 'failure' || i.last_full_sync?.status === 'failure'
  ).length
  const progressCount = items.filter(i => i.redis_progress).length

  return (
    <Card className="overflow-hidden">
      <div
        className="flex items-center justify-between px-4 py-2.5 bg-gray-50 cursor-pointer hover:bg-gray-100"
        onClick={() => setExpanded(e => !e)}
      >
        <div className="flex items-center gap-2">
          {expanded
            ? <ChevronDown className="w-4 h-4 text-gray-500" />
            : <ChevronRight className="w-4 h-4 text-gray-500" />}
          <span className="font-medium text-sm">{category}</span>
          <Badge variant="secondary" className="text-xs">{items.length}</Badge>
          {failureCount > 0 && (
            <Badge variant="destructive" className="text-xs">{failureCount} 失败</Badge>
          )}
          {progressCount > 0 && (
            <Badge variant="outline" className="text-xs text-orange-600 border-orange-300">
              {progressCount} 可续继
            </Badge>
          )}
        </div>
      </div>
      {expanded && (
        <>
          <div className="grid grid-cols-12 gap-2 px-3 py-1.5 bg-gray-50 border-b text-xs text-gray-500 font-medium">
            <div className="col-span-3">数据表</div>
            <div className="col-span-3">增量同步</div>
            <div className="col-span-2">全量同步</div>
            <div className="col-span-2">策略</div>
            <div className="col-span-2 text-right">操作</div>
          </div>
          {items.map(item => (
            <SyncRow
              key={item.table_key}
              item={item}
              onSync={onSync}
              onClearProgress={onClearProgress}
              onEdit={onEdit}
              onTest={onTest}
            />
          ))}
        </>
      )}
    </Card>
  )
}

export default function SyncConfigPage() {
  const [items, setItems] = useState<SyncOverviewItem[]>([])
  const [categories, setCategories] = useState<CategoryStat[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState<string>('全部')
  const [searchText, setSearchText] = useState('')

  // 清除进度确认
  const [clearProgressItem, setClearProgressItem] = useState<SyncOverviewItem | null>(null)

  // 测试数据源弹窗
  const [testDialogOpen, setTestDialogOpen] = useState(false)
  const [testingItem, setTestingItem] = useState<SyncOverviewItem | null>(null)

  // 编辑配置弹窗
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [editingItem, setEditingItem] = useState<SyncOverviewItem | null>(null)
  const [editForm, setEditForm] = useState<SyncConfigUpdate>({})
  const [scheduleForm, setScheduleForm] = useState<ScheduleUpdate>({})
  const [isSaving, setIsSaving] = useState(false)

  // 全局配置弹窗
  const { dataSource: configData, fetchDataSourceConfig } = useConfigStore()
  const [globalConfigOpen, setGlobalConfigOpen] = useState(false)
  const [tokenInput, setTokenInput] = useState('')
  const [earliestDate, setEarliestDate] = useState('2021-01-04')
  const [maxRpmInput, setMaxRpmInput] = useState('0')
  const [isSavingGlobal, setIsSavingGlobal] = useState(false)

  useEffect(() => {
    if (globalConfigOpen) {
      fetchDataSourceConfig()
      setTokenInput('')
      setEarliestDate(configData?.earliest_history_date || '2021-01-04')
      setMaxRpmInput(String(configData?.max_requests_per_minute ?? 0))
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [globalConfigOpen])

  useEffect(() => {
    if (configData && globalConfigOpen) {
      setEarliestDate(configData.earliest_history_date || '2021-01-04')
      setMaxRpmInput(String(configData.max_requests_per_minute ?? 0))
    }
  }, [configData, globalConfigOpen])

  const handleSaveGlobal = async () => {
    setIsSavingGlobal(true)
    try {
      const tokenToSave = tokenInput.trim() ? tokenInput.trim() : undefined
      const maxRpm = parseInt(maxRpmInput, 10)
      await apiClient.updateDataSourceConfig({
        tushare_token: tokenToSave,
        earliest_history_date: earliestDate || undefined,
        max_requests_per_minute: isNaN(maxRpm) ? 0 : maxRpm,
      })
      fetchDataSourceConfig(true)
      toast.success('配置已保存')
      setGlobalConfigOpen(false)
    } catch (err: any) {
      toast.error(err.message || '保存配置失败')
    } finally {
      setIsSavingGlobal(false)
    }
  }

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback } = useTaskStore()
  const callbacksRef = useRef<Map<string, () => void>>(new Map())

  const loadData = useCallback(async (silent = false) => {
    if (!silent) setIsLoading(true)
    try {
      const cat = selectedCategory === '全部' ? undefined : selectedCategory
      const resp = await syncDashboardApi.getOverview(cat)
      if (resp.code === 200 && resp.data) {
        setItems(resp.data.items)
        setCategories(resp.data.categories)
      }
    } catch {
      if (!silent) toast.error('加载失败')
    } finally {
      if (!silent) setIsLoading(false)
    }
  }, [selectedCategory])

  useEffect(() => { loadData() }, [loadData])

  useEffect(() => {
    return () => {
      callbacksRef.current.forEach((cb, taskId) => unregisterCompletionCallback(taskId, cb))
      callbacksRef.current.clear()
    }
  }, [unregisterCompletionCallback])

  const handleSync = useCallback(async (item: SyncOverviewItem, type: 'incremental' | 'full') => {
    if (!item.api_prefix) return
    try {
      // 若增量和全量共用同一 Celery 任务（没有独立的 /sync-full-history 路由），
      // 全量同步直接调用 /sync-async 并传入 start_date，由后端以全量模式处理。
      const isSharedTask = type === 'full' && item.full_sync_task_name === item.incremental_task_name
      const endpoint = type === 'full' && !isSharedTask
        ? `/api${item.api_prefix}/sync-full-history`
        : `/api${item.api_prefix}/sync-async`
      const params: Record<string, string | number> = {}
      if (type === 'full') {
        if (!isSharedTask) {
          if (item.full_sync_concurrency) params.concurrency = item.full_sync_concurrency
          // 独立全量任务：start_date 由后端从任务默认值读取
          // 全量同步前先清除 Redis 续继进度，确保从头开始而非续继上次
          try {
            await syncDashboardApi.clearProgress(item.table_key)
          } catch {
            // 清除失败不阻止全量同步（Redis 可能无进度记录）
          }
        } else {
          // 共用任务（基础数据类）：传入 earliest_history_date 作为 start_date
          const earliest = configData?.earliest_history_date
          if (earliest) {
            params.start_date = earliest.replace(/-/g, '')
          }
        }
      }
      const resp = await apiClient.post(endpoint, null, { params })
      if (resp.code === 200 && resp.data) {
        const taskId = resp.data.celery_task_id
        addTask({
          taskId,
          taskName: resp.data.task_name,
          displayName: resp.data.display_name,
          taskType: 'data_sync',
          status: 'running',
          progress: 0,
          startTime: Date.now(),
        })
        const cb = () => {
          loadData(true)
          unregisterCompletionCallback(taskId, cb)
          callbacksRef.current.delete(taskId)
        }
        callbacksRef.current.set(taskId, cb)
        registerCompletionCallback(taskId, cb)
        triggerPoll()
        toast.success(`${item.display_name} ${type === 'incremental' ? '增量' : '全量'}同步已提交`)
      } else {
        throw new Error(resp.message || '提交失败')
      }
    } catch (err: any) {
      toast.error(`提交失败: ${err.message}`)
    }
  }, [addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, loadData])

  const handleClearProgress = useCallback(async () => {
    if (!clearProgressItem) return
    try {
      const resp = await syncDashboardApi.clearProgress(clearProgressItem.table_key)
      if (resp.code === 200) {
        toast.success(`${clearProgressItem.display_name} 进度已清除`)
        loadData(true)
      } else {
        throw new Error(resp.message)
      }
    } catch (err: any) {
      toast.error(`清除失败: ${err.message}`)
    } finally {
      setClearProgressItem(null)
    }
  }, [clearProgressItem, loadData])

  const openEditDialog = (item: SyncOverviewItem) => {
    setEditingItem(item)
    setEditForm({
      incremental_default_days: item.incremental_default_days,
      incremental_sync_strategy: item.incremental_sync_strategy ?? undefined,
      full_sync_strategy: item.full_sync_strategy ?? undefined,
      full_sync_concurrency: item.full_sync_concurrency,
      passive_sync_enabled: item.passive_sync_enabled,
      passive_sync_task_name: item.passive_sync_task_name,
      notes: item.notes,
      data_source: item.data_source ?? 'tushare',
      max_requests_per_minute: item.max_requests_per_minute ?? null,
    })
    setScheduleForm({
      enabled: item.incremental_schedule?.enabled ?? undefined,
      cron_expression: item.incremental_schedule?.cron_expression ?? undefined,
    })
    setEditDialogOpen(true)
  }

  const handleSave = async () => {
    if (!editingItem) return
    setIsSaving(true)
    try {
      const configResp = await syncDashboardApi.updateConfig(editingItem.table_key, editForm)
      if (configResp.code !== 200) {
        toast.error(configResp.message || '保存失败')
        return
      }

      // 若该表有增量调度任务，同步更新调度配置
      if (editingItem.incremental_schedule && (scheduleForm.enabled !== undefined || scheduleForm.cron_expression !== undefined)) {
        const schedResp = await syncDashboardApi.updateSchedule(editingItem.table_key, scheduleForm)
        if (schedResp.code !== 200) {
          toast.error(schedResp.message || '调度配置保存失败')
          return
        }
        const now = new Date().toISOString()
        setItems(prev => prev.map(i =>
          i.table_key === editingItem.table_key
            ? {
                ...i, ...editForm, updated_at: now,
                incremental_schedule: i.incremental_schedule
                  ? { ...i.incremental_schedule, ...scheduleForm }
                  : i.incremental_schedule,
              } as SyncOverviewItem
            : i
        ))
      } else {
        const now = new Date().toISOString()
        setItems(prev => prev.map(i =>
          i.table_key === editingItem.table_key ? { ...i, ...editForm, updated_at: now } as SyncOverviewItem : i
        ))
      }

      toast.success('配置已保存')
      setEditDialogOpen(false)
    } catch {
      toast.error('保存失败，请重试')
    } finally {
      setIsSaving(false)
    }
  }

  // 分组
  const filteredItems = items.filter(i => {
    const q = searchText.trim().toLowerCase()
    return !q || i.display_name.toLowerCase().includes(q) || i.table_key.toLowerCase().includes(q)
  })

  const groupedItems = CATEGORY_ORDER.reduce<Record<string, SyncOverviewItem[]>>((acc, cat) => {
    const filtered = filteredItems.filter(i => i.category === cat)
    if (filtered.length > 0) acc[cat] = filtered
    return acc
  }, {})
  filteredItems.forEach(i => {
    if (!groupedItems[i.category]) groupedItems[i.category] = []
    if (!groupedItems[i.category].find(x => x.table_key === i.table_key)) {
      groupedItems[i.category].push(i)
    }
  })

  const totalTables = items.length
  const failedTables = items.filter(
    i => i.last_incremental?.status === 'failure' || i.last_full_sync?.status === 'failure'
  ).length
  const pendingProgress = items.filter(i => i.redis_progress).length
  const neverSynced = items.filter(i => !i.last_incremental && !i.last_full_sync).length

  const categoryOptions = ['全部', ...CATEGORY_ORDER.filter(c => categories.some(cat => cat.name === c))]

  return (
    <div className="space-y-4">
      <PageHeader
        title="同步配置"
        description="管理所有数据表的增量/全量同步任务状态与配置参数"
        actions={
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={() => setGlobalConfigOpen(true)}>
              <KeyRound className="h-4 w-4 mr-1" />
              配置
            </Button>
            <Button size="sm" onClick={loadData} disabled={isLoading}>
              {isLoading
                ? <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                : <RefreshCw className="h-4 w-4 mr-1" />}
              刷新
            </Button>
          </div>
        }
      />

      {/* 统计卡片 */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: '数据表总数', value: totalTables, color: 'text-blue-600' },
          { label: '从未同步', value: neverSynced, color: 'text-gray-500' },
          { label: '有失败记录', value: failedTables, color: 'text-red-500' },
          { label: '有续继进度', value: pendingProgress, color: 'text-orange-500' },
        ].map(stat => (
          <Card key={stat.label} className="p-3">
            <p className="text-xs text-gray-500">{stat.label}</p>
            <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
          </Card>
        ))}
      </div>

      {/* 筛选栏 */}
      <div className="flex flex-wrap items-center gap-3">
        <Input
          placeholder="搜索表名或 table_key..."
          value={searchText}
          onChange={e => setSearchText(e.target.value)}
          className="w-56 h-8 text-sm"
        />
        <Select value={selectedCategory} onValueChange={setSelectedCategory}>
          <SelectTrigger className="w-40 h-8 text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {categoryOptions.map(c => (
              <SelectItem key={c} value={c}>{c}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        {selectedCategory !== '全部' && (
          <Button variant="ghost" size="sm" onClick={() => setSelectedCategory('全部')}>
            清除筛选
          </Button>
        )}
      </div>

      {/* 分类表格 */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      ) : (
        <div className="space-y-3">
          {Object.entries(groupedItems).map(([category, catItems]) => (
            <CategorySection
              key={category}
              category={category}
              items={catItems}
              onSync={handleSync}
              onClearProgress={setClearProgressItem}
              onEdit={openEditDialog}
              onTest={(item) => { setTestingItem(item); setTestDialogOpen(true) }}
            />
          ))}
        </div>
      )}

      {/* 清除进度确认 */}
      <Dialog open={!!clearProgressItem} onOpenChange={() => setClearProgressItem(null)}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>清除全量同步进度</DialogTitle>
            <DialogDescription>
              确定要清除 <strong>{clearProgressItem?.display_name}</strong> 的 Redis 续继进度吗？
              清除后下次全量同步将从头开始。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setClearProgressItem(null)}>取消</Button>
            <Button variant="destructive" onClick={handleClearProgress}>确认清除</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 全局配置弹窗 */}
      <Dialog open={globalConfigOpen} onOpenChange={setGlobalConfigOpen}>
        <DialogContent className="sm:max-w-[440px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <KeyRound className="h-4 w-4" />
              数据源配置
            </DialogTitle>
            <DialogDescription>配置 Tushare API Token 及全量同步起始日期</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Label htmlFor="global-token">Tushare API Token</Label>
                {configData?.tushare_token && configData.tushare_token.includes('*') ? (
                  <span className="px-1.5 py-0.5 text-xs bg-green-100 text-green-800 rounded">已配置</span>
                ) : (
                  <span className="px-1.5 py-0.5 text-xs bg-yellow-100 text-yellow-800 rounded">未配置</span>
                )}
              </div>
              <Input
                id="global-token"
                type="password"
                value={tokenInput}
                onChange={e => setTokenInput(e.target.value)}
                placeholder={
                  configData?.tushare_token && configData.tushare_token.includes('*')
                    ? `留空不修改（${configData.tushare_token}）`
                    : '请输入您的 Tushare Token'
                }
                className="font-mono"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="global-earliest-date">全量同步最早日期</Label>
              <Input
                id="global-earliest-date"
                type="date"
                value={earliestDate}
                onChange={e => setEarliestDate(e.target.value)}
                className="max-w-xs"
              />
              <p className="text-xs text-gray-500">各页面点击「全量同步」时以此日期为起始日</p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="global-max-rpm">每分钟最大请求数</Label>
              <Input
                id="global-max-rpm"
                type="number"
                min={0}
                max={500}
                value={maxRpmInput}
                onChange={e => setMaxRpmInput(e.target.value)}
                className="max-w-xs"
              />
              <p className="text-xs text-gray-500">主动限速以防触达 Tushare 频率限制，0 表示不限速</p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setGlobalConfigOpen(false)}>取消</Button>
            <Button onClick={handleSaveGlobal} disabled={isSavingGlobal}>
              {isSavingGlobal ? '保存中...' : '保存配置'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 编辑配置弹窗 */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="sm:max-w-[560px] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Settings className="h-4 w-4" />
              编辑同步配置
            </DialogTitle>
            <DialogDescription className="flex items-center justify-between">
              <span>{editingItem?.display_name}（{editingItem?.table_key}）</span>
              {editingItem?.updated_at && (
                <span className="text-xs text-gray-400">
                  更新于 {new Date(editingItem.updated_at).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' })}
                </span>
              )}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            {/* 同步参数 */}
            <div className="text-xs font-medium text-gray-500 uppercase tracking-wide border-b pb-1">同步参数</div>
            <div className="grid grid-cols-3 items-center gap-4">
              <Label className="text-right text-sm">数据源</Label>
              <Select
                value={editForm.data_source ?? 'tushare'}
                onValueChange={v => setEditForm(prev => ({ ...prev, data_source: v }))}
              >
                <SelectTrigger className="col-span-2">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="tushare">Tushare</SelectItem>
                  <SelectItem value="akshare">AkShare</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-3 items-center gap-4">
              <Label className="text-right text-sm">回看天数</Label>
              <Input
                type="number" min={1} className="col-span-2"
                value={editForm.incremental_default_days ?? ''}
                onChange={e => setEditForm(prev => ({
                  ...prev,
                  incremental_default_days: e.target.value === '' ? undefined : Number(e.target.value)
                }))}
              />
            </div>
            <div className="grid grid-cols-3 items-center gap-4">
              <Label className="text-right text-sm">增量策略</Label>
              <Select
                value={editForm.incremental_sync_strategy ?? 'none'}
                onValueChange={v => setEditForm(prev => ({ ...prev, incremental_sync_strategy: v === 'none' ? null : v as SyncStrategy }))}
              >
                <SelectTrigger className="col-span-2"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {INCREMENTAL_STRATEGY_OPTIONS.map(opt => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-3 items-center gap-4">
              <Label className="text-right text-sm">全量策略</Label>
              <Select
                value={editForm.full_sync_strategy ?? 'none'}
                onValueChange={v => setEditForm(prev => ({ ...prev, full_sync_strategy: v as SyncStrategy }))}
              >
                <SelectTrigger className="col-span-2"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {STRATEGY_OPTIONS.map(opt => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-3 items-center gap-4">
              <Label className="text-right text-sm">并发数</Label>
              <Input
                type="number" min={1} max={20} className="col-span-2"
                value={editForm.full_sync_concurrency ?? ''}
                onChange={e => setEditForm(prev => ({
                  ...prev,
                  full_sync_concurrency: e.target.value === '' ? undefined : Number(e.target.value)
                }))}
              />
            </div>
            <div className="grid grid-cols-3 items-center gap-4">
              <Label className="text-right text-sm">任务限速（次/分钟）</Label>
              <div className="col-span-2 flex items-center gap-2">
                <Input
                  type="number" min={0} max={500} className="w-28 text-sm"
                  placeholder="留空继承全局设置"
                  value={editForm.max_requests_per_minute ?? ''}
                  onChange={e => setEditForm(prev => ({
                    ...prev,
                    max_requests_per_minute: e.target.value === '' ? null : Number(e.target.value)
                  }))}
                />
                <span className="text-xs text-gray-400">留空=继承全局，0=不限速</span>
              </div>
            </div>
            <div className="grid grid-cols-3 items-center gap-4">
              <Label className="text-right text-sm">被动同步</Label>
              <div className="col-span-2 flex items-center gap-2">
                <Switch
                  checked={editForm.passive_sync_enabled ?? false}
                  onCheckedChange={v => setEditForm(prev => ({ ...prev, passive_sync_enabled: v }))}
                />
                <span className="text-sm text-gray-500">
                  {editForm.passive_sync_enabled ? '已启用' : '已禁用'}
                </span>
              </div>
            </div>
            <div className="grid grid-cols-3 items-center gap-4">
              <Label className="text-right text-sm">被动同步任务</Label>
              <Input
                className="col-span-2 font-mono text-sm" placeholder="tasks.xxx（留空则不指定）"
                value={editForm.passive_sync_task_name ?? ''}
                onChange={e => setEditForm(prev => ({
                  ...prev,
                  passive_sync_task_name: e.target.value || null
                }))}
              />
            </div>
            <div className="grid grid-cols-3 items-start gap-4">
              <Label className="text-right text-sm pt-2">备注</Label>
              <textarea
                className="col-span-2 min-h-[60px] rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 resize-none"
                placeholder="可选备注"
                value={editForm.notes ?? ''}
                onChange={e => setEditForm(prev => ({ ...prev, notes: e.target.value || null }))}
              />
            </div>

            {/* 增量同步调度 */}
            {editingItem?.incremental_task_name && (
              <>
                <div className="text-xs font-medium text-gray-500 uppercase tracking-wide border-b pb-1 pt-2">增量同步调度</div>
                {editingItem.incremental_schedule ? (
                  <>
                    <div className="grid grid-cols-3 items-center gap-4">
                      <Label className="text-right text-sm">启用定时任务</Label>
                      <div className="col-span-2 flex items-center gap-2">
                        <Switch
                          checked={scheduleForm.enabled ?? editingItem.incremental_schedule.enabled}
                          onCheckedChange={v => setScheduleForm(prev => ({ ...prev, enabled: v }))}
                        />
                        <span className="text-sm text-gray-500">
                          {(scheduleForm.enabled ?? editingItem.incremental_schedule.enabled) ? '已启用' : '已禁用'}
                        </span>
                      </div>
                    </div>
                    <div className="grid grid-cols-3 items-center gap-4">
                      <Label className="text-right text-sm">Cron 表达式</Label>
                      <Input
                        className="col-span-2 font-mono text-sm"
                        placeholder="如 0 8 * * *（每天8点）"
                        value={scheduleForm.cron_expression ?? editingItem.incremental_schedule.cron_expression ?? ''}
                        onChange={e => setScheduleForm(prev => ({ ...prev, cron_expression: e.target.value || null }))}
                      />
                    </div>
                    <p className="text-xs text-gray-400 col-span-3 pl-[calc(33%+0.5rem)]">
                      任务名：{editingItem.incremental_task_name}
                    </p>
                  </>
                ) : (
                  <p className="text-xs text-gray-400 pl-[calc(33%+0.5rem)]">
                    该增量任务（{editingItem.incremental_task_name}）尚未在定时任务表中登记，请先到定时任务页面创建。
                  </p>
                )}
              </>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)}>取消</Button>
            <Button onClick={handleSave} disabled={isSaving}>
              {isSaving ? '保存中...' : '保存'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 测试数据源弹窗 */}
      <TestDatasourceDialog
        item={testingItem}
        open={testDialogOpen}
        onOpenChange={(open) => { setTestDialogOpen(open); if (!open) setTestingItem(null) }}
        onSaved={() => loadData(true)}
      />
    </div>
  )
}
