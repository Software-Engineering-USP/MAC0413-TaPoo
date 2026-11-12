from app.aplicacao.filtros import FiltroEstacoes
from app.aplicacao.portas import EstacaoRepositorio, FonteDadosHidrologicos


class SincronizarEstacoes:
    """Copia o inventário de estações da fonte para o repositório local."""

    def __init__(self, fonte: FonteDadosHidrologicos, estacoes: EstacaoRepositorio) -> None:
        self._fonte = fonte
        self._estacoes = estacoes

    def executar(self, filtro: FiltroEstacoes | None = None) -> int:
        return self._estacoes.salvar_varias(self._fonte.listar_estacoes(filtro or FiltroEstacoes()))
