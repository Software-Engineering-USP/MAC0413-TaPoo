"""Medições e séries temporais (docs/diagramas-de-classe-ana.md, seção 3).

A ANA entrega chuva, nível e vazão na mesma linha telemétrica; o domínio normaliza em
uma `Medicao` por grandeza. Cada subclasse define a grandeza (e a unidade, derivada dela)
e suas próprias validações.
"""

from abc import ABC, abstractmethod
from bisect import insort
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.dominio.enums import Grandeza, NivelConsistencia, OrigemDado
from app.dominio.periodo import Periodo
from app.dominio.tempo import exigir_utc


@dataclass(slots=True)
class Medicao(ABC):
    codigo_estacao: int
    data_hora_utc: datetime
    valor: float
    origem: OrigemDado = OrigemDado.TELEMETRICA
    consistencia: NivelConsistencia = NivelConsistencia.BRUTO
    status_fonte: str | None = None
    atualizado_na_fonte_em: datetime | None = None

    def __post_init__(self) -> None:
        self.data_hora_utc = exigir_utc(self.data_hora_utc, "data_hora_utc")
        if self.atualizado_na_fonte_em is not None:
            self.atualizado_na_fonte_em = exigir_utc(
                self.atualizado_na_fonte_em, "atualizado_na_fonte_em"
            )

    @abstractmethod
    def grandeza(self) -> Grandeza: ...

    def unidade(self) -> str:
        return self.grandeza().unidade

    def chave(self) -> tuple[int, Grandeza, datetime, OrigemDado]:
        """Chave natural usada para upsert (decisões de modelagem do doc)."""
        return (self.codigo_estacao, self.grandeza(), self.data_hora_utc, self.origem)


class MedicaoChuva(Medicao):
    def __post_init__(self) -> None:
        super().__post_init__()
        if self.valor < 0:
            raise ValueError("chuva não pode ser negativa")

    def grandeza(self) -> Grandeza:
        return Grandeza.CHUVA


class MedicaoNivel(Medicao):
    def grandeza(self) -> Grandeza:
        return Grandeza.NIVEL


class MedicaoVazao(Medicao):
    def __post_init__(self) -> None:
        super().__post_init__()
        if self.valor < 0:
            raise ValueError("vazão não pode ser negativa")

    def grandeza(self) -> Grandeza:
        return Grandeza.VAZAO


_CLASSE_POR_GRANDEZA: dict[Grandeza, type[Medicao]] = {
    Grandeza.CHUVA: MedicaoChuva,
    Grandeza.NIVEL: MedicaoNivel,
    Grandeza.VAZAO: MedicaoVazao,
}


def classe_de_medicao(grandeza: Grandeza) -> type[Medicao]:
    return _CLASSE_POR_GRANDEZA[grandeza]


@dataclass(slots=True)
class SerieTemporal:
    """Medições de uma grandeza de uma estação, sempre ordenadas por data/hora."""

    codigo_estacao: int
    grandeza: Grandeza
    medicoes: list[Medicao] = field(default_factory=list)

    def __post_init__(self) -> None:
        recebidas, self.medicoes = self.medicoes, []
        for medicao in recebidas:
            self.adicionar(medicao)

    def adicionar(self, medicao: Medicao) -> None:
        if medicao.codigo_estacao != self.codigo_estacao:
            raise ValueError("medição pertence a outra estação")
        if medicao.grandeza() != self.grandeza:
            raise ValueError(f"série de {self.grandeza} não aceita {medicao.grandeza()}")
        insort(self.medicoes, medicao, key=lambda m: m.data_hora_utc)

    def __len__(self) -> int:
        return len(self.medicoes)

    def vazia(self) -> bool:
        return not self.medicoes

    def unidade(self) -> str:
        return self.grandeza.unidade

    def no_periodo(self, periodo: Periodo) -> "SerieTemporal":
        return SerieTemporal(
            self.codigo_estacao,
            self.grandeza,
            [m for m in self.medicoes if periodo.contem(m.data_hora_utc)],
        )

    def ultimo(self) -> Medicao | None:
        return self.medicoes[-1] if self.medicoes else None

    def maximo(self) -> Medicao | None:
        return max(self.medicoes, key=lambda m: m.valor, default=None)

    def _janela_ate_ultimo(self, janela: timedelta) -> list[Medicao]:
        ultimo = self.ultimo()
        if ultimo is None:
            return []
        inicio = ultimo.data_hora_utc - janela
        return [m for m in self.medicoes if m.data_hora_utc > inicio]

    def acumulado(self, janela: timedelta) -> float:
        """Soma dos valores na janela que termina na última medição (ex.: chuva em 24h)."""
        return sum(m.valor for m in self._janela_ate_ultimo(janela))

    def variacao(self, janela: timedelta) -> float:
        """Diferença entre a última medição e a mais antiga da janela (ex.: subida do rio)."""
        medicoes = self._janela_ate_ultimo(janela)
        if len(medicoes) < 2:
            return 0.0
        return medicoes[-1].valor - medicoes[0].valor
