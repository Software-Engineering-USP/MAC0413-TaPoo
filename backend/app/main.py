from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.dependencias import Container, carga_inicial, montar_container
from app.api.erros import registrar_handlers
from app.api.routers import alertas, estacoes, municipios


def health() -> dict[str, str]:
    return {"status": "ok"}


def create_app(fabrica: Callable[[], Container] = montar_container) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        container = fabrica()
        carga_inicial(container)
        app.state.container = container
        yield

    app = FastAPI(title="TaPoo API", version="0.1.0", lifespan=lifespan)
    app.add_api_route("/health", health, methods=["GET"], tags=["infra"])
    registrar_handlers(app)
    app.include_router(estacoes.router)
    app.include_router(alertas.router)
    app.include_router(municipios.router)
    return app


app = create_app()
