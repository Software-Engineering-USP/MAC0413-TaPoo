"""Tradução centralizada das exceções em respostas HTTP.

Os controllers não usam `try/except`: deixam a exceção subir e ela é convertida aqui.
Toda resposta de erro tem o formato `{"detail": "<mensagem>"}`; erros de validação de
entrada trazem também `"erros"`, com a lista detalhada do FastAPI.

| Exceção                 | Status |
|-------------------------|--------|
| `RecursoNaoEncontrado`  | 404    |
| `ErroAplicacao` (demais)| 400    |
| `DadoInvalido`          | 422    |
| `RequestValidationError`| 422    |
| `FonteIndisponivel`     | 503    |
"""

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.aplicacao.erros import ErroAplicacao, RecursoNaoEncontrado
from app.dominio.erros import DadoInvalido, FonteIndisponivel

# Sugestão ao cliente de quando tentar de novo após a fonte externa falhar.
RETRY_AFTER_SEGUNDOS = 60


def _resposta(status_code: int, detalhe: str, **extra: object) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detalhe, **extra})


def _nao_encontrado(_: Request, erro: Exception) -> JSONResponse:
    return _resposta(status.HTTP_404_NOT_FOUND, str(erro))


def _erro_aplicacao(_: Request, erro: Exception) -> JSONResponse:
    return _resposta(status.HTTP_400_BAD_REQUEST, str(erro))


def _dado_invalido(_: Request, erro: Exception) -> JSONResponse:
    return _resposta(status.HTTP_422_UNPROCESSABLE_CONTENT, str(erro))


def _validacao(_: Request, erro: RequestValidationError) -> JSONResponse:
    erros = jsonable_encoder(erro.errors())
    mensagens = "; ".join(
        f"{'.'.join(str(p) for p in e['loc'] if p != 'query')}: {e['msg']}" for e in erros
    )
    return _resposta(status.HTTP_422_UNPROCESSABLE_CONTENT, mensagens, erros=erros)


def _fonte_indisponivel(_: Request, erro: Exception) -> JSONResponse:
    resposta = _resposta(status.HTTP_503_SERVICE_UNAVAILABLE, str(erro))
    resposta.headers["Retry-After"] = str(RETRY_AFTER_SEGUNDOS)
    return resposta


def registrar_handlers(app: FastAPI) -> None:
    # O Starlette escolhe o handler pela classe mais específica (MRO), então
    # RecursoNaoEncontrado vence ErroAplicacao mesmo sendo subclasse dela.
    app.add_exception_handler(RecursoNaoEncontrado, _nao_encontrado)
    app.add_exception_handler(ErroAplicacao, _erro_aplicacao)
    app.add_exception_handler(DadoInvalido, _dado_invalido)
    app.add_exception_handler(RequestValidationError, _validacao)
    app.add_exception_handler(FonteIndisponivel, _fonte_indisponivel)
