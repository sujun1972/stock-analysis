/**
 * 系统设置页面
 *
 * 功能：
 * - 管理系统级别的配置
 * - 股票分析页面跳转URL配置（支持灵活的URL模板）
 * - 支持query参数和path参数两种方式
 *
 * 优化：使用 React Query 管理数据状态
 */
'use client'

import { useState, useEffect } from 'react'
import { toast } from 'sonner'
import { Settings, Save, RotateCcw, ExternalLink, Info } from 'lucide-react'
import { useSystemConfig } from '@/contexts'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useSystemSettings, useUpdateSystemSettings } from '@/hooks/queries/use-system'

export default function SystemSettingsPage() {
  const { refreshConfig } = useSystemConfig()
  const [stockAnalysisUrl, setStockAnalysisUrl] = useState('')
  const [originalUrl, setOriginalUrl] = useState('')

  // 使用 React Query hooks
  const { data: settings, isLoading } = useSystemSettings()
  const updateSettingsMutation = useUpdateSystemSettings()

  // 初始化设置值
  useEffect(() => {
    if (settings) {
      const url = settings.stock_analysis_url || 'http://localhost:3000/analysis?code={code}'
      setStockAnalysisUrl(url)
      setOriginalUrl(url)
    }
  }, [settings])

  // 保存系统设置
  const handleSave = async () => {
    if (!stockAnalysisUrl.trim()) {
      toast.error('股票分析URL不能为空')
      return
    }

    if (!stockAnalysisUrl.includes('{code}')) {
      toast.error('URL模板必须包含 {code} 占位符')
      return
    }

    updateSettingsMutation.mutate(
      { stock_analysis_url: stockAnalysisUrl },
      {
        onSuccess: async () => {
          // 刷新全局配置，使其他页面立即生效
          await refreshConfig()
          setOriginalUrl(stockAnalysisUrl)
        }
      }
    )
  }

  // 重置为原始值
  const handleReset = () => {
    setStockAnalysisUrl(originalUrl)
    toast.info('已重置为保存的值')
  }

  // 测试URL
  const handleTestUrl = () => {
    const testCode = '000001'
    const testUrl = stockAnalysisUrl.replace('{code}', testCode)
    window.open(testUrl, '_blank')
    toast.info(`正在测试URL: ${testUrl}`)
  }

  // 生成预览URL
  const getPreviewUrl = () => {
    if (!stockAnalysisUrl) return ''
    return stockAnalysisUrl.replace('{code}', '000001')
  }

  const hasChanges = stockAnalysisUrl !== originalUrl
  const isValidTemplate = stockAnalysisUrl.includes('{code}')

  return (
    <div className="space-y-6">
      {/* 页头 */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight flex items-center gap-2">
          <Settings className="h-8 w-8" />
          系统配置
        </h1>
        <p className="text-sm sm:text-base text-muted-foreground mt-2">
          管理系统级别的全局配置
        </p>
      </div>

      {/* 股票分析URL设置 */}
      <Card>
        <CardHeader>
          <CardTitle>股票分析页面配置</CardTitle>
          <CardDescription>
            设置点击股票名称后跳转的分析页面URL模板
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
              <span className="ml-3 text-muted-foreground">加载中...</span>
            </div>
          ) : (
            <>
              <div className="space-y-2">
                <Label htmlFor="stockAnalysisUrl">URL 模板</Label>
                <Input
                  id="stockAnalysisUrl"
                  type="text"
                  placeholder="http://localhost:3000/analysis?code={code}"
                  value={stockAnalysisUrl}
                  onChange={(e) => setStockAnalysisUrl(e.target.value)}
                  className="font-mono"
                />
                <p className="text-xs text-muted-foreground">
                  使用 <code className="bg-muted px-1 rounded">{'{code}'}</code> 作为股票代码的占位符
                </p>
              </div>

              {/* 实时预览 */}
              {stockAnalysisUrl && (
                <div className="space-y-2">
                  <Label className="text-sm">预览（使用000001测试）</Label>
                  <div className="bg-muted p-3 rounded-md">
                    <code className="text-sm break-all">
                      {getPreviewUrl()}
                    </code>
                  </div>
                </div>
              )}

              {/* 验证提示 */}
              {stockAnalysisUrl && !isValidTemplate && (
                <Alert variant="destructive">
                  <Info className="h-4 w-4" />
                  <AlertDescription>
                    URL模板必须包含 <code>{'{code}'}</code> 占位符
                  </AlertDescription>
                </Alert>
              )}

              <div className="flex items-center gap-2 pt-2">
                <Button
                  onClick={handleTestUrl}
                  variant="outline"
                  disabled={!stockAnalysisUrl.trim() || !isValidTemplate}
                >
                  <ExternalLink className="h-4 w-4 mr-2" />
                  测试URL
                </Button>
                <span className="text-sm text-muted-foreground">
                  将使用股票代码 000001 测试跳转
                </span>
              </div>

              <div className="flex gap-2 pt-4 border-t">
                <Button
                  onClick={handleSave}
                  disabled={updateSettingsMutation.isPending || !hasChanges || !isValidTemplate}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  <Save className="h-4 w-4 mr-2" />
                  {updateSettingsMutation.isPending ? '保存中...' : '保存设置'}
                </Button>
                <Button
                  onClick={handleReset}
                  variant="outline"
                  disabled={!hasChanges}
                >
                  <RotateCcw className="h-4 w-4 mr-2" />
                  重置
                </Button>
              </div>

              {hasChanges && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                  <p className="text-sm text-yellow-800">
                    ⚠️ 您有未保存的更改
                  </p>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* 使用说明 */}
      <Card>
        <CardHeader>
          <CardTitle>配置说明</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2 text-sm">
            <p className="font-medium">支持的URL格式：</p>
            <div className="space-y-2">
              <div className="bg-muted p-3 rounded-md">
                <p className="font-medium mb-1">1. Query 参数方式（推荐）</p>
                <code className="text-xs block mb-1">http://localhost:3000/analysis?code={'{code}'}</code>
                <p className="text-xs text-muted-foreground">适用于大多数Web应用</p>
              </div>

              <div className="bg-muted p-3 rounded-md">
                <p className="font-medium mb-1">2. Path 参数方式</p>
                <code className="text-xs block mb-1">http://localhost:3000/stocks/{'{code}'}/analysis</code>
                <p className="text-xs text-muted-foreground">RESTful风格的URL</p>
              </div>

              <div className="bg-muted p-3 rounded-md">
                <p className="font-medium mb-1">3. 混合方式</p>
                <code className="text-xs block mb-1">http://localhost:3000/stock/{'{code}'}?tab=analysis</code>
                <p className="text-xs text-muted-foreground">同时使用path和query参数</p>
              </div>

              <div className="bg-muted p-3 rounded-md">
                <p className="font-medium mb-1">4. 自定义参数名</p>
                <code className="text-xs block mb-1">https://example.com/detail?symbol={'{code}'}&amp;market=cn</code>
                <p className="text-xs text-muted-foreground">支持自定义参数名称</p>
              </div>
            </div>
          </div>

          <div className="space-y-2 text-sm pt-4 border-t">
            <p className="font-medium">注意事项：</p>
            <ul className="list-disc list-inside space-y-1 text-muted-foreground ml-2">
              <li>URL 必须以 http:// 或 https:// 开头</li>
              <li>必须包含 <code className="bg-muted px-1 rounded">{'{code}'}</code> 占位符</li>
              <li><code className="bg-muted px-1 rounded">{'{code}'}</code> 会被替换为实际的股票代码（如 000001）</li>
              <li>可以在URL的任意位置使用 <code className="bg-muted px-1 rounded">{'{code}'}</code></li>
              <li>建议先使用&ldquo;测试URL&rdquo;按钮验证配置是否正确</li>
              <li>保存后立即生效，无需重启应用</li>
            </ul>
          </div>

          <div className="space-y-2 text-sm pt-4 border-t">
            <p className="font-medium">常见应用场景：</p>
            <ul className="list-disc list-inside space-y-1 text-muted-foreground ml-2">
              <li>跳转到本地开发环境的分析页面</li>
              <li>跳转到生产环境的股票详情页</li>
              <li>跳转到第三方金融数据平台（如同花顺、东方财富等）</li>
              <li>跳转到自定义的股票分析工具</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}