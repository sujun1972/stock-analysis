#!/bin/bash
# Provider 模块完整测试脚本
# 运行所有 Provider 相关测试并生成覆盖率报告

set -e  # 遇到错误立即退出

echo "========================================="
echo "Provider 模块完整测试"
echo "========================================="
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# 确保在虚拟环境中
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -d "venv" ]; then
        echo "激活虚拟环境..."
        source venv/bin/activate
    else
        echo "错误: 未找到虚拟环境"
        exit 1
    fi
fi

echo "1. 运行 data_converter 测试..."
echo "-----------------------------------------"
pytest tests/unit/providers/akshare/test_data_converter_comprehensive.py -v \
    --cov=src/providers/akshare/data_converter \
    --cov-report=term-missing \
    --cov-report=html:tests/coverage/data_converter

echo ""
echo "2. 运行 provider 测试..."
echo "-----------------------------------------"
pytest tests/unit/providers/akshare/test_provider_comprehensive.py -v \
    --cov=src/providers/akshare/provider \
    --cov-report=term-missing \
    --cov-report=html:tests/coverage/provider

echo ""
echo "3. 运行 provider_registry 测试..."
echo "-----------------------------------------"
pytest tests/unit/providers/test_provider_registry_comprehensive.py -v \
    --cov=src/providers/provider_registry \
    --cov-report=term-missing \
    --cov-report=html:tests/coverage/provider_registry

echo ""
echo "4. 运行 provider_factory 测试..."
echo "-----------------------------------------"
pytest tests/unit/providers/test_provider_factory_comprehensive.py -v \
    --cov=src/providers/provider_factory \
    --cov-report=term-missing \
    --cov-report=html:tests/coverage/provider_factory

echo ""
echo "5. 运行 providers 配置测试..."
echo "-----------------------------------------"
pytest tests/unit/config/test_providers_config.py -v \
    --cov=src/config/providers \
    --cov-report=term-missing \
    --cov-report=html:tests/coverage/providers_config

echo ""
echo "6. 运行 Provider 弹性机制集成测试..."
echo "-----------------------------------------"
pytest tests/integration/providers/test_provider_resilience.py -v

echo ""
echo "7. 生成完整覆盖率报告..."
echo "-----------------------------------------"
pytest \
    tests/unit/providers/akshare/test_data_converter_comprehensive.py \
    tests/unit/providers/akshare/test_provider_comprehensive.py \
    tests/unit/providers/test_provider_registry_comprehensive.py \
    tests/unit/providers/test_provider_factory_comprehensive.py \
    tests/unit/config/test_providers_config.py \
    tests/integration/providers/test_provider_resilience.py \
    --cov=src/providers \
    --cov=src/config/providers \
    --cov-report=term-missing \
    --cov-report=html:tests/coverage/provider_complete \
    --cov-report=json:tests/coverage/provider_coverage.json

echo ""
echo "========================================="
echo "测试完成！"
echo "========================================="
echo ""
echo "覆盖率报告位置:"
echo "  - HTML: tests/coverage/provider_complete/index.html"
echo "  - JSON: tests/coverage/provider_coverage.json"
echo ""
echo "打开 HTML 报告:"
echo "  open tests/coverage/provider_complete/index.html"
echo ""
