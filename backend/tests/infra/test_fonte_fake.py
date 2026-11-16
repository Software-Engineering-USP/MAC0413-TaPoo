from datetime import UTC, datetime, timedelta

from app.aplicacao.coleta import ColetarMedicoes
from app.aplicacao.filtros import FiltroEstacoes
from app.aplicacao.monitoramento import MonitorarEstacoes
from app.aplicacao.sincronizacao import SincronizarEstacoes
from app.dominio.enums import Severidade
from app.dominio.periodo import Periodo
from app.infra.fontes.fake import FonteFake, regras_de_exemplo
from app.infra.memoria.repositorios import (
    AlertaRepositorioMemoria,
    EstacaoRepositorioMemoria,
    MedicaoRepositorioMemoria,
    RegraRepositorioMemoria,
)

AGORA = datetime(2026, 1, 10, 12, 34, tzinfo=UTC)


def test_medicoes_horarias_e_incrementais() -> None:
    fonte = FonteFake(AGORA)
    periodo = Periodo.ultimos(timedelta(hours=3), ate=AGORA)
    todas = fonte.buscar_medicoes(90000002, periodo)
    assert len(todas) == 3  # 10h, 11h, 12h (só chuva)
    novas = fonte.buscar_medicoes(90000002, periodo, alteradas_desde=todas[1].data_hora_utc)
    assert [m.data_hora_utc.hour for m in novas] == [12]


def test_estacao_desconhecida_sem_medicoes() -> None:
    periodo = Periodo.ultimos(timedelta(hours=3), ate=AGORA)
    assert FonteFake(AGORA).buscar_medicoes(1, periodo) == []


def test_cenario_de_exemplo_gera_alertas_esperados() -> None:
    fonte = FonteFake(AGORA)
    estacoes, medicoes = EstacaoRepositorioMemoria(), MedicaoRepositorioMemoria()
    alertas = AlertaRepositorioMemoria()
    regras = RegraRepositorioMemoria(regras_de_exemplo())
    relogio = lambda: AGORA
    monitorar = MonitorarEstacoes(medicoes, regras, alertas, relogio=relogio)

    assert SincronizarEstacoes(fonte, estacoes).executar(FiltroEstacoes()) == 5
    ColetarMedicoes(fonte, estacoes, medicoes, monitorar, relogio=relogio).executar_todas()

    severidades = {a.codigo_estacao: a.severidade for a in alertas.ativos()}
    assert severidades == {90000001: Severidade.ALERTA, 90000004: Severidade.EMERGENCIA}
