from datetime import UTC, datetime, timedelta

import pytest

from app.dominio.enums import Grandeza, Severidade, TipoEstacao
from app.dominio.estacao import Estacao
from app.dominio.geografia import Coordenada
from app.dominio.medicao import Medicao, MedicaoChuva, MedicaoNivel, MedicaoVazao, SerieTemporal
from app.dominio.periodo import Periodo

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def chuva(horas: int, valor: float, codigo: int = 1) -> MedicaoChuva:
    return MedicaoChuva(codigo, T0 + timedelta(hours=horas), valor)


def test_medicao_e_abstrata() -> None:
    with pytest.raises(TypeError):
        Medicao(1, T0, 1.0)  # type: ignore[abstract]


@pytest.mark.parametrize(
    "classe, grandeza, unidade",
    [
        (MedicaoChuva, Grandeza.CHUVA, "mm"),
        (MedicaoNivel, Grandeza.NIVEL, "cm"),
        (MedicaoVazao, Grandeza.VAZAO, "m3/s"),
    ],
)
def test_polimorfismo_de_grandeza(classe: type[Medicao], grandeza: Grandeza, unidade: str) -> None:
    m = classe(1, T0, 10.0)
    assert m.grandeza() is grandeza
    assert m.unidade() == unidade


def test_chuva_negativa_e_invalida() -> None:
    with pytest.raises(ValueError):
        chuva(0, -1)


def test_nivel_pode_ser_negativo() -> None:
    assert MedicaoNivel(1, T0, -5).valor == -5


def test_serie_mantem_ordem_cronologica() -> None:
    serie = SerieTemporal(1, Grandeza.CHUVA, [chuva(2, 1), chuva(0, 2)])
    serie.adicionar(chuva(1, 3))
    assert [m.valor for m in serie.medicoes] == [2, 3, 1]
    assert serie.ultimo().valor == 1
    assert serie.maximo().valor == 3


def test_serie_rejeita_outra_grandeza_ou_estacao() -> None:
    serie = SerieTemporal(1, Grandeza.CHUVA)
    with pytest.raises(ValueError):
        serie.adicionar(MedicaoNivel(1, T0, 100))
    with pytest.raises(ValueError):
        serie.adicionar(chuva(0, 1, codigo=2))


def test_serie_vazia() -> None:
    serie = SerieTemporal(1, Grandeza.NIVEL)
    assert serie.ultimo() is None
    assert serie.maximo() is None
    assert serie.acumulado(timedelta(hours=1)) == 0
    assert serie.variacao(timedelta(hours=1)) == 0


def test_acumulado_considera_janela_ate_ultima_medicao() -> None:
    serie = SerieTemporal(1, Grandeza.CHUVA, [chuva(h, 10) for h in range(30)])
    assert serie.acumulado(timedelta(hours=24)) == 240


def test_variacao() -> None:
    niveis = [MedicaoNivel(1, T0 + timedelta(hours=h), 100 + 10 * h) for h in range(5)]
    serie = SerieTemporal(1, Grandeza.NIVEL, niveis)
    assert serie.variacao(timedelta(hours=2, minutes=30)) == 20


def test_no_periodo() -> None:
    serie = SerieTemporal(1, Grandeza.CHUVA, [chuva(h, 1) for h in range(10)])
    recorte = serie.no_periodo(Periodo(T0 + timedelta(hours=2), T0 + timedelta(hours=4)))
    assert len(recorte) == 3


def test_estacao_mede() -> None:
    fluvio = Estacao(1, "Rio X", TipoEstacao.FLUVIOMETRICA, Coordenada(0, 0), "sp", "Y")
    assert fluvio.uf == "SP"
    assert fluvio.mede(Grandeza.NIVEL)
    assert fluvio.mede(Grandeza.CHUVA)  # telemétrica
    fluvio.telemetrica = False
    assert not fluvio.mede(Grandeza.CHUVA)


def test_severidade_ordenada_por_gravidade() -> None:
    assert Severidade.NORMAL < Severidade.ATENCAO < Severidade.ALERTA < Severidade.EMERGENCIA
    assert max(Severidade.ALERTA, Severidade.EMERGENCIA) is Severidade.EMERGENCIA
