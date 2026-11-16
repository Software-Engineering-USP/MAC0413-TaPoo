"""Esquemas de resposta da API.

O domínio não é serializado diretamente: estes modelos definem o contrato público e
isolam o frontend de mudanças internas.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.dominio.alerta import Alerta
from app.dominio.enums import (
    Grandeza,
    NivelConsistencia,
    Severidade,
    StatusAlerta,
    TipoEstacao,
)
from app.dominio.estacao import Estacao
from app.dominio.medicao import Medicao, SerieTemporal
from app.dominio.periodo import Periodo


class EstacaoOut(BaseModel):
    codigo: int
    nome: str
    tipo: TipoEstacao
    latitude: float
    longitude: float
    uf: str
    municipio: str
    rio: str | None
    operando: bool
    telemetrica: bool
    grandezas: list[Grandeza]

    @classmethod
    def de(cls, estacao: Estacao) -> "EstacaoOut":
        return cls(
            codigo=estacao.codigo,
            nome=estacao.nome,
            tipo=estacao.tipo,
            latitude=estacao.coordenada.latitude,
            longitude=estacao.coordenada.longitude,
            uf=estacao.uf,
            municipio=estacao.municipio,
            rio=estacao.rio,
            operando=estacao.operando,
            telemetrica=estacao.telemetrica,
            grandezas=[g for g in Grandeza if estacao.mede(g)],
        )


class EstacaoProximaOut(EstacaoOut):
    distancia_km: float

    @classmethod
    def com_distancia(cls, estacao: Estacao, distancia_km: float) -> "EstacaoProximaOut":
        return cls(**EstacaoOut.de(estacao).model_dump(), distancia_km=round(distancia_km, 2))


class MedicaoOut(BaseModel):
    data_hora_utc: datetime
    valor: float
    consistencia: NivelConsistencia
    status_fonte: str | None

    @classmethod
    def de(cls, medicao: Medicao) -> "MedicaoOut":
        return cls(
            data_hora_utc=medicao.data_hora_utc,
            valor=medicao.valor,
            consistencia=medicao.consistencia,
            status_fonte=medicao.status_fonte,
        )


class SerieOut(BaseModel):
    codigo_estacao: int
    grandeza: Grandeza
    unidade: str
    inicio: datetime
    fim: datetime
    medicoes: list[MedicaoOut]

    @classmethod
    def de(cls, serie: SerieTemporal, periodo: Periodo) -> "SerieOut":
        return cls(
            codigo_estacao=serie.codigo_estacao,
            grandeza=serie.grandeza,
            unidade=serie.unidade(),
            inicio=periodo.inicio,
            fim=periodo.fim,
            medicoes=[MedicaoOut.de(m) for m in serie.medicoes],
        )


class AlertaOut(BaseModel):
    id: UUID
    codigo_estacao: int
    severidade: Severidade
    status: StatusAlerta
    mensagem: str
    emitido_em: datetime
    encerrado_em: datetime | None

    @classmethod
    def de(cls, alerta: Alerta) -> "AlertaOut":
        return cls(
            id=alerta.id,
            codigo_estacao=alerta.codigo_estacao,
            severidade=alerta.severidade,
            status=alerta.status,
            mensagem=alerta.mensagem,
            emitido_em=alerta.emitido_em,
            encerrado_em=alerta.encerrado_em,
        )
