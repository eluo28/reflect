"""MongoDB configuration and connection settings."""

import os
from pathlib import Path

from dotenv import load_dotenv

from src.common.base_reflect_model import BaseReflectModel

# Load .env file from backend directory
_backend_dir = Path(__file__).parent.parent.parent
load_dotenv(_backend_dir / ".env")


class MongoDBConfig(BaseReflectModel):
    """Configuration for MongoDB connection."""

    connection_string: str
    database_name: str

    # GridFS settings (4MB chunks for better performance with large video files)
    gridfs_chunk_size_bytes: int = 4 * 1024 * 1024

    # Local file cache settings (for faster local dev)
    file_cache_enabled: bool = True
    file_cache_dir: str = "~/.reflect/cache"

    # Connection pool settings
    max_pool_size: int = 10
    min_pool_size: int = 1


def get_mongodb_config() -> MongoDBConfig:
    """Get MongoDB configuration from environment variables.

    Environment variables:
        MONGODB_CONNECTION_STRING: MongoDB Atlas connection string
        MONGODB_DATABASE_NAME: Database name (default: reflect_dev)
    """
    connection_string = os.environ.get("MONGODB_CONNECTION_STRING", "")
    if not connection_string:
        msg = "MONGODB_CONNECTION_STRING environment variable is required"
        raise ValueError(msg)

    database_name = os.environ.get("MONGODB_DATABASE_NAME", "reflect_dev")

    return MongoDBConfig(
        connection_string=connection_string,
        database_name=database_name,
    )
