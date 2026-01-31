#!/usr/bin/env python3
"""
配置模板系统

提供配置模板的加载、应用、导出和管理功能
"""

from .base import ConfigTemplate
from .manager import ConfigTemplateManager

__all__ = ["ConfigTemplate", "ConfigTemplateManager"]
