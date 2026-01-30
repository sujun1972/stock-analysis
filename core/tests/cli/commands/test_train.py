"""
测试train命令
"""

import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
from click.testing import CliRunner
import pandas as pd
import numpy as np
import json

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.cli.commands.train import train, load_training_data, prepare_train_data


@pytest.mark.skip(reason="需要安装pyarrow库支持parquet文件")
class TestLoadTrainingData:
    """测试load_training_data函数"""

    def test_load_single_parquet_file(self, temp_dir):
        """测试加载单个parquet文件"""
        # 创建测试文件
        test_file = temp_dir / "test.parquet"
        df = pd.DataFrame({"feature1": [1, 2, 3], "feature2": [4, 5, 6]})
        df.to_parquet(test_file)

        # 加载数据
        result = load_training_data(test_file)

        assert len(result) == 3
        assert "feature1" in result.columns

    def test_load_multiple_parquet_files(self, temp_dir):
        """测试加载多个parquet文件"""
        # 创建多个测试文件
        for i in range(3):
            test_file = temp_dir / f"test_{i}.parquet"
            df = pd.DataFrame({"feature1": [i] * 5})
            df.to_parquet(test_file)

        # 加载目录下所有文件
        result = load_training_data(temp_dir)

        assert len(result) == 15  # 3 files * 5 rows

    def test_load_csv_file(self, temp_dir):
        """测试加载CSV文件"""
        test_file = temp_dir / "test.csv"
        df = pd.DataFrame({"feature1": [1, 2, 3]})
        df.to_csv(test_file, index=False)

        result = load_training_data(test_file)

        assert len(result) == 3

    def test_load_nonexistent_file(self, temp_dir):
        """测试加载不存在的文件"""
        test_file = temp_dir / "nonexistent.parquet"

        with pytest.raises(FileNotFoundError):
            load_training_data(test_file)

    def test_load_empty_directory(self, temp_dir):
        """测试加载空目录"""
        with pytest.raises(FileNotFoundError):
            load_training_data(temp_dir)

    def test_load_corrupted_file(self, temp_dir):
        """测试加载损坏的文件"""
        test_file = temp_dir / "corrupted.parquet"
        test_file.write_text("corrupted data")

        # 应该跳过损坏的文件或抛出错误
        with pytest.raises((ValueError, Exception)):
            load_training_data(test_file)


class TestPrepareTrainData:
    """测试prepare_train_data函数"""

    def test_prepare_with_target_column(self):
        """测试准备有目标列的数据"""
        df = pd.DataFrame({
            "date": pd.date_range("2023-01-01", periods=10),
            "feature1": np.random.randn(10),
            "feature2": np.random.randn(10),
            "return_5d": np.random.randn(10),
        })

        X, y, feature_names = prepare_train_data(df, target_col="return_5d")

        assert len(X) <= 10
        assert len(y) <= 10
        assert len(feature_names) >= 2
        assert "date" not in feature_names
        assert "return_5d" not in feature_names

    def test_prepare_without_target_column(self):
        """测试准备无目标列的数据（需要创建）"""
        df = pd.DataFrame({
            "close": [10.0, 11.0, 10.5, 12.0, 11.5] * 2,
            "feature1": np.random.randn(10),
        })

        X, y, feature_names = prepare_train_data(df, target_col="return_5d")

        # 应该自动创建return_5d
        assert len(X) <= 10
        assert len(y) <= 10

    def test_prepare_with_missing_values(self):
        """测试处理缺失值"""
        df = pd.DataFrame({
            "feature1": [1.0, np.nan, 3.0, 4.0, 5.0],
            "feature2": [1.0, 2.0, 3.0, np.nan, 5.0],
            "return_5d": [0.01, 0.02, np.nan, 0.04, 0.05],
        })

        X, y, feature_names = prepare_train_data(df, target_col="return_5d")

        # 应该删除包含缺失值的行
        assert len(X) < 5
        assert not X.isna().any().any()
        assert not y.isna().any()

    def test_prepare_with_non_numeric_columns(self):
        """测试处理非数值列"""
        df = pd.DataFrame({
            "symbol": ["000001"] * 10,
            "date": pd.date_range("2023-01-01", periods=10),
            "feature1": np.random.randn(10),
            "return_5d": np.random.randn(10),
        })

        X, y, feature_names = prepare_train_data(df, target_col="return_5d")

        # 应该只保留数值列
        assert "symbol" not in feature_names
        assert "date" not in feature_names

    def test_prepare_empty_dataframe(self):
        """测试空DataFrame"""
        df = pd.DataFrame()

        with pytest.raises((ValueError, KeyError)):
            prepare_train_data(df, target_col="return_5d")


