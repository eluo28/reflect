from pydantic import BaseModel, ConfigDict


class BaseReflectModel(BaseModel):
    """Base Pydantic model for the Reflect project.

    Provides defaults specific to our codebase and makes global changes easier.
    """

    model_config = ConfigDict(
        frozen=True,
        revalidate_instances="always",
        validate_assignment=True,
        populate_by_name=True,
    )
