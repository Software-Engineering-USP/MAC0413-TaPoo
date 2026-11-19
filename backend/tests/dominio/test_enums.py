import pytest

from app.dominio.enums import Grandeza, Severidade


@pytest.mark.parametrize(
    "severidade, rotulo",
    [
        (Severidade.NORMAL, "Normal"),
        (Severidade.ATENCAO, "Atenção"),
        (Severidade.ALERTA, "Alerta"),
        (Severidade.EMERGENCIA, "Emergência"),
    ],
)
def test_rotulo_da_severidade(severidade: Severidade, rotulo: str) -> None:
    assert severidade.rotulo == rotulo


@pytest.mark.parametrize(
    "grandeza, rotulo",
    [(Grandeza.CHUVA, "Chuva"), (Grandeza.NIVEL, "Nível"), (Grandeza.VAZAO, "Vazão")],
)
def test_rotulo_da_grandeza(grandeza: Grandeza, rotulo: str) -> None:
    assert grandeza.rotulo == rotulo


def test_rotulo_nao_altera_o_valor_serializado() -> None:
    assert Severidade.ATENCAO == "ATENCAO"
    assert str(Grandeza.NIVEL) == "NIVEL"
