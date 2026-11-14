from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencias import Consulta, Relogio
from app.api.schemas import EstacaoOut, EstacaoProximaOut, SerieOut
from app.aplicacao.filtros import FiltroEstacoes
from app.dominio.enums import Grandeza, TipoEstacao
from app.dominio.geografia import Coordenada
from app.dominio.periodo import Periodo

router = APIRouter(prefix="/estacoes", tags=["estações"])

PERIODO_PADRAO = timedelta(hours=24)
PERIODO_MAXIMO = timedelta(days=31)


@router.get("", response_model=list[EstacaoOut])
def listar_estacoes(
    consulta: Consulta,
    uf: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    tipo: TipoEstacao | None = None,
    apenas_telemetricas: bool = False,
) -> list[EstacaoOut]:
    filtro = FiltroEstacoes(uf=uf, tipo=tipo, apenas_telemetricas=apenas_telemetricas)
    return [EstacaoOut.de(e) for e in consulta.listar_estacoes(filtro)]


# Declarada antes de /{codigo} para "proximas" não ser lida como código.
@router.get("/proximas", response_model=list[EstacaoProximaOut])
def estacoes_proximas(
    consulta: Consulta,
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    raio_km: Annotated[float, Query(gt=0, le=1000)] = 50,
) -> list[EstacaoProximaOut]:
    return [
        EstacaoProximaOut.com_distancia(estacao, distancia)
        for estacao, distancia in consulta.estacoes_proximas(Coordenada(lat, lon), raio_km)
    ]


@router.get("/{codigo}", response_model=EstacaoOut)
def obter_estacao(codigo: int, consulta: Consulta) -> EstacaoOut:
    return EstacaoOut.de(consulta.estacao(codigo))


@router.get("/{codigo}/medicoes", response_model=SerieOut)
def serie_da_estacao(
    codigo: int,
    consulta: Consulta,
    relogio: Relogio,
    grandeza: Grandeza,
    inicio: Annotated[datetime | None, Query(description="ISO 8601 com fuso")] = None,
    fim: Annotated[datetime | None, Query(description="ISO 8601 com fuso")] = None,
) -> SerieOut:
    fim = fim or relogio()
    inicio = inicio or fim - PERIODO_PADRAO
    try:
        periodo = Periodo(inicio, fim)
    except ValueError as erro:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(erro)) from erro
    if periodo.duracao() > PERIODO_MAXIMO:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"período máximo é de {PERIODO_MAXIMO.days} dias",
        )
    return SerieOut.de(consulta.serie(codigo, grandeza, periodo), periodo)
