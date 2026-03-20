import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { CalendarIcon, RefreshCwIcon, Database, BrainCircuit } from "lucide-react"
import { format, zhCN } from "@/lib/date-utils"
import { cn } from "@/lib/utils"
import type { AIProvider } from '../hooks/useAIProviders'

interface ControlPanelProps {
  date: Date
  onDateChange: (date: Date | undefined) => void
  aiProvider: string
  onAiProviderChange: (value: string) => void
  aiProviders: AIProvider[]
  isLoadingProviders: boolean
  isSyncing: boolean
  isGenerating: boolean
  isLoading: boolean
  onSync: () => void
  onGenerate: () => void
  onRefresh: () => void
}

/**
 * 控制面板组件
 * 包含日期选择器、AI提供商选择器和操作按钮
 */
export function ControlPanel({
  date,
  onDateChange,
  aiProvider,
  onAiProviderChange,
  aiProviders,
  isLoadingProviders,
  isSyncing,
  isGenerating,
  isLoading,
  onSync,
  onGenerate,
  onRefresh
}: ControlPanelProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>控制面板</CardTitle>
        <CardDescription>选择日期，同步数据或生成AI碰撞分析</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-col space-y-4">
          {/* 第一行：日期和AI提供商选择 */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* 日期选择 */}
            <div className="w-full">
              <label className="text-sm font-medium mb-2 block">分析日期</label>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className={cn(
                      "w-full justify-start text-left font-normal",
                      !date && "text-muted-foreground"
                    )}
                  >
                    <CalendarIcon className="mr-2 h-4 w-4 flex-shrink-0" />
                    <span className="truncate">
                      {date ? format(date, "PPP", { locale: zhCN }) : "选择日期"}
                    </span>
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <Calendar
                    mode="single"
                    selected={date}
                    onSelect={onDateChange}
                    locale={zhCN}
                  />
                </PopoverContent>
              </Popover>
            </div>

            {/* AI提供商选择 */}
            <div className="w-full">
              <label className="text-sm font-medium mb-2 block">AI提供商</label>
              <Select value={aiProvider} onValueChange={onAiProviderChange} disabled={isLoadingProviders}>
                <SelectTrigger>
                  <SelectValue placeholder={isLoadingProviders ? "加载中..." : "选择AI提供商"} />
                </SelectTrigger>
                <SelectContent>
                  {aiProviders.length === 0 ? (
                    <div className="p-2 text-sm text-muted-foreground text-center">
                      暂无可用配置
                    </div>
                  ) : (
                    aiProviders.map((provider) => (
                      <SelectItem key={provider.id} value={provider.provider}>
                        <div className="flex flex-col">
                          <span>{provider.display_name} {provider.is_default && "(默认)"}</span>
                          <span className="text-xs text-muted-foreground">
                            {provider.model_name}
                          </span>
                        </div>
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* 第二行：操作按钮 */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            <Button
              onClick={onSync}
              disabled={isSyncing}
              variant="outline"
              className="w-full"
            >
              {isSyncing ? (
                <>
                  <RefreshCwIcon className="mr-2 h-4 w-4 animate-spin flex-shrink-0" />
                  <span className="truncate">同步中...</span>
                </>
              ) : (
                <>
                  <Database className="mr-2 h-4 w-4 flex-shrink-0" />
                  <span className="truncate">同步盘前数据</span>
                </>
              )}
            </Button>

            <Button
              onClick={onGenerate}
              disabled={isGenerating || aiProviders.length === 0}
              className="w-full"
            >
              {isGenerating ? (
                <>
                  <RefreshCwIcon className="mr-2 h-4 w-4 animate-spin flex-shrink-0" />
                  <span className="truncate">生成中...</span>
                </>
              ) : (
                <>
                  <BrainCircuit className="mr-2 h-4 w-4 flex-shrink-0" />
                  <span className="truncate">生成碰撞分析</span>
                </>
              )}
            </Button>

            <Button
              variant="outline"
              onClick={onRefresh}
              disabled={isLoading}
              className="w-full"
            >
              <RefreshCwIcon className={cn("mr-2 h-4 w-4 flex-shrink-0", isLoading && "animate-spin")} />
              <span className="truncate">刷新</span>
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
