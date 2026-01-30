"""
CLI测试的pytest配置和fixtures
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
import tempfile
import shutil


@pytest.fixture
def cli_runner():
    """提供Click CLI测试运行器"""
    return CliRunner()


@pytest.fixture
def temp_dir():
    """提供临时目录"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # 清理
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def mock_db_manager():
    """Mock数据库管理器"""
    with patch("database.db_manager.DatabaseManager") as mock:
        instance = MagicMock()
        mock.return_value = instance
        yield instance


@pytest.fixture
def mock_settings():
    """Mock设置对象"""
    with patch("config.settings.get_settings") as mock:
        settings = MagicMock()
        settings.PATH_DATA_PATH = Path("/tmp/data")
        settings.PATH_MODELS_PATH = Path("/tmp/models")
        settings.DB_HOST = "localhost"
        settings.DB_PORT = 5432
        settings.DB_NAME = "test_db"
        settings.DB_USER = "test_user"
        settings.DB_PASSWORD = "test_pass"
        mock.return_value = settings
        yield settings


@pytest.fixture
def sample_stock_data():
    """提供样本股票数据"""
    import pandas as pd
    import numpy as np

    dates = pd.date_range("2023-01-01", "2023-12-31", freq="D")
    data = {
        "trade_date": dates,
        "ts_code": ["000001"] * len(dates),
        "open": np.random.uniform(10, 20, len(dates)),
        "high": np.random.uniform(15, 25, len(dates)),
        "low": np.random.uniform(8, 15, len(dates)),
        "close": np.random.uniform(10, 20, len(dates)),
        "volume": np.random.uniform(1000000, 5000000, len(dates)),
        "amount": np.random.uniform(10000000, 50000000, len(dates)),
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_features_data():
    """提供样本特征数据"""
    import pandas as pd
    import numpy as np

    n_samples = 1000
    n_features = 50

    data = {
        f"feature_{i}": np.random.randn(n_samples)
        for i in range(n_features)
    }
    data["return_5d"] = np.random.randn(n_samples) * 0.02

    return pd.DataFrame(data)


@pytest.fixture
def mock_model():
    """Mock机器学习模型"""
    model = MagicMock()
    model.predict.return_value = [0.01, 0.02, -0.01, 0.03]
    model.feature_importances_ = [0.1, 0.2, 0.15, 0.05]
    return model


@pytest.fixture
def mock_logger():
    """Mock logger"""
    with patch("utils.logger.get_logger") as mock:
        logger = MagicMock()
        mock.return_value = logger
        yield logger
