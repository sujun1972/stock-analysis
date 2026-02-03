"""
Config API 集成测试

测试 config.py 中的所有端点：
- GET /api/config/source - 获取数据源配置
- POST /api/config/source - 更新数据源配置
- GET /api/config/all - 获取所有系统配置
- GET /api/config/sync-status - 获取同步状态

作者: Backend Team
创建日期: 2026-02-03
版本: 1.0.0
"""

import pytest
from unittest.mock import AsyncMock, patch, Mock

from app.api.endpoints.config import (
    get_data_source_config,
    update_data_source_config,
    get_all_configs,
    get_sync_status
)
from app.api.endpoints.config import DataSourceConfigRequest


class TestGetDataSourceConfig:
    """测试 GET /api/config/source 端点"""

    @pytest.mark.asyncio
    async def test_get_data_source_config_success(self):
        """测试成功获取数据源配置"""
        # Arrange
        mock_config = {
            'data_source': 'akshare',
            'minute_data_source': 'akshare',
            'realtime_data_source': 'akshare',
            'tushare_token': ''
        }

        with patch('app.api.endpoints.config.ConfigService') as mock_config_service:
            mock_service = Mock()
            mock_service.get_data_source_config = AsyncMock(return_value=mock_config)
            mock_config_service.return_value = mock_service

            # Act
            response = await get_data_source_config()

            # Assert
            assert response.code == 200
            assert response.message == 'success'
            assert response.data['data_source'] == 'akshare'
            mock_service.get_data_source_config.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_data_source_config_with_tushare(self):
        """测试获取Tushare数据源配置"""
        # Arrange
        mock_config = {
            'data_source': 'tushare',
            'minute_data_source': 'tushare',
            'realtime_data_source': 'akshare',
            'tushare_token': 'test_token_123'
        }

        with patch('app.api.endpoints.config.ConfigService') as mock_config_service:
            mock_service = Mock()
            mock_service.get_data_source_config = AsyncMock(return_value=mock_config)
            mock_config_service.return_value = mock_service

            # Act
            response = await get_data_source_config()

            # Assert
            assert response.data['data_source'] == 'tushare'
            assert response.data['tushare_token'] == 'test_token_123'


class TestUpdateDataSourceConfig:
    """测试 POST /api/config/source 端点"""

    @pytest.mark.asyncio
    async def test_update_data_source_config_success(self):
        """测试成功更新数据源配置"""
        # Arrange
        request = DataSourceConfigRequest(
            data_source='akshare',
            minute_data_source='akshare',
            realtime_data_source='akshare'
        )

        mock_updated_config = {
            'data_source': 'akshare',
            'minute_data_source': 'akshare',
            'realtime_data_source': 'akshare',
            'tushare_token': ''
        }

        with patch('app.api.endpoints.config.ConfigService') as mock_config_service:
            mock_service = Mock()
            mock_service.update_data_source = AsyncMock(return_value=mock_updated_config)
            mock_config_service.return_value = mock_service

            # Act
            response = await update_data_source_config(request)

            # Assert
            assert response.code == 200
            assert '成功切换数据源' in response.message
            assert response.data['data_source'] == 'akshare'
            mock_service.update_data_source.assert_called_once_with(
                data_source='akshare',
                minute_data_source='akshare',
                realtime_data_source='akshare',
                tushare_token=None
            )

    @pytest.mark.asyncio
    async def test_update_data_source_config_to_tushare(self):
        """测试切换到Tushare数据源"""
        # Arrange
        request = DataSourceConfigRequest(
            data_source='tushare',
            minute_data_source='tushare',
            realtime_data_source='akshare',
            tushare_token='test_token_456'
        )

        mock_updated_config = {
            'data_source': 'tushare',
            'minute_data_source': 'tushare',
            'realtime_data_source': 'akshare',
            'tushare_token': 'test_token_456'
        }

        with patch('app.api.endpoints.config.ConfigService') as mock_config_service:
            mock_service = Mock()
            mock_service.update_data_source = AsyncMock(return_value=mock_updated_config)
            mock_config_service.return_value = mock_service

            # Act
            response = await update_data_source_config(request)

            # Assert
            assert response.code == 200
            assert response.data['data_source'] == 'tushare'
            assert response.data['tushare_token'] == 'test_token_456'

    @pytest.mark.asyncio
    async def test_update_data_source_config_partial_update(self):
        """测试部分更新数据源配置"""
        # Arrange
        request = DataSourceConfigRequest(
            data_source='akshare',
            minute_data_source=None,  # 不更新分时数据源
            realtime_data_source=None  # 不更新实时数据源
        )

        mock_updated_config = {
            'data_source': 'akshare',
            'minute_data_source': 'tushare',  # 保持原值
            'realtime_data_source': 'akshare',  # 保持原值
            'tushare_token': ''
        }

        with patch('app.api.endpoints.config.ConfigService') as mock_config_service:
            mock_service = Mock()
            mock_service.update_data_source = AsyncMock(return_value=mock_updated_config)
            mock_config_service.return_value = mock_service

            # Act
            response = await update_data_source_config(request)

            # Assert
            assert response.code == 200
            assert response.data['data_source'] == 'akshare'


