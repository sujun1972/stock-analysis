"""
数据质量检查模块使用示例

演示：
1. 异常值检测和处理
2. 停牌股票过滤
3. 数据验证
4. 缺失值处理
5. 完整的数据清洗流程

作者: AI Assistant
日期: 2026-01-30
"""

import pandas as pd
import numpy as np
from loguru import logger

# 导入数据质量检查模块
from data import (
    OutlierDetector,
    SuspendFilter,
    DataValidator,
    MissingHandler,
    clean_outliers,
    filter_suspended_data,
    fill_missing,
    validate_stock_data
)


def example_1_outlier_detection():
    """示例1：异常值检测和处理"""
    logger.info("=" * 60)
    logger.info("示例1：异常值检测和处理")
    logger.info("=" * 60)

    # 创建测试数据
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    np.random.seed(42)

    base_price = 100
    returns = np.random.normal(0.001, 0.02, 100)

    # 注入异常值
    returns[20] = 0.25  # 单日暴涨25%
    returns[50] = -0.22  # 单日暴跌22%

    prices = base_price * (1 + returns).cumprod()

    df = pd.DataFrame({
        'open': prices * 0.99,
        'high': prices * 1.01,
        'low': prices * 0.98,
        'close': prices,
        'volume': np.random.uniform(1000000, 10000000, 100)
    }, index=dates)

    logger.info(f"\n原始数据: {len(df)} 行")
    logger.info(f"价格范围: {df['close'].min():.2f} - {df['close'].max():.2f}")

    # 1. 检测异常值
    detector = OutlierDetector(df)
    outliers_df = detector.detect_all_outliers(
        price_method='both',
        price_threshold=3.0,
        jump_threshold=0.20
    )

    logger.info(f"\n检测到 {outliers_df['is_outlier'].sum()} 个异常值")

    # 2. 获取摘要
    summary = detector.get_outlier_summary(outliers_df)
    logger.info(f"\n异常值摘要:")
    logger.info(f"  总记录数: {summary['total_records']}")
    logger.info(f"  异常值数: {summary['total_outliers']}")
    logger.info(f"  异常率: {summary['outlier_percentage']:.2f}%")

    # 3. 处理异常值 - 插值法
    df_cleaned = detector.handle_outliers(
        outliers_df['is_outlier'],
        method='interpolate'
    )

    logger.info(f"\n清洗后:")
    logger.info(f"  缺失值: {df_cleaned.isnull().sum().sum()}")
    logger.info(f"  价格范围: {df_cleaned['close'].min():.2f} - {df_cleaned['close'].max():.2f}")

    return df_cleaned


def example_2_suspension_filter():
    """示例2：停牌股票过滤"""
    logger.info("\n" + "=" * 60)
    logger.info("示例2：停牌股票过滤")
    logger.info("=" * 60)

    # 创建测试数据
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    np.random.seed(42)

    prices = 100 * (1 + np.random.normal(0.001, 0.02, 100)).cumprod()

    # 模拟停牌: 第20-25天停牌
    prices[20:26] = prices[19]

    volumes = np.random.uniform(1000000, 10000000, 100)
    volumes[20:26] = 0

    df = pd.DataFrame({
        'close': prices,
        'volume': volumes
    }, index=dates)

    logger.info(f"\n原始数据: {len(df)} 天")

    # 1. 检测停牌
    filter_obj = SuspendFilter(df)
    suspended_df = filter_obj.detect_all_suspended(
        volume_threshold=100,
        consecutive_days=3
    )

    logger.info(f"\n检测到 {suspended_df['is_suspended'].sum()} 天停牌")

    # 2. 获取停牌期间
    periods = filter_obj.get_suspension_periods(suspended_df['is_suspended'])
    logger.info(f"\n停牌期间:")
    for start, end, days in periods:
        logger.info(f"  {start.date()} 至 {end.date()}, 共 {days} 天")

    # 3. 过滤停牌数据
    df_filtered = filter_obj.filter_suspended(suspended_df['is_suspended'])

    logger.info(f"\n过滤后:")
    logger.info(f"  有效数据: {df_filtered['close'].notna().sum()} 天")
    logger.info(f"  缺失数据: {df_filtered['close'].isna().sum()} 天")

    return df_filtered


def example_3_data_validation():
    """示例3：数据验证"""
    logger.info("\n" + "=" * 60)
    logger.info("示例3：数据验证")
    logger.info("=" * 60)

    # 创建测试数据（包含一些问题）
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    np.random.seed(42)

    prices = 100 + np.random.normal(0, 5, 100)

    df = pd.DataFrame({
        'open': prices * 0.99,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices,
        'volume': np.random.uniform(1000000, 10000000, 100)
    }, index=dates)

    # 注入问题
    df.loc[dates[10], 'high'] = df.loc[dates[10], 'low'] - 1  # high < low
    df.loc[dates[20], 'close'] = df.loc[dates[20], 'high'] + 10  # close > high
    df.loc[dates[30:35], 'close'] = np.nan  # 缺失值

    logger.info(f"\n待验证数据: {len(df)} 行 x {len(df.columns)} 列")

    # 1. 执行全面验证
    validator = DataValidator(df)
    results = validator.validate_all(strict_mode=False)

    # 2. 打印验证报告
    logger.info(f"\n{validator.get_validation_report()}")

    # 3. 检查是否通过
    if results['passed']:
        logger.info("✓ 数据验证通过!")
    else:
        logger.warning("✗ 数据验证失败，需要清洗!")

    return df


