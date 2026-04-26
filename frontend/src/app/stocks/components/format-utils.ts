/**
 * 股票列表行/卡共用的数字格式化工具。
 * 桌面 StockTableRow 和移动 StockCard 使用同一套，避免单位/警戒值（如 PE>500）
 * 在两端语义漂移。
 */

/** 成交额 / 流水类金额（原始单位：元）→ X.XX 亿 / XXXX 万 / 元 */
export function fmtAmount(value: number | null | undefined): string {
  if (value == null || !isFinite(value)) return '—'
  const abs = Math.abs(value)
  if (abs >= 1e8) return `${(value / 1e8).toFixed(2)}亿`
  if (abs >= 1e4) return `${(value / 1e4).toFixed(0)}万`
  return value.toFixed(0)
}

/** 市值（daily_basic 原生单位：万元）→ ≥1 亿（10000 万元）显示 X.XX 亿，否则 XXXX 万 */
export function fmtMarketCap(wanYuan: number | null | undefined): string {
  if (wanYuan == null || !isFinite(wanYuan)) return '—'
  if (Math.abs(wanYuan) >= 1e4) return `${(wanYuan / 1e4).toFixed(0)}亿`
  return `${wanYuan.toFixed(0)}万`
}

export type PEFormatTone = 'normal' | 'muted' | 'warn'

/**
 * PE-TTM 渲染：
 * - null / NaN → "—" muted（缺数据）
 * - <0 → "亏损" warn（应警示）
 * - >500 → ">500" warn（虚高，超出合理估值区间）
 * - 正常 → 1 位小数 normal
 *
 * 调用方按 tone 选择 className：normal=正常字色 / muted=灰字 / warn=警示色
 */
export function fmtPE(pe: number | null | undefined): { text: string; tone: PEFormatTone } {
  if (pe == null || !isFinite(pe)) return { text: '—', tone: 'muted' }
  if (pe < 0) return { text: '亏损', tone: 'warn' }
  if (pe > 500) return { text: '>500', tone: 'warn' }
  return { text: pe.toFixed(1), tone: 'normal' }
}
