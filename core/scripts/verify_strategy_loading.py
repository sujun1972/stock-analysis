"""
验证策略加载功能

测试从数据库加载策略代码并动态实例化策略类
"""

import sys
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
from loguru import logger
import importlib.util
import tempfile

# 添加core/src到Python路径
CORE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CORE_DIR / 'src'))
# 同时添加src作为模块路径(用于src.utils.response导入)
sys.path.insert(0, str(CORE_DIR))

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'stock_analysis',
    'user': 'stock_user',
    'password': 'stock_password_123'
}


def load_strategy_from_db(strategy_id: int):
    """
    从数据库加载策略

    Args:
        strategy_id: 策略ID

    Returns:
        策略数据字典
    """
    conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT * FROM strategies WHERE id = %s",
            (strategy_id,)
        )
        strategy = cursor.fetchone()

        if not strategy:
            raise ValueError(f"策略 ID {strategy_id} 不存在")

        return dict(strategy)

    finally:
        cursor.close()
        conn.close()


def load_strategy_class(code: str, class_name: str):
    """
    动态加载策略类

    Args:
        code: 策略代码字符串
        class_name: 类名

    Returns:
        策略类
    """
    # 使用exec直接在当前命名空间中执行代码
    # 创建一个干净的命名空间
    namespace = {
        '__name__': '__dynamic_strategy__',
        '__file__': '<dynamic>',
    }

    # 添加必要的导入
    import pandas as pd
    import numpy as np
    from loguru import logger
    from strategies.base_strategy import BaseStrategy
    from strategies.signal_generator import SignalGenerator

    namespace.update({
        'pd': pd,
        'np': np,
        'logger': logger,
        'BaseStrategy': BaseStrategy,
        'SignalGenerator': SignalGenerator,
        'Optional': __import__('typing').Optional,
        'Dict': __import__('typing').Dict,
        'Any': __import__('typing').Any,
        'List': __import__('typing').List,
    })

    # 执行代码
    exec(code, namespace)

    # 获取类
    strategy_class = namespace.get(class_name)
    if not strategy_class:
        raise ValueError(f"类 {class_name} 在代码中未找到")

    return strategy_class


def verify_strategy_loading():
    """验证策略加载功能"""

    logger.info("=" * 60)
    logger.info("开始验证策略加载功能...")
    logger.info("=" * 60)

    # 获取所有策略
    conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, display_name, class_name FROM strategies ORDER BY id")
    strategies = cursor.fetchall()

    logger.info(f"\n找到 {len(strategies)} 个策略:\n")

    success_count = 0
    fail_count = 0

    for strategy in strategies:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"测试策略: {strategy['display_name']} (ID: {strategy['id']})")
        logger.info(f"类名: {strategy['class_name']}")

        try:
            # 1. 从数据库加载策略
            strategy_data = load_strategy_from_db(strategy['id'])
            logger.info(f"✓ 从数据库加载成功")
            logger.info(f"  代码长度: {len(strategy_data['code'])} bytes")
            logger.info(f"  代码哈希: {strategy_data['code_hash'][:16]}...")

            # 2. 动态加载类
            strategy_class = load_strategy_class(
                strategy_data['code'],
                strategy_data['class_name']
            )
            logger.info(f"✓ 动态加载类成功")

            # 3. 实例化策略
            strategy_instance = strategy_class(
                name=f"test_{strategy['name']}",
                config=strategy_data['default_params'] or {}
            )
            logger.info(f"✓ 实例化策略成功")

            # 4. 调用get_metadata方法
            if hasattr(strategy_instance, 'get_metadata'):
                metadata = strategy_instance.get_metadata()
                logger.info(f"✓ 获取元数据成功:")
                logger.info(f"  类别: {metadata.get('category')}")
                logger.info(f"  描述: {metadata.get('description')}")
                logger.info(f"  风险等级: {metadata.get('risk_level')}")
            else:
                logger.warning("策略类没有 get_metadata 方法")

            logger.success(f"✓ 策略 {strategy['display_name']} 验证通过!")
            success_count += 1

        except Exception as e:
            logger.error(f"✗ 策略 {strategy['display_name']} 验证失败:")
            logger.error(f"  错误: {e}")
            import traceback
            logger.error(f"  详情: {traceback.format_exc()}")
            fail_count += 1

    # 总结
    logger.info(f"\n{'=' * 60}")
    logger.info("验证结果:")
    logger.success(f"  成功: {success_count}")
    if fail_count > 0:
        logger.error(f"  失败: {fail_count}")
    else:
        logger.success(f"  失败: {fail_count}")
    logger.info(f"  总计: {success_count + fail_count}")
    logger.info("=" * 60)

    cursor.close()
    conn.close()

    return success_count, fail_count


if __name__ == "__main__":
    # 配置日志
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    # 执行验证
    success, fail = verify_strategy_loading()

    # 退出码
    sys.exit(0 if fail == 0 else 1)
