"""
初始化内置策略到数据库

将三个内置策略(动量、均值回归、多因子)的完整代码插入到 strategies 表中
"""

import sys
import hashlib
from pathlib import Path
from typing import Dict, Any
import psycopg2
from psycopg2.extras import Json
from loguru import logger

# 添加core路径
CORE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CORE_DIR / 'src'))

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'stock_analysis',
    'user': 'stock_user',
    'password': 'stock_password_123'
}


def load_strategy_code(strategy_file: str) -> str:
    """
    从文件加载策略代码

    Args:
        strategy_file: 策略文件名(不含.py扩展名)

    Returns:
        完整的策略代码字符串
    """
    file_path = Path(__file__).parent / 'builtin_strategies' / f'{strategy_file}.py'

    if not file_path.exists():
        raise FileNotFoundError(f"策略文件不存在: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    logger.info(f"✓ 加载策略代码: {strategy_file} ({len(code)} bytes)")
    return code


def calculate_code_hash(code: str) -> str:
    """
    计算代码 SHA256 哈希

    Args:
        code: 代码字符串

    Returns:
        SHA256 哈希值
    """
    return hashlib.sha256(code.encode('utf-8')).hexdigest()


def insert_strategy(conn, strategy_data: Dict[str, Any]) -> int:
    """
    插入策略到数据库

    Args:
        conn: 数据库连接
        strategy_data: 策略数据字典

    Returns:
        插入的策略ID
    """
    cursor = conn.cursor()

    try:
        # 检查是否已存在
        cursor.execute(
            "SELECT id FROM strategies WHERE name = %s",
            (strategy_data['name'],)
        )
        existing = cursor.fetchone()

        if existing:
            logger.warning(f"策略 {strategy_data['name']} 已存在 (ID: {existing[0]}), 跳过")
            return existing[0]

        # 插入新策略
        insert_sql = """
            INSERT INTO strategies (
                name, display_name, class_name, code, code_hash,
                source_type, description, category, tags,
                default_params, validation_status, risk_level, is_enabled
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s
            ) RETURNING id
        """

        cursor.execute(insert_sql, (
            strategy_data['name'],
            strategy_data['display_name'],
            strategy_data['class_name'],
            strategy_data['code'],
            strategy_data['code_hash'],
            strategy_data['source_type'],
            strategy_data['description'],
            strategy_data['category'],
            strategy_data['tags'],
            Json(strategy_data['default_params']),
            strategy_data['validation_status'],
            strategy_data['risk_level'],
            strategy_data['is_enabled']
        ))

        strategy_id = cursor.fetchone()[0]
        conn.commit()

        logger.success(f"✓ 创建策略: {strategy_data['display_name']} (ID: {strategy_id})")
        return strategy_id

    except Exception as e:
        conn.rollback()
        logger.error(f"✗ 插入策略失败: {strategy_data['name']}, 错误: {e}")
        raise


def init_builtin_strategies():
    """初始化内置策略"""

    logger.info("=" * 60)
    logger.info("开始初始化内置策略...")
    logger.info("=" * 60)

    # 定义三个内置策略
    builtin_strategies = [
        {
            'name': 'momentum_builtin',
            'display_name': '动量策略(内置)',
            'class_name': 'MomentumStrategy',
            'description': '基于价格动量选股,买入近期强势股',
            'category': 'momentum',
            'source_type': 'builtin',
            'tags': ['动量', '趋势', '短期'],
            'default_params': {
                'lookback_period': 20,
                'top_n': 50,
                'holding_period': 5,
                'use_log_return': False,
                'filter_negative': True,
            },
            'validation_status': 'passed',
            'risk_level': 'medium',
            'is_enabled': True,
            'code_file': 'momentum_strategy',
        },
        {
            'name': 'mean_reversion_builtin',
            'display_name': '均值回归策略(内置)',
            'class_name': 'MeanReversionStrategy',
            'description': '买入超跌股票,等待价格回归均值',
            'category': 'reversal',
            'source_type': 'builtin',
            'tags': ['均值回归', '反转', '震荡市'],
            'default_params': {
                'lookback_period': 20,
                'z_score_threshold': -2.0,
                'top_n': 30,
                'holding_period': 5,
                'use_bollinger': False,
                'bollinger_window': 20,
                'bollinger_std': 2.0,
            },
            'validation_status': 'passed',
            'risk_level': 'medium',
            'is_enabled': True,
            'code_file': 'mean_reversion_strategy',
        },
        {
            'name': 'multi_factor_builtin',
            'display_name': '多因子策略(内置)',
            'class_name': 'MultiFactorStrategy',
            'description': '综合多个因子进行选股',
            'category': 'factor',
            'source_type': 'builtin',
            'tags': ['多因子', '综合', '稳健'],
            'default_params': {
                'factors': ['MOM20', 'REV5', 'VOLATILITY20'],
                'weights': None,
                'normalize_method': 'rank',
                'top_n': 50,
                'holding_period': 5,
                'neutralize': False,
                'min_factor_coverage': 0.8,
            },
            'validation_status': 'passed',
            'risk_level': 'low',
            'is_enabled': True,
            'code_file': 'multi_factor_strategy',
        },
    ]

    # 连接数据库
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info(f"✓ 数据库连接成功: {DB_CONFIG['database']}")
    except Exception as e:
        logger.error(f"✗ 数据库连接失败: {e}")
        sys.exit(1)

    try:
        # 处理每个策略
        inserted_count = 0
        skipped_count = 0

        for strategy_data in builtin_strategies:
            logger.info(f"\n处理策略: {strategy_data['display_name']}")

            # 加载代码
            code = load_strategy_code(strategy_data['code_file'])
            code_hash = calculate_code_hash(code)

            strategy_data['code'] = code
            strategy_data['code_hash'] = code_hash

            # 删除临时字段
            del strategy_data['code_file']

            # 插入数据库
            strategy_id = insert_strategy(conn, strategy_data)

            if strategy_id:
                if conn.status == psycopg2.extensions.STATUS_READY:
                    inserted_count += 1
                else:
                    skipped_count += 1

        # 总结
        logger.info("\n" + "=" * 60)
        logger.success(f"✓ 内置策略初始化完成!")
        logger.info(f"  新增策略: {inserted_count}")
        logger.info(f"  跳过策略: {skipped_count}")
        logger.info(f"  总计: {inserted_count + skipped_count}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"\n✗ 初始化失败: {e}")
        sys.exit(1)
    finally:
        conn.close()
        logger.info("数据库连接已关闭")


if __name__ == "__main__":
    # 配置日志
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    # 执行初始化
    init_builtin_strategies()
