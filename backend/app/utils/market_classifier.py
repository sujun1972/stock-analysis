"""
市场分类工具

根据股票代码自动判断市场类型
"""

from typing import Callable, Dict

import pandas as pd
from loguru import logger


class MarketClassifier:
    """
    市场分类工具类

    根据股票代码前缀判断市场类型：
    - 上海主板: 60xxxx
    - 科创板: 688xxx
    - 深圳主板: 000xxx
    - 创业板: 300xxx
    - 北交所: 8xxxxx, 4xxxxx
    - 其他: 不匹配任何规则

    Examples:
        >>> classifier = MarketClassifier()
        >>> market = classifier.get_market("000001")
        >>> print(market)  # "深圳主板"
        >>>
        >>> df = pd.DataFrame({'code': ['000001', '600000', '300001']})
        >>> df = classifier.classify(df)
        >>> print(df['market'].tolist())  # ['深圳主板', '上海主板', '创业板']
    """

    # 市场分类规则（按优先级排序）
    MARKET_RULES: Dict[str, Callable[[str], bool]] = {
        "科创板": lambda x: x.startswith("688"),
        "上海主板": lambda x: x.startswith("60"),
        "创业板": lambda x: x.startswith("300"),
        "深圳主板": lambda x: x.startswith("000"),
        "北交所": lambda x: x.startswith(("8", "4")),
    }

    @classmethod
    def get_market(cls, code: str) -> str:
        """
        根据股票代码获取市场类型

        Args:
            code: 股票代码（如 '000001', '600000'）

        Returns:
            市场类型字符串

        Examples:
            >>> MarketClassifier.get_market("000001")
            '深圳主板'
            >>> MarketClassifier.get_market("688001")
            '科创板'
            >>> MarketClassifier.get_market("999999")
            '其他'
        """
        if not code or not isinstance(code, str):
            logger.warning(f"无效的股票代码: {code}")
            return "其他"

        # 按优先级匹配规则
        for market, rule in cls.MARKET_RULES.items():
            try:
                if rule(code):
                    return market
            except Exception as e:
                logger.error(f"市场分类规则匹配失败 (code={code}, market={market}): {e}")
                continue

        return "其他"

    @classmethod
    def classify(cls, df: pd.DataFrame, code_column: str = "code", target_column: str = "market") -> pd.DataFrame:
        """
        为 DataFrame 添加市场分类列

        Args:
            df: 包含股票代码的 DataFrame
            code_column: 股票代码列名（默认 'code'）
            target_column: 目标市场列名（默认 'market'）

        Returns:
            添加了市场分类列的 DataFrame

        Raises:
            ValueError: DataFrame 缺少股票代码列

        Examples:
            >>> df = pd.DataFrame({'code': ['000001', '600000', '300001'], 'name': ['平安银行', '浦发银行', '特锐德']})
            >>> df = MarketClassifier.classify(df)
            >>> print(df[['code', 'market']])
                  code  market
            0  000001  深圳主板
            1  600000  上海主板
            2  300001    创业板
        """
        # 验证输入
        if code_column not in df.columns:
            raise ValueError(
                f"DataFrame 缺少股票代码列: '{code_column}'\n"
                f"当前列: {', '.join(df.columns)}"
            )

        if df.empty:
            logger.warning("DataFrame 为空，跳过市场分类")
            df[target_column] = None
            return df

        # 应用分类规则
        try:
            df[target_column] = df[code_column].apply(cls.get_market)
            logger.debug(f"完成市场分类: {len(df)} 条记录")
            return df

        except Exception as e:
            logger.error(f"市场分类失败: {e}")
            raise

    @classmethod
    def get_market_summary(cls, df: pd.DataFrame, code_column: str = "code") -> Dict[str, int]:
        """
        统计各市场的股票数量

        Args:
            df: 包含股票代码的 DataFrame
            code_column: 股票代码列名（默认 'code'）

        Returns:
            各市场股票数量字典 {'上海主板': 100, '深圳主板': 200, ...}

        Examples:
            >>> df = pd.DataFrame({'code': ['000001', '600000', '300001']})
            >>> summary = MarketClassifier.get_market_summary(df)
            >>> print(summary)
            {'深圳主板': 1, '上海主板': 1, '创业板': 1}
        """
        if code_column not in df.columns:
            raise ValueError(f"DataFrame 缺少股票代码列: '{code_column}'")

        if df.empty:
            return {}

        # 临时分类
        markets = df[code_column].apply(cls.get_market)
        summary = markets.value_counts().to_dict()

        logger.debug(f"市场分布: {summary}")
        return summary

    @classmethod
    def validate_code(cls, code: str) -> bool:
        """
        验证股票代码是否符合市场规则

        Args:
            code: 股票代码

        Returns:
            是否为有效的A股代码

        Examples:
            >>> MarketClassifier.validate_code("000001")
            True
            >>> MarketClassifier.validate_code("999999")
            False
        """
        if not code or not isinstance(code, str):
            return False

        # 检查是否匹配任何市场规则（排除"其他"）
        market = cls.get_market(code)
        return market != "其他"

    @classmethod
    def filter_by_market(cls, df: pd.DataFrame, market: str, code_column: str = "code") -> pd.DataFrame:
        """
        按市场类型过滤 DataFrame

        Args:
            df: 包含股票代码的 DataFrame
            market: 市场类型（如 '上海主板'）
            code_column: 股票代码列名（默认 'code'）

        Returns:
            过滤后的 DataFrame

        Examples:
            >>> df = pd.DataFrame({'code': ['000001', '600000', '300001']})
            >>> df_sh = MarketClassifier.filter_by_market(df, '上海主板')
            >>> print(len(df_sh))  # 1
        """
        if code_column not in df.columns:
            raise ValueError(f"DataFrame 缺少股票代码列: '{code_column}'")

        if market not in cls.MARKET_RULES and market != "其他":
            available = ', '.join(list(cls.MARKET_RULES.keys()) + ['其他'])
            raise ValueError(f"无效的市场类型: {market}\n可用类型: {available}")

        # 过滤
        mask = df[code_column].apply(lambda code: cls.get_market(code) == market)
        filtered = df[mask].copy()

        logger.debug(f"按市场过滤 ({market}): {len(filtered)}/{len(df)} 条记录")
        return filtered
