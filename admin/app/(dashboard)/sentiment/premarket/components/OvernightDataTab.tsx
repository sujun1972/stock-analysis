import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AlertTriangleIcon } from "lucide-react"
import { cn } from "@/lib/utils"
import type { OvernightData } from "@/types/premarket"

interface OvernightDataTabProps {
  overnightData: OvernightData | null
}

// 获取变化率颜色
const getChangeColor = (change: number) => {
  if (change > 0) return "text-red-500"
  if (change < 0) return "text-green-500"
  return "text-gray-500"
}

// 获取变化率前缀
const getChangePrefix = (change: number) => {
  if (change > 0) return "+"
  return ""
}

/**
 * 外盘数据标签页组件
 * 显示A50、中概股、大宗商品、外汇、美股等外盘数据
 */
export function OvernightDataTab({ overnightData }: OvernightDataTabProps) {
  if (!overnightData) {
    return (
      <Alert>
        <AlertTriangleIcon className="h-4 w-4" />
        <AlertTitle>暂无数据</AlertTitle>
        <AlertDescription>
          请先点击"同步盘前数据"按钮获取隔夜外盘数据
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="space-y-4">
      {/* A50和中概股 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">富时A50期指</CardTitle>
            <CardDescription>直接影响A股大盘开盘</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold">{overnightData.a50.close.toFixed(2)}</span>
              <span className={cn("text-xl font-semibold", getChangeColor(overnightData.a50.change))}>
                {getChangePrefix(overnightData.a50.change)}{overnightData.a50.change.toFixed(2)}%
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">中概股指数</CardTitle>
            <CardDescription>外资对中国资产的态度</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold">{overnightData.china_concept.close.toFixed(2)}</span>
              <span className={cn("text-xl font-semibold", getChangeColor(overnightData.china_concept.change))}>
                {getChangePrefix(overnightData.china_concept.change)}{overnightData.china_concept.change.toFixed(2)}%
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 大宗商品 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">大宗商品</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
              <div className="text-sm text-muted-foreground mb-1">WTI原油</div>
              <div className="flex items-baseline gap-2">
                <span className="text-xl sm:text-2xl font-bold">{overnightData.wti_crude.close.toFixed(2)}</span>
                <span className={cn("text-sm sm:text-base font-semibold", getChangeColor(overnightData.wti_crude.change))}>
                  {getChangePrefix(overnightData.wti_crude.change)}{overnightData.wti_crude.change.toFixed(2)}%
                </span>
              </div>
            </div>
            <div className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
              <div className="text-sm text-muted-foreground mb-1">COMEX黄金</div>
              <div className="flex items-baseline gap-2">
                <span className="text-xl sm:text-2xl font-bold">{overnightData.comex_gold.close.toFixed(2)}</span>
                <span className={cn("text-sm sm:text-base font-semibold", getChangeColor(overnightData.comex_gold.change))}>
                  {getChangePrefix(overnightData.comex_gold.change)}{overnightData.comex_gold.change.toFixed(2)}%
                </span>
              </div>
            </div>
            <div className="p-3 bg-gray-50 dark:bg-gray-900 rounded-lg">
              <div className="text-sm text-muted-foreground mb-1">伦敦铜</div>
              <div className="flex items-baseline gap-2">
                <span className="text-xl sm:text-2xl font-bold">{overnightData.lme_copper.close.toFixed(2)}</span>
                <span className={cn("text-sm sm:text-base font-semibold", getChangeColor(overnightData.lme_copper.change))}>
                  {getChangePrefix(overnightData.lme_copper.change)}{overnightData.lme_copper.change.toFixed(2)}%
                </span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 外汇和美股 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">美元兑离岸人民币</CardTitle>
            <CardDescription>资金流向指标</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold">{overnightData.usdcnh.close.toFixed(4)}</span>
              <span className={cn("text-xl font-semibold", getChangeColor(overnightData.usdcnh.change))}>
                {getChangePrefix(overnightData.usdcnh.change)}{overnightData.usdcnh.change.toFixed(2)}%
              </span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">美股三大指数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">标普500:</span>
                <div className="flex items-center gap-2">
                  <span className="font-semibold">{overnightData.sp500.close.toFixed(2)}</span>
                  <span className={cn("font-semibold", getChangeColor(overnightData.sp500.change))}>
                    {getChangePrefix(overnightData.sp500.change)}{overnightData.sp500.change.toFixed(2)}%
                  </span>
                </div>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">纳斯达克:</span>
                <div className="flex items-center gap-2">
                  <span className="font-semibold">{overnightData.nasdaq.close.toFixed(2)}</span>
                  <span className={cn("font-semibold", getChangeColor(overnightData.nasdaq.change))}>
                    {getChangePrefix(overnightData.nasdaq.change)}{overnightData.nasdaq.change.toFixed(2)}%
                  </span>
                </div>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">道琼斯:</span>
                <div className="flex items-center gap-2">
                  <span className="font-semibold">{overnightData.dow.close.toFixed(2)}</span>
                  <span className={cn("font-semibold", getChangeColor(overnightData.dow.change))}>
                    {getChangePrefix(overnightData.dow.change)}{overnightData.dow.change.toFixed(2)}%
                  </span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
