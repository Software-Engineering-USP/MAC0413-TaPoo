from datetime import UTC, datetime, timedelta

import pytest

from app.aplicacao.filtros import FiltroEstacoes
from app.aplicacao.sincronizacao import SincronizarEstacoes
from app.dominio.enums import TipoEstacao
from app.dominio.erros import FonteIndisponivel
from app.dominio.estacao import Estacao
from app.dominio.geografia import Coordenada
from app.dominio.municipio import Municipio
from tests.aplicacao.fakes import Estacoes, FonteStub

AGORA = datetime(2026, 1, 10, 12, tzinfo=UTC)
ESTACAO = Estacao(
    1,
    "Rio Pinheiros",
    TipoEstacao.FLUVIOMETRICA,
    Coordenada(-23.56, -46.72),
    Municipio("São Paulo", "SP"),
)


class FonteInstavel(FonteStub):
    def __init__(self) -> None:
        super().__init__([ESTACAO], [])
        self.fora = False
        self.consultas = 0

    def listar_estacoes(self, filtro: FiltroEstacoes) -> list[Estacao]:
        self.consultas += 1
        if self.fora:
            raise FonteIndisponivel("ANA fora")
        return super().listar_estacoes(filtro)


class Relogio:
    def __init__(self) -> None:
        self.agora = AGORA

    def __call__(self) -> datetime:
        return self.agora


def _cenario() -> tuple[FonteInstavel, Estacoes, Relogio, SincronizarEstacoes]:
    fonte, estacoes, relogio = FonteInstavel(), Estacoes(), Relogio()
    return fonte, estacoes, relogio, SincronizarEstacoes(fonte, estacoes, relogio=relogio)


def test_fonte_fora_com_inventario_local_segue_sem_erro(caplog) -> None:
    fonte, estacoes, _, sincronizar = _cenario()
    sincronizar.executar()
    fonte.fora = True

    assert sincronizar.executar() == 0
    assert list(estacoes.dados) == [1]
    assert "inventário da fonte indisponível" in caplog.text


def test_fonte_fora_sem_inventario_local_propaga() -> None:
    fonte, _, _, sincronizar = _cenario()
    fonte.fora = True

    with pytest.raises(FonteIndisponivel, match="ANA fora"):
        sincronizar.executar()


def test_fonte_fora_sem_estacoes_para_o_filtro_propaga() -> None:
    fonte, _, _, sincronizar = _cenario()
    sincronizar.executar()
    fonte.fora = True

    with pytest.raises(FonteIndisponivel):
        sincronizar.executar(FiltroEstacoes(uf="MG"))


def test_depois_da_falha_espera_antes_de_consultar_a_fonte_de_novo() -> None:
    fonte, _, relogio, sincronizar = _cenario()
    sincronizar.executar()
    fonte.fora = True
    sincronizar.executar()
    assert fonte.consultas == 2

    relogio.agora += timedelta(seconds=30)
    sincronizar.executar()
    assert fonte.consultas == 2

    fonte.fora = False
    relogio.agora += timedelta(seconds=31)
    assert sincronizar.executar() == 1
    assert fonte.consultas == 3


def test_espera_nao_vale_quando_nao_ha_inventario_local() -> None:
    fonte, _, _, sincronizar = _cenario()
    fonte.fora = True
    with pytest.raises(FonteIndisponivel):
        sincronizar.executar()
    with pytest.raises(FonteIndisponivel):
        sincronizar.executar()
    assert fonte.consultas == 2
