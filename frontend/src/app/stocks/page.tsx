'use client'

import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api-client'
import { useStockStore } from '@/store/stock-store'
import type { StockInfo } from '@/types'

export default function StocksPage() {
  const { stocks, setStocks, setLoading, isLoading, error, setError } = useStockStore()
  const [searchTerm, setSearchTerm] = useState('')
  const [marketFilter, setMarketFilter] = useState<string>('all')
  const [currentPage, setCurrentPage] = useState(1)
  const [totalStocks, setTotalStocks] = useState(0)
  const [isUpdating, setIsUpdating] = useState(false)
  const [updateMessage, setUpdateMessage] = useState<string | null>(null)
  const [pageSize, setPageSize] = useState(20)
  const [sortBy, setSortBy] = useState('pct_change')
  const [sortOrder, setSortOrder] = useState('desc')

  useEffect(() => {
    loadStocks()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPage, marketFilter, searchTerm, pageSize, sortBy, sortOrder])

  const loadStocks = async () => {
    try {
      setLoading(true)
      setError(null)

      const params: any = {
        skip: (currentPage - 1) * pageSize,
        limit: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
      }

      if (marketFilter !== 'all') {
        params.market = marketFilter
      }

      if (searchTerm && searchTerm.trim()) {
        params.search = searchTerm.trim()
      }

      const response = await apiClient.getStockList(params)
      setStocks(response.data)
      setTotalStocks(response.total)
    } catch (err: any) {
      setError(err.message || '加载股票列表失败')
      console.error('Failed to load stocks:', err)
    } finally {
      setLoading(false)
    }
  }

  /**
   * 更新股票列表（从数据源拉取最新数据）
   */
  const handleUpdateStockList = async () => {
    try {
      setIsUpdating(true)
      setUpdateMessage(null)
      setError(null)

      const response = await apiClient.updateStockList()

      setUpdateMessage('成功更新股票列表！共获取 ' + (response.data?.total || 0) + ' 只股票')

      // 重新加载股票列表
      await loadStocks()

      // 5秒后清除成功消息
      setTimeout(() => setUpdateMessage(null), 5000)
    } catch (err: any) {
      setError(err.message || '更新股票列表失败')
      console.error('Failed to update stock list:', err)
    } finally {
      setIsUpdating(false)
    }
  }

  const totalPages = Math.ceil(totalStocks / pageSize)

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          股票列表
        </h1>
      </div>

      {/* 成功消息提示 */}
      {updateMessage && (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
          <div className="flex items-center">
            <svg className="w-5 h-5 text-green-600 dark:text-green-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <span className="text-green-800 dark:text-green-200">{updateMessage}</span>
          </div>
        </div>
      )}

      {/* 错误提示 */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex items-center">
            <svg className="w-5 h-5 text-red-600 dark:text-red-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <span className="text-red-800 dark:text-red-200">{error}</span>
          </div>
        </div>
      )}

      {/* 搜索和筛选 */}
      <div className="card">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              市场筛选
            </label>
            <select
              className="input-field"
              value={marketFilter}
              onChange={(e) => {
                setMarketFilter(e.target.value)
                setCurrentPage(1)
              }}
            >
              <option value="all">全部市场</option>
              <option value="上海主板">上海主板</option>
              <option value="深圳主板">深圳主板</option>
              <option value="创业板">创业板</option>
              <option value="科创板">科创板</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              搜索股票
            </label>
            <input
              type="text"
              placeholder="输入股票代码或名称..."
              className="input-field"
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value)
                setCurrentPage(1) // 搜索时重置到第一页
              }}
            />
          </div>
        </div>
      </div>

      {/* 股票表格 */}
      <div className="card">
        {isLoading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-300 border-t-blue-600"></div>
            <p className="mt-4 text-gray-600 dark:text-gray-400">加载中...</p>
          </div>
        ) : stocks.length === 0 ? (
          <div className="text-center py-12">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="mt-4 text-gray-600 dark:text-gray-400">没有找到股票</p>
            {totalStocks === 0 && (
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-500">
                请点击右上角的&ldquo;更新股票列表&rdquo;按钮获取股票数据
              </p>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    股票
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    最新价
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    <button
                      onClick={() => {
                        if (sortBy === 'pct_change') {
                          setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')
                        } else {
                          setSortBy('pct_change')
                          setSortOrder('desc')
                        }
                      }}
                      className="inline-flex items-center gap-1 hover:text-gray-700 dark:hover:text-gray-200"
                    >
                      涨跌幅
                      {sortBy === 'pct_change' && (
                        <svg
                          className="w-3 h-3 text-blue-600 dark:text-blue-400"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          {sortOrder === 'desc' ? (
                            <path fillRule="evenodd" d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L10 13.586l3.293-3.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          ) : (
                            <path fillRule="evenodd" d="M14.707 12.707a1 1 0 01-1.414 0L10 9.414l-3.293 3.293a1 1 0 01-1.414-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 010 1.414z" clipRule="evenodd" />
                          )}
                        </svg>
                      )}
                    </button>
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                {stocks.map((stock) => (
                  <tr key={stock.code} className="table-row">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <a
                        href={`/analysis?code=${stock.code}`}
                        className="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300 hover:underline"
                      >
                        {stock.name}({stock.code})
                      </a>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium">
                      {stock.latest_price ? (
                        <span className={
                          stock.pct_change !== null && stock.pct_change !== undefined
                            ? stock.pct_change > 0
                              ? 'text-red-600 dark:text-red-400'
                              : stock.pct_change < 0
                                ? 'text-green-600 dark:text-green-400'
                                : 'text-gray-900 dark:text-white'
                            : 'text-gray-900 dark:text-white'
                        }>
                          {stock.latest_price.toFixed(2)}
                        </span>
                      ) : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium">
                      {stock.pct_change !== null && stock.pct_change !== undefined ? (
                        <span className={stock.pct_change > 0 ? 'text-red-600 dark:text-red-400' : stock.pct_change < 0 ? 'text-green-600 dark:text-green-400' : 'text-gray-600 dark:text-gray-400'}>
                          {stock.pct_change > 0 ? '+' : ''}{stock.pct_change.toFixed(2)}%
                        </span>
                      ) : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* 分页 */}
        {totalPages > 1 && (
          <div className="mt-6 flex items-center justify-between border-t border-gray-200 dark:border-gray-700 pt-4">
            <div className="flex-1 flex justify-between sm:hidden">
              <button
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="btn-secondary disabled:opacity-50"
              >
                上一页
              </button>
              <button
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="btn-secondary disabled:opacity-50"
              >
                下一页
              </button>
            </div>
            <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
              <div className="flex items-center gap-4">
                <p className="text-sm text-gray-700 dark:text-gray-300">
                  显示第 <span className="font-medium">{(currentPage - 1) * pageSize + 1}</span> 到{' '}
                  <span className="font-medium">{Math.min(currentPage * pageSize, totalStocks)}</span> 条，
                  共 <span className="font-medium">{totalStocks}</span> 条
                </p>
                <div className="flex items-center gap-2 whitespace-nowrap">
                  <label className="text-sm text-gray-700 dark:text-gray-300">每页:</label>
                  <select
                    className="input-field py-1 px-2 text-sm"
                    value={pageSize}
                    onChange={(e) => {
                      setPageSize(Number(e.target.value))
                      setCurrentPage(1) // 重置到第一页
                    }}
                  >
                    <option value="10">10条</option>
                    <option value="20">20条</option>
                    <option value="30">30条</option>
                  </select>
                </div>
              </div>
              <div>
                <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                  <button
                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                    className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm font-medium text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
                  >
                    上一页
                  </button>

                  {/* 第一页 */}
                  {currentPage > 3 && (
                    <>
                      <button
                        onClick={() => setCurrentPage(1)}
                        className="relative inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 text-sm font-medium"
                      >
                        1
                      </button>
                      {currentPage > 4 && (
                        <span className="relative inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm font-medium">
                          ...
                        </span>
                      )}
                    </>
                  )}

                  {/* 当前页周围的页码 */}
                  {Array.from({ length: totalPages }, (_, i) => i + 1)
                    .filter(page => {
                      // 显示当前页及其前后各2页
                      return page >= currentPage - 2 && page <= currentPage + 2
                    })
                    .map(page => (
                      <button
                        key={page}
                        onClick={() => setCurrentPage(page)}
                        className={`relative inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium ${
                          currentPage === page
                            ? 'z-10 bg-blue-600 border-blue-600 text-white'
                            : 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                        }`}
                      >
                        {page}
                      </button>
                    ))}

                  {/* 最后一页 */}
                  {currentPage < totalPages - 2 && (
                    <>
                      {currentPage < totalPages - 3 && (
                        <span className="relative inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm font-medium">
                          ...
                        </span>
                      )}
                      <button
                        onClick={() => setCurrentPage(totalPages)}
                        className="relative inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 text-sm font-medium"
                      >
                        {totalPages}
                      </button>
                    </>
                  )}

                  <button
                    onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                    className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm font-medium text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
                  >
                    下一页
                  </button>
                </nav>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
