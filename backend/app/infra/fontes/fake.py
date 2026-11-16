"""Fonte de dados de exemplo, no lugar da ANA enquanto o adaptador real não existe.

Implementa a mesma porta (`FonteDadosHidrologicos`) que o futuro `FonteAna`. As estações
são FICTÍCIAS (códigos 9000000x), posicionadas em cidades reais só para o mapa fazer
sentido. As séries são horárias e determinísticas, terminando em `agora`, e foram
montadas para cobrir cenários de alerta:

- 90000001 (SP, fluviométrica): rio subindo até a faixa de ALERTA;
- 90000002 (SP, pluviométrica): chuva fraca, NORMAL;
- 90000003 (MG, fluviométrica): rio estável, NORMAL;
- 90000004 (RJ, pluviométrica): chuva forte nas últimas 24 h, EMERGENCIA;
- 90000005 (MG, pluviométrica convencional): não telemétrica, sem coleta automática.
"""

from collections.abc import Callable
from datetime import datetime, timedelta
from math import sin

from app.aplicacao.filtros import FiltroEstacoes
from app.aplicacao.portas import FonteDadosHidrologicos
from app.dominio.alerta import RegraAlerta, RegraChuvaAcumulada, RegraCotaReferencia
from app.dominio.enums import TipoEstacao
from app.dominio.estacao import Estacao
from app.dominio.geografia import Coordenada
from app.dominio.medicao import Medicao, MedicaoChuva, MedicaoNivel, MedicaoVazao
from app.dominio.periodo import Periodo
from app.dominio.tempo import agora_utc, exigir_utc

HISTORICO = timedelta(days=7)

# Perfis: função de "horas antes de agora" -> valor.
Perfil = Callable[[float], float]


def _rio_subindo(h: float) -> float:
    return max(250.0, 440.0 - 4.0 * h)  # cm; chega a 440 cm agora


def _rio_estavel(h: float) -> float:
    return 150.0 + 5.0 * sin(h / 6)


def _chuva_fraca(h: float) -> float:
    return round(max(0.0, 0.6 * sin(h / 3)), 1)


def _chuva_forte_recente(h: float) -> float:
    return 4.0 if h < 24 else 0.2  # 96 mm nas últimas 24 h


def _sem_chuva(h: float) -> float:
    return 0.0


def _vazao_de(nivel: Perfil) -> Perfil:
    return lambda h: round(0.002 * nivel(h) ** 1.5, 1)  # curva-chave fictícia


def _estacoes_e_perfis() -> list[tuple[Estacao, dict[type[Medicao], Perfil]]]:
    def estacao(codigo, nome, tipo, lat, lon, uf, municipio, rio=None, telemetrica=True):
        return Estacao(
            codigo,
            nome,
            tipo,
            Coordenada(lat, lon),
            uf,
            municipio,
            rio=rio,
            telemetrica=telemetrica,
        )

    fluvio, pluvio = TipoEstacao.FLUVIOMETRICA, TipoEstacao.PLUVIOMETRICA
    return [
        (
            estacao(
                90000001,
                "Rio Tietê - São Paulo (exemplo)",
                fluvio,
                -23.52,
                -46.63,
                "SP",
                "São Paulo",
                rio="Rio Tietê",
            ),
            {
                MedicaoNivel: _rio_subindo,
                MedicaoVazao: _vazao_de(_rio_subindo),
                MedicaoChuva: _chuva_fraca,
            },
        ),
        (
            estacao(90000002, "Campinas (exemplo)", pluvio, -22.91, -47.06, "SP", "Campinas"),
            {MedicaoChuva: _chuva_fraca},
        ),
        (
            estacao(
                90000003,
                "Rio das Velhas - Belo Horizonte (exemplo)",
                fluvio,
                -19.92,
                -43.94,
                "MG",
                "Belo Horizonte",
                rio="Rio das Velhas",
            ),
            {
                MedicaoNivel: _rio_estavel,
                MedicaoVazao: _vazao_de(_rio_estavel),
                MedicaoChuva: _sem_chuva,
            },
        ),
        (
            estacao(90000004, "Petrópolis (exemplo)", pluvio, -22.51, -43.18, "RJ", "Petrópolis"),
            {MedicaoChuva: _chuva_forte_recente},
        ),
        (
            estacao(
                90000005,
                "Ouro Preto (exemplo)",
                pluvio,
                -20.39,
                -43.50,
                "MG",
                "Ouro Preto",
                telemetrica=False,
            ),
            {MedicaoChuva: _sem_chuva},
        ),
    ]


def regras_de_exemplo() -> list[RegraAlerta]:
    """Cotas e limites fictícios; no TaPoo real são configurados por estação."""
    chuva_24h = {
        "janela": timedelta(hours=24),
        "limite_moderado_mm": 30,
        "limite_alto_mm": 50,
        "limite_extremo_mm": 80,
    }
    return [
        RegraCotaReferencia(
            90000001, cota_atencao_cm=300, cota_alerta_cm=400, cota_inundacao_cm=500
        ),
        RegraChuvaAcumulada(90000002, **chuva_24h),
        RegraCotaReferencia(
            90000003, cota_atencao_cm=250, cota_alerta_cm=320, cota_inundacao_cm=400
        ),
        RegraChuvaAcumulada(90000004, **chuva_24h),
    ]


class FonteFake(FonteDadosHidrologicos):
    def __init__(self, agora: datetime | None = None) -> None:
        agora = exigir_utc(agora or agora_utc())
        self._agora = agora.replace(minute=0, second=0, microsecond=0)
        self._dados = _estacoes_e_perfis()

    def listar_estacoes(self, filtro: FiltroEstacoes) -> list[Estacao]:
        return [estacao for estacao, _ in self._dados if filtro.aceita(estacao)]

    def buscar_medicoes(
        self, codigo: int, periodo: Periodo, alteradas_desde: datetime | None = None
    ) -> list[Medicao]:
        perfis = next((p for e, p in self._dados if e.codigo == codigo), None)
        if perfis is None:
            return []
        medicoes: list[Medicao] = []
        for instante in self._horas(periodo):
            if alteradas_desde is not None and instante <= alteradas_desde:
                continue
            horas_atras = (self._agora - instante) / timedelta(hours=1)
            for classe, perfil in perfis.items():
                medicoes.append(
                    classe(codigo, instante, perfil(horas_atras), atualizado_na_fonte_em=instante)
                )
        return medicoes

    def _horas(self, periodo: Periodo) -> list[datetime]:
        inicio = max(periodo.inicio, self._agora - HISTORICO)
        fim = min(periodo.fim, self._agora)
        atual = inicio.replace(minute=0, second=0, microsecond=0)
        if atual < inicio:
            atual += timedelta(hours=1)
        horas = []
        while atual <= fim:
            horas.append(atual)
            atual += timedelta(hours=1)
        return horas
