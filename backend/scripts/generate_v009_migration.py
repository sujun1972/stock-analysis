"""
生成策略迁移SQL脚本

将所有内置策略（入场+离场）插入到数据库，用于完全数据库驱动的策略系统。
策略代码从 core/src 目录读取，生成包含完整Python代码的SQL INSERT语句。

运行方式:
    cd backend/scripts
    python generate_v009_migration.py > ../migrations/V010__insert_builtin_strategies.sql

注意:
- 生成的策略默认 publish_status='approved'，可直接在前端显示
- 使用 ON CONFLICT 处理重复插入
- 自动计算代码哈希用于完整性验证

作者: Backend Team
创建日期: 2026-03-07
"""
import sys
import hashlib
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
core_path = project_root / "core"
sys.path.insert(0, str(core_path))


def escape_sql_string(text: str) -> str:
    """
    转义SQL字符串中的特殊字符

    Args:
        text: 原始文本

    Returns:
        转义后的文本
    """
    # 将单引号转义为两个单引号
    return text.replace("'", "''")


def calculate_code_hash(code: str) -> str:
    """计算代码哈希（SHA256前16位）"""
    return hashlib.sha256(code.encode()).hexdigest()[:16]


def read_strategy_code(file_path: Path, class_name: str) -> str:
    """
    读取策略代码并提取类定义

    Args:
        file_path: 策略文件路径
        class_name: 策略类名

    Returns:
        完整的策略代码（包含导入和类定义）
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 提取从导入到类定义结束的部分
    lines = content.split('\n')

    # 跳过文档字符串和注释
    start_idx = 0
    for i, line in enumerate(lines):
        if line.strip().startswith('from') or line.strip().startswith('import'):
            start_idx = i
            break

    # 找到类定义的结束（下一个顶层定义或文件结束）
    class_started = False
    end_idx = len(lines)

    for i in range(start_idx, len(lines)):
        line = lines[i]

        if f'class {class_name}' in line:
            class_started = True

        # 类定义结束的标志
        if class_started and i > start_idx:
            # 遇到新的顶层类或函数定义
            if (line.startswith('class ') and f'class {class_name}' not in line) or \
               (line.startswith('def ') and not line.startswith('    ')):
                end_idx = i
                break
            # 遇到分隔注释
            if line.strip().startswith('# ='):
                end_idx = i
                break

    code_lines = lines[start_idx:end_idx]

    # 移除相对导入，改为绝对导入
    processed_lines = []
    for line in code_lines:
        if 'from ..' in line:
            # from ..base_strategy import => from src.strategies.base_strategy import
            line = line.replace('from ..base_strategy', 'from src.strategies.base_strategy')
            line = line.replace('from ..signal_generator', 'from src.strategies.signal_generator')
            line = line.replace('from ..features.', 'from src.features.')
        processed_lines.append(line)

    return '\n'.join(processed_lines)


def generate_entry_strategies_sql() -> str:
    """生成入场策略的SQL INSERT语句"""
    strategies = []

    # 1. 动量策略
    momentum_code = read_strategy_code(
        core_path / 'src/strategies/predefined/momentum_strategy.py',
        'MomentumStrategy'
    )

    strategies.append({
        'name': 'momentum_entry',
        'display_name': '动量入场策略',
        'class_name': 'MomentumStrategy',
        'code': momentum_code,
        'description': '基于价格动量选股：买入近期强势股，持有一段时间后卖出',
        'category': 'momentum',
        'tags': ['动量', '趋势', '入场'],
        'default_params': {
            'lookback_period': 20,
            'top_n': 50,
            'holding_period': 5,
            'use_log_return': False,
            'filter_negative': True
        },
        'risk_level': 'medium'
    })

    # 2. 均值回归策略
    mean_reversion_code = read_strategy_code(
        core_path / 'src/strategies/predefined/mean_reversion_strategy.py',
        'MeanReversionStrategy'
    )

    strategies.append({
        'name': 'mean_reversion_entry',
        'display_name': '均值回归入场策略',
        'class_name': 'MeanReversionStrategy',
        'code': mean_reversion_code,
        'description': '基于均值回归效应：买入短期超跌股票，等待反弹后卖出',
        'category': 'mean_reversion',
        'tags': ['均值回归', '反转', '入场'],
        'default_params': {
            'lookback_period': 20,
            'z_score_threshold': -2.0,
            'top_n': 30,
            'holding_period': 5,
            'use_bollinger': False
        },
        'risk_level': 'medium'
    })

    # 3. 多因子策略
    multi_factor_code = read_strategy_code(
        core_path / 'src/strategies/predefined/multi_factor_strategy.py',
        'MultiFactorStrategy'
    )

    strategies.append({
        'name': 'multi_factor_entry',
        'display_name': '多因子入场策略',
        'class_name': 'MultiFactorStrategy',
        'code': multi_factor_code,
        'description': '结合多个Alpha因子进行选股，提高稳定性',
        'category': 'multi_factor',
        'tags': ['多因子', 'Alpha', '入场'],
        'default_params': {
            'factors': ['MOM20', 'REV5', 'VOLATILITY20'],
            'weights': None,
            'normalize_method': 'rank',
            'top_n': 50,
            'holding_period': 5
        },
        'risk_level': 'low'
    })

    # 生成SQL
    sql_statements = []

    for strategy in strategies:
        code_hash = calculate_code_hash(strategy['code'])
        escaped_code = escape_sql_string(strategy['code'])
        escaped_desc = escape_sql_string(strategy['description'])

        import json
        params_json = json.dumps(strategy['default_params'], ensure_ascii=False)
        escaped_params = escape_sql_string(params_json)

        tags_array = "ARRAY[" + ", ".join(f"'{tag}'" for tag in strategy['tags']) + "]"

        sql = f"""
