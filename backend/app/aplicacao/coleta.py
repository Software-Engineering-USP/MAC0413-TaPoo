from collections.abc import Callable
from datetime import datetime, timedelta

from app.aplicacao.erros import EstacaoNaoEncontrada
from app.aplicacao.monitoramento import MonitorarEstacoes
from app.aplicacao.portas import EstacaoRepositorio, FonteDadosHidrologicos, MedicaoRepositorio
from app.dominio.periodo import Periodo
from app.dominio.tempo import agora_utc


class ColetarMedicoes:
    """Coleta incremental de medições (docs/diagramas-de-classe-ana.md, seção 7).

    Na primeira coleta busca `janela_inicial`; nas seguintes, apenas o que mudou desde a
    última atualização registrada. Depois de salvar, dispara o monitoramento da estação.
    """

    def __init__(
        self,
        fonte: FonteDadosHidrologicos,
        estacoes: EstacaoRepositorio,
        medicoes: MedicaoRepositorio,
        monitorar: MonitorarEstacoes,
        *,
        janela_inicial: timedelta = timedelta(days=2),
        relogio: Callable[[], datetime] = agora_utc,
    ) -> None:
        self._fonte = fonte
        self._estacoes = estacoes
        self._medicoes = medicoes
        self._monitorar = monitorar
        self._janela_inicial = janela_inicial
        self._relogio = relogio

    def executar(self, codigo: int) -> int:
        if self._estacoes.por_codigo(codigo) is None:
            raise EstacaoNaoEncontrada(codigo)
        agora = self._relogio()
        desde = self._medicoes.ultima_atualizacao(codigo)
        salvas = 0
        if desde is None or desde < agora:
            inicio = desde if desde is not None else agora - self._janela_inicial
            novas = self._fonte.buscar_medicoes(codigo, Periodo(inicio, agora), desde)
            salvas = self._medicoes.salvar_varias(novas)
        self._monitorar.executar(codigo)
        return salvas

    def executar_todas(self) -> int:
        return sum(self.executar(e.codigo) for e in self._estacoes.monitoradas())
