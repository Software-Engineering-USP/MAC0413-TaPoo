"""Regras de alerta e alertas (docs/diagramas-de-classe-ana.md, seção 4).

A ANA não fornece cotas de alerta nem severidade: isso é regra do TaPoo, configurada
por estação. Cada regra é uma estratégia (padrão Strategy) que lê uma série temporal
e devolve uma `Severidade`; o `AvaliadorAlertas` combina as regras.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from app.dominio.enums import Grandeza, Severidade, StatusAlerta
from app.dominio.medicao import Medicao, SerieTemporal
from app.dominio.tempo import exigir_utc


class RegraAlerta(ABC):
    def __init__(self, codigo_estacao: int, *, id: int | None = None, ativa: bool = True) -> None:
        self.id = id
        self.codigo_estacao = codigo_estacao
        self.ativa = ativa

    @property
    @abstractmethod
    def grandeza(self) -> Grandeza:
        """Grandeza da série que a regra precisa ler."""

    @abstractmethod
    def avaliar(self, serie: SerieTemporal) -> Severidade: ...

    @abstractmethod
    def descrever(self, severidade: Severidade, serie: SerieTemporal) -> str: ...

    def _validar_serie(self, serie: SerieTemporal) -> None:
        if serie.codigo_estacao != self.codigo_estacao or serie.grandeza != self.grandeza:
            raise ValueError(f"{type(self).__name__} não se aplica a esta série")


def _classificar(valor: float, limites: Sequence[tuple[float, Severidade]]) -> Severidade:
    """Devolve a severidade do maior limite atingido (limites em ordem crescente)."""
    resultado = Severidade.NORMAL
    for limite, severidade in limites:
        if valor >= limite:
            resultado = severidade
    return resultado


def _validar_crescente(*limites: float) -> None:
    if list(limites) != sorted(limites) or len(set(limites)) != len(limites):
        raise ValueError("limites precisam ser estritamente crescentes")


class RegraCotaReferencia(RegraAlerta):
    """Compara o nível mais recente com as cotas de atenção, alerta e inundação."""

    def __init__(
        self,
        codigo_estacao: int,
        cota_atencao_cm: float,
        cota_alerta_cm: float,
        cota_inundacao_cm: float,
        *,
        id: int | None = None,
        ativa: bool = True,
    ) -> None:
        super().__init__(codigo_estacao, id=id, ativa=ativa)
        _validar_crescente(cota_atencao_cm, cota_alerta_cm, cota_inundacao_cm)
        self.cota_atencao_cm = cota_atencao_cm
        self.cota_alerta_cm = cota_alerta_cm
        self.cota_inundacao_cm = cota_inundacao_cm

    @property
    def grandeza(self) -> Grandeza:
        return Grandeza.NIVEL

    def avaliar(self, serie: SerieTemporal) -> Severidade:
        self._validar_serie(serie)
        ultimo = serie.ultimo()
        if ultimo is None:
            return Severidade.NORMAL
        return _classificar(
            ultimo.valor,
            [
                (self.cota_atencao_cm, Severidade.ATENCAO),
                (self.cota_alerta_cm, Severidade.ALERTA),
                (self.cota_inundacao_cm, Severidade.EMERGENCIA),
            ],
        )

    def descrever(self, severidade: Severidade, serie: SerieTemporal) -> str:
        ultimo = serie.ultimo()
        nivel = f"{ultimo.valor:.0f} cm" if ultimo else "sem leitura"
        return f"Nível do rio em {nivel} (cota de inundação: {self.cota_inundacao_cm:.0f} cm)"


class RegraChuvaAcumulada(RegraAlerta):
    """Compara a chuva acumulada na janela com limites moderado, alto e extremo."""

    def __init__(
        self,
        codigo_estacao: int,
        janela: timedelta,
        limite_moderado_mm: float,
        limite_alto_mm: float,
        limite_extremo_mm: float,
        *,
        id: int | None = None,
        ativa: bool = True,
    ) -> None:
        super().__init__(codigo_estacao, id=id, ativa=ativa)
        if janela <= timedelta(0):
            raise ValueError("janela precisa ser positiva")
        _validar_crescente(limite_moderado_mm, limite_alto_mm, limite_extremo_mm)
        self.janela = janela
        self.limite_moderado_mm = limite_moderado_mm
        self.limite_alto_mm = limite_alto_mm
        self.limite_extremo_mm = limite_extremo_mm

    @property
    def grandeza(self) -> Grandeza:
        return Grandeza.CHUVA

    def avaliar(self, serie: SerieTemporal) -> Severidade:
        self._validar_serie(serie)
        return _classificar(
            serie.acumulado(self.janela),
            [
                (self.limite_moderado_mm, Severidade.ATENCAO),
                (self.limite_alto_mm, Severidade.ALERTA),
                (self.limite_extremo_mm, Severidade.EMERGENCIA),
            ],
        )

    def descrever(self, severidade: Severidade, serie: SerieTemporal) -> str:
        horas = self.janela.total_seconds() / 3600
        return f"Chuva acumulada de {serie.acumulado(self.janela):.1f} mm em {horas:.0f} h"


@dataclass(slots=True)
class Alerta:
    codigo_estacao: int
    severidade: Severidade
    mensagem: str
    emitido_em: datetime
    medicao_gatilho: Medicao | None = None
    status: StatusAlerta = StatusAlerta.ATIVO
    encerrado_em: datetime | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if self.severidade is Severidade.NORMAL:
            raise ValueError("alerta não pode ser emitido com severidade NORMAL")
        self.emitido_em = exigir_utc(self.emitido_em, "emitido_em")

    @property
    def ativo(self) -> bool:
        return self.status is StatusAlerta.ATIVO

    def escalar(self, nova: Severidade, mensagem: str, gatilho: Medicao | None = None) -> None:
        """Eleva a severidade. Alertas não são rebaixados: só encerram ao normalizar."""
        if not self.ativo:
            raise ValueError("não é possível escalar um alerta encerrado")
        if nova <= self.severidade:
            raise ValueError(f"{nova} não é mais grave que {self.severidade}")
        self.severidade = nova
        self.mensagem = mensagem
        self.medicao_gatilho = gatilho

    def encerrar(self, quando: datetime) -> None:
        if not self.ativo:
            raise ValueError("alerta já encerrado")
        quando = exigir_utc(quando, "quando")
        if quando < self.emitido_em:
            raise ValueError("encerramento anterior à emissão")
        self.status = StatusAlerta.ENCERRADO
        self.encerrado_em = quando


class AvaliadorAlertas:
    """Aplica as regras ativas de uma estação e decide o que fazer com o alerta ativo."""

    def __init__(self, regras: Sequence[RegraAlerta]) -> None:
        self.regras = [r for r in regras if r.ativa]

    def avaliar(
        self,
        series: Mapping[Grandeza, SerieTemporal],
        ativo: Alerta | None,
        agora: datetime,
    ) -> Alerta | None:
        """Devolve o alerta criado/alterado/encerrado, ou None se nada mudou."""
        severidade, mensagem, gatilho, codigo = self._pior_resultado(series)

        if severidade is Severidade.NORMAL:
            if ativo is not None and ativo.ativo:
                ativo.encerrar(agora)
                return ativo
            return None

        if ativo is None or not ativo.ativo:
            return Alerta(codigo, severidade, mensagem, emitido_em=agora, medicao_gatilho=gatilho)

        if severidade > ativo.severidade:
            ativo.escalar(severidade, mensagem, gatilho)
            return ativo
        return None

    def _pior_resultado(
        self, series: Mapping[Grandeza, SerieTemporal]
    ) -> tuple[Severidade, str, Medicao | None, int]:
        pior: tuple[Severidade, str, Medicao | None, int] = (Severidade.NORMAL, "", None, 0)
        for regra in self.regras:
            serie = series.get(regra.grandeza)
            if serie is None or serie.vazia():
                continue
            severidade = regra.avaliar(serie)
            if severidade > pior[0]:
                pior = (
                    severidade,
                    regra.descrever(severidade, serie),
                    serie.ultimo(),
                    regra.codigo_estacao,
                )
        return pior
