#!/bin/bash

# 性能测试自动化脚本
# 作者: Backend Team
# 日期: 2026-02-05
# 版本: 1.0.0

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "======================================"
echo "性能基准测试 - 自动化执行"
echo "======================================"
echo ""

# 1. 检查服务状态
print_info "检查服务状态..."
if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
    print_error "后端服务未运行！"
    echo ""
    echo "请先启动服务:"
    echo "  cd /Volumes/MacDriver/stock-analysis/backend"
    echo "  docker-compose up -d"
    echo ""
    exit 1
fi
print_success "服务运行正常"
echo ""

# 2. 检查 Locust 安装
print_info "检查 Locust 安装..."
if ! command -v locust &> /dev/null; then
    print_warning "Locust 未安装"
    echo ""
    echo "安装 Locust:"
    echo "  pip install locust"
    echo ""
    read -p "是否现在安装 Locust? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pip install locust
        print_success "Locust 安装完成"
    else
        print_error "取消测试"
        exit 1
    fi
fi
print_success "Locust 已安装 ($(locust --version))"
echo ""

# 3. 创建报告目录
print_info "创建报告目录..."
mkdir -p tests/performance/reports
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
print_success "报告目录: tests/performance/reports/"
echo ""

# 4. 运行并发性能测试 (Pytest)
print_info "运行并发性能测试 (Pytest)..."
echo ""
if pytest tests/performance/test_concurrent_performance.py -v -s \
    --html=tests/performance/reports/pytest_${TIMESTAMP}.html \
    --self-contained-html 2>/dev/null; then
    print_success "并发性能测试通过"
else
    print_warning "并发性能测试失败，继续执行 Locust 测试..."
fi
echo ""

# 5. 选择测试场景
echo "======================================"
echo "选择测试场景:"
echo "======================================"
echo "1. 轻度负载测试 (50 用户, 3 分钟) - 快速验证"
echo "2. 标准负载测试 (100 用户, 5 分钟) - 基准测试 [推荐]"
echo "3. 峰值负载测试 (500 用户, 10 分钟) - 压力测试"
echo "4. 持续负载测试 (200 用户, 30 分钟) - 稳定性测试"
echo "5. 自定义配置"
echo ""
read -p "请选择 (1-5, 默认=2): " scenario
scenario=${scenario:-2}

case $scenario in
    1)
        USERS=50
        SPAWN_RATE=5
        RUN_TIME="3m"
        SCENARIO_NAME="sanity"
        print_info "场景: 轻度负载测试"
        ;;
    2)
        USERS=100
        SPAWN_RATE=10
        RUN_TIME="5m"
        SCENARIO_NAME="baseline"
        print_info "场景: 标准负载测试 (基准)"
        ;;
    3)
        USERS=500
        SPAWN_RATE=50
        RUN_TIME="10m"
        SCENARIO_NAME="peak"
        print_info "场景: 峰值负载测试"
        ;;
    4)
        USERS=200
        SPAWN_RATE=20
        RUN_TIME="30m"
        SCENARIO_NAME="soak"
        print_info "场景: 持续负载测试"
        ;;
    5)
        read -p "并发用户数: " USERS
        read -p "启动速率 (用户/秒): " SPAWN_RATE
        read -p "运行时长 (如 5m, 10m): " RUN_TIME
        read -p "场景名称: " SCENARIO_NAME
        print_info "场景: 自定义 - $SCENARIO_NAME"
        ;;
    *)
        print_error "无效选择，使用默认场景 2"
        USERS=100
        SPAWN_RATE=10
        RUN_TIME="5m"
        SCENARIO_NAME="baseline"
        ;;
esac

echo ""
echo "测试配置:"
echo "  - 并发用户: $USERS"
echo "  - 启动速率: $SPAWN_RATE 用户/秒"
echo "  - 运行时长: $RUN_TIME"
echo "  - 目标地址: http://localhost:8000"
echo ""

read -p "按 Enter 开始测试，或 Ctrl+C 取消..."
echo ""

# 6. 运行 Locust 压力测试
print_info "运行 Locust 压力测试..."
echo ""

locust -f tests/performance/locustfile.py \
       --headless \
       --users $USERS \
       --spawn-rate $SPAWN_RATE \
       --run-time $RUN_TIME \
       --host http://localhost:8000 \
       --html tests/performance/reports/locust_${SCENARIO_NAME}_${TIMESTAMP}.html \
       --csv tests/performance/reports/locust_${SCENARIO_NAME}_${TIMESTAMP}

echo ""
print_success "Locust 压力测试完成"
echo ""

# 7. 生成汇总报告
print_info "生成汇总报告..."
cat > tests/performance/reports/summary_${TIMESTAMP}.txt <<EOF
====================================
性能测试汇总报告
====================================
测试时间: $(date)
测试场景: ${SCENARIO_NAME}
并发用户: ${USERS}
启动速率: ${SPAWN_RATE} 用户/秒
运行时长: ${RUN_TIME}

测试报告:
- Pytest 报告: pytest_${TIMESTAMP}.html
- Locust HTML: locust_${SCENARIO_NAME}_${TIMESTAMP}.html
- Locust CSV: locust_${SCENARIO_NAME}_${TIMESTAMP}_stats.csv

性能指标 (从 Locust CSV 提取):
EOF

# 提取关键指标
if [ -f "tests/performance/reports/locust_${SCENARIO_NAME}_${TIMESTAMP}_stats.csv" ]; then
    # 使用 awk 提取总请求数和错误率
    TOTAL_REQUESTS=$(tail -1 tests/performance/reports/locust_${SCENARIO_NAME}_${TIMESTAMP}_stats.csv | awk -F',' '{print $3}')
    TOTAL_FAILURES=$(tail -1 tests/performance/reports/locust_${SCENARIO_NAME}_${TIMESTAMP}_stats.csv | awk -F',' '{print $4}')

    cat >> tests/performance/reports/summary_${TIMESTAMP}.txt <<EOF
- 总请求数: ${TOTAL_REQUESTS}
- 失败请求: ${TOTAL_FAILURES}

验收标准:
- RPS: > 500 (标准负载)
- P95 响应时间: < 100ms
- 错误率: < 0.1%

查看详细报告:
  open tests/performance/reports/locust_${SCENARIO_NAME}_${TIMESTAMP}.html

查看 CSV 数据:
  open tests/performance/reports/locust_${SCENARIO_NAME}_${TIMESTAMP}_stats.csv
====================================
EOF
fi

print_success "汇总报告已生成"
echo ""

# 8. 显示结果
echo "======================================"
echo "测试完成！"
echo "======================================"
echo ""
cat tests/performance/reports/summary_${TIMESTAMP}.txt
echo ""

# 9. 询问是否打开报告
if command -v open &> /dev/null; then
    read -p "是否打开 HTML 报告? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        open tests/performance/reports/locust_${SCENARIO_NAME}_${TIMESTAMP}.html
        print_success "报告已在浏览器中打开"
    fi
fi

echo ""
print_success "所有测试流程完成！"
echo ""
echo "下一步:"
echo "  1. 查看 HTML 报告分析性能"
echo "  2. 对比验收标准"
echo "  3. 如有问题，查看故障排查指南: tests/performance/README.md"
echo "  4. 填写性能基准测试报告: tests/performance/BENCHMARK_REPORT_TEMPLATE.md"
echo ""
