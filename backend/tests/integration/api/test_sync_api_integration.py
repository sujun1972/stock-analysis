"""
Sync API 集成测试

测试 sync.py 中的所有端点：
- GET /api/sync/status - 获取同步状态
- GET /api/sync/status/{module} - 获取模块同步状态
- POST /api/sync/abort - 中止同步
- POST /api/sync/stock-list - 同步股票列表
- POST /api/sync/new-stocks - 同步新股列表
- POST /api/sync/delisted-stocks - 同步退市股票
- POST /api/sync/daily/batch - 批量同步日线数据
- POST /api/sync/daily/{code} - 同步单只股票日线数据
- POST /api/sync/minute/{code} - 同步分时数据
- POST /api/sync/realtime - 同步实时行情
- GET /api/sync/history - 获取同步历史记录

作者: Backend Team
创建日期: 2026-02-03
版本: 1.0.0
"""

import pytest
from unittest.mock import AsyncMock, patch, Mock
from fastapi import HTTPException

from app.api.endpoints.sync import (
    get_sync_status,
    get_module_sync_status,
    abort_sync,
    sync_stock_list,
    sync_new_stocks,
    sync_delisted_stocks,
    sync_daily_batch,
    sync_daily_stock,
    sync_minute_data,
    sync_realtime_quotes,
    get_sync_history
)
from app.api.endpoints.sync import (
    SyncDailyBatchRequest,
    SyncMinuteRequest,
    SyncRealtimeRequest,
    SyncNewStocksRequest
)


class TestGetSyncStatus:
    """测试 GET /api/sync/status 端点"""

    @pytest.mark.asyncio
    async def test_get_sync_status_success(self):
        """测试成功获取同步状态"""
        # Arrange
        mock_status = {
            'status': 'running',
            'progress': 50,
            'total': 100,
            'completed': 50,
            'last_sync_date': '2023-01-01 10:00:00'
        }

        with patch('app.api.endpoints.sync.ConfigService') as mock_config_service:
            mock_service = Mock()
            mock_service.get_sync_status = AsyncMock(return_value=mock_status)
            mock_config_service.return_value = mock_service

            # Act
            response = await get_sync_status()

            # Assert
            assert response['code'] == 200
            assert response['message'] == 'success'
            assert response['data'] == mock_status

    @pytest.mark.asyncio
    async def test_get_sync_status_idle(self):
        """测试获取空闲状态"""
        # Arrange
        mock_status = {
            'status': 'idle',
            'progress': 0,
            'total': 0,
            'completed': 0,
            'last_sync_date': ''
        }

        with patch('app.api.endpoints.sync.ConfigService') as mock_config_service:
            mock_service = Mock()
            mock_service.get_sync_status = AsyncMock(return_value=mock_status)
            mock_config_service.return_value = mock_service

            # Act
            response = await get_sync_status()

            # Assert
            assert response['data']['status'] == 'idle'


class TestGetModuleSyncStatus:
    """测试 GET /api/sync/status/{module} 端点"""

    @pytest.mark.asyncio
    async def test_get_module_sync_status_success(self):
        """测试成功获取模块同步状态"""
        # Arrange
        module = 'stock_list'
        mock_status = {
            'module': module,
            'last_sync_at': '2023-01-01 10:00:00',
            'status': 'completed'
        }

        with patch('app.api.endpoints.sync.ConfigService') as mock_config_service:
            mock_service = Mock()
            mock_service.get_module_sync_status = AsyncMock(return_value=mock_status)
            mock_config_service.return_value = mock_service

            # Act
            response = await get_module_sync_status(module=module)

            # Assert
            assert response['code'] == 200
            assert response['data']['module'] == module

    @pytest.mark.asyncio
    async def test_get_module_sync_status_invalid_module(self):
        """测试无效模块名称"""
        # Arrange
        module = 'invalid_module'

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_module_sync_status(module=module)

        assert exc_info.value.status_code == 400
        assert '无效的模块名称' in str(exc_info.value.detail)


