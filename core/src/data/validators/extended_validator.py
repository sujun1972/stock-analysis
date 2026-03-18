"""
扩展数据验证器
用于验证Tushare扩展数据的质量和完整性
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
import logging
from .base_validator import BaseDataValidator

logger = logging.getLogger(__name__)


class ExtendedDataValidator(BaseDataValidator):
    """扩展数据验证器

    提供Tushare扩展数据的验证和修复功能，支持：
    - 每日指标(daily_basic)
    - 资金流向(moneyflow)
    - 北向资金(hk_hold)
    - 融资融券(margin_detail)
    - 涨跌停价格(stk_limit)
    - 复权因子(adj_factor)
    """

    def __init__(self):
        super().__init__()
        self.validation_errors = []
        self.validation_warnings = []

    def validate(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        实现基类的抽象方法 - 通用验证入口

        Args:
            df: 待验证的数据框

        Returns:
            (是否通过验证, 错误列表)
        """
        # 简单的验证实现：检查数据框是否为空
        errors = []
        if df is None or df.empty:
            errors.append("数据框为空")
            return False, errors

        # 检查是否有数据
        if len(df) == 0:
            errors.append("数据框没有记录")
            return False, errors

        return True, errors

    def validate_daily_basic(self, df: pd.DataFrame) -> Tuple[bool, List[str], List[str]]:
        """
        验证每日指标数据

        Args:
            df: 待验证的DataFrame

        Returns:
            (是否通过, 错误列表, 警告列表)
        """
        errors = []
        warnings = []

        if df is None or df.empty:
            errors.append("数据为空")
            return False, errors, warnings

        # 检查必要字段
        required_fields = ['ts_code', 'trade_date', 'turnover_rate']
        for field in required_fields:
            if field not in df.columns:
                errors.append(f"缺少必要字段: {field}")

        # 换手率合理性检查 (0-100)
        if 'turnover_rate' in df.columns:
            invalid_turnover = df[
                (df['turnover_rate'] < 0) |
                (df['turnover_rate'] > 100)
            ]
            if not invalid_turnover.empty:
                errors.append(f"换手率异常: {len(invalid_turnover)}条记录超出[0, 100]范围")
                for idx, row in invalid_turnover.head(5).iterrows():
                    errors.append(f"  - {row['ts_code']}: {row['turnover_rate']}%")

        # PE合理性检查 (-1000, 1000)
        if 'pe' in df.columns:
            invalid_pe = df[(df['pe'] < -1000) | (df['pe'] > 1000)]
            if not invalid_pe.empty:
                warnings.append(f"市盈率异常: {len(invalid_pe)}条记录超出[-1000, 1000]范围")

        # PB合理性检查 (0, 100)
        if 'pb' in df.columns:
            invalid_pb = df[(df['pb'] < 0) | (df['pb'] > 100)]
            if not invalid_pb.empty:
                warnings.append(f"市净率异常: {len(invalid_pb)}条记录超出[0, 100]范围")

        # 市值逻辑检查
        if 'total_mv' in df.columns and 'circ_mv' in df.columns:
            invalid_mv = df[df['circ_mv'] > df['total_mv'] * 1.01]  # 允许1%误差
            if not invalid_mv.empty:
                errors.append(f"市值逻辑错误: {len(invalid_mv)}条记录流通市值大于总市值")
                for idx, row in invalid_mv.head(3).iterrows():
                    errors.append(f"  - {row['ts_code']}: 流通{row['circ_mv']:.2f} > 总{row['total_mv']:.2f}")

        # 股本逻辑检查
        if 'total_share' in df.columns and 'float_share' in df.columns:
            invalid_share = df[df['float_share'] > df['total_share'] * 1.01]
            if not invalid_share.empty:
                errors.append(f"股本逻辑错误: {len(invalid_share)}条记录流通股本大于总股本")

        # 自由流通股本检查
        if 'float_share' in df.columns and 'free_share' in df.columns:
            invalid_free = df[df['free_share'] > df['float_share'] * 1.01]
            if not invalid_free.empty:
                warnings.append(f"自由流通股本异常: {len(invalid_free)}条记录自由流通股本大于流通股本")

        # 数据完整性检查
        null_counts = df.isnull().sum()
        high_null_fields = null_counts[null_counts > len(df) * 0.5]
        if not high_null_fields.empty:
            for field, count in high_null_fields.items():
                warnings.append(f"字段 {field} 缺失率高: {count}/{len(df)} ({count/len(df)*100:.1f}%)")

        return len(errors) == 0, errors, warnings

    def validate_moneyflow(self, df: pd.DataFrame) -> Tuple[bool, List[str], List[str]]:
        """
        验证资金流向数据

        Args:
            df: 待验证的DataFrame

        Returns:
            (是否通过, 错误列表, 警告列表)
        """
        errors = []
        warnings = []

        if df is None or df.empty:
            errors.append("数据为空")
            return False, errors, warnings

        # 买卖平衡检查
        buy_cols = ['buy_sm_amount', 'buy_md_amount',
                   'buy_lg_amount', 'buy_elg_amount']
        sell_cols = ['sell_sm_amount', 'sell_md_amount',
                    'sell_lg_amount', 'sell_elg_amount']

        if all(col in df.columns for col in buy_cols + sell_cols):
            df['total_buy'] = df[buy_cols].sum(axis=1)
            df['total_sell'] = df[sell_cols].sum(axis=1)

            # 买卖总额应该大致相等（允许5%误差）
            df['imbalance_ratio'] = abs(df['total_buy'] - df['total_sell']) / \
                                   df[['total_buy', 'total_sell']].mean(axis=1)

            imbalanced = df[df['imbalance_ratio'] > 0.05]
            if not imbalanced.empty:
                warnings.append(f"买卖金额不平衡: {len(imbalanced)}条记录偏差超过5%")
                for idx, row in imbalanced.head(3).iterrows():
                    warnings.append(f"  - {row['ts_code']}: 买{row['total_buy']:.2f} vs 卖{row['total_sell']:.2f}")

        # 净流入检查
        if 'net_mf_amount' in df.columns and 'total_buy' in df.columns:
            df['calc_net'] = df['total_buy'] - df['total_sell']
            invalid_net = df[abs(df['net_mf_amount'] - df['calc_net']) > 1]  # 允许1万元误差
            if not invalid_net.empty:
                errors.append(f"净流入计算错误: {len(invalid_net)}条记录")
                for idx, row in invalid_net.head(3).iterrows():
                    errors.append(f"  - {row['ts_code']}: 报告{row['net_mf_amount']:.2f} vs 计算{row['calc_net']:.2f}")

        # 金额合理性检查（不能为负）
        amount_cols = buy_cols + sell_cols if all(col in df.columns for col in buy_cols + sell_cols) else []
        for col in amount_cols:
            if col in df.columns:
                negative_amounts = df[df[col] < 0]
                if not negative_amounts.empty:
                    errors.append(f"{col} 存在负值: {len(negative_amounts)}条记录")

        # 交易量逻辑检查
        vol_cols = ['buy_sm_vol', 'buy_md_vol', 'buy_lg_vol', 'buy_elg_vol',
                   'sell_sm_vol', 'sell_md_vol', 'sell_lg_vol', 'sell_elg_vol']

        for col in vol_cols:
            if col in df.columns:
                negative_vols = df[df[col] < 0]
                if not negative_vols.empty:
                    errors.append(f"{col} 存在负值: {len(negative_vols)}条记录")

        # 数据一致性检查
        if 'trade_count' in df.columns:
            zero_count = df[df['trade_count'] == 0]
            if not zero_count.empty:
                # 如果交易笔数为0，所有金额应该也为0
                for idx, row in zero_count.iterrows():
                    if 'net_mf_amount' in df.columns and row['net_mf_amount'] != 0:
                        warnings.append(f"{row['ts_code']}: 交易笔数为0但净流入不为0")

        return len(errors) == 0, errors, warnings

    def validate_hk_hold(self, df: pd.DataFrame) -> Tuple[bool, List[str], List[str]]:
        """
        验证北向资金持股数据

        Args:
            df: 待验证的DataFrame

        Returns:
            (是否通过, 错误列表, 警告列表)
        """
        errors = []
        warnings = []

        if df is None or df.empty:
            errors.append("数据为空")
            return False, errors, warnings

        # 必要字段检查
        required_fields = ['code', 'trade_date', 'vol', 'ratio']
        for field in required_fields:
            if field not in df.columns:
                errors.append(f"缺少必要字段: {field}")

        # 持股数量合理性检查
        if 'vol' in df.columns:
            negative_vol = df[df['vol'] < 0]
            if not negative_vol.empty:
                errors.append(f"持股数量为负: {len(negative_vol)}条记录")

            # 异常大的持股数量（超过1000亿股）
            huge_vol = df[df['vol'] > 1000_0000_0000]
            if not huge_vol.empty:
                warnings.append(f"持股数量异常大: {len(huge_vol)}条记录超过1000亿股")

        # 持股占比合理性检查 (0-100)
        if 'ratio' in df.columns:
            invalid_ratio = df[(df['ratio'] < 0) | (df['ratio'] > 100)]
            if not invalid_ratio.empty:
                errors.append(f"持股占比异常: {len(invalid_ratio)}条记录超出[0, 100]范围")

            # 警告：持股占比超过30%（可能是数据异常）
            high_ratio = df[df['ratio'] > 30]
            if not high_ratio.empty:
                warnings.append(f"持股占比偏高: {len(high_ratio)}条记录超过30%")

        # 交易所代码检查
        if 'exchange' in df.columns:
            valid_exchanges = ['SH', 'SZ']
            invalid_exchange = df[~df['exchange'].isin(valid_exchanges)]
            if not invalid_exchange.empty:
                errors.append(f"无效的交易所代码: {len(invalid_exchange)}条记录")

        # 数据重复检查
        if all(field in df.columns for field in ['code', 'trade_date', 'exchange']):
            duplicates = df.duplicated(subset=['code', 'trade_date', 'exchange'], keep=False)
            if duplicates.any():
                dup_count = duplicates.sum()
                warnings.append(f"存在重复记录: {dup_count}条")

        return len(errors) == 0, errors, warnings

    def validate_margin_detail(self, df: pd.DataFrame) -> Tuple[bool, List[str], List[str]]:
        """
        验证融资融券数据

        Args:
            df: 待验证的DataFrame

        Returns:
            (是否通过, 错误列表, 警告列表)
        """
        errors = []
        warnings = []

        if df is None or df.empty:
            errors.append("数据为空")
            return False, errors, warnings

        # 必要字段检查
        required_fields = ['ts_code', 'trade_date', 'rzye', 'rqye']
        for field in required_fields:
            if field not in df.columns:
                errors.append(f"缺少必要字段: {field}")

        # 融资余额合理性检查
        if 'rzye' in df.columns:
            negative_rzye = df[df['rzye'] < 0]
            if not negative_rzye.empty:
                errors.append(f"融资余额为负: {len(negative_rzye)}条记录")

            # 异常大的融资余额（超过1000亿）
            huge_rzye = df[df['rzye'] > 1000_0000]
            if not huge_rzye.empty:
                warnings.append(f"融资余额异常大: {len(huge_rzye)}条记录超过1000亿")

        # 融券余额合理性检查
        if 'rqye' in df.columns:
            negative_rqye = df[df['rqye'] < 0]
            if not negative_rqye.empty:
                errors.append(f"融券余额为负: {len(negative_rqye)}条记录")

        # 融资融券余额逻辑检查
        if all(field in df.columns for field in ['rzye', 'rqye', 'rzrqye']):
            df['calc_rzrqye'] = df['rzye'] + df['rqye']
            invalid_total = df[abs(df['rzrqye'] - df['calc_rzrqye']) > 1]  # 允许1万元误差
            if not invalid_total.empty:
                errors.append(f"两融余额计算错误: {len(invalid_total)}条记录")
                for idx, row in invalid_total.head(3).iterrows():
                    errors.append(f"  - {row['ts_code']}: 报告{row['rzrqye']:.2f} vs 计算{row['calc_rzrqye']:.2f}")

        # 融资买入/偿还逻辑检查
        if 'rzmre' in df.columns:
            negative_rzmre = df[df['rzmre'] < 0]
            if not negative_rzmre.empty:
                errors.append(f"融资买入额为负: {len(negative_rzmre)}条记录")

        if 'rzche' in df.columns:
            negative_rzche = df[df['rzche'] < 0]
            if not negative_rzche.empty:
                errors.append(f"融资偿还额为负: {len(negative_rzche)}条记录")

        # 融券卖出/偿还逻辑检查
        if 'rqyl' in df.columns:
            negative_rqyl = df[df['rqyl'] < 0]
            if not negative_rqyl.empty:
                errors.append(f"融券余量为负: {len(negative_rqyl)}条记录")

        # 比例合理性检查
        if all(field in df.columns for field in ['rzye', 'rqye']):
            df['rq_ratio'] = df['rqye'] / (df['rzye'] + df['rqye'] + 1)  # 加1避免除零
            high_rq_ratio = df[df['rq_ratio'] > 0.1]  # 融券占比超过10%
            if not high_rq_ratio.empty:
                warnings.append(f"融券占比偏高: {len(high_rq_ratio)}条记录融券占比超过10%")

        return len(errors) == 0, errors, warnings

    def validate_stk_limit(self, df: pd.DataFrame) -> Tuple[bool, List[str], List[str]]:
        """
        验证涨跌停价格数据

        Args:
            df: 待验证的DataFrame

        Returns:
            (是否通过, 错误列表, 警告列表)
        """
        errors = []
        warnings = []

        if df is None or df.empty:
            errors.append("数据为空")
            return False, errors, warnings

        # 必要字段检查
        required_fields = ['ts_code', 'trade_date', 'pre_close', 'up_limit', 'down_limit']
        for field in required_fields:
            if field not in df.columns:
                errors.append(f"缺少必要字段: {field}")

        # 价格合理性检查
        if all(field in df.columns for field in ['pre_close', 'up_limit', 'down_limit']):
            # 涨停价应该大于昨收价
            invalid_up = df[df['up_limit'] <= df['pre_close']]
            if not invalid_up.empty:
                errors.append(f"涨停价格错误: {len(invalid_up)}条记录涨停价不高于昨收价")

            # 跌停价应该小于昨收价
            invalid_down = df[df['down_limit'] >= df['pre_close']]
            if not invalid_down.empty:
                errors.append(f"跌停价格错误: {len(invalid_down)}条记录跌停价不低于昨收价")

            # 涨跌幅度检查（一般为10%或20%）
            df['up_ratio'] = (df['up_limit'] - df['pre_close']) / df['pre_close']
            df['down_ratio'] = (df['pre_close'] - df['down_limit']) / df['pre_close']

            # 主板涨跌幅10%，创业板/科创板20%
            unusual_up = df[(df['up_ratio'] < 0.095) |
                           ((df['up_ratio'] > 0.105) & (df['up_ratio'] < 0.195)) |
                           (df['up_ratio'] > 0.205)]
            if not unusual_up.empty:
                warnings.append(f"涨幅异常: {len(unusual_up)}条记录涨幅不是10%或20%")

            unusual_down = df[(df['down_ratio'] < 0.095) |
                            ((df['down_ratio'] > 0.105) & (df['down_ratio'] < 0.195)) |
                            (df['down_ratio'] > 0.205)]
            if not unusual_down.empty:
                warnings.append(f"跌幅异常: {len(unusual_down)}条记录跌幅不是10%或20%")

        # 价格为负检查
        for field in ['pre_close', 'up_limit', 'down_limit']:
            if field in df.columns:
                negative_price = df[df[field] <= 0]
                if not negative_price.empty:
                    errors.append(f"{field} 存在非正值: {len(negative_price)}条记录")

        return len(errors) == 0, errors, warnings

    def validate_adj_factor(self, df: pd.DataFrame) -> Tuple[bool, List[str], List[str]]:
        """
        验证复权因子数据

        Args:
            df: 待验证的DataFrame

        Returns:
            (是否通过, 错误列表, 警告列表)
        """
        errors = []
        warnings = []

        if df is None or df.empty:
            errors.append("数据为空")
            return False, errors, warnings

        # 必要字段检查
        required_fields = ['ts_code', 'trade_date', 'adj_factor']
        for field in required_fields:
            if field not in df.columns:
                errors.append(f"缺少必要字段: {field}")

        # 复权因子合理性检查
        if 'adj_factor' in df.columns:
            # 复权因子应该大于0
            invalid_factor = df[df['adj_factor'] <= 0]
            if not invalid_factor.empty:
                errors.append(f"复权因子非正: {len(invalid_factor)}条记录")

            # 复权因子通常在0.1到10之间
            unusual_factor = df[(df['adj_factor'] < 0.1) | (df['adj_factor'] > 10)]
            if not unusual_factor.empty:
                warnings.append(f"复权因子异常: {len(unusual_factor)}条记录超出[0.1, 10]范围")

            # 检查复权因子的连续性（同一股票相邻日期的复权因子不应突变）
            if 'ts_code' in df.columns and 'trade_date' in df.columns:
                df_sorted = df.sort_values(['ts_code', 'trade_date'])
                df_sorted['factor_change'] = df_sorted.groupby('ts_code')['adj_factor'].pct_change()

                # 复权因子日变化超过50%的记录
                large_change = df_sorted[abs(df_sorted['factor_change']) > 0.5]
                if not large_change.empty:
                    warnings.append(f"复权因子突变: {len(large_change)}条记录日变化超过50%")

        return len(errors) == 0, errors, warnings

    def generate_validation_report(self,
                                  data_type: str,
                                  df: pd.DataFrame) -> Dict[str, Any]:
        """
        生成数据验证报告

        Args:
            data_type: 数据类型
            df: 待验证的DataFrame

        Returns:
            验证报告字典
        """
        validation_methods = {
            'daily_basic': self.validate_daily_basic,
            'moneyflow': self.validate_moneyflow,
            'hk_hold': self.validate_hk_hold,
            'margin_detail': self.validate_margin_detail,
            'stk_limit': self.validate_stk_limit,
            'adj_factor': self.validate_adj_factor
        }

        if data_type not in validation_methods:
            return {
                'data_type': data_type,
                'status': 'error',
                'message': f'不支持的数据类型: {data_type}'
            }

        validate_func = validation_methods[data_type]
        is_valid, errors, warnings = validate_func(df)

        report = {
            'data_type': data_type,
            'timestamp': datetime.now().isoformat(),
            'total_records': len(df) if df is not None else 0,
            'status': 'passed' if is_valid else 'failed',
            'errors_count': len(errors),
            'warnings_count': len(warnings),
            'errors': errors,
            'warnings': warnings,
            'summary': {
                'null_counts': df.isnull().sum().to_dict() if df is not None else {},
                'duplicates': df.duplicated().sum() if df is not None else 0,
                'date_range': {
                    'min': df['trade_date'].min() if df is not None and 'trade_date' in df.columns else None,
                    'max': df['trade_date'].max() if df is not None and 'trade_date' in df.columns else None
                }
            }
        }

        return report

    def fix_data(self, df: pd.DataFrame, data_type: str) -> pd.DataFrame:
        """
        修复数据中的常见问题

        Args:
            df: 待修复的DataFrame
            data_type: 数据类型

        Returns:
            修复后的DataFrame
        """
        if data_type == 'daily_basic':
            return self._fix_daily_basic(df)
        elif data_type == 'moneyflow':
            return self._fix_moneyflow(df)
        elif data_type == 'margin_detail':
            return self._fix_margin_detail(df)
        elif data_type == 'hk_hold':
            return self._fix_hk_hold(df)
        elif data_type == 'stk_limit':
            return self._fix_stk_limit(df)
        else:
            # 应用通用修复
            return self.auto_fix_common_issues(df)

    def _fix_daily_basic(self, df: pd.DataFrame) -> pd.DataFrame:
        """修复每日指标数据"""
        df_fixed = df.copy()

        # 修复换手率超过100%的情况
        if 'turnover_rate' in df_fixed.columns:
            mask = df_fixed['turnover_rate'] > 100
            if mask.sum() > 0:
                df_fixed.loc[mask, 'turnover_rate'] = df_fixed.loc[mask, 'turnover_rate'] / 100
                logger.info(f"修复了 {mask.sum()} 条换手率超过100%的记录")

        # 修复市值逻辑错误
        if all(col in df_fixed.columns for col in ['total_mv', 'circ_mv']):
            mask = df_fixed['circ_mv'] > df_fixed['total_mv']
            if mask.sum() > 0:
                df_fixed.loc[mask, ['total_mv', 'circ_mv']] = \
                    df_fixed.loc[mask, ['circ_mv', 'total_mv']].values
                logger.info(f"修复了 {mask.sum()} 条市值逻辑错误")

        # 修复股本逻辑错误
        if all(col in df_fixed.columns for col in ['total_share', 'float_share', 'free_share']):
            # 自由流通股本不应大于流通股本
            mask = df_fixed['free_share'] > df_fixed['float_share']
            if mask.sum() > 0:
                df_fixed.loc[mask, 'free_share'] = df_fixed.loc[mask, 'float_share']
                logger.info(f"修复了 {mask.sum()} 条自由流通股本错误")

            # 流通股本不应大于总股本
            mask = df_fixed['float_share'] > df_fixed['total_share']
            if mask.sum() > 0:
                df_fixed.loc[mask, 'float_share'] = df_fixed.loc[mask, 'total_share']
                logger.info(f"修复了 {mask.sum()} 条流通股本错误")

        return self.auto_fix_common_issues(df_fixed)

    def _fix_moneyflow(self, df: pd.DataFrame) -> pd.DataFrame:
        """修复资金流向数据"""
        df_fixed = df.copy()

        # 修复净流入计算错误
        buy_cols = ['buy_sm_amount', 'buy_md_amount', 'buy_lg_amount', 'buy_elg_amount']
        sell_cols = ['sell_sm_amount', 'sell_md_amount', 'sell_lg_amount', 'sell_elg_amount']

        if all(col in df_fixed.columns for col in buy_cols + sell_cols):
            total_buy = df_fixed[buy_cols].sum(axis=1)
            total_sell = df_fixed[sell_cols].sum(axis=1)
            calc_net = total_buy - total_sell

            if 'net_mf_amount' in df_fixed.columns:
                mask = abs(df_fixed['net_mf_amount'] - calc_net) > 0.01
                if mask.sum() > 0:
                    df_fixed.loc[mask, 'net_mf_amount'] = calc_net[mask]
                    logger.info(f"修复了 {mask.sum()} 条净流入计算错误")

        # 修复负值问题
        for col in buy_cols + sell_cols:
            if col in df_fixed.columns:
                mask = df_fixed[col] < 0
                if mask.sum() > 0:
                    df_fixed.loc[mask, col] = 0
                    logger.info(f"将 {col} 的 {mask.sum()} 个负值设为0")

        return self.auto_fix_common_issues(df_fixed)

    def _fix_margin_detail(self, df: pd.DataFrame) -> pd.DataFrame:
        """修复融资融券数据"""
        df_fixed = df.copy()

        # 修复两融余额计算错误
        if all(col in df_fixed.columns for col in ['rzye', 'rqye', 'rzrqye']):
            calc_rzrqye = df_fixed['rzye'] + df_fixed['rqye']
            mask = abs(df_fixed['rzrqye'] - calc_rzrqye) > 0.01
            if mask.sum() > 0:
                df_fixed.loc[mask, 'rzrqye'] = calc_rzrqye[mask]
                logger.info(f"修复了 {mask.sum()} 条两融余额计算错误")

        # 修复负值问题
        for col in ['rzye', 'rqye', 'rzmre', 'rzche', 'rqyl']:
            if col in df_fixed.columns:
                mask = df_fixed[col] < 0
                if mask.sum() > 0:
                    df_fixed.loc[mask, col] = 0
                    logger.info(f"将 {col} 的 {mask.sum()} 个负值设为0")

        return self.auto_fix_common_issues(df_fixed)

    def _fix_hk_hold(self, df: pd.DataFrame) -> pd.DataFrame:
        """修复北向资金数据"""
        df_fixed = df.copy()

        # 修复持股数量负值
        if 'vol' in df_fixed.columns:
            mask = df_fixed['vol'] < 0
            if mask.sum() > 0:
                df_fixed.loc[mask, 'vol'] = 0
                logger.info(f"修复了 {mask.sum()} 条持股数量负值")

        # 修复持股占比超过100%
        if 'ratio' in df_fixed.columns:
            mask = df_fixed['ratio'] > 100
            if mask.sum() > 0:
                df_fixed.loc[mask, 'ratio'] = 100
                logger.info(f"修复了 {mask.sum()} 条持股占比超过100%")

            mask = df_fixed['ratio'] < 0
            if mask.sum() > 0:
                df_fixed.loc[mask, 'ratio'] = 0
                logger.info(f"修复了 {mask.sum()} 条持股占比负值")

        return self.auto_fix_common_issues(df_fixed)

    def _fix_stk_limit(self, df: pd.DataFrame) -> pd.DataFrame:
        """修复涨跌停价格数据"""
        df_fixed = df.copy()

        # 修复涨跌停价格逻辑错误
        if all(col in df_fixed.columns for col in ['pre_close', 'up_limit', 'down_limit']):
            # 涨停价应该大于昨收价
            mask = df_fixed['up_limit'] <= df_fixed['pre_close']
            if mask.sum() > 0:
                # 按10%计算涨停价
                df_fixed.loc[mask, 'up_limit'] = df_fixed.loc[mask, 'pre_close'] * 1.1
                logger.info(f"修复了 {mask.sum()} 条涨停价格错误")

            # 跌停价应该小于昨收价
            mask = df_fixed['down_limit'] >= df_fixed['pre_close']
            if mask.sum() > 0:
                # 按10%计算跌停价
                df_fixed.loc[mask, 'down_limit'] = df_fixed.loc[mask, 'pre_close'] * 0.9
                logger.info(f"修复了 {mask.sum()} 条跌停价格错误")

        return self.auto_fix_common_issues(df_fixed)

    def batch_validate(self, data_dict: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        批量验证多个数据集

        Args:
            data_dict: {数据类型: DataFrame} 字典

        Returns:
            批量验证报告
        """
        reports = {}
        total_errors = 0
        total_warnings = 0

        for data_type, df in data_dict.items():
            report = self.generate_validation_report(data_type, df)
            reports[data_type] = report
            total_errors += report['errors_count']
            total_warnings += report['warnings_count']

        return {
            'timestamp': datetime.now().isoformat(),
            'total_datasets': len(data_dict),
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'reports': reports,
            'overall_status': 'passed' if total_errors == 0 else 'failed'
        }