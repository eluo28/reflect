"""Repository for AssetManifest documents."""

import hashlib

from bson import ObjectId
from pydantic_mongo import AsyncAbstractRepository

from src.asset_annotator.schemas import AssetManifest
from src.mongodb.client import get_mongodb_client
from src.mongodb.schemas import ManifestDocument


def compute_files_hash(filenames: list[str]) -> str:
    """Compute a hash of sorted filenames for manifest reuse."""
    sorted_names = sorted(filenames)
    combined = "|".join(sorted_names)
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


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

        # Compute hash of all filenames for reuse lookup
        all_filenames = [v.file_path.name for v in manifest.video_assets] + [
            a.file_path.name for a in manifest.audio_assets
        ]
        files_hash = compute_files_hash(all_filenames)

        doc = ManifestDocument(
            job_id=job_id,
            manifest_json=manifest.model_dump_json(),
            video_count=len(manifest.video_assets),
            audio_count=len(manifest.audio_assets),
            total_duration_seconds=total_duration,
            files_hash=files_hash,
        )

        await self.save(doc)
        return doc

    async def find_by_files_hash(self, files_hash: str) -> AssetManifest | None:
        """Find a manifest by the hash of its input filenames.

        Useful for reusing manifests across jobs with the same input files.

        Args:
            files_hash: Hash of sorted filenames.

        Returns:
            The most recent AssetManifest with matching files, or None.
        """
        # Find most recent manifest with this files_hash
        docs = await self.find_by({"files_hash": files_hash})
        doc_list = list(docs)
        if not doc_list:
            return None
        # Return the most recent one
        doc = max(doc_list, key=lambda d: d.created_at)
        return AssetManifest.model_validate_json(doc.manifest_json)

    async def backfill_files_hashes(self) -> int:
        """Backfill files_hash for manifests that don't have it.

        Returns:
            Number of manifests updated.
        """
        # Find manifests without files_hash (either null or field doesn't exist)
        # Using $or to match both cases
        collection = self.get_collection()
        cursor = collection.find({
            "$or": [
                {"files_hash": None},
                {"files_hash": {"$exists": False}},
            ]
        })
        doc_list = [ManifestDocument(**doc) async for doc in cursor]

        updated = 0
        for doc in doc_list:
            try:
                manifest = AssetManifest.model_validate_json(doc.manifest_json)
                all_filenames = [v.file_path.name for v in manifest.video_assets] + [
                    a.file_path.name for a in manifest.audio_assets
                ]
                doc.files_hash = compute_files_hash(all_filenames)
                await self.save(doc)
                updated += 1
            except Exception:
                # Skip manifests with parsing errors
                pass

        return updated

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
