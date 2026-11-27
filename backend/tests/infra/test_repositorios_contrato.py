"""Mesmo contrato para os repositórios em memória e SQL (#112).

Cada teste roda contra: memória, SQLite em memória e, se `TEST_DATABASE_URL` estiver
definida (como no CI), um Postgres de verdade.
"""

import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.api.dependencias import Repositorios, criar_repositorios, repositorios_sql
from app.aplicacao.filtros import FiltroEstacoes
from app.dominio.alerta import Alerta, FatorAvaliacao
from app.dominio.enums import (
    Grandeza,
    NivelConsistencia,
    OrigemDado,
    Severidade,
    StatusAlerta,
    TipoEstacao,
)
from app.dominio.estacao import Estacao
from app.dominio.geografia import Coordenada
from app.dominio.medicao import MedicaoChuva, MedicaoNivel
from app.dominio.municipio import Municipio
from app.dominio.periodo import Periodo
from app.infra.persistencia.repositorios_sql import BancoDeDados

T0 = datetime(2026, 1, 1, 12, tzinfo=UTC)
EM_VOLTA_DE_T0 = Periodo(T0 - timedelta(minutes=30), T0 + timedelta(minutes=30))
URL_POSTGRES = os.getenv("TEST_DATABASE_URL")

IMPLEMENTACOES = [
    "memoria",
    "sqlite",
    pytest.param(
        "postgres",
        marks=pytest.mark.skipif(not URL_POSTGRES, reason="TEST_DATABASE_URL não definida"),
    ),
]


@pytest.fixture(params=IMPLEMENTACOES)
def repos(request) -> Iterator[Repositorios]:
    if request.param == "memoria":
        yield criar_repositorios("memoria")
        return
    url = "sqlite://" if request.param == "sqlite" else URL_POSTGRES
    banco = BancoDeDados(url)
    banco.apagar_tabelas()  # cada teste começa com o banco vazio
    yield repositorios_sql(banco)
    banco.apagar_tabelas()
    banco.engine.dispose()


def estacao(codigo: int, uf: str = "SP", municipio: str = "São Paulo", **kw) -> Estacao:
    kw.setdefault("tipo", TipoEstacao.FLUVIOMETRICA)
    tipo = kw.pop("tipo")
    return Estacao(
        codigo, f"Estação {codigo}", tipo, Coordenada(-23.5, -46.6), Municipio(municipio, uf), **kw
    )


# --- Estações ---------------------------------------------------------------------


def test_estacao_ida_e_volta(repos: Repositorios) -> None:
    original = estacao(1, rio="Rio Tietê", atualizado_em=T0)
    assert repos.estacoes.salvar_varias([original]) == 1
    assert repos.estacoes.por_codigo(1) == original
    assert repos.estacoes.por_codigo(2) is None


def test_estacao_upsert_pelo_codigo(repos: Repositorios) -> None:
    repos.estacoes.salvar_varias([estacao(1)])
    repos.estacoes.salvar_varias([estacao(1, operando=False)])
    assert repos.estacoes.por_codigo(1).operando is False
    assert len(repos.estacoes.buscar(FiltroEstacoes())) == 1


def test_estacao_repetida_no_mesmo_lote_vale_a_ultima(repos: Repositorios) -> None:
    assert repos.estacoes.salvar_varias([estacao(1), estacao(1, uf="MG")]) == 2
    assert repos.estacoes.por_codigo(1).uf == "MG"


def test_buscar_aplica_todos_os_criterios_do_filtro(repos: Repositorios) -> None:
    repos.estacoes.salvar_varias(
        [
            estacao(3, tipo=TipoEstacao.PLUVIOMETRICA),
            estacao(1, uf="MG", municipio="Belo Horizonte", telemetrica=False),
            estacao(2, municipio="Campinas"),
        ]
    )

    def codigos(**filtro) -> list[int]:
        return [e.codigo for e in repos.estacoes.buscar(FiltroEstacoes(**filtro))]

    assert codigos() == [1, 2, 3]
    assert codigos(uf="sp") == [2, 3]
    assert codigos(tipo=TipoEstacao.PLUVIOMETRICA) == [3]
    assert codigos(apenas_telemetricas=True) == [2, 3]
    assert codigos(municipio="SAO PAULO") == [3]


def test_monitoradas_sao_telemetricas_e_operando(repos: Repositorios) -> None:
    repos.estacoes.salvar_varias(
        [estacao(3), estacao(1, telemetrica=False), estacao(2, operando=False)]
    )
    assert [e.codigo for e in repos.estacoes.monitoradas()] == [3]


