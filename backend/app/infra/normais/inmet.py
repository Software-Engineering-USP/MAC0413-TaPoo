"""Normais Climatológicas do INMET (1991–2020) lidas de um JSON versionado.

O arquivo é gerado por `scripts/importar_normais_inmet.py` a partir das planilhas
oficiais; a aplicação não depende do portal do INMET em tempo de execução.
"""

import json
from pathlib import Path
from threading import Lock

from app.aplicacao.portas import NormaisClimatologicas
from app.dominio.geografia import Coordenada
from app.dominio.normal_climatologica import NormalClimatologica

ARQUIVO_PADRAO = Path(__file__).parent / "dados" / "inmet-1991-2020-precipitacao.json"


class NormaisInmet(NormaisClimatologicas):
    """Carrega o arquivo na primeira consulta e mantém as normais em memória."""

    def __init__(self, arquivo: Path = ARQUIVO_PADRAO) -> None:
        self._arquivo = arquivo
        self._normais: list[NormalClimatologica] | None = None
        self._lock = Lock()

    def todas(self) -> list[NormalClimatologica]:
        with self._lock:
            if self._normais is None:
                self._normais = self._carregar()
            return list(self._normais)

    def _carregar(self) -> list[NormalClimatologica]:
        dados = json.loads(self._arquivo.read_text(encoding="utf-8"))
        return [
            NormalClimatologica(
                codigo=item["codigo"],
                nome=item["nome"],
                uf=item["uf"],
                coordenada=Coordenada(item["latitude"], item["longitude"]),
                chuva_mensal_mm=tuple(item["chuva_mensal_mm"]),
            )
            for item in dados["estacoes"]
        ]
