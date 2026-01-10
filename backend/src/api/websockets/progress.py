"""WebSocket handler for real-time progress updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.pipeline.progress_reporter import connection_manager

router = APIRouter()


@router.websocket("/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str) -> None:
    """WebSocket endpoint for real-time progress updates."""
    await connection_manager.connect(websocket, job_id)
    try:
        while True:
            # Keep connection alive, listen for client messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket, job_id)
