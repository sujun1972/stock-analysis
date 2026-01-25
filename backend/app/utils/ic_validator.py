"""
IC异常检测与告警模块
用于检测模型训练中的数据泄露和过拟合问题
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
from datetime import datetime


class AlertLevel(Enum):
    """告警级别"""
    CRITICAL = "critical"  # 严重：明确的数据泄露
    WARNING = "warning"    # 警告：可疑的高IC
    INFO = "info"          # 信息：需要注意
    OK = "ok"              # 正常


@dataclass
class ICAlert:
    """IC告警"""
    level: AlertLevel
    message: str
    ic_value: float
    dataset: str
    check_type: str
    suggestion: str = ""


class ICValidator:
    """
    IC验证器
    检测训练过程中的IC异常，防止数据泄露
    """

    # IC阈值配置
    THRESHOLDS = {
        'test_ic': {
            'critical': 0.5,    # >0.5 严重异常，几乎确定数据泄露
            'warning': 0.3,     # >0.3 警告，高度可疑
            'caution': 0.2,     # >0.2 需要注意
            'excellent': 0.15,  # 0.10-0.15 优秀
            'good': 0.1,        # 0.05-0.10 良好
            'acceptable': 0.05  # 0.01-0.05 可接受
        },
        'train_ic': {
            'critical': 0.8,    # >0.8 严重过拟合
            'warning': 0.6,     # >0.6 警告
            'caution': 0.4,     # >0.4 需要注意
            'normal': 0.3       # <0.3 正常
        },
        'ic_gap': {
            'critical': 0.6,    # Train-Test > 0.6 严重
            'warning': 0.4,     # Train-Test > 0.4 警告
            'caution': 0.25,    # Train-Test > 0.25 需要注意
            'normal': 0.15      # Train-Test < 0.15 正常
        }
    }

    def __init__(self, alert_log_dir: str = "logs/ic_alerts"):
        """
        初始化IC验证器

        参数:
            alert_log_dir: 告警日志目录
        """
        self.alert_log_dir = Path(alert_log_dir)
        self.alert_log_dir.mkdir(parents=True, exist_ok=True)

    def validate_all(
        self,
        train_ic: float,
        valid_ic: float,
        test_ic: float,
        train_r2: Optional[float] = None,
        test_r2: Optional[float] = None,
        model_id: Optional[str] = None,
        symbol: Optional[str] = None
    ) -> Tuple[bool, List[ICAlert]]:
        """
        执行全面的IC验证

        参数:
            train_ic: 训练集IC
            valid_ic: 验证集IC
            test_ic: 测试集IC
            train_r2: 训练集R²（可选）
            test_r2: 测试集R²（可选）
            model_id: 模型ID（可选，用于日志）
            symbol: 股票代码（可选，用于日志）

        返回:
            (is_valid, alerts) - 是否通过验证，告警列表
        """
        alerts = []

        # 检查1: Test IC
        test_alerts = self._check_test_ic(test_ic)
        alerts.extend(test_alerts)

        # 检查2: Train IC
        train_alerts = self._check_train_ic(train_ic)
        alerts.extend(train_alerts)

        # 检查3: IC Gap
        ic_gap = abs(train_ic) - abs(test_ic)
        gap_alerts = self._check_ic_gap(ic_gap, train_ic, test_ic)
        alerts.extend(gap_alerts)

        # 检查4: Valid IC异常
        valid_alerts = self._check_valid_ic(valid_ic, train_ic, test_ic)
        alerts.extend(valid_alerts)

        # 检查5: R²异常（如果提供）
        if train_r2 is not None and test_r2 is not None:
            r2_alerts = self._check_r2(train_r2, test_r2)
            alerts.extend(r2_alerts)

        # 判断是否通过验证（存在CRITICAL级别告警则不通过）
        has_critical = any(alert.level == AlertLevel.CRITICAL for alert in alerts)
        is_valid = not has_critical

        # 保存告警日志
        if alerts:
            self._log_alerts(alerts, model_id, symbol, {
                'train_ic': train_ic,
                'valid_ic': valid_ic,
                'test_ic': test_ic,
                'ic_gap': ic_gap
            })

        return is_valid, alerts

    def _check_test_ic(self, test_ic: float) -> List[ICAlert]:
        """检查Test IC是否异常"""
        alerts = []
        abs_ic = abs(test_ic)

        if abs_ic > self.THRESHOLDS['test_ic']['critical']:
            alerts.append(ICAlert(
                level=AlertLevel.CRITICAL,
                message=f"Test IC={test_ic:.4f} 严重异常（>0.5）",
                ic_value=test_ic,
                dataset='test',
                check_type='test_ic',
                suggestion="几乎确定存在数据泄露！请立即检查：1) 特征是否包含未来信息 2) 特征是否包含绝对价格 3) Target计算是否正确"
            ))
        elif abs_ic > self.THRESHOLDS['test_ic']['warning']:
            alerts.append(ICAlert(
                level=AlertLevel.WARNING,
                message=f"Test IC={test_ic:.4f} 过高（>0.3）",
                ic_value=test_ic,
                dataset='test',
                check_type='test_ic',
                suggestion="高度可疑！建议：1) 检查特征去价格化是否完整 2) 检查模型复杂度是否过高 3) 考虑多股票池化测试验证"
            ))
        elif abs_ic > self.THRESHOLDS['test_ic']['caution']:
            alerts.append(ICAlert(
                level=AlertLevel.INFO,
                message=f"Test IC={test_ic:.4f} 偏高（>0.2）",
                ic_value=test_ic,
                dataset='test',
                check_type='test_ic',
                suggestion="需要注意。建议：1) 降低模型复杂度 2) 检查是否有小样本统计巧合 3) 验证特征合理性"
            ))

        return alerts

    def _check_train_ic(self, train_ic: float) -> List[ICAlert]:
        """检查Train IC是否异常（过拟合）"""
        alerts = []
        abs_ic = abs(train_ic)

        if abs_ic > self.THRESHOLDS['train_ic']['critical']:
            alerts.append(ICAlert(
                level=AlertLevel.CRITICAL,
                message=f"Train IC={train_ic:.4f} 严重过拟合（>0.8）",
                ic_value=train_ic,
                dataset='train',
                check_type='train_ic',
                suggestion="模型在死记硬背训练数据！必须：1) 大幅降低模型复杂度（max_depth<=3, num_leaves<=10）2) 增加正则化 3) 检查是否有数据泄露"
            ))
        elif abs_ic > self.THRESHOLDS['train_ic']['warning']:
            alerts.append(ICAlert(
                level=AlertLevel.WARNING,
                message=f"Train IC={train_ic:.4f} 过拟合严重（>0.6）",
                ic_value=train_ic,
                dataset='train',
                check_type='train_ic',
                suggestion="过拟合明显。建议：1) 降低模型复杂度 2) 增加正则化（reg_alpha, reg_lambda）3) 减少特征数量"
            ))
        elif abs_ic > self.THRESHOLDS['train_ic']['caution']:
            alerts.append(ICAlert(
                level=AlertLevel.INFO,
                message=f"Train IC={train_ic:.4f} 存在过拟合（>0.4）",
                ic_value=train_ic,
                dataset='train',
                check_type='train_ic',
                suggestion="轻度过拟合。建议：1) 适当降低模型复杂度 2) 监控IC Gap"
            ))

        return alerts

    def _check_ic_gap(self, ic_gap: float, train_ic: float, test_ic: float) -> List[ICAlert]:
        """检查Train-Test IC Gap"""
        alerts = []

        if ic_gap > self.THRESHOLDS['ic_gap']['critical']:
            alerts.append(ICAlert(
                level=AlertLevel.CRITICAL,
                message=f"IC Gap={ic_gap:.4f} 过大（>0.6）",
                ic_value=ic_gap,
                dataset='gap',
                check_type='ic_gap',
                suggestion=f"Train IC={train_ic:.4f}, Test IC={test_ic:.4f}，差距过大！说明模型严重过拟合或存在数据泄露"
            ))
        elif ic_gap > self.THRESHOLDS['ic_gap']['warning']:
            alerts.append(ICAlert(
                level=AlertLevel.WARNING,
                message=f"IC Gap={ic_gap:.4f} 较大（>0.4）",
                ic_value=ic_gap,
                dataset='gap',
                check_type='ic_gap',
                suggestion=f"Train IC={train_ic:.4f}, Test IC={test_ic:.4f}，泛化能力不足"
            ))
        elif ic_gap > self.THRESHOLDS['ic_gap']['caution']:
            alerts.append(ICAlert(
                level=AlertLevel.INFO,
                message=f"IC Gap={ic_gap:.4f} 需要注意（>0.25）",
                ic_value=ic_gap,
                dataset='gap',
                check_type='ic_gap',
                suggestion=f"Train IC={train_ic:.4f}, Test IC={test_ic:.4f}，建议降低模型复杂度"
            ))

        return alerts

    def _check_valid_ic(self, valid_ic: float, train_ic: float, test_ic: float) -> List[ICAlert]:
        """检查Valid IC异常（如过低或为负）"""
        alerts = []

        # Valid IC异常低或为负
        if valid_ic < -0.1:
            alerts.append(ICAlert(
                level=AlertLevel.WARNING,
                message=f"Valid IC={valid_ic:.4f} 为负值且较大",
                ic_value=valid_ic,
                dataset='valid',
                check_type='valid_ic',
                suggestion="验证集预测方向相反！可能：1) 过度正则化 2) Valid Set特殊时期 3) 特征工程bug"
            ))
        elif abs(valid_ic) < 0.01 and abs(train_ic) > 0.3:
            alerts.append(ICAlert(
                level=AlertLevel.INFO,
                message=f"Valid IC={valid_ic:.4f} 接近0，但Train IC={train_ic:.4f}较高",
                ic_value=valid_ic,
                dataset='valid',
                check_type='valid_ic',
                suggestion="验证集无预测能力。可能：1) 模型过拟合 2) Valid Set数据质量问题"
            ))

        # Valid IC远高于Test IC（可疑）
        if abs(valid_ic) > abs(test_ic) * 2 and abs(valid_ic) > 0.3:
            alerts.append(ICAlert(
                level=AlertLevel.INFO,
                message=f"Valid IC={valid_ic:.4f} 远高于 Test IC={test_ic:.4f}",
                ic_value=valid_ic,
                dataset='valid',
                check_type='valid_ic_high',
                suggestion="验证集表现异常好。可能：1) Valid Set样本特殊 2) 模型过度拟合Valid Set"
            ))

        return alerts

    def _check_r2(self, train_r2: float, test_r2: float) -> List[ICAlert]:
        """检查R²异常"""
        alerts = []

        # R²异常高（>0.9通常不正常）
        if test_r2 > 0.9:
            alerts.append(ICAlert(
                level=AlertLevel.CRITICAL,
                message=f"Test R²={test_r2:.4f} 异常高（>0.9）",
                ic_value=test_r2,
                dataset='test',
                check_type='r2',
                suggestion="R²>0.9在金融预测中几乎不可能！极可能存在数据泄露"
            ))
        elif test_r2 > 0.7:
            alerts.append(ICAlert(
                level=AlertLevel.WARNING,
                message=f"Test R²={test_r2:.4f} 过高（>0.7）",
                ic_value=test_r2,
                dataset='test',
                check_type='r2',
                suggestion="R²过高，需要检查是否有数据泄露"
            ))

        return alerts

    def _log_alerts(
        self,
        alerts: List[ICAlert],
        model_id: Optional[str],
        symbol: Optional[str],
        metrics: Dict
    ):
        """保存告警日志"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_file = self.alert_log_dir / f"ic_alert_{timestamp}_{model_id or 'unknown'}.json"

            log_data = {
                'timestamp': timestamp,
                'model_id': model_id,
                'symbol': symbol,
                'metrics': metrics,
                'alerts': [
                    {
                        'level': alert.level.value,
                        'message': alert.message,
                        'ic_value': alert.ic_value,
                        'dataset': alert.dataset,
                        'check_type': alert.check_type,
                        'suggestion': alert.suggestion
                    }
                    for alert in alerts
                ]
            }

            with open(log_file, 'w') as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"⚠️  告警日志保存失败: {e}")

    def print_alerts(self, alerts: List[ICAlert]):
        """打印告警信息"""
        if not alerts:
            print("\n✅ 所有IC检测通过，未发现异常")
            return

        print(f"\n{'='*80}")
        print(f"🚨 IC异常检测报告")
        print(f"{'='*80}")

        # 按级别分组
        critical_alerts = [a for a in alerts if a.level == AlertLevel.CRITICAL]
        warning_alerts = [a for a in alerts if a.level == AlertLevel.WARNING]
        info_alerts = [a for a in alerts if a.level == AlertLevel.INFO]

        if critical_alerts:
            print(f"\n🔴 严重告警 (CRITICAL) - {len(critical_alerts)}项:")
            for i, alert in enumerate(critical_alerts, 1):
                print(f"\n  [{i}] {alert.message}")
                print(f"      数据集: {alert.dataset}")
                if alert.suggestion:
                    print(f"      建议: {alert.suggestion}")

        if warning_alerts:
            print(f"\n⚠️  警告 (WARNING) - {len(warning_alerts)}项:")
            for i, alert in enumerate(warning_alerts, 1):
                print(f"\n  [{i}] {alert.message}")
                print(f"      数据集: {alert.dataset}")
                if alert.suggestion:
                    print(f"      建议: {alert.suggestion}")

        if info_alerts:
            print(f"\n💡 信息 (INFO) - {len(info_alerts)}项:")
            for i, alert in enumerate(info_alerts, 1):
                print(f"\n  [{i}] {alert.message}")
                print(f"      数据集: {alert.dataset}")
                if alert.suggestion:
                    print(f"      建议: {alert.suggestion}")

        print(f"\n{'='*80}\n")

    def get_validation_summary(self, is_valid: bool, alerts: List[ICAlert]) -> str:
        """获取验证总结"""
        if is_valid:
            if not alerts:
                return "✅ 所有检测通过，模型IC正常"
            else:
                return f"⚠️  检测通过但有{len(alerts)}个提示，请注意"
        else:
            critical_count = sum(1 for a in alerts if a.level == AlertLevel.CRITICAL)
            return f"🔴 验证失败！发现{critical_count}个严重问题，疑似数据泄露"
