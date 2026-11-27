"""Converte as planilhas das Normais Climatológicas do INMET (1991–2020) no JSON da API.

Fonte: https://portal.inmet.gov.br/normais, seção "Normais Climatológicas 1991-2020":
- Normal-Climatologica-PREC.xlsx (precipitação acumulada mensal, mm)
- Normal-Climatologica-ESTAÇÕES.xlsx (código, nome, UF, latitude e longitude)

Uso (o openpyxl só é preciso aqui, não na aplicação):

    uv run --with openpyxl python -m scripts.importar_normais_inmet PREC.xlsx ESTACOES.xlsx

Grava `app/infra/normais/dados/inmet-1991-2020-precipitacao.json`. Meses sem normal
calculada ("-" na planilha) viram `null`; estações sem coordenadas ficam de fora.
"""

import json
import sys
from pathlib import Path
from typing import Any

DESTINO = (
    Path(__file__).resolve().parents[1]
    / "app/infra/normais/dados/inmet-1991-2020-precipitacao.json"
)
FONTE = "INMET — Normais Climatológicas do Brasil 1991–2020, precipitação acumulada mensal"


def _linhas(caminho: str) -> list[tuple[Any, ...]]:
    import openpyxl

    planilha = openpyxl.load_workbook(caminho, read_only=True, data_only=True).worksheets[0]
    linhas = list(planilha.iter_rows(values_only=True))
    # As duas primeiras linhas são título; a terceira é o cabeçalho.
    return [linha for linha in linhas[3:] if linha and linha[0] is not None]


def _numero(valor: Any) -> float | None:
    return float(valor) if isinstance(valor, int | float) else None


def converter(caminho_prec: str, caminho_estacoes: str) -> dict[str, Any]:
    coordenadas = {
        int(linha[1]): (float(linha[4]), float(linha[5]))
        for linha in _linhas(caminho_estacoes)
        if _numero(linha[4]) is not None and _numero(linha[5]) is not None
    }
    estacoes = []
    sem_coordenada = []
    for linha in _linhas(caminho_prec):
        codigo = int(linha[0])
        if codigo not in coordenadas:
            sem_coordenada.append(codigo)
            continue
        latitude, longitude = coordenadas[codigo]
        estacoes.append(
            {
                "codigo": codigo,
                "nome": str(linha[1]).strip(),
                "uf": str(linha[2]).strip().upper(),
                "latitude": latitude,
                "longitude": longitude,
                "chuva_mensal_mm": [_numero(valor) for valor in linha[3:15]],
            }
        )
    if sem_coordenada:
        print(f"sem coordenadas, ignoradas: {sorted(sem_coordenada)}", file=sys.stderr)
    estacoes.sort(key=lambda estacao: estacao["codigo"])
    return {"fonte": FONTE, "periodo": "1991-2020", "estacoes": estacoes}


def main(argv: list[str]) -> None:
    if len(argv) != 2:
        raise SystemExit(__doc__)
    dados = converter(*argv)
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(json.dumps(dados, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(dados['estacoes'])} estações gravadas em {DESTINO}")


if __name__ == "__main__":
    main(sys.argv[1:])
