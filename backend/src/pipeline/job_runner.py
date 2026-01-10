"""Pipeline job runner that orchestrates the full processing workflow."""

from __future__ import annotations

import asyncio
import logging
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from src.api.schemas.websocket import PipelineStage
from src.asset_annotator.annotator import annotate_assets
from src.edit_executor.providers import edit_executor_service
from src.edit_planner.providers import edit_planner_service
from src.style_extractor.providers import style_extractor_service
from src.edit_planner.schemas import AssemblyInput, TimelineBlueprint
from src.mongodb.gridfs_service import FileType, get_gridfs_service
from src.mongodb.repositories import BlueprintRepository, JobRepository, ManifestRepository
from src.mongodb.schemas import JobDocument, JobStage
from src.pipeline.progress_reporter import ProgressReporter
from src.style_extractor.schemas import StyleProfile

from src.asset_annotator.schemas import AssetManifest

logger = logging.getLogger(__name__)


class JobRunner:
    """Orchestrates the full pipeline execution."""

    def __init__(self, job_id: str) -> None:
        """Initialize the job runner.

        Args:
            job_id: The job ID for tracking.
        """
        self.job_id = job_id
        self.reporter = ProgressReporter(job_id)
        self.gridfs = get_gridfs_service()
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def run(self) -> None:
        """Execute the full pipeline with checkpoint resume support."""
        job_repo = JobRepository.create()
        manifest_repo = ManifestRepository.create()
        blueprint_repo = BlueprintRepository.create()
        temp_dir: Path | None = None

        logger.info("[job=%s] Starting pipeline execution", self.job_id)

        try:
            # Get job
            job = await job_repo.get_job(self.job_id)
            if not job:
                msg = f"Job {self.job_id} not found"
                raise ValueError(msg)

            total_files = len(job.video_file_ids) + len(job.audio_file_ids)
            logger.info(
                "[job=%s] Job loaded: name=%s, videos=%d, audio=%d",
                self.job_id,
                job.name,
                len(job.video_file_ids),
                len(job.audio_file_ids),
            )

            # Check for existing checkpoints
            manifest: AssetManifest | None = None
            manifest_id: str | None = job.manifest_id
            blueprint: TimelineBlueprint | None = None
            blueprint_id: str | None = job.blueprint_id

            # Try to load existing manifest (checkpoint 1)
            if manifest_id:
                logger.info("[job=%s] Found existing manifest checkpoint: %s", self.job_id, manifest_id)
                manifest = await manifest_repo.get_manifest(manifest_id)
                if manifest:
                    logger.info("[job=%s] Loaded manifest from checkpoint - skipping download/annotation", self.job_id)
                    await self.reporter.send_progress(
                        stage=PipelineStage.ANNOTATING,
                        progress_percent=60,
                        message="Loaded cached analysis results...",
                    )

            # Try to load existing blueprint (checkpoint 2)
            if blueprint_id:
                logger.info("[job=%s] Found existing blueprint checkpoint: %s", self.job_id, blueprint_id)
                blueprint = await blueprint_repo.get_blueprint(blueprint_id)
                if blueprint:
                    logger.info("[job=%s] Loaded blueprint from checkpoint - skipping planning", self.job_id)
                    await self.reporter.send_progress(
                        stage=PipelineStage.PLANNING,
                        progress_percent=70,
                        message="Loaded cached edit plan...",
                    )

            # Stage 1 & 2: Download and annotate (skip if manifest exists)
            if manifest is None:
                # Stage 1: Download files from GridFS (parallel)
                logger.info("[job=%s] Stage 1: Downloading %d files from GridFS", self.job_id, total_files)
                await self._update_stage(job_repo, JobStage.DOWNLOADING_FILES)
                await self.reporter.send_progress(
                    stage=PipelineStage.UPLOADING,
                    progress_percent=0,
                    total_items=total_files,
                    processed_items=0,
                    message="Preparing files for processing...",
                )

                temp_dir = Path(tempfile.mkdtemp(prefix="reflect_"))
                video_paths, audio_paths = await self._download_files(job, temp_dir, total_files)
                logger.info(
                    "[job=%s] Downloaded %d videos, %d audio files to %s",
                    self.job_id,
                    len(video_paths),
                    len(audio_paths),
                    temp_dir,
                )

                # Stage 2: Annotate assets
                logger.info("[job=%s] Stage 2: Annotating assets", self.job_id)
                await self._update_stage(job_repo, JobStage.ANNOTATING_ASSETS)

                manifest = await self._annotate_assets(
                    video_paths, audio_paths, job_repo, total_files
                )

                # Save manifest to MongoDB (checkpoint 1)
                logger.info(
                    "[job=%s] Saving manifest checkpoint: %d video assets, %d audio assets",
                    self.job_id,
                    len(manifest.video_assets),
                    len(manifest.audio_assets),
                )
                manifest_doc = await manifest_repo.save_manifest(self.job_id, manifest)
                manifest_id = str(manifest_doc.id)
                await job_repo.set_manifest(self.job_id, manifest_id)
                logger.info("[job=%s] Manifest checkpoint saved: %s", self.job_id, manifest_id)

            # Stage 3: Plan edits (skip if blueprint exists)
            if blueprint is None:
                logger.info("[job=%s] Stage 3: Planning edits", self.job_id)
                await self._update_stage(job_repo, JobStage.PLANNING_EDITS)
                await self.reporter.send_progress(
                    stage=PipelineStage.PLANNING,
                    progress_percent=70,
                    message="AI planning edit decisions...",
                )

                # Refresh job for config
                job = await job_repo.get_job(self.job_id)
                target_frame_rate = job.target_frame_rate if job else 60.0
                loop = asyncio.get_event_loop()

                # Load or extract style profile
                style_profile: StyleProfile | None = None

                # Check for cached style profile (checkpoint)
                if job and job.style_profile_json:
                    try:
                        style_profile = StyleProfile.model_validate_json(
                            job.style_profile_json
                        )
                        logger.info(
                            "[job=%s] Loaded cached style profile: %.1f cuts/min",
                            self.job_id,
                            style_profile.target_cuts_per_minute,
                        )
                        await self.reporter.send_progress(
                            stage=PipelineStage.PLANNING,
                            progress_percent=65,
                            message="Loaded cached style profile...",
                        )
                    except Exception as e:
                        logger.warning(
                            "[job=%s] Failed to parse cached style profile: %s",
                            self.job_id,
                            e,
                        )

                # Extract style from reference OTIO if not cached
                if style_profile is None and job and job.reference_otio_file_id:
                    logger.info(
                        "[job=%s] Extracting style from reference OTIO: %s",
                        self.job_id,
                        job.reference_otio_file_id,
                    )
                    await self.reporter.send_progress(
                        stage=PipelineStage.PLANNING,
                        progress_percent=65,
                        message="Extracting style from reference...",
                    )

                    # Ensure temp_dir exists for download
                    if temp_dir is None:
                        temp_dir = Path(tempfile.mkdtemp(prefix="reflect_"))

                    # Download reference OTIO
                    ref_path = temp_dir / "reference.otio"
                    await self.gridfs.download_file(job.reference_otio_file_id, ref_path)

                    # Extract style (in thread pool - has LLM call)
                    extracted_profile: StyleProfile = await loop.run_in_executor(
                        self.executor,
                        style_extractor_service().extract_style_from_file,
                        ref_path,
                    )
                    style_profile = extracted_profile
                    logger.info(
                        "[job=%s] Extracted style profile: %.1f cuts/min, prefer_beat_alignment=%s",
                        self.job_id,
                        extracted_profile.target_cuts_per_minute,
                        extracted_profile.prefer_beat_alignment,
                    )

                    # Save style profile checkpoint
                    await job_repo.set_style_profile(
                        self.job_id,
                        style_profile_json=extracted_profile.model_dump_json(),
                    )
                    logger.info("[job=%s] Style profile checkpoint saved", self.job_id)

                assembly_input = AssemblyInput(
                    manifest=manifest,
                    style_profile=style_profile,
                    target_frame_rate=target_frame_rate,
                )

                new_blueprint: TimelineBlueprint = await loop.run_in_executor(
                    self.executor,
                    edit_planner_service().assemble,
                    assembly_input,
                )
                blueprint = new_blueprint

                # Save blueprint to MongoDB (checkpoint 2)
                logger.info(
                    "[job=%s] Saving blueprint checkpoint: duration=%.2fs, %d chunks, %d cuts",
                    self.job_id,
                    new_blueprint.total_duration_seconds,
                    len(new_blueprint.chunk_decisions),
                    len(new_blueprint.all_decisions),
                )
                blueprint_doc = await blueprint_repo.save_blueprint(
                    self.job_id, manifest_id or "", new_blueprint
                )
                blueprint_id = str(blueprint_doc.id)
                await job_repo.set_blueprint(self.job_id, blueprint_id)
                logger.info("[job=%s] Blueprint checkpoint saved: %s", self.job_id, blueprint_id)

            # At this point, both manifest and blueprint must be set
            assert manifest is not None, "Manifest should be set by now"
            assert blueprint is not None, "Blueprint should be set by now"

            # Stage 4: Execute timeline (always run - generates new OTIO)
            logger.info("[job=%s] Stage 4: Executing timeline (generating OTIO)", self.job_id)
            await self._update_stage(job_repo, JobStage.EXECUTING_TIMELINE)
            await self.reporter.send_progress(
                stage=PipelineStage.EXECUTING,
                progress_percent=85,
                message="Building OTIO timeline...",
            )

            # Create temp dir for OTIO if not already created
            if temp_dir is None:
                temp_dir = Path(tempfile.mkdtemp(prefix="reflect_"))

            loop = asyncio.get_event_loop()
            otio_path = temp_dir / "final_edit.otio"
            await loop.run_in_executor(
                self.executor,
                edit_executor_service().execute,
                blueprint,
                otio_path,
            )
            logger.info("[job=%s] OTIO file generated at %s", self.job_id, otio_path)

            # Stage 5: Upload result
            logger.info("[job=%s] Stage 5: Uploading result to GridFS", self.job_id)
            await self._update_stage(job_repo, JobStage.UPLOADING_RESULT)
            await self.reporter.send_progress(
                stage=PipelineStage.EXECUTING,
                progress_percent=95,
                message="Saving result...",
            )

            stored_file = await self.gridfs.upload_file(
                otio_path,
                FileType.OTIO_ARTIFACT,
                project_id=self.job_id,
                custom_filename=f"reflect_edit_{self.job_id}.otio",
            )

            await job_repo.set_otio_file(self.job_id, stored_file.file_id)
            logger.info(
                "[job=%s] OTIO uploaded to GridFS with file_id=%s",
                self.job_id,
                stored_file.file_id,
            )

            # Complete
            await self._update_stage(job_repo, JobStage.COMPLETED)
            await self.reporter.send_complete()
            logger.info("[job=%s] Pipeline completed successfully", self.job_id)

        except Exception as e:
            logger.exception("[job=%s] Pipeline failed with error", self.job_id)
            await self._handle_error(job_repo, e)
            raise

        finally:
            # Cleanup temp directory
            if temp_dir and temp_dir.exists():
                logger.info("[job=%s] Cleaning up temp directory: %s", self.job_id, temp_dir)
                shutil.rmtree(temp_dir, ignore_errors=True)

    async def _download_files(
        self,
        job: JobDocument,
        temp_dir: Path,
        total_files: int,
    ) -> tuple[list[Path], list[Path]]:
        """Download job files from GridFS in parallel with progress reporting."""
        completed = 0
        lock = asyncio.Lock()

        async def download_one(file_id: str, is_video: bool) -> tuple[Path | None, bool]:
            """Download a single file and report progress."""
            nonlocal completed
            file_info = await self.gridfs.get_file_info(file_id)
            if not file_info:
                return None, is_video

            dest = temp_dir / file_info.filename
            _, was_cached = await self.gridfs.download_file_cached(file_id, dest)

            # Update progress
            async with lock:
                completed += 1
                percent = (completed / total_files) * 10  # 0-10% for downloads
                cache_status = "CACHE HIT" if was_cached else "downloaded"
                await self.reporter.send_progress(
                    stage=PipelineStage.UPLOADING,
                    progress_percent=percent,
                    current_item=file_info.filename,
                    total_items=total_files,
                    processed_items=completed,
                    message=f"{cache_status}: {file_info.filename} ({completed}/{total_files})",
                )
                logger.info(
                    "[job=%s] %s file %d/%d: %s",
                    self.job_id,
                    cache_status,
                    completed,
                    total_files,
                    file_info.filename,
                )

            return dest, is_video

        # Create all download tasks
        tasks: list[asyncio.Task[tuple[Path | None, bool]]] = []
        for file_id in job.video_file_ids:
            tasks.append(asyncio.create_task(download_one(file_id, is_video=True)))
        for file_id in job.audio_file_ids:
            tasks.append(asyncio.create_task(download_one(file_id, is_video=False)))

        # Download all in parallel
        results = await asyncio.gather(*tasks)

        # Separate results by type
        video_paths = [r[0] for r in results if r[0] is not None and r[1]]
        audio_paths = [r[0] for r in results if r[0] is not None and not r[1]]

        return video_paths, audio_paths

    async def _annotate_assets(
        self,
        video_paths: list[Path],
        audio_paths: list[Path],
        job_repo: JobRepository,
        total_files: int,
    ) -> AssetManifest:
        """Run asset annotation with progress reporting."""
        logger.info(
            "[job=%s] Starting annotation of %d files (%d videos, %d audio)",
            self.job_id,
            total_files,
            len(video_paths),
            len(audio_paths),
        )

        processed = 0
        loop = asyncio.get_event_loop()

        def on_progress(current: int, total: int, filename: str) -> None:
            nonlocal processed
            processed = current
            percent = (current / total) * 50 + 10  # 10-60% range for annotation

            logger.info(
                "[job=%s] Annotating file %d/%d: %s",
                self.job_id,
                current,
                total,
                filename,
            )

            # Schedule async updates
            asyncio.run_coroutine_threadsafe(
                self._update_annotation_progress(
                    job_repo, current, filename, percent, total
                ),
                loop,
            )

        # Run in thread pool (CPU-intensive)
        manifest = await loop.run_in_executor(
            self.executor,
            lambda: annotate_assets(video_paths, audio_paths, on_progress, max_workers=4),
        )

        logger.info("[job=%s] Annotation complete", self.job_id)
        return manifest

    async def _update_annotation_progress(
        self,
        job_repo: JobRepository,
        processed: int,
        filename: str,
        percent: float,
        total: int,
    ) -> None:
        """Update annotation progress in DB and WebSocket."""
        await job_repo.update_progress(
            self.job_id,
            processed_files=processed,
            current_file=filename,
            progress_percent=percent,
        )
        await self.reporter.send_progress(
            stage=PipelineStage.ANNOTATING,
            progress_percent=percent,
            current_item=filename,
            total_items=total,
            processed_items=processed,
            message=f"Analyzing {filename}...",
        )

    async def _update_stage(self, job_repo: JobRepository, stage: JobStage) -> None:
        """Update job stage in database."""
        await job_repo.update_stage(self.job_id, stage)

    async def _handle_error(self, job_repo: JobRepository, error: Exception) -> None:
        """Handle job error."""
        error_msg = f"{type(error).__name__}: {error}"
        await job_repo.set_error(self.job_id, error_msg)
        await self.reporter.send_error(error_msg)
