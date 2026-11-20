from datetime import UTC, datetime

from app.aplicacao.coleta import ColetarMedicoes
from app.aplicacao.monitoramento import MonitorarEstacoes
from app.aplicacao.portas import FonteDadosHidrologicos
from app.dominio.enums import TipoEstacao
from app.dominio.estacao import Estacao
from app.dominio.geografia import Coordenada
from app.dominio.medicao import MedicaoChuva
from app.infra.memoria.repositorios import (
    AlertaRepositorioMemoria,
    EstacaoRepositorioMemoria,
    MedicaoRepositorioMemoria,
    RegraRepositorioMemoria,
)

T0 = datetime(2026, 1, 10, 12, tzinfo=UTC)


def estacao() -> Estacao:
    return Estacao(1, "E", TipoEstacao.PLUVIOMETRICA, Coordenada(0, 0), "SP", "X")


class FonteStub(FonteDadosHidrologicos):
    def __init__(self, falhar: bool = False) -> None:
        self._falhar = falhar

    def listar_estacoes(self, filtro):
        return []

    def buscar_estacao(self, codigo):
        return None

    def buscar_medicoes(self, codigo, periodo, alteradas_desde=None):
        if self._falhar:
            raise RuntimeError("fonte indisponível")
        return [MedicaoChuva(codigo, T0, 10.0)]


def _coletar(fonte: FonteDadosHidrologicos) -> ColetarMedicoes:
    estacoes = EstacaoRepositorioMemoria()
    estacoes.salvar_varias([estacao()])
    medicoes = MedicaoRepositorioMemoria()
    monitorar = MonitorarEstacoes(medicoes, RegraRepositorioMemoria(), AlertaRepositorioMemoria())
    return ColetarMedicoes(fonte, estacoes, medicoes, monitorar, relogio=lambda: T0)


def test_executar_salva_medicoes_quando_fonte_funciona() -> None:
    assert _coletar(FonteStub()).executar(1) == 1


def test_executar_todas_continua_quando_fonte_falha() -> None:
    assert _coletar(FonteStub(falhar=True)).executar(1) == 0
