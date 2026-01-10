"""Providers for edit executor service."""

from functools import cache

from src.edit_executor.service import EditExecutorService


@cache
def edit_executor_service() -> EditExecutorService:
    """Provide a cached instance of the EditExecutorService."""
    return EditExecutorService()
