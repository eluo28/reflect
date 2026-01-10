"""Repository for TimelineBlueprint documents."""

from bson import ObjectId
from pydantic_mongo import AsyncAbstractRepository

from src.edit_planner.schemas import TimelineBlueprint
from src.mongodb.client import get_mongodb_client
from src.mongodb.schemas import BlueprintDocument


class BlueprintRepository(AsyncAbstractRepository[BlueprintDocument]):
    """Repository for storing and retrieving timeline blueprints."""

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        collection_name = "blueprints"

    @classmethod
    def create(cls) -> "BlueprintRepository":
        """Create a repository instance with the default database."""
        client = get_mongodb_client()
        return cls(client.database)  # pyright: ignore[reportArgumentType]

    async def save_blueprint(
        self,
        job_id: str,
        manifest_id: str,
        blueprint: TimelineBlueprint,
    ) -> BlueprintDocument:
        """Save a TimelineBlueprint to the database.

        Args:
            job_id: The job this blueprint belongs to.
            manifest_id: The manifest this blueprint was generated from.
            blueprint: The TimelineBlueprint to save.

        Returns:
            The saved BlueprintDocument with ID populated.
        """
        doc = BlueprintDocument(
            job_id=job_id,
            manifest_id=manifest_id,
            blueprint_json=blueprint.model_dump_json(),
            total_duration_seconds=blueprint.total_duration_seconds,
            frame_rate=blueprint.frame_rate,
            chunk_count=len(blueprint.chunk_decisions),
            cut_count=len(blueprint.all_decisions),
        )

        await self.save(doc)
        return doc

    async def get_blueprint(self, blueprint_id: str) -> TimelineBlueprint | None:
        """Retrieve a TimelineBlueprint by its document ID.

        Args:
            blueprint_id: The document ID.

        Returns:
            The TimelineBlueprint if found, None otherwise.
        """
        doc = await self.find_one_by_id(ObjectId(blueprint_id))
        if doc is None:
            return None
        return TimelineBlueprint.model_validate_json(doc.blueprint_json)

    async def get_blueprint_by_job(
        self,
        job_id: str,
    ) -> TimelineBlueprint | None:
        """Retrieve the TimelineBlueprint for a job.

        Args:
            job_id: The job ID.

        Returns:
            The TimelineBlueprint if found, None otherwise.
        """
        docs = await self.find_by({"job_id": job_id})
        doc_list = list(docs)
        if not doc_list:
            return None
        # Return the most recent one
        doc = doc_list[-1]
        return TimelineBlueprint.model_validate_json(doc.blueprint_json)
