# 股票表格颜色规范 (Stock Table Color)

## 概述

A股显示惯例：涨红跌绿。表格中与股票价格相关的列，颜色应跟随涨跌幅（`pct_change`）统一变化。

---

## 工具函数

**位置**：`admin/lib/utils.ts`

```typescript
/**
 * 根据涨跌幅返回对应的文字颜色 class
 * 涨（>0）→ 红色，跌（<0）→ 绿色，平（=0）→ 默认色
 */
export function pctChangeColor(pctChange: number | null | undefined): string {
  if (pctChange === null || pctChange === undefined) return ''
  if (pctChange > 0) return 'text-red-600'
  if (pctChange < 0) return 'text-green-600'
  return ''
}
```

使用方式：
```typescript
import { pctChangeColor } from '@/lib/utils'
```

---

## 应用规则

### 需要跟随涨跌幅着色的列

| 列 | 说明 |
|---|---|
| 股票代码 | 同时是可点击链接 |
| 股票名称 | 同时是可点击链接 |
| 收盘价 | |
| 涨跌幅% | |
| 换手率% | |
| 总成交额 | |
| 榜单成交额 | |

### 不着色的列

- 交易日期
- 净买入（有自己的正负颜色逻辑）
- 上榜理由

---

## 实现示例

### 普通列
```tsx
accessor: (row) => (
  <span className={pctChangeColor(row.pct_change)}>
    {row.close !== null ? row.close.toFixed(2) : '-'}
  </span>
),
```

### 可点击链接列（名称+代码合并列，格式：名称[代码]）
```tsx
accessor: (row) => (
  <span
    className={`cursor-pointer hover:underline ${pctChangeColor(row.pct_change)}`}
    onClick={() => openStockAnalysis(row.ts_code)}
  >
    {row.name || '-'}[{formatStockCode(row.ts_code)}]
  </span>
),
```

### 涨跌幅列（额外显示正负号）
```tsx
accessor: (row) => {
  if (row.pct_change === null) return '-'
  const value = row.pct_change
  return (
    <span className={pctChangeColor(value)}>
      {value >= 0 ? '+' : ''}{value.toFixed(2)}%
    </span>
  )
},
```

---

## 配套工具：股票代码格式化

**位置**：`admin/lib/utils.ts`

```typescript
/**
 * 提取股票纯代码（去除交易所后缀）
 * @example formatStockCode('002475.SZ') → '002475'
 */
export function formatStockCode(tsCode: string | null | undefined): string {
  if (!tsCode) return ''
  const dotIndex = tsCode.indexOf('.')
  return dotIndex !== -1 ? tsCode.slice(0, dotIndex) : tsCode
}
```

---

## 跳转分析页面

从系统配置读取分析页面 URL 模板，传入纯股票代码（不含交易所后缀）：

```typescript
import { useSystemConfig } from '@/contexts'
import { formatStockCode } from '@/lib/utils'

const { config } = useSystemConfig()

const openStockAnalysis = (tsCode: string) => {
  const url = config?.stock_analysis_url
  if (!url) return
  window.open(url.replace('{code}', formatStockCode(tsCode)), '_blank')
}
```

配置 key：`stock_analysis_url`，默认值：`http://localhost:3000/analysis?code={code}`

---

## 参考实现

`admin/app/(dashboard)/boardgame/top-list/page.tsx`
