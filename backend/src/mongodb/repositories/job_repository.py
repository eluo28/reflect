"""Repository for Job documents."""

from datetime import UTC, datetime

from bson import ObjectId
from pydantic_mongo import AsyncAbstractRepository

from src.mongodb.client import get_mongodb_client
from src.mongodb.schemas import JobDocument, JobStage


class JobRepository(AsyncAbstractRepository[JobDocument]):
    """Repository for storing and retrieving jobs."""

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        collection_name = "jobs"

    @classmethod
    def create(cls) -> "JobRepository":
        """Create a repository instance with the default database."""
        client = get_mongodb_client()
        return cls(client.database)  # pyright: ignore[reportArgumentType]

    async def create_job(
        self,
        name: str,
        description: str = "",
    ) -> JobDocument:
        """Create a new job.

        Args:
            name: Name of the job.
            description: Optional description.

        Returns:
            The created JobDocument with ID populated.
        """
        doc = JobDocument(
            name=name,
            description=description,
            stage=JobStage.CREATED,
        )
        await self.save(doc)
        return doc

    async def get_job(self, job_id: str) -> JobDocument | None:
        """Get a job by ID.

        Args:
            job_id: The job ID.

        Returns:
            The JobDocument if found, None otherwise.
        """
        return await self.find_one_by_id(ObjectId(job_id))

    async def list_jobs(self) -> list[JobDocument]:
        """List all jobs.

        Returns:
            List of all JobDocuments, ordered by creation date (newest first).
        """
        jobs = await self.find_by({})
        return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    async def delete_job(self, job_id: str) -> bool:
        """Delete a job by ID.

        Args:
            job_id: The job ID.

        Returns:
            True if deleted, False if not found.
        """
        doc = await self.find_one_by_id(ObjectId(job_id))
        if doc is None:
            return False
        await self.delete(doc)
        return True

    async def add_video_files(
        self,
        job_id: str,
        file_ids: list[str],
    ) -> JobDocument | None:
        """Add video file IDs to a job.

        Args:
            job_id: The job ID.
            file_ids: List of GridFS file IDs to add.

        Returns:
            The updated JobDocument if found, None otherwise.
        """
        doc = await self.find_one_by_id(ObjectId(job_id))
        if doc is None:
            return None

        doc.video_file_ids.extend(file_ids)
        doc.updated_at = datetime.now(UTC)
        await self.save(doc)
        return doc

    async def add_audio_files(
        self,
        job_id: str,
        file_ids: list[str],
    ) -> JobDocument | None:
        """Add audio file IDs to a job.

        Args:
            job_id: The job ID.
            file_ids: List of GridFS file IDs to add.

        Returns:
            The updated JobDocument if found, None otherwise.
        """
        doc = await self.find_one_by_id(ObjectId(job_id))
        if doc is None:
            return None

        doc.audio_file_ids.extend(file_ids)
        doc.updated_at = datetime.now(UTC)
        await self.save(doc)
        return doc

    async def set_manifest(
        self,
        job_id: str,
        manifest_id: str,
    ) -> JobDocument | None:
        """Set the manifest ID for a job.

        Args:
            job_id: The job ID.
            manifest_id: The manifest document ID.

        Returns:
            The updated JobDocument if found, None otherwise.
        """
        doc = await self.find_one_by_id(ObjectId(job_id))
        if doc is None:
            return None

        doc.manifest_id = manifest_id
        doc.updated_at = datetime.now(UTC)
        await self.save(doc)
        return doc

    async def set_blueprint(
        self,
        job_id: str,
        blueprint_id: str,
    ) -> JobDocument | None:
        """Set the blueprint ID for a job.

        Args:
            job_id: The job ID.
            blueprint_id: The blueprint document ID.

        Returns:
            The updated JobDocument if found, None otherwise.
        """
        doc = await self.find_one_by_id(ObjectId(job_id))
        if doc is None:
            return None

        doc.blueprint_id = blueprint_id
        doc.updated_at = datetime.now(UTC)
        await self.save(doc)
        return doc

    async def set_otio_file(
        self,
        job_id: str,
        otio_file_id: str,
    ) -> JobDocument | None:
        """Set the OTIO file ID for a job.

        Args:
            job_id: The job ID.
            otio_file_id: The GridFS file ID for the OTIO output.

        Returns:
            The updated JobDocument if found, None otherwise.
        """
        doc = await self.find_one_by_id(ObjectId(job_id))
        if doc is None:
            return None

        doc.otio_file_id = otio_file_id
        doc.updated_at = datetime.now(UTC)
        await self.save(doc)
        return doc

    async def start_processing(
        self,
        job_id: str,
        total_files: int,
        target_frame_rate: float = 60.0,
        style_profile_text: str | None = None,
    ) -> JobDocument | None:
        """Mark a job as started for processing.

        Args:
            job_id: The job ID.
            total_files: Total number of files to process.
            target_frame_rate: Target frame rate for output.
            style_profile_text: Optional style profile text.

        Returns:
            The updated JobDocument if found, None otherwise.
        """
        doc = await self.find_one_by_id(ObjectId(job_id))
        if doc is None:
            return None

        doc.stage = JobStage.QUEUED
        doc.total_files = total_files
        doc.target_frame_rate = target_frame_rate
        doc.style_profile_text = style_profile_text
        doc.updated_at = datetime.now(UTC)

        await self.save(doc)
        return doc

    async def update_stage(
        self,
        job_id: str,
        stage: JobStage,
    ) -> JobDocument | None:
        """Update a job's stage.

        Args:
            job_id: The job ID.
            stage: The new stage.

        Returns:
            The updated JobDocument if found, None otherwise.
        """
        doc = await self.find_one_by_id(ObjectId(job_id))
        if doc is None:
            return None

        doc.stage = stage
        doc.updated_at = datetime.now(UTC)

        if stage == JobStage.DOWNLOADING_FILES and doc.started_at is None:
            doc.started_at = datetime.now(UTC)
        elif stage in (JobStage.COMPLETED, JobStage.FAILED, JobStage.CANCELLED):
            doc.completed_at = datetime.now(UTC)

        await self.save(doc)
        return doc

    async def update_progress(
        self,
        job_id: str,
        processed_files: int,
        current_file: str | None = None,
        progress_percent: float | None = None,
    ) -> JobDocument | None:
        """Update job progress.

        Args:
            job_id: The job ID.
            processed_files: Number of files processed so far.
            current_file: Name of the file currently being processed.
            progress_percent: Overall progress percentage.

        Returns:
            The updated JobDocument if found, None otherwise.
        """
        doc = await self.find_one_by_id(ObjectId(job_id))
        if doc is None:
            return None

        doc.processed_files = processed_files
        doc.current_file = current_file
        if progress_percent is not None:
            doc.progress_percent = progress_percent
        doc.updated_at = datetime.now(UTC)

        await self.save(doc)
        return doc

    async def set_style_profile(
        self,
        job_id: str,
        style_profile_json: str | None = None,
        reference_otio_file_id: str | None = None,
    ) -> JobDocument | None:
        """Set the style profile for a job.

        Args:
            job_id: The job ID.
            style_profile_json: The StyleProfile serialized as JSON (optional).
            reference_otio_file_id: Optional GridFS ID of the reference OTIO.

        Returns:
            The updated JobDocument if found, None otherwise.
        """
        doc = await self.find_one_by_id(ObjectId(job_id))
        if doc is None:
            return None

        if style_profile_json is not None:
            doc.style_profile_json = style_profile_json
        if reference_otio_file_id is not None:
            doc.reference_otio_file_id = reference_otio_file_id
        doc.updated_at = datetime.now(UTC)

        await self.save(doc)
        return doc

    async def set_error(
        self,
        job_id: str,
        error_message: str,
    ) -> JobDocument | None:
        """Set job error and mark as failed.

        Args:
            job_id: The job ID.
            error_message: Error message describing the failure.

        Returns:
            The updated JobDocument if found, None otherwise.
        """
        doc = await self.find_one_by_id(ObjectId(job_id))
        if doc is None:
            return None

        doc.stage = JobStage.FAILED
        doc.error_message = error_message
        doc.completed_at = datetime.now(UTC)
        doc.updated_at = datetime.now(UTC)

        await self.save(doc)
        return doc
