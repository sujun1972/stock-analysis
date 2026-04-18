'use client'

import { Settings } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '@/components/ui/select'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle
} from '@/components/ui/dialog'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import type { SyncOverviewItem, SyncConfigUpdate, ScheduleUpdate, SyncStrategy } from '@/lib/api/sync-dashboard'

import { STRATEGY_OPTIONS, INCREMENTAL_STRATEGY_OPTIONS } from './constants'

export function EditConfigDialog({
  open,
  onOpenChange,
  editingItem,
  editForm,
  setEditForm,
  scheduleForm,
  setScheduleForm,
  isSaving,
  onSave,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  editingItem: SyncOverviewItem | null
  editForm: SyncConfigUpdate
  setEditForm: React.Dispatch<React.SetStateAction<SyncConfigUpdate>>
  scheduleForm: ScheduleUpdate
  setScheduleForm: React.Dispatch<React.SetStateAction<ScheduleUpdate>>
  isSaving: boolean
  onSave: () => void
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
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
          <Button variant="outline" onClick={() => onOpenChange(false)}>取消</Button>
          <Button onClick={onSave} disabled={isSaving}>
            {isSaving ? '保存中...' : '保存'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
