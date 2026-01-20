'use client'

interface Metrics {
  total_return?: number
  annualized_return?: number
  sharpe_ratio?: number
  sortino_ratio?: number
  calmar_ratio?: number
  max_drawdown?: number
  max_drawdown_duration?: number
  volatility?: number
  win_rate?: number
  alpha?: number | null
  beta?: number | null
  information_ratio?: number | null
}

interface PerformanceMetricsProps {
  metrics: Metrics
  mode?: 'single' | 'multi'
}

interface MetricItem {
  label: string
  value: string
  colorClass: string
  tooltip?: string
}

export default function PerformanceMetrics({ metrics, mode = 'multi' }: PerformanceMetricsProps) {
  // 格式化百分比
  const formatPercent = (value: number | undefined | null): string => {
    if (value === undefined || value === null) return '-'
    return `${(value * 100).toFixed(2)}%`
  }

  // 格式化数值
  const formatNumber = (value: number | undefined | null, decimals: number = 2): string => {
    if (value === undefined || value === null) return '-'
    return value.toFixed(decimals)
  }

  // 格式化天数
  const formatDays = (value: number | undefined | null): string => {
    if (value === undefined || value === null) return '-'
    return `${Math.round(value)}天`
  }

  // 获取颜色类名
  const getColorClass = (value: number | undefined | null): string => {
    if (value === undefined || value === null) return 'text-gray-700 dark:text-gray-300'
    if (value > 0) return 'text-green-600 dark:text-green-400 font-semibold'
    if (value < 0) return 'text-red-600 dark:text-red-400 font-semibold'
    return 'text-gray-700 dark:text-gray-300'
  }

  // 指标配置
  const metricsConfig: Array<{ category: string; items: MetricItem[] }> = [
    {
      category: '收益指标',
      items: [
        {
          label: '总收益率',
          value: formatPercent(metrics.total_return),
          colorClass: getColorClass(metrics.total_return)
        },
        {
          label: '年化收益率',
          value: formatPercent(metrics.annualized_return),
          colorClass: getColorClass(metrics.annualized_return)
        },
        {
          label: '波动率',
          value: formatPercent(metrics.volatility),
          colorClass: 'text-gray-700 dark:text-gray-300'
        }
      ]
    },
    {
      category: '风险指标',
      items: [
        {
          label: '最大回撤',
          value: formatPercent(metrics.max_drawdown),
          colorClass: getColorClass(metrics.max_drawdown)
        },
        {
          label: '最大回撤持续期',
          value: formatDays(metrics.max_drawdown_duration),
          colorClass: 'text-gray-700 dark:text-gray-300'
        },
        ...(mode === 'single' && metrics.win_rate !== undefined ? [{
          label: '胜率',
          value: formatPercent(metrics.win_rate),
          colorClass: getColorClass(metrics.win_rate)
        }] : [])
      ]
    },
    {
      category: '风险调整收益',
      items: [
        {
          label: '夏普比率',
          value: formatNumber(metrics.sharpe_ratio),
          colorClass: getColorClass(metrics.sharpe_ratio),
          tooltip: '衡量单位风险的超额收益,越高越好'
        },
        {
          label: '索提诺比率',
          value: formatNumber(metrics.sortino_ratio),
          colorClass: getColorClass(metrics.sortino_ratio),
          tooltip: '只考虑下行风险的夏普比率'
        },
        {
          label: '卡玛比率',
          value: formatNumber(metrics.calmar_ratio),
          colorClass: getColorClass(metrics.calmar_ratio),
          tooltip: '年化收益率/最大回撤'
        }
      ]
    }
  ]

  // 添加基准相关指标(仅多股模式)
  if (mode === 'multi' && (metrics.alpha !== undefined || metrics.beta !== undefined)) {
    metricsConfig.push({
      category: '相对基准指标',
      items: [
        {
          label: 'Alpha',
          value: formatNumber(metrics.alpha),
          colorClass: getColorClass(metrics.alpha),
          tooltip: '相对基准的超额收益'
        },
        {
          label: 'Beta',
          value: formatNumber(metrics.beta),
          colorClass: 'text-gray-700 dark:text-gray-300',
          tooltip: '相对基准的系统风险敞口'
        },
        {
          label: '信息比率',
          value: formatNumber(metrics.information_ratio),
          colorClass: getColorClass(metrics.information_ratio),
          tooltip: '超额收益的稳定性'
        }
      ]
    })
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-6">
        绩效报告
      </h2>

      <div className="space-y-6">
        {metricsConfig.map((category, idx) => (
          <div key={idx}>
            <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">
              {category.category}
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {category.items.map((item, itemIdx) => (
                <div
                  key={itemIdx}
                  className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 hover:shadow-md transition-shadow"
                  title={item.tooltip}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      {item.label}
                    </span>
                    {item.tooltip && (
                      <svg
                        className="w-4 h-4 text-gray-400"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                          clipRule="evenodd"
                        />
                      </svg>
                    )}
                  </div>
                  <div className={`text-2xl font-bold mt-2 ${item.colorClass}`}>
                    {item.value}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* 图例说明 */}
      <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
        <p className="text-xs text-gray-500 dark:text-gray-400">
          <span className="font-semibold">提示:</span>
          {' '}绿色表示正向指标,红色表示负向指标。夏普比率&gt;1表示风险调整后收益良好。
        </p>
      </div>
    </div>
  )
}
