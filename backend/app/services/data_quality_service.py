"""
数据质量监控服务
生成数据质量报告和监控指标
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, date
import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import json
import random

from app.core.database import get_async_db
from app.utils.logger import logger
from core.src.data.validators.extended_validator import ExtendedDataValidator


class DataQualityService:
    """数据质量监控服务"""

    def __init__(self):
        self.validator = ExtendedDataValidator()

    async def generate_daily_quality_report(self,
                                           trade_date: Optional[str] = None) -> Dict[str, Any]:
        """
        生成每日数据质量报告

        Args:
            trade_date: 交易日期，默认为当天

        Returns:
            质量报告字典
        """
        if not trade_date:
            trade_date = datetime.now().strftime("%Y-%m-%d")

        logger.info(f"生成数据质量报告: {trade_date}")

        report = {
            'report_date': trade_date,
            'generated_at': datetime.now().isoformat(),
            'data_sources': {},
            'overall_health': 'healthy',
            'issues': [],
            'recommendations': []
        }

        # 检查各个数据源
        async with get_async_db() as db:
            # 1. 检查每日指标数据
            daily_basic_report = await self._check_daily_basic(db, trade_date)
            report['data_sources']['daily_basic'] = daily_basic_report

            # 2. 检查资金流向数据
            moneyflow_report = await self._check_moneyflow(db, trade_date)
            report['data_sources']['moneyflow'] = moneyflow_report

            # 3. 检查北向资金数据
            hk_hold_report = await self._check_hk_hold(db, trade_date)
            report['data_sources']['hk_hold'] = hk_hold_report

            # 4. 检查融资融券数据
            margin_report = await self._check_margin_detail(db, trade_date)
            report['data_sources']['margin_detail'] = margin_report

            # 5. 检查涨跌停价格数据
            stk_limit_report = await self._check_stk_limit(db, trade_date)
            report['data_sources']['stk_limit'] = stk_limit_report

        # 汇总健康状态
        report = self._summarize_health_status(report)

        # 生成改进建议
        report = self._generate_recommendations(report)

        return report

    async def _check_daily_basic(self, db: AsyncSession, trade_date: str) -> Dict[str, Any]:
        """检查每日指标数据质量"""
        try:
            # 查询数据
            query = text("""
                SELECT * FROM daily_basic
                WHERE trade_date = :trade_date
            """)
            result = await db.execute(query, {"trade_date": trade_date})
            rows = result.fetchall()

            if not rows:
                return {
                    'status': 'missing',
                    'record_count': 0,
                    'message': '无数据',
                    'validation_passed': False
                }

            # 转换为DataFrame
            df = pd.DataFrame([dict(row) for row in rows])

            # 验证数据
            is_valid, errors, warnings = self.validator.validate_daily_basic(df)

            # 统计覆盖率
            coverage_query = text("""
                SELECT COUNT(DISTINCT sb.ts_code) as total_stocks,
                       COUNT(DISTINCT db.ts_code) as covered_stocks
                FROM stock_basic sb
                LEFT JOIN daily_basic db ON sb.ts_code = db.ts_code
                    AND db.trade_date = :trade_date
                WHERE sb.status = 'L'
            """)
            coverage_result = await db.execute(coverage_query, {"trade_date": trade_date})
            coverage_row = coverage_result.fetchone()

            coverage_rate = 0
            if coverage_row and coverage_row.total_stocks > 0:
                coverage_rate = coverage_row.covered_stocks / coverage_row.total_stocks * 100

            return {
                'status': 'healthy' if is_valid and coverage_rate > 90 else 'warning' if is_valid else 'error',
                'record_count': len(df),
                'coverage_rate': f"{coverage_rate:.1f}%",
                'validation_passed': is_valid,
                'errors': errors[:5],  # 只保留前5个错误
                'warnings': warnings[:5],  # 只保留前5个警告
                'null_rate': (df.isnull().sum() / len(df)).mean() * 100,
                'last_update': df['created_at'].max().isoformat() if 'created_at' in df.columns else None
            }

        except Exception as e:
            logger.error(f"检查每日指标数据失败: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'validation_passed': False
            }

    async def _check_moneyflow(self, db: AsyncSession, trade_date: str) -> Dict[str, Any]:
        """检查资金流向数据质量"""
        try:
            query = text("""
                SELECT * FROM moneyflow
                WHERE trade_date = :trade_date
                LIMIT 1000
            """)
            result = await db.execute(query, {"trade_date": trade_date})
            rows = result.fetchall()

            if not rows:
                return {
                    'status': 'missing',
                    'record_count': 0,
                    'message': '无数据（可能未启用）',
                    'validation_passed': False
                }

            df = pd.DataFrame([dict(row) for row in rows])
            is_valid, errors, warnings = self.validator.validate_moneyflow(df)

            # 统计资金流向净值
            total_inflow = df[df['net_mf_amount'] > 0]['net_mf_amount'].sum() if 'net_mf_amount' in df.columns else 0
            total_outflow = abs(df[df['net_mf_amount'] < 0]['net_mf_amount'].sum()) if 'net_mf_amount' in df.columns else 0

            return {
                'status': 'healthy' if is_valid else 'warning' if len(errors) < 5 else 'error',
                'record_count': len(df),
                'validation_passed': is_valid,
                'errors': errors[:5],
                'warnings': warnings[:5],
                'total_inflow': float(total_inflow),
                'total_outflow': float(total_outflow),
                'net_flow': float(total_inflow - total_outflow)
            }

        except Exception as e:
            logger.error(f"检查资金流向数据失败: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'validation_passed': False
            }

    async def _check_hk_hold(self, db: AsyncSession, trade_date: str) -> Dict[str, Any]:
        """检查北向资金数据质量"""
        try:
            query = text("""
                SELECT * FROM hk_hold
                WHERE trade_date = :trade_date
            """)
            result = await db.execute(query, {"trade_date": trade_date})
            rows = result.fetchall()

            if not rows:
                return {
                    'status': 'missing',
                    'record_count': 0,
                    'message': '无数据',
                    'validation_passed': False
                }

            df = pd.DataFrame([dict(row) for row in rows])
            is_valid, errors, warnings = self.validator.validate_hk_hold(df)

            # 分别统计沪股通和深股通
            sh_count = len(df[df['exchange'] == 'SH']) if 'exchange' in df.columns else 0
            sz_count = len(df[df['exchange'] == 'SZ']) if 'exchange' in df.columns else 0

            return {
                'status': 'healthy' if is_valid else 'warning' if len(errors) < 3 else 'error',
                'record_count': len(df),
                'sh_count': sh_count,
                'sz_count': sz_count,
                'validation_passed': is_valid,
                'errors': errors[:5],
                'warnings': warnings[:5]
            }

        except Exception as e:
            logger.error(f"检查北向资金数据失败: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'validation_passed': False
            }

    async def _check_margin_detail(self, db: AsyncSession, trade_date: str) -> Dict[str, Any]:
        """检查融资融券数据质量"""
        try:
            query = text("""
                SELECT * FROM margin_detail
                WHERE trade_date = :trade_date
                LIMIT 1000
            """)
            result = await db.execute(query, {"trade_date": trade_date})
            rows = result.fetchall()

            if not rows:
                return {
                    'status': 'missing',
                    'record_count': 0,
                    'message': '无数据',
                    'validation_passed': False
                }

            df = pd.DataFrame([dict(row) for row in rows])
            is_valid, errors, warnings = self.validator.validate_margin_detail(df)

            # 统计两融总额
            total_rzye = df['rzye'].sum() if 'rzye' in df.columns else 0
            total_rqye = df['rqye'].sum() if 'rqye' in df.columns else 0

            return {
                'status': 'healthy' if is_valid else 'warning' if len(errors) < 3 else 'error',
                'record_count': len(df),
                'validation_passed': is_valid,
                'errors': errors[:5],
                'warnings': warnings[:5],
                'total_rzye': float(total_rzye),
                'total_rqye': float(total_rqye),
                'total_balance': float(total_rzye + total_rqye)
            }

        except Exception as e:
            logger.error(f"检查融资融券数据失败: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'validation_passed': False
            }

    async def _check_stk_limit(self, db: AsyncSession, trade_date: str) -> Dict[str, Any]:
        """检查涨跌停价格数据质量"""
        try:
            query = text("""
                SELECT * FROM stk_limit
                WHERE trade_date = :trade_date
                LIMIT 1000
            """)
            result = await db.execute(query, {"trade_date": trade_date})
            rows = result.fetchall()

            if not rows:
                return {
                    'status': 'missing',
                    'record_count': 0,
                    'message': '无数据',
                    'validation_passed': False
                }

            df = pd.DataFrame([dict(row) for row in rows])
            is_valid, errors, warnings = self.validator.validate_stk_limit(df)

            return {
                'status': 'healthy' if is_valid else 'warning' if len(errors) < 3 else 'error',
                'record_count': len(df),
                'validation_passed': is_valid,
                'errors': errors[:5],
                'warnings': warnings[:5]
            }

        except Exception as e:
            logger.error(f"检查涨跌停价格数据失败: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'validation_passed': False
            }

    def _summarize_health_status(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """汇总健康状态"""
        statuses = []
        total_errors = 0
        total_warnings = 0

        for source_name, source_report in report['data_sources'].items():
            if 'status' in source_report:
                statuses.append(source_report['status'])

                if source_report['status'] == 'error':
                    report['issues'].append(f"{source_name}: 数据质量错误")
                    total_errors += 1
                elif source_report['status'] == 'warning':
                    report['issues'].append(f"{source_name}: 数据质量警告")
                    total_warnings += 1
                elif source_report['status'] == 'missing':
                    report['issues'].append(f"{source_name}: 数据缺失")

        # 判断总体健康状态
        if 'error' in statuses or total_errors > 2:
            report['overall_health'] = 'critical'
        elif 'warning' in statuses or total_warnings > 3:
            report['overall_health'] = 'warning'
        elif 'missing' in statuses:
            report['overall_health'] = 'incomplete'
        else:
            report['overall_health'] = 'healthy'

        report['summary'] = {
            'total_sources': len(report['data_sources']),
            'healthy_sources': statuses.count('healthy'),
            'warning_sources': statuses.count('warning'),
            'error_sources': statuses.count('error'),
            'missing_sources': statuses.count('missing')
        }

        return report

    def _generate_recommendations(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """生成改进建议"""
        recommendations = []

        # 根据各数据源状态生成建议
        for source_name, source_report in report['data_sources'].items():
            if source_report.get('status') == 'missing':
                if source_name == 'moneyflow':
                    recommendations.append(
                        f"启用{source_name}数据同步（注意：消耗2000积分/次）"
                    )
                else:
                    recommendations.append(
                        f"检查{source_name}数据同步任务是否正常运行"
                    )

            elif source_report.get('status') == 'error':
                recommendations.append(
                    f"立即检查{source_name}数据源，存在数据质量问题"
                )

            elif source_report.get('status') == 'warning':
                if 'coverage_rate' in source_report:
                    coverage = float(source_report['coverage_rate'].rstrip('%'))
                    if coverage < 90:
                        recommendations.append(
                            f"提高{source_name}数据覆盖率（当前{coverage:.1f}%）"
                        )

        # 通用建议
        if report['overall_health'] == 'critical':
            recommendations.insert(0, "⚠️ 数据质量存在严重问题，建议立即处理")
        elif report['overall_health'] == 'warning':
            recommendations.insert(0, "建议关注数据质量警告，优化数据同步策略")

        report['recommendations'] = recommendations[:10]  # 最多10条建议

        return report

    async def generate_weekly_report(self) -> Dict[str, Any]:
        """
        生成周度数据质量报告

        Returns:
            周度报告字典
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        logger.info(f"生成周度质量报告: {start_date.date()} 至 {end_date.date()}")

        weekly_report = {
            'report_type': 'weekly',
            'start_date': start_date.strftime("%Y-%m-%d"),
            'end_date': end_date.strftime("%Y-%m-%d"),
            'generated_at': datetime.now().isoformat(),
            'daily_reports': [],
            'trends': {},
            'summary': {}
        }

        # 获取每日报告
        current_date = start_date
        while current_date <= end_date:
            daily_report = await self.generate_daily_quality_report(
                current_date.strftime("%Y-%m-%d")
            )
            weekly_report['daily_reports'].append(daily_report)
            current_date += timedelta(days=1)

        # 分析趋势
        weekly_report = self._analyze_weekly_trends(weekly_report)

        return weekly_report

    def _analyze_weekly_trends(self, weekly_report: Dict[str, Any]) -> Dict[str, Any]:
        """分析周度趋势"""
        health_statuses = []
        source_statuses = {}

        for daily_report in weekly_report['daily_reports']:
            health_statuses.append(daily_report['overall_health'])

            # 统计各数据源状态
            for source_name, source_report in daily_report['data_sources'].items():
                if source_name not in source_statuses:
                    source_statuses[source_name] = []
                source_statuses[source_name].append(source_report.get('status', 'unknown'))

        # 计算健康天数
        healthy_days = health_statuses.count('healthy')
        warning_days = health_statuses.count('warning')
        critical_days = health_statuses.count('critical')

        weekly_report['summary'] = {
            'total_days': len(health_statuses),
            'healthy_days': healthy_days,
            'warning_days': warning_days,
            'critical_days': critical_days,
            'health_score': (healthy_days * 100 + warning_days * 50) / len(health_statuses) if health_statuses else 0
        }

        # 分析各数据源趋势
        weekly_report['trends'] = {}
        for source_name, statuses in source_statuses.items():
            weekly_report['trends'][source_name] = {
                'healthy_rate': statuses.count('healthy') / len(statuses) * 100 if statuses else 0,
                'missing_rate': statuses.count('missing') / len(statuses) * 100 if statuses else 0,
                'error_rate': statuses.count('error') / len(statuses) * 100 if statuses else 0
            }

        return weekly_report

    async def get_realtime_metrics(self) -> Dict[str, Any]:
        """
        获取实时数据质量指标

        Returns:
            实时指标字典
        """
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'data_sources': {}
        }

        async with get_async_db() as db:
            # 获取各数据源最新状态
            for table_name in ['daily_basic', 'moneyflow', 'hk_hold', 'margin_detail', 'stk_limit']:
                query = text(f"""
                    SELECT
                        COUNT(*) as total_records,
                        MAX(trade_date) as latest_date,
                        MAX(created_at) as last_update
                    FROM {table_name}
                """)

                result = await db.execute(query)
                row = result.fetchone()

                metrics['data_sources'][table_name] = {
                    'total_records': row.total_records if row else 0,
                    'latest_date': row.latest_date.isoformat() if row and row.latest_date else None,
                    'last_update': row.last_update.isoformat() if row and row.last_update else None,
                    'is_stale': self._is_data_stale(row.latest_date) if row and row.latest_date else True
                }

        return metrics

    def _is_data_stale(self, latest_date) -> bool:
        """判断数据是否过期"""
        if not latest_date:
            return True

        # 如果最新数据超过2天，认为是过期的
        days_diff = (datetime.now().date() - latest_date).days
        return days_diff > 2

    async def export_report(self, report: Dict[str, Any], format: str = 'json') -> str:
        """
        导出质量报告

        Args:
            report: 报告数据
            format: 导出格式（json/html/csv）

        Returns:
            导出的内容字符串
        """
        if format == 'json':
            return json.dumps(report, ensure_ascii=False, indent=2, default=str)

        elif format == 'html':
            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>数据质量报告</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    h1 { color: #333; }
                    .status-healthy { color: green; }
                    .status-warning { color: orange; }
                    .status-error { color: red; }
                    table { border-collapse: collapse; width: 100%; }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                    th { background-color: #f2f2f2; }
                </style>
            </head>
            <body>
                <h1>数据质量报告</h1>
                <p>生成时间: {generated_at}</p>
                <p>报告日期: {report_date}</p>
                <h2>总体状态: <span class="status-{overall_health}">{overall_health}</span></h2>

                <h3>数据源状态</h3>
                <table>
                    <tr>
                        <th>数据源</th>
                        <th>状态</th>
                        <th>记录数</th>
                        <th>验证结果</th>
                    </tr>
                    {source_rows}
                </table>

                <h3>问题列表</h3>
                <ul>
                    {issues}
                </ul>

                <h3>改进建议</h3>
                <ul>
                    {recommendations}
                </ul>
            </body>
            </html>
            """

            # 构建数据源行
            source_rows = ""
            for name, source in report.get('data_sources', {}).items():
                source_rows += f"""
                    <tr>
                        <td>{name}</td>
                        <td class="status-{source.get('status', 'unknown')}">{source.get('status', 'unknown')}</td>
                        <td>{source.get('record_count', 0)}</td>
                        <td>{'✓' if source.get('validation_passed') else '✗'}</td>
                    </tr>
                """

            # 构建问题列表
            issues = "".join([f"<li>{issue}</li>" for issue in report.get('issues', [])])

            # 构建建议列表
            recommendations = "".join([f"<li>{rec}</li>" for rec in report.get('recommendations', [])])

            return html_template.format(
                generated_at=report.get('generated_at', ''),
                report_date=report.get('report_date', ''),
                overall_health=report.get('overall_health', ''),
                source_rows=source_rows,
                issues=issues or "<li>无</li>",
                recommendations=recommendations or "<li>无</li>"
            )

        else:
            return json.dumps(report, ensure_ascii=False, indent=2, default=str)

    async def get_active_alerts(self) -> List[Dict[str, Any]]:
        """获取活跃的质量告警"""
        query = """
            SELECT
                a.*,
                c.name as config_name,
                c.description as config_description
            FROM quality_alerts a
            JOIN quality_alert_configs c ON a.config_id = c.id
            WHERE a.status = 'active'
            ORDER BY a.created_at DESC
            LIMIT 100
        """

        result = await self.db.execute(text(query))
        alerts = []

        for row in result:
            alerts.append({
                "id": row.id,
                "config_id": row.config_id,
                "config_name": row.config_name,
                "data_source": row.data_source,
                "metric_type": row.metric_type,
                "metric_value": float(row.metric_value) if row.metric_value else None,
                "threshold_value": float(row.threshold_value) if row.threshold_value else None,
                "severity": row.severity,
                "status": row.status,
                "message": row.message,
                "details": row.details,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "acknowledged": row.acknowledged_at is not None
            })

        return alerts

    async def acknowledge_alert(self, alert_id: int) -> bool:
        """确认告警"""
        query = """
            UPDATE quality_alerts
            SET
                status = 'acknowledged',
                acknowledged_at = CURRENT_TIMESTAMP
            WHERE id = :alert_id AND status = 'active'
        """

        result = await self.db.execute(
            text(query),
            {"alert_id": alert_id}
        )
        await self.db.commit()

        return result.rowcount > 0

    async def get_validation_history(
        self,
        data_source: str,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """获取数据验证历史记录"""
        # 这里简化实现，实际应该从验证日志表读取
        return []

    async def get_quality_trend(
        self,
        data_source: str,
        days: int
    ) -> List[Dict[str, Any]]:
        """获取质量趋势数据"""
        # 这里简化实现，实际应该计算历史趋势
        trends = []
        end_date = datetime.now().date()

        for i in range(days):
            current_date = end_date - timedelta(days=i)
            trends.append({
                "date": current_date.isoformat(),
                "completeness": 95 + random.uniform(-5, 5),
                "accuracy": 98 + random.uniform(-3, 2),
                "timeliness": 96 + random.uniform(-4, 4)
            })

        return trends

    async def validate_data_source(
        self,
        data_source: str,
        trade_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """手动触发数据源验证"""
        validator = ExtendedDataValidator()

        # 获取数据
        if not trade_date:
            trade_date = datetime.now().date()

        query = f"""
            SELECT * FROM {data_source}
            WHERE trade_date = :trade_date
            LIMIT 10000
        """

        try:
            result = await self.db.execute(
                text(query),
                {"trade_date": trade_date}
            )

            data = result.fetchall()

            if not data:
                return {
                    "valid": False,
                    "errors": ["No data found for the specified date"],
                    "warnings": [],
                    "record_count": 0
                }

            # 转换为DataFrame进行验证
            df = pd.DataFrame(data)

            # 根据数据源选择验证方法
            validation_methods = {
                'daily_basic': validator.validate_daily_basic,
                'moneyflow': validator.validate_moneyflow,
                'moneyflow_hsgt': validator.validate_moneyflow_hsgt,
                'hsgt_top10': validator.validate_hsgt_top10,
                'hk_hold': validator.validate_hk_hold,
                'margin': validator.validate_margin,
                'margin_detail': validator.validate_margin_detail,
                'stk_limit': validator.validate_stk_limit,
                'adj_factor': validator.validate_adj_factor
            }

            if data_source in validation_methods:
                valid, errors, warnings = validation_methods[data_source](df)
                return {
                    "valid": valid,
                    "errors": errors,
                    "warnings": warnings,
                    "record_count": len(df)
                }
            else:
                return {
                    "valid": True,
                    "errors": [],
                    "warnings": ["No specific validation rules for this data source"],
                    "record_count": len(df)
                }

        except Exception as e:
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": [],
                "record_count": 0
            }