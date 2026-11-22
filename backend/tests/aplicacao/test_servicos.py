from datetime import UTC, datetime, timedelta

import pytest

from app.aplicacao.coleta import ColetarMedicoes
from app.aplicacao.consulta import ConsultarDados
from app.aplicacao.erros import EstacaoNaoEncontrada, MunicipioNaoEncontrado
from app.aplicacao.filtros import FiltroEstacoes
from app.aplicacao.monitoramento import MonitorarEstacoes
from app.aplicacao.sincronizacao import SincronizarEstacoes
from app.dominio.alerta import RegraChuvaAcumulada, RegraCotaReferencia
from app.dominio.enums import Grandeza, Severidade, StatusAlerta, TipoEstacao
from app.dominio.estacao import Estacao
from app.dominio.geografia import Coordenada
from app.dominio.medicao import MedicaoChuva, MedicaoNivel
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
    coletar = Cenario([]).coletar
    with pytest.raises(EstacaoNaoEncontrada):
        coletar.executar(999)


def test_coleta_sob_demanda_para_periodo() -> None:
    c = Cenario(niveis(100, 200, 250))
    periodo = Periodo(AGORA - timedelta(hours=2), AGORA)

    assert c.coletar.executar_periodo(1, periodo) == 3
    assert [m.valor for m in c.consulta.serie(1, Grandeza.NIVEL, periodo).medicoes] == [
        100,
        200,
        250,
    ]


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


def test_monitoramento_persiste_mudanca_de_fatores_sem_escalar(monkeypatch) -> None:
    c = Cenario(niveis(450))
    c.coletar.executar(1)
    [alerta] = c.alertas.ativos()
    c.regras.regras.append(RegraChuvaAcumulada(1, timedelta(hours=24), 30, 50, 80))
    c.medicoes.salvar_varias([MedicaoChuva(1, AGORA - timedelta(hours=i), 3) for i in range(24)])
    alertas_salvos = []
    salvar = c.alertas.salvar

    def registrar_salvamento(atualizado) -> None:
        alertas_salvos.append(atualizado)
        salvar(atualizado)

    monkeypatch.setattr(c.alertas, "salvar", registrar_salvamento)
    resultado = c.monitorar.executar(1)

    assert resultado is alerta
    assert alertas_salvos == [alerta]
    assert alerta.severidade is Severidade.ALERTA
    assert len(alerta.fatores) == 2
    assert "Chuva acumulada" in alerta.mensagem


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
    consulta = Cenario([]).consulta
    with pytest.raises(EstacaoNaoEncontrada):
        consulta.estacao(999)


def test_estacoes_proximas_ordenadas_por_distancia() -> None:
    c = Cenario([])
    resultado = c.consulta.estacoes_proximas(Coordenada(-23.0, -47.0), raio_km=150)
    assert [s.estacao.codigo for s, _ in resultado] == [2, 1]
    assert resultado[0][1] < resultado[1][1]


def test_consulta_serie() -> None:
    c = Cenario(niveis(1, 2, 3))
    c.coletar.executar(1)
    serie = c.consulta.serie(1, Grandeza.NIVEL, Periodo.ultimos(timedelta(hours=1), ate=AGORA))
    assert [m.valor for m in serie.medicoes] == [2, 3]


def test_listar_estacoes_traz_situacao_atual() -> None:
    c = Cenario(niveis(300, 420))
    c.coletar.executar(1)
    situacoes = {s.estacao.codigo: s for s in c.consulta.listar_estacoes(FiltroEstacoes())}
    assert situacoes[1].severidade is Severidade.ALERTA
    assert situacoes[1].alerta is not None
    assert situacoes[2].severidade is Severidade.NORMAL
    assert situacoes[2].alerta is None


def test_situacao_estacao() -> None:
    c = Cenario(niveis(520))
    c.coletar.executar(1)
    assert c.consulta.situacao_estacao(1).severidade is Severidade.EMERGENCIA
    with pytest.raises(EstacaoNaoEncontrada):
        c.consulta.situacao_estacao(999)


def test_estacoes_proximas_trazem_situacao() -> None:
    c = Cenario(niveis(420))
    c.coletar.executar(1)
    resultado = c.consulta.estacoes_proximas(Coordenada(-23.0, -47.0), raio_km=150)
    assert [(s.estacao.codigo, s.severidade) for s, _ in resultado] == [
        (2, Severidade.NORMAL),
        (1, Severidade.ALERTA),
    ]


def test_situacao_municipio_ignora_acentos_e_maiusculas() -> None:
    c = Cenario(niveis(420))
    c.coletar.executar(1)
    situacao = c.consulta.situacao_municipio("sp", "  SAO   paulo ")
    assert (situacao.uf, situacao.municipio) == ("SP", "São Paulo")
    assert situacao.severidade is Severidade.ALERTA
    assert [s.estacao.codigo for s in situacao.estacoes] == [1]


def test_situacao_municipio_sem_alerta_e_normal() -> None:
    situacao = Cenario([]).consulta.situacao_municipio("SP", "Campinas")
    assert situacao.severidade is Severidade.NORMAL
    assert situacao.alertas == []


def test_situacao_municipio_exige_uf_correta() -> None:
    consulta = Cenario([]).consulta
    with pytest.raises(MunicipioNaoEncontrado):
        consulta.situacao_municipio("MG", "Campinas")