-- {strategy['display_name']}
INSERT INTO strategies (
    user_id, name, display_name, class_name, code, code_hash,
    source_type, strategy_type, description, category, tags,
    default_params, validation_status, risk_level, is_enabled, publish_status, created_by, version
) VALUES (
    NULL,
    '{strategy['name']}',
    '{strategy['display_name']}',
    '{strategy['class_name']}',
    '{escaped_code}',
    '{code_hash}',
    'builtin',
    'entry',
    '{escaped_desc}',
    '{strategy['category']}',
    {tags_array},
    '{escaped_params}'::jsonb,
    'passed',
    '{strategy['risk_level']}',
    TRUE,
    'approved',
    'system',
    1
) ON CONFLICT (user_id, name) DO UPDATE SET
    code = EXCLUDED.code,
    code_hash = EXCLUDED.code_hash,
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    default_params = EXCLUDED.default_params,
    updated_at = NOW();
"""
        sql_statements.append(sql)

    return '\n'.join(sql_statements)


def extract_exit_strategy_code(file_path: Path, class_name: str, end_marker: str = None) -> str:
    """
    从文件中提取单个离场策略类的代码

    Args:
        file_path: 文件路径
        class_name: 类名
        end_marker: 结束标记（下一个类的名称）

    Returns:
        策略代码
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')

    # 找到类定义的开始
    class_start = None
    for i, line in enumerate(lines):
        if f'class {class_name}' in line and 'BaseExitStrategy' in line:
            # 回溯找导入语句
            for j in range(i-1, -1, -1):
                if lines[j].strip().startswith('from') or lines[j].strip().startswith('import'):
                    class_start = j
                    break
            if class_start is None:
                class_start = i
            break

    if class_start is None:
        raise ValueError(f"未找到类: {class_name}")

    # 找到类定义的结束
    class_end = len(lines)
    found_class = False

    for i in range(class_start, len(lines)):
        line = lines[i]

        if f'class {class_name}' in line:
            found_class = True
            continue

        if found_class:
            # 遇到下一个类定义
            if end_marker and f'class {end_marker}' in line:
                class_end = i
                break
            # 遇到顶层函数或分隔符
            if line.startswith('class ') or line.startswith('def ') or line.strip().startswith('# ='):
                class_end = i
                break

    code_lines = lines[class_start:class_end]

    # 只保留必要的导入
    imports = [
        'from typing import Optional, Dict',
        'from datetime import datetime',
        'import pandas as pd',
        'import numpy as np',
        'from loguru import logger',
        'from src.ml.exit_strategy import BaseExitStrategy, ExitSignal'
    ]

    # 过滤掉原有导入，使用标准导入
    filtered_lines = []
    skip_imports = False

    for line in code_lines:
        # 跳过原文件中的导入部分
        if line.strip().startswith('from') or line.strip().startswith('import'):
            if not skip_imports:
                skip_imports = True
            continue
        else:
            if skip_imports:
                # 导入部分结束，添加标准导入
                filtered_lines.extend(imports)
                filtered_lines.append('')
                skip_imports = False
            filtered_lines.append(line)

    return '\n'.join(filtered_lines)


