'use client'

import { PageHeader } from '@/components/common/PageHeader'
import { StatisticsCards } from '@/components/common/StatisticsCards'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { Button } from '@/components/ui/button'
import { RefreshCw } from 'lucide-react'
import { useIndDcData, useIndDcActions } from './hooks'
import { IndDcFilters, IndDcTable, IndDcChart, IndDcSyncDialog } from './components'

export default function MoneyflowIndDcPage() {
  const {
    tradeDate,
    setTradeDate,
    contentType,
    setContentType,
    dp,
    statsCards,
    chartData,
    loadTopSectors,
  } = useIndDcData()

  const {
    syncDate,
    setSyncDate,
    syncContentType,
    setSyncContentType,
    handleSyncConfirm,
  } = useIndDcActions(dp, loadTopSectors)

  return (
    <div className="space-y-6">
      <PageHeader
        title="板块资金流向（DC）"
        description="获取东方财富板块资金流向，每天盘后更新"
        details={<>
          <div>接口：moneyflow_ind_dc</div>
          <a href="https://tushare.pro/document/2?doc_id=344" target="_blank" rel="noopener noreferrer">查看文档</a>
        </>}
        actions={
          <div className="flex gap-2">
            <Button onClick={() => dp.setSyncDialogOpen(true)} disabled={dp.syncing}>
              {dp.syncing ? (
                <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
              ) : (
                <><RefreshCw className="h-4 w-4 mr-1" />同步数据</>
              )}
            </Button>
            <BulkOpsButtons
              onFullSync={dp.handleFullSync}
              onClearConfirm={dp.handleClear}
              isClearDialogOpen={dp.isClearDialogOpen}
              setIsClearDialogOpen={dp.setIsClearDialogOpen}
              fullSyncing={dp.fullSyncing}
              isClearing={dp.isClearing}
              earliestHistoryDate={dp.earliestHistoryDate}
              tableName="板块资金流向(DC)"
            />
          </div>
        }
      />

      <StatisticsCards items={statsCards} />

      <IndDcChart chartData={chartData} />

      <IndDcFilters
        tradeDate={tradeDate}
        onTradeDateChange={setTradeDate}
        contentType={contentType}
        onContentTypeChange={setContentType}
        onQuery={dp.handleQuery}
        isLoading={dp.isLoading}
      />

      <IndDcTable
        data={dp.data}
        isLoading={dp.isLoading}
        sortKey={dp.sortKey}
        sortDirection={dp.sortDirection}
        onSort={dp.handleSort}
        page={dp.page}
        pageSize={dp.pageSize}
        total={dp.total}
        onPageChange={dp.handlePageChange}
      />

      <IndDcSyncDialog
        open={dp.syncDialogOpen}
        onOpenChange={dp.setSyncDialogOpen}
        syncDate={syncDate}
        onSyncDateChange={setSyncDate}
        syncContentType={syncContentType}
        onSyncContentTypeChange={setSyncContentType}
        onConfirm={handleSyncConfirm}
        syncing={dp.syncing}
      />
    </div>
  )
}
