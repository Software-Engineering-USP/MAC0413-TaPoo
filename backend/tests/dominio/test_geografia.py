import pytest

from app.dominio.geografia import Coordenada


def test_distancia_sao_paulo_rio_aproximadamente_360_km() -> None:
    sao_paulo = Coordenada(-23.5505, -46.6333)
    rio = Coordenada(-22.9068, -43.1729)
    assert sao_paulo.distancia_km(rio) == pytest.approx(361, abs=5)


def test_distancia_para_si_mesma_e_zero() -> None:
    c = Coordenada(-10.0, -50.0)
    assert c.distancia_km(c) == 0


@pytest.mark.parametrize("lat, lon", [(-91, 0), (91, 0), (0, -181), (0, 181)])
def test_coordenada_invalida(lat: float, lon: float) -> None:
    with pytest.raises(ValueError):
        Coordenada(lat, lon)


def test_coordenada_e_imutavel() -> None:
    c = Coordenada(0, 0)
    with pytest.raises(AttributeError):
        c.latitude = 1  # type: ignore[misc]
