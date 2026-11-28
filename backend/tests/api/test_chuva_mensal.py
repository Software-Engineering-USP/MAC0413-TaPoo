from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api.dependencias import criar_repositorios, montar_container
from app.aplicacao.portas import NormaisClimatologicas
from app.dominio.enums import TipoEstacao
from app.dominio.erros import FonteIndisponivel
from app.dominio.estacao import Estacao
from app.dominio.geografia import Coordenada
from app.dominio.municipio import Municipio
from app.dominio.normal_climatologica import NormalClimatologica
from app.main import create_app
from tests.aplicacao.fakes import FonteStub

AGORA = datetime(2026, 1, 10, 12, tzinfo=UTC)
ESTACAO = Estacao(
    123,
    "Pluviométrica de teste",
    TipoEstacao.PLUVIOMETRICA,
    Coordenada(-23.56, -46.72),
    Municipio("São Paulo", "SP"),
)
NORMAL = NormalClimatologica(
    83781,
    "SAO PAULO",
    "SP",
    Coordenada(-23.50, -46.62),
    (200.0,) + (100.0,) * 11,
)


class FonteIndisponivelStub(FonteStub):
    carregar_na_inicializacao = False

    def buscar_medicoes(self, codigo, periodo, alteradas_desde=None):
        raise FonteIndisponivel("ANA indisponível")


class NormaisStub(NormaisClimatologicas):
    def todas(self) -> list[NormalClimatologica]:
        return [NORMAL]


def test_chuva_mensal_sem_cache_quando_a_fonte_falha() -> None:
    fonte = FonteIndisponivelStub([ESTACAO], [])
    repositorios = criar_repositorios("memoria")
    repositorios.estacoes.salvar_varias([ESTACAO])
    app = create_app(
        lambda: montar_container(
            fonte,
            relogio=lambda: AGORA,
            repositorios=repositorios,
            normais=NormaisStub(),
        ),
        intervalo=lambda: None,
    )

    with TestClient(app) as client:
        resposta = client.get("/estacoes/123/chuva-mensal")

    assert resposta.status_code == 200
    assert resposta.json()["medicoes"] == 0
    assert resposta.json()["percentual"] is None
    assert resposta.json()["classificacao"] == "SEM_DADOS"
    assert resposta.json()["classificacao_rotulo"] == "Sem dados"
    assert resposta.json()["atualizado"] is False