# --- Medições ---------------------------------------------------------------------


def test_medicao_ida_e_volta_com_todos_os_campos(repos: Repositorios) -> None:
    repos.estacoes.salvar_varias([estacao(1)])
    original = MedicaoNivel(
        1,
        T0,
        321.5,
        origem=OrigemDado.TELEMETRICA,
        consistencia=NivelConsistencia.CONSISTIDO,
        status_fonte="1",
        atualizado_na_fonte_em=T0 + timedelta(minutes=5),
    )
    repos.medicoes.salvar_varias([original])
    [lida] = repos.medicoes.serie(1, Grandeza.NIVEL, EM_VOLTA_DE_T0).medicoes
    assert lida == original
    assert type(lida) is MedicaoNivel


def test_medicao_upsert_pela_chave_natural(repos: Repositorios) -> None:
    repos.estacoes.salvar_varias([estacao(1)])
    repos.medicoes.salvar_varias([MedicaoChuva(1, T0, 1.0)])
    repos.medicoes.salvar_varias([MedicaoChuva(1, T0, 2.0)])  # dado corrigido na fonte
    repos.medicoes.salvar_varias([MedicaoChuva(1, T0, 5.0, origem=OrigemDado.CONVENCIONAL)])

    serie = repos.medicoes.serie(1, Grandeza.CHUVA, EM_VOLTA_DE_T0)
    assert sorted((m.origem, m.valor) for m in serie.medicoes) == [
        (OrigemDado.CONVENCIONAL, 5.0),
        (OrigemDado.TELEMETRICA, 2.0),
    ]


def test_serie_filtra_estacao_grandeza_e_periodo_com_limites_inclusivos(
    repos: Repositorios,
) -> None:
    repos.estacoes.salvar_varias([estacao(1), estacao(2)])
    horas = [T0 + timedelta(hours=h) for h in range(5)]
    repos.medicoes.salvar_varias(
        [MedicaoNivel(1, h, float(i)) for i, h in enumerate(reversed(horas))]
        + [MedicaoChuva(1, horas[2], 9.0), MedicaoNivel(2, horas[2], 9.0)]
    )

    serie = repos.medicoes.serie(1, Grandeza.NIVEL, Periodo(horas[1], horas[3]))

    assert [m.data_hora_utc for m in serie.medicoes] == horas[1:4]  # ordenada
    assert serie.codigo_estacao == 1
    assert serie.grandeza is Grandeza.NIVEL


def test_datas_voltam_em_utc_mesmo_gravadas_em_outro_fuso(repos: Repositorios) -> None:
    repos.estacoes.salvar_varias([estacao(1)])
    brasilia = timezone(timedelta(hours=-3))
    repos.medicoes.salvar_varias([MedicaoNivel(1, datetime(2026, 1, 1, 9, tzinfo=brasilia), 1)])

    [lida] = repos.medicoes.serie(1, Grandeza.NIVEL, EM_VOLTA_DE_T0).medicoes
    assert lida.data_hora_utc == T0
    assert lida.data_hora_utc.tzinfo is UTC


def test_ultima_atualizacao_prefere_a_data_da_fonte(repos: Repositorios) -> None:
    repos.estacoes.salvar_varias([estacao(1), estacao(2)])
    assert repos.medicoes.ultima_atualizacao(1) is None

    repos.medicoes.salvar_varias(
        [
            MedicaoNivel(1, T0, 1),
            MedicaoNivel(1, T0 - timedelta(days=1), 1, atualizado_na_fonte_em=T0 + timedelta(1)),
            MedicaoNivel(2, T0 + timedelta(days=5), 1),
        ]
    )
    ultima = repos.medicoes.ultima_atualizacao(1)
    assert ultima == T0 + timedelta(days=1)
    assert ultima.tzinfo is not None


def test_salvar_muitas_medicoes_de_uma_vez(repos: Repositorios) -> None:
    repos.estacoes.salvar_varias([estacao(1)])
    medicoes = [MedicaoChuva(1, T0 + timedelta(minutes=15 * i), 0.2) for i in range(1200)]
    assert repos.medicoes.salvar_varias(medicoes) == 1200
    periodo = Periodo(T0, T0 + timedelta(days=30))
    assert len(repos.medicoes.serie(1, Grandeza.CHUVA, periodo)) == 1200


# --- Alertas ----------------------------------------------------------------------


