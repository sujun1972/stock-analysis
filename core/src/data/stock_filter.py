"""
股票过滤器模块
用于过滤ST股票、停牌股票、退市股票和异常数据
"""

import pandas as pd
import numpy as np
from typing import List, Tuple, Optional

from src.config.trading_rules import (
    StockFilterRules,
    DataQualityRules,
    MarketType
)


class StockFilter:
    """股票过滤器类"""

    def __init__(self, verbose: bool = True):
        """
        初始化股票过滤器

        参数:
            verbose: 是否打印详细信息
        """
        self.verbose = verbose
        self.filter_stats = {
            'total': 0,
            'st_filtered': 0,
            'delisting_filtered': 0,
            'suspended_filtered': 0,
            'insufficient_data_filtered': 0,
            'abnormal_price_filtered': 0,
            'passed': 0
        }

    def filter_stock_list(self, stock_df: pd.DataFrame) -> pd.DataFrame:
        """
        过滤股票列表

        参数:
            stock_df: 股票列表DataFrame，需包含 'name' 列

        返回:
            过滤后的股票列表
        """
        self.filter_stats['total'] = len(stock_df)

        if 'name' not in stock_df.columns:
            raise ValueError("股票列表DataFrame必须包含'name'列")

        # 创建过滤标记列
        stock_df = stock_df.copy()
        stock_df['should_exclude'] = stock_df['name'].apply(
            lambda x: StockFilterRules.should_exclude(x)
        )

        # 统计ST股票
        self.filter_stats['st_filtered'] = stock_df['name'].apply(
            lambda x: StockFilterRules.is_st_stock(x)
        ).sum()

        # 统计退市股票
        self.filter_stats['delisting_filtered'] = stock_df['name'].apply(
            lambda x: StockFilterRules.is_delisting_stock(x)
        ).sum()

        # 过滤
        filtered_df = stock_df[~stock_df['should_exclude']].copy()
        filtered_df = filtered_df.drop('should_exclude', axis=1)

        self.filter_stats['passed'] = len(filtered_df)

        if self.verbose:
            self._print_filter_report()

        return filtered_df

    def filter_price_data(
        self,
        price_df: pd.DataFrame,
        stock_code: str,
        min_trading_days: int = DataQualityRules.MIN_TRADING_DAYS
    ) -> Tuple[bool, Optional[pd.DataFrame], str]:
        """
        过滤单只股票的价格数据

        参数:
            price_df: 价格DataFrame
            stock_code: 股票代码
            min_trading_days: 最小交易天数

        返回:
            (是否通过, 过滤后的数据, 原因)
        """
        if price_df is None or price_df.empty:
            return False, None, "数据为空"

        # 检查1: 交易天数是否足够
        if len(price_df) < min_trading_days:
            self.filter_stats['insufficient_data_filtered'] += 1
            return False, None, f"交易天数不足({len(price_df)}<{min_trading_days})"

        # 检查2: 价格是否有效
        if 'close' in price_df.columns:
            invalid_prices = ~price_df['close'].apply(
                lambda x: DataQualityRules.is_price_valid(x)
            )
            if invalid_prices.any():
                self.filter_stats['abnormal_price_filtered'] += 1
                return False, None, "价格数据异常"

        # 检查3: 成交量是否有效（检测停牌）
        if 'vol' in price_df.columns:
            # 检查连续零成交量天数
            zero_volume = (price_df['vol'] == 0)
            if self._check_consecutive_days(zero_volume, DataQualityRules.CONSECUTIVE_ZERO_VOLUME_DAYS):
                self.filter_stats['suspended_filtered'] += 1
                return False, None, f"连续{DataQualityRules.CONSECUTIVE_ZERO_VOLUME_DAYS}天停牌"

        # 检查4: 移除停牌日数据
        cleaned_df = self._remove_suspended_days(price_df)

        # 再次检查清洗后的数据量
        if len(cleaned_df) < min_trading_days:
            self.filter_stats['insufficient_data_filtered'] += 1
            return False, None, f"去除停牌后数据不足({len(cleaned_df)}<{min_trading_days})"

        return True, cleaned_df, "通过"

    def _remove_suspended_days(self, df: pd.DataFrame) -> pd.DataFrame:
        """移除停牌日数据（成交量为0的交易日）"""
        if 'vol' in df.columns:
            return df[df['vol'] > 0].copy()
        return df

    def _check_consecutive_days(self, boolean_series: pd.Series, threshold: int) -> bool:
        """检查是否存在连续N天的True值"""
        consecutive_count = 0
        max_consecutive = 0

        for value in boolean_series:
            if value:
                consecutive_count += 1
                max_consecutive = max(max_consecutive, consecutive_count)
            else:
                consecutive_count = 0

        return max_consecutive >= threshold

    def batch_filter_stocks(
        self,
        stock_list: List[str],
        price_data_dict: dict,
        min_trading_days: int = DataQualityRules.MIN_TRADING_DAYS
    ) -> Tuple[List[str], dict]:
        """
        批量过滤股票

        参数:
            stock_list: 股票代码列表
            price_data_dict: {股票代码: DataFrame} 字典
            min_trading_days: 最小交易天数

        返回:
            (通过的股票列表, 过滤原因字典)
        """
        passed_stocks = []
        filter_reasons = {}

        for stock_code in stock_list:
            price_df = price_data_dict.get(stock_code)

            passed, cleaned_df, reason = self.filter_price_data(
                price_df,
                stock_code,
                min_trading_days
            )

            if passed:
                passed_stocks.append(stock_code)
                # 更新为清洗后的数据
                price_data_dict[stock_code] = cleaned_df
            else:
                filter_reasons[stock_code] = reason

        self.filter_stats['passed'] = len(passed_stocks)

        if self.verbose:
            print(f"\n批量过滤完成:")
            print(f"总数: {len(stock_list)}")
            print(f"通过: {len(passed_stocks)}")
            print(f"过滤: {len(filter_reasons)}")

        return passed_stocks, filter_reasons

    def _print_filter_report(self):
        """打印过滤报告"""
        print("\n" + "="*60)
        print("股票过滤报告")
        print("="*60)
        print(f"总股票数:           {self.filter_stats['total']:>6}")
        print(f"ST股票过滤:         {self.filter_stats['st_filtered']:>6}")
        print(f"退市股票过滤:       {self.filter_stats['delisting_filtered']:>6}")
        print(f"停牌股票过滤:       {self.filter_stats['suspended_filtered']:>6}")
        print(f"数据不足过滤:       {self.filter_stats['insufficient_data_filtered']:>6}")
        print(f"价格异常过滤:       {self.filter_stats['abnormal_price_filtered']:>6}")
        print("-"*60)
        print(f"通过股票数:         {self.filter_stats['passed']:>6}")
        print(f"过滤率:             {(1 - self.filter_stats['passed'] / max(self.filter_stats['total'], 1)) * 100:.2f}%")
        print("="*60 + "\n")

    def get_stats(self) -> dict:
        """获取过滤统计信息"""
        return self.filter_stats.copy()

    def reset_stats(self):
        """重置统计信息"""
        for key in self.filter_stats:
            self.filter_stats[key] = 0


