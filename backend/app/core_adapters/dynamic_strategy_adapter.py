"""
动态代码策略适配器 (Dynamic Strategy Adapter)

将 Core v6.0 的动态代码策略包装为异步方法，供 FastAPI 使用。

动态代码策略特点:
- 动态加载 Python 代码
- 支持 AI 生成策略
- 自动安全验证（AST 分析、权限检查、资源限制）

作者: Backend Team
创建日期: 2026-02-09
版本: 1.0.0
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

# 添加 core 项目到 Python 路径
core_path = Path(__file__).parent.parent.parent.parent / "core"
if str(core_path) not in sys.path:
    sys.path.insert(0, str(core_path))

# 导入 Core 模块
from src.strategies import StrategyFactory
from src.strategies.base_strategy import BaseStrategy

from app.core.exceptions import AdapterError, SecurityError
from app.repositories.dynamic_strategy_repository import DynamicStrategyRepository


class DynamicStrategyAdapter:
    """
    动态代码策略适配器

    包装 Core 的 StrategyFactory，支持从数据库动态代码创建策略。

    示例:
        >>> adapter = DynamicStrategyAdapter()
        >>> strategy = await adapter.create_strategy_from_code(strategy_id=1)
        >>> metadata = await adapter.get_strategy_metadata(strategy_id=1)
    """

    def __init__(self):
        """初始化动态代码策略适配器"""
        self.factory = StrategyFactory()
        self.repo = DynamicStrategyRepository()

    async def create_strategy_from_code(
        self,
        strategy_id: int,
        strict_mode: bool = True
    ) -> BaseStrategy:
        """
        从动态代码创建策略（异步）

        Args:
            strategy_id: 策略ID
            strict_mode: 严格模式（任何安全问题都拒绝）

        Returns:
            策略实例

        Raises:
            AdapterError: 策略不存在或已禁用
            SecurityError: 安全验证失败
        """

        def _create():
            # 从数据库加载策略
            strategy_data = self.repo.get_by_id(strategy_id)

            if not strategy_data:
                raise AdapterError(
                    f"策略不存在",
                    error_code="STRATEGY_NOT_FOUND",
                    strategy_id=strategy_id
                )

            if not strategy_data['is_enabled']:
                raise AdapterError(
                    f"策略已禁用",
                    error_code="STRATEGY_DISABLED",
                    strategy_id=strategy_id,
                    strategy_name=strategy_data['strategy_name']
                )

            # 检查验证状态
            validation_status = strategy_data['validation_status']
            if validation_status == 'failed':
                raise SecurityError(
                    f"策略验证失败",
                    error_code="VALIDATION_FAILED",
                    strategy_id=strategy_id,
                    strategy_name=strategy_data['strategy_name'],
                    validation_errors=strategy_data.get('validation_errors')
                )

            try:
                # 调用 Core 的 StrategyFactory
                # Core 会自动进行安全验证
                strategy = self.factory.create_from_code(
                    strategy_id=strategy_id,
                    strict_mode=strict_mode
                )

                logger.info(
                    f"成功创建动态代码策略: "
                    f"strategy_id={strategy_id}, "
                    f"name={strategy_data['strategy_name']}, "
                    f"class={strategy_data['class_name']}"
                )

                return strategy

            except SecurityError:
                # 重新抛出安全错误
                raise
            except Exception as e:
                logger.error(f"创建动态代码策略失败: {e}")
                raise AdapterError(
                    f"创建策略失败",
                    error_code="STRATEGY_CREATION_FAILED",
                    strategy_id=strategy_id,
                    error_message=str(e)
                )

        return await asyncio.to_thread(_create)

    async def get_strategy_metadata(self, strategy_id: int) -> Dict[str, Any]:
        """
        获取策略元信息（异步）

        包括安全审计信息、验证状态、测试结果等。

        Args:
            strategy_id: 策略ID

        Returns:
            元信息字典

        Raises:
            AdapterError: 策略不存在
        """

        def _get_metadata():
            strategy_data = self.repo.get_by_id(strategy_id)

            if not strategy_data:
                raise AdapterError(
                    f"策略不存在",
                    error_code="STRATEGY_NOT_FOUND",
                    strategy_id=strategy_id
                )

            return {
                'strategy_id': strategy_id,
                'strategy_name': strategy_data['strategy_name'],
                'display_name': strategy_data.get('display_name'),
                'description': strategy_data.get('description'),
                'class_name': strategy_data['class_name'],
                'validation_status': strategy_data['validation_status'],
                'validation_errors': strategy_data.get('validation_errors'),
                'validation_warnings': strategy_data.get('validation_warnings'),
                'test_status': strategy_data.get('test_status'),
                'test_results': strategy_data.get('test_results'),
                'code_hash': strategy_data['code_hash'],
                'is_enabled': strategy_data['is_enabled'],
                'status': strategy_data['status'],
                'last_backtest_metrics': strategy_data.get('last_backtest_metrics'),
                'last_backtest_date': strategy_data.get('last_backtest_date'),
                'ai_model': strategy_data.get('ai_model'),
                'created_by': strategy_data.get('created_by'),
                'created_at': strategy_data.get('created_at'),
                'updated_at': strategy_data.get('updated_at'),
            }

        return await asyncio.to_thread(_get_metadata)

    async def get_strategy_code(self, strategy_id: int) -> Dict[str, Any]:
        """
        获取策略代码（异步）

        Args:
            strategy_id: 策略ID

        Returns:
            包含代码和相关信息的字典

        Raises:
            AdapterError: 策略不存在
        """

        def _get_code():
            strategy_data = self.repo.get_by_id(strategy_id)

            if not strategy_data:
                raise AdapterError(
                    f"策略不存在",
                    error_code="STRATEGY_NOT_FOUND",
                    strategy_id=strategy_id
                )

            return {
                'strategy_id': strategy_id,
                'strategy_name': strategy_data['strategy_name'],
                'class_name': strategy_data['class_name'],
                'generated_code': strategy_data['generated_code'],
                'code_hash': strategy_data['code_hash'],
                'user_prompt': strategy_data.get('user_prompt'),
                'ai_model': strategy_data.get('ai_model'),
                'validation_status': strategy_data['validation_status'],
            }

        return await asyncio.to_thread(_get_code)

    async def list_strategies(
        self,
        validation_status: Optional[str] = None,
        is_enabled: Optional[bool] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        获取动态策略列表（异步）

        Args:
            validation_status: 验证状态过滤
            is_enabled: 是否启用过滤
            status: 状态过滤
            page: 页码
            page_size: 每页数量

        Returns:
            包含 items 和 meta 的字典
        """

        def _list():
            return self.repo.list(
                validation_status=validation_status,
                is_enabled=is_enabled,
                status=status,
                page=page,
                page_size=page_size
            )

        return await asyncio.to_thread(_list)

    async def validate_strategy_code(self, code: str) -> Dict[str, Any]:
        """
        验证策略代码（异步）

        使用 Core 的安全验证机制进行代码检查。

        Args:
            code: Python 策略代码

        Returns:
            验证结果字典，包含:
                - is_valid: 是否有效
                - status: 验证状态 (passed, warning, failed)
                - errors: 错误列表
                - warnings: 警告列表
                - security_issues: 安全问题列表
        """

        def _validate():
            try:
                # 导入 Core 的安全验证模块
                from src.strategies.security import CodeValidator

                validator = CodeValidator()
                result = validator.validate_code(code)

                return {
                    'is_valid': result.get('is_valid', False),
                    'status': result.get('status', 'pending'),
                    'errors': result.get('errors', []),
                    'warnings': result.get('warnings', []),
                    'security_issues': result.get('security_issues', []),
                }

            except ImportError:
                logger.warning("Core 的 CodeValidator 不可用，使用简单验证")
                # 简单的语法检查
                try:
                    compile(code, '<string>', 'exec')
                    return {
                        'is_valid': True,
                        'status': 'passed',
                        'errors': [],
                        'warnings': ['使用简单验证，建议升级 Core 版本'],
                        'security_issues': [],
                    }
                except SyntaxError as e:
                    return {
                        'is_valid': False,
                        'status': 'failed',
                        'errors': [{'type': 'SyntaxError', 'message': str(e)}],
                        'warnings': [],
                        'security_issues': [],
                    }

        return await asyncio.to_thread(_validate)

    async def update_validation_status(
        self,
        strategy_id: int,
        validation_status: str,
        validation_errors: Optional[Dict] = None,
        validation_warnings: Optional[Dict] = None
    ) -> int:
        """
        更新验证状态（异步）

        Args:
            strategy_id: 策略ID
            validation_status: 验证状态
            validation_errors: 验证错误
            validation_warnings: 验证警告

        Returns:
            受影响的行数
        """

        def _update():
            return self.repo.update_validation_status(
                strategy_id=strategy_id,
                validation_status=validation_status,
                validation_errors=validation_errors,
                validation_warnings=validation_warnings
            )

        return await asyncio.to_thread(_update)

    async def check_strategy_name_exists(
        self,
        strategy_name: str,
        exclude_id: Optional[int] = None
    ) -> bool:
        """
        检查策略名称是否已存在（异步）

        Args:
            strategy_name: 策略名称
            exclude_id: 排除的策略ID（用于更新时检查）

        Returns:
            是否存在
        """

        def _check():
            return self.repo.check_name_exists(strategy_name, exclude_id)

        return await asyncio.to_thread(_check)

    async def get_strategy_statistics(self) -> Dict[str, Any]:
        """
        获取动态策略统计信息（异步）

        Returns:
            统计信息字典，包含:
                - total_count: 总数
                - enabled_count: 启用数量
                - validation_passed: 验证通过数量
                - validation_failed: 验证失败数量
                - by_status: 按状态分组统计
        """

        def _get_statistics():
            # 获取所有策略（不分页）
            all_strategies = self.repo.list(page=1, page_size=10000)
            items = all_strategies['items']

            total_count = len(items)
            enabled_count = sum(1 for s in items if s['is_enabled'])
            validation_passed = sum(
                1 for s in items if s['validation_status'] == 'passed'
            )
            validation_failed = sum(
                1 for s in items if s['validation_status'] == 'failed'
            )

            # 按状态分组
            by_status = {}
            for item in items:
                status = item['status']
                by_status[status] = by_status.get(status, 0) + 1

            return {
                'total_count': total_count,
                'enabled_count': enabled_count,
                'disabled_count': total_count - enabled_count,
                'validation_passed': validation_passed,
                'validation_failed': validation_failed,
                'validation_pending': total_count - validation_passed - validation_failed,
                'by_status': by_status,
            }

        return await asyncio.to_thread(_get_statistics)
