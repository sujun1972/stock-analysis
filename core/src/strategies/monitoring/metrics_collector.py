"""
Metrics collection system for aggregating and exporting performance data.

Supports various metric types and export formats.
"""

import time
import json
from enum import Enum
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
from pathlib import Path
from loguru import logger


class MetricType(Enum):
    """Types of metrics to collect."""

    COUNTER = "counter"  # Incrementing count
    GAUGE = "gauge"      # Current value
    HISTOGRAM = "histogram"  # Distribution of values
    TIMER = "timer"      # Duration measurements


@dataclass
class Metric:
    """Individual metric data point."""

    name: str
    type: MetricType
    value: Union[int, float]
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'type': self.type.value,
            'value': self.value,
            'timestamp': self.timestamp,
            'tags': self.tags,
        }


class MetricsCollector:
    """
    Metrics collection and aggregation system.

    Collects various types of metrics for:
    - Strategy loading performance
    - Cache hit rates
    - Error rates
    - Resource usage

    Supports export to:
    - JSON files
    - Prometheus format
    - InfluxDB line protocol
    """

    def __init__(self, export_dir: Optional[str] = None):
        """
        Initialize metrics collector.

        Args:
            export_dir: Directory for exporting metrics (optional)
        """
        self.export_dir = Path(export_dir) if export_dir else None
        if self.export_dir:
            self.export_dir.mkdir(parents=True, exist_ok=True)

        # Metrics storage by type
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._timers: Dict[str, List[float]] = defaultdict(list)

        # All metrics for export
        self._all_metrics: List[Metric] = []

        logger.info(f"Metrics collector initialized: export_dir={export_dir}")

    # Counter methods

    def increment(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """
        Increment a counter.

        Args:
            name: Counter name
            value: Amount to increment (default: 1)
            tags: Optional tags for the metric
        """
        self._counters[name] += value

        metric = Metric(
            name=name,
            type=MetricType.COUNTER,
            value=value,
            tags=tags or {}
        )
        self._all_metrics.append(metric)

    def get_counter(self, name: str) -> int:
        """Get current counter value."""
        return self._counters.get(name, 0)

    # Gauge methods

    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """
        Set a gauge value.

        Args:
            name: Gauge name
            value: Current value
            tags: Optional tags for the metric
        """
        self._gauges[name] = value

        metric = Metric(
            name=name,
            type=MetricType.GAUGE,
            value=value,
            tags=tags or {}
        )
        self._all_metrics.append(metric)

    def get_gauge(self, name: str) -> Optional[float]:
        """Get current gauge value."""
        return self._gauges.get(name)

    # Histogram methods

    def record_histogram(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ):
        """
        Record a value in a histogram.

        Args:
            name: Histogram name
            value: Value to record
            tags: Optional tags for the metric
        """
        self._histograms[name].append(value)

        metric = Metric(
            name=name,
            type=MetricType.HISTOGRAM,
            value=value,
            tags=tags or {}
        )
        self._all_metrics.append(metric)

    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        """
        Get statistics for a histogram.

        Returns:
            Dictionary with count, sum, avg, min, max, p50, p95, p99
        """
        values = self._histograms.get(name, [])

        if not values:
            return {
                'count': 0,
                'sum': 0.0,
                'avg': 0.0,
                'min': 0.0,
                'max': 0.0,
                'p50': 0.0,
                'p95': 0.0,
                'p99': 0.0,
            }

        sorted_values = sorted(values)

        return {
            'count': len(values),
            'sum': sum(values),
            'avg': sum(values) / len(values),
            'min': min(values),
            'max': max(values),
            'p50': self._percentile(sorted_values, 0.50),
            'p95': self._percentile(sorted_values, 0.95),
            'p99': self._percentile(sorted_values, 0.99),
        }

    # Timer methods

    def record_timer(
        self,
        name: str,
        duration_ms: float,
        tags: Optional[Dict[str, str]] = None
    ):
        """
        Record a duration measurement.

        Args:
            name: Timer name
            duration_ms: Duration in milliseconds
            tags: Optional tags for the metric
        """
        self._timers[name].append(duration_ms)

        metric = Metric(
            name=name,
            type=MetricType.TIMER,
            value=duration_ms,
            tags=tags or {}
        )
        self._all_metrics.append(metric)

    def get_timer_stats(self, name: str) -> Dict[str, float]:
        """Get statistics for a timer (same as histogram)."""
        values = self._timers.get(name, [])

        if not values:
            return {
                'count': 0,
                'sum_ms': 0.0,
                'avg_ms': 0.0,
                'min_ms': 0.0,
                'max_ms': 0.0,
                'p50_ms': 0.0,
                'p95_ms': 0.0,
                'p99_ms': 0.0,
            }

        sorted_values = sorted(values)

        return {
            'count': len(values),
            'sum_ms': sum(values),
            'avg_ms': sum(values) / len(values),
            'min_ms': min(values),
            'max_ms': max(values),
            'p50_ms': self._percentile(sorted_values, 0.50),
            'p95_ms': self._percentile(sorted_values, 0.95),
            'p99_ms': self._percentile(sorted_values, 0.99),
        }

    # Export methods

    def export_json(self, filepath: Optional[str] = None) -> str:
        """
        Export all metrics to JSON format.

        Args:
            filepath: Optional file path (uses export_dir if not specified)

        Returns:
            Path to exported file
        """
        if filepath is None:
            if self.export_dir is None:
                raise ValueError("No export_dir configured and no filepath provided")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = self.export_dir / f"metrics_{timestamp}.json"
        else:
            filepath = Path(filepath)

        # Build export data
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'counters': dict(self._counters),
            'gauges': dict(self._gauges),
            'histograms': {
                name: self.get_histogram_stats(name)
                for name in self._histograms.keys()
            },
            'timers': {
                name: self.get_timer_stats(name)
                for name in self._timers.keys()
            },
            'metrics': [m.to_dict() for m in self._all_metrics],
        }

        # Write to file
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported metrics to JSON: {filepath}")
        return str(filepath)

    def export_prometheus(self, filepath: Optional[str] = None) -> str:
        """
        Export metrics in Prometheus text format.

        Args:
            filepath: Optional file path

        Returns:
            Path to exported file
        """
        if filepath is None:
            if self.export_dir is None:
                raise ValueError("No export_dir configured and no filepath provided")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = self.export_dir / f"metrics_{timestamp}.prom"
        else:
            filepath = Path(filepath)

        lines = []

        # Export counters
        for name, value in self._counters.items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")

        # Export gauges
        for name, value in self._gauges.items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")

        # Export histograms
        for name in self._histograms.keys():
            stats = self.get_histogram_stats(name)
            lines.append(f"# TYPE {name} histogram")
            lines.append(f"{name}_count {stats['count']}")
            lines.append(f"{name}_sum {stats['sum']}")

        # Write to file
        with open(filepath, 'w') as f:
            f.write('\n'.join(lines) + '\n')

        logger.info(f"Exported metrics to Prometheus format: {filepath}")
        return str(filepath)

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of all collected metrics.

        Returns:
            Dictionary with summary statistics
        """
        return {
            'total_metrics': len(self._all_metrics),
            'counters_count': len(self._counters),
            'gauges_count': len(self._gauges),
            'histograms_count': len(self._histograms),
            'timers_count': len(self._timers),
            'counters': dict(self._counters),
            'gauges': dict(self._gauges),
            'histogram_stats': {
                name: self.get_histogram_stats(name)
                for name in self._histograms.keys()
            },
            'timer_stats': {
                name: self.get_timer_stats(name)
                for name in self._timers.keys()
            },
        }

    def reset(self):
        """Reset all metrics."""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._timers.clear()
        self._all_metrics.clear()

        logger.info("Reset all metrics")

    def _percentile(self, sorted_data: List[float], p: float) -> float:
        """Calculate percentile from sorted data."""
        if not sorted_data:
            return 0.0

        index = int(len(sorted_data) * p)
        if index >= len(sorted_data):
            index = len(sorted_data) - 1

        return sorted_data[index]
