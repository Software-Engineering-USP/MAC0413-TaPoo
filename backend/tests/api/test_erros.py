import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.erros import RETRY_AFTER_SEGUNDOS, registrar_handlers
from app.aplicacao.erros import ErroAplicacao, EstacaoNaoEncontrada
from app.dominio.erros import DadoInvalido, FonteIndisponivel

ERROS = {
    "nao-encontrado": EstacaoNaoEncontrada(42),
    "aplicacao": ErroAplicacao("operação não permitida"),
    "dado-invalido": DadoInvalido("chuva não pode ser negativa"),
    "fonte": FonteIndisponivel("fonte fora do ar"),
}


@pytest.fixture
def cliente() -> TestClient:
    app = FastAPI()
    registrar_handlers(app)

    @app.get("/erro/{nome}")
    def lancar(nome: str) -> None:
        raise ERROS[nome]

    @app.get("/numero")
    def numero(valor: int) -> int:
        return valor

    return TestClient(app)


@pytest.mark.parametrize(
    ("nome", "status", "detalhe"),
    [
        ("nao-encontrado", 404, "estação 42 não encontrada"),
        ("aplicacao", 400, "operação não permitida"),
        ("dado-invalido", 422, "chuva não pode ser negativa"),
        ("fonte", 503, "fonte fora do ar"),
    ],
)
def test_excecao_vira_status_e_detalhe(cliente: TestClient, nome, status, detalhe) -> None:
    resposta = cliente.get(f"/erro/{nome}")
    assert resposta.status_code == status
    assert resposta.json() == {"detail": detalhe}


def test_fonte_indisponivel_sugere_quando_tentar_de_novo(cliente: TestClient) -> None:
    resposta = cliente.get("/erro/fonte")
    assert resposta.headers["Retry-After"] == str(RETRY_AFTER_SEGUNDOS)


def test_erro_de_validacao_tem_mensagem_legivel_e_lista(cliente: TestClient) -> None:
    resposta = cliente.get("/numero?valor=abc")
    corpo = resposta.json()
    assert resposta.status_code == 422
    assert corpo["detail"].startswith("valor: ")
    assert corpo["erros"][0]["loc"] == ["query", "valor"]


def test_parametro_obrigatorio_ausente(cliente: TestClient) -> None:
    corpo = cliente.get("/numero").json()
    assert corpo["detail"] == "valor: Field required"
