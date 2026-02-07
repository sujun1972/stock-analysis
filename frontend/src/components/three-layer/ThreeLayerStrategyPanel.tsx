'use client'

import { useEffect, useState } from 'react'
import { threeLayerApi } from '@/lib/three-layer'
import type { SelectorInfo, EntryInfo, ExitInfo, StrategyConfig, BacktestResult } from '@/lib/three-layer-types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ParametersForm } from './ParametersForm'
import { BacktestResultView } from './BacktestResultView'
import { useToast } from '@/hooks/use-toast'
import { Loader2, CheckCircle2, AlertCircle } from 'lucide-react'

export function ThreeLayerStrategyPanel() {
  const { toast } = useToast()

  // 可用组件列表
  const [selectors, setSelectors] = useState<SelectorInfo[]>([])
  const [entries, setEntries] = useState<EntryInfo[]>([])
  const [exits, setExits] = useState<ExitInfo[]>([])
  const [loadingComponents, setLoadingComponents] = useState(true)

  // 选中的组件
  const [selectedSelector, setSelectedSelector] = useState<string>('')
  const [selectedEntry, setSelectedEntry] = useState<string>('')
  const [selectedExit, setSelectedExit] = useState<string>('')

  // 参数
  const [selectorParams, setSelectorParams] = useState<Record<string, any>>({})
  const [entryParams, setEntryParams] = useState<Record<string, any>>({})
  const [exitParams, setExitParams] = useState<Record<string, any>>({})

  // 回测配置
  const [stockCodes, setStockCodes] = useState<string>('600000.SH,000001.SZ')
  const [startDate, setStartDate] = useState('2024-01-01')
  const [endDate, setEndDate] = useState('2024-12-31')
  const [rebalanceFreq, setRebalanceFreq] = useState<'D' | 'W' | 'M'>('W')
  const [initialCapital, setInitialCapital] = useState<number>(1000000)

  // 状态
  const [loading, setLoading] = useState(false)
  const [validating, setValidating] = useState(false)
  const [result, setResult] = useState<BacktestResult | null>(null)

  // 加载可用组件
  useEffect(() => {
    const loadComponents = async () => {
      try {
        setLoadingComponents(true)
        const { selectors: s, entries: e, exits: x } = await threeLayerApi.getAllComponents()
        setSelectors(s)
        setEntries(e)
        setExits(x)

        // 自动选择第一个组件（可选）
        if (s.length > 0) setSelectedSelector(s[0].id)
        if (e.length > 0) setSelectedEntry(e[0].id)
        if (x.length > 0) setSelectedExit(x[0].id)
      } catch (error) {
        toast({
          title: '加载组件失败',
          description: error instanceof Error ? error.message : '请检查后端服务是否运行',
          variant: 'destructive',
        })
        console.error(error)
      } finally {
        setLoadingComponents(false)
      }
    }
    loadComponents()
  }, [toast])

  // 验证策略
  const handleValidate = async () => {
    if (!selectedSelector || !selectedEntry || !selectedExit) {
      toast({
        title: '配置不完整',
        description: '请选择完整的三层策略（选股器、入场策略、退出策略）',
        variant: 'destructive',
      })
      return
    }

    setValidating(true)
    try {
      const config: StrategyConfig = {
        selector_id: selectedSelector,
        selector_params: selectorParams,
        entry_id: selectedEntry,
        entry_params: entryParams,
        exit_id: selectedExit,
        exit_params: exitParams,
        stock_codes: stockCodes.split(',').map(s => s.trim()).filter(s => s),
        start_date: startDate,
        end_date: endDate,
        rebalance_freq: rebalanceFreq,
        initial_capital: initialCapital,
      }

      const validation = await threeLayerApi.validateStrategy(config)

      if (validation.valid) {
        toast({
          title: '验证通过',
          description: '策略配置有效，可以运行回测',
        })
      } else {
        toast({
          title: '验证失败',
          description: validation.errors.join(', '),
          variant: 'destructive',
        })
      }

      if (validation.warnings.length > 0) {
        toast({
          title: '警告',
          description: validation.warnings.join(', '),
        })
      }
    } catch (error) {
      toast({
        title: '验证失败',
        description: error instanceof Error ? error.message : '未知错误',
        variant: 'destructive',
      })
      console.error(error)
    } finally {
      setValidating(false)
    }
  }

  // 运行回测
  const handleRunBacktest = async () => {
    if (!selectedSelector || !selectedEntry || !selectedExit) {
      toast({
        title: '配置不完整',
        description: '请选择完整的三层策略',
        variant: 'destructive',
      })
      return
    }

    setLoading(true)
    setResult(null)

    try {
      const config: StrategyConfig = {
        selector_id: selectedSelector,
        selector_params: selectorParams,
        entry_id: selectedEntry,
        entry_params: entryParams,
        exit_id: selectedExit,
        exit_params: exitParams,
        stock_codes: stockCodes.split(',').map(s => s.trim()).filter(s => s),
        start_date: startDate,
        end_date: endDate,
        rebalance_freq: rebalanceFreq,
        initial_capital: initialCapital,
      }

      const backtestResult = await threeLayerApi.runBacktest(config)

      if (backtestResult.status === 'success' && backtestResult.data) {
        setResult(backtestResult)
        toast({
          title: '回测完成',
          description: `总收益率: ${(backtestResult.data.total_return * 100).toFixed(2)}%`,
        })
      } else {
        toast({
          title: '回测失败',
          description: backtestResult.message || backtestResult.error || '未知错误',
          variant: 'destructive',
        })
      }
    } catch (error) {
      toast({
        title: '回测失败',
        description: error instanceof Error ? error.message : '未知错误',
        variant: 'destructive',
      })
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  // 获取选中组件的参数定义
  const getSelectorParams = () =>
    selectors.find(s => s.id === selectedSelector)?.parameters || []
  const getEntryParams = () =>
    entries.find(e => e.id === selectedEntry)?.parameters || []
  const getExitParams = () =>
    exits.find(x => x.id === selectedExit)?.parameters || []

  if (loadingComponents) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <span className="ml-2 text-muted-foreground">加载策略组件...</span>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 第一层：选股器 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <span className="flex items-center justify-center w-8 h-8 rounded-full bg-primary text-primary-foreground text-sm font-bold">
              1
            </span>
            第一层：选股器
          </CardTitle>
          <CardDescription>
            从全市场筛选候选股票池（周频/月频）- 共{selectors.length}个可用
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="selector">选择选股器</Label>
              <Select
                value={selectedSelector}
                onValueChange={(value) => {
                  setSelectedSelector(value)
                  setSelectorParams({})
                }}
              >
                <SelectTrigger id="selector">
                  <SelectValue placeholder="选择选股器..." />
                </SelectTrigger>
                <SelectContent>
                  {selectors.map(s => (
                    <SelectItem key={s.id} value={s.id}>
                      {s.name} - {s.description}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {selectedSelector && (
              <ParametersForm
                parameters={getSelectorParams()}
                values={selectorParams}
                onChange={setSelectorParams}
              />
            )}
          </div>
        </CardContent>
      </Card>

      {/* 第二层：入场策略 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <span className="flex items-center justify-center w-8 h-8 rounded-full bg-primary text-primary-foreground text-sm font-bold">
              2
            </span>
            第二层：入场策略
          </CardTitle>
          <CardDescription>
            决定何时买入候选股票（日频）- 共{entries.length}个可用
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="entry">选择入场策略</Label>
              <Select
                value={selectedEntry}
                onValueChange={(value) => {
                  setSelectedEntry(value)
                  setEntryParams({})
                }}
              >
                <SelectTrigger id="entry">
                  <SelectValue placeholder="选择入场策略..." />
                </SelectTrigger>
                <SelectContent>
                  {entries.map(e => (
                    <SelectItem key={e.id} value={e.id}>
                      {e.name} - {e.description}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {selectedEntry && (
              <ParametersForm
                parameters={getEntryParams()}
                values={entryParams}
                onChange={setEntryParams}
              />
            )}
          </div>
        </CardContent>
      </Card>

      {/* 第三层：退出策略 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <span className="flex items-center justify-center w-8 h-8 rounded-full bg-primary text-primary-foreground text-sm font-bold">
              3
            </span>
            第三层：退出策略
          </CardTitle>
          <CardDescription>
            管理持仓，决定何时卖出（日频/实时）- 共{exits.length}个可用
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="exit">选择退出策略</Label>
              <Select
                value={selectedExit}
                onValueChange={(value) => {
                  setSelectedExit(value)
                  setExitParams({})
                }}
              >
                <SelectTrigger id="exit">
                  <SelectValue placeholder="选择退出策略..." />
                </SelectTrigger>
                <SelectContent>
                  {exits.map(x => (
                    <SelectItem key={x.id} value={x.id}>
                      {x.name} - {x.description}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {selectedExit && (
              <ParametersForm
                parameters={getExitParams()}
                values={exitParams}
                onChange={setExitParams}
              />
            )}
          </div>
        </CardContent>
      </Card>

      {/* 回测配置 */}
      <Card>
        <CardHeader>
          <CardTitle>回测配置</CardTitle>
          <CardDescription>配置回测参数，包括股票池、时间范围和资金设置</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="stock-codes">股票池</Label>
              <Input
                id="stock-codes"
                type="text"
                value={stockCodes}
                onChange={(e) => setStockCodes(e.target.value)}
                placeholder="600000.SH,000001.SZ"
              />
              <p className="text-xs text-muted-foreground">
                多个股票代码用逗号分隔
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="rebalance-freq">调仓频率</Label>
              <Select
                value={rebalanceFreq}
                onValueChange={(v) => setRebalanceFreq(v as 'D' | 'W' | 'M')}
              >
                <SelectTrigger id="rebalance-freq">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="D">日频（每日调仓）</SelectItem>
                  <SelectItem value="W">周频（每周调仓）</SelectItem>
                  <SelectItem value="M">月频（每月调仓）</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="start-date">开始日期</Label>
              <Input
                id="start-date"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="end-date">结束日期</Label>
              <Input
                id="end-date"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="initial-capital">初始资金（元）</Label>
              <Input
                id="initial-capital"
                type="number"
                min="0"
                step="10000"
                value={initialCapital}
                onChange={(e) => setInitialCapital(Number(e.target.value))}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 操作按钮 */}
      <div className="flex gap-4">
        <Button
          variant="outline"
          onClick={handleValidate}
          disabled={!selectedSelector || !selectedEntry || !selectedExit || validating}
          className="gap-2"
        >
          {validating ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              验证中...
            </>
          ) : (
            <>
              <CheckCircle2 className="h-4 w-4" />
              验证策略
            </>
          )}
        </Button>
        <Button
          onClick={handleRunBacktest}
          disabled={!selectedSelector || !selectedEntry || !selectedExit || loading}
          size="lg"
          className="gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              运行中...
            </>
          ) : (
            '运行回测'
          )}
        </Button>
      </div>

      {/* ���测结果 */}
      {result && result.data && <BacktestResultView result={result} />}
      {result && result.status === 'error' && (
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              回测失败
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {result.message || result.error || '未知错误'}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
