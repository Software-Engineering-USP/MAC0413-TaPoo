"""Portas da aplicação (docs/diagramas-de-classe-ana.md, seção 6).

Os serviços dependem apenas destas interfaces. Implementações concretas ficam em
`app/infra` (hoje: repositórios em memória e uma fonte de dados de exemplo; depois:
repositórios SQL e o adaptador da ANA).
"""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import datetime

from app.aplicacao.filtros import FiltroEstacoes
from app.dominio.alerta import Alerta, RegraAlerta
from app.dominio.enums import Grandeza
from app.dominio.estacao import Estacao
from app.dominio.medicao import Medicao, SerieTemporal
from app.dominio.periodo import Periodo


class FonteDadosHidrologicos(ABC):
    @abstractmethod
    def listar_estacoes(self, filtro: FiltroEstacoes) -> list[Estacao]: ...

    @abstractmethod
    def buscar_medicoes(
        self, codigo: int, periodo: Periodo, alteradas_desde: datetime | None = None
    ) -> list[Medicao]: ...


class EstacaoRepositorio(ABC):
    @abstractmethod
    def salvar_varias(self, estacoes: Iterable[Estacao]) -> int: ...

    @abstractmethod
    def por_codigo(self, codigo: int) -> Estacao | None: ...

    @abstractmethod
    def buscar(self, filtro: FiltroEstacoes) -> list[Estacao]: ...

    @abstractmethod
    def monitoradas(self) -> list[Estacao]:
        """Estações operando e telemétricas, cujas medições são coletadas."""


class MedicaoRepositorio(ABC):
    @abstractmethod
    def salvar_varias(self, medicoes: Iterable[Medicao]) -> int:
        """Insere ou atualiza pela chave natural (`Medicao.chave()`)."""

    @abstractmethod
    def serie(self, codigo: int, grandeza: Grandeza, periodo: Periodo) -> SerieTemporal: ...

    @abstractmethod
    def ultima_atualizacao(self, codigo: int) -> datetime | None: ...


class AlertaRepositorio(ABC):
    @abstractmethod
    def salvar(self, alerta: Alerta) -> None: ...

    @abstractmethod
    def ativo_da_estacao(self, codigo: int) -> Alerta | None: ...

    @abstractmethod
    def ativos(self) -> list[Alerta]: ...


class RegraRepositorio(ABC):
    @abstractmethod
    def da_estacao(self, codigo: int) -> list[RegraAlerta]: ...
