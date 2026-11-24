"""Cliente Open-Meteo: implementa a porta `FonteDePrevisao` com chamada real."""

import json
from datetime import datetime
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from app.aplicacao.portas import FonteDePrevisao
from app.dominio.erros import FonteIndisponivel
from app.dominio.geografia import Coordenada
from app.dominio.medicao import PrevisaoChuva
from app.dominio.tempo import exigir_utc

_BASE_URL = "https://api.open-meteo.com/v1/forecast"
_USER_AGENT = "tapoo-backend"
_TIMEOUT = 10


class FonteOpenMeteo(FonteDePrevisao):
    def buscar_previsao(self, coordenada: Coordenada) -> list[PrevisaoChuva]:
        params = {
            "latitude": coordenada.latitude,
            "longitude": coordenada.longitude,
            "hourly": "precipitation",
            "timezone": "GMT",
            "forecast_days": 7,
        }
        url = f"{_BASE_URL}?{urlencode(params)}"
        try:
            with urlopen(
                Request(url, headers={"User-Agent": _USER_AGENT}), timeout=_TIMEOUT
            ) as resp:
                dados = json.loads(resp.read().decode("utf-8"))
            if not isinstance(dados, dict):
                raise TypeError("resposta não é um objeto JSON")
            hourly = dados.get("hourly", {})
            if not isinstance(hourly, dict):
                raise TypeError("campo hourly inválido")
            tempos = hourly.get("time", [])
            chuvas = hourly.get("precipitation", [])
            if not isinstance(tempos, list) or not isinstance(chuvas, list):
                raise TypeError("séries horárias inválidas")
            if len(tempos) != len(chuvas):
                raise ValueError("séries horárias com comprimentos diferentes")
            fuso = ZoneInfo(str(dados.get("timezone", "UTC")))
            previsoes = []
            for texto, mm in zip(tempos, chuvas):
                data = datetime.fromisoformat(str(texto))
                if data.tzinfo is None:
                    data = data.replace(tzinfo=fuso)
                previsoes.append(PrevisaoChuva(exigir_utc(data), float(mm)))
            return previsoes
        except (
            URLError,
            TimeoutError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            TypeError,
            ValueError,
        ) as erro:
            raise FonteIndisponivel(
                "Open-Meteo indisponível ou retornou dados inválidos."
            ) from erro
