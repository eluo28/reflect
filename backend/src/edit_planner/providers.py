"""Providers for edit planner service."""

from functools import cache

from src.common.openai_model_identifier import OpenAIModelIdentifier
from src.edit_planner.service import EditPlannerService


@cache
def edit_planner_service(
    model_identifier: OpenAIModelIdentifier = OpenAIModelIdentifier.GPT_5_2,
) -> EditPlannerService:
    """Provide a cached instance of the EditPlannerService."""
    return EditPlannerService(model_identifier=model_identifier)
