from datetime import UTC, datetime
import logging

import pytest

from app.aplicacao.coleta import ColetarMedicoes
from app.aplicacao.filtros import FiltroEstacoes
from app.aplicacao.monitoramento import MonitorarEstacoes
from app.aplicacao.portas import FonteDadosHidrologicos
from app.dominio.erros import FonteIndisponivel
from app.dominio.enums import Grandeza, TipoEstacao
from app.dominio.estacao import Estacao
from app.dominio.geografia import Coordenada
from app.dominio.medicao import Medicao, MedicaoChuva
from app.dominio.periodo import Periodo
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
    def __init__(self, falhar_em: set[int] | None = None) -> None:
        self._falhar_em = falhar_em or set()

    def listar_estacoes(self, filtro: FiltroEstacoes) -> list[Estacao]:
        return []

    def buscar_estacao(self, codigo: int) -> Estacao | None:
        return None

    def buscar_medicoes(
        self, codigo: int, periodo: Periodo, alteradas_desde: datetime | None = None
    ) -> list[Medicao]:
        if codigo in self._falhar_em:
            raise FonteIndisponivel("fonte indisponível")
        return [MedicaoChuva(codigo, T0, 10.0)]


def _coletar(
    fonte: FonteDadosHidrologicos,
    estacoes_conhecidas: list[Estacao] | None = None,
    medicoes: MedicaoRepositorioMemoria | None = None,
) -> ColetarMedicoes:
    estacoes = EstacaoRepositorioMemoria()
    estacoes.salvar_varias(estacoes_conhecidas or [estacao()])
    medicoes = medicoes or MedicaoRepositorioMemoria()
    monitorar = MonitorarEstacoes(medicoes, RegraRepositorioMemoria(), AlertaRepositorioMemoria())
    return ColetarMedicoes(fonte, estacoes, medicoes, monitorar, relogio=lambda: T0)


def test_executar_salva_medicoes_quando_fonte_funciona() -> None:
    assert _coletar(FonteStub()).executar(1) == 1


def test_executar_todas_continua_quando_fonte_falha(caplog) -> None:
    segunda = Estacao(2, "E2", TipoEstacao.PLUVIOMETRICA, Coordenada(1, 1), "SP", "Y")
    medicoes = MedicaoRepositorioMemoria()
    coletar = _coletar(FonteStub(falhar_em={1}), [estacao(), segunda], medicoes)

    with caplog.at_level(logging.WARNING):
        assert coletar.executar_todas() == 1

    assert medicoes.serie(2, Grandeza.CHUVA, Periodo(T0, T0)).medicoes
    assert "coleta da estação 1 falhou" in caplog.text


def test_executar_periodo_propaga_falha_da_fonte() -> None:
    coletar = _coletar(FonteStub(falhar_em={1}))

    with pytest.raises(FonteIndisponivel, match="fonte indisponível"):
        coletar.executar_periodo(1, Periodo(T0, T0))
