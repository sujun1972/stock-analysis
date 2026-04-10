"""
基础数据验证器
提供通用的数据验证功能
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date
from abc import ABC, abstractmethod
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BaseDataValidator(ABC):
    """基础数据验证器抽象类"""

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.validation_rules = {}
        self.error_threshold = 0.05  # 5%的错误容忍度

    @abstractmethod
    def validate(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        验证数据框架

        Args:
            df: 待验证的数据框

        Returns:
            (是否通过验证, 错误列表)
        """
        pass

    def check_required_columns(self, df: pd.DataFrame, required_cols: List[str]) -> List[str]:
        """
        检查必要的列是否存在

        Args:
            df: 数据框
            required_cols: 必要的列名列表

        Returns:
            缺失列的错误消息列表
        """
        errors = []
        missing_cols = set(required_cols) - set(df.columns)

        for col in missing_cols:
            errors.append(f"缺少必要字段: {col}")

        return errors

    def check_data_types(self, df: pd.DataFrame, type_map: Dict[str, type]) -> List[str]:
        """
        检查数据类型

        Args:
            df: 数据框
            type_map: 列名到类型的映射

        Returns:
            类型错误消息列表
        """
        errors = []

        for col, expected_type in type_map.items():
            if col not in df.columns:
                continue

            # 检查数值类型
            if expected_type in [int, float, np.number]:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    errors.append(f"字段 {col} 应为数值类型")

            # 检查日期类型
            elif expected_type in [datetime, date, pd.Timestamp]:
                if not pd.api.types.is_datetime64_any_dtype(df[col]):
                    try:
                        pd.to_datetime(df[col])
                    except:
                        errors.append(f"字段 {col} 应为日期类型")

            # 检查字符串类型
            elif expected_type == str:
                if not pd.api.types.is_string_dtype(df[col]):
                    errors.append(f"字段 {col} 应为字符串类型")

        return errors

    def check_value_range(self, df: pd.DataFrame, col: str,
                         min_val: Optional[float] = None,
                         max_val: Optional[float] = None) -> List[str]:
        """
        检查值的范围

        Args:
            df: 数据框
            col: 列名
            min_val: 最小值
            max_val: 最大值

        Returns:
            范围错误消息列表
        """
        errors = []

        if col not in df.columns:
            return errors

        # 检查最小值
        if min_val is not None:
            invalid_count = (df[col] < min_val).sum()
            if invalid_count > 0:
                errors.append(f"{col} 有 {invalid_count} 条记录小于最小值 {min_val}")

        # 检查最大值
        if max_val is not None:
            invalid_count = (df[col] > max_val).sum()
            if invalid_count > 0:
                errors.append(f"{col} 有 {invalid_count} 条记录大于最大值 {max_val}")

        return errors

    def check_null_values(self, df: pd.DataFrame,
                         not_null_cols: List[str]) -> List[str]:
        """
        检查空值

        Args:
            df: 数据框
            not_null_cols: 不允许为空的列

        Returns:
            空值错误消息列表
        """
        errors = []

        for col in not_null_cols:
            if col not in df.columns:
                continue

            null_count = df[col].isnull().sum()
            if null_count > 0:
                null_ratio = null_count / len(df)
                if null_ratio > self.error_threshold:
                    errors.append(f"{col} 有 {null_count} ({null_ratio:.1%}) 条空值记录")
                else:
                    self.logger.warning(f"{col} 有 {null_count} ({null_ratio:.1%}) 条空值记录")

        return errors

    def check_duplicates(self, df: pd.DataFrame,
                        key_cols: List[str]) -> List[str]:
        """
        检查重复记录

        Args:
            df: 数据框
            key_cols: 用于判断重复的关键列

        Returns:
            重复错误消息列表
        """
        errors = []

        # 检查是否所有关键列都存在
        if not all(col in df.columns for col in key_cols):
            return errors

        dup_count = df.duplicated(subset=key_cols).sum()
        if dup_count > 0:
            errors.append(f"发现 {dup_count} 条重复记录 (键: {', '.join(key_cols)})")

        return errors

    def check_logical_consistency(self, df: pd.DataFrame,
                                 rules: Dict[str, callable]) -> List[str]:
        """
        检查逻辑一致性

        Args:
            df: 数据框
            rules: 规则名称到验证函数的映射

        Returns:
            逻辑错误消息列表
        """
        errors = []

        for rule_name, rule_func in rules.items():
            try:
                invalid_mask = rule_func(df)
                invalid_count = invalid_mask.sum() if isinstance(invalid_mask, pd.Series) else 0

                if invalid_count > 0:
                    errors.append(f"逻辑规则 '{rule_name}' 失败: {invalid_count} 条记录")
            except Exception as e:
                self.logger.error(f"执行逻辑规则 '{rule_name}' 时出错: {str(e)}")

        return errors

    def check_date_sequence(self, df: pd.DataFrame,
                           date_col: str,
                           allow_gaps: bool = True) -> List[str]:
        """
        检查日期序列的完整性

        Args:
            df: 数据框
            date_col: 日期列名
            allow_gaps: 是否允许日期间隔

        Returns:
            日期序列错误消息列表
        """
        errors = []

        if date_col not in df.columns:
            return errors

        # 转换为日期类型
        try:
            dates = pd.to_datetime(df[date_col])
        except:
            errors.append(f"无法解析日期列 {date_col}")
            return errors

        # 检查日期排序
        if not dates.is_monotonic_increasing:
            errors.append(f"日期列 {date_col} 未按升序排列")

        # 检查日期连续性
        if not allow_gaps:
            date_diff = dates.diff()
            if date_diff.max() > pd.Timedelta(days=1):
                errors.append(f"日期列 {date_col} 存在间隔")

        return errors

    def generate_validation_report(self, df: pd.DataFrame,
                                  errors: List[str]) -> Dict[str, Any]:
        """
        生成验证报告

        Args:
            df: 数据框
            errors: 错误列表

        Returns:
            验证报告字典
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_records': len(df),
            'total_columns': len(df.columns),
            'validation_passed': len(errors) == 0,
            'error_count': len(errors),
            'errors': errors,
            'statistics': {
                'null_ratio': df.isnull().sum().sum() / (len(df) * len(df.columns)),
                'duplicate_ratio': df.duplicated().sum() / len(df) if len(df) > 0 else 0,
            }
        }

        # 添加数据类型统计
        type_stats = {}
        for dtype in df.dtypes.unique():
            type_stats[str(dtype)] = (df.dtypes == dtype).sum()
        report['type_statistics'] = type_stats

        return report

    def auto_fix_common_issues(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        自动修复常见问题

        Args:
            df: 数据框

        Returns:
            修复后的数据框
        """
        df_fixed = df.copy()

        # 去除重复行
        before_len = len(df_fixed)
        df_fixed = df_fixed.drop_duplicates()
        if len(df_fixed) < before_len:
            self.logger.info(f"删除了 {before_len - len(df_fixed)} 条重复记录")

        # 去除全空行
        df_fixed = df_fixed.dropna(how='all')

        # 修复字符串类型的空白
        for col in df_fixed.select_dtypes(include=['object']).columns:
            df_fixed[col] = df_fixed[col].str.strip()

        # 将明显的异常值设置为 NaN
        numeric_cols = df_fixed.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            # 使用 IQR 方法检测异常值
            Q1 = df_fixed[col].quantile(0.25)
            Q3 = df_fixed[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 3 * IQR
            upper_bound = Q3 + 3 * IQR

            outliers = (df_fixed[col] < lower_bound) | (df_fixed[col] > upper_bound)
            outlier_count = outliers.sum()

            if outlier_count > 0 and outlier_count < len(df_fixed) * 0.01:  # 少于1%才处理
                df_fixed.loc[outliers, col] = np.nan
                self.logger.info(f"将 {col} 列的 {outlier_count} 个异常值设为 NaN")

        return df_fixed