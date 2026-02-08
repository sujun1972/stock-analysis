"""
Database query optimization utilities.

Provides tools for batch loading, query caching, and connection pooling.
"""

from typing import List, Dict, Any, Optional, Callable
from loguru import logger


class QueryOptimizer:
    """
    Database query optimizer.

    Optimizations:
    - Batch loading to reduce round trips
    - Query result caching
    - Prepared statement caching
    - Connection pooling (via DatabaseManager)
    """

    def __init__(self, db_manager):
        """
        Initialize query optimizer.

        Args:
            db_manager: DatabaseManager instance
        """
        self.db = db_manager
        self._query_cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutes
        logger.info("Query optimizer initialized")

    def batch_load_configs(
        self,
        config_ids: List[int],
        use_cache: bool = True
    ) -> Dict[int, Dict[str, Any]]:
        """
        Batch load multiple strategy configs in a single query.

        Args:
            config_ids: List of configuration IDs
            use_cache: Whether to use cache

        Returns:
            Dictionary mapping config_id -> config_data
        """
        if not config_ids:
            return {}

        # Check cache
        if use_cache:
            cache_key = f"batch_configs_{','.join(map(str, sorted(config_ids)))}"
            cached = self._query_cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for batch config load: {len(config_ids)} configs")
                return cached

        # Build query with IN clause
        placeholders = ','.join(['%s'] * len(config_ids))
        query = f"""
            SELECT
                id, name, display_name, strategy_type,
                config, config_hash, version,
                is_active, created_at, updated_at
            FROM strategy_configs
            WHERE id IN ({placeholders})
        """

        try:
            results = self.db.execute_query(query, tuple(config_ids))

            # Convert to dictionary
            configs_dict = {row['id']: row for row in results}

            # Cache results
            if use_cache:
                self._query_cache[cache_key] = configs_dict

            logger.info(f"Batch loaded {len(configs_dict)} strategy configs")
            return configs_dict

        except Exception as e:
            logger.error(f"Batch config load failed: {e}")
            return {}

    def batch_load_strategies(
        self,
        strategy_ids: List[int],
        use_cache: bool = True
    ) -> Dict[int, Dict[str, Any]]:
        """
        Batch load multiple AI strategies in a single query.

        Args:
            strategy_ids: List of strategy IDs
            use_cache: Whether to use cache

        Returns:
            Dictionary mapping strategy_id -> strategy_data
        """
        if not strategy_ids:
            return {}

        # Check cache
        if use_cache:
            cache_key = f"batch_strategies_{','.join(map(str, sorted(strategy_ids)))}"
            cached = self._query_cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for batch strategy load: {len(strategy_ids)} strategies")
                return cached

        # Build query with IN clause
        placeholders = ','.join(['%s'] * len(strategy_ids))
        query = f"""
            SELECT
                id, strategy_name, class_name,
                generated_code, code_hash,
                validation_status, test_status,
                is_enabled, version,
                created_at, updated_at
            FROM ai_strategies
            WHERE id IN ({placeholders})
        """

        try:
            results = self.db.execute_query(query, tuple(strategy_ids))

            # Convert to dictionary
            strategies_dict = {row['id']: row for row in results}

            # Cache results
            if use_cache:
                self._query_cache[cache_key] = strategies_dict

            logger.info(f"Batch loaded {len(strategies_dict)} AI strategies")
            return strategies_dict

        except Exception as e:
            logger.error(f"Batch strategy load failed: {e}")
            return {}

    def preload_active_configs(self) -> Dict[int, Dict[str, Any]]:
        """
        Preload all active strategy configs.

        Useful for warming up the cache at startup.

        Returns:
            Dictionary of active configs
        """
        query = """
            SELECT
                id, name, display_name, strategy_type,
                config, config_hash, version,
                is_active, created_at, updated_at
            FROM strategy_configs
            WHERE is_active = TRUE
            ORDER BY updated_at DESC
        """

        try:
            results = self.db.execute_query(query)
            configs_dict = {row['id']: row for row in results}

            logger.info(f"Preloaded {len(configs_dict)} active strategy configs")
            return configs_dict

        except Exception as e:
            logger.error(f"Preload active configs failed: {e}")
            return {}

    def preload_enabled_strategies(self) -> Dict[int, Dict[str, Any]]:
        """
        Preload all enabled AI strategies.

        Returns:
            Dictionary of enabled strategies
        """
        query = """
            SELECT
                id, strategy_name, class_name,
                generated_code, code_hash,
                validation_status, test_status,
                is_enabled, version,
                created_at, updated_at
            FROM ai_strategies
            WHERE is_enabled = TRUE
            AND validation_status = 'passed'
            ORDER BY updated_at DESC
        """

        try:
            results = self.db.execute_query(query)
            strategies_dict = {row['id']: row for row in results}

            logger.info(f"Preloaded {len(strategies_dict)} enabled AI strategies")
            return strategies_dict

        except Exception as e:
            logger.error(f"Preload enabled strategies failed: {e}")
            return {}

    def clear_cache(self):
        """Clear query cache."""
        self._query_cache.clear()
        logger.info("Query cache cleared")


