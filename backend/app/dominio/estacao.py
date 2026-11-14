"""Entidade Estacao (docs/diagramas-de-classe-ana.md, seção 2).

Nesta primeira versão UF, município e rio são guardados como texto simples; as
entidades de referência (UnidadeFederativa, Municipio, Bacia, ...) entram quando a
sincronização das tabelas de referência da ANA for implementada.
"""

from dataclasses import dataclass, field
from datetime import datetime

from app.dominio.enums import Grandeza, TipoEstacao
from app.dominio.geografia import Coordenada
from app.dominio.tempo import agora_utc, exigir_utc

_GRANDEZAS_POR_TIPO: dict[TipoEstacao, frozenset[Grandeza]] = {
    TipoEstacao.PLUVIOMETRICA: frozenset({Grandeza.CHUVA}),
    TipoEstacao.FLUVIOMETRICA: frozenset({Grandeza.NIVEL, Grandeza.VAZAO}),
}


@dataclass(slots=True)
class Estacao:
    codigo: int
    nome: str
    tipo: TipoEstacao
    coordenada: Coordenada
    uf: str
    municipio: str
    rio: str | None = None
    operando: bool = True
    telemetrica: bool = True
    atualizado_em: datetime = field(default_factory=agora_utc)

    def __post_init__(self) -> None:
        if self.codigo <= 0:
            raise ValueError("codigo da estação precisa ser positivo")
        self.uf = self.uf.upper()
        self.atualizado_em = exigir_utc(self.atualizado_em, "atualizado_em")

    def mede(self, grandeza: Grandeza) -> bool:
        """Estações telemétricas da ANA medem chuva junto com nível/vazão."""
        grandezas = _GRANDEZAS_POR_TIPO[self.tipo]
        if self.telemetrica:
            grandezas = grandezas | {Grandeza.CHUVA}
        return grandeza in grandezas
