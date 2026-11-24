import json
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import pytest

from app.aplicacao.portas import FonteDePrevisao
from app.dominio.geografia import Coordenada
from app.dominio.medicao import PrevisaoChuva
from app.infra.fontes import openmeteo
from app.infra.fontes.openmeteo import FonteOpenMeteo


class RespostaFake:
    def __init__(self, dados: dict) -> None:
        self._dados = json.dumps(dados).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return self._dados


def test_fonte_openmeteo_e_uma_fonte_de_previsao() -> None:
    assert isinstance(FonteOpenMeteo(), FonteDePrevisao)


def test_buscar_previsao_mapeia_horas(monkeypatch) -> None:
    corpo = {
        "timezone": "GMT",
        "hourly": {
            "time": ["2026-11-21T11:00", "2026-11-21T12:00"],
            "precipitation": [2.5, 0.0],
        },
    }
    requisicoes = []

    def abrir(req, timeout):
        requisicoes.append((req, timeout))
        return RespostaFake(corpo)

    monkeypatch.setattr(openmeteo, "urlopen", abrir)

    previsoes = FonteOpenMeteo().buscar_previsao(Coordenada(-23.5, -46.6))

    assert [p.chuva_mm for p in previsoes] == [2.5, 0.0]
    for previsao in previsoes:
        assert previsao.data_hora_utc.tzinfo is not None
    requisicao, timeout = requisicoes[0]
    parametros = parse_qs(urlparse(requisicao.full_url).query)
    assert parametros["timezone"] == ["GMT"]
    assert parametros["forecast_days"] == ["7"]
    assert requisicao.get_header("User-agent") == "tapoo-backend"
    assert timeout == openmeteo._TIMEOUT


def test_buscar_previsao_sem_horas_retorna_lista_vazia(monkeypatch) -> None:
    monkeypatch.setattr(openmeteo, "urlopen", lambda req, timeout: RespostaFake({}))
    assert FonteOpenMeteo().buscar_previsao(Coordenada(-23.5, -46.6)) == []


def test_previsao_chuva_valida_valor_negativo() -> None:
    from app.dominio.erros import DadoInvalido

    with pytest.raises(DadoInvalido):
        PrevisaoChuva(datetime(2026, 1, 1, tzinfo=ZoneInfo("UTC")), -1.0)
