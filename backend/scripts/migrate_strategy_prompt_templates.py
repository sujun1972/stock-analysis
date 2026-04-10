"""
迁移 AI 策略生成提示词模板到数据库

新增三种策略类型的专属提示词模板：
  - strategy_generation_entry        入场策略
  - strategy_generation_exit         离场策略
  - strategy_generation_stock_selection 选股策略

使用方法:
    cd /Volumes/MacDriver/stock-analysis/backend
    python scripts/migrate_strategy_prompt_templates.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.services.prompt_template_service import get_prompt_template_service
from app.schemas.llm_prompt_template import PromptTemplateCreate

# ────────────────────────────────────────────────────────────
# 公共部分：所有策略类型共用的注意事项
# ────────────────────────────────────────────────────────────
COMMON_NOTES = """
## 特别注意

1. **配置参数访问**:
   - ⚠️ 策略自定义参数必须使用 `self.config.custom_params.get('param_name', default_value)`
   - ✅ 正确写法：`self.config.custom_params.get('stop_loss', 0.08)`

2. **信号赋值正确方式**:
   ```python
   # 1. 获取满足条件的日期索引
   signal_dates = condition[condition].index
   # 2. 与信号DataFrame的索引求交集
   valid_dates = signals.index.intersection(signal_dates)
   # 3. 赋值
   signals.loc[valid_dates, stock] = 1   # 或 -1
   ```

3. **数据验证**:
   - 计算指标后验证：`if pd.isna(indicator): continue`
   - 检查数据长度：`if len(data) < min_length: continue`
   - 避免除零：使用 `(denominator + 1e-9)`

4. **日志记录** (重要):
   - ✅ 必须使用全局 `logger` 变量，例如：`logger.info("message")`
   - ❌ 禁止使用 `self.logger`（会导致安全验证失败）
   - 允许的 logger 方法：`debug`, `info`, `warning`, `error`, `critical`, `success`

5. **允许使用的库**:
   - **Pandas**: `pd.Series`, `pd.DataFrame`, `rolling`, `groupby`, `merge` 等几乎全部方法
   - **NumPy**: `np.array`, `np.where`, `np.mean`, `np.std`, `np.exp`, `np.log` 等
   - **BaseStrategy 方法**: `self.filter_stocks()`, `self.validate_signals()`, `self.get_position_weights()`
   - **自定义私有方法**: 允许定义和调用任何 `self._xxx()` 方法

6. **禁止使用的内容**:
   - ❌ 文件操作: `open`, `read`, `write`
   - ❌ 系统调用: `os.system`, `subprocess`, `exec`, `eval`
   - ❌ 网络请求: `requests`, `urllib`, `socket`
   - ❌ 不安全属性: `__dict__`, `__class__`, `__globals__`
   - ❌ 使用 `self.logger`（必须用全局 `logger`）
"""

COMMON_OUTPUT_REQUIREMENTS = """
## 输出要求

请按照以下格式输出：

### 1. 策略元信息（JSON格式）
```json
{
  "strategy_id": "my_strategy_v1",
  "display_name": "策略显示名称",
  "class_name": "MyStrategyClass",
  "category": "momentum",
  "description": "策略描述",
  "tags": ["标签1", "标签2"]
}
```

**重要**: category 字段必须使用以下预定义类别之一：
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

**现在请根据以上要求和用户的策略需求，生成完整的策略代码和元信息。**
"""

REQUIRED_IMPORTS = """```python
from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
from loguru import logger
from core.strategies.base_strategy import BaseStrategy
```"""

INIT_TEMPLATE = """```python
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
```"""

SYSTEM_PROMPT = "你是一个专业的量化交易策略开发专家，精通Python和量化金融。请严格按照用户提供的模板和要求生成完整的策略代码，代码必须能够通过系统验证并可直接使用。"

# ────────────────────────────────────────────────────────────
# 入场策略 prompt
# ────────────────────────────────────────────────────────────
ENTRY_PROMPT = f"""# 量化交易策略代码生成任务（入场策略）

## 任务目标
请为我生成一个完整的Python**入场策略**代码，决定何时产生买入信号，要求能够通过系统验证并可直接使用。

## 入场策略接口要求

**入场策略**（决定何时买入），必须实现以下三个方法：

### 1. 必须的导入语句
{REQUIRED_IMPORTS}

### 2. 初始化方法 (__init__)
{INIT_TEMPLATE}

### 3. 计算评分方法 (calculate_scores) - 必须实现
```python
def calculate_scores(self, prices: pd.DataFrame, features: Optional[pd.DataFrame] = None, date: Optional[pd.Timestamp] = None) -> pd.Series:
    \"\"\"
    对每只股票打分，分数越高越优先买入。
    返回: pd.Series，索引为股票代码，值为评分（数值越大越好）
    \"\"\"
    pass
```

