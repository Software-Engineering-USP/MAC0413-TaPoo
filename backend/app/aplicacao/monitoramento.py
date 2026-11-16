from collections.abc import Callable
from datetime import datetime, timedelta

from app.aplicacao.portas import AlertaRepositorio, MedicaoRepositorio, RegraRepositorio
from app.dominio.alerta import Alerta, AvaliadorAlertas
from app.dominio.periodo import Periodo
from app.dominio.tempo import agora_utc


class MonitorarEstacoes:
    """Avalia as regras de uma estação sobre as séries recentes e persiste o alerta."""

    def __init__(
        self,
        medicoes: MedicaoRepositorio,
        regras: RegraRepositorio,
        alertas: AlertaRepositorio,
        *,
        janela: timedelta = timedelta(hours=72),
        relogio: Callable[[], datetime] = agora_utc,
    ) -> None:
        self._medicoes = medicoes
        self._regras = regras
        self._alertas = alertas
        self._janela = janela
        self._relogio = relogio

    def executar(self, codigo: int) -> Alerta | None:
        regras = self._regras.da_estacao(codigo)
        if not regras:
            return None
        agora = self._relogio()
        periodo = Periodo.ultimos(self._janela, ate=agora)
        series = {
            regra.grandeza: self._medicoes.serie(codigo, regra.grandeza, periodo)
            for regra in regras
        }
        ativo = self._alertas.ativo_da_estacao(codigo)
        resultado = AvaliadorAlertas(regras).avaliar(series, ativo, agora)
        if resultado is not None:
            self._alertas.salvar(resultado)
        return resultado
