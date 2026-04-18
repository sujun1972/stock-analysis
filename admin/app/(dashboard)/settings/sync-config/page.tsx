'use client'

import { RefreshCw, Loader2, KeyRound } from 'lucide-react'

import { PageHeader } from '@/components/common/PageHeader'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '@/components/ui/select'

import { useSyncConfigData, useSyncConfigActions, useGlobalConfig } from './hooks'
import {
  CategorySection,
  TestDatasourceDialog,
  EditConfigDialog,
  GlobalConfigDialog,
  ClearProgressDialog,
  SummaryCards,
} from './components'

export default function SyncConfigPage() {
  const {
    items,
    setItems,
    isLoading,
    selectedCategory,
    setSelectedCategory,
    searchText,
    setSearchText,
    loadData,
    groupedItems,
    categoryOptions,
  } = useSyncConfigData()

  const {
    clearProgressItem,
    setClearProgressItem,
    handleClearProgress,
    testDialogOpen,
    testingItem,
    openTestDialog,
    closeTestDialog,
    editDialogOpen,
    setEditDialogOpen,
    editingItem,
    editForm,
    setEditForm,
    scheduleForm,
    setScheduleForm,
    isSaving,
    openEditDialog,
    handleSave,
    handleSync,
  } = useSyncConfigActions({ loadData, setItems })

  const {
    configData,
    globalConfigOpen,
    setGlobalConfigOpen,
    tokenInput,
    setTokenInput,
    earliestDate,
    setEarliestDate,
    maxRpmInput,
    setMaxRpmInput,
    isSavingGlobal,
    handleSaveGlobal,
  } = useGlobalConfig()

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
            <Button size="sm" onClick={() => loadData()} disabled={isLoading}>
              {isLoading
                ? <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                : <RefreshCw className="h-4 w-4 mr-1" />}
              刷新
            </Button>
          </div>
        }
      />

      {/* 统计卡片 */}
      <SummaryCards items={items} />

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
              onTest={openTestDialog}
            />
          ))}
        </div>
      )}

      {/* 清除进度确认 */}
      <ClearProgressDialog
        item={clearProgressItem}
        onClose={() => setClearProgressItem(null)}
        onConfirm={handleClearProgress}
      />

      {/* 全局配置弹窗 */}
      <GlobalConfigDialog
        open={globalConfigOpen}
        onOpenChange={setGlobalConfigOpen}
        configData={configData}
        tokenInput={tokenInput}
        setTokenInput={setTokenInput}
        earliestDate={earliestDate}
        setEarliestDate={setEarliestDate}
        maxRpmInput={maxRpmInput}
        setMaxRpmInput={setMaxRpmInput}
        isSaving={isSavingGlobal}
        onSave={handleSaveGlobal}
      />

      {/* 编辑配置弹窗 */}
      <EditConfigDialog
        open={editDialogOpen}
        onOpenChange={setEditDialogOpen}
        editingItem={editingItem}
        editForm={editForm}
        setEditForm={setEditForm}
        scheduleForm={scheduleForm}
        setScheduleForm={setScheduleForm}
        isSaving={isSaving}
        onSave={handleSave}
      />

      {/* 测试数据源弹窗 */}
      <TestDatasourceDialog
        item={testingItem}
        open={testDialogOpen}
        onOpenChange={closeTestDialog}
        onSaved={() => loadData(true)}
      />
    </div>
  )
}