### 4. 生成信号方法 (generate_signals) - 必须实现
```python
def generate_signals(self, prices: pd.DataFrame, features: Optional[pd.DataFrame] = None, **kwargs) -> pd.DataFrame:
    \"\"\"
    生成买入信号。
    返回: pd.DataFrame，列为股票代码，行为日期，值含义：
      1  = 产生买入信号（策略框架将据此建仓）
      0  = 无信号，继续观望
      -1 = 减仓/卖出（可选实现）
    \"\"\"
    pass
```

**信号语义**：值为 `1` 表示产生买入信号，策略框架将据此建仓。

## 用户的策略需求

{{{{ strategy_requirement }}}}

{COMMON_OUTPUT_REQUIREMENTS}
{COMMON_NOTES}"""

# ────────────────────────────────────────────────────────────
# 离场策略 prompt
# ────────────────────────────────────────────────────────────
EXIT_PROMPT = f"""# 量化交易策略代码生成任务（离场策略）

## 任务目标
请为我生成一个完整的Python**离场策略**代码，决定何时止盈/止损/卖出，要求能够通过系统验证并可直接使用。

## 离场策略接口要求

**离场策略**（决定何时卖出/止损/止盈），必须实现以下三个方法：

### 1. 必须的导入语句
{REQUIRED_IMPORTS}

### 2. 初始化方法 (__init__)
{INIT_TEMPLATE}

### 3. 计算评分方法 (calculate_scores) - 必须实现
```python
def calculate_scores(self, prices: pd.DataFrame, features: Optional[pd.DataFrame] = None, date: Optional[pd.Timestamp] = None) -> pd.Series:
    \"\"\"
    对持仓股票打分，分数越低越优先卖出（紧急程度越高）。
    返回: pd.Series，索引为股票代码，值为评分（数值越小越需要卖出）
    \"\"\"
    pass
```

### 4. 生成信号方法 (generate_signals) - 必须实现
```python
def generate_signals(self, prices: pd.DataFrame, features: Optional[pd.DataFrame] = None, **kwargs) -> pd.DataFrame:
    \"\"\"
    生成卖出/平仓信号。
    返回: pd.DataFrame，列为股票代码，行为日期，值含义：
      -1 = 产生卖出/止损信号（策略框架将据此平仓）
       0 = 继续持有，无操作
    \"\"\"
    pass
```

**信号语义**：值为 `-1` 表示产生卖出/止损信号，策略框架将据此平仓。

**典型离场场景**：
- 固定止损比例（如跌破买入价 -8%）
- 移动止盈（Trailing Stop，涨幅超过阈值后回落触发）
- 技术指标死叉（MA死叉、MACD下穿零轴）
- 持仓周期到期（固定持有N天后强制清仓）
- 涨幅目标止盈（涨幅达到目标后分批减仓）

**注意**：`kwargs` 中通常会传入 `entry_prices`（买入价格字典），可通过 `kwargs.get('entry_prices', {{}})` 获取，用于计算涨跌幅。

## 用户的策略需求

{{{{ strategy_requirement }}}}

{COMMON_OUTPUT_REQUIREMENTS}
{COMMON_NOTES}"""

# ────────────────────────────────────────────────────────────
# 选股策略 prompt
# ────────────────────────────────────────────────────────────
STOCK_SELECTION_PROMPT = f"""# 量化交易策略代码生成任务（选股策略）

## 任务目标
请为我生成一个完整的Python**选股策略**代码，从全市场筛选目标股票池，要求能够通过系统验证并可直接使用。

## 选股策略接口要求

**选股策略**（从全市场筛选目标股票池，供入场策略进一步决策），必须实现以下三个方法：

### 1. 必须的导入语句
{REQUIRED_IMPORTS}

### 2. 初始化方法 (__init__)
{INIT_TEMPLATE}

### 3. 计算评分方法 (calculate_scores) - 必须实现
```python
def calculate_scores(self, prices: pd.DataFrame, features: Optional[pd.DataFrame] = None, date: Optional[pd.Timestamp] = None) -> pd.Series:
    \"\"\"
    对全市场每只股票打分，分数越高越优先入选股票池。
    返回: pd.Series，索引为股票代码，值为评分（数值越大越优先入选）
    \"\"\"
    pass
```

