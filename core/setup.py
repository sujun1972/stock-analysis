#!/usr/bin/env python3
"""
Core 模块安装配置
将 core/src 安装为可导入的 Python 包，消除 sys.path.insert 硬编码
"""

from setuptools import setup, find_packages
from pathlib import Path

# 读取 README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding='utf-8') if readme_file.exists() else ""

# 读取依赖
requirements_file = Path(__file__).parent / "requirements.txt"
if requirements_file.exists():
    with open(requirements_file, 'r', encoding='utf-8') as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
else:
    requirements = [
        'pandas>=2.0.0',
        'numpy>=1.24.0',
        'akshare>=1.11.0',
        'TA-Lib>=0.4.28',
        'lightgbm>=4.0.0',
        'torch>=2.0.0',
        'scikit-learn>=1.3.0',
        'imbalanced-learn>=0.11.0',
        'psycopg2-binary>=2.9.0',
        'python-dotenv>=1.0.0',
        'loguru>=0.7.0',
        'pyarrow>=14.0.0',
        'click>=8.1.0',
        'rich>=13.7.0',
    ]

setup(
    name='stock-analysis-core',
    version='2.0.0',
    description='A股AI量化交易系统 - 核心模块',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Stock Analysis Team',
    author_email='',
    url='https://github.com/yourusername/stock-analysis',

    # 包发现
    package_dir={'': 'src'},  # 源码在 src/ 目录
    packages=find_packages(where='src'),

    # 依赖
    install_requires=requirements,

    # Python 版本要求
    python_requires='>=3.9',

    # 额外依赖（可选）
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-asyncio>=0.21.0',
            'pytest-cov>=4.0.0',
            'black>=23.0.0',
            'flake8>=6.0.0',
            'mypy>=1.0.0',
        ],
        'jupyter': [
            'jupyter>=1.0.0',
            'ipykernel>=6.0.0',
            'matplotlib>=3.7.0',
        ]
    },

    # 分类
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Financial and Insurance Industry',
        'Topic :: Office/Business :: Financial :: Investment',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],

    # 包含数据文件
    include_package_data=True,
    zip_safe=False,

    # CLI入口点
    entry_points={
        'console_scripts': [
            'stock-cli=cli.main:cli',
        ],
    },
)
