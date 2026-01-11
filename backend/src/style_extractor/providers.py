"""Providers for style extractor service."""

from functools import cache

from src.common.openai_model_identifier import OpenAIModelIdentifier
from src.style_extractor.service import StyleExtractorService


@cache
def style_extractor_service(
    model_identifier: OpenAIModelIdentifier = OpenAIModelIdentifier.GPT_5_2,
) -> StyleExtractorService:
    """Provide a singleton instance of the StyleExtractorService."""
    return StyleExtractorService(model_identifier)
