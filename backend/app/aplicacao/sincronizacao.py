import logging
from collections.abc import Callable
from datetime import datetime, timedelta

from app.aplicacao.filtros import FiltroEstacoes
from app.aplicacao.portas import EstacaoRepositorio, FonteDadosHidrologicos
from app.dominio.erros import FonteIndisponivel
from app.dominio.estacao import Estacao
from app.dominio.tempo import agora_utc

logger = logging.getLogger(__name__)

# Depois de uma falha, quanto tempo usar só o inventário local antes de tentar a fonte.
ESPERA_APOS_FALHA = timedelta(seconds=60)


class SincronizarEstacoes:
    """Copia o inventário de estações da fonte para o repositório local.

    Se a fonte cair e já houver estações locais para o filtro, segue com elas em vez de
    falhar; depois de uma falha, passa `espera_apos_falha` sem consultar a fonte, para
    que pedidos seguidos não esperem o timeout cada um.
    """

    def __init__(
        self,
        fonte: FonteDadosHidrologicos,
        estacoes: EstacaoRepositorio,
        *,
        espera_apos_falha: timedelta = ESPERA_APOS_FALHA,
        relogio: Callable[[], datetime] = agora_utc,
    ) -> None:
        self._fonte = fonte
        self._estacoes = estacoes
        self._espera_apos_falha = espera_apos_falha
        self._relogio = relogio
        self._ultima_falha: datetime | None = None

    def executar(self, filtro: FiltroEstacoes | None = None) -> int:
        filtro = filtro or FiltroEstacoes()
        if self._em_espera() and self._tem_locais(filtro):
            return 0
        try:
            estacoes = self._fonte.listar_estacoes(filtro)
        except FonteIndisponivel as erro:
            self._ultima_falha = self._relogio()
            if not self._tem_locais(filtro):
                raise
            logger.warning("inventário da fonte indisponível; usando o local: %s", erro)
            return 0
        self._ultima_falha = None
        return self._estacoes.salvar_varias(estacoes)

    def garantir(self, codigo: int) -> Estacao | None:
        estacao = self._estacoes.por_codigo(codigo)
        if estacao is not None:
            return estacao
        estacao = self._fonte.buscar_estacao(codigo)
        if estacao is not None:
            self._estacoes.salvar_varias([estacao])
        return estacao

    def _em_espera(self) -> bool:
        return (
            self._ultima_falha is not None
            and self._relogio() - self._ultima_falha < self._espera_apos_falha
        )

    def _tem_locais(self, filtro: FiltroEstacoes) -> bool:
        return bool(self._estacoes.buscar(filtro))