def filter_stocks_by_market(
    stock_df: pd.DataFrame,
    markets: List[str] = ['main', 'small', 'gem']
) -> pd.DataFrame:
    """
    按市场类型过滤股票

    参数:
        stock_df: 股票列表DataFrame，需包含 'market' 列
        markets: 允许的市场类型列表

    返回:
        过滤后的股票列表
    """
    if 'market' in stock_df.columns:
        # 将中文市场名称映射到英文
        market_mapping = {
            '主板': 'main',
            '中小板': 'small',
            '创业板': 'gem',
            '科创板': 'star',
            '北交所': 'bse'
        }

        stock_df['market_en'] = stock_df['market'].map(market_mapping)
        filtered_df = stock_df[stock_df['market_en'].isin(markets)].copy()
        filtered_df = filtered_df.drop('market_en', axis=1)

        return filtered_df
    else:
        print("警告: stock_df中没有'market'列，无法按市场过滤")
        return stock_df


# ==================== 使用示例 ====================

if __name__ == "__main__":
    # 示例1: 过滤股票列表
    print("示例1: 过滤股票列表")

    # 创建测试数据
    test_stocks = pd.DataFrame({
        'symbol': ['000001', '000002', '600000', '600001', '300001'],
        'name': ['平安银行', '*ST万科', '浦发银行', 'ST国华', '特锐德'],
        'market': ['主板', '主板', '主板', '主板', '创业板']
    })

    filter = StockFilter(verbose=True)
    filtered_stocks = filter.filter_stock_list(test_stocks)

    print("\n原始股票列表:")
    print(test_stocks)
    print("\n过滤后股票列表:")
    print(filtered_stocks)

    # 示例2: 过滤价格数据
    print("\n\n示例2: 过滤价格数据")

    # 创建测试价格数据（不足250天）
    test_price_df = pd.DataFrame({
        'close': np.random.uniform(10, 20, 100),
        'vol': np.random.uniform(1000000, 10000000, 100)
    })

    passed, cleaned_df, reason = filter.filter_price_data(
        test_price_df,
        '000001',
        min_trading_days=250
    )

    print(f"过滤结果: {'通过' if passed else '不通过'}")
    print(f"原因: {reason}")
