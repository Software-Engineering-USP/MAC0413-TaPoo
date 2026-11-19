"""Composição da aplicação: liga as portas às implementações concretas.

É o único lugar que conhece `app.infra`. Trocar memória por SQL, ou `FonteFake` por
`FonteAna`, muda só este arquivo.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated

from fastapi import Depends, Request

from app.aplicacao.coleta import ColetarMedicoes
from app.aplicacao.consulta import ConsultarDados
from app.aplicacao.monitoramento import MonitorarEstacoes
from app.aplicacao.portas import FonteDadosHidrologicos
from app.aplicacao.sincronizacao import SincronizarEstacoes
from app.configuracao import base_url_ana, credenciais_ana, timeout_ana
from app.dominio.tempo import agora_utc
from app.infra.fontes.ana import FonteAna
from app.infra.fontes.fake import FonteFake, regras_de_exemplo
from app.infra.memoria.repositorios import (
    AlertaRepositorioMemoria,
    EstacaoRepositorioMemoria,
    MedicaoRepositorioMemoria,
    RegraRepositorioMemoria,
)


@dataclass(frozen=True, slots=True)
class Container:
    consulta: ConsultarDados
    sincronizar: SincronizarEstacoes
    coletar: ColetarMedicoes
    relogio: Callable[[], datetime]
    carregar_na_inicializacao: bool = True


def montar_container(
    fonte: FonteDadosHidrologicos | None = None,
    relogio: Callable[[], datetime] = agora_utc,
) -> Container:
    if fonte is None:
        credenciais = credenciais_ana()
        fonte = (
            FonteAna(
                *credenciais,
                base_url=base_url_ana(),
                timeout=timeout_ana(),
            )
            if credenciais
            else FonteFake(relogio())
        )
    estacoes = EstacaoRepositorioMemoria()
    medicoes = MedicaoRepositorioMemoria()
    alertas = AlertaRepositorioMemoria()
    regras = RegraRepositorioMemoria(regras_de_exemplo())

    monitorar = MonitorarEstacoes(medicoes, regras, alertas, relogio=relogio)
    return Container(
        consulta=ConsultarDados(estacoes, medicoes, alertas),
        sincronizar=SincronizarEstacoes(fonte, estacoes),
        coletar=ColetarMedicoes(fonte, estacoes, medicoes, monitorar, relogio=relogio),
        relogio=relogio,
        carregar_na_inicializacao=fonte.carregar_na_inicializacao,
    )


def carga_inicial(container: Container) -> None:
    """Sincroniza estações; fontes pequenas também carregam séries de exemplo."""
    if container.carregar_na_inicializacao:
        container.sincronizar.executar()
        container.coletar.executar_todas()


def _container(request: Request) -> Container:
    return request.app.state.container


def get_consulta(request: Request) -> ConsultarDados:
    return _container(request).consulta


def get_relogio(request: Request) -> Callable[[], datetime]:
    return _container(request).relogio


def get_coletar(request: Request) -> ColetarMedicoes:
    return _container(request).coletar


def get_sincronizar(request: Request) -> SincronizarEstacoes:
    return _container(request).sincronizar


Consulta = Annotated[ConsultarDados, Depends(get_consulta)]
Relogio = Annotated[Callable[[], datetime], Depends(get_relogio)]
Coletar = Annotated[ColetarMedicoes, Depends(get_coletar)]
Sincronizar = Annotated[SincronizarEstacoes, Depends(get_sincronizar)]
