from app.aplicacao.filtros import FiltroEstacoes
from app.aplicacao.portas import EstacaoRepositorio, FonteDadosHidrologicos
from app.dominio.estacao import Estacao


class SincronizarEstacoes:
    """Copia o inventário de estações da fonte para o repositório local."""

    def __init__(self, fonte: FonteDadosHidrologicos, estacoes: EstacaoRepositorio) -> None:
        self._fonte = fonte
        self._estacoes = estacoes

    def executar(self, filtro: FiltroEstacoes | None = None) -> int:
        return self._estacoes.salvar_varias(self._fonte.listar_estacoes(filtro or FiltroEstacoes()))

    def garantir(self, codigo: int) -> Estacao | None:
        estacao = self._estacoes.por_codigo(codigo)
        if estacao is not None:
            return estacao
        estacao = self._fonte.buscar_estacao(codigo)
        if estacao is not None:
            self._estacoes.salvar_varias([estacao])
        return estacao
