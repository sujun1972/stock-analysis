"""
扩展数据同步服务集成测试
测试同步服务的完整功能流程
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import pandas as pd

from backend.app.services.extended_sync_service import ExtendedDataSyncService


class TestExtendedDataSyncService:
    """扩展数据同步服务测试类"""

    @pytest.fixture
    async def service(self):
        """创建服务实例"""
        service = ExtendedDataSyncService()
        return service

    @pytest.fixture
    def mock_provider(self):
        """创建模拟数据提供者"""
        provider = Mock()

        # 模拟每日指标数据
        provider.get_daily_basic = Mock(return_value=pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ'],
            'trade_date': ['20240315', '20240315'],
            'turnover_rate': [5.5, 8.2],
            'pe': [15.5, 20.3],
            'pb': [2.1, 3.5],
            'total_mv': [10000000, 8000000],
            'circ_mv': [8000000, 6000000]
        }))

        # 模拟资金流向数据
        provider.get_moneyflow = Mock(return_value=pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240315'],
            'buy_sm_amount': [1000],
            'buy_md_amount': [2000],
            'buy_lg_amount': [3000],
            'buy_elg_amount': [4000],
            'sell_sm_amount': [900],
            'sell_md_amount': [2100],
            'sell_lg_amount': [2900],
            'sell_elg_amount': [4100],
            'net_mf_amount': [0]
        }))

        # 模拟北向资金数据
        provider.get_hk_hold = Mock(return_value=pd.DataFrame({
            'code': ['000001', '000002'],
            'trade_date': ['20240315', '20240315'],
            'vol': [1000000, 2000000],
            'ratio': [5.5, 8.2],
            'exchange': ['SH', 'SH']
        }))

        # 模拟融资融券数据
        provider.get_margin_detail = Mock(return_value=pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240315'],
            'rzye': [1000000],
            'rqye': [500000],
            'rzrqye': [1500000]
        }))

        # 模拟涨跌停价格数据
        provider.get_stk_limit = Mock(return_value=pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240315'],
            'pre_close': [10.0],
            'up_limit': [11.0],
            'down_limit': [9.0]
        }))

        return provider

    @pytest.mark.asyncio
    async def test_sync_daily_basic(self, service, mock_provider):
        """测试每日指标同步"""
        with patch.object(service, '_get_provider', return_value=mock_provider):
            with patch.object(service, '_insert_daily_basic', new_callable=AsyncMock):
                result = await service.sync_daily_basic(trade_date="20240315")

                assert result['status'] == 'success'
                assert result['records'] == 2
                assert 'validation_errors' in result
                assert 'validation_warnings' in result

                # 验证数据提供者被调用
                mock_provider.get_daily_basic.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_daily_basic_with_validation_errors(self, service, mock_provider):
        """测试每日指标同步带验证错误的情况"""
        # 创建包含错误数据的DataFrame
        df_with_errors = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240315'],
            'turnover_rate': [150],  # 超过100%
            'total_mv': [5000000],
            'circ_mv': [8000000]  # 流通市值大于总市值
        })
        mock_provider.get_daily_basic = Mock(return_value=df_with_errors)

        with patch.object(service, '_get_provider', return_value=mock_provider):
            with patch.object(service, '_insert_daily_basic', new_callable=AsyncMock):
                result = await service.sync_daily_basic(trade_date="20240315")

                assert result['status'] == 'success'
                assert result['records'] == 1
                # 数据应该被修复

    @pytest.mark.asyncio
    async def test_sync_moneyflow(self, service, mock_provider):
        """测试资金流向同步"""
        with patch.object(service, '_get_provider', return_value=mock_provider):
            with patch.object(service, '_get_active_stocks', new_callable=AsyncMock,
                            return_value=['000001.SZ']):
                with patch.object(service, '_insert_moneyflow', new_callable=AsyncMock):
                    result = await service.sync_moneyflow(trade_date="20240315")

                    assert result['status'] == 'success'
                    assert result['records'] > 0

    @pytest.mark.asyncio
    async def test_sync_moneyflow_with_specific_stocks(self, service, mock_provider):
        """测试指定股票列表的资金流向同步"""
        stock_list = ['000001.SZ', '000002.SZ']

        with patch.object(service, '_get_provider', return_value=mock_provider):
            with patch.object(service, '_insert_moneyflow', new_callable=AsyncMock):
                result = await service.sync_moneyflow(
                    trade_date="20240315",
                    stock_list=stock_list
                )

                assert result['status'] == 'success'
                # 验证每只股票都被调用
                assert mock_provider.get_moneyflow.call_count == len(stock_list)

    @pytest.mark.asyncio
    async def test_sync_hk_hold(self, service, mock_provider):
        """测试北向资金同步"""
        with patch.object(service, '_get_provider', return_value=mock_provider):
            with patch.object(service, '_insert_hk_hold', new_callable=AsyncMock):
                result = await service.sync_hk_hold(trade_date="20240315")

                assert result['status'] == 'success'
                assert result['records'] > 0

                # 验证沪深两个交易所都被调用
                assert mock_provider.get_hk_hold.call_count == 2

    @pytest.mark.asyncio
    async def test_sync_margin_detail(self, service, mock_provider):
        """测试融资融券同步"""
        with patch.object(service, '_get_provider', return_value=mock_provider):
            with patch.object(service, '_insert_margin_detail', new_callable=AsyncMock):
                result = await service.sync_margin_detail(trade_date="20240315")

                assert result['status'] == 'success'
                assert result['records'] == 1

    @pytest.mark.asyncio
    async def test_sync_stk_limit(self, service, mock_provider):
        """测试涨跌停价格同步"""
        with patch.object(service, '_get_provider', return_value=mock_provider):
            with patch.object(service, '_insert_stk_limit', new_callable=AsyncMock):
                result = await service.sync_stk_limit(trade_date="20240315")

                assert result['status'] == 'success'
                assert result['records'] == 1

    @pytest.mark.asyncio
    async def test_sync_with_empty_data(self, service):
        """测试空数据的处理"""
        mock_provider = Mock()
        mock_provider.get_daily_basic = Mock(return_value=None)

        with patch.object(service, '_get_provider', return_value=mock_provider):
            result = await service.sync_daily_basic(trade_date="20240315")

            assert result['status'] == 'success'
            assert result['records'] == 0
            assert '无数据需要同步' in result['message']

    @pytest.mark.asyncio
    async def test_sync_with_exception(self, service):
        """测试异常处理"""
        mock_provider = Mock()
        mock_provider.get_daily_basic = Mock(side_effect=Exception("API Error"))

        with patch.object(service, '_get_provider', return_value=mock_provider):
            result = await service.sync_daily_basic(trade_date="20240315")

            assert result['status'] == 'error'
            assert 'error' in result
            assert 'API Error' in result['error']

    @pytest.mark.asyncio
    async def test_concurrent_sync(self, service, mock_provider):
        """测试并发同步"""
        with patch.object(service, '_get_provider', return_value=mock_provider):
            with patch.object(service, '_insert_daily_basic', new_callable=AsyncMock):
                with patch.object(service, '_insert_hk_hold', new_callable=AsyncMock):
                    # 并发执行多个同步任务
                    tasks = [
                        service.sync_daily_basic(trade_date="20240315"),
                        service.sync_hk_hold(trade_date="20240315")
                    ]

                    results = await asyncio.gather(*tasks)

                    # 验证所有任务都成功
                    assert all(r['status'] == 'success' for r in results)

    @pytest.mark.asyncio
    async def test_date_range_sync(self, service, mock_provider):
        """测试日期范围同步"""
        with patch.object(service, '_get_provider', return_value=mock_provider):
            with patch.object(service, '_insert_daily_basic', new_callable=AsyncMock):
                result = await service.sync_daily_basic(
                    start_date="20240301",
                    end_date="20240315"
                )

                assert result['status'] == 'success'
                mock_provider.get_daily_basic.assert_called_with(
                    trade_date=None,
                    start_date="20240301",
                    end_date="20240315"
                )


class TestDataValidationIntegration:
    """数据验证集成测试"""

    @pytest.mark.asyncio
    async def test_validation_fixes_data(self):
        """测试验证器修复数据"""
        service = ExtendedDataSyncService()

        # 创建包含错误的数据
        bad_data = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240315'],
            'turnover_rate': [200],  # 需要修复
            'pe': [15.5],
            'total_mv': [5000000],
            'circ_mv': [8000000]  # 需要修复
        })

        mock_provider = Mock()
        mock_provider.get_daily_basic = Mock(return_value=bad_data)

        with patch.object(service, '_get_provider', return_value=mock_provider):
            with patch.object(service, '_insert_daily_basic', new_callable=AsyncMock) as mock_insert:
                await service.sync_daily_basic(trade_date="20240315")

                # 获取插入的数据
                inserted_df = mock_insert.call_args[0][0]

                # 验证数据已被修复
                assert inserted_df['turnover_rate'].iloc[0] <= 100
                assert inserted_df['circ_mv'].iloc[0] <= inserted_df['total_mv'].iloc[0]


class TestPerformanceOptimization:
    """性能优化测试"""

    @pytest.mark.asyncio
    async def test_batch_processing(self):
        """测试批量处理"""
        service = ExtendedDataSyncService()

        # 创建大量数据
        large_df = pd.DataFrame({
            'ts_code': [f'{i:06d}.SZ' for i in range(5000)],
            'trade_date': ['20240315'] * 5000,
            'turnover_rate': [5.5] * 5000
        })

        mock_provider = Mock()
        mock_provider.get_daily_basic = Mock(return_value=large_df)

        with patch.object(service, '_get_provider', return_value=mock_provider):
            with patch.object(service, '_insert_daily_basic', new_callable=AsyncMock) as mock_insert:
                start_time = datetime.now()
                await service.sync_daily_basic(trade_date="20240315")
                duration = (datetime.now() - start_time).total_seconds()

                # 验证处理时间合理
                assert duration < 10  # 应该在10秒内完成
                assert mock_insert.called

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """测试请求频率限制"""
        service = ExtendedDataSyncService()

        stock_list = [f'{i:06d}.SZ' for i in range(10)]

        mock_provider = Mock()
        mock_provider.get_moneyflow = Mock(return_value=pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240315'],
            'net_mf_amount': [1000]
        }))

        with patch.object(service, '_get_provider', return_value=mock_provider):
            with patch.object(service, '_insert_moneyflow', new_callable=AsyncMock):
                start_time = datetime.now()
                await service.sync_moneyflow(
                    trade_date="20240315",
                    stock_list=stock_list
                )
                duration = (datetime.now() - start_time).total_seconds()

                # 验证有适当的延迟（每个请求0.5秒）
                assert duration >= (len(stock_list) - 1) * 0.5


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])