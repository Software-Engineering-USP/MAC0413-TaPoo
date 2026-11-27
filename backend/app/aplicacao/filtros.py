from dataclasses import dataclass

from app.dominio.enums import TipoEstacao
from app.dominio.estacao import Estacao
from app.dominio.municipio import normalizar_nome


@dataclass(frozen=True, slots=True)
class FiltroEstacoes:
    """Critérios de busca de estações (docs/diagramas-de-classe-ana.md, seção 6)."""

    uf: str | None = None
    tipo: TipoEstacao | None = None
    apenas_telemetricas: bool = False
    municipio: str | None = None
    texto: str | None = None
    """Busca livre: cada palavra precisa aparecer no nome, no município ou no rio."""

    def aceita(self, estacao: Estacao) -> bool:
        if self.uf is not None and estacao.uf != self.uf.upper():
            return False
        if self.tipo is not None and estacao.tipo is not self.tipo:
            return False
        if self.municipio is not None and not estacao.municipio.corresponde(self.municipio):
            return False
        if not self._aceita_texto(estacao):
            return False
        return not (self.apenas_telemetricas and not estacao.telemetrica)

    def _aceita_texto(self, estacao: Estacao) -> bool:
        if self.texto is None:
            return True
        palavras = normalizar_nome(self.texto).split()
        if not palavras:
            return False
        onde = normalizar_nome(" ".join((estacao.nome, estacao.municipio.nome, estacao.rio or "")))
        return all(palavra in onde for palavra in palavras)
