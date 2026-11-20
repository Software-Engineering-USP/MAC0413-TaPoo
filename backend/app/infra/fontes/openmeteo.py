"""Cliente Open-Meteo: implementa a porta `FonteDePrevisao` com chamada real."""

import json
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from app.aplicacao.portas import FonteDePrevisao
from app.dominio.geografia import Coordenada
from app.dominio.medicao import PrevisaoChuva
from app.dominio.tempo import exigir_utc

_BASE_URL = "https://api.open-meteo.com/v1/forecast"
_USER_AGENT = "taploo-backend"
_TIMEOUT = 10


class FonteOpenMeteo(FonteDePrevisao):
    def buscar_previsao(self, coordenada: Coordenada) -> list[PrevisaoChuva]:
        params = {
            "latitude": coordenada.latitude,
            "longitude": coordenada.longitude,
            "hourly": "precipitation",
            "timezone": "auto",
        }
        url = f"{_BASE_URL}?{urlencode(params)}"
        with urlopen(Request(url, headers={"User-Agent": _USER_AGENT}), timeout=_TIMEOUT) as resp:
            dados = json.loads(resp.read().decode("utf-8"))
        hourly = dados.get("hourly", {})
        fuso = ZoneInfo(str(dados.get("timezone", "UTC")))
        previsoes = []
        for texto, mm in zip(hourly.get("time", []), hourly.get("precipitation", [])):
            data = datetime.fromisoformat(str(texto))
            if data.tzinfo is None:
                data = data.replace(tzinfo=fuso)
            previsoes.append(PrevisaoChuva(exigir_utc(data), float(mm)))
        return previsoes
