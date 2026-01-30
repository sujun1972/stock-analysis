"""
数据验证器 - 验证股票价格数据的完整性和合理性

功能：
- 验证必需字段完整性
- 价格数据合理性检查（high ≥ low, close在high-low之间）
- 时间序列连续性检查
- 数据类型验证
- 生成验证报告

作者: AI Assistant
日期: 2026-01-30
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Any, Tuple
from loguru import logger
from datetime import datetime, timedelta


class DataValidator:
    """
    数据验证器 - 全面验证股票数据质量

    验证项目：
    1. 必需字段完整性
    2. 数据类型正确性
    3. 价格逻辑关系（high ≥ close ≥ low）
    4. 时间序列连续性
    5. 数值范围合理性
    6. 缺失值统计

    用途：
    - 数据入库前验证
    - 数据质量监控
    - 数据清洗辅助
    """

    # 必需字段定义
    REQUIRED_PRICE_FIELDS = ['close']
    OPTIONAL_PRICE_FIELDS = ['open', 'high', 'low']
    OPTIONAL_VOLUME_FIELDS = ['volume', 'vol']
    OPTIONAL_AMOUNT_FIELDS = ['amount']

    def __init__(
        self,
        df: pd.DataFrame,
        required_fields: List[str] = None,
        date_column: str = None
    ):
        """
        初始化数据验证器

        参数：
            df: 待验证的DataFrame
            required_fields: 必需字段列表（None则使用默认）
            date_column: 日期列名（None则使用索引作为日期）
        """
        self.df = df.copy()
        self.date_column = date_column

        # 设置必需字段
        if required_fields is None:
            self.required_fields = self.REQUIRED_PRICE_FIELDS
        else:
            self.required_fields = required_fields

        # 验证结果存储
        self.validation_results = {
            'passed': True,
            'errors': [],
            'warnings': [],
            'stats': {}
        }

        logger.debug(
            f"初始化数据验证器: 行数={len(df)}, 列数={len(df.columns)}, "
            f"必需字段={self.required_fields}"
        )

    def validate_required_fields(self) -> bool:
        """
        验证必需字段是否存在

        返回：
            True表示通过，False表示失败
        """
        missing_fields = [
            field for field in self.required_fields
            if field not in self.df.columns
        ]

        if missing_fields:
            error_msg = f"缺少必需字段: {missing_fields}"
            logger.error(error_msg)
            self.validation_results['errors'].append(error_msg)
            self.validation_results['passed'] = False
            return False

        logger.info(f"✓ 必需字段验证通过: {self.required_fields}")
        return True

    def validate_data_types(self) -> bool:
        """
        验证数据类型正确性

        返回：
            True表示通过，False表示失败
        """
        type_errors = []

        # 验证价格列应为数值类型
        price_cols = [col for col in ['open', 'high', 'low', 'close'] if col in self.df.columns]

        for col in price_cols:
            if not pd.api.types.is_numeric_dtype(self.df[col]):
                type_errors.append(f"{col} 不是数值类型")

        # 验证成交量应为数值类型
        volume_cols = [col for col in ['volume', 'vol'] if col in self.df.columns]

        for col in volume_cols:
            if not pd.api.types.is_numeric_dtype(self.df[col]):
                type_errors.append(f"{col} 不是数值类型")

        if type_errors:
            error_msg = f"数据类型错误: {type_errors}"
            logger.error(error_msg)
            self.validation_results['errors'].append(error_msg)
            self.validation_results['passed'] = False
            return False

        logger.info("✓ 数据类型验证通过")
        return True

    def validate_price_logic(self) -> Tuple[bool, Dict[str, int]]:
        """
        验证价格逻辑关系

        规则：
        1. high ≥ low
        2. high ≥ close ≥ low
        3. high ≥ open ≥ low (如果有open)
        4. 价格 > 0

        返回：
            (是否通过, 错误统计字典)
        """
        has_ohlc = all(col in self.df.columns for col in ['open', 'high', 'low', 'close'])

        error_stats = {
            'high_less_than_low': 0,
            'close_out_of_range': 0,
            'open_out_of_range': 0,
            'negative_price': 0
        }

        # 检查 high ≥ low
        if 'high' in self.df.columns and 'low' in self.df.columns:
            invalid = self.df['high'] < self.df['low']
            error_stats['high_less_than_low'] = invalid.sum()

            if invalid.any():
                warning_msg = f"发现 {invalid.sum()} 条记录的high < low"
                logger.warning(warning_msg)
                self.validation_results['warnings'].append(warning_msg)

        # 检查 close 在 [low, high] 范围内
        if has_ohlc:
            invalid_close = (self.df['close'] < self.df['low']) | (self.df['close'] > self.df['high'])
            error_stats['close_out_of_range'] = invalid_close.sum()

            if invalid_close.any():
                warning_msg = f"发现 {invalid_close.sum()} 条记录的close不在[low, high]范围内"
                logger.warning(warning_msg)
                self.validation_results['warnings'].append(warning_msg)

        # 检查 open 在 [low, high] 范围内
        if has_ohlc:
            invalid_open = (self.df['open'] < self.df['low']) | (self.df['open'] > self.df['high'])
            error_stats['open_out_of_range'] = invalid_open.sum()

            if invalid_open.any():
                warning_msg = f"发现 {invalid_open.sum()} 条记录的open不在[low, high]范围内"
                logger.warning(warning_msg)
                self.validation_results['warnings'].append(warning_msg)

        # 检查价格 > 0
        price_cols = [col for col in ['open', 'high', 'low', 'close'] if col in self.df.columns]
        for col in price_cols:
            negative = self.df[col] <= 0
            negative_count = negative.sum()

            if negative_count > 0:
                error_stats['negative_price'] += negative_count
                warning_msg = f"发现 {negative_count} 条记录的{col} ≤ 0"
                logger.warning(warning_msg)
                self.validation_results['warnings'].append(warning_msg)

        # 判断是否通过
        total_errors = sum(error_stats.values())
        passed = total_errors == 0

        if passed:
            logger.info("✓ 价格逻辑验证通过")
        else:
            logger.warning(f"⚠ 价格逻辑验证发现 {total_errors} 个问题")

        self.validation_results['stats']['price_logic_errors'] = error_stats

        return passed, error_stats

    def validate_date_continuity(
        self,
        allow_gaps: bool = True,
        max_gap_days: int = 10
    ) -> Tuple[bool, List[Tuple[datetime, datetime, int]]]:
        """
        验证日期序列连续性

        参数：
            allow_gaps: 是否允许日期间隔（考虑周末和节假日）
            max_gap_days: 最大允许间隔天数

        返回：
            (是否通过, 间隔列表)
        """
        # 获取日期索引
        if self.date_column:
            dates = pd.to_datetime(self.df[self.date_column])
        else:
            if not isinstance(self.df.index, pd.DatetimeIndex):
                warning_msg = "索引不是DatetimeIndex，跳过日期连续性检查"
                logger.warning(warning_msg)
                self.validation_results['warnings'].append(warning_msg)
                return True, []
            dates = self.df.index

        # 检查日期排序
        if not dates.is_monotonic_increasing:
            error_msg = "日期序列未按升序排列"
            logger.error(error_msg)
            self.validation_results['errors'].append(error_msg)
            self.validation_results['passed'] = False
            return False, []

        # 检查日期间隔
        gaps = []
        date_diffs = dates.to_series().diff()

        for i, diff in enumerate(date_diffs[1:], start=1):
            gap_days = diff.days

            if gap_days > max_gap_days:
                start_date = dates[i - 1]
                end_date = dates[i]
                gaps.append((start_date, end_date, gap_days))

        if gaps:
            warning_msg = f"发现 {len(gaps)} 个日期间隔 > {max_gap_days}天"
            logger.warning(warning_msg)
            self.validation_results['warnings'].append(warning_msg)

            if not allow_gaps:
                self.validation_results['passed'] = False
                return False, gaps

        logger.info(f"✓ 日期连续性验证通过 (间隔数={len(gaps)})")
        self.validation_results['stats']['date_gaps'] = gaps

        return True, gaps

    def validate_value_ranges(
        self,
        price_min: float = 0.01,
        price_max: float = 10000.0,
        volume_min: float = 0,
        volume_max: float = 1e12
    ) -> Tuple[bool, Dict[str, int]]:
        """
        验证数值范围合理性

        参数：
            price_min: 最小价格（默认0.01元）
            price_max: 最大价格（默认10000元）
            volume_min: 最小成交量
            volume_max: 最大成交量

        返回：
            (是否通过, 异常统计)
        """
        range_errors = {}

        # 验证价格范围
        price_cols = [col for col in ['open', 'high', 'low', 'close'] if col in self.df.columns]

        for col in price_cols:
            out_of_range = (self.df[col] < price_min) | (self.df[col] > price_max)
            count = out_of_range.sum()

            if count > 0:
                range_errors[f'{col}_out_of_range'] = count
                warning_msg = f"{col} 有 {count} 条记录超出合理范围 [{price_min}, {price_max}]"
                logger.warning(warning_msg)
                self.validation_results['warnings'].append(warning_msg)

        # 验证成交量范围
        volume_cols = [col for col in ['volume', 'vol'] if col in self.df.columns]

        for col in volume_cols:
            out_of_range = (self.df[col] < volume_min) | (self.df[col] > volume_max)
            count = out_of_range.sum()

            if count > 0:
                range_errors[f'{col}_out_of_range'] = count
                warning_msg = f"{col} 有 {count} 条记录超出合理范围 [{volume_min}, {volume_max}]"
                logger.warning(warning_msg)
                self.validation_results['warnings'].append(warning_msg)

        passed = len(range_errors) == 0

        if passed:
            logger.info("✓ 数值范围验证通过")
        else:
            logger.warning(f"⚠ 数值范围验证发现 {sum(range_errors.values())} 个问题")

        self.validation_results['stats']['value_range_errors'] = range_errors

        return passed, range_errors

    def validate_missing_values(
        self,
        max_missing_rate: float = 0.5
    ) -> Tuple[bool, Dict[str, float]]:
        """
        验证缺失值比例

        参数：
            max_missing_rate: 最大允许缺失率（默认50%）

        返回：
            (是否通过, 缺失率字典)
        """
        missing_stats = {}
        total_rows = len(self.df)

        for col in self.df.columns:
            missing_count = self.df[col].isna().sum()
            missing_rate = missing_count / total_rows

            missing_stats[col] = {
                'count': int(missing_count),
                'rate': round(missing_rate, 4)
            }

            if missing_rate > max_missing_rate:
                warning_msg = f"{col} 缺失率 {missing_rate:.2%} 超过阈值 {max_missing_rate:.2%}"
                logger.warning(warning_msg)
                self.validation_results['warnings'].append(warning_msg)

        # 判断是否通过
        high_missing_cols = [
            col for col, stats in missing_stats.items()
            if stats['rate'] > max_missing_rate
        ]

        passed = len(high_missing_cols) == 0

        if passed:
            logger.info("✓ 缺失值验证通过")
        else:
            logger.warning(f"⚠ {len(high_missing_cols)} 列缺失率过高")

        self.validation_results['stats']['missing_values'] = missing_stats

        return passed, missing_stats

    def validate_duplicates(self) -> Tuple[bool, int]:
        """
        验证是否存在重复记录

        返回：
            (是否通过, 重复记录数)
        """
        duplicate_count = self.df.duplicated().sum()

        if duplicate_count > 0:
            warning_msg = f"发现 {duplicate_count} 条重复记录"
            logger.warning(warning_msg)
            self.validation_results['warnings'].append(warning_msg)
        else:
            logger.info("✓ 无重复记录")

        self.validation_results['stats']['duplicate_records'] = int(duplicate_count)

        return duplicate_count == 0, duplicate_count

    def validate_all(
        self,
        strict_mode: bool = False,
        allow_date_gaps: bool = True,
        max_missing_rate: float = 0.5
    ) -> Dict[str, Any]:
        """
        执行全部验证检查

        参数：
            strict_mode: 严格模式（警告也视为失败）
            allow_date_gaps: 是否允许日期间隔
            max_missing_rate: 最大允许缺失率

        返回：
            完整的验证结果字典
        """
        logger.info("开始全面数据验证...")

        # 1. 必需字段
        self.validate_required_fields()

        # 2. 数据类型
        self.validate_data_types()

        # 3. 价格逻辑
        self.validate_price_logic()

        # 4. 日期连续性
        self.validate_date_continuity(allow_gaps=allow_date_gaps)

        # 5. 数值范围
        self.validate_value_ranges()

        # 6. 缺失值
        self.validate_missing_values(max_missing_rate=max_missing_rate)

        # 7. 重复记录
        self.validate_duplicates()

        # 严格模式：警告也视为失败
        if strict_mode and self.validation_results['warnings']:
            self.validation_results['passed'] = False

        # 汇总结果
        error_count = len(self.validation_results['errors'])
        warning_count = len(self.validation_results['warnings'])

        self.validation_results['summary'] = {
            'total_records': len(self.df),
            'total_columns': len(self.df.columns),
            'passed': self.validation_results['passed'],
            'error_count': error_count,
            'warning_count': warning_count,
            'strict_mode': strict_mode
        }

        if self.validation_results['passed']:
            logger.info(
                f"✓ 数据验证通过! "
                f"(错误={error_count}, 警告={warning_count})"
            )
        else:
            logger.error(
                f"✗ 数据验证失败! "
                f"(错误={error_count}, 警告={warning_count})"
            )

        return self.validation_results

    def get_validation_report(self) -> str:
        """
        生成可读的验证报告

        返回：
            格式化的验证报告字符串
        """
        if not self.validation_results.get('summary'):
            return "尚未执行验证，请先调用 validate_all()"

        report_lines = [
            "=" * 60,
            "数据验证报告",
            "=" * 60,
            ""
        ]

        # 摘要信息
        summary = self.validation_results['summary']
        report_lines.extend([
            f"总记录数: {summary['total_records']}",
            f"总列数: {summary['total_columns']}",
            f"验证结果: {'✓ 通过' if summary['passed'] else '✗ 失败'}",
            f"错误数: {summary['error_count']}",
            f"警告数: {summary['warning_count']}",
            ""
        ])

        # 错误信息
        if self.validation_results['errors']:
            report_lines.append("错误列表:")
            for i, error in enumerate(self.validation_results['errors'], 1):
                report_lines.append(f"  {i}. {error}")
            report_lines.append("")

        # 警告信息
        if self.validation_results['warnings']:
            report_lines.append("警告列表:")
            for i, warning in enumerate(self.validation_results['warnings'], 1):
                report_lines.append(f"  {i}. {warning}")
            report_lines.append("")

        # 统计信息
        if self.validation_results['stats']:
            report_lines.append("详细统计:")

            # 缺失值
            if 'missing_values' in self.validation_results['stats']:
                report_lines.append("\n  缺失值统计:")
                missing = self.validation_results['stats']['missing_values']
                for col, stats in missing.items():
                    if stats['count'] > 0:
                        report_lines.append(
                            f"    {col}: {stats['count']} ({stats['rate']:.2%})"
                        )

            # 重复记录
            if 'duplicate_records' in self.validation_results['stats']:
                dup_count = self.validation_results['stats']['duplicate_records']
                report_lines.append(f"\n  重复记录: {dup_count}")

            # 日期间隔
            if 'date_gaps' in self.validation_results['stats']:
                gaps = self.validation_results['stats']['date_gaps']
                if gaps:
                    report_lines.append(f"\n  日期间隔: {len(gaps)} 处")
                    for start, end, days in gaps[:5]:  # 只显示前5个
                        report_lines.append(
                            f"    {start.date()} 到 {end.date()}: {days}天"
                        )
                    if len(gaps) > 5:
                        report_lines.append(f"    ... (还有 {len(gaps)-5} 处)")

        report_lines.append("")
        report_lines.append("=" * 60)

        return "\n".join(report_lines)


# ==================== 便捷函数 ====================


def validate_stock_data(
    df: pd.DataFrame,
    required_fields: List[str] = None,
    strict_mode: bool = False
) -> Dict[str, Any]:
    """
    便捷函数：快速验证股票数据

    参数：
        df: 待验证的DataFrame
        required_fields: 必需字段列表
        strict_mode: 严格模式

    返回：
        验证结果字典
    """
    validator = DataValidator(df, required_fields=required_fields)
    return validator.validate_all(strict_mode=strict_mode)


def print_validation_report(df: pd.DataFrame) -> None:
    """
    便捷函数：验证数据并打印报告

    参数：
        df: 待验证的DataFrame
    """
    validator = DataValidator(df)
    validator.validate_all()
    print(validator.get_validation_report())


# ==================== 使用示例 ====================


if __name__ == "__main__":
    # 创建测试数据
    dates = pd.date_range('2023-01-01', periods=100, freq='D')

    np.random.seed(42)
    base_price = 100
    returns = np.random.normal(0.001, 0.02, 100)
    prices = base_price * (1 + returns).cumprod()

    test_df = pd.DataFrame({
        'open': prices * 0.99,
        'high': prices * 1.01,
        'low': prices * 0.98,
        'close': prices,
        'volume': np.random.uniform(1000000, 10000000, 100)
    }, index=dates)

    # 注入一些问题
    test_df.loc[dates[10], 'high'] = test_df.loc[dates[10], 'low'] - 1  # high < low
    test_df.loc[dates[20:25], 'close'] = np.nan  # 缺失值

    print("=" * 60)
    print("数据验证器测试")
    print("=" * 60)

    # 执行验证
    validator = DataValidator(test_df)
    results = validator.validate_all()

    # 打印报告
    print("\n" + validator.get_validation_report())

    print("\n测试完成！")
