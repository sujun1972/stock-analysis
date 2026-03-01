/**
 * AI策略生成提示词助手组件
 * 提供标准化的AI提示词模板，帮助用户使用AI生成策略代码
 */

'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Sparkles,
  Copy,
  CheckCircle,
  Lightbulb,
  ChevronDown,
  ChevronUp,
  Wand2,
  FileText
} from 'lucide-react'
import { useToast } from '@/hooks/use-toast'

interface AIStrategyPromptHelperProps {
  onPromptGenerated?: (prompt: string) => void
}

export default function AIStrategyPromptHelper({ onPromptGenerated }: AIStrategyPromptHelperProps) {
  const { toast } = useToast()
  const [isExpanded, setIsExpanded] = useState(false)
  const [copied, setCopied] = useState(false)

  // 用户输入的策略需求
  const [strategyRequirement, setStrategyRequirement] = useState(`**策略类型**: 趋势跟踪策略

**核心逻辑**:
- 使用 EMA(20, 60, 120) 定义趋势层级
- 使用 MACD(12, 26, 9) 捕捉动能转折
- 买入条件：股价 > EMA120 且 EMA20 > EMA60 且 MACD在零轴上方金叉
- 卖出条件：MACD死叉 或 股价跌破EMA60

**技术指标**:
- EMA（指数移动平均线）
- MACD（指数平滑异同移动平均线）

**参数配置**:
- ema_short: 20 (短期均线周期)
- ema_mid: 60 (中期均线周期)
- ema_long: 120 (长期均线周期)
- macd_fast: 12, macd_slow: 26, macd_signal: 9

**风险控制**:
- 成交量需大于20日均量的80%
- 每期选择前20只股票`)

  // 完整提示词模板（可编辑）
  const [promptTemplate, setPromptTemplate] = useState(`# 量化交易策略代码生成任务

## 任务目标
请为我生成一个完整的Python量化交易策略代码，要求能够通过系统验证并可直接使用。

## 代码框架要求

### 1. 必须的导入语句
\`\`\`python
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
from core.strategies.base_strategy import BaseStrategy
\`\`\`

### 2. 必须实现的三个方法

#### 2.1 初始化方法 (__init__)
\`\`\`python
def __init__(self, name: str = "strategy_name", config: Dict[str, Any] = None):
    """
    初始化策略

    Args:
        name: 策略名称
        config: 策略配置字典
    """
    # 定义默认配置
    default_config = {
        'name': 'StrategyName',
        'description': '策略描述',
        'top_n': 20,                # 每期选择前N只股票
        'holding_period': 5,        # 最短持仓期（天）
        'rebalance_freq': 'W',      # 调仓频率 ('D'=日, 'W'=周, 'M'=月)

        # 在这里添加策略特有参数
        # 例如: 'ema_short': 20, 'ema_mid': 60
    }

    # 合并用户配置
    if config:
        default_config.update(config)

    super().__init__(name, default_config)
\`\`\`

#### 2.2 计算评分方法 (calculate_scores) - 必须实现
\`\`\`python
def calculate_scores(
    self,
    prices: pd.DataFrame,
    features: Optional[pd.DataFrame] = None,
    date: Optional[pd.Timestamp] = None
) -> pd.Series:
    """
    计算股票评分（用于排序选股）

    Args:
        prices: 价格DataFrame (index=date, columns=stock_codes)
        features: 特征DataFrame (可选)
        date: 指定日期（None表示最新日期）

    Returns:
        scores: 股票评分Series (index=stock_codes, values=scores)
                分数越高越好
    """
    if date is None:
        date = prices.index[-1]

    scores = pd.Series(0.0, index=prices.columns)

    for stock in prices.columns:
        try:
            stock_prices = prices[stock].dropna()
            if len(stock_prices) < 120:  # 数据不足，跳过
                continue

            # TODO: 在这里实现评分逻辑
            # 示例: 基于趋势和动能的综合评分
            # scores[stock] = trend_score * 0.6 + momentum_score * 0.4

        except Exception:
            continue

    return scores
\`\`\`

#### 2.3 生成信号方法 (generate_signals) - 必须实现
\`\`\`python
def generate_signals(
    self,
    prices: pd.DataFrame,
    features: Optional[pd.DataFrame] = None,
    **kwargs
) -> pd.DataFrame:
    """
    生成交易信号

    Args:
        prices: 价格DataFrame (index=date, columns=stock_codes, values=close_price)
        features: 特征DataFrame (可选)
        **kwargs: 其他参数

    Returns:
        signals: 信号DataFrame (index=date, columns=stock_codes)
            值: 1 = 买入, 0 = 持有, -1 = 卖出
    """
    # 初始化信号矩阵
    signals = pd.DataFrame(0, index=prices.index, columns=prices.columns)

    # 逐个股票计算信号
    for stock in prices.columns:
        try:
            stock_prices = prices[stock].dropna()
            if len(stock_prices) < 120:
                continue

            # TODO: 在这里实现信号生成逻辑
            # 1. 计算技术指标
            # 2. 判断买入条件
            # 3. 判断卖出条件

        except Exception:
            continue

    return signals
\`\`\`

## 常用技术指标计算参考

### 趋势指标
\`\`\`python
# 简单移动平均线 (SMA)
sma = prices.rolling(window=20).mean()

# 指数移动平均线 (EMA)
ema = prices.ewm(span=20, adjust=False).mean()

# 布林带 (Bollinger Bands)
sma = prices.rolling(window=20).mean()
std = prices.rolling(window=20).std()
upper_band = sma + (std * 2)
lower_band = sma - (std * 2)
\`\`\`

### 动量指标
\`\`\`python
# MACD
ema_fast = prices.ewm(span=12, adjust=False).mean()
ema_slow = prices.ewm(span=26, adjust=False).mean()
macd = ema_fast - ema_slow
signal = macd.ewm(span=9, adjust=False).mean()
histogram = macd - signal

# RSI (相对强弱指数)
delta = prices.diff()
gain = delta.where(delta > 0, 0).rolling(window=14).mean()
loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
rs = gain / loss
rsi = 100 - (100 / (1 + rs))

# 动量 (Momentum)
momentum = prices.pct_change(periods=20)  # 20日收益率
\`\`\`

### 波动率指标
\`\`\`python
# ATR (平均真实波幅) - 需要 high, low, close
tr1 = high - low
tr2 = abs(high - close.shift(1))
tr3 = abs(low - close.shift(1))
tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
atr = tr.rolling(window=14).mean()

# 标准差 (Volatility)
volatility = prices.pct_change().rolling(window=20).std()
\`\`\`

### 成交量指标
\`\`\`python
# 成交量移动平均
volume_ma = volumes.rolling(window=20).mean()
volume_ratio = volumes / volume_ma

# OBV (能量潮)
price_change = prices.diff()
obv = (volumes * np.sign(price_change)).cumsum()
\`\`\`

### 金叉/死叉检测
\`\`\`python
# 金叉（快线上穿慢线）
golden_cross = (fast_line > slow_line) & (fast_line.shift(1) <= slow_line.shift(1))

# 死叉（快线下穿慢线）
death_cross = (fast_line < slow_line) & (fast_line.shift(1) >= slow_line.shift(1))
\`\`\`

## 我的策略需求

{STRATEGY_REQUIREMENT}

## 代码规范要求

### 1. 类命名规范
- 使用大写驼峰命名（PascalCase）
- 例如: \`TrendMomentumStrategy\`, \`RSIReversalStrategy\`

### 2. 文档字符串
- 类和每个方法都必须有完整的文档字符串
- 使用Google风格的docstring
- 包含参数说明和返回值说明

### 3. 错误处理和数据验证
- 在循环中使用 try-except 捕获异常
- 数据不足时跳过该股票：\`if len(data) < min_length: continue\`
- 计算指标后必须验证结果：\`if pd.isna(value): continue\`
- 避免除零错误：使用 \`(value + 1e-9)\` 作为分母
- 避免因单只股票错误导致整个策略失败

### 4. 性能优化
- 避免在循环中重复计算
- 使用向量化操作替代循环（如果可能）

## 输出要求

请按照以下格式输出：

### 1. 策略元信息
\`\`\`
策略标识: trend_momentum_strategy (小写字母、数字和下划线)
显示名称: 趋势+动能双重确认策略
Python类名: TrendMomentumStrategy (大写驼峰)
策略类别: momentum (可选: momentum/reversal/factor/technical/ml)
策略描述: 基于EMA趋势过滤和MACD动能触发的双重确认入场策略
标签: 趋势, 动能, MACD, EMA, 双重确认
\`\`\`

### 2. 完整Python代码
生成完整的策略代码，包括:
- ✅ 文档字符串（策略说明）
- ✅ 正确继承 BaseStrategy 基类
- ✅ 实现 __init__, calculate_scores, generate_signals 三个方法
- ✅ 包含完整的参数配置
- ✅ 添加错误处理（try-except）
- ✅ 代码注释清晰
- ✅ 符合PEP 8编码规范

## 特别注意

1. **数据结构理解**:
   - prices: DataFrame, index=日期, columns=股票代码, values=收盘价
   - 访问单只股票: \`prices[stock_code]\`
   - 访问某日所有股票: \`prices.loc[date]\`

2. **信号值规范**:
   - 1 = 买入信号
   - 0 = 持有/无操作
   - -1 = 卖出信号

3. **配置参数访问（非常重要！）**:
   - ⚠️ 策略自定义参数必须使用 \`self.config.custom_params.get('param_name', default_value)\`
   - ❌ 错误写法：\`self.config.get('bb_window', 20)\` （会报错！）
   - ✅ 正确写法：\`self.config.custom_params.get('bb_window', 20)\`
   - 通用参数可直接访问：\`self.config.top_n\`, \`self.config.holding_period\`

4. **信号赋值正确方式（非常重要！）**:
   - 不要直接使用布尔Series作为loc索引
   - 正确步骤：
     \`\`\`python
     # 1. 获取满足条件的日期索引
     buy_dates = buy_condition[buy_condition].index

     # 2. 与信号DataFrame的索引求交集
     valid_dates = signals.index.intersection(buy_dates)

     # 3. 赋值
     signals.loc[valid_dates, stock] = 1
     \`\`\`
   - ❌ 错误写法：\`signals.loc[buy_cond, stock] = 1\` （可能索引错误！）
   - ✅ 正确写法：见上方示例

5. **数据验证**:
   - 计算指标后验证：\`if pd.isna(indicator): continue\`
   - 检查数据长度：\`if len(data) < min_length: continue\`
   - 避免除零：使用 \`(denominator + 1e-9)\`

6. **性能考虑**:
   - 单只股票计算失败不应影响其他股票
   - 使用 try-except 包裹每只股票的处理逻辑
   - 优先使用向量化操作

---

**现在请根据以上模板和我的策略需求，生成完整的策略代码和元信息。**`)

  // 生成最终提示词（替换占位符）
  const generateFinalPrompt = () => {
    return promptTemplate.replace('{STRATEGY_REQUIREMENT}', strategyRequirement)
  }

  const copyToClipboard = async () => {
    const finalPrompt = generateFinalPrompt()

    try {
      await navigator.clipboard.writeText(finalPrompt)
      setCopied(true)
      toast({
        title: '复制成功',
        description: '提示词已复制到剪贴板，现在可以粘贴到AI对话中'
      })
      setTimeout(() => setCopied(false), 2000)

      if (onPromptGenerated) {
        onPromptGenerated(finalPrompt)
      }
    } catch (error) {
      toast({
        title: '复制失败',
        description: '请手动复制提示词',
        variant: 'destructive'
      })
    }
  }

  return (
    <Card className="border-2 border-primary/20 bg-gradient-to-br from-primary/5 to-primary/10">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            <CardTitle>AI 策略生成助手</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="default"
              size="sm"
              onClick={copyToClipboard}
              className="gap-2"
            >
              {copied ? (
                <>
                  <CheckCircle className="h-4 w-4" />
                  已复制
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4" />
                  复制提示词
                </>
              )}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? (
                <>
                  <ChevronUp className="h-4 w-4 mr-1" />
                  收起
                </>
              ) : (
                <>
                  <ChevronDown className="h-4 w-4 mr-1" />
                  展开
                </>
              )}
            </Button>
          </div>
        </div>
        <CardDescription>
          使用AI（Claude、ChatGPT）生成完整的策略代码。填写策略需求后，复制提示词到AI对话即可获得代码和元信息。
        </CardDescription>
      </CardHeader>

      {isExpanded && (
        <CardContent className="space-y-4">
          {/* 使用步骤 */}
          <Alert>
            <Lightbulb className="h-4 w-4" />
            <AlertTitle>使用步骤</AlertTitle>
            <AlertDescription className="text-sm space-y-2 mt-2">
              <ol className="list-decimal list-inside space-y-1">
                <li>在&ldquo;策略需求&rdquo;标签页中填写你的策略需求</li>
                <li>（可选）在&ldquo;提示词模板&rdquo;标签页中查看或修改模板</li>
                <li>点击右上角&ldquo;复制提示词&rdquo;按钮</li>
                <li>打开AI工具（推荐 Claude 3.5 Sonnet 或 ChatGPT-4）</li>
                <li>粘贴提示词，等待AI生成代码和元信息</li>
                <li>复制AI返回的元信息，填写到下方表单中</li>
                <li>复制AI生成的代码，粘贴到代码编辑器中</li>
                <li>点击&ldquo;验证代码&rdquo;并保存</li>
              </ol>
            </AlertDescription>
          </Alert>

          {/* Tabs: 策略需求 vs 提示词模板 */}
          <Tabs defaultValue="requirement" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="requirement">
                <Wand2 className="h-4 w-4 mr-2" />
                策略需求
              </TabsTrigger>
              <TabsTrigger value="template">
                <FileText className="h-4 w-4 mr-2" />
                提示词模板
              </TabsTrigger>
            </TabsList>

            {/* 策略需求标签页 */}
            <TabsContent value="requirement" className="space-y-3">
              <div className="space-y-2">
                <Label htmlFor="strategy-requirement" className="text-base font-semibold">
                  策略需求描述 *
                </Label>
                <Textarea
                  id="strategy-requirement"
                  value={strategyRequirement}
                  onChange={(e) => setStrategyRequirement(e.target.value)}
                  placeholder="详细描述你的策略需求..."
                  className="min-h-[400px] font-mono text-sm"
                />
                <p className="text-xs text-muted-foreground">
                  💡 提示：描述越详细，AI生成的代码质量越高。包含策略类型、核心逻辑、技术指标、参数配置、风险控制等信息。
                </p>
              </div>

              {/* 策略描述示例 */}
              <div className="pt-4 border-t space-y-3">
                <p className="text-sm font-medium">📝 策略描述示例:</p>
                <div className="bg-muted/50 rounded-lg p-4 space-y-3 text-xs">
                  <div>
                    <p className="font-medium text-green-600 dark:text-green-400 mb-1">✅ 好的描述（详细清晰）:</p>
                    <pre className="text-muted-foreground whitespace-pre-wrap">
{`**策略类型**: 趋势跟踪策略

**核心逻辑**:
- 使用EMA(20,60,120)定义趋势，MACD(12,26,9)捕捉动能
- 买入条件：股价>EMA120 且 EMA20>EMA60 且 MACD零轴上方金叉
- 卖出条件：MACD死叉 或 股价跌破EMA60

**技术指标**: EMA, MACD

**参数配置**: ema_short:20, ema_mid:60, ema_long:120

**风险控制**: 成交量>20日均量80%, 每期选20只股票`}
                    </pre>
                  </div>
                  <div>
                    <p className="font-medium text-red-600 dark:text-red-400 mb-1">❌ 不好的描述（过于简单）:</p>
                    <pre className="text-muted-foreground">
{`使用MACD策略
均线策略
一个赚钱的策略`}
                    </pre>
                  </div>
                </div>
              </div>
            </TabsContent>

            {/* 提示词模板标签页 */}
            <TabsContent value="template" className="space-y-3">
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="prompt-template" className="text-base font-semibold">
                    完整提示词模板（可编辑）
                  </Label>
                  <p className="text-xs text-muted-foreground">
                    包含占位符: {'{STRATEGY_REQUIREMENT}'}
                  </p>
                </div>
                <Textarea
                  id="prompt-template"
                  value={promptTemplate}
                  onChange={(e) => setPromptTemplate(e.target.value)}
                  className="min-h-[500px] font-mono text-xs"
                />
                <p className="text-xs text-muted-foreground">
                  💡 提示：复制时会自动将&ldquo;{'{STRATEGY_REQUIREMENT}'}&rdquo;替换为您填写的策略需求。您也可以修改模板以适应特定需求。
                </p>
              </div>
            </TabsContent>
          </Tabs>

          {/* AI工具推荐 */}
          <div className="pt-4 border-t space-y-2">
            <p className="text-sm font-medium">🤖 推荐的AI工具:</p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="bg-primary/10 rounded-lg p-3">
                <p className="font-semibold text-primary mb-1">Claude 3.5 Sonnet ⭐⭐⭐⭐⭐</p>
                <p className="text-muted-foreground">代码质量高，理解准确，推荐首选</p>
              </div>
              <div className="bg-muted/50 rounded-lg p-3">
                <p className="font-semibold mb-1">ChatGPT-4 ⭐⭐⭐⭐</p>
                <p className="text-muted-foreground">生成速度快，代码规范</p>
              </div>
              <div className="bg-muted/50 rounded-lg p-3">
                <p className="font-semibold mb-1">Gemini Pro ⭐⭐⭐</p>
                <p className="text-muted-foreground">免费额度高</p>
              </div>
              <div className="bg-muted/50 rounded-lg p-3">
                <p className="font-semibold mb-1">通义千问 / 文心一言 ⭐⭐⭐</p>
                <p className="text-muted-foreground">中文理解好</p>
              </div>
            </div>
          </div>

          {/* 注意事项 */}
          <div className="pt-4 border-t">
            <Alert variant="default" className="bg-yellow-50 dark:bg-yellow-900/10 border-yellow-200">
              <AlertTitle className="text-sm">⚠️ 重要提示</AlertTitle>
              <AlertDescription className="text-xs space-y-1 mt-2">
                <p>• AI会同时生成<strong>策略元信息</strong>和<strong>代码</strong>，请分别复制到对应位置</p>
                <p>• 确保填写的<strong>Python类名</strong>与代码中的类名完全一致</p>
                <p>• 生成代码后务必点击<strong>&ldquo;验证代码&rdquo;</strong>按钮检查</p>
                <p>• 如果验证失败，可以将错误信息反馈给AI进行修正</p>
              </AlertDescription>
            </Alert>
          </div>
        </CardContent>
      )}
    </Card>
  )
}
