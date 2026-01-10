"""Asset type enum."""

from enum import StrEnum, auto


class AssetType(StrEnum):
    """Type of asset being annotated."""

    VIDEO = auto()
    AUDIO = auto()
