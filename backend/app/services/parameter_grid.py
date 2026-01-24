"""
参数网格生成器
生成用于批量实验的参数组合
"""

from typing import List, Dict, Any, Optional
from itertools import product
import random
import hashlib
import json
from loguru import logger


class ParameterGrid:
    """
    参数网格生成器
    支持三种策略: grid (网格搜索), random (随机采样), bayesian (贝叶斯优化)
    """

    def __init__(self, param_space: Dict[str, Any]):
        """
        初始化参数网格

        Args:
            param_space: 参数空间定义
                {
                    'symbols': ['000001', '600000'],
                    'date_ranges': [['20200101', '20231231']],
                    'model_types': ['lightgbm', 'gru'],
                    'target_periods': [5, 10, 20],
                    'scaler_types': ['robust', 'standard'],
                    'balance_samples': [False, True],
                    'lightgbm': {
                        'num_leaves': [31, 63, 127],
                        'learning_rate': [0.01, 0.05, 0.1]
                    },
                    'gru': {
                        'hidden_size': [32, 64, 128],
                        'num_layers': [1, 2, 3]
                    }
                }
        """
        self.param_space = param_space
        self._validate_param_space()

    def _validate_param_space(self):
        """验证参数空间定义"""
        required_keys = ['symbols', 'model_types']

        for key in required_keys:
            if key not in self.param_space:
                raise ValueError(f"参数空间缺少必需字段: {key}")

            if not isinstance(self.param_space[key], list) or len(self.param_space[key]) == 0:
                raise ValueError(f"字段 {key} 必须是非空列表")

    def generate(
        self,
        strategy: str = 'grid',
        max_experiments: Optional[int] = None,
        random_seed: int = 42
    ) -> List[Dict[str, Any]]:
        """
        生成参数组合

        Args:
            strategy: 生成策略 ('grid', 'random', 'bayesian')
            max_experiments: 最大实验数量（仅对random和bayesian有效）
            random_seed: 随机种子（用于可复现性）

        Returns:
            参数组合列表
        """
        logger.info(f"🎲 使用 {strategy} 策略生成参数组合...")

        if strategy == 'grid':
            configs = self._grid_search()
        elif strategy == 'random':
            configs = self._random_search(max_experiments or 100, random_seed)
        elif strategy == 'bayesian':
            # 贝叶斯优化需要迭代训练，这里先用随机采样替代
            logger.warning("贝叶斯优化暂未实现，使用随机采样代替")
            configs = self._random_search(max_experiments or 100, random_seed)
        else:
            raise ValueError(f"不支持的策略: {strategy}")

        # 为每个配置生成唯一哈希
        for config in configs:
            config['experiment_hash'] = self._generate_hash(config)

        logger.info(f"✅ 生成了 {len(configs)} 个参数组合")
        return configs

    def _grid_search(self) -> List[Dict[str, Any]]:
        """完全网格搜索（所有参数组合）"""

        configs = []

        # 提取通用参数
        symbols = self.param_space.get('symbols', [])
        date_ranges = self.param_space.get('date_ranges', [['20200101', '20231231']])
        model_types = self.param_space.get('model_types', ['lightgbm'])
        target_periods = self.param_space.get('target_periods', [5])
        scaler_types = self.param_space.get('scaler_types', ['robust'])
        balance_samples_options = self.param_space.get('balance_samples', [False])

        # 遍历所有基础组合
        for symbol in symbols:
            for date_range in date_ranges:
                for model_type in model_types:
                    for target_period in target_periods:
                        for scaler_type in scaler_types:
                            for balance_samples in balance_samples_options:

                                # 基础配置
                                base_config = {
                                    'symbol': symbol,
                                    'start_date': date_range[0],
                                    'end_date': date_range[1],
                                    'model_type': model_type,
                                    'target_period': target_period,
                                    'scaler_type': scaler_type,
                                    'balance_samples': balance_samples
                                }

                                # 根据模型类型添加超参数组合
                                if model_type == 'lightgbm':
                                    lgb_configs = self._generate_lightgbm_configs(base_config)
                                    configs.extend(lgb_configs)
                                elif model_type == 'gru':
                                    gru_configs = self._generate_gru_configs(base_config)
                                    configs.extend(gru_configs)
                                else:
                                    # 未知模型类型，只添加基础配置
                                    configs.append(base_config)

        return configs

    def _generate_lightgbm_configs(self, base_config: Dict) -> List[Dict]:
        """生成LightGBM超参数组合"""

        lgb_params = self.param_space.get('lightgbm', {})

        if not lgb_params:
            # 如果没有定义超参数，使用默认值
            return [base_config]

        # 提取超参数
        num_leaves_list = lgb_params.get('num_leaves', [31])
        learning_rate_list = lgb_params.get('learning_rate', [0.05])
        n_estimators_list = lgb_params.get('n_estimators', [100])
        max_depth_list = lgb_params.get('max_depth', [-1])

        configs = []
        for num_leaves, lr, n_est, max_depth in product(
            num_leaves_list, learning_rate_list, n_estimators_list, max_depth_list
        ):
            config = base_config.copy()
            config['model_params'] = {
                'num_leaves': num_leaves,
                'learning_rate': lr,
                'n_estimators': n_est,
                'max_depth': max_depth
            }
            configs.append(config)

        return configs

    def _generate_gru_configs(self, base_config: Dict) -> List[Dict]:
        """生成GRU超参数组合"""

        gru_params = self.param_space.get('gru', {})

        if not gru_params:
            return [base_config]

        # 提取超参数
        hidden_size_list = gru_params.get('hidden_size', [64])
        num_layers_list = gru_params.get('num_layers', [2])
        dropout_list = gru_params.get('dropout', [0.2])
        seq_length_list = gru_params.get('seq_length', [20])
        epochs_list = gru_params.get('epochs', [100])

        configs = []
        for hidden_size, num_layers, dropout, seq_length, epochs in product(
            hidden_size_list, num_layers_list, dropout_list, seq_length_list, epochs_list
        ):
            config = base_config.copy()
            config['seq_length'] = seq_length
            config['epochs'] = epochs
            config['model_params'] = {
                'hidden_size': hidden_size,
                'num_layers': num_layers,
                'dropout': dropout
            }
            configs.append(config)

        return configs

    def _random_search(self, n_samples: int, random_seed: int) -> List[Dict[str, Any]]:
        """随机采样参数组合"""

        random.seed(random_seed)
        configs = []

        symbols = self.param_space.get('symbols', [])
        date_ranges = self.param_space.get('date_ranges', [['20200101', '20231231']])
        model_types = self.param_space.get('model_types', ['lightgbm'])
        target_periods = self.param_space.get('target_periods', [5])
        scaler_types = self.param_space.get('scaler_types', ['robust'])
        balance_samples_options = self.param_space.get('balance_samples', [False])

        for _ in range(n_samples):
            # 随机选择基础参数
            symbol = random.choice(symbols)
            date_range = random.choice(date_ranges)
            model_type = random.choice(model_types)
            target_period = random.choice(target_periods)
            scaler_type = random.choice(scaler_types)
            balance_samples = random.choice(balance_samples_options)

            config = {
                'symbol': symbol,
                'start_date': date_range[0],
                'end_date': date_range[1],
                'model_type': model_type,
                'target_period': target_period,
                'scaler_type': scaler_type,
                'balance_samples': balance_samples
            }

            # 随机选择模型超参数
            if model_type == 'lightgbm':
                lgb_params = self.param_space.get('lightgbm', {})
                if lgb_params:
                    config['model_params'] = {
                        'num_leaves': random.choice(lgb_params.get('num_leaves', [31])),
                        'learning_rate': random.choice(lgb_params.get('learning_rate', [0.05])),
                        'n_estimators': random.choice(lgb_params.get('n_estimators', [100])),
                        'max_depth': random.choice(lgb_params.get('max_depth', [-1]))
                    }

            elif model_type == 'gru':
                gru_params = self.param_space.get('gru', {})
                if gru_params:
                    config['seq_length'] = random.choice(gru_params.get('seq_length', [20]))
                    config['epochs'] = random.choice(gru_params.get('epochs', [100]))
                    config['model_params'] = {
                        'hidden_size': random.choice(gru_params.get('hidden_size', [64])),
                        'num_layers': random.choice(gru_params.get('num_layers', [2])),
                        'dropout': random.choice(gru_params.get('dropout', [0.2]))
                    }

            configs.append(config)

        return configs

    def _generate_hash(self, config: Dict[str, Any]) -> str:
        """
        为配置生成MD5哈希
        用于避免重复实验
        """
        # 排序后序列化，确保哈希一致性
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()

    def estimate_total_combinations(self) -> int:
        """估算总参数组合数（用于grid策略）"""

        count = 1

        # 基础参数
        count *= len(self.param_space.get('symbols', []))
        count *= len(self.param_space.get('date_ranges', [['20200101', '20231231']]))
        count *= len(self.param_space.get('model_types', ['lightgbm']))
        count *= len(self.param_space.get('target_periods', [5]))
        count *= len(self.param_space.get('scaler_types', ['robust']))
        count *= len(self.param_space.get('balance_samples', [False]))

        # 超参数（取最大）
        max_hyperparams = 1

        lgb_params = self.param_space.get('lightgbm', {})
        if lgb_params and 'lightgbm' in self.param_space.get('model_types', []):
            lgb_count = (
                len(lgb_params.get('num_leaves', [1])) *
                len(lgb_params.get('learning_rate', [1])) *
                len(lgb_params.get('n_estimators', [1])) *
                len(lgb_params.get('max_depth', [1]))
            )
            max_hyperparams = max(max_hyperparams, lgb_count)

        gru_params = self.param_space.get('gru', {})
        if gru_params and 'gru' in self.param_space.get('model_types', []):
            gru_count = (
                len(gru_params.get('hidden_size', [1])) *
                len(gru_params.get('num_layers', [1])) *
                len(gru_params.get('dropout', [1])) *
                len(gru_params.get('seq_length', [1])) *
                len(gru_params.get('epochs', [1]))
            )
            max_hyperparams = max(max_hyperparams, gru_count)

        count *= max_hyperparams

        return count


