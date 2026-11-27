import pytest

from app.dominio.erros import DadoInvalido
from app.dominio.municipio import Municipio, normalizar_nome


def test_normaliza_nome_e_uf_mantendo_a_grafia() -> None:
    municipio = Municipio("  São   Paulo ", " sp")
    assert municipio.nome == "São Paulo"
    assert municipio.uf == "SP"
    assert str(municipio) == "São Paulo/SP"


@pytest.mark.parametrize("nome", ["", "   "])
def test_rejeita_nome_vazio(nome: str) -> None:
    with pytest.raises(DadoInvalido, match="nome"):
        Municipio(nome, "SP")


@pytest.mark.parametrize("uf", ["", "S", "SPX", "1A"])
def test_rejeita_uf_invalida(uf: str) -> None:
    with pytest.raises(DadoInvalido, match="UF"):
        Municipio("São Paulo", uf)


def test_igualdade_ignora_acentos_maiusculas_e_espacos() -> None:
    a, b = Municipio("São Paulo", "SP"), Municipio("SAO  paulo", "sp")
    assert a == b
    assert hash(a) == hash(b)
    assert len({a, b}) == 1


def test_mesmo_nome_em_outra_uf_e_outro_municipio() -> None:
    assert Municipio("Bom Jesus", "PI") != Municipio("Bom Jesus", "RS")


def test_nao_e_igual_a_texto() -> None:
    assert Municipio("Campinas", "SP") != "Campinas"


def test_corresponde_ao_texto_digitado() -> None:
    municipio = Municipio("São Paulo", "SP")
    assert municipio.corresponde("  sao PAULO ")
    assert municipio.corresponde("são paulo", uf="sp")
    assert not municipio.corresponde("são paulo", uf="RJ")
    assert not municipio.corresponde("santos")


def test_imutavel() -> None:
    municipio = Municipio("Campinas", "SP")
    with pytest.raises(AttributeError):
        municipio.nome = "Santos"  # type: ignore[misc]


def test_normalizar_nome() -> None:
    assert normalizar_nome("  SÃO   Paulo ") == "sao paulo"
