import pytest

from app.dominio.erros import DadoInvalido, ErroDominio, FonteIndisponivel
from app.dominio.geografia import Coordenada


def test_hierarquia_de_erros_do_dominio() -> None:
    assert issubclass(DadoInvalido, ErroDominio)
    assert issubclass(FonteIndisponivel, ErroDominio)
    assert not issubclass(FonteIndisponivel, DadoInvalido)


def test_dado_invalido_continua_sendo_value_error() -> None:
    with pytest.raises(ValueError, match="latitude"):
        Coordenada(91, 0)
