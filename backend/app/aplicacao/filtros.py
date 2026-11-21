import unicodedata
from dataclasses import dataclass

from app.dominio.enums import TipoEstacao
from app.dominio.estacao import Estacao


def normalizar_nome(texto: str) -> str:
    """Forma canônica para comparar nomes: sem acentos, minúsculas e espaços simples.

    "São  Paulo", "sao paulo" e "SÃO PAULO" ficam todos "sao paulo".
    """
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return " ".join(sem_acento.casefold().split())


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
        if not self._aceita_municipio(estacao.municipio):
            return False
        if not self._aceita_texto(estacao):
            return False
        return not (self.apenas_telemetricas and not estacao.telemetrica)

    def _aceita_municipio(self, municipio: str) -> bool:
        return self.municipio is None or normalizar_nome(municipio) == normalizar_nome(
            self.municipio
        )

    def _aceita_texto(self, estacao: Estacao) -> bool:
        if self.texto is None:
            return True
        onde = normalizar_nome(" ".join((estacao.nome, estacao.municipio, estacao.rio or "")))
        return all(palavra in onde for palavra in normalizar_nome(self.texto).split())