class TestGetAllConfigs:
    """测试 GET /api/config/all 端点"""

    @pytest.mark.asyncio
    async def test_get_all_configs_success(self):
        """测试成功获取所有配置"""
        # Arrange
        mock_all_configs = {
            'data_source': 'akshare',
            'minute_data_source': 'akshare',
            'realtime_data_source': 'akshare',
            'tushare_token': '',
            'sync_status': 'idle',
            'last_sync_date': '2023-01-01 10:00:00',
            'sync_progress': 0,
            'api_rate_limit': '100/minute',
            'database_pool_size': '10'
        }

        with patch('app.api.endpoints.config.ConfigService') as mock_config_service:
            mock_service = Mock()
            mock_service.get_all_configs = AsyncMock(return_value=mock_all_configs)
            mock_config_service.return_value = mock_service

            # Act
            response = await get_all_configs()

            # Assert
            assert response.code == 200
            assert response.message == 'success'
            assert 'data_source' in response.data
            assert 'sync_status' in response.data
            assert response.data['data_source'] == 'akshare'
            mock_service.get_all_configs.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_configs_empty(self):
        """测试获取空配置"""
        # Arrange
        with patch('app.api.endpoints.config.ConfigService') as mock_config_service:
            mock_service = Mock()
            mock_service.get_all_configs = AsyncMock(return_value={})
            mock_config_service.return_value = mock_service

            # Act
            response = await get_all_configs()

            # Assert
            assert response.code == 200
            assert response.data == {}


class TestGetSyncStatus:
    """测试 GET /api/config/sync-status 端点"""

    @pytest.mark.asyncio
    async def test_get_sync_status_success(self):
        """测试成功获取同步状态"""
        # Arrange
        mock_status = {
            'status': 'running',
            'progress': 50,
            'total': 100,
            'completed': 50,
            'last_sync_date': '2023-01-01 10:00:00',
            'current_stock': '000001'
        }

        with patch('app.api.endpoints.config.ConfigService') as mock_config_service:
            mock_service = Mock()
            mock_service.get_sync_status = AsyncMock(return_value=mock_status)
            mock_config_service.return_value = mock_service

            # Act
            response = await get_sync_status()

            # Assert
            assert response.code == 200
            assert response.message == 'success'
            assert response.data['status'] == 'running'
            assert response.data['progress'] == 50
            assert response.data['total'] == 100
            mock_service.get_sync_status.assert_called_once()

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

        with patch('app.api.endpoints.config.ConfigService') as mock_config_service:
            mock_service = Mock()
            mock_service.get_sync_status = AsyncMock(return_value=mock_status)
            mock_config_service.return_value = mock_service

            # Act
            response = await get_sync_status()

            # Assert
            assert response.code == 200
            assert response.data['status'] == 'idle'
            assert response.data['progress'] == 0

    @pytest.mark.asyncio
    async def test_get_sync_status_completed(self):
        """测试获取已完成状态"""
        # Arrange
        mock_status = {
            'status': 'completed',
            'progress': 100,
            'total': 5000,
            'completed': 5000,
            'last_sync_date': '2023-01-01 12:00:00'
        }

        with patch('app.api.endpoints.config.ConfigService') as mock_config_service:
            mock_service = Mock()
            mock_service.get_sync_status = AsyncMock(return_value=mock_status)
            mock_config_service.return_value = mock_service

            # Act
            response = await get_sync_status()

            # Assert
            assert response.code == 200
            assert response.data['status'] == 'completed'
            assert response.data['progress'] == 100
            assert response.data['completed'] == 5000

    @pytest.mark.asyncio
    async def test_get_sync_status_failed(self):
        """测试获取失败状态"""
        # Arrange
        mock_status = {
            'status': 'failed',
            'progress': 30,
            'total': 100,
            'completed': 30,
            'last_sync_date': '2023-01-01 10:30:00',
            'error_message': '网络连接超时'
        }

        with patch('app.api.endpoints.config.ConfigService') as mock_config_service:
            mock_service = Mock()
            mock_service.get_sync_status = AsyncMock(return_value=mock_status)
            mock_config_service.return_value = mock_service

            # Act
            response = await get_sync_status()

            # Assert
            assert response.code == 200
            assert response.data['status'] == 'failed'
            assert 'error_message' in response.data
