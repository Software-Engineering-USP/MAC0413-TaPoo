"""Situação atual de estações e municípios: o que o mapa e a página do município mostram.

A situação de uma estação é a severidade do seu alerta ativo (ou NORMAL, sem alerta).
A de um município é a pior situação entre as suas estações.
"""

from dataclasses import dataclass

from app.dominio.alerta import Alerta
from app.dominio.enums import Severidade
from app.dominio.estacao import Estacao


@dataclass(frozen=True, slots=True)
class SituacaoEstacao:
    estacao: Estacao
    alerta: Alerta | None = None

    def __post_init__(self) -> None:
        if self.alerta is None:
            return
        if self.alerta.codigo_estacao != self.estacao.codigo:
            raise ValueError("alerta pertence a outra estação")
        if not self.alerta.ativo:
            raise ValueError("situação atual só considera alertas ativos")

    @property
    def severidade(self) -> Severidade:
        return self.alerta.severidade if self.alerta is not None else Severidade.NORMAL


@dataclass(frozen=True, slots=True)
class SituacaoMunicipio:
    uf: str
    municipio: str
    estacoes: tuple[SituacaoEstacao, ...]

    def __post_init__(self) -> None:
        if not self.estacoes:
            raise ValueError("município sem estações não tem situação")
        # Da mais grave para a menos grave; empate pelo código, para ordem estável.
        ordenadas = sorted(self.estacoes, key=lambda s: (-s.severidade.nivel, s.estacao.codigo))
        object.__setattr__(self, "estacoes", tuple(ordenadas))

    @property
    def severidade(self) -> Severidade:
        return self.estacoes[0].severidade

    @property
    def alertas(self) -> list[Alerta]:
        return [s.alerta for s in self.estacoes if s.alerta is not None]
