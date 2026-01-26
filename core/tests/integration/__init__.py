"""
集成测试模块

包含端到端的集成测试，需要真实的数据库连接和完整的运行环境。

测试内容：
- 完整数据流水线 (DataPipeline)
- 数据库管理器 (DatabaseManager)
- 阶段性测试（Phase 1-4）
  - Phase 1: 数据流水线测试
  - Phase 2: 特征工程测试
  - Phase 3: 模型训练测试
  - Phase 4: 回测测试
"""

__all__ = []
