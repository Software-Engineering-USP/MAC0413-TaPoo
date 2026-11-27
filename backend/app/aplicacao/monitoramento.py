import logging
from collections.abc import Callable
from datetime import datetime, timedelta

from app.aplicacao.portas import (
    AlertaRepositorio,
    FonteDePrevisao,
    MedicaoRepositorio,
    RegraRepositorio,
)
from app.dominio.alerta import Alerta, AvaliadorAlertas, RegraChuvaPrevisao
from app.dominio.erros import FonteIndisponivel
from app.dominio.periodo import Periodo
from app.dominio.tempo import agora_utc

logger = logging.getLogger(__name__)


class MonitorarEstacoes:
    """Avalia as regras de uma estação sobre as séries recentes e persiste o alerta."""

    def __init__(
        self,
        medicoes: MedicaoRepositorio,
        regras: RegraRepositorio,
        alertas: AlertaRepositorio,
        *,
        fonte_previsao: FonteDePrevisao | None = None,
        janela: timedelta = timedelta(hours=72),
        relogio: Callable[[], datetime] = agora_utc,
    ) -> None:
        self._medicoes = medicoes
        self._regras = regras
        self._alertas = alertas
        self._fonte_previsao = fonte_previsao
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
            if regra.usa_serie
        }
        regras_previsao = [r for r in regras if isinstance(r, RegraChuvaPrevisao)]
        previsoes = None
        if self._fonte_previsao is not None and regras_previsao:
            try:
                previsoes = self._fonte_previsao.buscar_previsao(regras_previsao[0].coordenada)
            except FonteIndisponivel as erro:
                logger.warning("previsão de chuva da estação %s falhou: %s", codigo, erro)
        ativo = self._alertas.ativo_da_estacao(codigo)
        resultado = AvaliadorAlertas(regras).avaliar(series, ativo, agora, previsoes)
        if resultado is not None:
            self._alertas.salvar(resultado)
        return resultado
