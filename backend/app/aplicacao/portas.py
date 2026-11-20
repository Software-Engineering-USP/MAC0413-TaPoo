"""Portas da aplicação (docs/diagramas-de-classe-ana.md, seção 6).

Os serviços dependem apenas destas interfaces. Implementações concretas ficam em
`app/infra` (repositórios em memória e fontes fake ou ANA); repositórios SQL podem ser
adicionados sem alterar os serviços.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import datetime

from app.aplicacao.filtros import FiltroEstacoes
from app.dominio.alerta import Alerta, RegraAlerta
from app.dominio.enums import Grandeza
from app.dominio.estacao import Estacao
from app.dominio.geografia import Coordenada
from app.dominio.medicao import Medicao, PrevisaoChuva, SerieTemporal
from app.dominio.periodo import Periodo


class FonteDadosHidrologicos(ABC):
    carregar_na_inicializacao = True

    @abstractmethod
    def listar_estacoes(self, filtro: FiltroEstacoes) -> list[Estacao]: ...

    @abstractmethod
    def buscar_estacao(self, codigo: int) -> Estacao | None: ...

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


class FonteDePrevisao(ABC):
    """Fonte de previsão de chuva por coordenada (a porta externa, Open-Meteo)."""

    @abstractmethod
    def buscar_previsao(self, coordenada: Coordenada) -> list[PrevisaoChuva]:
        """Previsão de chuva por hora, em ordem cronológica."""


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
