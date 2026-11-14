from datetime import UTC, datetime, timedelta

import pytest

from app.dominio.alerta import (
    Alerta,
    AvaliadorAlertas,
    RegraChuvaAcumulada,
    RegraCotaReferencia,
)
from app.dominio.enums import Grandeza, Severidade, StatusAlerta
from app.dominio.medicao import MedicaoChuva, MedicaoNivel, SerieTemporal

T0 = datetime(2026, 1, 1, tzinfo=UTC)
COD = 100


def serie_nivel(*valores: float) -> SerieTemporal:
    return SerieTemporal(
        COD,
        Grandeza.NIVEL,
        [MedicaoNivel(COD, T0 + timedelta(hours=i), v) for i, v in enumerate(valores)],
    )


def serie_chuva(mm_por_hora: float, horas: int) -> SerieTemporal:
    return SerieTemporal(
        COD,
        Grandeza.CHUVA,
        [MedicaoChuva(COD, T0 + timedelta(hours=i), mm_por_hora) for i in range(horas)],
    )


COTA = RegraCotaReferencia(COD, cota_atencao_cm=300, cota_alerta_cm=400, cota_inundacao_cm=500)
CHUVA = RegraChuvaAcumulada(COD, timedelta(hours=24), 30, 50, 80)


@pytest.mark.parametrize(
    "nivel, esperado",
    [
        (299, Severidade.NORMAL),
        (300, Severidade.ATENCAO),
        (450, Severidade.ALERTA),
        (500, Severidade.EMERGENCIA),
    ],
)
def test_regra_cota_usa_ultima_leitura(nivel: float, esperado: Severidade) -> None:
    assert COTA.avaliar(serie_nivel(600, nivel)) is esperado


@pytest.mark.parametrize(
    "mm_h, esperado",
    [
        (1, Severidade.NORMAL),
        (1.5, Severidade.ATENCAO),
        (3, Severidade.ALERTA),
        (4, Severidade.EMERGENCIA),
    ],
)
def test_regra_chuva_acumulada(mm_h: float, esperado: Severidade) -> None:
    assert CHUVA.avaliar(serie_chuva(mm_h, 24)) is esperado


def test_regra_rejeita_limites_fora_de_ordem() -> None:
    with pytest.raises(ValueError):
        RegraCotaReferencia(COD, 500, 400, 300)


def test_regra_rejeita_serie_de_outra_grandeza() -> None:
    with pytest.raises(ValueError):
        COTA.avaliar(serie_chuva(1, 1))


def test_alerta_nao_pode_ser_normal() -> None:
    with pytest.raises(ValueError):
        Alerta(COD, Severidade.NORMAL, "x", T0)


def test_alerta_escalar_e_encerrar() -> None:
    alerta = Alerta(COD, Severidade.ATENCAO, "x", T0)
    with pytest.raises(ValueError):
        alerta.escalar(Severidade.ATENCAO, "y")
    alerta.escalar(Severidade.ALERTA, "y")
    assert alerta.severidade is Severidade.ALERTA
    alerta.encerrar(T0 + timedelta(hours=1))
    assert alerta.status is StatusAlerta.ENCERRADO
    with pytest.raises(ValueError):
        alerta.escalar(Severidade.EMERGENCIA, "z")
    with pytest.raises(ValueError):
        alerta.encerrar(T0 + timedelta(hours=2))


def test_avaliador_cria_alerta_com_pior_severidade() -> None:
    avaliador = AvaliadorAlertas([COTA, CHUVA])
    series = {Grandeza.NIVEL: serie_nivel(320), Grandeza.CHUVA: serie_chuva(3, 24)}
    alerta = avaliador.avaliar(series, None, T0)
    assert alerta is not None
    assert alerta.severidade is Severidade.ALERTA
    assert "Chuva acumulada" in alerta.mensagem
    assert alerta.medicao_gatilho.grandeza() is Grandeza.CHUVA


def test_avaliador_sem_alerta_quando_normal() -> None:
    assert AvaliadorAlertas([COTA]).avaliar({Grandeza.NIVEL: serie_nivel(100)}, None, T0) is None


def test_avaliador_escala_mas_nao_rebaixa() -> None:
    avaliador = AvaliadorAlertas([COTA])
    ativo = Alerta(COD, Severidade.ALERTA, "x", T0)
    assert avaliador.avaliar({Grandeza.NIVEL: serie_nivel(350)}, ativo, T0) is None
    assert ativo.severidade is Severidade.ALERTA
    resultado = avaliador.avaliar({Grandeza.NIVEL: serie_nivel(550)}, ativo, T0)
    assert resultado is ativo
    assert ativo.severidade is Severidade.EMERGENCIA


def test_avaliador_encerra_quando_normaliza() -> None:
    ativo = Alerta(COD, Severidade.ALERTA, "x", T0)
    fim = T0 + timedelta(hours=3)
    resultado = AvaliadorAlertas([COTA]).avaliar({Grandeza.NIVEL: serie_nivel(100)}, ativo, fim)
    assert resultado is ativo
    assert ativo.status is StatusAlerta.ENCERRADO
    assert ativo.encerrado_em == fim


def test_avaliador_ignora_regras_inativas() -> None:
    inativa = RegraCotaReferencia(COD, 1, 2, 3, ativa=False)
    assert AvaliadorAlertas([inativa]).avaliar({Grandeza.NIVEL: serie_nivel(10)}, None, T0) is None
