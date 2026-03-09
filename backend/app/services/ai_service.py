"""
AI策略生成服务

支持多个AI提供商（DeepSeek、Gemini、OpenAI等）通过API调用生成量化交易策略代码。

主要功能：
- 多AI提供商支持（DeepSeek、Gemini、OpenAI）
- 统一的客户端接口
- 自动解析生成的策略代码和元信息
- 完善的错误处理和日志记录

作者: Backend Team
创建日期: 2026-03-01
"""

import json
import re
import time
from typing import Dict, Any, Optional, Tuple
import httpx
from loguru import logger

from app.core.exceptions import AIServiceError


class AIProviderClient:
    """AI提供商客户端基类"""

    def __init__(self, api_key: str, api_base_url: str, model_name: str, max_tokens: int, temperature: float, timeout: int):
        self.api_key = api_key
        self.api_base_url = api_base_url
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout

    async def generate_strategy(self, prompt: str) -> Tuple[str, int]:
        """
        生成策略代码

        Args:
            prompt: 提示词

        Returns:
            (生成的内容, 使用的token数)
        """
        raise NotImplementedError


class DeepSeekClient(AIProviderClient):
    """DeepSeek AI客户端"""

    def __init__(self, api_key: str, model_name: str = "deepseek-chat", **kwargs):
        super().__init__(
            api_key=api_key,
            api_base_url=kwargs.get("api_base_url", "https://api.deepseek.com/v1"),
            model_name=model_name,
            max_tokens=kwargs.get("max_tokens", 8000),
            temperature=kwargs.get("temperature", 0.7),
            timeout=kwargs.get("timeout", 60)
        )

    async def generate_strategy(self, prompt: str) -> Tuple[str, int]:
        """使用DeepSeek API生成策略"""
        url = f"{self.api_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的量化交易策略开发专家，精通Python和量化金融。请严格按照用户提供的模板和要求生成完整的策略代码。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                result = response.json()

                content = result["choices"][0]["message"]["content"]
                tokens_used = result.get("usage", {}).get("total_tokens", 0)

                return content, tokens_used

        except httpx.HTTPStatusError as e:
            logger.error(f"DeepSeek API请求失败: {e.response.status_code} - {e.response.text}")
            raise AIServiceError(f"DeepSeek API请求失败: {e.response.status_code}")
        except KeyError as e:
            logger.error(f"DeepSeek响应格式错误，缺少字段: {str(e)}", exc_info=True)
            raise AIServiceError(f"DeepSeek响应格式错误: {str(e)}")
        except Exception as e:
            logger.error(f"DeepSeek调用异常: {str(e)}", exc_info=True)
            raise AIServiceError(f"DeepSeek调用失败: {str(e)}")


class GeminiClient(AIProviderClient):
    """Google Gemini AI客户端"""

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash", **kwargs):
        super().__init__(
            api_key=api_key,
            api_base_url=kwargs.get("api_base_url", "https://generativelanguage.googleapis.com/v1beta"),
            model_name=model_name,
            max_tokens=kwargs.get("max_tokens", 8000),
            temperature=kwargs.get("temperature", 0.7),
            timeout=kwargs.get("timeout", 60)
        )

    async def generate_strategy(self, prompt: str) -> Tuple[str, int]:
        """使用Gemini API生成策略"""
        url = f"{self.api_base_url}/models/{self.model_name}:generateContent?key={self.api_key}"
        headers = {
            "Content-Type": "application/json"
        }
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"你是一个专业的量化交易策略开发专家，精通Python和量化金融。请严格按照用户提供的模板和要求生成完整的策略代码。\n\n{prompt}"
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                result = response.json()

                content = result["candidates"][0]["content"]["parts"][0]["text"]
                tokens_used = result.get("usageMetadata", {}).get("totalTokenCount", 0)

                return content, tokens_used

        except httpx.HTTPStatusError as e:
            logger.error(f"Gemini API请求失败: {e.response.status_code} - {e.response.text}")
            raise AIServiceError(f"Gemini API请求失败: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Gemini调用异常: {str(e)}")
            raise AIServiceError(f"Gemini调用失败: {str(e)}")


class OpenAIClient(AIProviderClient):
    """OpenAI兼容客户端（支持OpenAI、Azure OpenAI等）"""

    def __init__(self, api_key: str, model_name: str = "gpt-4o", **kwargs):
        super().__init__(
            api_key=api_key,
            api_base_url=kwargs.get("api_base_url", "https://api.openai.com/v1"),
            model_name=model_name,
            max_tokens=kwargs.get("max_tokens", 8000),
            temperature=kwargs.get("temperature", 0.7),
            timeout=kwargs.get("timeout", 60)
        )

    async def generate_strategy(self, prompt: str) -> Tuple[str, int]:
        """使用OpenAI API生成策略"""
        url = f"{self.api_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的量化交易策略开发专家，精通Python和量化金融。请严格按照用户提供的模板和要求生成完整的策略代码。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                result = response.json()

                content = result["choices"][0]["message"]["content"]
                tokens_used = result.get("usage", {}).get("total_tokens", 0)

                return content, tokens_used

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI API请求失败: {e.response.status_code} - {e.response.text}")
            raise AIServiceError(f"OpenAI API请求失败: {e.response.status_code}")
        except Exception as e:
            logger.error(f"OpenAI调用异常: {str(e)}")
            raise AIServiceError(f"OpenAI调用失败: {str(e)}")


class AIStrategyService:
    """AI策略生成服务"""

    # 默认提示词模板
    DEFAULT_PROMPT_TEMPLATE = """# 量化交易策略代码生成任务

## 任务目标
请为我生成一个完整的Python量化交易策略代码，要求能够通过系统验证并可直接使用。

## 代码框架要求

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

    def __init__(self):
        self.client_factory = {
            "deepseek": DeepSeekClient,
            "gemini": GeminiClient,
            "openai": OpenAIClient,
        }

    def create_client(self, provider: str, config: Dict[str, Any]) -> AIProviderClient:
        """创建AI客户端"""
        client_class = self.client_factory.get(provider.lower())
        if not client_class:
            raise AIServiceError(f"不支持的AI提供商: {provider}")

        return client_class(**config)

    async def generate_strategy(
        self,
        strategy_requirement: str,
        provider_config: Dict[str, Any],
        custom_prompt_template: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成策略代码

        Args:
            strategy_requirement: 策略需求描述
            provider_config: AI提供商配置
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

        # 构建提示词
        prompt_template = custom_prompt_template or self.DEFAULT_PROMPT_TEMPLATE
        prompt = prompt_template.replace("{STRATEGY_REQUIREMENT}", strategy_requirement)

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