@pytest.mark.skip(reason="需要实现UnifiedModelTrainer类")
class TestTrainCommand:
    """测试train命令"""

    def test_train_help(self, cli_runner):
        """测试help信息"""
        result = cli_runner.invoke(train, ["--help"])
        assert result.exit_code == 0
        assert "训练" in result.output or "train" in result.output.lower()

    @patch("src.cli.commands.train.UnifiedModelTrainer")
    @patch("src.cli.commands.train.prepare_train_data")
    @patch("src.cli.commands.train.load_training_data")
    def test_train_lightgbm(self, mock_load, mock_prepare, mock_trainer_class, cli_runner, temp_dir):
        """测试训练LightGBM模型"""
        # Mock数据加载
        mock_df = pd.DataFrame({"feature1": [1, 2, 3] * 100})
        mock_load.return_value = mock_df

        # Mock数据准备
        X = pd.DataFrame({"feature1": np.random.randn(300)})
        y = pd.Series(np.random.randn(300))
        mock_prepare.return_value = (X, y, ["feature1"])

        # Mock训练器
        mock_trainer = MagicMock()
        mock_model = MagicMock()
        mock_model.predict.return_value = np.random.randn(60)
        mock_trainer.train.return_value = mock_model
        mock_trainer_class.return_value = mock_trainer

        # 创建临时数据文件
        data_file = temp_dir / "data.parquet"
        pd.DataFrame({"feature1": [1, 2, 3]}).to_parquet(data_file)

        # 执行命令
        result = cli_runner.invoke(
            train,
            [
                "--model", "lightgbm",
                "--data", str(data_file),
                "--output", str(temp_dir / "model.pkl")
            ]
        )

        # 验证调用
        mock_load.assert_called_once()
        mock_trainer.train.assert_called_once()

    @patch("src.cli.commands.train.UnifiedModelTrainer")
    @patch("src.cli.commands.train.prepare_train_data")
    @patch("src.cli.commands.train.load_training_data")
    def test_train_gru(self, mock_load, mock_prepare, mock_trainer_class, cli_runner, temp_dir):
        """测试训练GRU模型"""
        # Setup mocks
        mock_df = pd.DataFrame({"feature1": [1, 2, 3] * 100})
        mock_load.return_value = mock_df

        X = pd.DataFrame({"feature1": np.random.randn(300)})
        y = pd.Series(np.random.randn(300))
        mock_prepare.return_value = (X, y, ["feature1"])

        mock_trainer = MagicMock()
        mock_model = MagicMock()
        mock_model.predict.return_value = np.random.randn(60)
        mock_trainer.train.return_value = mock_model
        mock_trainer_class.return_value = mock_trainer

        data_file = temp_dir / "data.parquet"
        pd.DataFrame({"feature1": [1, 2, 3]}).to_parquet(data_file)

        # 执行命令
        result = cli_runner.invoke(
            train,
            [
                "--model", "gru",
                "--data", str(data_file),
            ]
        )

        mock_trainer.train.assert_called_once()

    @patch("src.cli.commands.train.UnifiedModelTrainer")
    @patch("src.cli.commands.train.prepare_train_data")
    @patch("src.cli.commands.train.load_training_data")
    def test_train_with_custom_target(self, mock_load, mock_prepare, mock_trainer_class, cli_runner, temp_dir):
        """测试自定义目标列"""
        mock_df = pd.DataFrame({"feature1": [1, 2, 3] * 100})
        mock_load.return_value = mock_df

        X = pd.DataFrame({"feature1": np.random.randn(300)})
        y = pd.Series(np.random.randn(300))
        mock_prepare.return_value = (X, y, ["feature1"])

        mock_trainer = MagicMock()
        mock_model = MagicMock()
        mock_model.predict.return_value = np.random.randn(60)
        mock_trainer.train.return_value = mock_model
        mock_trainer_class.return_value = mock_trainer

        data_file = temp_dir / "data.parquet"
        pd.DataFrame({"feature1": [1, 2, 3]}).to_parquet(data_file)

        result = cli_runner.invoke(
            train,
            [
                "--model", "lightgbm",
                "--data", str(data_file),
                "--target", "return_10d"
            ]
        )

        # 验证target参数传递
        call_args = mock_prepare.call_args[1]
        assert call_args["target_col"] == "return_10d"

    @patch("src.cli.commands.train.UnifiedModelTrainer")
    @patch("src.cli.commands.train.prepare_train_data")
    @patch("src.cli.commands.train.load_training_data")
    def test_train_with_test_size(self, mock_load, mock_prepare, mock_trainer_class, cli_runner, temp_dir):
        """测试自定义测试集比例"""
        mock_df = pd.DataFrame({"feature1": [1, 2, 3] * 100})
        mock_load.return_value = mock_df

        X = pd.DataFrame({"feature1": np.random.randn(300)})
        y = pd.Series(np.random.randn(300))
        mock_prepare.return_value = (X, y, ["feature1"])

        mock_trainer = MagicMock()
        mock_model = MagicMock()
        mock_model.predict.return_value = np.random.randn(90)
        mock_trainer.train.return_value = mock_model
        mock_trainer_class.return_value = mock_trainer

        data_file = temp_dir / "data.parquet"
        pd.DataFrame({"feature1": [1, 2, 3]}).to_parquet(data_file)

        result = cli_runner.invoke(
            train,
            [
                "--model", "lightgbm",
                "--data", str(data_file),
                "--test-size", "0.3"
            ]
        )

        # 验证训练被调用
        mock_trainer.train.assert_called_once()

    def test_train_missing_data_param(self, cli_runner):
        """测试缺少必需的data参数"""
        result = cli_runner.invoke(
            train,
            ["--model", "lightgbm"]
        )

        # 应该报错
        assert result.exit_code != 0

    @patch("src.cli.commands.train.load_training_data")
    def test_train_with_nonexistent_data(self, mock_load, cli_runner):
        """测试不存在的数据文件"""
        mock_load.side_effect = FileNotFoundError("文件不存在")

        result = cli_runner.invoke(
            train,
            [
                "--model", "lightgbm",
                "--data", "/nonexistent/path/data.parquet"
            ]
        )

        # 应该处理错误
        assert result.exit_code != 0


