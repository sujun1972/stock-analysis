"""
Scheduler API 集成测试

测试 scheduler.py 中的所有端点：
- GET /api/scheduler/tasks - 获取所有定时任务列表
- GET /api/scheduler/tasks/{task_id} - 获取单个定时任务详情
- POST /api/scheduler/tasks - 创建定时任务
- PUT /api/scheduler/tasks/{task_id} - 更新定时任务
- DELETE /api/scheduler/tasks/{task_id} - 删除定时任务
- POST /api/scheduler/tasks/{task_id}/toggle - 切换定时任务启用状态
- GET /api/scheduler/tasks/{task_id}/history - 获取任务执行历史
- GET /api/scheduler/history/recent - 获取最近的任务执行历史

作者: Backend Team
创建日期: 2026-02-03
版本: 1.0.0
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException

from app.api.endpoints.scheduler import (
    ScheduledTaskCreate,
    ScheduledTaskUpdate,
    create_scheduled_task,
    delete_scheduled_task,
    get_recent_execution_history,
    get_scheduled_task,
    get_scheduled_tasks,
    get_task_execution_history,
    toggle_scheduled_task,
    update_scheduled_task,
)


class TestGetScheduledTasks:
    """测试 GET /api/scheduler/tasks 端点"""

    @pytest.mark.asyncio
    async def test_get_scheduled_tasks_success(self):
        """测试成功获取定时任务列表"""
        # Arrange
        mock_rows = [
            (
                1,
                "daily_sync",
                "daily",
                "每日同步",
                "0 0 * * *",
                True,
                {},
                datetime(2023, 1, 1, 10, 0),
                datetime(2023, 1, 2, 0, 0),
                "completed",
                None,
                10,
                datetime(2023, 1, 1, 0, 0),
                datetime(2023, 1, 1, 9, 0),
            ),
            (
                2,
                "stock_list_sync",
                "stock_list",
                "股票列表同步",
                "0 8 * * 1",
                False,
                {},
                None,
                None,
                None,
                None,
                0,
                datetime(2023, 1, 1, 0, 0),
                datetime(2023, 1, 1, 0, 0),
            ),
        ]

        with (
            patch("app.api.endpoints.scheduler.ConfigService") as mock_config_service,
            patch("asyncio.to_thread", new=AsyncMock(return_value=mock_rows)),
        ):

            mock_service = Mock()
            mock_config_service.return_value = mock_service

            # Act
            response = await get_scheduled_tasks()

            # Assert
            assert response["code"] == 200
            assert response["message"] == "success"
            assert len(response["data"]) == 2
            assert response["data"][0]["task_name"] == "daily_sync"
            assert response["data"][0]["enabled"] is True
            assert response["data"][1]["enabled"] is False

    @pytest.mark.asyncio
    async def test_get_scheduled_tasks_empty(self):
        """测试获取空任务列表"""
        # Arrange
        with (
            patch("app.api.endpoints.scheduler.ConfigService"),
            patch("asyncio.to_thread", new=AsyncMock(return_value=[])),
        ):

            # Act
            response = await get_scheduled_tasks()

            # Assert
            assert response["code"] == 200
            assert len(response["data"]) == 0


class TestGetScheduledTask:
    """测试 GET /api/scheduler/tasks/{task_id} 端点"""

    @pytest.mark.asyncio
    async def test_get_scheduled_task_success(self):
        """测试成功获取单个定时任务"""
        # Arrange
        task_id = 1
        mock_row = (
            1,
            "daily_sync",
            "daily",
            "每日同步",
            "0 0 * * *",
            True,
            {},
            datetime(2023, 1, 1, 10, 0),
            datetime(2023, 1, 2, 0, 0),
            "completed",
            None,
            10,
            datetime(2023, 1, 1, 0, 0),
            datetime(2023, 1, 1, 9, 0),
        )

        with (
            patch("app.api.endpoints.scheduler.ConfigService"),
            patch("asyncio.to_thread", new=AsyncMock(return_value=[mock_row])),
        ):

            # Act
            response = await get_scheduled_task(task_id=task_id)

            # Assert
            assert response["code"] == 200
            assert response["data"]["id"] == 1
            assert response["data"]["task_name"] == "daily_sync"
            assert response["data"]["enabled"] is True

    @pytest.mark.asyncio
    async def test_get_scheduled_task_not_found(self):
        """测试获取不存在的任务"""
        # Arrange
        task_id = 999

        with (
            patch("app.api.endpoints.scheduler.ConfigService"),
            patch("asyncio.to_thread", new=AsyncMock(return_value=[])),
        ):

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await get_scheduled_task(task_id=task_id)

            assert exc_info.value.status_code == 404
            assert "不存在" in str(exc_info.value.detail)


class TestCreateScheduledTask:
    """测试 POST /api/scheduler/tasks 端点"""

    @pytest.mark.asyncio
    async def test_create_scheduled_task_success(self):
        """测试成功创建定时任务"""
        # Arrange
        import time
        unique_task_name = f"test_task_{int(time.time() * 1000)}"
        request = ScheduledTaskCreate(
            task_name=unique_task_name,
            module="stock_list",
            description="测试任务",
            cron_expression="0 0 * * *",
            enabled=False,
            params={},
        )

        # Mock check for existing task (returns empty)
        # Mock insert returning new task_id
        with (
            patch("app.api.endpoints.scheduler.ConfigService"),
            patch(
                "asyncio.to_thread",
                side_effect=[
                    [],  # check query - 直接返回值而不是协程
                    [(123,)],  # insert query
                ],
            ),
        ):

            # Act
            response = await create_scheduled_task(request)

            # Assert
            assert response["code"] == 200
            assert response["data"]["id"] == 123

    @pytest.mark.asyncio
    async def test_create_scheduled_task_duplicate_name(self):
        """测试创建重名任务"""
        # Arrange
        request = ScheduledTaskCreate(
            task_name="existing_task", module="stock_list", cron_expression="0 0 * * *"
        )

        with (
            patch("app.api.endpoints.scheduler.ConfigService"),
            patch("asyncio.to_thread", new=AsyncMock(return_value=[(1,)])),
        ):

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await create_scheduled_task(request)

            assert exc_info.value.status_code == 400
            assert "已存在" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_scheduled_task_invalid_module(self):
        """测试无效模块名称"""
        # Arrange
        request = ScheduledTaskCreate(
            task_name="test_task", module="invalid_module", cron_expression="0 0 * * *"
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await create_scheduled_task(request)

        assert exc_info.value.status_code == 400
        assert "无效的模块名称" in str(exc_info.value.detail)


class TestUpdateScheduledTask:
    """测试 PUT /api/scheduler/tasks/{task_id} 端点"""

    @pytest.mark.asyncio
    async def test_update_scheduled_task_success(self):
        """测试成功更新定时任务"""
        # Arrange
        task_id = 1
        request = ScheduledTaskUpdate(description="更新后的描述", enabled=True)

        with (
            patch("app.api.endpoints.scheduler.ConfigService"),
            patch("asyncio.to_thread", new=AsyncMock()),
        ):

            # Act
            response = await update_scheduled_task(task_id=task_id, request=request)

            # Assert
            assert response["code"] == 200
            assert response["data"]["id"] == task_id

    @pytest.mark.asyncio
    async def test_update_scheduled_task_no_fields(self):
        """测试无更新字段"""
        # Arrange
        task_id = 1
        request = ScheduledTaskUpdate()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await update_scheduled_task(task_id=task_id, request=request)

        assert exc_info.value.status_code == 400
        assert "没有需要更新的字段" in str(exc_info.value.detail)


class TestDeleteScheduledTask:
    """测试 DELETE /api/scheduler/tasks/{task_id} 端点"""

    @pytest.mark.asyncio
    async def test_delete_scheduled_task_success(self):
        """测试成功删除定时任务"""
        # Arrange
        task_id = 1

        with (
            patch("app.api.endpoints.scheduler.ConfigService"),
            patch("asyncio.to_thread", new=AsyncMock()),
        ):

            # Act
            response = await delete_scheduled_task(task_id=task_id)

            # Assert
            assert response["code"] == 200
            assert response["data"]["id"] == task_id


class TestToggleScheduledTask:
    """测试 POST /api/scheduler/tasks/{task_id}/toggle 端点"""

    @pytest.mark.asyncio
    async def test_toggle_scheduled_task_enable(self):
        """测试启用定时任务"""
        # Arrange
        task_id = 1

        with (
            patch("app.api.endpoints.scheduler.ConfigService"),
            patch(
                "asyncio.to_thread",
                side_effect=[
                    [(False,)],  # get current status - 直接返回值而不是协程
                    None,  # update status
                ],
            ),
        ):

            # Act
            response = await toggle_scheduled_task(task_id=task_id)

            # Assert
            assert response["code"] == 200
            assert response["data"]["enabled"] is True

    @pytest.mark.asyncio
    async def test_toggle_scheduled_task_disable(self):
        """测试禁用定时任务"""
        # Arrange
        task_id = 1

        with (
            patch("app.api.endpoints.scheduler.ConfigService"),
            patch(
                "asyncio.to_thread",
                side_effect=[
                    [(True,)],  # get current status - 直接返回值而不是协程
                    None,  # update status
                ],
            ),
        ):

            # Act
            response = await toggle_scheduled_task(task_id=task_id)

            # Assert
            assert response["code"] == 200
            assert response["data"]["enabled"] is False

    @pytest.mark.asyncio
    async def test_toggle_scheduled_task_not_found(self):
        """测试切换不存在的任务"""
        # Arrange
        task_id = 999

        with (
            patch("app.api.endpoints.scheduler.ConfigService"),
            patch("asyncio.to_thread", new=AsyncMock(return_value=[])),
        ):

            # Act & Assert
            with pytest.raises(HTTPException) as exc_info:
                await toggle_scheduled_task(task_id=task_id)

            assert exc_info.value.status_code == 404


class TestGetTaskExecutionHistory:
    """测试 GET /api/scheduler/tasks/{task_id}/history 端点"""

    @pytest.mark.asyncio
    async def test_get_task_execution_history_success(self):
        """测试成功获取任务执行历史"""
        # Arrange
        task_id = 1
        limit = 20

        mock_rows = [
            (
                1,
                "daily_sync",
                "daily",
                "completed",
                datetime(2023, 1, 1, 10, 0),
                datetime(2023, 1, 1, 10, 30),
                1800,
                {"success": 100},
                None,
            ),
            (
                2,
                "daily_sync",
                "daily",
                "failed",
                datetime(2023, 1, 1, 9, 0),
                datetime(2023, 1, 1, 9, 5),
                300,
                None,
                "数据源错误",
            ),
        ]

        with (
            patch("app.api.endpoints.scheduler.ConfigService"),
            patch("asyncio.to_thread", new=AsyncMock(return_value=mock_rows)),
        ):

            # Act
            response = await get_task_execution_history(task_id=task_id, limit=limit)

            # Assert
            assert response["code"] == 200
            assert len(response["data"]) == 2
            assert response["data"][0]["status"] == "completed"
            assert response["data"][1]["status"] == "failed"

    @pytest.mark.asyncio
    async def test_get_task_execution_history_empty(self):
        """测试获取空执行历史"""
        # Arrange
        task_id = 1

        with (
            patch("app.api.endpoints.scheduler.ConfigService"),
            patch("asyncio.to_thread", new=AsyncMock(return_value=[])),
        ):

            # Act
            response = await get_task_execution_history(task_id=task_id)

            # Assert
            assert response["code"] == 200
            assert len(response["data"]) == 0


class TestGetRecentExecutionHistory:
    """测试 GET /api/scheduler/history/recent 端点"""

    @pytest.mark.asyncio
    async def test_get_recent_execution_history_success(self):
        """测试成功获取最近执行历史"""
        # Arrange
        limit = 50

        mock_rows = [
            (
                1,
                "daily_sync",
                "daily",
                "completed",
                datetime(2023, 1, 2, 10, 0),
                datetime(2023, 1, 2, 10, 30),
                1800,
                {"success": 100},
                None,
                "0 0 * * *",
            ),
            (
                2,
                "stock_list_sync",
                "stock_list",
                "completed",
                datetime(2023, 1, 2, 8, 0),
                datetime(2023, 1, 2, 8, 5),
                300,
                {"total": 5000},
                None,
                "0 8 * * 1",
            ),
            (
                3,
                "realtime_sync",
                "realtime",
                "failed",
                datetime(2023, 1, 2, 15, 0),
                datetime(2023, 1, 2, 15, 2),
                120,
                None,
                "网络超时",
                "*/5 * * * *",
            ),
        ]

        with (
            patch("app.api.endpoints.scheduler.ConfigService"),
            patch("asyncio.to_thread", new=AsyncMock(return_value=mock_rows)),
        ):

            # Act
            response = await get_recent_execution_history(limit=limit)

            # Assert
            assert response["code"] == 200
            assert len(response["data"]) == 3
            assert response["data"][0]["task_name"] == "daily_sync"
            assert response["data"][2]["status"] == "failed"

    @pytest.mark.asyncio
    async def test_get_recent_execution_history_with_limit(self):
        """测试限制返回数量"""
        # Arrange
        limit = 10

        mock_rows = [
            (
                i,
                f"task_{i}",
                "daily",
                "completed",
                datetime(2023, 1, 1, 10, 0),
                datetime(2023, 1, 1, 10, 30),
                1800,
                {},
                None,
                "0 0 * * *",
            )
            for i in range(10)
        ]

        with (
            patch("app.api.endpoints.scheduler.ConfigService"),
            patch("asyncio.to_thread", new=AsyncMock(return_value=mock_rows)),
        ):

            # Act
            response = await get_recent_execution_history(limit=limit)

            # Assert
            assert response["code"] == 200
            assert len(response["data"]) == 10