def example_4_missing_handler():
    """示例4：缺失值处理"""
    logger.info("\n" + "=" * 60)
    logger.info("示例4：缺失值处理")
    logger.info("=" * 60)

    # 创建测试数据
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    np.random.seed(42)

    prices = 100 + np.random.normal(0, 5, 100)
    volumes = np.random.uniform(1000000, 10000000, 100)

    df = pd.DataFrame({
        'close': prices,
        'volume': volumes
    }, index=dates)

    # 注入缺失值
    df.loc[dates[0:3], 'close'] = np.nan  # 前导缺失
    df.loc[dates[10:15], 'close'] = np.nan  # 中间缺失
    df.loc[dates[95:], 'close'] = np.nan  # 尾部缺失

    logger.info(f"\n原始数据: {len(df)} 行")
    logger.info(f"缺失值: {df.isnull().sum().sum()} 个")

    # 1. 检测缺失值
    handler = MissingHandler(df)
    stats = handler.detect_missing()

    logger.info(f"\n缺失值统计:")
    logger.info(f"  总缺失: {stats['total_missing']} ({stats['missing_rate']:.2f}%)")
    logger.info(f"  受影响行: {stats['rows_with_missing']}")

    # 2. 分析缺失模式
    patterns = handler.get_missing_patterns()
    logger.info(f"\n缺失模式:")
    logger.info(f"  前导缺失: {patterns['leading_missing']}")
    logger.info(f"  尾部缺失: {patterns['trailing_missing']}")

    # 3. 智能填充
    df_filled = handler.smart_fill(
        leading_method='bfill',
        trailing_method='ffill',
        middle_method='interpolate',
        max_gap=5
    )

    # 4. 生成报告
    report = handler.get_fill_report(df_filled)
    logger.info(f"\n填充报告:")
    logger.info(f"  原始缺失: {report['original_missing']}")
    logger.info(f"  剩余缺失: {report['remaining_missing']}")
    logger.info(f"  填充数量: {report['filled_count']}")
    logger.info(f"  填充率: {report['fill_rate']:.2f}%")

    return df_filled


def example_5_complete_pipeline():
    """示例5：完整的数据清洗流程"""
    logger.info("\n" + "=" * 60)
    logger.info("示例5：完整的数据清洗流程")
    logger.info("=" * 60)

    # 创建包含各种问题的数据
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    np.random.seed(42)

    base_price = 100
    returns = np.random.normal(0.001, 0.02, 100)
    returns[20] = 0.25  # 异常值
    returns[50] = -0.22  # 异常值

    prices = base_price * (1 + returns).cumprod()
    volumes = np.random.uniform(1000000, 10000000, 100)

    # 停牌
    prices[30:36] = prices[29]
    volumes[30:36] = 0

    df = pd.DataFrame({
        'close': prices,
        'volume': volumes
    }, index=dates)

    # 缺失值
    df.loc[dates[10:13], 'close'] = np.nan

    logger.info(f"\n原始数据: {len(df)} 行")
    logger.info(f"  异常值: 未知")
    logger.info(f"  停牌天数: 6")
    logger.info(f"  缺失值: {df.isnull().sum().sum()}")

    # ========== 完整清洗流程 ==========

    # 步骤1：数据验证
    logger.info("\n步骤1: 数据验证...")
    validator = DataValidator(df)
    validation_results = validator.validate_all(strict_mode=False)

    if not validation_results['passed']:
        logger.warning("数据验证失败，开始清洗...")

    # 步骤2：异常值处理
    logger.info("\n步骤2: 异常值处理...")
    df_clean = clean_outliers(
        df,
        method='interpolate',
        detection_method='both',
        threshold=3.0
    )

    # 步骤3：停牌过滤
    logger.info("\n步骤3: 停牌过滤...")
    df_clean = filter_suspended_data(
        df_clean,
        volume_threshold=100,
        consecutive_days=3,
        fill_value=np.nan
    )

    # 步骤4：缺失值填充
    logger.info("\n步骤4: 缺失值填充...")
    df_clean = fill_missing(
        df_clean,
        method='smart'
    )

    # 步骤5：最终验证
    logger.info("\n步骤5: 最终验证...")
    validator_final = DataValidator(df_clean)
    final_results = validator_final.validate_all(strict_mode=False)

    logger.info(f"\n清洗完成!")
    logger.info(f"  最终数据: {len(df_clean)} 行")
    logger.info(f"  缺失值: {df_clean.isnull().sum().sum()}")
    logger.info(f"  验证结果: {'✓ 通过' if final_results['passed'] else '✗ 失败'}")
    logger.info(f"  错误数: {final_results['summary']['error_count']}")
    logger.info(f"  警告数: {final_results['summary']['warning_count']}")

    return df_clean


def main():
    """主函数"""
    # 配置日志
    logger.remove()
    logger.add(lambda msg: print(msg, end=''), level="INFO")

    logger.info("\n" + "=" * 60)
    logger.info("数据质量检查模块使用示例")
    logger.info("=" * 60)

    # 运行所有示例
    example_1_outlier_detection()
    example_2_suspension_filter()
    example_3_data_validation()
    example_4_missing_handler()
    example_5_complete_pipeline()

    logger.info("\n" + "=" * 60)
    logger.info("所有示例运行完成!")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
