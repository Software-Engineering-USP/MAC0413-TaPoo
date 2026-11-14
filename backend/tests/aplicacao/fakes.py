"""Implementações mínimas das portas, só para testar os serviços isoladamente."""

from collections.abc import Iterable
from datetime import datetime

from app.aplicacao.filtros import FiltroEstacoes
from app.aplicacao.portas import (
    AlertaRepositorio,
    EstacaoRepositorio,
    FonteDadosHidrologicos,
    MedicaoRepositorio,
    RegraRepositorio,
)
from app.dominio.alerta import Alerta, RegraAlerta
from app.dominio.enums import Grandeza
from app.dominio.estacao import Estacao
from app.dominio.medicao import Medicao, SerieTemporal
from app.dominio.periodo import Periodo


class FonteStub(FonteDadosHidrologicos):
    def __init__(self, estacoes: list[Estacao], medicoes: list[Medicao]) -> None:
        self.estacoes = estacoes
        self.medicoes = medicoes
        self.chamadas: list[tuple[int, Periodo, datetime | None]] = []

    def listar_estacoes(self, filtro: FiltroEstacoes) -> list[Estacao]:
        return [e for e in self.estacoes if filtro.aceita(e)]

    def buscar_medicoes(self, codigo, periodo, alteradas_desde=None) -> list[Medicao]:
        self.chamadas.append((codigo, periodo, alteradas_desde))
        return [
            m
            for m in self.medicoes
            if m.codigo_estacao == codigo and periodo.contem(m.data_hora_utc)
        ]


class Estacoes(EstacaoRepositorio):
    def __init__(self) -> None:
        self.dados: dict[int, Estacao] = {}

    def salvar_varias(self, estacoes: Iterable[Estacao]) -> int:
        n = 0
        for e in estacoes:
            self.dados[e.codigo] = e
            n += 1
        return n

    def por_codigo(self, codigo: int) -> Estacao | None:
        return self.dados.get(codigo)

    def buscar(self, filtro: FiltroEstacoes) -> list[Estacao]:
        return [e for e in self.dados.values() if filtro.aceita(e)]

    def monitoradas(self) -> list[Estacao]:
        return [e for e in self.dados.values() if e.operando and e.telemetrica]


class Medicoes(MedicaoRepositorio):
    def __init__(self) -> None:
        self.dados: dict[tuple, Medicao] = {}

    def salvar_varias(self, medicoes: Iterable[Medicao]) -> int:
        n = 0
        for m in medicoes:
            self.dados[m.chave()] = m
            n += 1
        return n

    def serie(self, codigo: int, grandeza: Grandeza, periodo: Periodo) -> SerieTemporal:
        return SerieTemporal(
            codigo,
            grandeza,
            [
                m
                for m in self.dados.values()
                if m.codigo_estacao == codigo
                and m.grandeza() is grandeza
                and periodo.contem(m.data_hora_utc)
            ],
        )

    def ultima_atualizacao(self, codigo: int) -> datetime | None:
        datas = [m.data_hora_utc for m in self.dados.values() if m.codigo_estacao == codigo]
        return max(datas, default=None)


class Alertas(AlertaRepositorio):
    def __init__(self) -> None:
        self.dados: dict = {}

    def salvar(self, alerta: Alerta) -> None:
        self.dados[alerta.id] = alerta

    def ativo_da_estacao(self, codigo: int) -> Alerta | None:
        return next((a for a in self.ativos() if a.codigo_estacao == codigo), None)

    def ativos(self) -> list[Alerta]:
        return [a for a in self.dados.values() if a.ativo]


class Regras(RegraRepositorio):
    def __init__(self, regras: list[RegraAlerta]) -> None:
        self.regras = regras

    def da_estacao(self, codigo: int) -> list[RegraAlerta]:
        return [r for r in self.regras if r.codigo_estacao == codigo]
