'use client'

import { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api-client'
import StrategyParamsPanel from './StrategyParamsPanel'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { DatePicker } from '@/components/ui/date-picker'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { useToast } from '@/hooks/use-toast'
import { format, subYears } from 'date-fns'
import { Settings } from 'lucide-react'

interface BacktestPanelProps {
  onBacktestComplete?: (result: any) => void
}

interface Strategy {
  id: string
  name: string
  description: string
  version: string
  parameter_count: number
}

export default function BacktestPanel({ onBacktestComplete }: BacktestPanelProps) {
  // 表单状态
  const [symbols, setSymbols] = useState<string>('600000')
  const [startDate, setStartDate] = useState<Date>(() => subYears(new Date(), 5)) // 默认开始日期为5年前
  const [endDate, setEndDate] = useState<Date>(new Date()) // 默认结束日期为今天
  const [initialCash, setInitialCash] = useState<number>(1000000)

  // 策略相关状态
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [selectedStrategyId, setSelectedStrategyId] = useState<string>('complex_indicator')
  const [strategyParams, setStrategyParams] = useState<Record<string, any>>({})
  const [dialogOpenStrategyId, setDialogOpenStrategyId] = useState<string | null>(null) // 控制哪个策略的对话框打开

  // 加载状态
  const [isLoading, setIsLoading] = useState(false)
  const [progress, setProgress] = useState<string>('')
  const [error, setError] = useState<string>('')

  // Toast hook
  const { toast } = useToast()

  // 加载策略列表
  useEffect(() => {
    const fetchStrategies = async () => {
      try {
        const response = await apiClient.getStrategyList()
        if (response.data) {
          setStrategies(response.data)
        }
      } catch (error) {
        console.error('获取策略列表失败:', error)
      }
    }

    fetchStrategies()
  }, [])

  // 自动添加交易所后缀
  const normalizeSymbol = (code: string): string => {
    const cleanCode = code.trim()

    // 如果已经有后缀,直接返回
    if (cleanCode.includes('.')) {
      return cleanCode
    }

    // 根据股票代码规则自动添加后缀
    if (cleanCode.startsWith('6') || cleanCode.startsWith('688')) {
      return `${cleanCode}.SH`
    } else if (cleanCode.startsWith('0') || cleanCode.startsWith('3')) {
      return `${cleanCode}.SZ`
    } else if (cleanCode.startsWith('8') || cleanCode.startsWith('4')) {
      return `${cleanCode}.BJ`
    }

    return cleanCode
  }

  // 处理回测提交
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setProgress('正在初始化回测引擎...')
    setError('')

    try {
      // 解析股票代码(支持逗号分隔)并自动添加交易所后缀
      const symbolList = symbols
        .split(',')
        .map(s => s.trim())
        .filter(s => s.length > 0)
        .map(s => normalizeSymbol(s))

      setProgress('正在获取历史数据...')

      // 调用回测API，将日期对象格式化为字符串
      const response = await apiClient.runBacktest({
        symbols: symbolList.length === 1 ? symbolList[0] : symbolList,
        start_date: format(startDate, 'yyyy-MM-dd'),
        end_date: format(endDate, 'yyyy-MM-dd'),
        initial_cash: initialCash,
        strategy_id: selectedStrategyId,
        strategy_params: Object.keys(strategyParams).length > 0 ? strategyParams : undefined
      })

      setProgress('正在计算绩效指标...')

      if (response.data) {
        setProgress('回测完成！')
        // 显示成功 toast
        toast({
          title: "回测完成",
          description: `策略 ${response.data.strategy_name} 回测成功`,
        })
        // 将结果传递给父组件
        if (onBacktestComplete) {
          onBacktestComplete(response.data)
        }
      } else {
        throw new Error('回测失败')
      }
    } catch (err: any) {
      console.error('回测错误:', err)
      const errorMsg = err.response?.data?.detail || err.message || '回测失败，请检查参数'
      setError(errorMsg)
      // 显示错误 toast
      toast({
        variant: "destructive",
        title: "回测失败",
        description: errorMsg,
      })
    } finally {
      setIsLoading(false)
      setTimeout(() => setProgress(''), 3000)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>回测配置</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
        {/* 基础配置 */}
        <div className="space-y-4 pb-4 border-b">
          {/* 股票代码 */}
          <div className="space-y-2">
            <Label htmlFor="symbols">股票代码</Label>
            <Input
              id="symbols"
              type="text"
              value={symbols}
              onChange={(e) => setSymbols(e.target.value)}
              placeholder="600000 或 000031,600519"
              required
            />
            <p className="text-xs text-muted-foreground">
              支持单股或多股（逗号分隔），无需添加交易所后缀
            </p>
          </div>

          {/* 日期范围 */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>开始日期</Label>
              <DatePicker
                date={startDate}
                onDateChange={(date) => date && setStartDate(date)}
                placeholder="选择开始日期"
              />
            </div>
            <div className="space-y-2">
              <Label>结束日期</Label>
              <DatePicker
                date={endDate}
                onDateChange={(date) => date && setEndDate(date)}
                placeholder="选择结束日期"
              />
            </div>
          </div>

          {/* 初始资金 */}
          <div className="space-y-2">
            <Label htmlFor="initialCash">
              初始资金: ¥{initialCash.toLocaleString()}
            </Label>
            <input
              id="initialCash"
              type="range"
              min="100000"
              max="10000000"
              step="100000"
              value={initialCash}
              onChange={(e) => setInitialCash(Number(e.target.value))}
              className="w-full h-2 bg-secondary rounded-lg appearance-none cursor-pointer accent-primary"
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>10万</span>
              <span>1000万</span>
            </div>
          </div>
        </div>

        {/* 策略选择 */}
        <div className="space-y-3">
          <Label>回测策略</Label>

          <div className="space-y-2">
            {strategies.map(strategy => (
              <div
                key={strategy.id}
                className={`p-3 border rounded-lg transition-colors ${
                  selectedStrategyId === strategy.id
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
                }`}
              >
                {/* 第一行: 单选框 + 名称 + 版本号 + 设置按钮 */}
                <div className="flex items-center justify-between gap-2">
                  <div
                    className="flex items-center gap-2 flex-1 cursor-pointer"
                    onClick={() => setSelectedStrategyId(strategy.id)}
                  >
                    <input
                      type="radio"
                      checked={selectedStrategyId === strategy.id}
                      onChange={() => setSelectedStrategyId(strategy.id)}
                      className="text-blue-600"
                    />
                    <span className="font-medium text-gray-900 dark:text-white">
                      {strategy.name}
                    </span>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      v{strategy.version}
                    </span>
                  </div>

                  {/* 参数配置按钮 - 在第一行右侧 */}
                  {strategy.parameter_count > 0 && (
                    <Dialog
                      open={dialogOpenStrategyId === strategy.id}
                      onOpenChange={(open) => setDialogOpenStrategyId(open ? strategy.id : null)}
                    >
                      <DialogTrigger asChild>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="shrink-0"
                          onClick={(e) => {
                            e.stopPropagation()
                            setSelectedStrategyId(strategy.id)
                          }}
                        >
                          <Settings className="h-4 w-4" />
                        </Button>
                      </DialogTrigger>
                      <DialogContent className="max-w-[95vw] sm:max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
                        <DialogHeader>
                          <DialogTitle className="text-base sm:text-lg">
                            {strategy.name} - 参数配置
                          </DialogTitle>
                        </DialogHeader>
                        <div className="flex-1 overflow-y-auto py-2 sm:py-4 px-1">
                          <StrategyParamsPanel
                            strategyId={strategy.id}
                            onParamsChange={setStrategyParams}
                            isInDialog={true}
                          />
                        </div>
                      </DialogContent>
                    </Dialog>
                  )}
                </div>

                {/* 第二行: 参数数量标签 */}
                {strategy.parameter_count > 0 && (
                  <div className="ml-6">
                    <span className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-xs text-gray-600 dark:text-gray-400 rounded">
                      {strategy.parameter_count} 个参数
                    </span>
                  </div>
                )}

                {/* 第三行: 描述信息 */}
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-2 ml-6">
                  {strategy.description}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        {/* 运行按钮 */}
        <Button
          type="submit"
          disabled={isLoading}
          className="w-full"
        >
          {isLoading ? (
            <span className="flex items-center justify-center">
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              {progress || '运行中...'}
            </span>
          ) : (
            '运行回测'
          )}
        </Button>
        </form>
      </CardContent>
    </Card>
  )
}
