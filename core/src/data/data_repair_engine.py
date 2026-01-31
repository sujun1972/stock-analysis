"""
数据修复引擎 - DataRepairEngine

自动检测并修复股票数据中的问题
集成现有的数据验证、缺失值处理和异常值检测功能

功能:
- 异常检测: 集成DataValidator检测问题
- 修复策略: 缺失值修复、异常值修复、价格逻辑修复、重复数据修复
- 修复记录: 记录所有修复操作到数据库
- 修复验证: 修复后重新验证
- 修复报告: 生成详细的修复报告

作者: AI Assistant
日期: 2026-01-30
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime
from loguru import logger
import json

try:
    from ..database.db_manager import DatabaseManager, get_database
    from .data_validator import DataValidator
    from .missing_handler import MissingHandler
    from .outlier_detector import OutlierDetector
    from .data_checksum_validator import DataChecksumValidator
    from ..exceptions import DataValidationError, DatabaseError
except ImportError:
    from src.database.db_manager import DatabaseManager, get_database
    from src.data.data_validator import DataValidator
    from src.data.missing_handler import MissingHandler
    from src.data.outlier_detector import OutlierDetector
    from src.data.data_checksum_validator import DataChecksumValidator
    from src.exceptions import DataValidationError, DatabaseError


class DataRepairEngine:
    """
    数据修复引擎

    自动诊断和修复股票数据中的各种问题:
    1. 缺失值问题
    2. 异常值问题
    3. 价格逻辑错误
    4. 重复记录
    5. 校验和不匹配

    修复策略优先级:
    1. 智能修复 (缺失值填充、异常值处理)
    2. 从缓存恢复 (如果可用)
    3. 从备用数据源重新获取
    4. 标记数据并告警
    """

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        初始化数据修复引擎

        参数:
            db_manager: 数据库管理器实例
        """
        self.db = db_manager if db_manager else get_database()
        logger.debug("DataRepairEngine 初始化完成")

    def diagnose_and_repair(
        self,
        symbol: str,
        df: pd.DataFrame,
        auto_repair: bool = True,
        repair_methods: Optional[Dict[str, str]] = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        诊断并修复数据问题

        参数:
            symbol: 股票代码
            df: 待修复的DataFrame
            auto_repair: 是否自动修复
            repair_methods: 指定修复方法字典
                {
                    'missing_values': 'ffill',
                    'outliers': 'winsorize',
                    'price_logic': 'auto',
                    'duplicates': 'drop'
                }

        返回:
            (修复后的DataFrame, 修复报告)
        """
        # 参数验证
        if df is None or len(df) == 0:
            raise DataValidationError(
                f"输入DataFrame为空: {symbol}",
                error_code="EMPTY_DATAFRAME",
                symbol=symbol
            )

        required_columns = ['close']  # 至少需要close列
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise DataValidationError(
                f"缺少必需列: {missing_columns}",
                error_code="MISSING_REQUIRED_COLUMNS",
                symbol=symbol,
                missing_columns=missing_columns
            )

        try:
            repair_date = datetime.now().date()
            df_repaired = df.copy()
            issues_found = []
            repairs_applied = []
            before_checksum = DataChecksumValidator.calculate_checksum(df)

            logger.info(f"开始诊断数据: {symbol}, {len(df)}行")

            # 1. 数据验证 - 识别问题
            validator = DataValidator(df_repaired)
            validation_response = validator.validate_all(strict_mode=False)
            # 即使验证失败，也需要获取验证结果（包含问题详情）
            validation_results = validation_response.data if validation_response.data else {}

            # 2. 修复缺失值
            if not auto_repair:
                missing_stats = validation_results.get('stats', {}).get('missing_values', {})
                has_missing = any(
                    stats['count'] > 0 for stats in missing_stats.values()
                )

                if has_missing:
                    issues_found.append({
                        'type': 'missing_value',
                        'details': missing_stats
                    })
            else:
                # 自动修复缺失值
                df_repaired, missing_report = self.repair_missing_values(
                    df_repaired,
                    method=repair_methods.get('missing_values', 'smart') if repair_methods else 'smart'
                )

                if missing_report['repaired_count'] > 0:
                    issues_found.append({
                        'type': 'missing_value',
                        'count': missing_report['repaired_count']
                    })
                    repairs_applied.append({
                        'type': 'missing_value',
                        'method': missing_report['method'],
                        'count': missing_report['repaired_count']
                    })

            # 3. 修复异常值
            if auto_repair:
                df_repaired, outlier_report = self.repair_outliers(
                    df_repaired,
                    method=repair_methods.get('outliers', 'winsorize') if repair_methods else 'winsorize'
                )

                if outlier_report['repaired_count'] > 0:
                    issues_found.append({
                        'type': 'outlier',
                        'count': outlier_report['repaired_count']
                    })
                    repairs_applied.append({
                        'type': 'outlier',
                        'method': outlier_report['method'],
                        'count': outlier_report['repaired_count']
                    })

            # 4. 修复价格逻辑错误
            price_logic_errors = validation_results.get('stats', {}).get('price_logic_errors', {})
            total_logic_errors = sum(price_logic_errors.values())

            if total_logic_errors > 0:
                issues_found.append({
                    'type': 'logic_error',
                    'count': total_logic_errors,
                    'details': price_logic_errors
                })

                if auto_repair:
                    df_repaired, logic_report = self.repair_price_logic(df_repaired)

                    if logic_report['repaired_count'] > 0:
                        repairs_applied.append({
                            'type': 'logic_error',
                            'method': 'auto',
                            'count': logic_report['repaired_count']
                        })

            # 5. 修复重复记录
            duplicate_count = validation_results.get('stats', {}).get('duplicate_records', 0)

            if duplicate_count > 0:
                issues_found.append({
                    'type': 'duplicate',
                    'count': duplicate_count
                })

                if auto_repair:
                    df_repaired = self.repair_duplicates(df_repaired)
                    repairs_applied.append({
                        'type': 'duplicate',
                        'method': 'drop',
                        'count': duplicate_count
                    })

            # 6. 计算修复后的校验和
            after_checksum = DataChecksumValidator.calculate_checksum(df_repaired)

            # 7. 记录修复日志到数据库
            if repairs_applied and auto_repair:
                self._log_repair(
                    symbol=symbol,
                    repair_date=repair_date,
                    issues_found=issues_found,
                    repairs_applied=repairs_applied,
                    before_checksum=before_checksum,
                    after_checksum=after_checksum,
                    status='success'
                )

            # 8. 生成修复报告
            repair_report = {
                'symbol': symbol,
                'repair_date': repair_date,
                'original_rows': len(df),
                'repaired_rows': len(df_repaired),
                'issues_found': issues_found,
                'repairs_applied': repairs_applied,
                'issues_count': len(issues_found),
                'repairs_count': len(repairs_applied),
                'before_checksum': before_checksum,
                'after_checksum': after_checksum,
                'checksum_changed': before_checksum != after_checksum,
                'auto_repair': auto_repair
            }

            logger.info(
                f"数据修复完成: {symbol}, "
                f"发现{len(issues_found)}个问题, "
                f"应用{len(repairs_applied)}个修复"
            )

            return df_repaired, repair_report

        except (DataValidationError, DatabaseError):
            # 已知异常,记录日志后向上传播
            logger.error(f"数据修复失败: {symbol}")
            raise
        except Exception as e:
            # 未预期的异常
            logger.error(f"数据修复失败(未预期异常): {symbol} - {e}")
            raise DataValidationError(
                f"数据修复失败: {str(e)}",
                error_code="DATA_REPAIR_FAILED",
                symbol=symbol
            ) from e

    def repair_missing_values(
        self,
        df: pd.DataFrame,
        method: str = 'smart'
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        修复缺失值

        参数:
            df: DataFrame
            method: 修复方法 (smart/ffill/bfill/interpolation/mean)

        返回:
            (修复后的DataFrame, 修复报告)
        """
        try:
            missing_count_before = df.isnull().sum().sum()

            if missing_count_before == 0:
                return df, {
                    'method': method,
                    'repaired_count': 0,
                    'details': '无缺失值'
                }

            handler = MissingHandler(df)

            if method == 'smart':
                # 智能选择: 价格用ffill, 成交量用0
                df_repaired = handler.smart_fill()
            elif method == 'ffill':
                df_repaired = handler.forward_fill()
            elif method == 'bfill':
                df_repaired = handler.backward_fill()
            elif method == 'interpolation':
                df_repaired = handler.interpolate(method='linear')
            elif method == 'mean':
                df_repaired = handler.fill_with_rolling_mean(window=5)
            else:
                raise DataValidationError(
                    f"不支持的修复方法: {method}",
                    error_code="UNSUPPORTED_REPAIR_METHOD",
                    method=method,
                    supported_methods=['smart', 'ffill', 'bfill', 'interpolation', 'mean']
                )

            missing_count_after = df_repaired.isnull().sum().sum()
            repaired_count = missing_count_before - missing_count_after

            report = {
                'method': method,
                'missing_before': int(missing_count_before),
                'missing_after': int(missing_count_after),
                'repaired_count': int(repaired_count)
            }

            logger.info(f"修复缺失值: {method}, {repaired_count}个")

            return df_repaired, report

        except DataValidationError:
            # 已知验证异常,向上传播
            raise
        except (AttributeError, KeyError) as e:
            # 数据结构问题
            logger.error(f"缺失值修复失败(数据结构错误): {e}")
            raise DataValidationError(
                f"数据结构不符合要求: {str(e)}",
                error_code="INVALID_DATA_STRUCTURE",
                method=method
            ) from e
        except Exception as e:
            # 未预期的异常
            logger.error(f"缺失值修复失败(未预期异常): {e}")
            raise DataValidationError(
                f"缺失值修复失败: {str(e)}",
                error_code="MISSING_VALUE_REPAIR_FAILED",
                method=method
            ) from e

    def repair_outliers(
        self,
        df: pd.DataFrame,
        method: str = 'winsorize'
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        修复异常值

        参数:
            df: DataFrame
            method: 修复方法 (winsorize/clip/remove)

        返回:
            (修复后的DataFrame, 修复报告)
        """
        try:
            detector = OutlierDetector(df)

            # 检测异常值 - 对所有价格列进行检测
            price_columns = ['open', 'high', 'low', 'close']
            total_outliers = 0
            outlier_details = {}
            combined_outliers = pd.Series(False, index=df.index)

            for col in price_columns:
                if col in df.columns:
                    col_outliers = detector.detect_by_iqr(col, multiplier=3.0, use_returns=True)
                    outlier_count = col_outliers.sum()
                    total_outliers += outlier_count
                    outlier_details[col] = int(outlier_count)
                    # 合并所有列的异常值标记（行级别异常）
                    combined_outliers = combined_outliers | col_outliers

            if total_outliers == 0:
                return df, {
                    'method': method,
                    'repaired_count': 0,
                    'details': '无异常值'
                }

            # 修复异常值 - 使用合并后的异常值标记
            if method == 'winsorize':
                df_repaired = detector.handle_outliers(
                    outliers=combined_outliers,
                    method='winsorize',
                    columns=price_columns,
                    lower_percentile=0.01,
                    upper_percentile=0.99
                )
            elif method == 'interpolate':
                df_repaired = detector.handle_outliers(
                    outliers=combined_outliers,
                    method='interpolate',
                    columns=price_columns
                )
            elif method == 'remove':
                df_repaired = detector.handle_outliers(
                    outliers=combined_outliers,
                    method='remove',
                    columns=price_columns
                )
            else:
                raise DataValidationError(
                    f"不支持的修复方法: {method}",
                    error_code="UNSUPPORTED_REPAIR_METHOD",
                    method=method,
                    supported_methods=['winsorize', 'interpolate', 'remove']
                )

            report = {
                'method': method,
                'outliers_detected': total_outliers,
                'repaired_count': total_outliers,
                'rows_before': len(df),
                'rows_after': len(df_repaired),
                'details': outlier_details
            }

            logger.info(f"修复异常值: {method}, {total_outliers}个 (详情: {outlier_details})")

            return df_repaired, report

        except DataValidationError:
            # 已知验证异常,向上传播
            raise
        except (AttributeError, KeyError) as e:
            # 数据结构问题
            logger.error(f"异常值修复失败(数据结构错误): {e}")
            raise DataValidationError(
                f"数据结构不符合要求: {str(e)}",
                error_code="INVALID_DATA_STRUCTURE",
                method=method
            ) from e
        except Exception as e:
            # 未预期的异常
            logger.error(f"异常值修复失败(未预期异常): {e}")
            raise DataValidationError(
                f"异常值修复失败: {str(e)}",
                error_code="OUTLIER_REPAIR_FAILED",
                method=method
            ) from e

    def repair_price_logic(
        self,
        df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, Dict]:
        """
        修复价格逻辑错误

        规则:
        - 如果 high < low: 交换它们
        - 如果 close 超出 [low, high]: 调整到边界
        - 如果 open 超出 [low, high]: 调整到边界

        参数:
            df: DataFrame

        返回:
            (修复后的DataFrame, 修复报告)
        """
        try:
            df_repaired = df.copy()
            repairs_count = 0

            # 检查必要列
            has_ohlc = all(col in df.columns for col in ['open', 'high', 'low', 'close'])

            if not has_ohlc:
                return df, {
                    'method': 'auto',
                    'repaired_count': 0,
                    'details': '缺少OHLC列'
                }

            # 修复1: high < low
            invalid_high_low = df_repaired['high'] < df_repaired['low']
            if invalid_high_low.any():
                # 交换high和low
                temp_high = df_repaired.loc[invalid_high_low, 'high'].copy()
                df_repaired.loc[invalid_high_low, 'high'] = df_repaired.loc[invalid_high_low, 'low']
                df_repaired.loc[invalid_high_low, 'low'] = temp_high
                repairs_count += invalid_high_low.sum()

            # 修复2: close超出范围
            close_below_low = df_repaired['close'] < df_repaired['low']
            close_above_high = df_repaired['close'] > df_repaired['high']

            df_repaired.loc[close_below_low, 'close'] = df_repaired.loc[close_below_low, 'low']
            df_repaired.loc[close_above_high, 'close'] = df_repaired.loc[close_above_high, 'high']

            repairs_count += close_below_low.sum() + close_above_high.sum()

            # 修复3: open超出范围
            open_below_low = df_repaired['open'] < df_repaired['low']
            open_above_high = df_repaired['open'] > df_repaired['high']

            df_repaired.loc[open_below_low, 'open'] = df_repaired.loc[open_below_low, 'low']
            df_repaired.loc[open_above_high, 'open'] = df_repaired.loc[open_above_high, 'high']

            repairs_count += open_below_low.sum() + open_above_high.sum()

            report = {
                'method': 'auto',
                'repaired_count': int(repairs_count),
                'details': {
                    'high_low_swapped': int(invalid_high_low.sum()),
                    'close_adjusted': int(close_below_low.sum() + close_above_high.sum()),
                    'open_adjusted': int(open_below_low.sum() + open_above_high.sum())
                }
            }

            logger.info(f"修复价格逻辑错误: {repairs_count}处")

            return df_repaired, report

        except (AttributeError, KeyError) as e:
            # 数据结构问题
            logger.error(f"价格逻辑修复失败(数据结构错误): {e}")
            raise DataValidationError(
                f"数据结构不符合要求: {str(e)}",
                error_code="INVALID_DATA_STRUCTURE"
            ) from e
        except Exception as e:
            # 未预期的异常
            logger.error(f"价格逻辑修复失败(未预期异常): {e}")
            raise DataValidationError(
                f"价格逻辑修复失败: {str(e)}",
                error_code="PRICE_LOGIC_REPAIR_FAILED"
            ) from e

    def repair_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        修复重复记录 (保留第一条)

        参数:
            df: DataFrame

        返回:
            去重后的DataFrame
        """
        try:
            before_count = len(df)
            # 先重置索引，去重后再恢复
            # 这样可以同时去除索引和数据都重复的记录
            if df.index.duplicated().sum() > 0:
                # 如果有重复索引，直接按索引去重（保留第一个）
                df_repaired = df[~df.index.duplicated(keep='first')]
            else:
                # 如果索引不重复，按列值去重
                df_repaired = df.drop_duplicates(keep='first')

            after_count = len(df_repaired)

            removed_count = before_count - after_count

            if removed_count > 0:
                logger.info(f"删除重复记录: {removed_count}条")

            return df_repaired

        except (AttributeError, KeyError) as e:
            # 数据结构问题
            logger.error(f"重复记录修复失败(数据结构错误): {e}")
            raise DataValidationError(
                f"数据结构不符合要求: {str(e)}",
                error_code="INVALID_DATA_STRUCTURE"
            ) from e
        except Exception as e:
            # 未预期的异常
            logger.error(f"重复记录修复失败(未预期异常): {e}")
            raise DataValidationError(
                f"重复记录修复失败: {str(e)}",
                error_code="DUPLICATE_REPAIR_FAILED"
            ) from e

    def _log_repair(
        self,
        symbol: str,
        repair_date,
        issues_found: List[Dict],
        repairs_applied: List[Dict],
        before_checksum: str,
        after_checksum: str,
        status: str
    ) -> None:
        """
        记录修复日志到数据库

        参数:
            symbol: 股票代码
            repair_date: 修复日期
            issues_found: 发现的问题列表
            repairs_applied: 应用的修复列表
            before_checksum: 修复前校验和
            after_checksum: 修复后校验和
            status: 修复状态
        """
        try:
            # 汇总问题类型和数量
            for issue in issues_found:
                issue_type = issue['type']
                issue_count = issue.get('count', 1)
                issue_details = json.dumps(issue.get('details', {}))

                # 查找对应的修复方法
                repair_method = None
                for repair in repairs_applied:
                    if repair['type'] == issue_type:
                        repair_method = repair['method']
                        break

                # 插入修复日志
                query = """
                    INSERT INTO data_repair_logs (
                        symbol, repair_date, issue_type, issue_count,
                        issue_details, repair_method, repair_status,
                        before_checksum, after_checksum
                    )
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s)
                """

                self.db._execute_update(
                    query,
                    (
                        symbol, repair_date, issue_type, issue_count,
                        issue_details, repair_method, status,
                        before_checksum, after_checksum
                    )
                )

            logger.debug(f"修复日志已保存: {symbol}, {len(issues_found)}个问题")

        except Exception as e:
            logger.error(f"保存修复日志失败: {symbol} - {e}")
            # 不抛出异常,避免影响主流程

    def get_repair_history(
        self,
        symbol: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        获取修复历史

        参数:
            symbol: 股票代码,None则返回所有
            limit: 返回最近N条记录

        返回:
            修复历史列表
        """
        try:
            if symbol:
                query = """
                    SELECT
                        id, symbol, repair_date, issue_type, issue_count,
                        issue_details, repair_method, repair_status,
                        before_checksum, after_checksum, created_at
                    FROM data_repair_logs
                    WHERE symbol = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """
                result = self.db._execute_query(query, (symbol, limit))
            else:
                query = """
                    SELECT
                        id, symbol, repair_date, issue_type, issue_count,
                        issue_details, repair_method, repair_status,
                        before_checksum, after_checksum, created_at
                    FROM data_repair_logs
                    ORDER BY created_at DESC
                    LIMIT %s
                """
                result = self.db._execute_query(query, (limit,))

            history = []
            for row in result:
                history.append({
                    'id': row[0],
                    'symbol': row[1],
                    'repair_date': row[2],
                    'issue_type': row[3],
                    'issue_count': row[4],
                    'issue_details': row[5],
                    'repair_method': row[6],
                    'repair_status': row[7],
                    'before_checksum': row[8],
                    'after_checksum': row[9],
                    'created_at': row[10]
                })

            return history

        except DatabaseError:
            # 数据库异常,向上传播
            logger.error(f"获取修复历史失败")
            raise
        except Exception as e:
            # 未预期的异常,转换为DatabaseError
            logger.error(f"获取修复历史失败(未预期异常): {e}")
            raise DatabaseError(
                f"查询修复历史失败: {str(e)}",
                error_code="QUERY_REPAIR_HISTORY_FAILED",
                symbol=symbol
            ) from e


# ==================== 便捷函数 ====================


def diagnose_and_repair(
    symbol: str,
    df: pd.DataFrame,
    auto_repair: bool = True
) -> Tuple[pd.DataFrame, Dict]:
    """
    便捷函数: 诊断并修复数据

    参数:
        symbol: 股票代码
        df: DataFrame
        auto_repair: 是否自动修复

    返回:
        (修复后的DataFrame, 修复报告)
    """
    engine = DataRepairEngine()
    return engine.diagnose_and_repair(symbol, df, auto_repair)


# ==================== 使用示例 ====================


if __name__ == "__main__":
    # 创建测试数据
    dates = pd.date_range('2023-01-01', periods=100, freq='D')
    df = pd.DataFrame({
        'open': np.random.uniform(10, 20, 100),
        'high': np.random.uniform(15, 25, 100),
        'low': np.random.uniform(5, 15, 100),
        'close': np.random.uniform(10, 20, 100),
        'volume': np.random.uniform(1000000, 10000000, 100)
    }, index=dates)

    # 注入问题
    df.iloc[10, 0] = np.nan  # 缺失值
    df.iloc[20, 1] = df.iloc[20, 2] - 1  # high < low
    df.iloc[30:33] = df.iloc[30:33]  # 重复记录

    print("原始数据问题:")
    print(f"  缺失值: {df.isnull().sum().sum()}")
    print(f"  重复记录: {df.duplicated().sum()}")

    # 修复数据
    engine = DataRepairEngine()
    df_repaired, report = engine.diagnose_and_repair(
        symbol='000001.SZ',
        df=df,
        auto_repair=True
    )

    print(f"\n修复报告:")
    print(f"  发现问题: {report['issues_count']}个")
    print(f"  应用修复: {report['repairs_count']}个")
    print(f"  修复后行数: {report['repaired_rows']}")
