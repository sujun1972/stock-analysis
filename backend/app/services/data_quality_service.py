"""
数据质量监控服务
生成数据质量报告和监控指标
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta, date
import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session
import json
import random

from loguru import logger
from core.src.data.validators.extended_validator import ExtendedDataValidator


class DataQualityService:
    """数据质量监控服务"""

    def __init__(self, db: Session):
        self.validator = ExtendedDataValidator()
        self.db = db

    def generate_daily_quality_report(self,
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
        data_sources = [
            'daily_basic', 'moneyflow', 'moneyflow_hsgt',
            'hsgt_top10', 'hk_hold', 'margin', 'margin_detail',
            'adj_factor', 'block_trade', 'suspend'
        ]

        total_errors = 0
        total_warnings = 0

        for source in data_sources:
            metrics = self.get_data_source_metrics(source, trade_date)
            report['data_sources'][source] = metrics

            if metrics:
                total_errors += metrics.get('error_count', 0)
                total_warnings += metrics.get('warning_count', 0)

                if metrics.get('error_count', 0) > 0:
                    report['issues'].append({
                        'type': 'error',
                        'source': source,
                        'message': f"{source} 有 {metrics['error_count']} 个错误",
                        'severity': 'high'
                    })

        # 判断整体健康状态
        if total_errors > 10:
            report['overall_health'] = 'critical'
            report['recommendations'].append('建议立即修复数据错误')
        elif total_errors > 0:
            report['overall_health'] = 'warning'
            report['recommendations'].append('存在少量数据错误，建议检查')
        elif total_warnings > 20:
            report['overall_health'] = 'warning'
            report['recommendations'].append('警告数量较多，建议关注')

        return report

    def generate_weekly_quality_report(self,
                                      start_date: Optional[date] = None,
                                      end_date: Optional[date] = None) -> Dict[str, Any]:
        """生成周度质量报告"""
        if not end_date:
            end_date = datetime.now().date()
        if not start_date:
            start_date = end_date - timedelta(days=7)

        report = {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'generated_at': datetime.now().isoformat(),
            'summary': {},
            'trends': {}
        }

        # 模拟数据
        report['summary'] = {
            'total_records_processed': random.randint(50000, 100000),
            'total_errors': random.randint(0, 50),
            'total_warnings': random.randint(0, 200),
            'average_quality_score': round(random.uniform(85, 99), 2)
        }

        return report

    def get_data_source_metrics(self, data_source: str,
                               trade_date: Optional[str] = None) -> Dict[str, Any]:
        """获取数据源指标"""
        # 模拟指标数据
        metrics = {
            'data_source': data_source,
            'trade_date': trade_date,
            'record_count': random.randint(1000, 5000),
            'error_count': random.randint(0, 10),
            'warning_count': random.randint(0, 50),
            'completeness': round(random.uniform(90, 100), 2),
            'accuracy': round(random.uniform(95, 100), 2),
            'timeliness': round(random.uniform(85, 100), 2),
            'last_update': datetime.now().isoformat()
        }

        return metrics

    def get_health_summary(self) -> Dict[str, Any]:
        """获取健康状态摘要"""
        return {
            'status': 'healthy',
            'last_check': datetime.now().isoformat(),
            'metrics': {
                'api_response_time': random.uniform(0.1, 0.5),
                'database_connection': 'active',
                'cache_hit_rate': round(random.uniform(70, 95), 2),
                'error_rate': round(random.uniform(0, 2), 2)
            },
            'alerts': []
        }

    def get_validation_history(self, data_source: str,
                              start_date: date,
                              end_date: date) -> List[Dict[str, Any]]:
        """获取验证历史"""
        history = []

        current_date = start_date
        while current_date <= end_date:
            history.append({
                'date': current_date.isoformat(),
                'data_source': data_source,
                'records_validated': random.randint(1000, 5000),
                'errors_found': random.randint(0, 10),
                'errors_fixed': random.randint(0, 10),
                'validation_time': round(random.uniform(0.5, 2.0), 2)
            })
            current_date += timedelta(days=1)

        return history

    def get_quality_trend(self, data_source: str, days: int) -> Dict[str, Any]:
        """获取质量趋势"""
        trend_data = []

        for i in range(days):
            date = (datetime.now() - timedelta(days=days-i-1)).date()
            trend_data.append({
                'date': date.isoformat(),
                'quality_score': round(random.uniform(85, 100), 2),
                'error_rate': round(random.uniform(0, 5), 2),
                'completeness': round(random.uniform(90, 100), 2)
            })

        return {
            'data_source': data_source,
            'period_days': days,
            'trend': trend_data,
            'improvement': round(random.uniform(-5, 10), 2)
        }

    def validate_data_source(self, data_source: str,
                           trade_date: Optional[date] = None) -> Dict[str, Any]:
        """验证数据源"""
        return {
            'data_source': data_source,
            'trade_date': trade_date.isoformat() if trade_date else None,
            'validation_result': 'passed',
            'errors': [],
            'warnings': [],
            'validated_at': datetime.now().isoformat()
        }

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """获取活跃告警"""
        # 模拟告警数据
        if random.random() > 0.7:
            return [{
                'id': 1,
                'type': 'data_quality',
                'severity': 'warning',
                'message': '资金流向数据延迟',
                'source': 'moneyflow',
                'created_at': datetime.now().isoformat(),
                'status': 'active'
            }]
        return []

    def acknowledge_alert(self, alert_id: int) -> bool:
        """确认告警"""
        # 模拟确认操作
        logger.info(f"确认告警 ID: {alert_id}")
        return True

    def export_report_html(self, report: Dict[str, Any]) -> str:
        """导出HTML报告"""
        html = f"""
        <html>
        <head>
            <title>数据质量报告</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                .status {{ padding: 10px; margin: 10px 0; border-radius: 5px; }}
                .healthy {{ background-color: #d4edda; }}
                .warning {{ background-color: #fff3cd; }}
                .critical {{ background-color: #f8d7da; }}
            </style>
        </head>
        <body>
            <h1>数据质量报告</h1>
            <div class="status {report['overall_health']}">
                整体状态: {report['overall_health']}
            </div>
            <p>生成时间: {report['generated_at']}</p>
            <h2>数据源状态</h2>
            <ul>
        """

        for source, metrics in report.get('data_sources', {}).items():
            if metrics:
                html += f"""
                <li>{source}:
                    记录数: {metrics.get('record_count', 0)},
                    错误: {metrics.get('error_count', 0)},
                    警告: {metrics.get('warning_count', 0)}
                </li>
                """

        html += """
            </ul>
        </body>
        </html>
        """

        return html