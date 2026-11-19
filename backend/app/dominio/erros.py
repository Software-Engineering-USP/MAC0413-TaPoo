"""Exceções do domínio.

`DadoInvalido` também é `ValueError`, para que código que já trata erros de valor
(parsers, validação de entrada) continue funcionando. `FonteIndisponivel` é o erro
que toda implementação de `FonteDadosHidrologicos` lança quando a origem externa
falha; a API o traduz sem precisar conhecer a fonte concreta.
"""


class ErroDominio(Exception):
    """Base das exceções do domínio."""


class DadoInvalido(ErroDominio, ValueError):
    """Valor que viola uma invariante do domínio (chuva negativa, período invertido...)."""


class FonteIndisponivel(ErroDominio):
    """A fonte externa de dados hidrológicos falhou ou respondeu algo inutilizável."""
