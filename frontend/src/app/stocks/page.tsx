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
  const pageSize = 20

  useEffect(() => {
    loadStocks()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPage, marketFilter])

  const loadStocks = async () => {
    try {
      setLoading(true)
      setError(null)

      const params: any = {
        skip: (currentPage - 1) * pageSize,
        limit: pageSize,
      }

      if (marketFilter !== 'all') {
        params.market = marketFilter
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

  const filteredStocks = stocks.filter(stock => {
    if (!searchTerm) return true
    const term = searchTerm.toLowerCase()
    return (
      stock.code.toLowerCase().includes(term) ||
      stock.name.toLowerCase().includes(term)
    )
  })

  const totalPages = Math.ceil(totalStocks / pageSize)

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          股票列表
        </h1>
        <p className="text-gray-600 dark:text-gray-300 mt-2">
          查看所有A股股票，支持搜索和筛选
        </p>
      </div>

      {/* 搜索和筛选 */}
      <div className="card">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              搜索股票
            </label>
            <input
              type="text"
              placeholder="输入股票代码或名称..."
              className="input-field"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

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

          <div className="flex items-end">
            <button
              onClick={loadStocks}
              disabled={isLoading}
              className="btn-primary w-full"
            >
              {isLoading ? '加载中...' : '刷新列表'}
            </button>
          </div>
        </div>
      </div>

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

      {/* 股票表格 */}
      <div className="card">
        <div className="mb-4 flex justify-between items-center">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            股票列表 ({totalStocks} 只)
          </h2>
          <span className="text-sm text-gray-600 dark:text-gray-400">
            显示 {filteredStocks.length} 条结果
          </span>
        </div>

        {isLoading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-300 border-t-blue-600"></div>
            <p className="mt-4 text-gray-600 dark:text-gray-400">加载中...</p>
          </div>
        ) : filteredStocks.length === 0 ? (
          <div className="text-center py-12">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="mt-4 text-gray-600 dark:text-gray-400">没有找到股票</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    股票代码
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    股票名称
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    市场
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    行业
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    地区
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    状态
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                {filteredStocks.map((stock) => (
                  <tr key={stock.code} className="table-row">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                      {stock.code}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {stock.name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                      {stock.market || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                      {stock.industry || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                      {stock.area || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        stock.status === 'L'
                          ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                          : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
                      }`}>
                        {stock.status === 'L' ? '上市' : stock.status || '-'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <a
                        href={`/analysis?code=${stock.code}`}
                        className="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300"
                      >
                        分析
                      </a>
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
              <div>
                <p className="text-sm text-gray-700 dark:text-gray-300">
                  显示第 <span className="font-medium">{(currentPage - 1) * pageSize + 1}</span> 到{' '}
                  <span className="font-medium">{Math.min(currentPage * pageSize, totalStocks)}</span> 条，
                  共 <span className="font-medium">{totalStocks}</span> 条
                </p>
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
                  {[...Array(Math.min(5, totalPages))].map((_, i) => {
                    const page = i + 1
                    return (
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
                    )
                  })}
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
