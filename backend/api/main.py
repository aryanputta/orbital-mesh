import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from api.websocket_manager import get_ws_manager
from api.routers import nodes, telemetry, topology, anomalies, control
from core.logging import configure_logging, get_logger
from core.config import get_settings

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    configure_logging()
    settings = get_settings()

    from simulation.runner import get_runner, create_runner
    runner = get_runner()
    if runner is None:
        runner = await create_runner()
        await runner.start()

    ws_manager = get_ws_manager()
    await ws_manager.start_broadcast_loop()

    logger.info("api.startup.complete", host=settings.api_host, port=settings.api_port)
    yield

    logger.info("api.shutdown.starting")
    await ws_manager.stop_broadcast_loop()

    runner = get_runner()
    if runner:
        await runner.stop()

    logger.info("api.shutdown.complete")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Orbital Mesh",
        description="Distributed telemetry and control system",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:5173", "http://frontend"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(nodes.router, prefix="/api/v1")
    app.include_router(telemetry.router, prefix="/api/v1")
    app.include_router(topology.router, prefix="/api/v1")
    app.include_router(anomalies.router, prefix="/api/v1")
    app.include_router(control.router, prefix="/api/v1")

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        manager = get_ws_manager()
        conn_id = await manager.connect(websocket)
        try:
            while True:
                data = await websocket.receive_text()
        except WebSocketDisconnect:
            await manager.disconnect(conn_id)
        except Exception as exc:
            logger.warning("websocket.error", conn_id=conn_id, error=str(exc))
            await manager.disconnect(conn_id)

    return app


app = create_app()
