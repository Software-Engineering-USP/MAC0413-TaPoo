from collections.abc import Iterable

from app.aplicacao.erros import EstacaoNaoEncontrada, MunicipioNaoEncontrado
from app.aplicacao.filtros import FiltroEstacoes
from app.aplicacao.portas import AlertaRepositorio, EstacaoRepositorio, MedicaoRepositorio
from app.dominio.alerta import Alerta
from app.dominio.enums import Grandeza
from app.dominio.estacao import Estacao
from app.dominio.geografia import Coordenada
from app.dominio.medicao import SerieTemporal
from app.dominio.periodo import Periodo
from app.dominio.situacao import SituacaoEstacao, SituacaoMunicipio


class ConsultarDados:
    """Casos de uso somente leitura usados pela API: o usuário apenas consulta dados."""

    def __init__(
        self,
        estacoes: EstacaoRepositorio,
        medicoes: MedicaoRepositorio,
        alertas: AlertaRepositorio,
    ) -> None:
        self._estacoes = estacoes
        self._medicoes = medicoes
        self._alertas = alertas

    def listar_estacoes(self, filtro: FiltroEstacoes) -> list[SituacaoEstacao]:
        """Estações que atendem ao filtro, cada uma com a sua situação atual."""
        return self._com_situacao(self._estacoes.buscar(filtro))

    def estacao(self, codigo: int) -> Estacao:
        estacao = self._estacoes.por_codigo(codigo)
        if estacao is None:
            raise EstacaoNaoEncontrada(codigo)
        return estacao

    def situacao_estacao(self, codigo: int) -> SituacaoEstacao:
        estacao = self.estacao(codigo)
        return SituacaoEstacao(estacao, self._alertas.ativo_da_estacao(codigo))

    def situacao_municipio(self, uf: str, municipio: str) -> SituacaoMunicipio:
        """Pior situação entre as estações do município (nome comparado sem acentos)."""
        estacoes = self._estacoes.buscar(FiltroEstacoes(uf=uf, municipio=municipio))
        if not estacoes:
            raise MunicipioNaoEncontrado(uf, municipio)
        # Usa a grafia cadastrada, não a digitada pelo usuário.
        return SituacaoMunicipio(
            estacoes[0].uf, estacoes[0].municipio, tuple(self._com_situacao(estacoes))
        )

    def estacoes_proximas(
        self, centro: Coordenada, raio_km: float
    ) -> list[tuple[SituacaoEstacao, float]]:
        """Estações dentro do raio, da mais próxima para a mais distante, com a distância."""
        if raio_km <= 0:
            raise ValueError("raio_km precisa ser positivo")
        com_distancia = [
            (estacao, centro.distancia_km(estacao.coordenada))
            for estacao in self._estacoes.buscar(FiltroEstacoes())
        ]
        proximas = sorted(
            [(e, d) for e, d in com_distancia if d <= raio_km],
            key=lambda par: par[1],
        )
        situacoes = self._com_situacao(e for e, _ in proximas)
        return [(s, d) for s, (_, d) in zip(situacoes, proximas, strict=True)]

    def serie(self, codigo: int, grandeza: Grandeza, periodo: Periodo) -> SerieTemporal:
        self.estacao(codigo)
        return self._medicoes.serie(codigo, grandeza, periodo)

    def alertas_ativos(self) -> list[Alerta]:
        return sorted(self._alertas.ativos(), key=lambda a: a.severidade, reverse=True)

    def _com_situacao(self, estacoes: Iterable[Estacao]) -> list[SituacaoEstacao]:
        """Associa a cada estação o seu alerta ativo, consultando os alertas uma só vez."""
        ativos = {a.codigo_estacao: a for a in self._alertas.ativos()}
        return [SituacaoEstacao(e, ativos.get(e.codigo)) for e in estacoes]
