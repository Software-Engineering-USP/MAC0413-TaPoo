"""Chuva do mês comparada à normal climatológica (issue #166).

A ANA informa só a chuva medida. Para saber se ela está acima do esperado, o TaPoo
compara o acumulado do mês com a normal de 1991–2020 da estação do INMET mais próxima.
"""

from dataclasses import dataclass
from enum import StrEnum

from app.dominio.erros import DadoInvalido
from app.dominio.geografia import Coordenada

# Faixa "dentro do normal": de 80% a 120% da normal do mês.
LIMITE_ABAIXO_PERCENTUAL = 80.0
LIMITE_ACIMA_PERCENTUAL = 120.0


class ClassificacaoChuva(StrEnum):
    SEM_DADOS = "SEM_DADOS"
    ABAIXO = "ABAIXO"
    NORMAL = "NORMAL"
    ACIMA = "ACIMA"

    @property
    def rotulo(self) -> str:
        return _ROTULOS_CLASSIFICACAO[self]

    @classmethod
    def de_percentual(cls, percentual: float) -> "ClassificacaoChuva":
        if percentual < LIMITE_ABAIXO_PERCENTUAL:
            return cls.ABAIXO
        if percentual > LIMITE_ACIMA_PERCENTUAL:
            return cls.ACIMA
        return cls.NORMAL


_ROTULOS_CLASSIFICACAO = {
    ClassificacaoChuva.SEM_DADOS: "Sem dados",
    ClassificacaoChuva.ABAIXO: "Abaixo do normal",
    ClassificacaoChuva.NORMAL: "Dentro do normal",
    ClassificacaoChuva.ACIMA: "Acima do normal",
}


@dataclass(frozen=True, slots=True)
class NormalClimatologica:
    """Chuva média de cada mês (janeiro a dezembro) em uma estação do INMET.

    Um mês pode não ter normal calculada (`None`), quando a série histórica da estação
    não tinha dados suficientes.
    """

    codigo: int
    nome: str
    uf: str
    coordenada: Coordenada
    chuva_mensal_mm: tuple[float | None, ...]

    def __post_init__(self) -> None:
        if len(self.chuva_mensal_mm) != 12:
            raise DadoInvalido("a normal precisa ter um valor para cada um dos 12 meses")
        if any(valor is not None and valor < 0 for valor in self.chuva_mensal_mm):
            raise DadoInvalido("chuva normal não pode ser negativa")

    def chuva_do_mes(self, mes: int) -> float | None:
        if not 1 <= mes <= 12:
            raise DadoInvalido(f"mês fora do intervalo [1, 12]: {mes}")
        return self.chuva_mensal_mm[mes - 1]


@dataclass(frozen=True, slots=True)
class ChuvaMensal:
    """Acumulado de chuva de uma estação em um mês, comparado à normal de referência."""

    codigo_estacao: int
    ano: int
    mes: int
    acumulado_mm: float
    medicoes: int
    referencia: NormalClimatologica
    distancia_km: float
    atualizado: bool = True

    def __post_init__(self) -> None:
        if self.acumulado_mm < 0:
            raise DadoInvalido("chuva acumulada não pode ser negativa")
        if self.normal_mm is None:
            raise DadoInvalido(f"a estação {self.referencia.codigo} não tem normal do mês")

    @property
    def normal_mm(self) -> float | None:
        return self.referencia.chuva_do_mes(self.mes)

    @property
    def percentual(self) -> float | None:
        """Acumulado em relação à normal, só quando há medições e normal positiva."""
        if self.medicoes == 0:
            return None
        normal = self.normal_mm
        if not normal:
            return None
        return self.acumulado_mm / normal * 100

    @property
    def classificacao(self) -> ClassificacaoChuva:
        if self.medicoes == 0:
            return ClassificacaoChuva.SEM_DADOS
        percentual = self.percentual
        if percentual is None:
            # Mês em que historicamente não chove: qualquer chuva já está acima.
            return ClassificacaoChuva.ACIMA if self.acumulado_mm > 0 else ClassificacaoChuva.NORMAL
        return ClassificacaoChuva.de_percentual(percentual)