class TestAbortSync:
    """测试 POST /api/sync/abort 端点"""

    @pytest.mark.asyncio
    async def test_abort_sync_success(self):
        """测试成功中止同步"""
        # Arrange
        mock_status = {'status': 'running'}

        with patch('app.api.endpoints.sync.ConfigService') as mock_config_service:
            mock_service = Mock()
            mock_service.get_sync_status = AsyncMock(return_value=mock_status)
            mock_service.set_sync_abort_flag = AsyncMock()
            mock_config_service.return_value = mock_service

            # Act
            response = await abort_sync()

            # Assert
            assert response['code'] == 200
            assert '中止请求已发送' in response['message']
            mock_service.set_sync_abort_flag.assert_called_once_with(True)

    @pytest.mark.asyncio
    async def test_abort_sync_no_running_task(self):
        """测试没有运行中的任务"""
        # Arrange
        mock_status = {'status': 'idle'}

        with patch('app.api.endpoints.sync.ConfigService') as mock_config_service:
            mock_service = Mock()
            mock_service.get_sync_status = AsyncMock(return_value=mock_status)
            mock_config_service.return_value = mock_service

            # Act
            response = await abort_sync()

            # Assert
            assert response['code'] == 400
            assert '没有正在运行的同步任务' in response['message']


class TestSyncStockList:
    """测试 POST /api/sync/stock-list 端点"""

    @pytest.mark.asyncio
    async def test_sync_stock_list_success(self):
        """测试成功同步股票列表"""
        # Arrange
        mock_result = {'total': 5000}

        with patch('app.api.endpoints.sync.StockListSyncService') as mock_service_class:
            mock_service = Mock()
            mock_service.sync_stock_list = AsyncMock(return_value=mock_result)
            mock_service_class.return_value = mock_service

            # Act
            response = await sync_stock_list()

            # Assert
            assert response['code'] == 200
            assert response['data']['total'] == 5000
            mock_service.sync_stock_list.assert_called_once()


class TestSyncNewStocks:
    """测试 POST /api/sync/new-stocks 端点"""

    @pytest.mark.asyncio
    async def test_sync_new_stocks_success(self):
        """测试成功同步新股列表"""
        # Arrange
        request = SyncNewStocksRequest(days=30)
        mock_result = {'total': 10}

        with patch('app.api.endpoints.sync.StockListSyncService') as mock_service_class:
            mock_service = Mock()
            mock_service.sync_new_stocks = AsyncMock(return_value=mock_result)
            mock_service_class.return_value = mock_service

            # Act
            response = await sync_new_stocks(request)

            # Assert
            assert response['code'] == 200
            assert response['data']['total'] == 10
            mock_service.sync_new_stocks.assert_called_once_with(days=30)


class TestSyncDelistedStocks:
    """测试 POST /api/sync/delisted-stocks 端点"""

    @pytest.mark.asyncio
    async def test_sync_delisted_stocks_success(self):
        """测试成功同步退市股票"""
        # Arrange
        mock_result = {'total': 5}

        with patch('app.api.endpoints.sync.StockListSyncService') as mock_service_class:
            mock_service = Mock()
            mock_service.sync_delisted_stocks = AsyncMock(return_value=mock_result)
            mock_service_class.return_value = mock_service

            # Act
            response = await sync_delisted_stocks()

            # Assert
            assert response['code'] == 200
            assert response['data']['total'] == 5


class TestSyncDailyBatch:
    """测试 POST /api/sync/daily/batch 端点"""

    @pytest.mark.asyncio
    async def test_sync_daily_batch_success(self):
        """测试成功批量同步日线数据"""
        # Arrange
        request = SyncDailyBatchRequest(
            codes=['000001', '000002'],
            years=5
        )
        mock_result = {
            'total': 2,
            'success': 2,
            'failed': 0,
            'aborted': False
        }

        with patch('app.api.endpoints.sync.DailySyncService') as mock_service_class:
            mock_service = Mock()
            mock_service.sync_batch = AsyncMock(return_value=mock_result)
            mock_service_class.return_value = mock_service

            # Act
            response = await sync_daily_batch(request)

            # Assert
            assert response['code'] == 200
            assert response['data']['total'] == 2
            assert response['data']['success'] == 2

    @pytest.mark.asyncio
    async def test_sync_daily_batch_aborted(self):
        """测试同步被中止"""
        # Arrange
        request = SyncDailyBatchRequest(codes=['000001', '000002'])
        mock_result = {
            'total': 2,
            'success': 1,
            'failed': 0,
            'aborted': True
        }

        with patch('app.api.endpoints.sync.DailySyncService') as mock_service_class:
            mock_service = Mock()
            mock_service.sync_batch = AsyncMock(return_value=mock_result)
            mock_service_class.return_value = mock_service

            # Act
            response = await sync_daily_batch(request)

            # Assert
            assert response['code'] == 200
            assert response['message'] == '同步已中止'
            assert response['data']['aborted'] is True


