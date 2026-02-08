"""
Lazy loading utilities for strategies.

Defers strategy loading until actually needed to improve startup time.
"""

from typing import Any, Optional, Dict
from loguru import logger


class LazyStrategy:
    """
    Lazy loading wrapper for strategies.

    Delays strategy loading until the strategy is actually used,
    improving application startup time and reducing memory usage.

    Usage:
        lazy_strategy = LazyStrategy(strategy_id=123, loader=loader_factory)

        # Strategy not loaded yet
        signals = lazy_strategy.generate_signals(prices)  # Now it loads
    """

    def __init__(
        self,
        strategy_id: int,
        loader_factory,
        source: str = 'config',
        **loader_kwargs
    ):
        """
        Initialize lazy strategy wrapper.

        Args:
            strategy_id: Strategy ID
            loader_factory: LoaderFactory instance
            source: Strategy source ('config' or 'dynamic')
            **loader_kwargs: Additional arguments for loader
        """
        self.strategy_id = strategy_id
        self.loader_factory = loader_factory
        self.source = source
        self.loader_kwargs = loader_kwargs

        # Internal state
        self._strategy: Optional[Any] = None
        self._loaded = False
        self._load_error: Optional[Exception] = None

        logger.debug(
            f"Lazy strategy wrapper created: "
            f"id={strategy_id}, source={source}"
        )

    def _ensure_loaded(self):
        """Ensure strategy is loaded."""
        if self._loaded:
            return

        if self._load_error:
            raise self._load_error

        try:
            logger.info(f"Lazy loading strategy: id={self.strategy_id}, source={self.source}")

            self._strategy = self.loader_factory.load_strategy(
                strategy_source=self.source,
                strategy_id=self.strategy_id,
                **self.loader_kwargs
            )

            self._loaded = True
            logger.info(f"Strategy loaded successfully: id={self.strategy_id}")

        except Exception as e:
            self._load_error = e
            logger.error(f"Failed to lazy load strategy {self.strategy_id}: {e}")
            raise

    # Proxy methods to underlying strategy

    def generate_signals(self, *args, **kwargs):
        """Generate signals (loads strategy if needed)."""
        self._ensure_loaded()
        return self._strategy.generate_signals(*args, **kwargs)

    def calculate_scores(self, *args, **kwargs):
        """Calculate scores (loads strategy if needed)."""
        self._ensure_loaded()
        return self._strategy.calculate_scores(*args, **kwargs)

    def get_metadata(self) -> Dict[str, Any]:
        """Get metadata (loads strategy if needed)."""
        self._ensure_loaded()
        return self._strategy.get_metadata()

    def __getattr__(self, name):
        """
        Forward any other attribute access to the underlying strategy.

        This automatically loads the strategy if it hasn't been loaded yet.
        """
        self._ensure_loaded()
        return getattr(self._strategy, name)

    def is_loaded(self) -> bool:
        """Check if strategy has been loaded."""
        return self._loaded

    def unload(self):
        """Unload the strategy to free memory."""
        if self._strategy is not None:
            self._strategy = None
            self._loaded = False
            logger.debug(f"Strategy unloaded: id={self.strategy_id}")

    def reload(self):
        """Reload the strategy."""
        self.unload()
        self._load_error = None
        self._ensure_loaded()

    def __repr__(self) -> str:
        status = "loaded" if self._loaded else "not loaded"
        return f"LazyStrategy(id={self.strategy_id}, source={self.source}, {status})"


class LazyStrategyPool:
    """
    Pool of lazy-loaded strategies.

    Manages a collection of strategies that are loaded on-demand.
    Useful for managing large numbers of strategies efficiently.
    """

    def __init__(self, loader_factory, max_loaded: int = 10):
        """
        Initialize lazy strategy pool.

        Args:
            loader_factory: LoaderFactory instance
            max_loaded: Maximum number of strategies to keep loaded
        """
        self.loader_factory = loader_factory
        self.max_loaded = max_loaded

        self._strategies: Dict[int, LazyStrategy] = {}
        self._access_order: List[int] = []

        logger.info(f"Lazy strategy pool initialized: max_loaded={max_loaded}")

    def add(
        self,
        strategy_id: int,
        source: str = 'config',
        **loader_kwargs
    ):
        """
        Add a strategy to the pool.

        Args:
            strategy_id: Strategy ID
            source: Strategy source
            **loader_kwargs: Loader arguments
        """
        if strategy_id not in self._strategies:
            self._strategies[strategy_id] = LazyStrategy(
                strategy_id=strategy_id,
                loader_factory=self.loader_factory,
                source=source,
                **loader_kwargs
            )

            logger.debug(f"Added strategy to pool: id={strategy_id}")

    def get(self, strategy_id: int) -> LazyStrategy:
        """
        Get a strategy from the pool.

        Args:
            strategy_id: Strategy ID

        Returns:
            LazyStrategy instance
        """
        if strategy_id not in self._strategies:
            raise KeyError(f"Strategy {strategy_id} not in pool")

        strategy = self._strategies[strategy_id]

        # Update access order
        if strategy_id in self._access_order:
            self._access_order.remove(strategy_id)
        self._access_order.append(strategy_id)

        # Manage loaded strategies count
        self._manage_loaded_count()

        return strategy

    def remove(self, strategy_id: int):
        """Remove a strategy from the pool."""
        if strategy_id in self._strategies:
            strategy = self._strategies[strategy_id]
            strategy.unload()
            del self._strategies[strategy_id]

            if strategy_id in self._access_order:
                self._access_order.remove(strategy_id)

            logger.debug(f"Removed strategy from pool: id={strategy_id}")

    def clear(self):
        """Clear all strategies from the pool."""
        for strategy in self._strategies.values():
            strategy.unload()

        self._strategies.clear()
        self._access_order.clear()

        logger.info("Strategy pool cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        loaded_count = sum(
            1 for s in self._strategies.values()
            if s.is_loaded()
        )

        return {
            'total_strategies': len(self._strategies),
            'loaded_strategies': loaded_count,
            'max_loaded': self.max_loaded,
            'memory_usage_percent': loaded_count / self.max_loaded if self.max_loaded > 0 else 0,
        }

    def _manage_loaded_count(self):
        """Ensure we don't exceed max_loaded limit."""
        loaded_count = sum(
            1 for s in self._strategies.values()
            if s.is_loaded()
        )

        # If we exceed the limit, unload least recently used
        while loaded_count > self.max_loaded and self._access_order:
            # Get least recently used
            lru_id = self._access_order[0]

            if lru_id in self._strategies:
                strategy = self._strategies[lru_id]
                if strategy.is_loaded():
                    strategy.unload()
                    loaded_count -= 1
                    logger.debug(f"Unloaded LRU strategy: id={lru_id}")

            self._access_order.pop(0)

    def __len__(self) -> int:
        return len(self._strategies)

    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"LazyStrategyPool("
            f"total={stats['total_strategies']}, "
            f"loaded={stats['loaded_strategies']}/{stats['max_loaded']})"
        )
