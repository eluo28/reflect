"""MongoDB client management with connection pooling."""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from src.mongodb.config import MongoDBConfig, get_mongodb_config


class MongoDBClient:
    """Manages MongoDB connection lifecycle."""

    _instance: "MongoDBClient | None" = None
    _client: AsyncIOMotorClient | None = None
    _config: MongoDBConfig | None = None

    def __new__(cls) -> "MongoDBClient":
        """Singleton pattern for connection reuse."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self, config: MongoDBConfig | None = None) -> None:
        """Initialize the MongoDB client.

        Args:
            config: Optional config. If not provided, reads from environment.
        """
        if self._client is not None:
            return

        resolved_config = config or get_mongodb_config()
        self._config = resolved_config
        self._client = AsyncIOMotorClient(
            resolved_config.connection_string,
            maxPoolSize=resolved_config.max_pool_size,
            minPoolSize=resolved_config.min_pool_size,
        )

    @property
    def client(self) -> AsyncIOMotorClient:
        """Get the MongoDB client instance."""
        if self._client is None:
            self.initialize()
        if self._client is None:
            msg = "MongoDB client not initialized"
            raise RuntimeError(msg)
        return self._client

    @property
    def database(self) -> AsyncIOMotorDatabase:
        """Get the default database instance."""
        if self._config is None:
            self.initialize()
        if self._config is None:
            msg = "MongoDB config not initialized"
            raise RuntimeError(msg)
        return self.client[self._config.database_name]

    @property
    def config(self) -> MongoDBConfig:
        """Get the current configuration."""
        if self._config is None:
            self.initialize()
        if self._config is None:
            msg = "MongoDB config not initialized"
            raise RuntimeError(msg)
        return self._config

    async def close(self) -> None:
        """Close the MongoDB connection."""
        if self._client is not None:
            self._client.close()
            self._client = None

    async def ping(self) -> bool:
        """Check if the connection is alive."""
        try:
            await self.client.admin.command("ping")
            return True
        except Exception as e:
            print(f"  MongoDB ping error: {e}")
            return False


def get_mongodb_client() -> MongoDBClient:
    """Get the MongoDB client singleton."""
    return MongoDBClient()
