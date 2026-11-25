"""Fonte determinística para demonstrações, configurada pelo arquivo cenario-demo.json."""

import json
from datetime import datetime, timedelta
from math import sin
from pathlib import Path
from typing import Any

from app.aplicacao.filtros import FiltroEstacoes
from app.aplicacao.portas import FonteDadosHidrologicos
from app.dominio.alerta import (
    RegraAlerta,
    RegraChuvaAcumulada,
    RegraChuvaPrevisao,
    RegraCotaReferencia,
)
from app.dominio.enums import TipoEstacao
from app.dominio.estacao import Estacao
from app.dominio.geografia import Coordenada
from app.dominio.medicao import Medicao, MedicaoChuva, MedicaoNivel, MedicaoVazao
from app.dominio.periodo import Periodo
from app.dominio.tempo import agora_utc, exigir_utc

HISTORICO = timedelta(days=7)
ARQUIVO_CENARIO = Path(__file__).with_name("dados") / "cenario-demo.json"
_CLASSES_MEDICAO = {
    "chuva": MedicaoChuva,
    "nivel": MedicaoNivel,
    "vazao": MedicaoVazao,
}


def _ler_cenario(arquivo: Path = ARQUIVO_CENARIO) -> dict[str, Any]:
    try:
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as erro:
        raise RuntimeError(f"Não foi possível carregar o cenário simulado: {arquivo}.") from erro
    if not isinstance(dados, dict) or not isinstance(dados.get("estacoes"), list):
        raise RuntimeError("Cenário simulado inválido: informe a lista de estações.")
    return dados


def regras_de_exemplo(arquivo: Path = ARQUIVO_CENARIO) -> list[RegraAlerta]:
    """Lê as regras e limiares fictícios do mesmo cenário usado pela fonte simulada."""
    regras = []
    for item in _ler_cenario(arquivo).get("regras", []):
        tipo = item["tipo"]
        codigo = int(item["codigo_estacao"])
        janela = timedelta(hours=float(item.get("janela_horas", 24)))
        if tipo == "cota_referencia":
            regra = RegraCotaReferencia(
                codigo,
                float(item["cota_atencao_cm"]),
                float(item["cota_alerta_cm"]),
                float(item["cota_inundacao_cm"]),
            )
        elif tipo == "chuva_acumulada":
            regra = RegraChuvaAcumulada(codigo, janela, *_limites_chuva(item))
        elif tipo == "chuva_previsao":
            regra = RegraChuvaPrevisao(
                codigo,
                Coordenada(float(item["latitude"]), float(item["longitude"])),
                janela,
                *_limites_chuva(item),
            )
        else:
            raise RuntimeError(f"Tipo de regra desconhecido no cenário simulado: {tipo}.")
        regras.append(regra)
    return regras


Perfil = dict[str, Any]


class FonteSimulada(FonteDadosHidrologicos):
    """Gera séries horárias fictícias a partir dos perfis definidos em JSON."""

    def __init__(
        self,
        agora: datetime | None = None,
        *,
        arquivo: Path = ARQUIVO_CENARIO,
    ) -> None:
        self._agora = exigir_utc(agora or agora_utc()).replace(minute=0, second=0, microsecond=0)
        dados = _ler_cenario(arquivo)
        self._dados: list[tuple[Estacao, dict[str, Perfil]]] = []
        for item in dados["estacoes"]:
            codigo = int(item["codigo"])
            estacao = Estacao(
                codigo=codigo,
                nome=str(item["nome"]),
                tipo=TipoEstacao(item["tipo"]),
                coordenada=Coordenada(float(item["latitude"]), float(item["longitude"])),
                uf=str(item["uf"]),
                municipio=str(item["municipio"]),
                rio=item.get("rio"),
                operando=bool(item.get("operando", True)),
                telemetrica=bool(item.get("telemetrica", True)),
            )
            perfis = item.get("perfis", {})
            if not isinstance(perfis, dict) or not set(perfis).issubset(_CLASSES_MEDICAO):
                raise RuntimeError(f"Perfis de medição inválidos para a estação {codigo}.")
            self._dados.append((estacao, perfis))

    def listar_estacoes(self, filtro: FiltroEstacoes) -> list[Estacao]:
        return [estacao for estacao, _ in self._dados if filtro.aceita(estacao)]

    def buscar_estacao(self, codigo: int) -> Estacao | None:
        return next((estacao for estacao, _ in self._dados if estacao.codigo == codigo), None)

    def buscar_medicoes(
        self, codigo: int, periodo: Periodo, alteradas_desde: datetime | None = None
    ) -> list[Medicao]:
        perfis = next((perfis for estacao, perfis in self._dados if estacao.codigo == codigo), None)
        if perfis is None:
            return []
        medicoes = []
        for instante in self._horas(periodo):
            if alteradas_desde is not None and instante <= exigir_utc(alteradas_desde):
                continue
            horas_atras = (self._agora - instante) / timedelta(hours=1)
            for grandeza in perfis:
                valor = self._avaliar_perfil(perfis, grandeza, horas_atras)
                medicoes.append(
                    _CLASSES_MEDICAO[grandeza](
                        codigo,
                        instante,
                        valor,
                        atualizado_na_fonte_em=instante,
                    )
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

    @classmethod
    def _avaliar_perfil(cls, perfis: dict[str, Perfil], nome: str, horas_atras: float) -> float:
        perfil = perfis[nome]
        tipo = perfil["tipo"]
        if tipo == "linear":
            return max(
                float(perfil["minimo"]),
                float(perfil["valor_atual"]) - float(perfil["queda_por_hora"]) * horas_atras,
            )
        if tipo in ("senoide", "senoide_positiva"):
            valor = float(perfil.get("base", 0)) + float(perfil["amplitude"]) * sin(
                horas_atras / float(perfil["periodo_horas"])
            )
            if tipo == "senoide_positiva":
                valor = max(0.0, valor)
            casas = perfil.get("casas")
            return round(valor, int(casas)) if casas is not None else valor
        if tipo == "recente":
            chave = (
                "valor_recente"
                if horas_atras < float(perfil["horas_recentes"])
                else "valor_anterior"
            )
            return float(perfil[chave])
        if tipo == "constante":
            return float(perfil["valor"])
        if tipo == "vazao_por_nivel":
            nivel = cls._avaliar_perfil(perfis, str(perfil["perfil_nivel"]), horas_atras)
            valor = float(perfil["coeficiente"]) * nivel ** float(perfil["expoente"])
            return round(valor, int(perfil.get("casas", 1)))
        raise RuntimeError(f"Perfil desconhecido no cenário simulado: {tipo}.")


def _limites_chuva(item: dict[str, Any]) -> tuple[float, float, float]:
    return (
        float(item["limite_moderado_mm"]),
        float(item["limite_alto_mm"]),
        float(item["limite_extremo_mm"]),
    )
