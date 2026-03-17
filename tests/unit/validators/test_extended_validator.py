"""
扩展数据验证器单元测试
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, date
from core.src.data.validators.extended_validator import ExtendedDataValidator


class TestExtendedDataValidator:
    """扩展数据验证器测试类"""

    def setup_method(self):
        """初始化测试环境"""
        self.validator = ExtendedDataValidator()

    def test_validate_daily_basic_valid_data(self):
        """测试验证有效的每日指标数据"""
        # 创建有效的测试数据
        df = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ'],
            'trade_date': [date(2024, 3, 15), date(2024, 3, 15)],
            'turnover_rate': [5.5, 8.2],
            'pe': [15.5, 20.3],
            'pb': [2.1, 3.5],
            'total_mv': [10000000, 8000000],
            'circ_mv': [8000000, 6000000],
            'total_share': [1000000, 800000],
            'float_share': [800000, 600000],
            'free_share': [600000, 400000]
        })

        is_valid, errors, warnings = self.validator.validate_daily_basic(df)

        assert is_valid is True
        assert len(errors) == 0
        assert len(warnings) == 0

    def test_validate_daily_basic_invalid_turnover(self):
        """测试换手率异常的情况"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ'],
            'trade_date': [date(2024, 3, 15), date(2024, 3, 15)],
            'turnover_rate': [150, -5]  # 超过100%和负值
        })

        is_valid, errors, warnings = self.validator.validate_daily_basic(df)

        assert is_valid is False
        assert len(errors) > 0
        assert '换手率异常' in errors[0]

    def test_validate_daily_basic_invalid_market_value(self):
        """测试市值逻辑错误的情况"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': [date(2024, 3, 15)],
            'turnover_rate': [5.5],
            'total_mv': [5000000],
            'circ_mv': [8000000]  # 流通市值大于总市值
        })

        is_valid, errors, warnings = self.validator.validate_daily_basic(df)

        assert is_valid is False
        assert len(errors) > 0
        assert '市值逻辑错误' in errors[0]

    def test_validate_moneyflow_valid_data(self):
        """测试验证有效的资金流向数据"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': [date(2024, 3, 15)],
            'buy_sm_amount': [1000],
            'buy_md_amount': [2000],
            'buy_lg_amount': [3000],
            'buy_elg_amount': [4000],
            'sell_sm_amount': [900],
            'sell_md_amount': [2100],
            'sell_lg_amount': [2900],
            'sell_elg_amount': [4100],
            'net_mf_amount': [0]  # 买入10000 - 卖出10000 = 0
        })

        is_valid, errors, warnings = self.validator.validate_moneyflow(df)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_moneyflow_imbalance(self):
        """测试买卖金额不平衡的情况"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': [date(2024, 3, 15)],
            'buy_sm_amount': [1000],
            'buy_md_amount': [2000],
            'buy_lg_amount': [3000],
            'buy_elg_amount': [4000],
            'sell_sm_amount': [100],  # 卖出金额明显偏小
            'sell_md_amount': [200],
            'sell_lg_amount': [300],
            'sell_elg_amount': [400],
            'net_mf_amount': [9000]
        })

        is_valid, errors, warnings = self.validator.validate_moneyflow(df)

        # 买卖不平衡应该产生警告
        assert len(warnings) > 0
        assert '买卖金额不平衡' in warnings[0]

    def test_validate_hk_hold_valid_data(self):
        """测试验证有效的北向资金数据"""
        df = pd.DataFrame({
            'code': ['000001', '000002'],
            'trade_date': [date(2024, 3, 15), date(2024, 3, 15)],
            'vol': [1000000, 2000000],
            'ratio': [5.5, 8.2],
            'exchange': ['SH', 'SZ']
        })

        is_valid, errors, warnings = self.validator.validate_hk_hold(df)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_hk_hold_invalid_ratio(self):
        """测试持股占比异常的情况"""
        df = pd.DataFrame({
            'code': ['000001'],
            'trade_date': [date(2024, 3, 15)],
            'vol': [1000000],
            'ratio': [150],  # 超过100%
            'exchange': ['SH']
        })

        is_valid, errors, warnings = self.validator.validate_hk_hold(df)

        assert is_valid is False
        assert len(errors) > 0
        assert '持股占比异常' in errors[0]

    def test_validate_margin_detail_valid_data(self):
        """测试验证有效的融资融券数据"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': [date(2024, 3, 15)],
            'rzye': [1000000],
            'rqye': [500000],
            'rzrqye': [1500000],  # 正确的总和
            'rzmre': [100000],
            'rzche': [80000]
        })

        is_valid, errors, warnings = self.validator.validate_margin_detail(df)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_margin_detail_calculation_error(self):
        """测试两融余额计算错误的情况"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': [date(2024, 3, 15)],
            'rzye': [1000000],
            'rqye': [500000],
            'rzrqye': [2000000],  # 错误的总和
        })

        is_valid, errors, warnings = self.validator.validate_margin_detail(df)

        assert is_valid is False
        assert len(errors) > 0
        assert '两融余额计算错误' in errors[0]

    def test_validate_stk_limit_valid_data(self):
        """测试验证有效的涨跌停价格数据"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': [date(2024, 3, 15)],
            'pre_close': [10.0],
            'up_limit': [11.0],  # 涨停10%
            'down_limit': [9.0]   # 跌停10%
        })

        is_valid, errors, warnings = self.validator.validate_stk_limit(df)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_stk_limit_invalid_prices(self):
        """测试涨跌停价格逻辑错误的情况"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': [date(2024, 3, 15)],
            'pre_close': [10.0],
            'up_limit': [9.0],   # 涨停价低于昨收价
            'down_limit': [11.0]  # 跌停价高于昨收价
        })

        is_valid, errors, warnings = self.validator.validate_stk_limit(df)

        assert is_valid is False
        assert len(errors) >= 2
        assert '涨停价格错误' in errors[0]
        assert '跌停价格错误' in errors[1]

    def test_validate_adj_factor_valid_data(self):
        """测试验证有效的复权因子数据"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ'],
            'trade_date': [date(2024, 3, 15), date(2024, 3, 16)],
            'adj_factor': [1.0, 1.1]
        })

        is_valid, errors, warnings = self.validator.validate_adj_factor(df)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_adj_factor_invalid(self):
        """测试复权因子异常的情况"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': [date(2024, 3, 15)],
            'adj_factor': [0]  # 复权因子为0
        })

        is_valid, errors, warnings = self.validator.validate_adj_factor(df)

        assert is_valid is False
        assert len(errors) > 0
        assert '复权因子非正' in errors[0]

    def test_fix_daily_basic(self):
        """测试修复每日指标数据"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': [date(2024, 3, 15)],
            'turnover_rate': [150],  # 需要修复
            'total_mv': [5000000],
            'circ_mv': [8000000],  # 需要修复
            'total_share': [1000000],
            'float_share': [1200000],  # 需要修复
            'free_share': [1500000]  # 需要修复
        })

        df_fixed = self.validator.fix_data(df, 'daily_basic')

        # 验证修复后的数据
        assert df_fixed['turnover_rate'].iloc[0] <= 100
        assert df_fixed['circ_mv'].iloc[0] <= df_fixed['total_mv'].iloc[0]
        assert df_fixed['float_share'].iloc[0] <= df_fixed['total_share'].iloc[0]
        assert df_fixed['free_share'].iloc[0] <= df_fixed['float_share'].iloc[0]

    def test_fix_moneyflow(self):
        """测试修复资金流向数据"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': [date(2024, 3, 15)],
            'buy_sm_amount': [-100],  # 负值需要修复
            'buy_md_amount': [2000],
            'buy_lg_amount': [3000],
            'buy_elg_amount': [4000],
            'sell_sm_amount': [900],
            'sell_md_amount': [2100],
            'sell_lg_amount': [2900],
            'sell_elg_amount': [4100],
            'net_mf_amount': [999999]  # 错误的净流入
        })

        df_fixed = self.validator.fix_data(df, 'moneyflow')

        # 验证修复后的数据
        assert df_fixed['buy_sm_amount'].iloc[0] >= 0
        # 净流入应该被重新计算
        buy_total = df_fixed[['buy_sm_amount', 'buy_md_amount', 'buy_lg_amount', 'buy_elg_amount']].sum(axis=1).iloc[0]
        sell_total = df_fixed[['sell_sm_amount', 'sell_md_amount', 'sell_lg_amount', 'sell_elg_amount']].sum(axis=1).iloc[0]
        expected_net = buy_total - sell_total
        assert abs(df_fixed['net_mf_amount'].iloc[0] - expected_net) < 0.01

    def test_generate_validation_report(self):
        """测试生成验证报告"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ'],
            'trade_date': [date(2024, 3, 15), date(2024, 3, 15)],
            'turnover_rate': [5.5, 8.2]
        })

        report = self.validator.generate_validation_report('daily_basic', df)

        assert 'data_type' in report
        assert report['data_type'] == 'daily_basic'
        assert 'status' in report
        assert 'errors' in report
        assert 'warnings' in report
        assert 'summary' in report
        assert report['total_records'] == 2

    def test_batch_validate(self):
        """测试批量验证"""
        data_dict = {
            'daily_basic': pd.DataFrame({
                'ts_code': ['000001.SZ'],
                'trade_date': [date(2024, 3, 15)],
                'turnover_rate': [5.5]
            }),
            'moneyflow': pd.DataFrame({
                'ts_code': ['000001.SZ'],
                'trade_date': [date(2024, 3, 15)],
                'buy_sm_amount': [1000],
                'sell_sm_amount': [900]
            })
        }

        batch_report = self.validator.batch_validate(data_dict)

        assert 'total_datasets' in batch_report
        assert batch_report['total_datasets'] == 2
        assert 'reports' in batch_report
        assert 'daily_basic' in batch_report['reports']
        assert 'moneyflow' in batch_report['reports']
        assert 'overall_status' in batch_report


if __name__ == '__main__':
    pytest.main([__file__, '-v'])