def generate_exit_strategies_sql() -> str:
    """生成离场策略的SQL INSERT语句"""
    strategies = []

    exit_strategy_file = core_path / 'src/ml/exit_strategy.py'
    adaptive_file = core_path / 'src/ml/adaptive_exit_strategy.py'

    # 1. 止损策略
    stop_loss_code = extract_exit_strategy_code(
        exit_strategy_file, 'StopLossExitStrategy', 'TakeProfitExitStrategy'
    )

    strategies.append({
        'name': 'stop_loss_exit',
        'display_name': '止损离场策略',
        'class_name': 'StopLossExitStrategy',
        'code': stop_loss_code,
        'description': '当亏损超过指定比例时触发离场，用于风险控制',
        'category': 'stop_loss',
        'tags': ['风控', '止损', '离场'],
        'default_params': {
            'stop_loss_pct': 0.10,
            'priority': 10
        },
        'risk_level': 'safe'
    })

    # 2. 止盈策略
    take_profit_code = extract_exit_strategy_code(
        exit_strategy_file, 'TakeProfitExitStrategy', 'HoldingPeriodExitStrategy'
    )

    strategies.append({
        'name': 'take_profit_exit',
        'display_name': '止盈离场策略',
        'class_name': 'TakeProfitExitStrategy',
        'code': take_profit_code,
        'description': '当盈利达到目标时触发离场，锁定利润',
        'category': 'take_profit',
        'tags': ['止盈', '离场'],
        'default_params': {
            'take_profit_pct': 0.20,
            'priority': 8
        },
        'risk_level': 'safe'
    })

    # 3. 持仓时长策略
    holding_period_code = extract_exit_strategy_code(
        exit_strategy_file, 'HoldingPeriodExitStrategy', 'TrailingStopExitStrategy'
    )

    strategies.append({
        'name': 'holding_period_exit',
        'display_name': '持仓时长离场策略',
        'class_name': 'HoldingPeriodExitStrategy',
        'code': holding_period_code,
        'description': '当持仓天数达到上限时触发离场',
        'category': 'holding_period',
        'tags': ['持仓时长', '离场'],
        'default_params': {
            'max_holding_days': 30,
            'priority': 3
        },
        'risk_level': 'low'
    })

    # 4. 移动止损策略
    trailing_stop_code = extract_exit_strategy_code(
        exit_strategy_file, 'TrailingStopExitStrategy', 'CompositeExitManager'
    )

    strategies.append({
        'name': 'trailing_stop_exit',
        'display_name': '移动止损离场策略',
        'class_name': 'TrailingStopExitStrategy',
        'code': trailing_stop_code,
        'description': '跟踪最高价，当回撤超过阈值时触发离场',
        'category': 'trailing_stop',
        'tags': ['移动止损', '风控', '离场'],
        'default_params': {
            'trailing_stop_pct': 0.05,
            'priority': 9
        },
        'risk_level': 'safe'
    })

    # 5. 自适应离场策略
    adaptive_code = extract_exit_strategy_code(
        adaptive_file, 'AdaptiveExitStrategy'
    )

    strategies.append({
        'name': 'adaptive_exit',
        'display_name': '自适应离场策略',
        'class_name': 'AdaptiveExitStrategy',
        'code': adaptive_code,
        'description': '根据市场波动性和持仓盈亏动态调整止盈止损参数',
        'category': 'adaptive',
        'tags': ['自适应', '动态调整', '离场'],
        'default_params': {
            'base_stop_loss': 0.08,
            'base_take_profit': 0.15,
            'volatility_window': 20,
            'priority': 9
        },
        'risk_level': 'medium'
    })

    # 生成SQL
    sql_statements = []

    for strategy in strategies:
        code_hash = calculate_code_hash(strategy['code'])
        escaped_code = escape_sql_string(strategy['code'])
        escaped_desc = escape_sql_string(strategy['description'])

        import json
        params_json = json.dumps(strategy['default_params'], ensure_ascii=False)
        escaped_params = escape_sql_string(params_json)

        tags_array = "ARRAY[" + ", ".join(f"'{tag}'" for tag in strategy['tags']) + "]"

        sql = f"""
-- {strategy['display_name']}
INSERT INTO strategies (
    user_id, name, display_name, class_name, code, code_hash,
    source_type, strategy_type, description, category, tags,
    default_params, validation_status, risk_level, is_enabled, publish_status, created_by, version
) VALUES (
    NULL,
    '{strategy['name']}',
    '{strategy['display_name']}',
    '{strategy['class_name']}',
    '{escaped_code}',
    '{code_hash}',
    'builtin',
    'exit',
    '{escaped_desc}',
    '{strategy['category']}',
    {tags_array},
    '{escaped_params}'::jsonb,
    'passed',
    '{strategy['risk_level']}',
    TRUE,
    'approved',
    'system',
    1
) ON CONFLICT (user_id, name) DO UPDATE SET
    code = EXCLUDED.code,
    code_hash = EXCLUDED.code_hash,
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    default_params = EXCLUDED.default_params,
    updated_at = NOW();
"""
        sql_statements.append(sql)

    return '\n'.join(sql_statements)


