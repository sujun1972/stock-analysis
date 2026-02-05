"""
Locust 性能基准测试脚本

✅ 任务 3.4: 性能基准测试 (P0)
- 压力测试脚本
- 多种负载场景
- 性能指标收集

目标指标:
- RPS (Requests Per Second): > 500
- P95 响应时间: < 100ms
- 错误率: < 0.1%

作者: Backend Team
创建日期: 2026-02-05
版本: 1.0.0

使用方法:
    # 基础测试 (100 并发用户, 10 用户/秒启动速率, 运行 5 分钟)
    locust -f tests/performance/locustfile.py \
           --headless \
           --users 100 \
           --spawn-rate 10 \
           --run-time 5m \
           --host http://localhost:8000

    # 轻度负载测试
    locust -f tests/performance/locustfile.py --headless \
           --users 50 --spawn-rate 5 --run-time 3m --host http://localhost:8000

    # 中度负载测试
    locust -f tests/performance/locustfile.py --headless \
           --users 200 --spawn-rate 20 --run-time 5m --host http://localhost:8000

    # 重度负载测试
    locust -f tests/performance/locustfile.py --headless \
           --users 500 --spawn-rate 50 --run-time 10m --host http://localhost:8000

    # 带 Web UI (查看实时图表)
    locust -f tests/performance/locustfile.py --host http://localhost:8000
    # 然后访问 http://localhost:8089
"""

from locust import HttpUser, task, between, TaskSet
import random
from datetime import datetime, timedelta


class StockAPITaskSet(TaskSet):
    """股票 API 任务集"""

    # 测试用股票代码池
    stock_codes = [
        "000001.SZ", "000002.SZ", "000004.SZ", "000005.SZ",
        "000006.SZ", "000007.SZ", "000008.SZ", "000009.SZ",
        "000010.SZ", "000011.SZ", "000012.SZ", "000014.SZ",
        "000016.SZ", "000017.SZ", "000019.SZ", "000020.SZ",
    ]

    def on_start(self):
        """用户启动时执行 (模拟用户登录/初始化)"""
        # 可以在这里添加认证逻辑
        pass

    @task(5)
    def get_stock_list(self):
        """获取股票列表 (高频任务 - 权重5)"""
        page = random.randint(1, 5)
        page_size = random.choice([10, 20, 50])
        self.client.get(
            f"/api/stocks/list",
            params={"page": page, "page_size": page_size},
            name="/api/stocks/list"
        )

    @task(3)
    def get_daily_data(self):
        """获取日线数据 (中频任务 - 权重3)"""
        code = random.choice(self.stock_codes)
        # 随机时间范围: 最近 30-365 天
        days = random.randint(30, 365)
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        self.client.get(
            f"/api/data/daily/{code}",
            params={"start_date": start_date},
            name="/api/data/daily/{code}"
        )

    @task(2)
    def get_stock_features(self):
        """获取技术特征 (中频任务 - 权重2)"""
        code = random.choice(self.stock_codes)
        feature_type = random.choice(["technical", "volume", "all"])

        self.client.get(
            f"/api/features/{code}",
            params={"feature_type": feature_type},
            name="/api/features/{code}"
        )

    @task(1)
    def get_stock_info(self):
        """获取股票详情 (低频任务 - 权重1)"""
        code = random.choice(self.stock_codes)
        self.client.get(
            f"/api/stocks/{code}",
            name="/api/stocks/{code}"
        )

    @task(1)
    def get_backtest_result(self):
        """获取回测结果 (低频任务 - 权重1)"""
        code = random.choice(self.stock_codes)

        self.client.post(
            "/api/backtest/run",
            json={
                "stock_code": code,
                "strategy_name": "momentum",
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "initial_capital": 100000
            },
            name="/api/backtest/run"
        )

    @task(1)
    def batch_get_daily_data(self):
        """批量获取日线数据 (低频任务 - 权重1)"""
        # 随机选择 5-10 只股票
        num_stocks = random.randint(5, 10)
        codes = random.sample(self.stock_codes, num_stocks)

        self.client.post(
            "/api/data/batch/daily",
            params={"codes": codes},
            name="/api/data/batch/daily"
        )

    @task(2)
    def get_market_status(self):
        """获取市场状态 (中频任务 - 权重2)"""
        self.client.get(
            "/api/market/status",
            name="/api/market/status"
        )


class DataAPITaskSet(TaskSet):
    """数据 API 任务集 (更侧重数据密集型操作)"""

    stock_codes = [
        "000001.SZ", "000002.SZ", "000004.SZ", "000005.SZ",
        "000006.SZ", "000007.SZ", "000008.SZ", "000009.SZ",
    ]

    @task(4)
    def get_daily_data_range(self):
        """获取日线数据范围查询"""
        code = random.choice(self.stock_codes)
        days = random.choice([30, 90, 180, 365])
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        self.client.get(
            f"/api/data/daily/{code}",
            params={
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d")
            },
            name="/api/data/daily/{code}?range"
        )

    @task(3)
    def get_multiple_features(self):
        """批量获取多只股票特征"""
        codes = random.sample(self.stock_codes, random.randint(3, 6))

        for code in codes:
            self.client.get(
                f"/api/features/{code}",
                params={"feature_type": "all"},
                name="/api/features/batch"
            )

    @task(2)
    def batch_download_data(self):
        """批量下载数据"""
        codes = random.sample(self.stock_codes, random.randint(5, 8))

        self.client.post(
            "/api/data/batch/daily",
            params={"codes": codes},
            name="/api/data/batch/daily"
        )


class ReadOnlyUser(HttpUser):
    """只读用户 (模拟普通查询用户)"""
    tasks = [StockAPITaskSet]
    wait_time = between(1, 3)  # 用户操作间隔 1-3 秒
    weight = 8  # 80% 的用户


class DataIntensiveUser(HttpUser):
    """数据密集型用户 (模拟数据分析用户)"""
    tasks = [DataAPITaskSet]
    wait_time = between(0.5, 2)  # 更快的操作频率
    weight = 2  # 20% 的用户


class BurstUser(HttpUser):
    """突发用户 (模拟瞬时高并发场景)"""
    tasks = [StockAPITaskSet]
    wait_time = between(0.1, 0.5)  # 非常快的操作频率
    weight = 1  # 10% 的用户 (实际只在峰值测试时启用)


# 辅助任务: 健康检查
class HealthCheckUser(HttpUser):
    """健康检查用户 (低频监控)"""

    @task
    def health_check(self):
        """健康检查端点"""
        self.client.get("/health", name="/health")

    wait_time = between(10, 30)  # 每 10-30 秒检查一次
    weight = 0.5  # 5% 的用户


# 性能测试场景配置
# 可以通过命令行或代码配置不同的测试场景

# 场景 1: 正常负载 (推荐用于基准测试)
# locust -f locustfile.py --users 100 --spawn-rate 10 --run-time 5m

# 场景 2: 峰值负载 (测试系统极限)
# locust -f locustfile.py --users 500 --spawn-rate 50 --run-time 10m

# 场景 3: 持续负载 (测试系统稳定性)
# locust -f locustfile.py --users 200 --spawn-rate 20 --run-time 30m

# 场景 4: 压力递增 (逐步找到系统瓶颈)
# locust -f locustfile.py --users 1000 --spawn-rate 10 --run-time 20m
