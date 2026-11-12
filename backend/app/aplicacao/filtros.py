from dataclasses import dataclass

from app.dominio.enums import TipoEstacao
from app.dominio.estacao import Estacao


@dataclass(frozen=True, slots=True)
class FiltroEstacoes:
    """Critérios de busca de estações (docs/diagramas-de-classe-ana.md, seção 6)."""

    uf: str | None = None
    tipo: TipoEstacao | None = None
    apenas_telemetricas: bool = False

    def aceita(self, estacao: Estacao) -> bool:
        if self.uf is not None and estacao.uf != self.uf.upper():
            return False
        if self.tipo is not None and estacao.tipo is not self.tipo:
            return False
        return not (self.apenas_telemetricas and not estacao.telemetrica)
