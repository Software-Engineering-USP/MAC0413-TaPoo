import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from app.aplicacao.coleta import ColetarMedicoes
from app.aplicacao.erros import EstacaoNaoEncontrada, EstacaoSemChuva, NormalNaoEncontrada
from app.aplicacao.portas import EstacaoRepositorio, MedicaoRepositorio, NormaisClimatologicas
from app.dominio.enums import Grandeza
from app.dominio.erros import FonteIndisponivel
from app.dominio.geografia import Coordenada
from app.dominio.normal_climatologica import ChuvaMensal, NormalClimatologica
from app.dominio.periodo import Periodo
from app.dominio.tempo import agora_utc

logger = logging.getLogger(__name__)

# O "mês atual" é o do calendário brasileiro, não o de UTC.
FUSO_MES = ZoneInfo("America/Sao_Paulo")


class CompararChuvaComNormal:
    """Chuva acumulada no mês corrente comparada à normal do INMET mais próxima (#166).

    Antes de somar, tenta trazer da fonte as medições do mês; se a fonte estiver fora,
    usa o que já está salvo.
    """

    def __init__(
        self,
        estacoes: EstacaoRepositorio,
        medicoes: MedicaoRepositorio,
        normais: NormaisClimatologicas,
        coletar: ColetarMedicoes,
        *,
        relogio: Callable[[], datetime] = agora_utc,
    ) -> None:
        self._estacoes = estacoes
        self._medicoes = medicoes
        self._normais = normais
        self._coletar = coletar
        self._relogio = relogio

    def executar(self, codigo: int) -> ChuvaMensal:
        estacao = self._estacoes.por_codigo(codigo)
        if estacao is None:
            raise EstacaoNaoEncontrada(codigo)
        if not estacao.mede(Grandeza.CHUVA):
            raise EstacaoSemChuva(codigo)

        agora = self._relogio()
        local = agora.astimezone(FUSO_MES)
        periodo = periodo_do_mes(agora)
        atualizado = True
        try:
            self._coletar.executar_periodo(codigo, periodo)
        except FonteIndisponivel as erro:
            atualizado = False
            logger.warning("chuva do mês da estação %s sem atualizar: %s", codigo, erro)

        serie = self._medicoes.serie(codigo, Grandeza.CHUVA, periodo)
        referencia, distancia = self.referencia(estacao.coordenada, local.month)
        return ChuvaMensal(
            codigo_estacao=codigo,
            ano=local.year,
            mes=local.month,
            acumulado_mm=sum(medicao.valor for medicao in serie.medicoes),
            medicoes=len(serie),
            referencia=referencia,
            distancia_km=distancia,
            atualizado=atualizado,
        )

    def referencia(self, coordenada: Coordenada, mes: int) -> tuple[NormalClimatologica, float]:
        """Estação do INMET mais próxima que tem normal para o mês, com a distância."""
        candidatas = [
            (normal, coordenada.distancia_km(normal.coordenada))
            for normal in self._normais.todas()
            if normal.chuva_do_mes(mes) is not None
        ]
        if not candidatas:
            raise NormalNaoEncontrada(mes)
        return min(candidatas, key=lambda par: par[1])


def periodo_do_mes(agora: datetime) -> Periodo:
    """Do primeiro instante do mês (horário de Brasília) até `agora`."""
    local = agora.astimezone(FUSO_MES)
    inicio = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)
    return Periodo(inicio, max(agora, inicio + timedelta(seconds=1)))
