"""Ciclo completo do agendador: coleta na fonte → medições salvas → alerta emitido (#114)."""

import time
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.api.dependencias import executar_ciclo, montar_container
from app.dominio.enums import Severidade
from app.infra.fontes.fake import FonteFake
from app.main import create_app

AGORA = datetime(2026, 1, 10, 12, tzinfo=UTC)


class FonteContada(FonteFake):
    """`FonteFake` sem carga inicial, que registra as buscas de medições."""

    carregar_na_inicializacao = False

    def __init__(self, agora: datetime) -> None:
        super().__init__(agora)
        self.buscas: list[tuple[int, datetime | None]] = []

    def buscar_medicoes(self, codigo, periodo, alteradas_desde=None):
        self.buscas.append((codigo, alteradas_desde))
        return super().buscar_medicoes(codigo, periodo, alteradas_desde)


def test_ciclo_coleta_medicoes_e_emite_alertas() -> None:
    relogio = [AGORA]
    fonte = FonteContada(AGORA)
    container = montar_container(fonte, relogio=lambda: relogio[0])
    container.sincronizar.executar()
    assert container.consulta.alertas_ativos() == []

    salvas = executar_ciclo(container)

    assert salvas > 0
    severidades = {a.codigo_estacao: a.severidade for a in container.consulta.alertas_ativos()}
    assert severidades[90000001] >= Severidade.ALERTA  # rio subindo
    assert severidades[90000004] > Severidade.ALERTA  # chuva forte em 24 h
    assert 90000003 not in severidades  # rio estável
    assert 90000005 not in {codigo for codigo, _ in fonte.buscas}  # não telemétrica


def test_segundo_ciclo_busca_so_o_que_mudou() -> None:
    relogio = [AGORA]
    fonte = FonteContada(AGORA)
    container = montar_container(fonte, relogio=lambda: relogio[0])
    container.sincronizar.executar()
    executar_ciclo(container)
    alertas_antes = {a.id for a in container.consulta.alertas_ativos()}

    fonte.buscas.clear()
    relogio[0] = AGORA + timedelta(minutes=15)
    executar_ciclo(container)

    assert fonte.buscas
    assert all(desde == AGORA for _, desde in fonte.buscas)
    assert {a.id for a in container.consulta.alertas_ativos()} == alertas_antes


def test_agendador_no_lifespan_atualiza_os_alertas_da_api() -> None:
    fonte = FonteContada(AGORA)

    def fabrica():
        container = montar_container(fonte, relogio=lambda: AGORA)
        container.sincronizar.executar()  # estações conhecidas, ainda sem medições
        return container

    app = create_app(fabrica, intervalo=lambda: timedelta(milliseconds=10))
    with TestClient(app) as client:
        assert app.state.agendador.rodando
        limite = time.monotonic() + 3
        alertas = []
        while not alertas and time.monotonic() < limite:
            time.sleep(0.02)
            alertas = client.get("/alertas").json()
        assert {a["codigo_estacao"] for a in alertas} >= {90000001, 90000004}
        agendador = app.state.agendador

    assert not agendador.rodando


def test_sem_intervalo_nao_ha_agendador() -> None:
    app = create_app(lambda: montar_container(FonteContada(AGORA)), intervalo=lambda: None)
    with TestClient(app):
        assert app.state.agendador is None
