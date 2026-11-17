"""Adaptador de leitura da API HidroWebService da ANA."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from app.aplicacao.filtros import FiltroEstacoes
from app.aplicacao.portas import FonteDadosHidrologicos
from app.dominio.enums import NivelConsistencia, TipoEstacao
from app.dominio.estacao import Estacao
from app.dominio.geografia import Coordenada
from app.dominio.medicao import Medicao, MedicaoChuva, MedicaoNivel, MedicaoVazao
from app.dominio.periodo import Periodo
from app.dominio.tempo import exigir_utc

_BASE_URL_PADRAO = "https://www.ana.gov.br/hidrowebservice/EstacoesTelemetricas"
_UFS = (
    "AC",
    "AL",
    "AM",
    "AP",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MG",
    "MS",
    "MT",
    "PA",
    "PB",
    "PE",
    "PI",
    "PR",
    "RJ",
    "RN",
    "RO",
    "RR",
    "RS",
    "SC",
    "SE",
    "SP",
    "TO",
)
_FORMATOS_DATA_ANA = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
)
_FUSO_ANA = ZoneInfo("America/Sao_Paulo")


class ErroFonteAna(RuntimeError):
    """Falha de autenticação, comunicação ou interpretação da resposta da ANA."""


class FonteAna(FonteDadosHidrologicos):
    """Consulta inventário e séries telemétricas adotadas da ANA.

    A sessão é renovada somente quando o token expira. Credenciais são recebidas em
    tempo de execução e nunca incluídas em mensagens de erro.
    """

    def __init__(
        self,
        identificador: str,
        senha: str,
        *,
        base_url: str = _BASE_URL_PADRAO,
        timeout: float = 20.0,
    ) -> None:
        if not identificador.strip() or not senha.strip():
            raise ValueError("identificador e senha da ANA são obrigatórios")
        self._identificador = identificador.strip()
        self._senha = senha
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._token: str | None = None
        self._token_expira_em: datetime | None = None
        self._estacoes_por_uf: dict[str, list[Estacao]] = {}

    def listar_estacoes(self, filtro: FiltroEstacoes) -> list[Estacao]:
        ufs = (filtro.uf.upper(),) if filtro.uf else _UFS
        por_codigo: dict[int, Estacao] = {}
        for uf in ufs:
            if uf not in self._estacoes_por_uf:
                resposta = self._get("HidroInventarioEstacoes/v1", {"Unidade Federativa": uf})
                estacoes_uf = []
                for item in self._itens(resposta):
                    try:
                        estacoes_uf.append(self._mapear_estacao(item))
                    except (KeyError, TypeError, ValueError):
                        # Registros incompletos ou sem coordenadas não vão ao mapa.
                        continue
                self._estacoes_por_uf[uf] = estacoes_uf
            for estacao in self._estacoes_por_uf[uf]:
                if filtro.aceita(estacao):
                    por_codigo[estacao.codigo] = estacao
        return sorted(por_codigo.values(), key=lambda estacao: (estacao.uf, estacao.nome))

    def buscar_medicoes(
        self, codigo: int, periodo: Periodo, alteradas_desde: datetime | None = None
    ) -> list[Medicao]:
        del alteradas_desde  # A consulta da ANA é delimitada pelo período de leitura.
        periodo = Periodo(exigir_utc(periodo.inicio), exigir_utc(periodo.fim))
        medicoes: dict[tuple[int, str, datetime], Medicao] = {}
        cursor = periodo.fim
        while cursor >= periodo.inicio:
            inicio_janela = max(periodo.inicio, cursor - timedelta(days=29))
            dias = max(1, (cursor.date() - inicio_janela.date()).days + 1)
            range_busca = self._range_api(dias)
            resposta = self._get(
                "HidroinfoanaSerieTelemetricaAdotada/v1",
                {
                    "Código da Estação": codigo,
                    "Tipo Filtro Data": "DATA_LEITURA",
                    "Data de Busca (yyyy-MM-dd)": cursor.date().isoformat(),
                    "Range Intervalo de busca": range_busca,
                },
            )
            for item in self._itens(resposta):
                for medicao in self._mapear_medicoes(codigo, item):
                    if periodo.contem(medicao.data_hora_utc):
                        chave = (codigo, medicao.grandeza().value, medicao.data_hora_utc)
                        medicoes[chave] = medicao
            if inicio_janela <= periodo.inicio:
                break
            cursor = inicio_janela - timedelta(seconds=1)
        return sorted(medicoes.values(), key=lambda medicao: medicao.data_hora_utc)

    def _get(self, rota: str, parametros: dict[str, Any] | None = None) -> Any:
        token = self._obter_token()
        url = f"{self._base_url}/{rota}"
        if parametros:
            url = f"{url}?{urlencode(parametros)}"
        requisicao = Request(url, headers={"Authorization": f"Bearer {token}"})
        try:
            with urlopen(requisicao, timeout=self._timeout) as resposta:
                dados = json.loads(resposta.read().decode("utf-8"))
        except TimeoutError as erro:
            raise ErroFonteAna(
                f"A ANA não respondeu à consulta em {self._timeout:g} segundos."
            ) from erro
        except (HTTPError, URLError, OSError, json.JSONDecodeError) as erro:
            raise ErroFonteAna("A consulta à API da ANA falhou.") from erro
        if isinstance(dados, dict) and dados.get("status") not in (None, "OK"):
            raise ErroFonteAna("A ANA retornou uma resposta de erro.")
        return dados

    def _obter_token(self) -> str:
        agora = datetime.now(UTC)
        if self._token and self._token_expira_em and agora < self._token_expira_em:
            return self._token

        requisicao = Request(
            # A rota publicada no Swagger usa esta capitalização não convencional.
            f"{self._base_url}/OAUth/v1",
            headers={"Identificador": self._identificador, "Senha": self._senha},
        )
        try:
            with urlopen(requisicao, timeout=self._timeout) as resposta:
                dados = json.loads(resposta.read().decode("utf-8"))
        except TimeoutError as erro:
            raise ErroFonteAna(
                f"A ANA não respondeu à autenticação em {self._timeout:g} segundos."
            ) from erro
        except (HTTPError, URLError, OSError, json.JSONDecodeError) as erro:
            raise ErroFonteAna("Não foi possível autenticar na API da ANA.") from erro

        items = dados.get("items", {}) if isinstance(dados, dict) else {}
        if isinstance(items, list):
            items = items[0] if items else {}
        token = items.get("tokenautenticacao") if isinstance(items, dict) else None
        if not token:
            raise ErroFonteAna("A autenticação da ANA não retornou um token válido.")

        self._token = str(token)
        validade = items.get("validade")
        self._token_expira_em = self._interpretar_validade(validade) or (
            agora + timedelta(minutes=55)
        )
        return self._token

    @staticmethod
    def _itens(resposta: Any) -> list[dict[str, Any]]:
        if isinstance(resposta, list):
            return [item for item in resposta if isinstance(item, dict)]
        if not isinstance(resposta, dict):
            return []
        items = resposta.get("items", [])
        if isinstance(items, dict):
            return [items]
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
        return []

    @staticmethod
    def _mapear_estacao(item: dict[str, Any]) -> Estacao:
        tipo_texto = str(item.get("Tipo_Estacao", "")).casefold()
        if "fluvi" in tipo_texto:
            tipo = TipoEstacao.FLUVIOMETRICA
        elif "pluv" in tipo_texto:
            tipo = TipoEstacao.PLUVIOMETRICA
        else:
            raise ValueError("tipo de estação desconhecido")

        codigo = int(item["codigoestacao"])
        latitude, longitude = float(item["Latitude"]), float(item["Longitude"])
        inicio_telemetria = item.get("Data_Periodo_Telemetrica_Inicio")
        telemetrica = inicio_telemetria not in (None, "", "0")
        return Estacao(
            codigo=codigo,
            nome=str(item.get("Estacao_Nome") or f"Estação {codigo}").strip(),
            tipo=tipo,
            coordenada=Coordenada(latitude, longitude),
            uf=str(item.get("UF_Estacao") or "").upper(),
            municipio=str(item.get("Municipio_Nome") or "Não informado").strip(),
            rio=item.get("Rio_Nome") or item.get("Rio"),
            operando=str(item.get("Operando", "1")) == "1",
            telemetrica=telemetrica,
        )

    @classmethod
    def _mapear_medicoes(cls, codigo: int, item: dict[str, Any]) -> list[Medicao]:
        data_hora = cls._data_hora(item.get("Data_Hora_Medicao"))
        atualizacao = cls._data_hora(item.get("Data_Atualizacao"), obrigatoria=False)
        medicoes: list[Medicao] = []
        for campo, classe, status_campo in (
            ("Chuva_Adotada", MedicaoChuva, "Chuva_Adotada_Status"),
            ("Cota_Adotada", MedicaoNivel, "Cota_Adotada_Status"),
            ("Vazao_Adotada", MedicaoVazao, "Vazao_Adotada_Status"),
        ):
            valor = item.get(campo)
            if valor in (None, ""):
                continue
            status_fonte = str(item.get(status_campo, "")) or None
            consistencia = (
                NivelConsistencia.CONSISTIDO
                if status_fonte in (None, "0")
                else NivelConsistencia.BRUTO
            )
            medicoes.append(
                classe(
                    codigo_estacao=codigo,
                    data_hora_utc=data_hora,
                    valor=float(valor),
                    consistencia=consistencia,
                    status_fonte=status_fonte,
                    atualizado_na_fonte_em=atualizacao,
                )
            )
        return medicoes

    @staticmethod
    def _data_hora(valor: Any, *, obrigatoria: bool = True) -> datetime | None:
        if valor in (None, ""):
            if obrigatoria:
                raise ValueError("resposta da ANA sem data da medição")
            return None
        texto = str(valor).strip()
        for formato in _FORMATOS_DATA_ANA:
            try:
                data = datetime.strptime(texto, formato)
                # A ANA fornece os campos de data sem offset; interpretamos como hora
                # oficial de Brasília e normalizamos para UTC, conforme o domínio.
                return data.replace(tzinfo=_FUSO_ANA).astimezone(UTC)
            except ValueError:
                continue
        try:
            data = datetime.fromisoformat(texto)
            return exigir_utc(data)
        except ValueError as erro:
            raise ValueError("data da ANA em formato desconhecido") from erro

    @staticmethod
    def _interpretar_validade(valor: Any) -> datetime | None:
        if not valor:
            return None
        texto = str(valor).replace("GMT", "")
        for formato in ("%a %b %d %H:%M:%S %z %Y", "%Y-%m-%dT%H:%M:%S%z"):
            try:
                data = datetime.strptime(texto, formato)
                return exigir_utc(data) - timedelta(minutes=2)
            except ValueError:
                continue
        return None

    @staticmethod
    def _range_api(dias: int) -> str:
        opcoes = (1, 2, 7, 14, 21, 30)
        dias_escolhidos = next((opcao for opcao in opcoes if opcao >= dias), 30)
        return "HORA_24" if dias_escolhidos == 1 else f"DIAS_{dias_escolhidos}"
