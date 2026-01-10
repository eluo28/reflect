"""GridFS service for storing large binary files (clips, OTIO artifacts)."""

import logging
import shutil
from collections.abc import AsyncIterator
from enum import StrEnum, auto
from pathlib import Path

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from src.common.base_reflect_model import BaseReflectModel
from src.mongodb.client import get_mongodb_client

logger = logging.getLogger(__name__)


class FileType(StrEnum):
    """Type of file stored in GridFS."""

    VIDEO_CLIP = auto()
    AUDIO_CLIP = auto()
    OTIO_ARTIFACT = auto()
    MANIFEST = auto()


class StoredFileInfo(BaseReflectModel):
    """Information about a file stored in GridFS."""

    file_id: str
    filename: str
    file_type: FileType
    content_type: str
    size_bytes: int
    project_id: str | None = None


class GridFSService:
    """Service for storing and retrieving large files via GridFS."""

    def __init__(self, bucket_name: str = "reflect_files") -> None:
        """Initialize GridFS service.

        Args:
            bucket_name: Name of the GridFS bucket.
        """
        self._bucket_name = bucket_name
        self._bucket: AsyncIOMotorGridFSBucket | None = None

    @property
    def bucket(self) -> AsyncIOMotorGridFSBucket:
        """Get the GridFS bucket instance."""
        if self._bucket is None:
            client = get_mongodb_client()
            self._bucket = AsyncIOMotorGridFSBucket(
                client.database,
                bucket_name=self._bucket_name,
                chunk_size_bytes=client.config.gridfs_chunk_size_bytes,
            )
        return self._bucket

    async def upload_file(
        self,
        file_path: Path,
        file_type: FileType,
        project_id: str | None = None,
        custom_filename: str | None = None,
    ) -> StoredFileInfo:
        """Upload a file to GridFS.

        Args:
            file_path: Path to the file to upload.
            file_type: Type of file being uploaded.
            project_id: Optional project ID to associate with the file.
            custom_filename: Optional custom filename (uses original if not provided).

        Returns:
            StoredFileInfo with file metadata.
        """
        filename = custom_filename or file_path.name
        content_type = self._get_content_type(file_path)

        metadata = {
            "file_type": str(file_type),
            "original_path": str(file_path),
            "content_type": content_type,
        }
        if project_id:
            metadata["project_id"] = project_id

        file_size = file_path.stat().st_size

        with file_path.open("rb") as f:
            file_id = await self.bucket.upload_from_stream(
                filename,
                f,
                metadata=metadata,
            )

        return StoredFileInfo(
            file_id=str(file_id),
            filename=filename,
            file_type=file_type,
            content_type=content_type,
            size_bytes=file_size,
            project_id=project_id,
        )

    async def upload_bytes(
        self,
        data: bytes,
        filename: str,
        file_type: FileType,
        content_type: str,
        project_id: str | None = None,
    ) -> StoredFileInfo:
        """Upload bytes directly to GridFS.

        Args:
            data: Raw bytes to upload.
            filename: Name for the file.
            file_type: Type of file being uploaded.
            content_type: MIME type of the content.
            project_id: Optional project ID to associate with the file.

        Returns:
            StoredFileInfo with file metadata.
        """
        metadata = {
            "file_type": str(file_type),
            "content_type": content_type,
        }
        if project_id:
            metadata["project_id"] = project_id

        file_id = await self.bucket.upload_from_stream(
            filename,
            data,
            metadata=metadata,
        )

        return StoredFileInfo(
            file_id=str(file_id),
            filename=filename,
            file_type=file_type,
            content_type=content_type,
            size_bytes=len(data),
            project_id=project_id,
        )

    async def upload_stream(
        self,
        stream: AsyncIterator[bytes],
        filename: str,
        file_type: FileType,
        content_type: str,
        project_id: str | None = None,
    ) -> StoredFileInfo:
        """Upload from an async stream to GridFS without loading entire file into memory.

        Args:
            stream: Async iterator yielding bytes chunks.
            filename: Name for the file.
            file_type: Type of file being uploaded.
            content_type: MIME type of the content.
            project_id: Optional project ID to associate with the file.

        Returns:
            StoredFileInfo with file metadata.
        """
        metadata = {
            "file_type": str(file_type),
            "content_type": content_type,
        }
        if project_id:
            metadata["project_id"] = project_id

        grid_in = self.bucket.open_upload_stream(filename, metadata=metadata)
        total_size = 0

        try:
            async for chunk in stream:
                await grid_in.write(chunk)
                total_size += len(chunk)
            await grid_in.close()
        except Exception:
            await grid_in.abort()
            raise

        return StoredFileInfo(
            file_id=str(grid_in._id),
            filename=filename,
            file_type=file_type,
            content_type=content_type,
            size_bytes=total_size,
            project_id=project_id,
        )

    async def download_file(
        self,
        file_id: str,
        destination_path: Path,
    ) -> Path:
        """Download a file from GridFS to disk.

        Args:
            file_id: The GridFS file ID.
            destination_path: Where to save the file.

        Returns:
            Path to the downloaded file.
        """
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        with destination_path.open("wb") as f:
            await self.bucket.download_to_stream(ObjectId(file_id), f)

        return destination_path

    async def download_bytes(self, file_id: str) -> bytes:
        """Download a file from GridFS as bytes.

        Args:
            file_id: The GridFS file ID.

        Returns:
            File contents as bytes.
        """
        stream = await self.bucket.open_download_stream(ObjectId(file_id))
        return await stream.read()

    def _get_cache_path(self, file_id: str) -> Path:
        """Get the local cache path for a file.

        Uses subdirectories based on first 2 chars of file_id to avoid
        too many files in a single directory.

        Args:
            file_id: The GridFS file ID.

        Returns:
            Path where the file should be cached.
        """
        client = get_mongodb_client()
        cache_dir = Path(client.config.file_cache_dir).expanduser()
        # Use first 2 chars as subdir to distribute files
        return cache_dir / file_id[:2] / file_id

    def _is_cache_enabled(self) -> bool:
        """Check if file caching is enabled."""
        client = get_mongodb_client()
        return client.config.file_cache_enabled

    async def cache_file(self, file_id: str, data: bytes) -> None:
        """Write file data to local cache.

        Args:
            file_id: The GridFS file ID (used as cache key).
            data: The file contents to cache.
        """
        if not self._is_cache_enabled():
            return

        cache_path = self._get_cache_path(file_id)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(data)
        logger.debug("Cached file %s to %s", file_id, cache_path)

    async def download_file_cached(
        self,
        file_id: str,
        destination_path: Path,
    ) -> tuple[Path, bool]:
        """Download a file from GridFS, checking local cache first.

        Args:
            file_id: The GridFS file ID.
            destination_path: Where to save the file.

        Returns:
            Tuple of (path to file, was_cached).
        """
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        # Check cache first
        if self._is_cache_enabled():
            cache_path = self._get_cache_path(file_id)
            if cache_path.exists():
                shutil.copy(cache_path, destination_path)
                return destination_path, True

        # Cache miss - download from GridFS
        with destination_path.open("wb") as f:
            await self.bucket.download_to_stream(ObjectId(file_id), f)

        # Store in cache for next time
        if self._is_cache_enabled():
            cache_path = self._get_cache_path(file_id)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(destination_path, cache_path)

        return destination_path, False

    async def delete_file(self, file_id: str) -> None:
        """Delete a file from GridFS.

        Args:
            file_id: The GridFS file ID.
        """
        await self.bucket.delete(ObjectId(file_id))

    async def get_file_info(self, file_id: str) -> StoredFileInfo | None:
        """Get metadata for a stored file.

        Args:
            file_id: The GridFS file ID.

        Returns:
            StoredFileInfo if found, None otherwise.
        """
        cursor = self.bucket.find({"_id": ObjectId(file_id)})
        async for grid_out in cursor:
            metadata = grid_out.metadata or {}
            return StoredFileInfo(
                file_id=str(grid_out._id),
                filename=grid_out.filename,
                file_type=FileType(metadata.get("file_type", FileType.VIDEO_CLIP)),
                content_type=metadata.get("content_type", "application/octet-stream"),
                size_bytes=grid_out.length,
                project_id=metadata.get("project_id"),
            )
        return None

    async def list_files_by_project(self, project_id: str) -> list[StoredFileInfo]:
        """List all files associated with a project.

        Args:
            project_id: The project ID.

        Returns:
            List of StoredFileInfo for files in the project.
        """
        files: list[StoredFileInfo] = []
        cursor = self.bucket.find({"metadata.project_id": project_id})

        async for grid_out in cursor:
            metadata = grid_out.metadata or {}
            files.append(
                StoredFileInfo(
                    file_id=str(grid_out._id),
                    filename=grid_out.filename,
                    file_type=FileType(metadata.get("file_type", FileType.VIDEO_CLIP)),
                    content_type=metadata.get(
                        "content_type", "application/octet-stream"
                    ),
                    size_bytes=grid_out.length,
                    project_id=metadata.get("project_id"),
                )
            )

        return files

    def _get_content_type(self, file_path: Path) -> str:
        """Determine content type from file extension."""
        suffix = file_path.suffix.lower()

        content_types = {
            ".mov": "video/quicktime",
            ".mp4": "video/mp4",
            ".avi": "video/x-msvideo",
            ".mkv": "video/x-matroska",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".aac": "audio/aac",
            ".flac": "audio/flac",
            ".otio": "application/json",
            ".json": "application/json",
        }

        return content_types.get(suffix, "application/octet-stream")


def get_gridfs_service(bucket_name: str = "reflect_files") -> GridFSService:
    """Get a GridFS service instance."""
    return GridFSService(bucket_name)
