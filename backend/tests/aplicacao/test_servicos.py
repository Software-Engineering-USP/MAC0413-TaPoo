from datetime import UTC, datetime, timedelta

import pytest

from app.aplicacao.coleta import ColetarMedicoes
from app.aplicacao.consulta import ConsultarDados
from app.aplicacao.erros import EstacaoNaoEncontrada
from app.aplicacao.filtros import FiltroEstacoes
from app.aplicacao.monitoramento import MonitorarEstacoes
from app.aplicacao.sincronizacao import SincronizarEstacoes
from app.dominio.alerta import RegraCotaReferencia
from app.dominio.enums import Grandeza, Severidade, StatusAlerta, TipoEstacao
from app.dominio.estacao import Estacao
from app.dominio.geografia import Coordenada
from app.dominio.medicao import MedicaoNivel
from app.dominio.periodo import Periodo
from tests.aplicacao.fakes import Alertas, Estacoes, FonteStub, Medicoes, Regras

AGORA = datetime(2026, 1, 10, 12, tzinfo=UTC)

SAO_PAULO = Estacao(
    1, "Rio Tietê - SP", TipoEstacao.FLUVIOMETRICA, Coordenada(-23.55, -46.63), "SP", "São Paulo"
)
CAMPINAS = Estacao(
    2, "Campinas", TipoEstacao.PLUVIOMETRICA, Coordenada(-22.90, -47.06), "SP", "Campinas"
)
BH = Estacao(
    3,
    "Belo Horizonte",
    TipoEstacao.PLUVIOMETRICA,
    Coordenada(-19.92, -43.94),
    "MG",
    "Belo Horizonte",
    telemetrica=False,
)


def niveis(*valores: float) -> list[MedicaoNivel]:
    n = len(valores)
    return [MedicaoNivel(1, AGORA - timedelta(hours=n - 1 - i), v) for i, v in enumerate(valores)]


class Cenario:
    def __init__(self, medicoes_fonte: list) -> None:
        self.fonte = FonteStub([SAO_PAULO, CAMPINAS, BH], medicoes_fonte)
        self.estacoes = Estacoes()
        self.medicoes = Medicoes()
        self.alertas = Alertas()
        self.regras = Regras([RegraCotaReferencia(1, 300, 400, 500)])
        self.relogio = lambda: AGORA
        self.monitorar = MonitorarEstacoes(
            self.medicoes, self.regras, self.alertas, relogio=lambda: self.relogio()
        )
        self.coletar = ColetarMedicoes(
            self.fonte,
            self.estacoes,
            self.medicoes,
            self.monitorar,
            relogio=lambda: self.relogio(),
        )
        self.consulta = ConsultarDados(self.estacoes, self.medicoes, self.alertas)
        SincronizarEstacoes(self.fonte, self.estacoes).executar()


def test_sincronizar_respeita_filtro() -> None:
    fonte = FonteStub([SAO_PAULO, CAMPINAS, BH], [])
    estacoes = Estacoes()
    assert SincronizarEstacoes(fonte, estacoes).executar(FiltroEstacoes(uf="mg")) == 1
    assert list(estacoes.dados) == [3]


def test_coleta_inicial_e_incremental() -> None:
    c = Cenario(niveis(100, 200, 250))
    assert c.coletar.executar(1) == 3
    _, periodo, desde = c.fonte.chamadas[0]
    assert desde is None
    assert periodo.duracao() == timedelta(days=2)

    c.relogio = lambda: AGORA + timedelta(hours=1)
    c.coletar.executar(1)
    _, periodo, desde = c.fonte.chamadas[1]
    assert desde == AGORA
    assert periodo.inicio == AGORA


def test_coleta_de_estacao_inexistente() -> None:
    with pytest.raises(EstacaoNaoEncontrada):
        Cenario([]).coletar.executar(999)


def test_coletar_todas_ignora_estacoes_nao_telemetricas() -> None:
    c = Cenario(niveis(100))
    c.coletar.executar_todas()
    assert {codigo for codigo, _, _ in c.fonte.chamadas} == {1, 2}


def test_coleta_dispara_monitoramento_e_gera_alerta() -> None:
    c = Cenario(niveis(300, 420))
    c.coletar.executar(1)
    [alerta] = c.consulta.alertas_ativos()
    assert alerta.codigo_estacao == 1
    assert alerta.severidade is Severidade.ALERTA


def test_monitoramento_encerra_alerta_quando_nivel_baixa() -> None:
    c = Cenario(niveis(420))
    c.coletar.executar(1)
    [alerta] = c.alertas.ativos()

    c.medicoes.salvar_varias([MedicaoNivel(1, AGORA + timedelta(minutes=30), 100)])
    c.relogio = lambda: AGORA + timedelta(hours=1)
    c.monitorar.executar(1)
    assert alerta.status is StatusAlerta.ENCERRADO
    assert c.consulta.alertas_ativos() == []


def test_monitoramento_sem_regras_nao_faz_nada() -> None:
    c = Cenario([])
    assert c.monitorar.executar(2) is None


def test_consulta_estacao_inexistente() -> None:
    with pytest.raises(EstacaoNaoEncontrada):
        Cenario([]).consulta.estacao(999)


def test_estacoes_proximas_ordenadas_por_distancia() -> None:
    c = Cenario([])
    resultado = c.consulta.estacoes_proximas(Coordenada(-23.0, -47.0), raio_km=150)
    assert [e.codigo for e, _ in resultado] == [2, 1]
    assert resultado[0][1] < resultado[1][1]


def test_consulta_serie() -> None:
    c = Cenario(niveis(1, 2, 3))
    c.coletar.executar(1)
    serie = c.consulta.serie(1, Grandeza.NIVEL, Periodo.ultimos(timedelta(hours=1), ate=AGORA))
    assert [m.valor for m in serie.medicoes] == [2, 3]
