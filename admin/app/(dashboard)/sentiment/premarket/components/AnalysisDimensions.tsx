import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import type { CollisionAnalysis } from "@/types/premarket"

interface AnalysisDimensionsProps {
  analysis: CollisionAnalysis
}

/**
 * 四维度分析组件
 * 显示宏观定调、持仓排雷、计划修正、竞价盯盘四个维度
 */
export function AnalysisDimensions({ analysis }: AnalysisDimensionsProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* 宏观定调 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">🎯 宏观定调</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {analysis.macro_tone ? (
            <>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">开盘预期:</span>
                <Badge className="text-lg py-1 px-3">
                  {analysis.macro_tone.direction}
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">置信度:</span>
                <span className="font-bold">{analysis.macro_tone.confidence}</span>
              </div>
              <div className="bg-blue-50 dark:bg-blue-900/10 p-3 rounded text-sm">
                <div className="font-medium mb-1">A50影响:</div>
                <p>{analysis.macro_tone.a50_impact}</p>
              </div>
              <div className="bg-gray-50 dark:bg-gray-900/10 p-3 rounded text-sm">
                <div className="font-medium mb-1">综合判断:</div>
                <p>{analysis.macro_tone.reasoning}</p>
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">暂无数据</p>
          )}
        </CardContent>
      </Card>

      {/* 持仓排雷 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">⚠️ 持仓排雷</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {analysis.holdings_alert ? (
            <>
              <div className="flex items-center gap-2">
                {analysis.holdings_alert.has_risk ? (
                  <Badge variant="destructive">发现风险</Badge>
                ) : (
                  <Badge className="bg-green-500">无风险</Badge>
                )}
              </div>
              {analysis.holdings_alert.affected_sectors.length > 0 && (
                <div>
                  <div className="text-sm text-muted-foreground mb-2">受影响板块:</div>
                  <div className="flex flex-wrap gap-1">
                    {analysis.holdings_alert.affected_sectors.map((sector, idx) => (
                      <Badge key={idx} variant="outline">{sector}</Badge>
                    ))}
                  </div>
                </div>
              )}
              {analysis.holdings_alert.affected_stocks.length > 0 && (
                <div>
                  <div className="text-sm text-muted-foreground mb-2">受影响个股:</div>
                  <div className="space-y-2">
                    {analysis.holdings_alert.affected_stocks.map((stock, idx) => (
                      <div key={idx} className="bg-red-50 dark:bg-red-900/10 p-2 rounded text-sm">
                        <div className="font-medium">{stock.name} ({stock.code})</div>
                        <div className="text-xs text-muted-foreground">{stock.reason}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {analysis.holdings_alert.actions && (
                <div className="bg-orange-50 dark:bg-orange-900/10 p-3 rounded text-sm">
                  <div className="font-medium mb-1">操作建议:</div>
                  <p>{analysis.holdings_alert.actions}</p>
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-muted-foreground">暂无数据</p>
          )}
        </CardContent>
      </Card>

      {/* 计划修正 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">📝 计划修正</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {analysis.plan_adjustment ? (
            <>
              {analysis.plan_adjustment.cancel_buy.length > 0 && (
                <div>
                  <div className="text-sm text-muted-foreground mb-2">❌ 取消买入:</div>
                  <div className="space-y-2">
                    {analysis.plan_adjustment.cancel_buy.map((item, idx) => (
                      <div key={idx} className="bg-red-50 dark:bg-red-900/10 p-2 rounded text-sm">
                        <div className="font-medium">{item.stock}</div>
                        <div className="text-xs text-muted-foreground">{item.reason}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {analysis.plan_adjustment.early_stop_loss.length > 0 && (
                <div>
                  <div className="text-sm text-muted-foreground mb-2">🛑 提前止损:</div>
                  <div className="space-y-2">
                    {analysis.plan_adjustment.early_stop_loss.map((item, idx) => (
                      <div key={idx} className="bg-orange-50 dark:bg-orange-900/10 p-2 rounded text-sm">
                        <div className="font-medium">{item.stock}</div>
                        <div className="text-xs text-muted-foreground">{item.reason}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {analysis.plan_adjustment.keep_plan && (
                <div className="bg-green-50 dark:bg-green-900/10 p-3 rounded text-sm">
                  <div className="font-medium mb-1">✅ 保持计划:</div>
                  <p>{analysis.plan_adjustment.keep_plan}</p>
                </div>
              )}
              <div className="bg-gray-50 dark:bg-gray-900/10 p-3 rounded text-sm">
                <div className="font-medium mb-1">推理过程:</div>
                <p>{analysis.plan_adjustment.reasoning}</p>
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">暂无数据</p>
          )}
        </CardContent>
      </Card>

      {/* 竞价盯盘 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">👀 竞价盯盘 (9:15-9:25)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {analysis.auction_focus ? (
            <>
              {analysis.auction_focus.stocks.length > 0 && (
                <div>
                  <div className="text-sm text-muted-foreground mb-2">核心标的:</div>
                  <div className="space-y-2">
                    {analysis.auction_focus.stocks.map((stock, idx) => (
                      <div key={idx} className="bg-blue-50 dark:bg-blue-900/10 p-2 rounded text-sm">
                        <div className="font-medium">{stock.name} ({stock.code})</div>
                        <div className="text-xs text-muted-foreground">{stock.reason}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {analysis.auction_focus.conditions && (
                <div className="space-y-2">
                  <div className="bg-green-50 dark:bg-green-900/10 p-3 rounded text-sm">
                    <div className="font-medium mb-1">✅ 参与条件:</div>
                    <p>{analysis.auction_focus.conditions.participate_conditions}</p>
                  </div>
                  <div className="bg-red-50 dark:bg-red-900/10 p-3 rounded text-sm">
                    <div className="font-medium mb-1">❌ 禁止条件:</div>
                    <p>{analysis.auction_focus.conditions.avoid_conditions}</p>
                  </div>
                </div>
              )}
              {analysis.auction_focus.actions && (
                <div className="bg-purple-50 dark:bg-purple-900/10 p-3 rounded text-sm">
                  <div className="font-medium mb-1">操作步骤:</div>
                  <p>{analysis.auction_focus.actions}</p>
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-muted-foreground">暂无数据</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
