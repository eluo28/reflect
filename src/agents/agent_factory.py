"""Factory for creating agents with consistent model configuration."""

from typing import Any

from agents.extensions.models.litellm_model import LitellmModel

from agents import Agent
from src.common.openai_model_identifier import OpenAIModelIdentifier

# Mapping of model identifiers to LiteLLM model strings
LITELLM_MODEL_MAP: dict[OpenAIModelIdentifier, str] = {
    OpenAIModelIdentifier.GPT_OSS_120B: "ollama/gpt-oss:120b-cloud",
}


def resolve_model(
    model_identifier: OpenAIModelIdentifier,
) -> str | LitellmModel:
    """Resolve a model identifier to an agent-compatible model.

    Args:
        model_identifier: The model identifier to resolve.

    Returns:
        Either a string model name or a LitellmModel instance.
    """
    if model_identifier in LITELLM_MODEL_MAP:
        return LitellmModel(model=LITELLM_MODEL_MAP[model_identifier])
    return model_identifier.value


def create_agent(
    *,
    name: str,
    instructions: str,
    model_identifier: OpenAIModelIdentifier,
    output_type: type[Any] | None = None,
    tools: list[Any] | None = None,
) -> Agent[Any]:
    """Create an agent with consistent model configuration.

    Args:
        name: The name of the agent.
        instructions: The system instructions for the agent.
        model_identifier: The model to use for the agent.
        output_type: Optional structured output type (Pydantic model).
        tools: Optional list of tools for the agent.

    Returns:
        A configured Agent instance.
    """
    model = resolve_model(model_identifier)

    agent_kwargs: dict[str, Any] = {
        "name": name,
        "instructions": instructions,
        "model": model,
    }

    if output_type is not None:
        agent_kwargs["output_type"] = output_type

    if tools is not None:
        agent_kwargs["tools"] = tools

    return Agent(**agent_kwargs)
