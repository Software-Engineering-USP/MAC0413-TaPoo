"""Esquemas de resposta da API.

O domínio não é serializado diretamente: estes modelos definem o contrato público e
isolam o frontend de mudanças internas.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.dominio.alerta import (
    Alerta,
    FatorAvaliacao,
    LimitesClassificacao,
)
from app.dominio.enums import (
    Grandeza,
    NivelConsistencia,
    OrigemDado,
    Severidade,
    StatusAlerta,
    TipoEstacao,
    TipoRegraAlerta,
)
from app.dominio.medicao import Medicao, SerieTemporal
from app.dominio.periodo import Periodo
from app.dominio.situacao import SituacaoEstacao, SituacaoMunicipio


class FatorAvaliacaoOut(BaseModel):
    descricao: str
    severidade: Severidade
    severidade_rotulo: str

    @classmethod
    def de(cls, fator: FatorAvaliacao) -> "FatorAvaliacaoOut":
        return cls(
            descricao=fator.descricao,
            severidade=fator.severidade,
            severidade_rotulo=fator.severidade.rotulo,
        )


class AlertaOut(BaseModel):
    id: UUID
    codigo_estacao: int
    severidade: Severidade
    severidade_rotulo: str
    status: StatusAlerta
    mensagem: str
    fatores: list[FatorAvaliacaoOut]
    emitido_em: datetime
    encerrado_em: datetime | None

    @classmethod
    def de(cls, alerta: Alerta) -> "AlertaOut":
        return cls(
            id=alerta.id,
            codigo_estacao=alerta.codigo_estacao,
            severidade=alerta.severidade,
            severidade_rotulo=alerta.severidade.rotulo,
            fatores=[FatorAvaliacaoOut.de(fator) for fator in alerta.fatores],
            status=alerta.status,
            mensagem=alerta.mensagem,
            emitido_em=alerta.emitido_em,
            encerrado_em=alerta.encerrado_em,
        )


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
    severidade: Severidade
    severidade_rotulo: str
    alerta: AlertaOut | None

    @classmethod
    def de(cls, situacao: SituacaoEstacao) -> "EstacaoOut":
        estacao = situacao.estacao
        return cls(
            codigo=estacao.codigo,
            nome=estacao.nome,
            tipo=estacao.tipo,
            latitude=estacao.coordenada.latitude,
            longitude=estacao.coordenada.longitude,
            uf=estacao.municipio.uf,
            municipio=estacao.municipio.nome,
            rio=estacao.rio,
            operando=estacao.operando,
            telemetrica=estacao.telemetrica,
            grandezas=[g for g in Grandeza if estacao.mede(g)],
            severidade=situacao.severidade,
            severidade_rotulo=situacao.severidade.rotulo,
            alerta=AlertaOut.de(situacao.alerta) if situacao.alerta is not None else None,
        )


class EstacaoProximaOut(EstacaoOut):
    distancia_km: float

    @classmethod
    def com_distancia(cls, situacao: SituacaoEstacao, distancia_km: float) -> "EstacaoProximaOut":
        return cls(**EstacaoOut.de(situacao).model_dump(), distancia_km=round(distancia_km, 2))


class MedicaoOut(BaseModel):
    data_hora_utc: datetime
    valor: float
    consistencia: NivelConsistencia
    status_fonte: str | None
    origem: OrigemDado
    atualizado_na_fonte_em: datetime | None

    @classmethod
    def de(cls, medicao: Medicao) -> "MedicaoOut":
        return cls(
            data_hora_utc=medicao.data_hora_utc,
            valor=medicao.valor,
            consistencia=medicao.consistencia,
            status_fonte=medicao.status_fonte,
            origem=medicao.origem,
            atualizado_na_fonte_em=medicao.atualizado_na_fonte_em,
        )


class LimiteEstacaoOut(BaseModel):
    grandeza: Grandeza
    tipo: TipoRegraAlerta
    descricao: str
    unidade: str
    janela_horas: float | None
    atencao: float
    alerta: float
    emergencia: float

    @classmethod
    def de(cls, limites: LimitesClassificacao) -> "LimiteEstacaoOut":
        return cls(
            grandeza=limites.grandeza,
            tipo=limites.tipo,
            descricao=limites.descricao,
            unidade=limites.unidade,
            janela_horas=limites.janela_horas,
            atencao=limites.atencao,
            alerta=limites.alerta,
            emergencia=limites.emergencia,
        )


class SerieOut(BaseModel):
    codigo_estacao: int
    grandeza: Grandeza
    grandeza_rotulo: str
    unidade: str
    inicio: datetime
    fim: datetime
    medicoes: list[MedicaoOut]

    @classmethod
    def de(cls, serie: SerieTemporal, periodo: Periodo) -> "SerieOut":
        return cls(
            codigo_estacao=serie.codigo_estacao,
            grandeza=serie.grandeza,
            grandeza_rotulo=serie.grandeza.rotulo,
            unidade=serie.unidade(),
            inicio=periodo.inicio,
            fim=periodo.fim,
            medicoes=[MedicaoOut.de(m) for m in serie.medicoes],
        )


class SituacaoMunicipioOut(BaseModel):
    uf: str
    municipio: str
    severidade: Severidade
    severidade_rotulo: str
    estacoes: list[EstacaoOut]

    @classmethod
    def de(cls, situacao: SituacaoMunicipio) -> "SituacaoMunicipioOut":
        return cls(
            uf=situacao.municipio.uf,
            municipio=situacao.municipio.nome,
            severidade=situacao.severidade,
            severidade_rotulo=situacao.severidade.rotulo,
            estacoes=[EstacaoOut.de(s) for s in situacao.estacoes],
        )
