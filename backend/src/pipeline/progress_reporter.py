"""WebSocket connection manager and progress reporter."""

import logging

from fastapi import WebSocket

from src.api.schemas.websocket import PipelineStage, ProgressMessage

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections per job."""

    def __init__(self) -> None:
        """Initialize the connection manager."""
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, job_id: str) -> None:
        """Accept a WebSocket connection and register it for a job."""
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = []
        self.active_connections[job_id].append(websocket)
        logger.info("[ws] Client connected for job=%s (total: %d)", job_id, len(self.active_connections[job_id]))

    def disconnect(self, websocket: WebSocket, job_id: str) -> None:
        """Remove a WebSocket connection."""
        if job_id in self.active_connections:
            if websocket in self.active_connections[job_id]:
                self.active_connections[job_id].remove(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]

    async def broadcast(self, job_id: str, message: ProgressMessage) -> None:
        """Broadcast a message to all connections for a job."""
        if job_id not in self.active_connections:
            return

        disconnected: list[WebSocket] = []
        for connection in self.active_connections[job_id]:
            try:
                await connection.send_json(message.model_dump(mode="json"))
            except Exception:
                disconnected.append(connection)

        # Clean up disconnected sockets
        for ws in disconnected:
            self.disconnect(ws, job_id)


# Global instance
connection_manager = ConnectionManager()


class ProgressReporter:
    """Reports progress to WebSocket clients and updates job state."""

    def __init__(self, job_id: str) -> None:
        """Initialize the progress reporter.

        Args:
            job_id: The job ID.
        """
        self.job_id = job_id

    async def send_progress(
        self,
        stage: PipelineStage,
        progress_percent: float,
        current_item: str | None = None,
        total_items: int = 0,
        processed_items: int = 0,
        message: str = "",
    ) -> None:
        """Send a progress update to connected clients.

        Args:
            stage: Current pipeline stage.
            progress_percent: Overall progress percentage (0-100).
            current_item: Name of item currently being processed.
            total_items: Total number of items.
            processed_items: Number of items processed.
            message: Optional status message.
        """
        # Log to terminal for visibility
        logger.info(
            "[job=%s] PROGRESS: stage=%s, percent=%.1f%%, message=%s",
            self.job_id,
            stage.value,
            progress_percent,
            message or current_item or "-",
        )

        msg = ProgressMessage(
            job_id=self.job_id,
            stage=stage,
            progress_percent=progress_percent,
            current_item=current_item,
            total_items=total_items,
            processed_items=processed_items,
            message=message,
        )
        await connection_manager.broadcast(self.job_id, msg)

    async def send_complete(self) -> None:
        """Send completion notification."""
        await self.send_progress(
            stage=PipelineStage.COMPLETED,
            progress_percent=100.0,
            message="Processing complete!",
        )

    async def send_error(self, error_message: str) -> None:
        """Send error notification."""
        await self.send_progress(
            stage=PipelineStage.FAILED,
            progress_percent=0.0,
            message=error_message,
        )
