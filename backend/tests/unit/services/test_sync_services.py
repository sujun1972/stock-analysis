"""
Sync Services 单元测试

测试同步服务模块：
- DailySyncService: 日线数据同步
- StockListSyncService: 股票列表同步
- RealtimeSyncService: 实时行情同步
- SyncStatusManager: 同步状态管理

作者: Backend Team
创建日期: 2026-02-03
版本: 1.0.0
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from datetime import datetime, timedelta
import pandas as pd

from app.services.daily_sync_service import DailySyncService
from app.services.stock_list_sync_service import StockListSyncService
from app.services.realtime_sync_service import RealtimeSyncService
from app.services.sync_status_manager import SyncStatusManager


# ==================== DailySyncService Tests ====================

class TestDailySyncServiceInit:
    """测试 DailySyncService 初始化"""

    def test_init_with_defaults(self):
        """测试默认初始化"""
        # Act
        service = DailySyncService()

        # Assert
        assert service.config_service is not None
        assert service.data_service is not None


class TestSyncSingleStock:
    """测试单只股票日线数据同步"""

    @pytest.mark.asyncio
    async def test_sync_single_stock_success(self):
        """测试成功同步单只股票"""
        # Arrange
        service = DailySyncService()
        code = '000001'
        years = 5

        mock_config = {
            'data_source': 'akshare',
            'tushare_token': ''
        }

        mock_df = pd.DataFrame({
            'date': ['2023-01-01', '2023-01-02'],
            'open': [10.0, 10.5],
            'close': [10.5, 11.0],
            'high': [10.8, 11.2],
            'low': [9.8, 10.2],
            'volume': [1000000, 1100000]
        })

        with patch.object(service.config_service, 'get_data_source_config', new=AsyncMock(return_value=mock_config)), \
             patch('app.services.daily_sync_service.DataProviderFactory.create_provider') as mock_provider_factory, \
             patch('asyncio.to_thread', new=AsyncMock(return_value=mock_df)) as mock_to_thread:

            mock_provider = Mock()
            mock_provider.get_daily_data = Mock(return_value=mock_df)
            mock_provider_factory.return_value = mock_provider

            # Mock save_daily_data to return count
            with patch.object(service.data_service.db, 'save_daily_data', return_value=2):
                # Act
                result = await service.sync_single_stock(code=code, years=years)

                # Assert
                assert result['code'] == code
                assert result['records'] == 2
                mock_provider_factory.assert_called_once_with(source='akshare', token='')

    @pytest.mark.asyncio
    async def test_sync_single_stock_timeout(self):
        """测试同步超时"""
        # Arrange
        service = DailySyncService()
        code = '000001'

        mock_config = {'data_source': 'akshare', 'tushare_token': ''}

        with patch.object(service.config_service, 'get_data_source_config', new=AsyncMock(return_value=mock_config)), \
             patch('app.services.daily_sync_service.DataProviderFactory.create_provider'), \
             patch('asyncio.wait_for', side_effect=TimeoutError(f"{code}: 数据获取超时")):

            # Act & Assert
            with pytest.raises(TimeoutError, match="数据获取超时"):
                await service.sync_single_stock(code=code, years=5)

    @pytest.mark.asyncio
    async def test_sync_single_stock_no_data(self):
        """测试无数据情况"""
        # Arrange
        service = DailySyncService()
        code = '999999'

        mock_config = {'data_source': 'akshare', 'tushare_token': ''}
        empty_df = pd.DataFrame()

        with patch.object(service.config_service, 'get_data_source_config', new=AsyncMock(return_value=mock_config)), \
             patch('app.services.daily_sync_service.DataProviderFactory.create_provider'), \
             patch('asyncio.to_thread', new=AsyncMock(return_value=empty_df)):

            # Act & Assert
            with pytest.raises(ValueError, match="无数据"):
                await service.sync_single_stock(code=code, years=5)


class TestSyncBatch:
    """测试批量同步日线数据"""

    @pytest.mark.asyncio
    async def test_sync_batch_with_codes(self):
        """测试批量同步指定股票"""
        # Arrange
        service = DailySyncService()
        codes = ['000001', '000002']

        mock_config = {'data_source': 'akshare', 'tushare_token': ''}
        mock_df = pd.DataFrame({'date': ['2023-01-01'], 'close': [10.0]})

        with patch.object(service.config_service, 'get_data_source_config', new=AsyncMock(return_value=mock_config)), \
             patch.object(service.config_service, 'clear_sync_abort_flag', new=AsyncMock()), \
             patch.object(service.config_service, 'update_sync_status', new=AsyncMock()), \
             patch.object(service.config_service, 'check_sync_abort', new=AsyncMock(return_value=False)), \
             patch('app.services.daily_sync_service.DataProviderFactory.create_provider'), \
             patch('asyncio.to_thread', new=AsyncMock(return_value=mock_df)), \
             patch.object(service.data_service.db, 'save_daily_data', return_value=1):

            # Act
            result = await service.sync_batch(codes=codes, years=5)

            # Assert
            assert result['total'] == 2
            assert result['success'] == 2
            assert result['failed'] == 0

    @pytest.mark.asyncio
    async def test_sync_batch_abort(self):
        """测试同步中止"""
        # Arrange
        service = DailySyncService()
        codes = ['000001', '000002', '000003']

        mock_config = {'data_source': 'akshare', 'tushare_token': ''}

        # Mock check_sync_abort to return True after first stock
        abort_calls = [False, True]

        with patch.object(service.config_service, 'get_data_source_config', new=AsyncMock(return_value=mock_config)), \
             patch.object(service.config_service, 'clear_sync_abort_flag', new=AsyncMock()), \
             patch.object(service.config_service, 'update_sync_status', new=AsyncMock()), \
             patch.object(service.config_service, 'check_sync_abort', new=AsyncMock(side_effect=abort_calls)):

            # Act
            result = await service.sync_batch(codes=codes, years=5)

            # Assert
            assert result['aborted'] is True
            assert result['total'] == 3


# ==================== StockListSyncService Tests ====================

class TestStockListSyncServiceInit:
    """测试 StockListSyncService 初始化"""

    def test_init_with_defaults(self):
        """测试默认初始化"""
        # Act
        service = StockListSyncService()

        # Assert
        assert service.config_service is not None
        assert service.data_service is not None


class TestSyncStockList:
    """测试同步股票列表"""

    @pytest.mark.asyncio
    async def test_sync_stock_list_success(self):
        """测试成功同步股票列表"""
        # Arrange
        service = StockListSyncService()

        mock_config = {'data_source': 'akshare', 'tushare_token': ''}
        mock_stock_list = pd.DataFrame({
            'code': ['000001', '000002'],
            'name': ['平安银行', '万科A'],
            'market': ['主板', '主板']
        })

        task_id = f"stock_list_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        with patch.object(service.config_service, 'get_data_source_config', new=AsyncMock(return_value=mock_config)), \
             patch.object(service.config_service, 'create_sync_task', new=AsyncMock()), \
             patch.object(service.config_service, 'update_sync_task', new=AsyncMock()), \
             patch.object(service.config_service, 'update_sync_status', new=AsyncMock()), \
             patch('app.services.stock_list_sync_service.DataProviderFactory.create_provider') as mock_provider_factory, \
             patch('app.utils.retry.retry_async', new=AsyncMock(return_value=mock_stock_list)), \
             patch('asyncio.to_thread', new=AsyncMock(return_value=2)):

            mock_provider = Mock()
            mock_provider_factory.return_value = mock_provider

            # Act
            result = await service.sync_stock_list()

            # Assert
            assert result['total'] == 2
            service.config_service.create_sync_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_stock_list_failure(self):
        """测试同步股票列表失败"""
        # Arrange
        service = StockListSyncService()

        mock_config = {'data_source': 'akshare', 'tushare_token': ''}

        with patch.object(service.config_service, 'get_data_source_config', new=AsyncMock(return_value=mock_config)), \
             patch.object(service.config_service, 'create_sync_task', new=AsyncMock()), \
             patch.object(service.config_service, 'update_sync_task', new=AsyncMock()), \
             patch.object(service.config_service, 'update_sync_status', new=AsyncMock()), \
             patch('app.services.stock_list_sync_service.DataProviderFactory.create_provider'), \
             patch('app.utils.retry.retry_async', new=AsyncMock(side_effect=Exception("网络错误"))):

            # Act & Assert
            with pytest.raises(Exception, match="网络错误"):
                await service.sync_stock_list()


class TestSyncNewStocks:
    """测试同步新股列表"""

    @pytest.mark.asyncio
    async def test_sync_new_stocks_success(self):
        """测试成功同步新股列表"""
        # Arrange
        service = StockListSyncService()
        days = 30

        mock_config = {'data_source': 'akshare', 'tushare_token': ''}
        mock_new_stocks = pd.DataFrame({
            'code': ['301234', '301235'],
            'name': ['新股A', '新股B']
        })

        with patch.object(service.config_service, 'get_data_source_config', new=AsyncMock(return_value=mock_config)), \
             patch.object(service.config_service, 'create_sync_task', new=AsyncMock()), \
             patch.object(service.config_service, 'update_sync_task', new=AsyncMock()), \
             patch.object(service.config_service, 'update_sync_status', new=AsyncMock()), \
             patch('app.services.stock_list_sync_service.DataProviderFactory.create_provider'), \
             patch('app.utils.retry.retry_async', new=AsyncMock(return_value=mock_new_stocks)), \
             patch('asyncio.to_thread', new=AsyncMock(return_value=2)):

            # Act
            result = await service.sync_new_stocks(days=days)

            # Assert
            assert result['total'] == 2


class TestSyncDelistedStocks:
    """测试同步退市股票列表"""

    @pytest.mark.asyncio
    async def test_sync_delisted_stocks_success(self):
        """测试成功同步退市股票列表"""
        # Arrange
        service = StockListSyncService()

        mock_config = {'data_source': 'akshare', 'tushare_token': ''}
        mock_delisted = pd.DataFrame({
            'code': ['000123', '000124'],
            'name': ['退市A', '退市B']
        })

        with patch.object(service.config_service, 'get_data_source_config', new=AsyncMock(return_value=mock_config)), \
             patch.object(service.config_service, 'create_sync_task', new=AsyncMock()), \
             patch.object(service.config_service, 'update_sync_task', new=AsyncMock()), \
             patch.object(service.config_service, 'update_sync_status', new=AsyncMock()), \
             patch('app.services.stock_list_sync_service.DataProviderFactory.create_provider'), \
             patch('app.utils.retry.retry_async', new=AsyncMock(return_value=mock_delisted)), \
             patch('asyncio.to_thread', new=AsyncMock(return_value=2)):

            # Act
            result = await service.sync_delisted_stocks()

            # Assert
            assert result['total'] == 2


# ==================== RealtimeSyncService Tests ====================

class TestRealtimeSyncServiceInit:
    """测试 RealtimeSyncService 初始化"""

    def test_init_with_defaults(self):
        """测试默认初始化"""
        # Act
        service = RealtimeSyncService()

        # Assert
        assert service.config_service is not None
        assert service.data_service is not None


class TestSyncMinuteData:
    """测试同步分时数据"""

    @pytest.mark.asyncio
    async def test_sync_minute_data_success(self):
        """测试成功同步分时数据"""
        # Arrange
        service = RealtimeSyncService()
        code = '000001'
        period = '5'
        days = 5

        mock_config = {
            'data_source': 'akshare',
            'minute_data_source': 'akshare',
            'tushare_token': ''
        }

        mock_df = pd.DataFrame({
            'time': ['2023-01-01 09:30', '2023-01-01 09:35'],
            'open': [10.0, 10.5],
            'close': [10.5, 11.0]
        })

        with patch.object(service.config_service, 'get_data_source_config', new=AsyncMock(return_value=mock_config)), \
             patch('app.services.realtime_sync_service.DataProviderFactory.create_provider') as mock_provider_factory, \
             patch('asyncio.to_thread', new=AsyncMock(return_value=mock_df)):

            mock_provider = Mock()
            mock_provider_factory.return_value = mock_provider

            # Act
            result = await service.sync_minute_data(code=code, period=period, days=days)

            # Assert
            assert result['code'] == code
            assert result['period'] == period
            assert result['records'] == 2

    @pytest.mark.asyncio
    async def test_sync_minute_data_no_data(self):
        """测试无分时数据"""
        # Arrange
        service = RealtimeSyncService()
        code = '999999'

        mock_config = {'minute_data_source': 'akshare', 'tushare_token': ''}
        empty_df = pd.DataFrame()

        with patch.object(service.config_service, 'get_data_source_config', new=AsyncMock(return_value=mock_config)), \
             patch('app.services.realtime_sync_service.DataProviderFactory.create_provider'), \
             patch('asyncio.to_thread', new=AsyncMock(return_value=empty_df)):

            # Act & Assert
            with pytest.raises(ValueError, match="无分时数据"):
                await service.sync_minute_data(code=code, period='5', days=5)


class TestSyncRealtimeQuotes:
    """测试同步实时行情"""

    @pytest.mark.asyncio
    async def test_sync_realtime_quotes_with_codes(self):
        """测试同步指定股票实时行情"""
        # Arrange
        service = RealtimeSyncService()
        codes = ['000001', '000002']

        mock_config = {
            'data_source': 'akshare',
            'realtime_data_source': 'akshare',
            'tushare_token': ''
        }

        mock_df = pd.DataFrame({
            'code': codes,
            'name': ['平安银行', '万科A'],
            'price': [10.0, 20.0]
        })

        with patch.object(service.config_service, 'get_data_source_config', new=AsyncMock(return_value=mock_config)), \
             patch('app.services.realtime_sync_service.DataProviderFactory.create_provider'), \
             patch('asyncio.wait_for', new=AsyncMock(return_value=mock_df)), \
             patch('asyncio.to_thread', new=AsyncMock(return_value=2)):

            # Act
            result = await service.sync_realtime_quotes(codes=codes, batch_size=100)

            # Assert
            assert 'success' in result or 'total' in result

    @pytest.mark.asyncio
    async def test_sync_realtime_quotes_timeout(self):
        """测试实时行情同步超时"""
        # Arrange
        service = RealtimeSyncService()
        codes = ['000001']

        mock_config = {'realtime_data_source': 'akshare', 'tushare_token': ''}

        with patch.object(service.config_service, 'get_data_source_config', new=AsyncMock(return_value=mock_config)), \
             patch('app.services.realtime_sync_service.DataProviderFactory.create_provider'), \
             patch('asyncio.wait_for', side_effect=TimeoutError("超时")):

            # Act
            result = await service.sync_realtime_quotes(codes=codes)

            # Assert - 应该返回部分成功结果
            assert 'partial_success' in result or 'error' in str(result).lower()


# ==================== SyncStatusManager Tests ====================

class TestSyncStatusManagerInit:
    """测试 SyncStatusManager 初始化"""

    def test_init_with_defaults(self):
        """测试默认初始化"""
        # Act
        manager = SyncStatusManager()

        # Assert
        assert manager.db is not None
        assert manager.config_repo is not None

    def test_init_with_custom_db(self):
        """测试自定义数据库初始化"""
        # Arrange
        mock_db = Mock()

        # Act
        manager = SyncStatusManager(db=mock_db)

        # Assert
        assert manager.db == mock_db


class TestGetSyncStatus:
    """测试获取同步状态"""

    @pytest.mark.asyncio
    async def test_get_sync_status_success(self):
        """测试成功获取同步状态"""
        # Arrange
        manager = SyncStatusManager()

        mock_configs = {
            'sync_status': 'running',
            'last_sync_date': '2023-01-01 10:00:00',
            'sync_progress': '50',
            'sync_total': '100',
            'sync_completed': '50'
        }

        with patch('asyncio.to_thread', new=AsyncMock(return_value=mock_configs)):
            # Act
            result = await manager.get_sync_status()

            # Assert
            assert result['status'] == 'running'
            assert result['progress'] == 50
            assert result['total'] == 100
            assert result['completed'] == 50

    @pytest.mark.asyncio
    async def test_get_sync_status_default_values(self):
        """测试获取同步状态（默认值）"""
        # Arrange
        manager = SyncStatusManager()

        with patch('asyncio.to_thread', new=AsyncMock(return_value={})):
            # Act
            result = await manager.get_sync_status()

            # Assert
            assert result['status'] == 'idle'
            assert result['progress'] == 0
            assert result['total'] == 0


class TestUpdateSyncStatus:
    """测试更新同步状态"""

    @pytest.mark.asyncio
    async def test_update_sync_status_success(self):
        """测试成功更新同步状态"""
        # Arrange
        manager = SyncStatusManager()

        with patch('asyncio.to_thread', new=AsyncMock()), \
             patch.object(manager, 'get_sync_status', new=AsyncMock(return_value={
                 'status': 'running',
                 'progress': 50,
                 'total': 100,
                 'completed': 50,
                 'last_sync_date': '2023-01-01 10:00:00'
             })):

            # Act
            result = await manager.update_sync_status(
                status='running',
                progress=50,
                total=100,
                completed=50
            )

            # Assert
            assert result['status'] == 'running'
            assert result['progress'] == 50
