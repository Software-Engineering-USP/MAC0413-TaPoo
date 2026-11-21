from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.dependencias import Container, carga_inicial, criar_agendador, montar_container
from app.api.routers import alertas, estacoes, municipios
from app.aplicacao.erros import RecursoNaoEncontrado
from app.configuracao import intervalo_coleta
from app.infra.fontes.ana import ErroFonteAna


def health() -> dict[str, str]:
    return {"status": "ok"}


def _nao_encontrado(_: Request, erro: Exception) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(erro)})


def _ana_indisponivel(_: Request, erro: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={"detail": str(erro)},
    )


def create_app(
    fabrica: Callable[[], Container] = montar_container,
    intervalo: Callable[[], timedelta | None] = intervalo_coleta,
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
    app.add_api_route("/health", health, methods=["GET"], tags=["infra"])
    app.add_exception_handler(RecursoNaoEncontrado, _nao_encontrado)
    app.add_exception_handler(ErroFonteAna, _ana_indisponivel)
    app.include_router(estacoes.router)
    app.include_router(alertas.router)
    app.include_router(municipios.router)
    return app


app = create_app()
