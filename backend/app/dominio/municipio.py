"""Município de uma estação, como value object (docs/decisoes.md).

O município é identificado pela UF e pelo nome, comparado sem acentos, sem diferença
entre maiúsculas e minúsculas e sem espaços repetidos: "São Paulo/SP" e "sao  paulo/sp"
são o mesmo município. A grafia original fica guardada em `nome` para exibição.

Ainda não é uma entidade com identidade própria (código IBGE): isso entra quando a
tabela de referência de municípios for sincronizada.
"""

import unicodedata
from dataclasses import dataclass

from app.dominio.erros import DadoInvalido


def normalizar_nome(texto: str) -> str:
    """Forma canônica para comparar nomes: sem acentos, minúsculas e espaços simples.

    "São  Paulo", "sao paulo" e "SÃO PAULO" ficam todos "sao paulo".
    """
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return " ".join(sem_acento.casefold().split())


@dataclass(frozen=True, slots=True, eq=False)
class Municipio:
    nome: str
    uf: str

    def __post_init__(self) -> None:
        nome = " ".join(self.nome.split())
        if not nome:
            raise DadoInvalido("nome do município não pode ser vazio")
        uf = self.uf.strip().upper()
        if len(uf) != 2 or not uf.isalpha():
            raise DadoInvalido(f"UF inválida: {self.uf!r}")
        object.__setattr__(self, "nome", nome)
        object.__setattr__(self, "uf", uf)

    @property
    def chave(self) -> tuple[str, str]:
        """O que identifica o município: UF e nome normalizado."""
        return self.uf, normalizar_nome(self.nome)

    def corresponde(self, nome: str, uf: str | None = None) -> bool:
        """Se `nome` (e `uf`, quando informada) digitados se referem a este município."""
        if uf is not None and uf.strip().upper() != self.uf:
            return False
        return normalizar_nome(nome) == self.chave[1]

    def __eq__(self, outro: object) -> bool:
        if not isinstance(outro, Municipio):
            return NotImplemented
        return self.chave == outro.chave

    def __hash__(self) -> int:
        return hash(self.chave)

    def __str__(self) -> str:
        return f"{self.nome}/{self.uf}"
