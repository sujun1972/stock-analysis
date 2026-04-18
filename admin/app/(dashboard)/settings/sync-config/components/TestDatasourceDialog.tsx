'use client'

import { useState, useEffect } from 'react'
import { toast } from 'sonner'
import { Database, Loader2, Play } from 'lucide-react'

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
import { syncDashboardApi, type SyncOverviewItem, type SyncConfigUpdate, type ApiParams } from '@/lib/api/sync-dashboard'

export function TestDatasourceDialog({
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
