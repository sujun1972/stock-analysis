"""
AI策略生成服务

支持多个AI提供商（DeepSeek、Gemini、OpenAI等）通过 LangChain 统一接口调用 LLM。

主要功能：
- 多AI提供商支持（DeepSeek、Gemini、OpenAI），通过 LangChain ChatModel
- 统一的客户端接口（LangChainClient）
- 自动解析生成的策略代码和元信息
- 完善的错误处理和日志记录

作者: Backend Team
创建日期: 2026-03-01
更新日期: 2026-04-15（迁移至 LangChain）
"""

import json
import re
import time
from typing import Dict, Any, Optional, Tuple
from loguru import logger

from app.core.config import settings
from app.core.exceptions import AIServiceError
from app.services.langchain_client import LangChainClient

# 策略类型 → 数据库 business_type 映射
_STRATEGY_TYPE_BUSINESS_TYPE = {
    "entry": "strategy_generation_entry",
    "exit": "strategy_generation_exit",
    "stock_selection": "strategy_generation_stock_selection",
}


class AIStrategyService:
    """AI策略生成服务"""

    # 默认提示词模板
    DEFAULT_PROMPT_TEMPLATE = """# 量化交易策略代码生成任务

## 任务目标
请为我生成一个完整的Python量化交易策略代码，要求能够通过系统验证并可直接使用。

## 代码框架要求

{STRATEGY_TYPE_FRAMEWORK}

### 1. 必须的导入语句
```python
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
from loguru import logger
from core.strategies.base_strategy import BaseStrategy
```

### 2. 必须实现的三个方法

#### 2.1 初始化方法 (__init__)
```python
def __init__(self, name: str = "strategy_name", config: Dict[str, Any] = None):
    default_config = {
        'name': 'StrategyName',
        'description': '策略描述',
        'top_n': 20,
        'holding_period': 5,
        'rebalance_freq': 'W',
        # 添加策略特有参数
    }
    if config:
        default_config.update(config)
    super().__init__(name, default_config)
```

#### 2.2 计算评分方法 (calculate_scores) - 必须实现
```python
def calculate_scores(self, prices: pd.DataFrame, features: Optional[pd.DataFrame] = None, date: Optional[pd.Timestamp] = None) -> pd.Series:
    # 实现评分逻辑
    pass
```

#### 2.3 生成信号方法 (generate_signals) - 必须实现
```python
def generate_signals(self, prices: pd.DataFrame, features: Optional[pd.DataFrame] = None, **kwargs) -> pd.DataFrame:
    # 实现信号生成逻辑
    pass
```

## 我的策略需求

{STRATEGY_REQUIREMENT}

## 输出要求

请按照以下格式输出：

### 1. 策略元信息（使用JSON格式）
```json
{
  "strategy_id": "trend_momentum_strategy",
  "display_name": "趋势+动能双重确认策略",
  "class_name": "TrendMomentumStrategy",
  "category": "momentum",
  "description": "基于EMA趋势过滤和MACD动能触发的双重确认入场策略",
  "tags": ["趋势", "动能", "MACD", "EMA"]
}
```

**重要**: category字段必须使用以下预定义类别之一，不要自创类别：
- `momentum` - 动量策略
- `reversal` - 反转策略
- `mean_reversion` - 均值回归策略
- `factor` - 因子策略
- `ml` - 机器学习策略
- `arbitrage` - 套利策略
- `hybrid` - 混合策略
- `trend_following` - 趋势跟踪策略
- `breakout` - 突破策略
- `statistical` - 统计套利策略

### 2. 完整Python代码
生成完整的策略代码，包括:
- ✅ 正确继承 BaseStrategy 基类
- ✅ 实现所有必需方法
- ✅ 包含完整的参数配置
- ✅ 添加错误处理（try-except）
- ✅ 代码注释清晰

## 特别注意

1. **配置参数访问**:
   - ⚠️ 策略自定义参数必须使用 `self.config.custom_params.get('param_name', default_value)`
   - ✅ 正确写法：`self.config.custom_params.get('bb_window', 20)`

2. **信号赋值正确方式**:
   ```python
   # 1. 获取满足条件的日期索引
   buy_dates = buy_condition[buy_condition].index
   # 2. 与信号DataFrame的索引求交集
   valid_dates = signals.index.intersection(buy_dates)
   # 3. 赋值
   signals.loc[valid_dates, stock] = 1
   ```

3. **数据验证**:
   - 计算指标后验证：`if pd.isna(indicator): continue`
   - 检查数据长度：`if len(data) < min_length: continue`
   - 避免除零：使用 `(denominator + 1e-9)`

4. **日志记录** (重要):
   - ✅ 必须使用全局 `logger` 变量，例如：`logger.info("message")`
   - ❌ 禁止使用 `self.logger`（会导致安全验证失败）
   - 允许的 logger 方法：`debug`, `info`, `warning`, `error`, `critical`, `success`
   - 示例：
     ```python
     logger.info(f"策略参数: {self.config.custom_params}")
     logger.warning("数据不足，跳过计算")
     logger.error(f"计算失败: {str(e)}")
     ```

5. **允许使用的库和方法** (采用宽松策略):

   **Pandas 库** - ✅ 几乎所有方法都允许:
   - 核心类: `pd.Series()`, `pd.DataFrame()`, `pd.Index()`, `pd.DatetimeIndex()`
   - 时间处理: `pd.to_datetime()`, `pd.date_range()`, `pd.period_range()`
   - 所有 DataFrame/Series 方法: `loc`, `iloc`, `fillna`, `rolling`, `groupby`, `merge` 等
   - 示例:
     ```python
     df = pd.DataFrame(data)
     series = pd.Series(values)
     result = df.groupby('category').mean()
     ```

   **NumPy 库** - ✅ 几乎所有方法都允许:
   - 数组创建: `np.array()`, `np.zeros()`, `np.ones()`, `np.arange()`
   - 数学函数: `np.mean()`, `np.std()`, `np.sqrt()`, `np.exp()`, `np.log()`
   - 逻辑函数: `np.where()`, `np.isnan()`, `np.all()`, `np.any()`

   **BaseStrategy 方法** - ✅ 允许所有:
   - 基类方法: `self.filter_stocks()`, `self.validate_signals()`, `self.get_position_weights()`
   - 配置访问: `self.config.custom_params.get()`
   - 自定义私有方法: 允许定义和调用任何 `self._xxx()` 方法

6. **禁止使用的内容**:
   - ❌ 文件操作: `open`, `read`, `write`
   - ❌ 系统调用: `os.system`, `subprocess`, `exec`, `eval`
   - ❌ 网络请求: `requests`, `urllib`, `socket`
   - ❌ 不安全的属性: `__dict__`, `__class__`, `__globals__`
   - ❌ 使用 `self.logger`（必须用全局 `logger`）

**现在请根据以上模板和我的策略需求，生成完整的策略代码和元信息。**"""

    def create_client(self, provider: str, config: Dict[str, Any]) -> LangChainClient:
        """创建 LangChain 统一 AI 客户端"""
        return LangChainClient(provider=provider, config=config)

    def get_provider_config(self, provider: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
        """从 ai_provider_configs 表获取指定提供商的配置；找不到时回退到 DEEPSEEK_API_KEY 环境变量。"""
        _DEFAULT = {
            "provider": "deepseek",
            "api_key": settings.DEEPSEEK_API_KEY,
            "api_base_url": "https://api.deepseek.com/v1",
            "model_name": model or "deepseek-chat",
            "max_tokens": 4000,
            "temperature": 0.7,
            "timeout": 60,
        }
        try:
            import psycopg2
            conn = psycopg2.connect(**settings.db_config_dict_dbname())
            cur = conn.cursor()
            if provider:
                cur.execute(
                    "SELECT provider, api_key, api_base_url, model_name, max_tokens, temperature, timeout "
                    "FROM ai_provider_configs WHERE provider = %s AND is_active = true LIMIT 1",
                    (provider,),
                )
            else:
                cur.execute(
                    "SELECT provider, api_key, api_base_url, model_name, max_tokens, temperature, timeout "
                    "FROM ai_provider_configs WHERE is_active = true AND is_default = true LIMIT 1"
                )
            row = cur.fetchone()
            cur.close()
            conn.close()
            if not row:
                logger.warning(f"未找到 AI 提供商配置 (provider={provider})，使用默认配置")
                return _DEFAULT
            return {
                "provider": row[0],
                "api_key": row[1],
                "api_base_url": row[2],
                "model_name": model or row[3],
                "max_tokens": row[4],
                "temperature": float(row[5]),
                "timeout": row[6],
            }
        except Exception as e:
            logger.error(f"获取 AI 提供商配置失败: {e}")
            return _DEFAULT

    def _load_db_prompt(self, strategy_type: str) -> Optional[str]:
        """从数据库按策略类型加载 user_prompt_template，失败时返回 None"""
        try:
            from app.core.database import SessionLocal
            from app.services.prompt_template_service import get_prompt_template_service

            business_type = _STRATEGY_TYPE_BUSINESS_TYPE.get(strategy_type)
            if not business_type:
                return None

            db = SessionLocal()
            try:
                svc = get_prompt_template_service()
                template = svc.get_active_template(db, business_type)
                return template.user_prompt_template
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"从数据库加载 prompt 模板失败，将降级使用硬编码: {e}")
            return None

    # 各策略类型的接口框架片段，注入到 prompt 的"代码框架要求"节（数据库模板缺失时的降级备用）
    STRATEGY_TYPE_FRAMEWORKS = {
        "entry": """\
### 入场策略接口要求
本次生成的是**入场策略**（决定何时买入），必须实现以下方法：
- `calculate_scores(prices, features, date) -> pd.Series`：对每只股票打分，分数越高越优先买入
- `generate_signals(prices, features, **kwargs) -> pd.DataFrame`：返回信号 DataFrame，列为股票代码，行为日期，值 1=买入 0=持有 -1=卖出

**信号语义**：1 表示产生买入信号，策略框架将据此建仓。""",

        "exit": """\
### 离场策略接口要求
本次生成的是**离场策略**（决定何时卖出/止损/止盈），必须实现以下方法：
- `calculate_scores(prices, features, date) -> pd.Series`：对持仓股票打分，分数越低越优先卖出
- `generate_signals(prices, features, **kwargs) -> pd.DataFrame`：返回信号 DataFrame，列为股票代码，行为日期，值 -1=卖出 0=继续持有

**信号语义**：-1 表示产生卖出/止损信号，策略框架将据此平仓。
**典型实现**：固定止损比例、trailing stop、技术指标死叉、持仓周期到期等。""",

        "stock_selection": """\
### 选股策略接口要求
本次生成的是**选股策略**（从全市场筛选目标股票池），必须实现以下方法：
- `calculate_scores(prices, features, date) -> pd.Series`：对每只股票打分，分数越高越入选
- `generate_signals(prices, features, **kwargs) -> pd.DataFrame`：返回信号 DataFrame，列为股票代码，行为日期，值 1=入选 0=不入选

**信号语义**：1 表示该股票进入候选股票池，后续由入场策略决定具体买入时机。
**典型实现**：因子选股（动量、估值、质量）、量价筛选、财务指标排名、机器学习打分等。""",
    }

    async def generate_strategy(
        self,
        strategy_requirement: str,
        provider_config: Dict[str, Any],
        strategy_type: str = "entry",
        custom_prompt_template: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成策略代码

        Args:
            strategy_requirement: 策略需求描述
            provider_config: AI提供商配置
            strategy_type: 策略类型（entry / exit / stock_selection）
            custom_prompt_template: 自定义提示词模板（可选）

        Returns:
            {
                "strategy_code": "...",
                "strategy_metadata": {...},
                "tokens_used": 1000,
                "generation_time": 5.2
            }
        """
        start_time = time.time()

        # 构建提示词：优先使用 custom_prompt_template，其次从数据库按策略类型取，最后降级到硬编码
        if custom_prompt_template:
            prompt = custom_prompt_template.replace("{STRATEGY_REQUIREMENT}", strategy_requirement)
        else:
            db_template_text = self._load_db_prompt(strategy_type)
            if db_template_text:
                # 数据库模板使用 Jinja2 风格 {{ strategy_requirement }}，直接替换
                prompt = db_template_text.replace("{{ strategy_requirement }}", strategy_requirement)
                logger.info(f"使用数据库模板生成策略 (strategy_type={strategy_type})")
            else:
                # 降级：硬编码模板 + STRATEGY_TYPE_FRAMEWORKS 注入
                type_framework = self.STRATEGY_TYPE_FRAMEWORKS.get(
                    strategy_type, self.STRATEGY_TYPE_FRAMEWORKS["entry"]
                )
                prompt = (
                    self.DEFAULT_PROMPT_TEMPLATE
                    .replace("{STRATEGY_REQUIREMENT}", strategy_requirement)
                    .replace("{STRATEGY_TYPE_FRAMEWORK}", type_framework)
                )
                logger.warning(f"数据库模板未找到，降级使用硬编码模板 (strategy_type={strategy_type})")

        # 创建客户端
        provider = provider_config.get("provider", "deepseek")
        client = self.create_client(provider, provider_config)

        # 调用AI生成
        logger.info(f"使用 {provider} 生成策略，需求长度: {len(strategy_requirement)}")
        content, tokens_used = await client.generate_strategy(prompt)

        generation_time = time.time() - start_time

        # 解析返回内容
        strategy_code, strategy_metadata = self._parse_ai_response(content)

        logger.info(f"策略生成完成，耗时: {generation_time:.2f}s, tokens: {tokens_used}")

        return {
            "strategy_code": strategy_code,
            "strategy_metadata": strategy_metadata,
            "tokens_used": tokens_used,
            "generation_time": round(generation_time, 2)
        }

    def _parse_ai_response(self, content: str) -> Tuple[Optional[str], Optional[Dict]]:
        """
        解析AI返回的内容，提取策略代码和元信息

        Args:
            content: AI返回的原始内容

        Returns:
            (策略代码, 策略元信息)
        """
        strategy_code = None
        strategy_metadata = None

        # 提取JSON元信息
        json_pattern = r'```json\s*(\{[\s\S]*?\})\s*```'
        json_matches = re.findall(json_pattern, content)
        if json_matches:
            try:
                strategy_metadata = json.loads(json_matches[0])
                logger.info(f"成功解析策略元信息: {strategy_metadata.get('strategy_id', 'unknown')}")
            except json.JSONDecodeError as e:
                logger.warning(f"解析JSON元信息失败: {e}")

        # 提取Python代码
        python_pattern = r'```python\s*([\s\S]*?)\s*```'
        python_matches = re.findall(python_pattern, content)
        if python_matches:
            # 取最长的代码块（通常是完整策略代码）
            strategy_code = max(python_matches, key=len)
            logger.info(f"成功提取策略代码，长度: {len(strategy_code)}")
        else:
            # 如果没有代码块标记，尝试查找class定义
            class_pattern = r'(class\s+\w+.*?:[\s\S]*?)(?=\n\nclass\s+|\n\n#\s+|$)'
            class_matches = re.findall(class_pattern, content)
            if class_matches:
                strategy_code = max(class_matches, key=len)
                logger.info(f"从文本中提取到类定义，长度: {len(strategy_code)}")

        return strategy_code, strategy_metadata


# 全局实例
ai_strategy_service = AIStrategyService()
