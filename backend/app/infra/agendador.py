"""Execução periódica de uma ação em segundo plano, dentro do event loop da API."""

import asyncio
import logging
from collections.abc import Callable
from datetime import timedelta

logger = logging.getLogger(__name__)


class AgendadorDeColeta:
    """Roda `acao` a cada `intervalo` até `parar()` ser chamado.

    A ação é síncrona (os clientes HTTP das fontes usam `httpx` síncrono), por isso roda em
    uma thread com `asyncio.to_thread`, sem travar as requisições da API. O intervalo é
    contado a partir do fim de cada ciclo, então dois ciclos nunca se sobrepõem. Uma falha
    em um ciclo vai para o log e não interrompe os próximos.
    """

    def __init__(
        self,
        acao: Callable[[], object],
        intervalo: timedelta,
        *,
        atraso_inicial: timedelta | None = None,
    ) -> None:
        if intervalo <= timedelta(0):
            raise ValueError("O intervalo do agendador precisa ser maior que zero.")
        self._acao = acao
        self._intervalo = intervalo
        self._atraso_inicial = intervalo if atraso_inicial is None else atraso_inicial
        self._tarefa: asyncio.Task[None] | None = None

    @property
    def rodando(self) -> bool:
        return self._tarefa is not None and not self._tarefa.done()

    def iniciar(self) -> None:
        if self.rodando:
            return
        self._tarefa = asyncio.create_task(self._loop(), name="agendador-de-coleta")

    async def parar(self) -> None:
        tarefa, self._tarefa = self._tarefa, None
        if tarefa is None:
            return
        tarefa.cancel()
        # `wait` espera o fim da tarefa sem relançar o cancelamento dela; se quem chamou
        # `parar()` for cancelado, o `CancelledError` dele continua propagando.
        await asyncio.wait([tarefa])

    async def _loop(self) -> None:
        await asyncio.sleep(self._atraso_inicial.total_seconds())
        while True:
            await self._executar_ciclo()
            await asyncio.sleep(self._intervalo.total_seconds())

    async def _executar_ciclo(self) -> None:
        try:
            resultado = await asyncio.to_thread(self._acao)
        except Exception:
            logger.exception("Falha no ciclo de coleta; nova tentativa no próximo ciclo.")
        else:
            logger.info("Ciclo de coleta concluído: %s", resultado)
