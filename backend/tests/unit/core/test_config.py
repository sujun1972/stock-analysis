"""
测试配置模块的生产环境属性
"""

import os
import pytest

from app.core.config import Settings


def test_is_production():
    """测试 is_production 属性"""
    # 测试生产环境
    os.environ["ENVIRONMENT"] = "production"
    settings = Settings()
    assert settings.is_production is True
    assert settings.is_development is False
    assert settings.is_testing is False

    # 测试开发环境
    os.environ["ENVIRONMENT"] = "development"
    settings = Settings()
    assert settings.is_production is False
    assert settings.is_development is True
    assert settings.is_testing is False


def test_is_development():
    """测试 is_development 属性"""
    os.environ["ENVIRONMENT"] = "development"
    settings = Settings()
    assert settings.is_development is True
    assert settings.is_production is False


def test_is_testing():
    """测试 is_testing 属性"""
    os.environ["ENVIRONMENT"] = "testing"
    settings = Settings()
    assert settings.is_testing is True
    assert settings.is_production is False
    assert settings.is_development is False


def test_log_level_production():
    """测试生产环境日志级别"""
    os.environ["ENVIRONMENT"] = "production"
    settings = Settings()
    assert settings.log_level == "INFO"


def test_log_level_development():
    """测试开发环境日志级别"""
    os.environ["ENVIRONMENT"] = "development"
    settings = Settings()
    assert settings.log_level == "DEBUG"


def test_log_level_testing():
    """测试测试环境日志级别"""
    os.environ["ENVIRONMENT"] = "testing"
    settings = Settings()
    assert settings.log_level == "WARNING"
