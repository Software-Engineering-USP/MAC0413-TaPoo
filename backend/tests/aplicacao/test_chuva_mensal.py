from datetime import UTC, datetime

import pytest

from app.aplicacao.chuva_mensal import CompararChuvaComNormal, periodo_do_mes
from app.aplicacao.coleta import ColetarMedicoes
from app.aplicacao.erros import EstacaoNaoEncontrada, EstacaoSemChuva, NormalNaoEncontrada
from app.aplicacao.monitoramento import MonitorarEstacoes
from app.aplicacao.portas import NormaisClimatologicas
from app.dominio.enums import TipoEstacao
from app.dominio.erros import FonteIndisponivel
from app.dominio.estacao import Estacao
from app.dominio.geografia import Coordenada
from app.dominio.medicao import Medicao, MedicaoChuva
from app.dominio.normal_climatologica import ClassificacaoChuva, NormalClimatologica
from app.dominio.periodo import Periodo
from app.infra.memoria.repositorios import (
    AlertaRepositorioMemoria,
    EstacaoRepositorioMemoria,
    MedicaoRepositorioMemoria,
    RegraRepositorioMemoria,
)
from tests.aplicacao.fakes import FonteStub

# 10/01/2026 12h UTC = 09h em Brasília.
AGORA = datetime(2026, 1, 10, 12, tzinfo=UTC)
PINHEIROS = Estacao(
    1, "Rio Pinheiros", TipoEstacao.PLUVIOMETRICA, Coordenada(-23.56, -46.72), "SP", "São Paulo"
)
SO_NIVEL = Estacao(
    2,
    "Só nível",
    TipoEstacao.FLUVIOMETRICA,
    Coordenada(-23.56, -46.72),
    "SP",
    "São Paulo",
    telemetrica=False,
)
JANEIRO_200 = (200.0,) + (100.0,) * 11
PERTO = NormalClimatologica(83781, "SAO PAULO", "SP", Coordenada(-23.50, -46.62), JANEIRO_200)
LONGE_SEM_JANEIRO = NormalClimatologica(
    1, "LONGE", "RJ", Coordenada(-22.9, -43.2), (None,) + (100.0,) * 11
)
MAIS_PERTO_SEM_JANEIRO = NormalClimatologica(
    2, "VIZINHA", "SP", Coordenada(-23.561, -46.721), (None,) + (100.0,) * 11
)


class Normais(NormaisClimatologicas):
    def __init__(self, normais: list[NormalClimatologica]) -> None:
        self.normais = normais

    def todas(self) -> list[NormalClimatologica]:
        return self.normais


class Fonte(FonteStub):
    def __init__(self, medicoes: list[Medicao], fora: bool = False) -> None:
        super().__init__([PINHEIROS, SO_NIVEL], medicoes)
        self.fora = fora

    def buscar_medicoes(self, codigo, periodo, alteradas_desde=None):
        if self.fora:
            raise FonteIndisponivel("ANA fora")
        return super().buscar_medicoes(codigo, periodo, alteradas_desde)


def _servico(
    fonte: Fonte,
    normais: list[NormalClimatologica] | None = None,
    salvas: list[Medicao] | None = None,
) -> CompararChuvaComNormal:
    estacoes, medicoes = EstacaoRepositorioMemoria(), MedicaoRepositorioMemoria()
    estacoes.salvar_varias([PINHEIROS, SO_NIVEL])
    medicoes.salvar_varias(salvas or [])
    monitorar = MonitorarEstacoes(medicoes, RegraRepositorioMemoria(), AlertaRepositorioMemoria())
    coletar = ColetarMedicoes(fonte, estacoes, medicoes, monitorar, relogio=lambda: AGORA)
    return CompararChuvaComNormal(
        estacoes,
        medicoes,
        Normais(normais if normais is not None else [PERTO, LONGE_SEM_JANEIRO]),
        coletar,
        relogio=lambda: AGORA,
    )


def chuva(quando: datetime, mm: float) -> MedicaoChuva:
    return MedicaoChuva(1, quando, mm)


def test_periodo_do_mes_comeca_a_meia_noite_de_brasilia() -> None:
    assert periodo_do_mes(AGORA) == Periodo(datetime(2026, 1, 1, 3, tzinfo=UTC), AGORA)
    # 1º/02 01h UTC ainda é 31/01 em Brasília.
    virada = datetime(2026, 2, 1, 1, tzinfo=UTC)
    assert periodo_do_mes(virada).inicio == datetime(2026, 1, 1, 3, tzinfo=UTC)
    primeiro_instante = datetime(2026, 1, 1, 3, tzinfo=UTC)
    assert periodo_do_mes(primeiro_instante).duracao().total_seconds() == 1


def test_soma_so_a_chuva_do_mes_e_compara_com_a_normal() -> None:
    fonte = Fonte(
        [
            chuva(datetime(2026, 1, 2, 12, tzinfo=UTC), 120.0),
            chuva(datetime(2026, 1, 9, 12, tzinfo=UTC), 180.0),
            # 31/12 23h em Brasília: ainda é dezembro, fica fora.
            chuva(datetime(2026, 1, 1, 2, tzinfo=UTC), 50.0),
        ]
    )
    resultado = _servico(fonte).executar(1)

    assert (resultado.ano, resultado.mes) == (2026, 1)
    assert resultado.acumulado_mm == 300.0
    assert resultado.medicoes == 2
    assert resultado.referencia is PERTO
    assert resultado.normal_mm == 200.0
    assert resultado.percentual == 150.0
    assert resultado.classificacao is ClassificacaoChuva.ACIMA
    assert resultado.distancia_km == pytest.approx(
        PINHEIROS.coordenada.distancia_km(PERTO.coordenada)
    )


def test_referencia_ignora_estacao_sem_normal_do_mes() -> None:
    servico = _servico(Fonte([]), [MAIS_PERTO_SEM_JANEIRO, PERTO])
    assert servico.executar(1).referencia is PERTO


def test_sem_normal_para_o_mes() -> None:
    servico = _servico(Fonte([]), [LONGE_SEM_JANEIRO])
    with pytest.raises(NormalNaoEncontrada, match="mês 1"):
        servico.executar(1)


def test_fonte_fora_usa_medicoes_ja_salvas(caplog) -> None:
    resultado = _servico(
        Fonte([], fora=True), salvas=[chuva(datetime(2026, 1, 5, tzinfo=UTC), 40.0)]
    ).executar(1)
    assert resultado.acumulado_mm == 40.0
    assert resultado.classificacao is ClassificacaoChuva.ABAIXO
    assert resultado.atualizado is False
    assert "sem atualizar" in caplog.text


def test_fonte_fora_sem_medicoes_nao_classifica_como_abaixo() -> None:
    resultado = _servico(Fonte([], fora=True)).executar(1)

    assert resultado.medicoes == 0
    assert resultado.percentual is None
    assert resultado.classificacao is ClassificacaoChuva.SEM_DADOS
    assert resultado.atualizado is False


def test_mes_sem_medicoes_tem_classificacao_sem_dados() -> None:
    resultado = _servico(Fonte([])).executar(1)

    assert resultado.medicoes == 0
    assert resultado.percentual is None
    assert resultado.classificacao is ClassificacaoChuva.SEM_DADOS
    assert resultado.atualizado is True


def test_estacao_inexistente_ou_sem_chuva() -> None:
    servico = _servico(Fonte([]))
    with pytest.raises(EstacaoNaoEncontrada):
        servico.executar(99)
    with pytest.raises(EstacaoSemChuva, match="não mede chuva"):
        servico.executar(2)