def generate_full_migration() -> str:
    """生成完整的迁移脚本"""
    header = """-- ============================================================
-- V009: 插入系统内置策略（完全数据库驱动）
-- 创建时间: 2026-03-07
-- 说明: 将所有入场策略和离场策略从本地文件迁移到数据库
-- ============================================================

-- 1. 清理旧的占位符数据（如果存在）
DELETE FROM strategies
WHERE source_type = 'builtin'
AND code LIKE '%pass%'
AND (code_hash = encode(sha256('%pass%'::bytea), 'hex') OR LENGTH(code) < 200);

-- ============================================================
-- 2. 插入入场策略（3个）
-- ============================================================
"""

    entry_sql = generate_entry_strategies_sql()

    middle = """
-- ============================================================
-- 3. 插入离场策���（5个）
-- ============================================================
"""

    exit_sql = generate_exit_strategies_sql()

    footer = """
-- ============================================================
-- 4. 验证插入结果
-- ============================================================

DO $$
DECLARE
    entry_count INT;
    exit_count INT;
    rec RECORD;
BEGIN
    SELECT COUNT(*) INTO entry_count FROM strategies WHERE strategy_type = 'entry' AND source_type = 'builtin';
    SELECT COUNT(*) INTO exit_count FROM strategies WHERE strategy_type = 'exit' AND source_type = 'builtin';

    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
    RAISE NOTICE '✅ 系统内置策略迁移完成！';
    RAISE NOTICE '============================================================';
    RAISE NOTICE '';
    RAISE NOTICE '入场策略数量: %', entry_count;
    RAISE NOTICE '离场策略数量: %', exit_count;
    RAISE NOTICE '总计: % 个策略', entry_count + exit_count;
    RAISE NOTICE '';
    RAISE NOTICE '策略列表:';

    FOR rec IN SELECT id, name, display_name, strategy_type FROM strategies WHERE source_type = 'builtin' ORDER BY strategy_type, id
    LOOP
        RAISE NOTICE '  [%] % - % (%)', rec.id, rec.strategy_type, rec.display_name, rec.name;
    END LOOP;

    RAISE NOTICE '';
    RAISE NOTICE '============================================================';
END $$;
"""

    return header + entry_sql + middle + exit_sql + footer


if __name__ == '__main__':
    try:
        migration_sql = generate_full_migration()
        print(migration_sql)
    except Exception as e:
        print(f"-- 错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
