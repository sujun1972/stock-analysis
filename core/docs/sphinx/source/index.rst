.. Stock Analysis Core documentation master file, created by
   sphinx-quickstart on Sun Feb  1 19:03:16 2026.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Stock Analysis Core 文档
========================

欢迎使用 Stock Analysis Core API 文档!

这是一个完整的A股AI量化交易系统核心模块，包含数据获取、特征工程、模型训练、策略回测、风险管理等功能。

**版本**: v3.0.0

**主要特性**:

* 完整的数据管道 (TimescaleDB + 多数据源)
* 125+ Alpha因子 + 60+ 技术指标
* 多种机器学习模型 (LightGBM, GRU, Ridge)
* 5种交易策略 + 并行回测引擎
* 完善的风险管理系统 (VaR/CVaR)

快速开始
--------

参考用户指南快速上手: :ref:`用户指南 <../user_guide/quick_start.md>`

.. toctree::
   :maxdepth: 2
   :caption: 目录:

   api/modules

