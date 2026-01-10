"""API request schemas."""

from pydantic import Field

from src.common.base_reflect_model import BaseReflectModel


class CreateJobRequest(BaseReflectModel):
    """Request to create a new job."""

    name: str = Field(min_length=1, max_length=100)
    description: str = ""


class StartJobRequest(BaseReflectModel):
    """Request to start a pipeline job."""

    target_frame_rate: float = 60.0
    style_profile_text: str | None = None
