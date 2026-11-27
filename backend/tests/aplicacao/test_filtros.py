import pytest

from app.aplicacao.filtros import FiltroEstacoes
from app.dominio.enums import TipoEstacao
from app.dominio.estacao import Estacao
from app.dominio.geografia import Coordenada
from app.dominio.municipio import Municipio

TIETE = Estacao(
    1,
    "Ponte das Bandeiras",
    TipoEstacao.FLUVIOMETRICA,
    Coordenada(-23.5, -46.6),
    Municipio("São Paulo", "SP"),
    rio="Rio Tietê",
)


@pytest.mark.parametrize(
    "texto",
    ["bandeiras", "PONTE", "tiete", "Tietê", "sao paulo", "  são   PAULO ", "tiete paulo"],
)
def test_texto_encontra_nome_municipio_ou_rio(texto: str) -> None:
    assert FiltroEstacoes(texto=texto).aceita(TIETE)


@pytest.mark.parametrize("texto", ["campinas", "tiete campinas", "rio doce"])
def test_texto_exige_todas_as_palavras(texto: str) -> None:
    assert not FiltroEstacoes(texto=texto).aceita(TIETE)


def test_texto_em_estacao_sem_rio() -> None:
    estacao = Estacao(
        2,
        "Campinas",
        TipoEstacao.PLUVIOMETRICA,
        Coordenada(-22.9, -47.0),
        Municipio("Campinas", "SP"),
    )
    assert FiltroEstacoes(texto="campinas").aceita(estacao)
    assert not FiltroEstacoes(texto="rio").aceita(estacao)


def test_texto_combina_com_os_outros_criterios() -> None:
    assert FiltroEstacoes(uf="sp", texto="tiete").aceita(TIETE)
    assert not FiltroEstacoes(uf="mg", texto="tiete").aceita(TIETE)
    assert not FiltroEstacoes(tipo=TipoEstacao.PLUVIOMETRICA, texto="tiete").aceita(TIETE)


@pytest.mark.parametrize("texto", ["", "   ", "\t\n"])
def test_texto_sem_palavras_nao_aceita_nenhuma_estacao(texto: str) -> None:
    assert not FiltroEstacoes(texto=texto).aceita(TIETE)


def test_sem_texto_aceita_qualquer_estacao() -> None:
    assert FiltroEstacoes().aceita(TIETE)
