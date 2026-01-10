"""Style profile output schema."""

from src.common.base_reflect_model import BaseReflectModel


class StyleProfile(BaseReflectModel):
    """Output schema containing the extracted editing style profile.

    Contains a natural language description of the editing style,
    similar to the style_profile.md described in CLAUDE.md.
    """

    profile: str