# ============================================================
# 预定义的参数空间模板
# ============================================================

class ParameterSpaceTemplates:
    """常用参数空间模板"""

    @staticmethod
    def minimal_test() -> Dict:
        """最小测试模板（快速验证）"""
        return {
            'symbols': ['000001'],
            'date_ranges': [['20220101', '20231231']],
            'model_types': ['lightgbm'],
            'target_periods': [5],
            'scaler_types': ['robust'],
            'balance_samples': [False],
            'lightgbm': {
                'num_leaves': [31],
                'learning_rate': [0.05],
                'n_estimators': [100],
                'max_depth': [-1]
            }
        }

    @staticmethod
    def small_grid() -> Dict:
        """小规模网格（约100个实验）"""
        return {
            'symbols': ['000001', '000002', '600000', '600036', '600519'],
            'date_ranges': [
                ['20200101', '20231231'],
                ['20210101', '20231231']
            ],
            'model_types': ['lightgbm'],
            'target_periods': [5, 10],
            'scaler_types': ['robust', 'standard'],
            'balance_samples': [False],
            'lightgbm': {
                'num_leaves': [31, 63],
                'learning_rate': [0.05, 0.1],
                'n_estimators': [100],
                'max_depth': [-1]
            }
        }

    @staticmethod
    def medium_grid() -> Dict:
        """中等规模网格（约500个实验）"""
        return {
            'symbols': ['000001', '000002', '000333', '000651', '000858',
                       '600000', '600036', '600519', '600585', '600900'],
            'date_ranges': [
                ['20200101', '20231231'],
                ['20210101', '20231231'],
                ['20220101', '20231231']
            ],
            'model_types': ['lightgbm', 'gru'],
            'target_periods': [5, 10, 20],
            'scaler_types': ['robust', 'standard'],
            'balance_samples': [False, True],
            'lightgbm': {
                'num_leaves': [31, 63],
                'learning_rate': [0.05, 0.1],
                'n_estimators': [100, 200],
                'max_depth': [-1, 5]
            },
            'gru': {
                'hidden_size': [64, 128],
                'num_layers': [2],
                'dropout': [0.2],
                'seq_length': [20],
                'epochs': [50, 100]
            }
        }

    @staticmethod
    def large_random() -> Dict:
        """大规模随机采样（配合random策略使用）"""
        return {
            'symbols': ['000001', '000002', '000333', '000651', '000858',
                       '002594', '002714', '002920', '300059', '300750',
                       '600000', '600036', '600276', '600309', '600519',
                       '600585', '600690', '600887', '600900', '601318'],
            'date_ranges': [
                ['20180101', '20231231'],
                ['20190101', '20231231'],
                ['20200101', '20231231'],
                ['20210101', '20231231'],
                ['20220101', '20231231']
            ],
            'model_types': ['lightgbm', 'gru'],
            'target_periods': [1, 3, 5, 10, 20],
            'scaler_types': ['standard', 'robust', 'minmax'],
            'balance_samples': [False, True],
            'lightgbm': {
                'num_leaves': [15, 31, 63, 127],
                'learning_rate': [0.01, 0.03, 0.05, 0.1, 0.2],
                'n_estimators': [50, 100, 200, 500],
                'max_depth': [-1, 3, 5, 7, 10]
            },
            'gru': {
                'hidden_size': [32, 64, 128, 256],
                'num_layers': [1, 2, 3],
                'dropout': [0.1, 0.2, 0.3],
                'seq_length': [10, 20, 30, 60],
                'epochs': [50, 100, 200]
            }
        }
