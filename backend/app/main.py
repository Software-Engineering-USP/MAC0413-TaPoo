import os
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.dependencias import Container, carga_inicial, criar_agendador, montar_container
from app.api.erros import registrar_handlers
from app.api.routers import alertas, estacoes, municipios
from app.configuracao import intervalo_coleta

# Front servido pelo compose (3000) e pelo `npm run dev` do Vite (5173).
ORIGENS_CORS_PADRAO = ("http://localhost:3000", "http://localhost:5173")


def origens_cors() -> list[str]:
    """Origens com acesso à API, de `CORS_ORIGENS` (separadas por vírgula)."""
    valor = os.getenv("CORS_ORIGENS")
    if valor is None:
        return list(ORIGENS_CORS_PADRAO)
    return [origem.strip().rstrip("/") for origem in valor.split(",") if origem.strip()]


def health() -> dict[str, str]:
    return {"status": "ok"}


def create_app(
    fabrica: Callable[[], Container] = montar_container,
    intervalo: Callable[[], timedelta | None] = intervalo_coleta,
    origens: Sequence[str] | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        container = fabrica()
        carga_inicial(container)
        app.state.container = container
        periodo = intervalo()
        app.state.agendador = criar_agendador(container, periodo) if periodo else None
        if app.state.agendador is not None:
            app.state.agendador.iniciar()
        try:
            yield
        finally:
            if app.state.agendador is not None:
                await app.state.agendador.parar()

    app = FastAPI(title="TaPoo API", version="0.1.0", lifespan=lifespan)
    # A API é só de leitura e não usa cookies: basta liberar GET das origens do front.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(origens) if origens is not None else origens_cors(),
        allow_methods=["GET"],
    )
    app.add_api_route("/health", health, methods=["GET"], tags=["infra"])
    registrar_handlers(app)
    app.include_router(estacoes.router)
    app.include_router(alertas.router)
    app.include_router(municipios.router)
    return app


app = create_app()
