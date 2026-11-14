from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.dependencias import Container, carga_inicial, montar_container
from app.api.routers import alertas, estacoes
from app.aplicacao.erros import EstacaoNaoEncontrada


def health() -> dict[str, str]:
    return {"status": "ok"}


async def _estacao_nao_encontrada(_: Request, erro: Exception) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(erro)})


def create_app(fabrica: Callable[[], Container] = montar_container) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        container = fabrica()
        carga_inicial(container)
        app.state.container = container
        yield

    app = FastAPI(title="TaPoo API", version="0.1.0", lifespan=lifespan)
    app.add_api_route("/health", health, methods=["GET"], tags=["infra"])
    app.add_exception_handler(EstacaoNaoEncontrada, _estacao_nao_encontrada)
    app.include_router(estacoes.router)
    app.include_router(alertas.router)
    return app


app = create_app()
