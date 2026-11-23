from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.dependencias import montar_container
from app.infra.fontes.fake import FonteFake
from app.main import ORIGENS_CORS_PADRAO, create_app, origens_cors
from tests.api.conftest import AGORA

FRONT = "https://tapoo.example.org"


@pytest.fixture
def cliente_cors() -> Iterator[TestClient]:
    app = create_app(
        lambda: montar_container(FonteFake(AGORA), relogio=lambda: AGORA), origens=[FRONT]
    )
    with TestClient(app) as c:
        yield c


def test_origem_permitida_recebe_cabecalho(cliente_cors: TestClient) -> None:
    resposta = cliente_cors.get("/health", headers={"Origin": FRONT})
    assert resposta.headers["access-control-allow-origin"] == FRONT


def test_origem_desconhecida_nao_recebe_cabecalho(cliente_cors: TestClient) -> None:
    resposta = cliente_cors.get("/health", headers={"Origin": "https://outro.example.org"})
    assert resposta.status_code == 200  # CORS é aplicado pelo navegador, não pela API
    assert "access-control-allow-origin" not in resposta.headers


def test_preflight_libera_apenas_get(cliente_cors: TestClient) -> None:
    def preflight(metodo: str) -> int:
        cabecalhos = {"Origin": FRONT, "Access-Control-Request-Method": metodo}
        return cliente_cors.options("/estacoes", headers=cabecalhos).status_code

    assert preflight("GET") == 200
    assert preflight("POST") == 400


def test_origens_padrao_sem_variavel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CORS_ORIGENS", raising=False)
    assert origens_cors() == list(ORIGENS_CORS_PADRAO)


def test_origens_lidas_da_variavel(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGENS", " https://a.example.org/ , ,https://b.example.org")
    assert origens_cors() == ["https://a.example.org", "https://b.example.org"]


def test_variavel_vazia_bloqueia_todas(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGENS", "")
    assert origens_cors() == []
