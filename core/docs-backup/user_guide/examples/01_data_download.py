"""
数据下载示例

演示如何从多个数据源下载A股数据并保存到数据库。

作者: Quant Team
版本: v3.0.0
日期: 2026-02-01
"""

import argparse
from datetime import datetime, timedelta
from typing import List, Optional

import pandas as pd
from loguru import logger

from src.providers import DataProviderFactory
from src.data.database_manager import DatabaseManager
from src.data.data_validator import DataValidator
from src.utils.exceptions import DataFetchError, DataValidationError


def download_single_stock(
    stock_code: str,
    start_date: str,
    end_date: Optional[str] = None,
    provider_name: str = 'akshare',
    save_to_db: bool = True
) -> pd.DataFrame:
    """
    下载单只股票数据

    Args:
        stock_code: 股票代码（如'000001.SZ'）
        start_date: 开始日期（'YYYY-MM-DD'）
        end_date: 结束日期（默认为今天）
        provider_name: 数据提供者（'akshare'或'tushare'）
        save_to_db: 是否保存到数据库

    Returns:
        pd.DataFrame: 股票数据

    Raises:
        DataFetchError: 数据获取失败
        DataValidationError: 数据验证失败
    """
    logger.info(f"开始下载 {stock_code} 数据...")

    # 设置结束日期
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')

    try:
        # 1. 创建数据提供者
        provider = DataProviderFactory.create_provider(provider_name)
        logger.info(f"使用数据源: {provider_name}")

        # 2. 获取数据
        data = provider.get_daily_data(
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date
        )

        logger.info(f"✅ 获取了 {len(data)} 条数据")

        # 3. 数据验证
        validator = DataValidator()
        is_valid, errors = validator.validate(data)

        if not is_valid:
            logger.warning(f"⚠️ 数据质量问题: {errors}")
            # 清洗数据
            data = validator.clean(data)
            logger.info("✅ 数据已清洗")

        # 4. 保存到数据库（可选）
        if save_to_db:
            db = DatabaseManager()
            db.insert_stock_data(data)
            logger.info(f"✅ 数据已保存到数据库")

        # 5. 显示数据概览
        logger.info("\n数据概览:")
        logger.info(f"  时间范围: {data['trade_date'].min()} ~ {data['trade_date'].max()}")
        logger.info(f"  价格范围: {data['close'].min():.2f} ~ {data['close'].max():.2f}")
        logger.info(f"  平均成交量: {data['volume'].mean():.0f}")

        return data

    except Exception as e:
        logger.exception(f"❌ 下载失败: {e}")
        raise DataFetchError(f"Failed to download {stock_code}: {e}")


def download_multiple_stocks(
    stock_codes: List[str],
    start_date: str,
    end_date: Optional[str] = None,
    provider_name: str = 'akshare',
    save_to_db: bool = True
) -> dict:
    """
    批量下载多只股票数据

    Args:
        stock_codes: 股票代码列表
        start_date: 开始日期
        end_date: 结束日期
        provider_name: 数据提供者
        save_to_db: 是否保存到数据库

    Returns:
        dict: {股票代码: DataFrame}
    """
    logger.info(f"开始批量下载 {len(stock_codes)} 只股票...")

    results = {}
    success_count = 0
    fail_count = 0

    for i, code in enumerate(stock_codes, 1):
        try:
            logger.info(f"\n[{i}/{len(stock_codes)}] 处理 {code}")

            data = download_single_stock(
                stock_code=code,
                start_date=start_date,
                end_date=end_date,
                provider_name=provider_name,
                save_to_db=save_to_db
            )

            results[code] = data
            success_count += 1

        except Exception as e:
            logger.error(f"❌ {code} 下载失败: {e}")
            fail_count += 1
            continue

    # 汇总结果
    logger.info("\n" + "=" * 50)
    logger.info("下载完成!")
    logger.info(f"  成功: {success_count}/{len(stock_codes)}")
    logger.info(f"  失败: {fail_count}/{len(stock_codes)}")
    logger.info("=" * 50)

    return results


def download_index_components(
    index_code: str = '000300.SH',
    start_date: str = '2023-01-01',
    save_to_db: bool = True
) -> dict:
    """
    下载指数成分股数据

    Args:
        index_code: 指数代码（'000300.SH'=沪深300）
        start_date: 开始日期
        save_to_db: 是否保存到数据库

    Returns:
        dict: 成分股数据
    """
    logger.info(f"获取 {index_code} 成分股...")

    from src.utils.stock_utils import get_index_components

    # 获取成分股列表
    components = get_index_components(index_code)
    logger.info(f"✅ 获取了 {len(components)} 只成分股")

    # 批量下载
    return download_multiple_stocks(
        stock_codes=components,
        start_date=start_date,
        save_to_db=save_to_db
    )


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='A股数据下载工具')

    parser.add_argument(
        '--stock',
        type=str,
        default='000001.SZ',
        help='股票代码（默认：000001.SZ 平安银行）'
    )

    parser.add_argument(
        '--stocks',
        type=str,
        nargs='+',
        help='多只股票代码（如：000001.SZ 600000.SH）'
    )

    parser.add_argument(
        '--index',
        type=str,
        help='指数代码（如：000300.SH 沪深300）'
    )

    parser.add_argument(
        '--start',
        type=str,
        default=(datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d'),
        help='开始日期（默认：1年前）'
    )

    parser.add_argument(
        '--end',
        type=str,
        default=datetime.now().strftime('%Y-%m-%d'),
        help='结束日期（默认：今天）'
    )

    parser.add_argument(
        '--provider',
        type=str,
        default='akshare',
        choices=['akshare', 'tushare'],
        help='数据提供者（默认：akshare）'
    )

    parser.add_argument(
        '--no-db',
        action='store_true',
        help='不保存到数据库'
    )

    parser.add_argument(
        '--output',
        type=str,
        help='输出文件路径（CSV格式）'
    )

    args = parser.parse_args()

    try:
        # 场景1: 下载指数成分股
        if args.index:
            results = download_index_components(
                index_code=args.index,
                start_date=args.start,
                save_to_db=not args.no_db
            )

        # 场景2: 下载多只股票
        elif args.stocks:
            results = download_multiple_stocks(
                stock_codes=args.stocks,
                start_date=args.start,
                end_date=args.end,
                provider_name=args.provider,
                save_to_db=not args.no_db
            )

        # 场景3: 下载单只股票
        else:
            data = download_single_stock(
                stock_code=args.stock,
                start_date=args.start,
                end_date=args.end,
                provider_name=args.provider,
                save_to_db=not args.no_db
            )

            # 保存到文件（可选）
            if args.output:
                data.to_csv(args.output, index=False)
                logger.info(f"✅ 数据已保存到: {args.output}")

        logger.info("\n🎉 全部完成！")

    except Exception as e:
        logger.exception(f"❌ 程序执行失败: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
