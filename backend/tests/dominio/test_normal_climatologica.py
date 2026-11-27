import pytest

from app.dominio.erros import DadoInvalido
from app.dominio.geografia import Coordenada
from app.dominio.normal_climatologica import ChuvaMensal, ClassificacaoChuva, NormalClimatologica

MESES = (200.0, None, 0.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0)


def normal(chuva: tuple[float | None, ...] = MESES) -> NormalClimatologica:
    return NormalClimatologica(83781, "SAO PAULO", "SP", Coordenada(-23.5, -46.6), chuva)


def chuva(acumulado: float, mes: int = 1) -> ChuvaMensal:
    return ChuvaMensal(1, 2026, mes, acumulado, 10, normal(), 3.2)


@pytest.mark.parametrize(
    ("percentual", "esperada"),
    [
        (0, ClassificacaoChuva.ABAIXO),
        (79.9, ClassificacaoChuva.ABAIXO),
        (80, ClassificacaoChuva.NORMAL),
        (120, ClassificacaoChuva.NORMAL),
        (120.1, ClassificacaoChuva.ACIMA),
    ],
)
def test_classificacao_pelos_limites_da_issue(percentual, esperada) -> None:
    assert ClassificacaoChuva.de_percentual(percentual) is esperada


def test_rotulos() -> None:
    assert ClassificacaoChuva.ACIMA.rotulo == "Acima do normal"
    assert ClassificacaoChuva.NORMAL.rotulo == "Dentro do normal"
    assert ClassificacaoChuva.ABAIXO.rotulo == "Abaixo do normal"


def test_normal_exige_doze_meses_e_valores_nao_negativos() -> None:
    with pytest.raises(DadoInvalido, match="12 meses"):
        normal((100.0,) * 11)
    with pytest.raises(DadoInvalido, match="negativa"):
        normal((-1.0,) + (100.0,) * 11)


def test_chuva_do_mes() -> None:
    assert normal().chuva_do_mes(1) == 200.0
    assert normal().chuva_do_mes(2) is None
    with pytest.raises(DadoInvalido, match="mês"):
        normal().chuva_do_mes(13)


def test_percentual_e_classificacao() -> None:
    acima = chuva(300.0)
    assert acima.normal_mm == 200.0
    assert acima.percentual == 150.0
    assert acima.classificacao is ClassificacaoChuva.ACIMA
    assert chuva(200.0).classificacao is ClassificacaoChuva.NORMAL
    assert chuva(50.0).classificacao is ClassificacaoChuva.ABAIXO


def test_mes_com_normal_zero() -> None:
    seco = chuva(0.0, mes=3)
    assert seco.percentual is None
    assert seco.classificacao is ClassificacaoChuva.NORMAL
    assert chuva(0.5, mes=3).classificacao is ClassificacaoChuva.ACIMA


def test_chuva_mensal_invalida() -> None:
    with pytest.raises(DadoInvalido, match="negativa"):
        chuva(-1.0)
    with pytest.raises(DadoInvalido, match="não tem normal"):
        chuva(10.0, mes=2)