def test_alerta_ida_e_volta_com_medicao_gatilho(repos: Repositorios) -> None:
    repos.estacoes.salvar_varias([estacao(1)])
    gatilho = MedicaoNivel(1, T0, 420)
    repos.medicoes.salvar_varias([gatilho])
    alerta = Alerta(1, Severidade.ALERTA, "Rio acima da cota", T0, medicao_gatilho=gatilho)

    repos.alertas.salvar(alerta)

    lido = repos.alertas.ativo_da_estacao(1)
    assert lido.id == alerta.id
    assert (lido.severidade, lido.mensagem, lido.emitido_em) == (
        Severidade.ALERTA,
        "Rio acima da cota",
        T0,
    )
    assert lido.medicao_gatilho == gatilho


def test_alerta_ida_e_volta_com_fatores_em_ordem(repos: Repositorios) -> None:
    repos.estacoes.salvar_varias([estacao(1), estacao(2)])
    nivel = MedicaoNivel(1, T0, 420)
    chuva = MedicaoChuva(2, T0, 80)
    repos.medicoes.salvar_varias([nivel, chuva])
    fatores = (
        FatorAvaliacao("Nível acima da cota", Severidade.EMERGENCIA, 1, nivel),
        FatorAvaliacao("Chuva forte a montante", Severidade.ALERTA, 2, chuva),
        FatorAvaliacao("Sem medição", Severidade.ATENCAO, 1, None),
    )
    alerta = Alerta(1, Severidade.EMERGENCIA, "x", T0, medicao_gatilho=nivel, fatores=fatores)
    repos.alertas.salvar(alerta)

    lido = repos.alertas.ativo_da_estacao(1)
    assert lido.fatores == fatores
    # A mesma avaliação, aplicada ao alerta lido de volta, não conta como mudança.
    assert lido.atualizar_motivos("x", nivel, fatores) is False


def test_alerta_regravado_troca_os_fatores(repos: Repositorios) -> None:
    repos.estacoes.salvar_varias([estacao(1)])
    antes = (
        FatorAvaliacao("a", Severidade.ALERTA, 1, None),
        FatorAvaliacao("b", Severidade.ATENCAO, 1, None),
    )
    alerta = Alerta(1, Severidade.ALERTA, "a; b", T0, fatores=antes)
    repos.alertas.salvar(alerta)

    depois = (FatorAvaliacao("c", Severidade.EMERGENCIA, 1, None),)
    alerta.escalar(Severidade.EMERGENCIA, "c", None, depois)
    repos.alertas.salvar(alerta)
    assert repos.alertas.ativo_da_estacao(1).fatores == depois

    alerta.atualizar_motivos("c", None, ())
    repos.alertas.salvar(alerta)
    assert repos.alertas.ativo_da_estacao(1).fatores == ()


def test_alerta_alterado_e_encerrado_e_regravado(repos: Repositorios) -> None:
    repos.estacoes.salvar_varias([estacao(1), estacao(2)])
    alerta = Alerta(1, Severidade.ATENCAO, "subindo", T0)
    outro = Alerta(2, Severidade.ALERTA, "outra estação", T0)
    repos.alertas.salvar(alerta)
    repos.alertas.salvar(outro)

    lido = repos.alertas.ativo_da_estacao(1)
    lido.escalar(Severidade.EMERGENCIA, "muito acima", None, ())
    repos.alertas.salvar(lido)
    assert repos.alertas.ativo_da_estacao(1).severidade is Severidade.EMERGENCIA

    lido.encerrar(T0 + timedelta(hours=3))
    repos.alertas.salvar(lido)
    assert repos.alertas.ativo_da_estacao(1) is None
    assert [a.id for a in repos.alertas.ativos()] == [outro.id]


def test_historico_de_alertas_guarda_os_encerrados() -> None:
    """Só para SQL: o histórico em memória chega com o #152."""
    banco = BancoDeDados("sqlite://")
    repos = repositorios_sql(banco)
    repos.estacoes.salvar_varias([estacao(1), estacao(2)])
    antigo = Alerta(1, Severidade.ALERTA, "antigo", T0)
    antigo.encerrar(T0 + timedelta(hours=1))
    recente = Alerta(1, Severidade.ATENCAO, "recente", T0 + timedelta(hours=2))
    for alerta in (antigo, recente, Alerta(2, Severidade.ALERTA, "outra", T0)):
        repos.alertas.salvar(alerta)

    historico = repos.alertas.historico_da_estacao(1)
    assert [(a.mensagem, a.status) for a in historico] == [
        ("recente", StatusAlerta.ATIVO),
        ("antigo", StatusAlerta.ENCERRADO),
    ]
    assert [a.mensagem for a in repos.alertas.historico_da_estacao(1, limite=1)] == ["recente"]
    banco.engine.dispose()