### 4. 生成信号方法 (generate_signals) - 必须实现
```python
def generate_signals(self, prices: pd.DataFrame, features: Optional[pd.DataFrame] = None, **kwargs) -> pd.DataFrame:
    \"\"\"
    生成股票入选/排除信号。
    返回: pd.DataFrame，列为股票代码，行为日期，值含义：
      1 = 股票进入候选股票池（后续由入场策略决定具体买入时机）
      0 = 不入选，排除在外
    \"\"\"
    pass
```

**信号语义**：值为 `1` 表示该股票进入候选股票池，后续由入场策略决定具体买入时机。

**典型选股场景**：
- **因子选股**：动量因子（近N日涨幅排名）、估值因子（PE/PB低位）、质量因子（ROE高）
- **量价选股**：成交量放大 + 价格突破近期高点
- **趋势过滤**：股价站上均线系统（MA20/MA60）
- **财务指标**：营收增速、净利润增速排名前X%
- **机器学习打分**：综合多因子的ML模型输出

**重要**：选股策略应专注于**筛选范围**，而非具体买卖时机。`top_n` 参数控制最终入选数量，通过 `self.config.custom_params.get('top_n', 50)` 读取。

## 用户的策略需求

{{{{ strategy_requirement }}}}

{COMMON_OUTPUT_REQUIREMENTS}
{COMMON_NOTES}"""


# ────────────────────────────────────────────────────────────
# 迁移函数
# ────────────────────────────────────────────────────────────

TEMPLATES = [
    {
        "business_type": "strategy_generation_entry",
        "template_name": "入场策略代码生成",
        "template_key": "strategy_generation_entry_v1",
        "user_prompt_template": ENTRY_PROMPT,
        "output_format": "JSON元信息（strategy_id, display_name, class_name, category, description, tags）+ 完整Python入场策略代码",
        "description": "生成入场策略Python代码，信号值 1=买入、0=观望，核心方法为 calculate_scores 和 generate_signals",
        "tags": ["入场策略", "买入信号", "量化策略"],
    },
    {
        "business_type": "strategy_generation_exit",
        "template_name": "离场策略代码生成",
        "template_key": "strategy_generation_exit_v1",
        "user_prompt_template": EXIT_PROMPT,
        "output_format": "JSON元信息（strategy_id, display_name, class_name, category, description, tags）+ 完整Python离场策略代码",
        "description": "生成离场策略Python代码，信号值 -1=卖出/止损、0=持有，支持固定止损、移动止盈、技术指标止损等",
        "tags": ["离场策略", "止损止盈", "卖出信号", "量化策略"],
    },
    {
        "business_type": "strategy_generation_stock_selection",
        "template_name": "选股策略代码生成",
        "template_key": "strategy_generation_stock_selection_v1",
        "user_prompt_template": STOCK_SELECTION_PROMPT,
        "output_format": "JSON元信息（strategy_id, display_name, class_name, category, description, tags）+ 完整Python选股策略代码",
        "description": "生成选股策略Python代码，信号值 1=入选股票池、0=排除，支持因子选股、量价选股、财务筛选等",
        "tags": ["选股策略", "股票池筛选", "因子选股", "量化策略"],
    },
]


def migrate_strategy_prompt_templates():
    db: Session = SessionLocal()
    try:
        service = get_prompt_template_service()

        for tpl in TEMPLATES:
            key = tpl["template_key"]
            existing = service.get_template_by_key(db, key)
            if existing:
                print(f"⚠️  已存在，跳过: {tpl['template_name']} (key={key}, ID={existing.id})")
                continue

            template_data = PromptTemplateCreate(
                business_type=tpl["business_type"],
                template_name=tpl["template_name"],
                template_key=key,
                system_prompt=SYSTEM_PROMPT,
                user_prompt_template=tpl["user_prompt_template"],
                output_format=tpl["output_format"],
                required_variables={"strategy_requirement": "用户的策略需求描述"},
                optional_variables={},
                version="1.0.0",
                is_active=True,
                is_default=True,
                recommended_provider="deepseek",
                recommended_model="deepseek-chat",
                recommended_temperature=0.7,
                recommended_max_tokens=8000,
                description=tpl["description"],
                changelog="初始版本",
                tags=tpl["tags"],
                created_by="system",
            )

            template = service.create_template(db, template_data)
            print(f"✅ 创建成功: {template.template_name} (business_type={template.business_type}, ID={template.id})")

    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


def main():
    print("=" * 60)
    print("AI 策略生成提示词模板迁移")
    print("=" * 60)
    print()
    migrate_strategy_prompt_templates()
    print()
    print("=" * 60)
    print("完成！访问 http://localhost:3001/settings/prompt-templates 查看")
    print("=" * 60)


if __name__ == "__main__":
    main()
