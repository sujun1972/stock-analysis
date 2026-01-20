'use client'

import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api-client'

export default function Home() {
  const [healthStatus, setHealthStatus] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    checkHealth()
  }, [])

  const checkHealth = async () => {
    try {
      setIsLoading(true)
      const response = await apiClient.healthCheck()
      setHealthStatus(response)
    } catch (error) {
      console.error('Health check failed:', error)
      setHealthStatus({ status: 'error', message: '无法连接到后端服务' })
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="space-y-8">
      {/* 欢迎卡片 */}
      <div className="card">
        <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
          欢迎使用 A股AI量化交易系统
        </h2>
        <p className="text-gray-600 dark:text-gray-300 mb-6">
          这是一个功能完整的A股量化交易分析系统，集成数据获取、技术分析、机器学习预测、回测引擎和Web API服务。
        </p>

        {/* 系统状态 */}
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">
            系统状态
          </h3>
          {isLoading ? (
            <p className="text-blue-700 dark:text-blue-300">检查中...</p>
          ) : healthStatus?.status === 'healthy' ? (
            <div className="flex items-center text-green-600 dark:text-green-400">
              <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              后端服务运行正常
            </div>
          ) : (
            <div className="flex items-center text-red-600 dark:text-red-400">
              <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              后端服务连接失败
            </div>
          )}
        </div>
      </div>

      {/* 功能介绍 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="card">
          <div className="flex items-center mb-4">
            <div className="bg-blue-100 dark:bg-blue-900 rounded-lg p-3">
              <svg className="w-6 h-6 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <h3 className="ml-3 text-lg font-semibold text-gray-900 dark:text-white">
              数据获取
            </h3>
          </div>
          <p className="text-gray-600 dark:text-gray-300 text-sm">
            支持AkShare、Tushare等多数据源，获取A股历史行情数据
          </p>
        </div>

        <div className="card">
          <div className="flex items-center mb-4">
            <div className="bg-green-100 dark:bg-green-900 rounded-lg p-3">
              <svg className="w-6 h-6 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
              </svg>
            </div>
            <h3 className="ml-3 text-lg font-semibold text-gray-900 dark:text-white">
              技术分析
            </h3>
          </div>
          <p className="text-gray-600 dark:text-gray-300 text-sm">
            计算60+种技术指标，包括趋势、动量、波动率等
          </p>
        </div>

        <div className="card">
          <div className="flex items-center mb-4">
            <div className="bg-purple-100 dark:bg-purple-900 rounded-lg p-3">
              <svg className="w-6 h-6 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <h3 className="ml-3 text-lg font-semibold text-gray-900 dark:text-white">
              AI预测
            </h3>
          </div>
          <p className="text-gray-600 dark:text-gray-300 text-sm">
            基于LightGBM和GRU的机器学习模型进行价格预测
          </p>
        </div>

        <div className="card">
          <div className="flex items-center mb-4">
            <div className="bg-yellow-100 dark:bg-yellow-900 rounded-lg p-3">
              <svg className="w-6 h-6 text-yellow-600 dark:text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
            </div>
            <h3 className="ml-3 text-lg font-semibold text-gray-900 dark:text-white">
              策略回测
            </h3>
          </div>
          <p className="text-gray-600 dark:text-gray-300 text-sm">
            完整的回测引擎，支持多策略组合和性能评估
          </p>
        </div>

        <div className="card">
          <div className="flex items-center mb-4">
            <div className="bg-red-100 dark:bg-red-900 rounded-lg p-3">
              <svg className="w-6 h-6 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
              </svg>
            </div>
            <h3 className="ml-3 text-lg font-semibold text-gray-900 dark:text-white">
              数据库
            </h3>
          </div>
          <p className="text-gray-600 dark:text-gray-300 text-sm">
            TimescaleDB时序数据库，高性能存储历史行情
          </p>
        </div>

        <div className="card">
          <div className="flex items-center mb-4">
            <div className="bg-indigo-100 dark:bg-indigo-900 rounded-lg p-3">
              <svg className="w-6 h-6 text-indigo-600 dark:text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
            </div>
            <h3 className="ml-3 text-lg font-semibold text-gray-900 dark:text-white">
              API服务
            </h3>
          </div>
          <p className="text-gray-600 dark:text-gray-300 text-sm">
            FastAPI提供RESTful API，支持完整的量化分析流程
          </p>
        </div>
      </div>

      {/* 快速开始 */}
      <div className="card">
        <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          快速开始
        </h3>
        <div className="space-y-3">
          <div className="flex items-start">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-semibold mr-3">
              1
            </span>
            <div>
              <p className="text-gray-900 dark:text-white font-medium">访问股票列表</p>
              <p className="text-gray-600 dark:text-gray-300 text-sm">
                查看所有可用的A股股票，支持筛选和搜索
              </p>
            </div>
          </div>
          <div className="flex items-start">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-semibold mr-3">
              2
            </span>
            <div>
              <p className="text-gray-900 dark:text-white font-medium">数据分析</p>
              <p className="text-gray-600 dark:text-gray-300 text-sm">
                下载历史数据，计算技术指标和Alpha因子
              </p>
            </div>
          </div>
          <div className="flex items-start">
            <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-semibold mr-3">
              3
            </span>
            <div>
              <p className="text-gray-900 dark:text-white font-medium">策略回测</p>
              <p className="text-gray-600 dark:text-gray-300 text-sm">
                使用回测引擎验证交易策略，查看绩效指标
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* 免责声明 */}
      <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
        <div className="flex">
          <svg className="w-5 h-5 text-yellow-600 dark:text-yellow-400 mr-3 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          <div>
            <h4 className="font-semibold text-yellow-900 dark:text-yellow-100 mb-1">
              免责声明
            </h4>
            <p className="text-yellow-800 dark:text-yellow-200 text-sm">
              本系统仅供<strong>学习和研究</strong>使用。所有技术指标、信号、预测结果<strong>不构成任何投资建议</strong>。
              使用本系统进行实际交易的风险由用户自行承担。
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
