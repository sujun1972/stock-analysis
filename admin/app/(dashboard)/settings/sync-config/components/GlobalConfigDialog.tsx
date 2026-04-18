'use client'

import { KeyRound } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'

export function GlobalConfigDialog({
  open,
  onOpenChange,
  configData,
  tokenInput,
  setTokenInput,
  earliestDate,
  setEarliestDate,
  maxRpmInput,
  setMaxRpmInput,
  isSaving,
  onSave,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  configData: { tushare_token?: string; earliest_history_date?: string; max_requests_per_minute?: number } | null
  tokenInput: string
  setTokenInput: (v: string) => void
  earliestDate: string
  setEarliestDate: (v: string) => void
  maxRpmInput: string
  setMaxRpmInput: (v: string) => void
  isSaving: boolean
  onSave: () => void
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
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
          <Button variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
          <Button onClick={onSave} disabled={isSaving}>
            {isSaving ? '保存中...' : '保存配置'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
