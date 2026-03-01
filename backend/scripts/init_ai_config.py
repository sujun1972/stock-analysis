"""
初始化AI配置
添加默认的DeepSeek配置
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.repositories.ai_config_repository import ai_config_repository


def init_ai_config():
    """初始化AI配置"""

    # 检查是否已存在DeepSeek配置
    existing = ai_config_repository.get_by_provider("deepseek")
    if existing:
        print(f"✅ DeepSeek配置已存在，跳过初始化")
        return

    # 创建DeepSeek配置
    deepseek_config = {
        "provider": "deepseek",
        "display_name": "DeepSeek",
        "api_key": "sk-4f697b5dd887435ab027612dc63779fd",
        "api_base_url": "https://api.deepseek.com/v1",
        "model_name": "deepseek-chat",
        "max_tokens": 8000,
        "temperature": 0.7,
        "is_active": True,
        "is_default": True,
        "priority": 100,
        "rate_limit": 10,
        "timeout": 60,
        "description": "DeepSeek AI - 高性价比的中文AI模型"
    }

    created = ai_config_repository.create(deepseek_config)
    print(f"✅ 成功创建DeepSeek配置: {created.provider}")

    # 可选：创建Gemini配置（需要用户自己填写API Key）
    gemini_existing = ai_config_repository.get_by_provider("gemini")
    if not gemini_existing:
        gemini_config = {
            "provider": "gemini",
            "display_name": "Google Gemini",
            "api_key": "YOUR_GEMINI_API_KEY",
            "api_base_url": "https://generativelanguage.googleapis.com/v1beta",
            "model_name": "gemini-1.5-flash",
            "max_tokens": 8000,
            "temperature": 0.7,
            "is_active": False,  # 默认不启用，需要用户填写API Key后启用
            "is_default": False,
            "priority": 50,
            "rate_limit": 10,
            "timeout": 60,
            "description": "Google Gemini - 支持免费额度"
        }
        created_gemini = ai_config_repository.create(gemini_config)
        print(f"✅ 成功创建Gemini配置模板: {created_gemini.provider} (请在管理页面填写API Key)")

    print("\n🎉 AI配置初始化完成！")
    print(f"默认AI提供商: DeepSeek")
    print(f"可以通过 /api/ai-strategy/providers 查看所有配置")


if __name__ == "__main__":
    init_ai_config()
