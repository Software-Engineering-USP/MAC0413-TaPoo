from app.aplicacao.erros import EstacaoNaoEncontrada
from app.aplicacao.filtros import FiltroEstacoes
from app.aplicacao.portas import AlertaRepositorio, EstacaoRepositorio, MedicaoRepositorio
from app.dominio.alerta import Alerta
from app.dominio.enums import Grandeza
from app.dominio.estacao import Estacao
from app.dominio.geografia import Coordenada
from app.dominio.medicao import SerieTemporal
from app.dominio.periodo import Periodo


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

    def listar_estacoes(self, filtro: FiltroEstacoes) -> list[Estacao]:
        return self._estacoes.buscar(filtro)

    def estacao(self, codigo: int) -> Estacao:
        estacao = self._estacoes.por_codigo(codigo)
        if estacao is None:
            raise EstacaoNaoEncontrada(codigo)
        return estacao

    def estacoes_proximas(self, centro: Coordenada, raio_km: float) -> list[tuple[Estacao, float]]:
        """Estações dentro do raio, da mais próxima para a mais distante, com a distância."""
        if raio_km <= 0:
            raise ValueError("raio_km precisa ser positivo")
        com_distancia = [
            (estacao, centro.distancia_km(estacao.coordenada))
            for estacao in self._estacoes.buscar(FiltroEstacoes())
        ]
        return sorted(
            [(e, d) for e, d in com_distancia if d <= raio_km],
            key=lambda par: par[1],
        )

    def serie(self, codigo: int, grandeza: Grandeza, periodo: Periodo) -> SerieTemporal:
        self.estacao(codigo)
        return self._medicoes.serie(codigo, grandeza, periodo)

    def alertas_ativos(self) -> list[Alerta]:
        return sorted(self._alertas.ativos(), key=lambda a: a.severidade, reverse=True)
