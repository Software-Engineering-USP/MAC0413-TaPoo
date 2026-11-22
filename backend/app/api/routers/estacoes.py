from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencias import Coletar, Consulta, Relogio, Sincronizar
from app.api.schemas import AlertaOut, EstacaoOut, EstacaoProximaOut, SerieOut
from app.aplicacao.filtros import FiltroEstacoes
from app.dominio.enums import Grandeza, TipoEstacao
from app.dominio.erros import DadoInvalido
from app.dominio.geografia import Coordenada
from app.dominio.periodo import Periodo

router = APIRouter(prefix="/estacoes", tags=["estações"])

PERIODO_PADRAO = timedelta(hours=24)
PERIODO_MAXIMO = timedelta(days=31)


@router.get("")
def listar_estacoes(
    consulta: Consulta,
    sincronizar: Sincronizar,
    uf: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    tipo: TipoEstacao | None = None,
    apenas_telemetricas: bool = False,
    q: Annotated[
        str | None,
        Query(
            min_length=2,
            max_length=100,
            description="Busca por nome da estação, município ou rio (sem acento e maiúsculas).",
        ),
    ] = None,
) -> list[EstacaoOut]:
    filtro = FiltroEstacoes(uf=uf, tipo=tipo, apenas_telemetricas=apenas_telemetricas, texto=q)
    # Busca sem UF fica nas estações já conhecidas: na ANA, sincronizar sem UF baixaria
    # o inventário do país inteiro a cada tecla digitada no front.
    if q is None or uf is not None:
        sincronizar.executar(filtro)
    return [EstacaoOut.de(e) for e in consulta.listar_estacoes(filtro)]


# Declarada antes de /{codigo} para "proximas" não ser lida como código.
@router.get("/proximas")
def estacoes_proximas(
    consulta: Consulta,
    sincronizar: Sincronizar,
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    raio_km: Annotated[float, Query(gt=0, le=1000)] = 50,
) -> list[EstacaoProximaOut]:
    sincronizar.executar(FiltroEstacoes())
    return [
        EstacaoProximaOut.com_distancia(situacao, distancia)
        for situacao, distancia in consulta.estacoes_proximas(Coordenada(lat, lon), raio_km)
    ]


@router.get("/{codigo}")
def obter_estacao(codigo: int, consulta: Consulta, sincronizar: Sincronizar) -> EstacaoOut:
    sincronizar.garantir(codigo)
    return EstacaoOut.de(consulta.situacao_estacao(codigo))


@router.get("/{codigo}/medicoes")
def serie_da_estacao(
    codigo: int,
    consulta: Consulta,
    coletar: Coletar,
    sincronizar: Sincronizar,
    relogio: Relogio,
    grandeza: Grandeza,
    inicio: Annotated[datetime | None, Query(description="ISO 8601 com fuso")] = None,
    fim: Annotated[datetime | None, Query(description="ISO 8601 com fuso")] = None,
) -> SerieOut:
    fim = fim or relogio()
    inicio = inicio or fim - PERIODO_PADRAO
    periodo = Periodo(inicio, fim)
    if periodo.duracao() > PERIODO_MAXIMO:
        raise DadoInvalido(f"período máximo é de {PERIODO_MAXIMO.days} dias")
    sincronizar.garantir(codigo)
    coletar.executar_periodo(codigo, periodo)
    return SerieOut.de(consulta.serie(codigo, grandeza, periodo), periodo)


@router.get("/{codigo}/alertas")
def historico_de_alertas(
    codigo: int,
    consulta: Consulta,
    sincronizar: Sincronizar,
    limite: Annotated[int, Query(ge=1, le=500)] = 50,
) -> list[AlertaOut]:
    """Alertas ativos e encerrados da estação, do mais recente para o mais antigo."""
    sincronizar.garantir(codigo)
    return [AlertaOut.de(a) for a in consulta.historico_alertas(codigo, limite)]
