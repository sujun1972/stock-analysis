"""
扩展数据API接口集成测试
"""

import pytest
import asyncio
from datetime import datetime, date
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd
import json

# 导入待测试模块
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../'))


class TestExtendedDataAPI:
    """扩展数据API测试类"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from backend.app.main import app
        return TestClient(app)

    @pytest.fixture
    def mock_db_session(self):
        """创建模拟的数据库会话"""
        session = AsyncMock()
        return session

    @pytest.fixture
    def auth_headers(self):
        """创建认证头"""
        # 模拟已认证的用户token
        return {
            "Authorization": "Bearer test_token_123"
        }

    @pytest.fixture
    def sample_daily_basic_records(self):
        """创建示例每日指标记录"""
        return [
            {
                'ts_code': '000001.SZ',
                'trade_date': '2024-03-17',
                'close': 12.34,
                'turnover_rate': 2.34,
                'turnover_rate_f': 2.12,
                'volume_ratio': 1.23,
                'pe': 15.6,
                'pe_ttm': 16.2,
                'pb': 1.2,
                'ps': 2.3,
                'ps_ttm': 2.4,
                'dv_ratio': 1.2,
                'dv_ttm': 1.3,
                'total_share': 10000.0,
                'float_share': 8000.0,
                'free_share': 6000.0,
                'total_mv': 123400.0,
                'circ_mv': 98720.0
            }
        ]

    def test_get_daily_basic_success(self, client, mock_db_session, sample_daily_basic_records):
        """测试获取每日指标成功"""
        # Mock数据库查询结果
        mock_result = Mock()
        mock_result.fetchall = Mock(return_value=[
            Mock(
                ts_code='000001.SZ',
                trade_date=date(2024, 3, 17),
                close=12.34,
                turnover_rate=2.34,
                turnover_rate_f=2.12,
                volume_ratio=1.23,
                pe=15.6,
                pe_ttm=16.2,
                pb=1.2,
                ps=2.3,
                ps_ttm=2.4,
                dv_ratio=1.2,
                dv_ttm=1.3,
                total_share=10000.0,
                float_share=8000.0,
                free_share=6000.0,
                total_mv=123400.0,
                circ_mv=98720.0
            )
        ])

        with patch('backend.app.api.endpoints.extended_data.get_async_db') as mock_get_db:
            mock_db_session.execute = AsyncMock(return_value=mock_result)
            mock_get_db.return_value = mock_db_session

            response = client.get(
                "/api/v1/extended/daily-basic/000001.SZ",
                params={
                    "start_date": "2024-03-01",
                    "end_date": "2024-03-17",
                    "limit": 100
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data['code'] == 0
            assert 'data' in data
            assert len(data['data']) > 0
            assert data['data'][0]['ts_code'] == '000001.SZ'

    def test_get_daily_basic_invalid_code(self, client):
        """测试无效的股票代码"""
        with patch('backend.app.api.endpoints.extended_data.get_async_db') as mock_get_db:
            mock_result = Mock()
            mock_result.fetchall = Mock(return_value=[])

            mock_db_session = AsyncMock()
            mock_db_session.execute = AsyncMock(return_value=mock_result)
            mock_get_db.return_value = mock_db_session

            response = client.get("/api/v1/extended/daily-basic/INVALID")

            assert response.status_code == 200
            data = response.json()
            assert data['code'] == 0
            assert len(data['data']) == 0

    def test_get_moneyflow_success(self, client):
        """测试获取资金流向成功"""
        mock_result = Mock()
        mock_result.fetchall = Mock(return_value=[
            Mock(
                ts_code='000001.SZ',
                trade_date=date(2024, 3, 17),
                buy_sm_vol=1000000,
                buy_sm_amount=1234.56,
                sell_sm_vol=900000,
                sell_sm_amount=1123.45,
                buy_md_vol=500000,
                buy_md_amount=2345.67,
                sell_md_vol=450000,
                sell_md_amount=2234.56,
                buy_lg_vol=300000,
                buy_lg_amount=3456.78,
                sell_lg_vol=280000,
                sell_lg_amount=3345.67,
                buy_elg_vol=200000,
                buy_elg_amount=4567.89,
                sell_elg_vol=190000,
                sell_elg_amount=4456.78,
                net_mf_vol=80000,
                net_mf_amount=456.78,
                trade_count=12345
            )
        ])

        with patch('backend.app.api.endpoints.extended_data.get_async_db') as mock_get_db:
            mock_db_session = AsyncMock()
            mock_db_session.execute = AsyncMock(return_value=mock_result)
            mock_get_db.return_value = mock_db_session

            response = client.get(
                "/api/v1/extended/moneyflow/000001.SZ",
                params={"limit": 100}
            )

            assert response.status_code == 200
            data = response.json()
            assert data['code'] == 0
            assert 'data' in data
            assert len(data['data']) > 0

    def test_get_hk_hold_success(self, client):
        """测试获取北向资金成功"""
        mock_result = Mock()
        mock_result.fetchall = Mock(return_value=[
            Mock(
                code='000001',
                trade_date=date(2024, 3, 17),
                ts_code='000001.SZ',
                name='平安银行',
                vol=100000000,
                ratio=1.23,
                exchange='SZ'
            )
        ])

        with patch('backend.app.api.endpoints.extended_data.get_async_db') as mock_get_db:
            mock_db_session = AsyncMock()
            mock_db_session.execute = AsyncMock(return_value=mock_result)
            mock_get_db.return_value = mock_db_session

            response = client.get(
                "/api/v1/extended/hk-hold",
                params={
                    "trade_date": "2024-03-17",
                    "exchange": "SZ",
                    "top": 50
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data['code'] == 0
            assert 'data' in data

    def test_get_margin_detail_success(self, client):
        """测试获取融资融券数据成功"""
        mock_result = Mock()
        mock_result.fetchall = Mock(return_value=[
            Mock(
                ts_code='000001.SZ',
                trade_date=date(2024, 3, 17),
                rzye=123456.78,
                rqye=12345.67,
                rzmre=34567.89,
                rqyl=1000000,
                rzche=23456.78,
                rqchl=900000,
                rqmcl=100000,
                rzrqye=135802.45
            )
        ])

        with patch('backend.app.api.endpoints.extended_data.get_async_db') as mock_get_db:
            mock_db_session = AsyncMock()
            mock_db_session.execute = AsyncMock(return_value=mock_result)
            mock_get_db.return_value = mock_db_session

            response = client.get(
                "/api/v1/extended/margin/000001.SZ",
                params={"limit": 100}
            )

            assert response.status_code == 200
            data = response.json()
            assert data['code'] == 0
            assert 'data' in data

    def test_get_limit_prices_success(self, client):
        """测试获取涨跌停价格成功"""
        mock_result = Mock()
        mock_result.fetchall = Mock(return_value=[
            Mock(
                ts_code='000001.SZ',
                trade_date=date(2024, 3, 17),
                pre_close=10.0,
                up_limit=11.0,
                down_limit=9.0
            )
        ])

        with patch('backend.app.api.endpoints.extended_data.get_async_db') as mock_get_db:
            mock_db_session = AsyncMock()
            mock_db_session.execute = AsyncMock(return_value=mock_result)
            mock_get_db.return_value = mock_db_session

            response = client.get(
                "/api/v1/extended/limit-prices",
                params={"trade_date": "2024-03-17"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data['code'] == 0
            assert 'data' in data

    def test_get_block_trade_success(self, client):
        """测试获取大宗交易数据成功"""
        mock_result = Mock()
        mock_result.fetchall = Mock(return_value=[
            Mock(
                id=1,
                ts_code='000001.SZ',
                trade_date=date(2024, 3, 17),
                price=12.34,
                vol=1000.0,
                amount=12340.0,
                buyer='机构A',
                seller='机构B'
            )
        ])

        with patch('backend.app.api.endpoints.extended_data.get_async_db') as mock_get_db:
            mock_db_session = AsyncMock()
            mock_db_session.execute = AsyncMock(return_value=mock_result)
            mock_get_db.return_value = mock_db_session

            response = client.get(
                "/api/v1/extended/block-trade",
                params={
                    "trade_date": "2024-03-17",
                    "ts_code": "000001.SZ"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data['code'] == 0
            assert 'data' in data

    def test_trigger_sync_success(self, client, auth_headers):
        """测试触发同步任务成功"""
        with patch('backend.app.api.endpoints.extended_data.sync_daily_basic_task') as mock_task:
            mock_result = Mock()
            mock_result.id = 'task_123456'
            mock_task.delay = Mock(return_value=mock_result)

            with patch('backend.app.api.endpoints.extended_data.get_current_user'):
                response = client.post(
                    "/api/v1/extended/sync/trigger",
                    params={
                        "data_type": "daily_basic",
                        "trade_date": "20240317"
                    },
                    headers=auth_headers
                )

                assert response.status_code == 200
                data = response.json()
                assert data['code'] == 0
                assert data['data']['task_id'] == 'task_123456'
                assert data['msg'] == '同步任务已提交'

    def test_trigger_sync_invalid_type(self, client, auth_headers):
        """测试触发同步任务 - 无效类型"""
        with patch('backend.app.api.endpoints.extended_data.get_current_user'):
            response = client.post(
                "/api/v1/extended/sync/trigger",
                params={
                    "data_type": "invalid_type",
                    "trade_date": "20240317"
                },
                headers=auth_headers
            )

            assert response.status_code == 400
            assert '不支持的数据类型' in response.json()['detail']

    def test_get_sync_status_success(self, client):
        """测试获取同步任务状态成功"""
        with patch('backend.app.api.endpoints.extended_data.AsyncResult') as mock_async_result:
            mock_result = Mock()
            mock_result.state = 'SUCCESS'
            mock_result.result = {'records': 100, 'status': 'success'}
            mock_result.info = None
            mock_async_result.return_value = mock_result

            response = client.get("/api/v1/extended/sync/status/task_123456")

            assert response.status_code == 200
            data = response.json()
            assert data['code'] == 0
            assert data['data']['state'] == 'SUCCESS'
            assert data['data']['result']['records'] == 100

    def test_get_data_summary_success(self, client):
        """测试获取数据统计摘要成功"""
        # Mock多个数据表的统计结果
        mock_results = [
            Mock(stock_count=100, latest_date=date(2024, 3, 17), total_records=10000),
            Mock(stock_count=50, latest_date=date(2024, 3, 17), total_records=5000),
            Mock(stock_count=200, latest_date=date(2024, 3, 17), total_records=20000),
            Mock(stock_count=150, latest_date=date(2024, 3, 17), total_records=15000)
        ]

        with patch('backend.app.api.endpoints.extended_data.get_async_db') as mock_get_db:
            mock_db_session = AsyncMock()

            # 设置每次查询返回不同的结果
            mock_db_session.execute = AsyncMock(side_effect=[
                Mock(fetchone=Mock(return_value=mock_results[0])),
                Mock(fetchone=Mock(return_value=mock_results[1])),
                Mock(fetchone=Mock(return_value=mock_results[2])),
                Mock(fetchone=Mock(return_value=mock_results[3]))
            ])

            mock_get_db.return_value = mock_db_session

            response = client.get("/api/v1/extended/stats/summary")

            assert response.status_code == 200
            data = response.json()
            assert data['code'] == 0
            assert 'data' in data
            assert 'daily_basic' in data['data']
            assert 'moneyflow' in data['data']
            assert 'hk_hold' in data['data']
            assert 'margin_detail' in data['data']

    def test_api_error_handling(self, client):
        """测试API错误处理"""
        with patch('backend.app.api.endpoints.extended_data.get_async_db') as mock_get_db:
            mock_db_session = AsyncMock()
            mock_db_session.execute = AsyncMock(side_effect=Exception('Database error'))
            mock_get_db.return_value = mock_db_session

            response = client.get("/api/v1/extended/daily-basic/000001.SZ")

            assert response.status_code == 500
            assert 'Database error' in response.json()['detail']

    def test_pagination_parameters(self, client):
        """测试分页参数"""
        mock_result = Mock()
        # 创建多条记录用于测试分页
        mock_records = []
        for i in range(150):
            mock_records.append(Mock(
                ts_code=f'00000{i}.SZ',
                trade_date=date(2024, 3, 17),
                close=10.0 + i * 0.1,
                turnover_rate=2.0 + i * 0.01,
                turnover_rate_f=2.0,
                volume_ratio=1.0,
                pe=15.0,
                pe_ttm=15.0,
                pb=1.5,
                ps=2.0,
                ps_ttm=2.0,
                dv_ratio=1.0,
                dv_ttm=1.0,
                total_share=10000.0,
                float_share=8000.0,
                free_share=6000.0,
                total_mv=100000.0,
                circ_mv=80000.0
            ))

        # 只返回前100条（limit限制）
        mock_result.fetchall = Mock(return_value=mock_records[:100])

        with patch('backend.app.api.endpoints.extended_data.get_async_db') as mock_get_db:
            mock_db_session = AsyncMock()
            mock_db_session.execute = AsyncMock(return_value=mock_result)
            mock_get_db.return_value = mock_db_session

            response = client.get(
                "/api/v1/extended/daily-basic/000001.SZ",
                params={"limit": 100}  # 测试limit参数
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data['data']) <= 100  # 确保不超过limit

    def test_date_range_filtering(self, client):
        """测试日期范围过滤"""
        mock_result = Mock()
        mock_result.fetchall = Mock(return_value=[
            Mock(
                ts_code='000001.SZ',
                trade_date=date(2024, 3, 15),
                close=12.34,
                turnover_rate=2.34,
                turnover_rate_f=2.12,
                volume_ratio=1.23,
                pe=15.6,
                pe_ttm=16.2,
                pb=1.2,
                ps=2.3,
                ps_ttm=2.4,
                dv_ratio=1.2,
                dv_ttm=1.3,
                total_share=10000.0,
                float_share=8000.0,
                free_share=6000.0,
                total_mv=123400.0,
                circ_mv=98720.0
            )
        ])

        with patch('backend.app.api.endpoints.extended_data.get_async_db') as mock_get_db:
            mock_db_session = AsyncMock()
            mock_db_session.execute = AsyncMock(return_value=mock_result)
            mock_get_db.return_value = mock_db_session

            response = client.get(
                "/api/v1/extended/daily-basic/000001.SZ",
                params={
                    "start_date": "2024-03-01",
                    "end_date": "2024-03-31"
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data['code'] == 0
            # 验证返回的数据在日期范围内
            if data['data']:
                assert data['data'][0]['trade_date'] >= '2024-03-01'
                assert data['data'][0]['trade_date'] <= '2024-03-31'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])