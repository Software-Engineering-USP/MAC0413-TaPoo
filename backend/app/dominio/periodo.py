"""Objeto de valor Periodo (docs/diagramas-de-classe-ana.md, seção 3)."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.dominio.tempo import exigir_utc


@dataclass(frozen=True, slots=True)
class Periodo:
    """Intervalo fechado [inicio, fim] em UTC."""

    inicio: datetime
    fim: datetime

    def __post_init__(self) -> None:
        # frozen=True: usamos object.__setattr__ para normalizar no construtor.
        object.__setattr__(self, "inicio", exigir_utc(self.inicio, "inicio"))
        object.__setattr__(self, "fim", exigir_utc(self.fim, "fim"))
        if self.inicio >= self.fim:
            raise ValueError("inicio precisa ser anterior a fim")

    @classmethod
    def ultimos(cls, duracao: timedelta, ate: datetime) -> "Periodo":
        return cls(ate - duracao, ate)

    def duracao(self) -> timedelta:
        return self.fim - self.inicio

    def contem(self, instante: datetime) -> bool:
        return self.inicio <= instante <= self.fim

    def dividir(self, max_dias: int) -> list["Periodo"]:
        """Fatia o período em pedaços de no máximo `max_dias` (limites 30/366 dias da ANA)."""
        if max_dias <= 0:
            raise ValueError("max_dias precisa ser positivo")
        passo = timedelta(days=max_dias)
        fatias: list[Periodo] = []
        inicio = self.inicio
        while inicio < self.fim:
            fim = min(inicio + passo, self.fim)
            fatias.append(Periodo(inicio, fim))
            inicio = fim
        return fatias