class TestSyncDailyStock:
    """测试 POST /api/sync/daily/{code} 端点"""

    @pytest.mark.asyncio
    async def test_sync_daily_stock_success(self):
        """测试成功同步单只股票"""
        # Arrange
        code = '000001'
        years = 5
        mock_result = {'code': code, 'records': 1200}

        with patch('app.api.endpoints.sync.DailySyncService') as mock_service_class:
            mock_service = Mock()
            mock_service.sync_single_stock = AsyncMock(return_value=mock_result)
            mock_service_class.return_value = mock_service

            # Act
            response = await sync_daily_stock(code=code, years=years)

            # Assert
            assert response['code'] == 200
            assert response['data']['code'] == code
            assert response['data']['records'] == 1200


class TestSyncMinuteData:
    """测试 POST /api/sync/minute/{code} 端点"""

    @pytest.mark.asyncio
    async def test_sync_minute_data_success(self):
        """测试成功同步分时数据"""
        # Arrange
        code = '000001'
        request = SyncMinuteRequest(period='5', days=5)
        mock_result = {'code': code, 'period': '5', 'records': 240}

        with patch('app.api.endpoints.sync.RealtimeSyncService') as mock_service_class:
            mock_service = Mock()
            mock_service.sync_minute_data = AsyncMock(return_value=mock_result)
            mock_service_class.return_value = mock_service

            # Act
            response = await sync_minute_data(code=code, request=request)

            # Assert
            assert response['code'] == 200
            assert response['data']['code'] == code
            assert response['data']['records'] == 240


class TestSyncRealtimeQuotes:
    """测试 POST /api/sync/realtime 端点"""

    @pytest.mark.asyncio
    async def test_sync_realtime_quotes_success(self):
        """测试成功同步实时行情"""
        # Arrange
        request = SyncRealtimeRequest(
            codes=['000001', '000002'],
            batch_size=100,
            update_oldest=False
        )
        mock_result = {
            'total': 2,
            'success': 2,
            'failed': 0,
            'partial_success': False
        }

        with patch('app.api.endpoints.sync.RealtimeSyncService') as mock_service_class:
            mock_service = Mock()
            mock_service.sync_realtime_quotes = AsyncMock(return_value=mock_result)
            mock_service_class.return_value = mock_service

            # Act
            response = await sync_realtime_quotes(request)

            # Assert
            assert response['code'] == 200
            assert response['data']['success'] == 2

    @pytest.mark.asyncio
    async def test_sync_realtime_quotes_partial_success(self):
        """测试部分成功同步实时行情"""
        # Arrange
        request = SyncRealtimeRequest(codes=['000001', '000002'])
        mock_result = {
            'total': 2,
            'success': 1,
            'failed': 1,
            'partial_success': True
        }

        with patch('app.api.endpoints.sync.RealtimeSyncService') as mock_service_class:
            mock_service = Mock()
            mock_service.sync_realtime_quotes = AsyncMock(return_value=mock_result)
            mock_service_class.return_value = mock_service

            # Act
            response = await sync_realtime_quotes(request)

            # Assert
            assert response['code'] == 206  # Partial Content
            assert response['message'] == 'partial_success'


class TestGetSyncHistory:
    """测试 GET /api/sync/history 端点"""

    @pytest.mark.asyncio
    async def test_get_sync_history_success(self):
        """测试成功获取同步历史"""
        # Arrange
        limit = 20
        offset = 0

        # Act
        response = await get_sync_history(limit=limit, offset=offset)

        # Assert
        assert response['code'] == 200
        assert 'data' in response
        assert isinstance(response['data'], list)

    @pytest.mark.asyncio
    async def test_get_sync_history_with_pagination(self):
        """测试分页获取同步历史"""
        # Arrange
        limit = 10
        offset = 10

        # Act
        response = await get_sync_history(limit=limit, offset=offset)

        # Assert
        assert response['code'] == 200
        assert isinstance(response['data'], list)
