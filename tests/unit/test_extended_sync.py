"""
扩展数据同步服务单元测试
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd
import numpy as np

# 导入待测试模块
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))
from backend.app.services.extended_sync_service import ExtendedDataSyncService
from core.src.data.validators.extended_validator import ExtendedDataValidator


class TestExtendedDataSyncService:
    """扩展数据同步服务测试类"""

    @pytest.fixture
    def sync_service(self):
        """创建同步服务实例"""
        return ExtendedDataSyncService()

    @pytest.fixture
    def mock_provider(self):
        """创建模拟的数据提供者"""
        provider = Mock()
        return provider

    @pytest.fixture
    def sample_daily_basic_data(self):
        """创建示例每日指标数据"""
        return pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ', '600000.SH'],
            'trade_date': pd.to_datetime(['2024-03-17', '2024-03-17', '2024-03-17']),
            'close': [12.34, 23.45, 34.56],
            'turnover_rate': [2.34, 5.67, 3.45],
            'turnover_rate_f': [2.12, 5.23, 3.21],
            'volume_ratio': [1.23, 0.89, 1.05],
            'pe': [15.6, 23.4, 12.3],
            'pe_ttm': [16.2, 24.1, 12.8],
            'pb': [1.2, 2.3, 1.5],
            'ps': [2.3, 3.4, 2.1],
            'ps_ttm': [2.4, 3.5, 2.2],
            'dv_ratio': [1.2, 0.8, 1.5],
            'dv_ttm': [1.3, 0.9, 1.6],
            'total_share': [10000.0, 20000.0, 30000.0],
            'float_share': [8000.0, 15000.0, 25000.0],
            'free_share': [6000.0, 12000.0, 20000.0],
            'total_mv': [123400.0, 469000.0, 1036800.0],
            'circ_mv': [98720.0, 351750.0, 864000.0]
        })

    @pytest.fixture
    def sample_moneyflow_data(self):
        """创建示例资金流向数据"""
        return pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ'],
            'trade_date': pd.to_datetime(['2024-03-17', '2024-03-17']),
            'buy_sm_vol': [1000000, 2000000],
            'buy_sm_amount': [1234.56, 2345.67],
            'sell_sm_vol': [900000, 1900000],
            'sell_sm_amount': [1123.45, 2234.56],
            'buy_md_vol': [500000, 600000],
            'buy_md_amount': [2345.67, 3456.78],
            'sell_md_vol': [450000, 550000],
            'sell_md_amount': [2234.56, 3345.67],
            'buy_lg_vol': [300000, 400000],
            'buy_lg_amount': [3456.78, 4567.89],
            'sell_lg_vol': [280000, 380000],
            'sell_lg_amount': [3345.67, 4456.78],
            'buy_elg_vol': [200000, 300000],
            'buy_elg_amount': [4567.89, 5678.90],
            'sell_elg_vol': [190000, 290000],
            'sell_elg_amount': [4456.78, 5567.89],
            'net_mf_vol': [80000, 90000],
            'net_mf_amount': [456.78, 567.89],
            'trade_count': [12345, 23456]
        })

    @pytest.mark.asyncio
    async def test_sync_daily_basic_success(self, sync_service, mock_provider, sample_daily_basic_data):
        """测试每日指标同步成功"""
        # 配置mock
        mock_provider.get_daily_basic = Mock(return_value=sample_daily_basic_data)

        with patch.object(sync_service, '_get_provider', return_value=mock_provider):
            with patch.object(sync_service, '_insert_daily_basic', new_callable=AsyncMock) as mock_insert:
                result = await sync_service.sync_daily_basic(trade_date='20240317')

                # 验证结果
                assert result['status'] == 'success'
                assert result['records'] == 3
                assert 'task_id' in result
                assert 'daily_basic' in result['task_id']

                # 验证调用
                mock_provider.get_daily_basic.assert_called_once_with(
                    trade_date='20240317',
                    start_date=None,
                    end_date=None
                )
                mock_insert.assert_called_once_with(sample_daily_basic_data)

    @pytest.mark.asyncio
    async def test_sync_daily_basic_empty_data(self, sync_service, mock_provider):
        """测试每日指标同步空数据"""
        # 配置mock返回空数据
        mock_provider.get_daily_basic = Mock(return_value=pd.DataFrame())

        with patch.object(sync_service, '_get_provider', return_value=mock_provider):
            result = await sync_service.sync_daily_basic(trade_date='20240317')

            assert result['status'] == 'success'
            assert result['records'] == 0
            assert result['message'] == '无数据需要同步'

    @pytest.mark.asyncio
    async def test_sync_daily_basic_error(self, sync_service, mock_provider):
        """测试每日指标同步失败"""
        # 配置mock抛出异常
        mock_provider.get_daily_basic = Mock(side_effect=Exception('API Error'))

        with patch.object(sync_service, '_get_provider', return_value=mock_provider):
            result = await sync_service.sync_daily_basic(trade_date='20240317')

            assert result['status'] == 'error'
            assert result['records'] == 0
            assert 'API Error' in result['error']

    @pytest.mark.asyncio
    async def test_sync_moneyflow_with_stock_list(self, sync_service, mock_provider, sample_moneyflow_data):
        """测试资金流向同步（指定股票列表）"""
        stock_list = ['000001.SZ', '000002.SZ']

        # 配置mock
        mock_provider.get_moneyflow = Mock(return_value=sample_moneyflow_data)

        with patch.object(sync_service, '_get_provider', return_value=mock_provider):
            with patch.object(sync_service, '_insert_moneyflow', new_callable=AsyncMock) as mock_insert:
                result = await sync_service.sync_moneyflow(
                    trade_date='20240317',
                    stock_list=stock_list
                )

                assert result['status'] == 'success'
                assert result['records'] == 4  # 2 stocks * 2 records
                assert len(result.get('failed_stocks', [])) == 0

    @pytest.mark.asyncio
    async def test_sync_moneyflow_without_stock_list(self, sync_service, mock_provider):
        """测试资金流向同步（自动获取活跃股票）"""
        # Mock活跃股票列表
        active_stocks = ['000001.SZ', '000002.SZ']

        with patch.object(sync_service, '_get_active_stocks', new_callable=AsyncMock) as mock_get_active:
            mock_get_active.return_value = active_stocks

            # 配置mock返回数据
            mock_provider.get_moneyflow = Mock(return_value=pd.DataFrame())

            with patch.object(sync_service, '_get_provider', return_value=mock_provider):
                result = await sync_service.sync_moneyflow(trade_date='20240317')

                # 验证获取活跃股票被调用
                mock_get_active.assert_called_once_with('20240317')
                assert result['status'] == 'success'

    @pytest.mark.asyncio
    async def test_sync_hk_hold_success(self, sync_service, mock_provider):
        """测试北向资金同步成功"""
        sample_data = pd.DataFrame({
            'code': ['000001', '000002'],
            'trade_date': pd.to_datetime(['2024-03-17', '2024-03-17']),
            'ts_code': ['000001.SZ', '000002.SZ'],
            'name': ['平安银行', '万科A'],
            'vol': [100000000, 200000000],
            'ratio': [1.23, 2.34],
            'exchange': ['SZ', 'SZ']
        })

        mock_provider.get_hk_hold = Mock(return_value=sample_data)

        with patch.object(sync_service, '_get_provider', return_value=mock_provider):
            with patch.object(sync_service, '_insert_hk_hold', new_callable=AsyncMock) as mock_insert:
                result = await sync_service.sync_hk_hold(trade_date='20240317')

                assert result['status'] == 'success'
                assert result['records'] == 4  # 2 exchanges * 2 records

                # 验证沪股通和深股通都被调用
                assert mock_provider.get_hk_hold.call_count == 2

    @pytest.mark.asyncio
    async def test_sync_margin_detail_success(self, sync_service, mock_provider):
        """测试融资融券同步成功"""
        sample_data = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ'],
            'trade_date': pd.to_datetime(['2024-03-17', '2024-03-17']),
            'rzye': [123456.78, 234567.89],
            'rqye': [12345.67, 23456.78],
            'rzmre': [34567.89, 45678.90],
            'rqyl': [1000000, 2000000],
            'rzche': [23456.78, 34567.89],
            'rqchl': [900000, 1900000],
            'rqmcl': [100000, 200000],
            'rzrqye': [135802.45, 258024.67]
        })

        mock_provider.get_margin_detail = Mock(return_value=sample_data)

        with patch.object(sync_service, '_get_provider', return_value=mock_provider):
            with patch.object(sync_service, '_insert_margin_detail', new_callable=AsyncMock) as mock_insert:
                result = await sync_service.sync_margin_detail(trade_date='20240317')

                assert result['status'] == 'success'
                assert result['records'] == 2
                mock_insert.assert_called_once_with(sample_data)

    @pytest.mark.asyncio
    async def test_get_active_stocks(self, sync_service):
        """测试获取活跃股票列表"""
        # 这个测试需要模拟数据库连接
        with patch('backend.app.services.extended_sync_service.get_async_db') as mock_get_db:
            # 模拟数据库查询结果
            mock_result = Mock()
            mock_result.fetchall = Mock(return_value=[
                ('000001.SZ',),
                ('000002.SZ',),
                ('600000.SH',)
            ])

            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=mock_result)
            mock_db.__aenter__ = AsyncMock(return_value=mock_db)
            mock_db.__aexit__ = AsyncMock(return_value=None)

            mock_get_db.return_value = mock_db

            stocks = await sync_service._get_active_stocks('2024-03-17')

            assert len(stocks) == 3
            assert '000001.SZ' in stocks
            assert '000002.SZ' in stocks
            assert '600000.SH' in stocks


class TestExtendedDataValidator:
    """扩展数据验证器测试类"""

    @pytest.fixture
    def validator(self):
        """创建验证器实例"""
        return ExtendedDataValidator()

    def test_validate_daily_basic_valid(self, validator):
        """测试有效的每日指标数据"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['2024-03-17'],
            'turnover_rate': [5.0],
            'pe': [15.0],
            'pb': [2.0],
            'total_mv': [100000.0],
            'circ_mv': [80000.0],
            'total_share': [10000.0],
            'float_share': [8000.0],
            'free_share': [6000.0]
        })

        is_valid, errors, warnings = validator.validate_daily_basic(df)

        assert is_valid is True
        assert len(errors) == 0
        assert len(warnings) == 0

    def test_validate_daily_basic_invalid_turnover(self, validator):
        """测试无效的换手率"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ'],
            'trade_date': ['2024-03-17', '2024-03-17'],
            'turnover_rate': [150.0, -5.0]  # 无效的换手率
        })

        is_valid, errors, warnings = validator.validate_daily_basic(df)

        assert is_valid is False
        assert len(errors) > 0
        assert '换手率异常' in errors[0]

    def test_validate_daily_basic_invalid_market_value(self, validator):
        """测试无效的市值逻辑"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['2024-03-17'],
            'turnover_rate': [5.0],
            'total_mv': [100000.0],
            'circ_mv': [120000.0]  # 流通市值大于总市值
        })

        is_valid, errors, warnings = validator.validate_daily_basic(df)

        assert is_valid is False
        assert len(errors) > 0
        assert '市值逻辑错误' in errors[0]

    def test_validate_moneyflow_valid(self, validator):
        """测试有效的资金流向数据"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['2024-03-17'],
            'buy_sm_amount': [1000.0],
            'sell_sm_amount': [950.0],
            'buy_md_amount': [2000.0],
            'sell_md_amount': [1900.0],
            'buy_lg_amount': [3000.0],
            'sell_lg_amount': [2900.0],
            'buy_elg_amount': [4000.0],
            'sell_elg_amount': [3900.0],
            'net_mf_amount': [400.0],
            'trade_count': [10000]
        })

        is_valid, errors, warnings = validator.validate_moneyflow(df)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_moneyflow_negative_amount(self, validator):
        """测试负值金额"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['2024-03-17'],
            'buy_sm_amount': [-1000.0],  # 负值
            'sell_sm_amount': [950.0],
            'net_mf_amount': [-1950.0]
        })

        is_valid, errors, warnings = validator.validate_moneyflow(df)

        assert is_valid is False
        assert len(errors) > 0
        assert '存在负值' in str(errors)

    def test_validate_hk_hold_valid(self, validator):
        """测试有效的北向资金数据"""
        df = pd.DataFrame({
            'code': ['000001'],
            'trade_date': ['2024-03-17'],
            'vol': [100000000],
            'ratio': [2.5],
            'exchange': ['SZ']
        })

        is_valid, errors, warnings = validator.validate_hk_hold(df)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_hk_hold_invalid_ratio(self, validator):
        """测试无效的持股占比"""
        df = pd.DataFrame({
            'code': ['000001'],
            'trade_date': ['2024-03-17'],
            'vol': [100000000],
            'ratio': [150.0],  # 超过100%
            'exchange': ['SZ']
        })

        is_valid, errors, warnings = validator.validate_hk_hold(df)

        assert is_valid is False
        assert len(errors) > 0
        assert '持股占比异常' in errors[0]

    def test_validate_margin_detail_valid(self, validator):
        """测试有效的融资融券数据"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['2024-03-17'],
            'rzye': [100000.0],
            'rqye': [10000.0],
            'rzrqye': [110000.0],
            'rzmre': [20000.0],
            'rzche': [15000.0]
        })

        is_valid, errors, warnings = validator.validate_margin_detail(df)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_margin_detail_calculation_error(self, validator):
        """测试两融余额计算错误"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['2024-03-17'],
            'rzye': [100000.0],
            'rqye': [10000.0],
            'rzrqye': [200000.0]  # 计算错误
        })

        is_valid, errors, warnings = validator.validate_margin_detail(df)

        assert is_valid is False
        assert len(errors) > 0
        assert '两融余额计算错误' in errors[0]

    def test_validate_stk_limit_valid(self, validator):
        """测试有效的涨跌停价格数据"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['2024-03-17'],
            'pre_close': [10.0],
            'up_limit': [11.0],   # 涨停价10%
            'down_limit': [9.0]    # 跌停价10%
        })

        is_valid, errors, warnings = validator.validate_stk_limit(df)

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_stk_limit_invalid_prices(self, validator):
        """测试无效的涨跌停价格"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['2024-03-17'],
            'pre_close': [10.0],
            'up_limit': [9.0],     # 涨停价小于昨收价
            'down_limit': [11.0]   # 跌停价大于昨收价
        })

        is_valid, errors, warnings = validator.validate_stk_limit(df)

        assert is_valid is False
        assert len(errors) >= 2
        assert any('涨停价格错误' in e for e in errors)
        assert any('跌停价格错误' in e for e in errors)

    def test_generate_validation_report(self, validator):
        """测试生成验证报告"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ'],
            'trade_date': ['2024-03-17', '2024-03-17'],
            'turnover_rate': [5.0, 150.0]  # 一个正常，一个异常
        })

        report = validator.generate_validation_report('daily_basic', df)

        assert report['data_type'] == 'daily_basic'
        assert report['total_records'] == 2
        assert report['status'] == 'failed'
        assert report['errors_count'] > 0
        assert 'timestamp' in report
        assert 'summary' in report

    def test_batch_validate(self, validator):
        """测试批量验证"""
        data_dict = {
            'daily_basic': pd.DataFrame({
                'ts_code': ['000001.SZ'],
                'trade_date': ['2024-03-17'],
                'turnover_rate': [5.0]
            }),
            'moneyflow': pd.DataFrame({
                'ts_code': ['000001.SZ'],
                'trade_date': ['2024-03-17'],
                'buy_sm_amount': [1000.0],
                'sell_sm_amount': [950.0],
                'net_mf_amount': [50.0]
            })
        }

        batch_report = validator.batch_validate(data_dict)

        assert batch_report['total_datasets'] == 2
        assert 'reports' in batch_report
        assert 'daily_basic' in batch_report['reports']
        assert 'moneyflow' in batch_report['reports']
        assert 'overall_status' in batch_report


if __name__ == '__main__':
    pytest.main([__file__, '-v'])