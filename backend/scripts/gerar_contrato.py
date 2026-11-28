"""Gera o contrato da API (docs/contrato-api.md) e os mocks do front (frontend/src/mocks).

Sobe a aplicação com a `FonteFake` e um relógio fixo, chama cada rota pelo `TestClient`
e grava as respostas exatamente como a API as devolve. A documentação dos parâmetros e
dos campos sai do `/openapi.json`, então acompanha `app/api/schemas.py` sozinha.

Uso (a partir de `backend/`):

    uv run python -m scripts.gerar_contrato          # regrava os arquivos
    uv run python -m scripts.gerar_contrato --check  # só confere se estão em dia

`tests/test_contrato.py` roda o equivalente ao `--check`: se um schema ou uma rota mudar
sem regerar os arquivos, o teste falha.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.dependencias import criar_repositorios, montar_container
from app.infra.fontes.fake import FonteFake
from app.main import create_app

RAIZ = Path(__file__).resolve().parents[2]
PASTA_MOCKS = RAIZ / "frontend" / "src" / "mocks"
ARQUIVO_DOC = RAIZ / "docs" / "contrato-api.md"

# Instante fixo: as séries da FonteFake terminam aqui, então os mocks não mudam.
AGORA = datetime(2026, 1, 10, 12, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class Exemplo:
    arquivo: str
    url: str
    descricao: str
    status: int = 200


EXEMPLOS = (
    Exemplo("estacoes.json", "/estacoes", "Todas as estações, com a situação de cada uma."),
    Exemplo("estacoes-busca.json", "/estacoes?q=tiete", "Busca por nome, município ou rio."),
    Exemplo(
        "estacoes-proximas.json",
        "/estacoes/proximas?lat=-23.55&lon=-46.63&raio_km=100",
        "Estações num raio, da mais próxima para a mais distante.",
    ),
    Exemplo("estacao.json", "/estacoes/90000001", "Detalhe de uma estação em alerta."),
    Exemplo(
        "medicoes-nivel.json",
        "/estacoes/90000001/medicoes?grandeza=NIVEL",
        "Série de nível das últimas 24 h (padrão).",
    ),
    Exemplo(
        "medicoes-chuva.json",
        "/estacoes/90000004/medicoes?grandeza=CHUVA",
        "Série de chuva das últimas 24 h.",
    ),
    Exemplo(
        "chuva-mensal.json",
        "/estacoes/90000004/chuva-mensal",
        "Chuva do mês corrente comparada à normal do INMET mais próxima.",
    ),
    Exemplo(
        "limites-cota.json",
        "/estacoes/90000001/limites",
        "Limites de uma estação fluviométrica (cotas de referência).",
    ),
    Exemplo(
        "limites-chuva.json",
        "/estacoes/90000004/limites",
        "Limites de uma estação pluviométrica (chuva acumulada e previsão).",
    ),
    Exemplo("alertas.json", "/alertas", "Alertas ativos, do mais grave para o menos grave."),
    Exemplo(
        "alertas-estacao.json",
        "/estacoes/90000004/alertas",
        "Histórico de alertas (ativos e encerrados) de uma estação.",
    ),
    Exemplo(
        "municipio-situacao.json",
        "/municipios/RJ/Petr%C3%B3polis/situacao",
        "Situação de um município: a pior entre as suas estações.",
    ),
    Exemplo("metadados.json", "/metadados", "Origem dos dados servidos pela API."),
    Exemplo("erro-404.json", "/estacoes/1", "Recurso inexistente.", status=404),
    Exemplo(
        "erro-422.json",
        "/estacoes/proximas?lat=200&lon=0",
        "Parâmetro inválido: `detail` legível e `erros` detalhados.",
        status=422,
    ),
)


# --- Execução das rotas ------------------------------------------------------------


def _cliente() -> TestClient:
    def container():
        fonte = FonteFake(AGORA)
        repositorios = criar_repositorios("memoria", regras=fonte.regras_iniciais())
        return montar_container(fonte, relogio=lambda: AGORA, repositorios=repositorios)

    app = create_app(
        container,
        intervalo=lambda: None,
        origens=[],
    )
    return TestClient(app)


def _ids_estaveis(respostas: dict[str, Any]) -> dict[str, Any]:
    """Troca os UUIDs aleatórios dos alertas por ids fixos, na ordem em que aparecem.

    O mesmo alerta recebe o mesmo id em todos os arquivos.
    """
    mapa: dict[str, str] = {}

    def trocar(valor: Any) -> Any:
        if isinstance(valor, list):
            return [trocar(item) for item in valor]
        if not isinstance(valor, dict):
            return valor
        novo = {}
        for chave, item in valor.items():
            if chave == "id" and _e_uuid(item):
                item = mapa.setdefault(item, str(UUID(int=len(mapa) + 1)))
            novo[chave] = trocar(item)
        return novo

    return {nome: trocar(corpo) for nome, corpo in respostas.items()}


def _e_uuid(valor: Any) -> bool:
    if not isinstance(valor, str):
        return False
    try:
        UUID(valor)
    except ValueError:
        return False
    return True


def coletar_respostas() -> tuple[dict[str, Any], dict[str, Any]]:
    """Corpo de cada exemplo (por arquivo) e o documento OpenAPI."""
    respostas: dict[str, Any] = {}
    with _cliente() as cliente:
        for exemplo in EXEMPLOS:
            resposta = cliente.get(exemplo.url)
            if resposta.status_code != exemplo.status:
                raise RuntimeError(
                    f"{exemplo.url}: esperado {exemplo.status}, veio {resposta.status_code}"
                )
            respostas[exemplo.arquivo] = resposta.json()
        openapi = cliente.get("/openapi.json").json()
    return _ids_estaveis(respostas), openapi


# --- Documentação a partir do OpenAPI --------------------------------------------


def _nome_ref(ref: str) -> str:
    return ref.rsplit("/", 1)[-1]


def _tipo(schema: dict[str, Any]) -> str:
    if "$ref" in schema:
        nome = _nome_ref(schema["$ref"])
        return f"[`{nome}`](#{nome.lower()})"
    if "anyOf" in schema:
        partes = [s for s in schema["anyOf"] if s.get("type") != "null"]
        texto = " \\| ".join(_tipo(s) for s in partes)
        return f"{texto} \\| `null`" if len(partes) < len(schema["anyOf"]) else texto
    if schema.get("type") == "array":
        return f"lista de {_tipo(schema.get('items', {}))}"
    tipo = schema.get("type", "qualquer")
    formato = schema.get("format")
    return f"`{tipo}` ({formato})" if formato else f"`{tipo}`"


def _restricoes(schema: dict[str, Any]) -> str:
    rotulos = {
        "minimum": "≥",
        "exclusiveMinimum": ">",
        "maximum": "≤",
        "exclusiveMaximum": "<",
        "minLength": "tamanho ≥",
        "maxLength": "tamanho ≤",
    }
    alvo = schema
    if "anyOf" in schema:
        alvo = next((s for s in schema["anyOf"] if s.get("type") != "null"), {})
    return ", ".join(
        f"{rotulo} {alvo[chave]}" for chave, rotulo in rotulos.items() if chave in alvo
    )


def _celula(texto: str) -> str:
    return " ".join(texto.split()).replace("|", "\\|")


def _tabela_parametros(parametros: list[dict[str, Any]]) -> Iterator[str]:
    yield "| Parâmetro | Onde | Obrigatório | Tipo | Restrições | Padrão | Descrição |"
    yield "|---|---|---|---|---|---|---|"
    for p in parametros:
        schema = p.get("schema", {})
        padrao = f"`{json.dumps(schema['default'])}`" if "default" in schema else ""
        yield (
            f"| `{p['name']}` | {p['in']} | {'sim' if p.get('required') else 'não'} "
            f"| {_tipo(schema)} | {_restricoes(schema)} | {padrao} "
            f"| {_celula(p.get('description', ''))} |"
        )


def _resposta_ok(operacao: dict[str, Any]) -> str:
    schema = operacao["responses"]["200"]["content"]["application/json"]["schema"]
    return _tipo(schema)


def _trecho(valor: Any, itens: int = 1) -> Any:
    """Exemplo encurtado para o doc: listas de objetos ficam com os primeiros itens."""
    if isinstance(valor, list):
        if any(isinstance(v, dict) for v in valor):
            valor = valor[:itens]
        return [_trecho(v, itens) for v in valor]
    if isinstance(valor, dict):
        return {k: _trecho(v, 2 if k == "medicoes" else itens) for k, v in valor.items()}
    return valor


def _json(valor: Any) -> str:
    return json.dumps(valor, ensure_ascii=False, indent=2) + "\n"


def _caminho_do_exemplo(url: str) -> str:
    return url.split("?", 1)[0]


def _secao_rotas(openapi: dict[str, Any], respostas: dict[str, Any]) -> Iterator[str]:
    rota_de = {e.arquivo: _rota_do_exemplo(e.url, openapi["paths"]) for e in EXEMPLOS}

    yield "## Rotas"
    for caminho, metodos in openapi["paths"].items():
        for metodo, operacao in metodos.items():
            yield ""
            yield f"### `{metodo.upper()} {caminho}`"
            yield ""
            # Só a docstring da rota; o "summary" automático repete o nome da função.
            descricao = operacao.get("description", "")
            if descricao:
                yield _celula(descricao)
                yield ""
            if operacao.get("parameters"):
                yield from _tabela_parametros(operacao["parameters"])
                yield ""
            yield f"**Resposta 200:** {_resposta_ok(operacao)}"
            for exemplo in EXEMPLOS:
                if exemplo.status != 200 or rota_de[exemplo.arquivo] != caminho:
                    continue
                yield ""
                yield (
                    f"Exemplo: `GET {exemplo.url}`. {exemplo.descricao} "
                    f"Resposta completa em `frontend/src/mocks/{exemplo.arquivo}`; trecho:"
                )
                yield ""
                yield "```json"
                yield _json(_trecho(respostas[exemplo.arquivo])).rstrip("\n")
                yield "```"


def _rota_do_exemplo(url: str, caminhos: dict[str, Any]) -> str | None:
    """A rota que a URL chama; havendo empate, a com mais trechos fixos.

    `/estacoes/proximas` casa com `/estacoes/proximas` e com `/estacoes/{codigo}`, mas
    quem atende é a primeira, como no roteador do FastAPI.
    """
    partes_url = _caminho_do_exemplo(url).strip("/").split("/")
    melhor, melhor_fixos = None, -1
    for caminho in caminhos:
        partes_rota = caminho.strip("/").split("/")
        if len(partes_rota) != len(partes_url):
            continue
        pares = list(zip(partes_rota, partes_url, strict=True))
        if not all(r == u or r.startswith("{") for r, u in pares):
            continue
        fixos = sum(r == u for r, u in pares)
        if fixos > melhor_fixos:
            melhor, melhor_fixos = caminho, fixos
    return melhor


def _secao_schemas(openapi: dict[str, Any]) -> Iterator[str]:
    schemas = openapi["components"]["schemas"]
    ignorar = {"HTTPValidationError", "ValidationError"}  # substituídos pelo formato de erro
    yield "## Modelos"
    for nome, schema in sorted(schemas.items()):
        if nome in ignorar:
            continue
        yield ""
        yield f'<a id="{nome.lower()}"></a>'
        yield ""
        yield f"### `{nome}`"
        yield ""
        if "enum" in schema:
            yield "Valores: " + ", ".join(f"`{v}`" for v in schema["enum"]) + "."
            continue
        obrigatorios = set(schema.get("required", []))
        yield "| Campo | Tipo | Obrigatório |"
        yield "|---|---|---|"
        for campo, definicao in schema.get("properties", {}).items():
            obrigatorio = "sim" if campo in obrigatorios else "não"
            yield f"| `{campo}` | {_tipo(definicao)} | {obrigatorio} |"


def _secao_erros(respostas: dict[str, Any]) -> Iterator[str]:
    yield "## Erros"
    yield ""
    yield (
        'Toda resposta de erro tem o formato `{"detail": "<mensagem>"}` '
        "(`app/api/erros.py`). Erros de validação trazem também `erros`, a lista "
        "detalhada do FastAPI."
    )
    yield ""
    yield "| Status | Quando |"
    yield "|---|---|"
    yield "| 400 | Erro de regra da aplicação (`ErroAplicacao`). |"
    yield "| 404 | Estação ou município inexistente (`RecursoNaoEncontrado`). |"
    yield "| 422 | Parâmetro inválido ou dado que viola o domínio (`DadoInvalido`). |"
    yield "| 503 | Fonte externa (ANA) indisponível; vem com o cabeçalho `Retry-After`. |"
    for exemplo in EXEMPLOS:
        if exemplo.status == 200:
            continue
        yield ""
        yield (
            f"Exemplo {exemplo.status}: `GET {exemplo.url}` "
            f"(`frontend/src/mocks/{exemplo.arquivo}`):"
        )
        yield ""
        yield "```json"
        yield _json(respostas[exemplo.arquivo]).rstrip("\n")
        yield "```"


def gerar_doc(openapi: dict[str, Any], respostas: dict[str, Any]) -> str:
    linhas = [
        "# Contrato da API",
        "",
        "<!-- Gerado por backend/scripts/gerar_contrato.py; não edite à mão. -->",
        "",
        (
            "Formato das respostas da API do TaPoo, gerado a partir do `/openapi.json` e de "
            "chamadas reais à API com a `FonteFake` e o relógio fixo em "
            f"`{AGORA.isoformat()}`. Os mesmos exemplos, completos, estão em "
            "`frontend/src/mocks/`, para o front funcionar sem o backend."
        ),
        "",
        "Para regerar depois de mudar uma rota ou `backend/app/api/schemas.py`:",
        "",
        "```bash",
        "cd backend",
        "uv run python -m scripts.gerar_contrato",
        "```",
        "",
        (
            "Datas estão em ISO 8601 com fuso (UTC). Os `id` de alerta nos exemplos são "
            "fixos; na API real são UUIDs aleatórios."
        ),
        "",
        "## Mocks",
        "",
        "| Arquivo | Requisição | Status | Conteúdo |",
        "|---|---|---|---|",
    ]
    linhas += [f"| `{e.arquivo}` | `GET {e.url}` | {e.status} | {e.descricao} |" for e in EXEMPLOS]
    linhas.append("")
    linhas += _secao_rotas(openapi, respostas)
    linhas.append("")
    linhas += _secao_erros(respostas)
    linhas.append("")
    linhas += _secao_schemas(openapi)
    return "\n".join(linhas) + "\n"


# --- Arquivos -------------------------------------------------------------------------


def gerar_arquivos() -> dict[Path, str]:
    respostas, openapi = coletar_respostas()
    arquivos = {PASTA_MOCKS / nome: _json(corpo) for nome, corpo in respostas.items()}
    arquivos[ARQUIVO_DOC] = gerar_doc(openapi, respostas)
    return arquivos


def desatualizados(arquivos: dict[Path, str]) -> list[Path]:
    """Arquivos que faltam ou diferem do que o gerador produz agora, e mocks que sobraram."""
    diferentes = [
        caminho
        for caminho, conteudo in arquivos.items()
        if not caminho.is_file() or caminho.read_text(encoding="utf-8") != conteudo
    ]
    if PASTA_MOCKS.is_dir():
        diferentes += [p for p in sorted(PASTA_MOCKS.glob("*.json")) if p not in arquivos]
    return diferentes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="só confere, sem gravar")
    args = parser.parse_args(argv)

    arquivos = gerar_arquivos()
    if args.check:
        pendentes = desatualizados(arquivos)
        for caminho in pendentes:
            print(f"desatualizado: {caminho.relative_to(RAIZ)}", file=sys.stderr)
        return 1 if pendentes else 0

    PASTA_MOCKS.mkdir(parents=True, exist_ok=True)
    for sobra in sorted(PASTA_MOCKS.glob("*.json")):
        if sobra not in arquivos:
            sobra.unlink()
    for caminho, conteudo in arquivos.items():
        caminho.write_text(conteudo, encoding="utf-8")
        print(f"gravado: {caminho.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
