/**
 * 模型对比表格
 * 显示LightGBM vs Ridge性能对比
 */

'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, TrendingDown, Trophy } from 'lucide-react';
import type { MLTrainingTask } from '@/store/mlStore';

interface ModelComparisonTableProps {
  task: MLTrainingTask;
}

export function ModelComparisonTable({ task }: ModelComparisonTableProps) {
  if (!task.has_baseline || !task.baseline_metrics) {
    return null;
  }

  const lgbMetrics = task.metrics || {};
  const ridgeMetrics = task.baseline_metrics || {};
  const comparison = task.comparison_result || {};
  const recommendation = task.recommendation;

  // 对比数据
  const comparisonData = [
    {
      metric: 'Test IC',
      lgb: lgbMetrics.ic || lgbMetrics.test_ic,
      ridge: ridgeMetrics.test_ic,
      higher_better: true,
      format: (v: number) => v.toFixed(4)
    },
    {
      metric: 'Rank IC',
      lgb: lgbMetrics.rank_ic || lgbMetrics.test_rank_ic,
      ridge: ridgeMetrics.test_rank_ic,
      higher_better: true,
      format: (v: number) => v.toFixed(4)
    },
    {
      metric: 'MAE',
      lgb: lgbMetrics.mae || lgbMetrics.test_mae,
      ridge: ridgeMetrics.test_mae,
      higher_better: false,
      format: (v: number) => v.toFixed(4)
    },
    {
      metric: 'R²',
      lgb: lgbMetrics.r2 || lgbMetrics.test_r2,
      ridge: ridgeMetrics.test_r2,
      higher_better: true,
      format: (v: number) => v.toFixed(4)
    },
    {
      metric: '过拟合 (IC差)',
      lgb: lgbMetrics.overfit_ic,
      ridge: ridgeMetrics.overfit_ic,
      higher_better: false,
      format: (v: number) => v.toFixed(4)
    },
  ];

  const getBetterValue = (row: typeof comparisonData[0]) => {
    if (row.lgb === undefined || row.ridge === undefined) return null;

    if (row.higher_better) {
      return row.ridge > row.lgb ? 'ridge' : 'lightgbm';
    } else {
      return row.ridge < row.lgb ? 'ridge' : 'lightgbm';
    }
  };

  return (
    <Card className="mt-4">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">模型对比结果</CardTitle>
          {recommendation && (
            <Badge
              variant={recommendation === 'ridge' ? 'default' : 'secondary'}
              className="flex items-center gap-1"
            >
              <Trophy className="h-3 w-3" />
              推荐: {recommendation === 'ridge' ? 'Ridge' : 'LightGBM'}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {/* 汇总信息 */}
        <div className="grid grid-cols-2 gap-4 mb-4 p-4 bg-muted/50 rounded-lg">
          <div>
            <p className="text-xs text-muted-foreground">总样本数</p>
            <p className="text-lg font-semibold">{task.total_samples?.toLocaleString()}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">成功股票</p>
            <p className="text-lg font-semibold">
              {task.successful_symbols?.length || 0} 只
            </p>
          </div>
        </div>

        {/* 对比表格 */}
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b">
                <th className="text-left py-3 px-4 font-medium text-sm">指标</th>
                <th className="text-center py-3 px-4 font-medium text-sm">LightGBM</th>
                <th className="text-center py-3 px-4 font-medium text-sm">Ridge</th>
                <th className="text-center py-3 px-4 font-medium text-sm">优势</th>
              </tr>
            </thead>
            <tbody>
              {comparisonData.map((row, index) => {
                const better = getBetterValue(row);

                return (
                  <tr key={index} className="border-b last:border-0 hover:bg-muted/30">
                    <td className="py-3 px-4 text-sm">{row.metric}</td>
                    <td className={`py-3 px-4 text-center font-mono text-sm ${
                      better === 'lightgbm' ? 'font-semibold text-green-600 dark:text-green-400' : ''
                    }`}>
                      {row.lgb !== undefined ? row.format(row.lgb) : '-'}
                    </td>
                    <td className={`py-3 px-4 text-center font-mono text-sm ${
                      better === 'ridge' ? 'font-semibold text-green-600 dark:text-green-400' : ''
                    }`}>
                      {row.ridge !== undefined ? row.format(row.ridge) : '-'}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {better === 'ridge' ? (
                        <Badge variant="default" className="text-xs">
                          Ridge
                        </Badge>
                      ) : better === 'lightgbm' ? (
                        <Badge variant="secondary" className="text-xs">
                          LightGBM
                        </Badge>
                      ) : (
                        <span className="text-xs text-muted-foreground">-</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* 对比摘要 */}
        {comparison.test_ic_diff !== undefined && (
          <div className="mt-4 p-4 border rounded-lg space-y-2">
            <h4 className="text-sm font-medium">性能差异</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">IC 差异</p>
                <p className="font-mono flex items-center gap-1">
                  {comparison.test_ic_diff > 0 ? (
                    <TrendingUp className="h-4 w-4 text-green-600" />
                  ) : (
                    <TrendingDown className="h-4 w-4 text-red-600" />
                  )}
                  {Math.abs(comparison.test_ic_diff).toFixed(4)}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">过拟合差异</p>
                <p className="font-mono flex items-center gap-1">
                  {comparison.overfit_diff < 0 ? (
                    <TrendingUp className="h-4 w-4 text-green-600" />
                  ) : (
                    <TrendingDown className="h-4 w-4 text-red-600" />
                  )}
                  {Math.abs(comparison.overfit_diff).toFixed(4)}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* 成功股票列表 */}
        {task.successful_symbols && task.successful_symbols.length > 0 && (
          <div className="mt-4">
            <p className="text-xs text-muted-foreground mb-2">成功加载的股票:</p>
            <div className="flex flex-wrap gap-1">
              {task.successful_symbols.map((symbol) => (
                <Badge key={symbol} variant="outline" className="text-xs">
                  {symbol}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
