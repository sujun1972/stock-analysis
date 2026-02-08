"""
测试 BaseLoader 抽象基类
"""

import pytest
from src.strategies.loaders.base_loader import BaseLoader


class ConcreteLoader(BaseLoader):
    """用于测试的具体加载器实现"""

    def load_strategy(self, strategy_id: int, use_cache: bool = True, **kwargs):
        """简单实现"""
        if use_cache and strategy_id in self._cache:
            return self._cache[strategy_id]

        # 模拟加载
        strategy = {'id': strategy_id, 'name': f'Strategy_{strategy_id}'}
        self._cache[strategy_id] = strategy
        return strategy


class TestBaseLoader:
    """测试 BaseLoader"""

    def test_init(self):
        """测试初始化"""
        loader = ConcreteLoader()
        assert loader._cache == {}
        assert isinstance(loader._cache, dict)

    def test_load_strategy_no_cache(self):
        """测试不使用缓存加载"""
        loader = ConcreteLoader()
        strategy = loader.load_strategy(1, use_cache=False)

        assert strategy['id'] == 1
        assert strategy['name'] == 'Strategy_1'

    def test_load_strategy_with_cache(self):
        """测试使用缓存加载"""
        loader = ConcreteLoader()

        # 第一次加载
        strategy1 = loader.load_strategy(1, use_cache=True)
        assert strategy1['id'] == 1

        # 第二次应该从缓存读取
        strategy2 = loader.load_strategy(1, use_cache=True)
        assert strategy2 is strategy1  # 应该是同一个对象

    def test_clear_cache_single(self):
        """测试清除单个缓存"""
        loader = ConcreteLoader()

        # 加载两个策略
        loader.load_strategy(1)
        loader.load_strategy(2)
        assert len(loader._cache) == 2

        # 清除一个
        loader.clear_cache(1)
        assert len(loader._cache) == 1
        assert 1 not in loader._cache
        assert 2 in loader._cache

    def test_clear_cache_all(self):
        """测试清除所有缓存"""
        loader = ConcreteLoader()

        # 加载多个策略
        loader.load_strategy(1)
        loader.load_strategy(2)
        loader.load_strategy(3)
        assert len(loader._cache) == 3

        # 清除所有
        loader.clear_cache()
        assert len(loader._cache) == 0

    def test_get_cache_info(self):
        """测试获取缓存信息"""
        loader = ConcreteLoader()

        # 加载一些策略
        loader.load_strategy(1)
        loader.load_strategy(2)

        info = loader.get_cache_info()
        assert info['loader_type'] == 'ConcreteLoader'
        assert info['cached_count'] == 2
        assert 1 in info['cached_ids']
        assert 2 in info['cached_ids']

    def test_repr(self):
        """测试字符串表示"""
        loader = ConcreteLoader()
        loader.load_strategy(1)

        repr_str = repr(loader)
        assert 'ConcreteLoader' in repr_str
        assert 'cached=1' in repr_str
