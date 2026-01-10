"""Repository for AssetManifest documents."""

from bson import ObjectId
from pydantic_mongo import AsyncAbstractRepository

from src.asset_annotator.schemas import AssetManifest
from src.mongodb.client import get_mongodb_client
from src.mongodb.schemas import ManifestDocument


class ManifestRepository(AsyncAbstractRepository[ManifestDocument]):
    """Repository for storing and retrieving asset manifests."""

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        collection_name = "manifests"

    @classmethod
    def create(cls) -> "ManifestRepository":
        """Create a repository instance with the default database."""
        client = get_mongodb_client()
        return cls(client.database)  # pyright: ignore[reportArgumentType]

    async def save_manifest(
        self,
        job_id: str,
        manifest: AssetManifest,
    ) -> ManifestDocument:
        """Save an AssetManifest to the database.

        Args:
            job_id: The job this manifest belongs to.
            manifest: The AssetManifest to save.

        Returns:
            The saved ManifestDocument with ID populated.
        """
        total_duration = sum(
            v.duration_seconds for v in manifest.video_assets
        ) + sum(a.duration_seconds for a in manifest.audio_assets)

        doc = ManifestDocument(
            job_id=job_id,
            manifest_json=manifest.model_dump_json(),
            video_count=len(manifest.video_assets),
            audio_count=len(manifest.audio_assets),
            total_duration_seconds=total_duration,
        )

        await self.save(doc)
        return doc

    async def get_manifest(self, manifest_id: str) -> AssetManifest | None:
        """Retrieve an AssetManifest by its document ID.

        Args:
            manifest_id: The document ID.

        Returns:
            The AssetManifest if found, None otherwise.
        """
        doc = await self.find_one_by_id(ObjectId(manifest_id))
        if doc is None:
            return None
        return AssetManifest.model_validate_json(doc.manifest_json)

    async def get_manifest_by_job(
        self,
        job_id: str,
    ) -> AssetManifest | None:
        """Retrieve the AssetManifest for a job.

        Args:
            job_id: The job ID.

        Returns:
            The AssetManifest if found, None otherwise.
        """
        docs = await self.find_by({"job_id": job_id})
        doc_list = list(docs)
        if not doc_list:
            return None
        # Return the most recent one
        doc = doc_list[-1]
        return AssetManifest.model_validate_json(doc.manifest_json)