@pytest.mark.skip(reason="需要实现UnifiedModelTrainer类")
class TestTrainEdgeCases:
    """测试边界情况"""

    @patch("src.cli.commands.train.UnifiedModelTrainer")
    @patch("src.cli.commands.train.prepare_train_data")
    @patch("src.cli.commands.train.load_training_data")
    def test_train_with_small_dataset(self, mock_load, mock_prepare, mock_trainer_class, cli_runner, temp_dir):
        """测试小数据集"""
        mock_df = pd.DataFrame({"feature1": [1, 2, 3]})
        mock_load.return_value = mock_df

        # 只有3个样本
        X = pd.DataFrame({"feature1": [1, 2, 3]})
        y = pd.Series([0.01, 0.02, 0.03])
        mock_prepare.return_value = (X, y, ["feature1"])

        mock_trainer = MagicMock()
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0.01])
        mock_trainer.train.return_value = mock_model
        mock_trainer_class.return_value = mock_trainer

        data_file = temp_dir / "data.parquet"
        pd.DataFrame({"feature1": [1, 2, 3]}).to_parquet(data_file)

        result = cli_runner.invoke(
            train,
            [
                "--model", "ridge",  # Ridge适合小数据集
                "--data", str(data_file),
            ]
        )

        # 应该能完成训练
        mock_trainer.train.assert_called_once()

    @patch("src.cli.commands.train.UnifiedModelTrainer")
    @patch("src.cli.commands.train.prepare_train_data")
    @patch("src.cli.commands.train.load_training_data")
    def test_train_saves_metadata(self, mock_load, mock_prepare, mock_trainer_class, cli_runner, temp_dir):
        """测试保存元数据"""
        mock_df = pd.DataFrame({"feature1": [1, 2, 3] * 100})
        mock_load.return_value = mock_df

        X = pd.DataFrame({"feature1": np.random.randn(300)})
        y = pd.Series(np.random.randn(300))
        mock_prepare.return_value = (X, y, ["feature1"])

        mock_trainer = MagicMock()
        mock_model = MagicMock()
        mock_model.predict.return_value = np.random.randn(60)
        mock_trainer.train.return_value = mock_model
        mock_trainer_class.return_value = mock_trainer

        data_file = temp_dir / "data.parquet"
        pd.DataFrame({"feature1": [1, 2, 3]}).to_parquet(data_file)

        output_path = temp_dir / "model.pkl"

        result = cli_runner.invoke(
            train,
            [
                "--model", "lightgbm",
                "--data", str(data_file),
                "--output", str(output_path)
            ]
        )

        # 验证模型保存被调用
        mock_model.save.assert_called()


@pytest.mark.skip(reason="需要实现UnifiedModelTrainer类")
class TestTrainIntegration:
    """集成测试"""

    @patch("src.cli.commands.train.UnifiedModelTrainer")
    def test_full_training_workflow(self, mock_trainer_class, cli_runner, temp_dir):
        """测试完整的训练流程"""
        # 创建真实的测试数据
        df = pd.DataFrame({
            "feature1": np.random.randn(1000),
            "feature2": np.random.randn(1000),
            "feature3": np.random.randn(1000),
            "return_5d": np.random.randn(1000) * 0.02,
        })
        data_file = temp_dir / "train_data.parquet"
        df.to_parquet(data_file)

        # Mock训练器
        mock_trainer = MagicMock()
        mock_model = MagicMock()
        mock_model.predict.return_value = np.random.randn(200)
        mock_model.feature_importances_ = np.array([0.5, 0.3, 0.2])
        mock_model.model = MagicMock()
        mock_model.model.feature_importances_ = np.array([0.5, 0.3, 0.2])
        mock_trainer.train.return_value = mock_model
        mock_trainer_class.return_value = mock_trainer

        output_path = temp_dir / "model.pkl"

        # 执行完整流程
        result = cli_runner.invoke(
            train,
            [
                "--model", "lightgbm",
                "--data", str(data_file),
                "--target", "return_5d",
                "--test-size", "0.2",
                "--output", str(output_path)
            ]
        )

        # 验证各个步骤
        mock_trainer.train.assert_called_once()
        mock_model.predict.assert_called()
        mock_model.save.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