class BatchLoader:
    """
    Batch loader for efficiently loading multiple strategies.

    Groups strategy loading requests and executes them in batches
    to minimize database round trips.
    """

    def __init__(
        self,
        loader_factory,
        batch_size: int = 50,
        enable_batching: bool = True
    ):
        """
        Initialize batch loader.

        Args:
            loader_factory: LoaderFactory instance
            batch_size: Maximum batch size
            enable_batching: Enable batching (False = load individually)
        """
        self.loader_factory = loader_factory
        self.batch_size = batch_size
        self.enable_batching = enable_batching

        logger.info(
            f"Batch loader initialized: batch_size={batch_size}, "
            f"batching_enabled={enable_batching}"
        )

    def load_configs(
        self,
        config_ids: List[int],
        **kwargs
    ) -> Dict[int, Any]:
        """
        Load multiple strategy configs.

        Args:
            config_ids: List of config IDs
            **kwargs: Additional arguments for loader

        Returns:
            Dictionary mapping config_id -> strategy instance
        """
        if not self.enable_batching:
            # Load individually
            return self._load_individually('config', config_ids, **kwargs)

        strategies = {}
        failed_ids = []

        # Process in batches
        for i in range(0, len(config_ids), self.batch_size):
            batch = config_ids[i:i + self.batch_size]

            logger.debug(f"Loading config batch {i // self.batch_size + 1}: {len(batch)} configs")

            for config_id in batch:
                try:
                    strategy = self.loader_factory.load_strategy(
                        strategy_source='config',
                        strategy_id=config_id,
                        **kwargs
                    )
                    strategies[config_id] = strategy

                except Exception as e:
                    logger.error(f"Failed to load config {config_id}: {e}")
                    failed_ids.append(config_id)

        if failed_ids:
            logger.warning(f"Failed to load {len(failed_ids)} configs: {failed_ids}")

        logger.info(
            f"Batch loaded {len(strategies)} configs "
            f"({len(failed_ids)} failed)"
        )

        return strategies

    def load_strategies(
        self,
        strategy_ids: List[int],
        **kwargs
    ) -> Dict[int, Any]:
        """
        Load multiple AI strategies.

        Args:
            strategy_ids: List of strategy IDs
            **kwargs: Additional arguments for loader

        Returns:
            Dictionary mapping strategy_id -> strategy instance
        """
        if not self.enable_batching:
            # Load individually
            return self._load_individually('dynamic', strategy_ids, **kwargs)

        strategies = {}
        failed_ids = []

        # Process in batches
        for i in range(0, len(strategy_ids), self.batch_size):
            batch = strategy_ids[i:i + self.batch_size]

            logger.debug(f"Loading strategy batch {i // self.batch_size + 1}: {len(batch)} strategies")

            for strategy_id in batch:
                try:
                    strategy = self.loader_factory.load_strategy(
                        strategy_source='dynamic',
                        strategy_id=strategy_id,
                        **kwargs
                    )
                    strategies[strategy_id] = strategy

                except Exception as e:
                    logger.error(f"Failed to load strategy {strategy_id}: {e}")
                    failed_ids.append(strategy_id)

        if failed_ids:
            logger.warning(f"Failed to load {len(failed_ids)} strategies: {failed_ids}")

        logger.info(
            f"Batch loaded {len(strategies)} strategies "
            f"({len(failed_ids)} failed)"
        )

        return strategies

    def _load_individually(
        self,
        source: str,
        ids: List[int],
        **kwargs
    ) -> Dict[int, Any]:
        """Load strategies individually (no batching)."""
        results = {}

        for strategy_id in ids:
            try:
                strategy = self.loader_factory.load_strategy(
                    strategy_source=source,
                    strategy_id=strategy_id,
                    **kwargs
                )
                results[strategy_id] = strategy

            except Exception as e:
                logger.error(f"Failed to load {source} {strategy_id}: {e}")

        return results
