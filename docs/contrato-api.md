# Contrato da API

<!-- Gerado por backend/scripts/gerar_contrato.py; não edite à mão. -->

Formato das respostas da API do TaPoo, gerado a partir do `/openapi.json` e de chamadas reais à API com a `FonteFake` e o relógio fixo em `2026-01-10T12:00:00+00:00`. Os mesmos exemplos, completos, estão em `frontend/src/mocks/`, para o front funcionar sem o backend.

Para regerar depois de mudar uma rota ou `backend/app/api/schemas.py`:

```bash
cd backend
uv run python -m scripts.gerar_contrato
```

Datas estão em ISO 8601 com fuso (UTC). Os `id` de alerta nos exemplos são fixos; na API real são UUIDs aleatórios.

## Mocks

| Arquivo | Requisição | Status | Conteúdo |
|---|---|---|---|
| `estacoes.json` | `GET /estacoes` | 200 | Todas as estações, com a situação de cada uma. |
| `estacoes-busca.json` | `GET /estacoes?q=tiete` | 200 | Busca por nome, município ou rio. |
| `estacoes-proximas.json` | `GET /estacoes/proximas?lat=-23.55&lon=-46.63&raio_km=100` | 200 | Estações num raio, da mais próxima para a mais distante. |
| `estacao.json` | `GET /estacoes/90000001` | 200 | Detalhe de uma estação em alerta. |
| `medicoes-nivel.json` | `GET /estacoes/90000001/medicoes?grandeza=NIVEL` | 200 | Série de nível das últimas 24 h (padrão). |
| `medicoes-chuva.json` | `GET /estacoes/90000004/medicoes?grandeza=CHUVA` | 200 | Série de chuva das últimas 24 h. |
| `alertas.json` | `GET /alertas` | 200 | Alertas ativos, do mais grave para o menos grave. |
| `alertas-estacao.json` | `GET /estacoes/90000004/alertas` | 200 | Histórico de alertas (ativos e encerrados) de uma estação. |
| `municipio-situacao.json` | `GET /municipios/RJ/Petr%C3%B3polis/situacao` | 200 | Situação de um município: a pior entre as suas estações. |
| `erro-404.json` | `GET /estacoes/1` | 404 | Recurso inexistente. |
| `erro-422.json` | `GET /estacoes/proximas?lat=200&lon=0` | 422 | Parâmetro inválido: `detail` legível e `erros` detalhados. |

## Rotas

### `GET /health`

**Resposta 200:** `object`

### `GET /estacoes`

| Parâmetro | Onde | Obrigatório | Tipo | Restrições | Padrão | Descrição |
|---|---|---|---|---|---|---|
| `uf` | query | não | `string` \| `null` | tamanho ≥ 2, tamanho ≤ 2 |  |  |
| `tipo` | query | não | [`TipoEstacao`](#tipoestacao) \| `null` |  |  |  |
| `apenas_telemetricas` | query | não | `boolean` |  | `false` |  |
| `q` | query | não | `string` \| `null` | tamanho ≥ 2, tamanho ≤ 100 |  | Busca por nome da estação, município ou rio (sem acento e maiúsculas). |

**Resposta 200:** lista de [`EstacaoOut`](#estacaoout)

Exemplo: `GET /estacoes`. Todas as estações, com a situação de cada uma. Resposta completa em `frontend/src/mocks/estacoes.json`; trecho:

```json
[
  {
    "codigo": 90000001,
    "nome": "Rio Tietê - São Paulo (exemplo)",
    "tipo": "FLUVIOMETRICA",
    "latitude": -23.52,
    "longitude": -46.63,
    "uf": "SP",
    "municipio": "São Paulo",
    "rio": "Rio Tietê",
    "operando": true,
    "telemetrica": true,
    "grandezas": [
      "CHUVA",
      "NIVEL",
      "VAZAO"
    ],
    "severidade": "ALERTA",
    "severidade_rotulo": "Alerta",
    "alerta": {
      "id": "00000000-0000-0000-0000-000000000001",
      "codigo_estacao": 90000001,
      "severidade": "ALERTA",
      "severidade_rotulo": "Alerta",
      "status": "ATIVO",
      "mensagem": "Rio acima da cota de alerta (440 cm, limite 400 cm)",
      "fatores": [
        {
          "descricao": "Rio acima da cota de alerta (440 cm, limite 400 cm)",
          "severidade": "ALERTA",
          "severidade_rotulo": "Alerta"
        }
      ],
      "emitido_em": "2026-01-10T12:00:00Z",
      "encerrado_em": null
    }
  }
]
```

Exemplo: `GET /estacoes?q=tiete`. Busca por nome, município ou rio. Resposta completa em `frontend/src/mocks/estacoes-busca.json`; trecho:

```json
[
  {
    "codigo": 90000001,
    "nome": "Rio Tietê - São Paulo (exemplo)",
    "tipo": "FLUVIOMETRICA",
    "latitude": -23.52,
    "longitude": -46.63,
    "uf": "SP",
    "municipio": "São Paulo",
    "rio": "Rio Tietê",
    "operando": true,
    "telemetrica": true,
    "grandezas": [
      "CHUVA",
      "NIVEL",
      "VAZAO"
    ],
    "severidade": "ALERTA",
    "severidade_rotulo": "Alerta",
    "alerta": {
      "id": "00000000-0000-0000-0000-000000000001",
      "codigo_estacao": 90000001,
      "severidade": "ALERTA",
      "severidade_rotulo": "Alerta",
      "status": "ATIVO",
      "mensagem": "Rio acima da cota de alerta (440 cm, limite 400 cm)",
      "fatores": [
        {
          "descricao": "Rio acima da cota de alerta (440 cm, limite 400 cm)",
          "severidade": "ALERTA",
          "severidade_rotulo": "Alerta"
        }
      ],
      "emitido_em": "2026-01-10T12:00:00Z",
      "encerrado_em": null
    }
  }
]
```

### `GET /estacoes/proximas`

| Parâmetro | Onde | Obrigatório | Tipo | Restrições | Padrão | Descrição |
|---|---|---|---|---|---|---|
| `lat` | query | sim | `number` | ≥ -90, ≤ 90 |  |  |
| `lon` | query | sim | `number` | ≥ -180, ≤ 180 |  |  |
| `raio_km` | query | não | `number` | > 0, ≤ 1000 | `50` |  |

**Resposta 200:** lista de [`EstacaoProximaOut`](#estacaoproximaout)

Exemplo: `GET /estacoes/proximas?lat=-23.55&lon=-46.63&raio_km=100`. Estações num raio, da mais próxima para a mais distante. Resposta completa em `frontend/src/mocks/estacoes-proximas.json`; trecho:

```json
[
  {
    "codigo": 90000001,
    "nome": "Rio Tietê - São Paulo (exemplo)",
    "tipo": "FLUVIOMETRICA",
    "latitude": -23.52,
    "longitude": -46.63,
    "uf": "SP",
    "municipio": "São Paulo",
    "rio": "Rio Tietê",
    "operando": true,
    "telemetrica": true,
    "grandezas": [
      "CHUVA",
      "NIVEL",
      "VAZAO"
    ],
    "severidade": "ALERTA",
    "severidade_rotulo": "Alerta",
    "alerta": {
      "id": "00000000-0000-0000-0000-000000000001",
      "codigo_estacao": 90000001,
      "severidade": "ALERTA",
      "severidade_rotulo": "Alerta",
      "status": "ATIVO",
      "mensagem": "Rio acima da cota de alerta (440 cm, limite 400 cm)",
      "fatores": [
        {
          "descricao": "Rio acima da cota de alerta (440 cm, limite 400 cm)",
          "severidade": "ALERTA",
          "severidade_rotulo": "Alerta"
        }
      ],
      "emitido_em": "2026-01-10T12:00:00Z",
      "encerrado_em": null
    },
    "distancia_km": 3.34
  }
]
```

### `GET /estacoes/{codigo}`

| Parâmetro | Onde | Obrigatório | Tipo | Restrições | Padrão | Descrição |
|---|---|---|---|---|---|---|
| `codigo` | path | sim | `integer` |  |  |  |

**Resposta 200:** [`EstacaoOut`](#estacaoout)

Exemplo: `GET /estacoes/90000001`. Detalhe de uma estação em alerta. Resposta completa em `frontend/src/mocks/estacao.json`; trecho:

```json
{
  "codigo": 90000001,
  "nome": "Rio Tietê - São Paulo (exemplo)",
  "tipo": "FLUVIOMETRICA",
  "latitude": -23.52,
  "longitude": -46.63,
  "uf": "SP",
  "municipio": "São Paulo",
  "rio": "Rio Tietê",
  "operando": true,
  "telemetrica": true,
  "grandezas": [
    "CHUVA",
    "NIVEL",
    "VAZAO"
  ],
  "severidade": "ALERTA",
  "severidade_rotulo": "Alerta",
  "alerta": {
    "id": "00000000-0000-0000-0000-000000000001",
    "codigo_estacao": 90000001,
    "severidade": "ALERTA",
    "severidade_rotulo": "Alerta",
    "status": "ATIVO",
    "mensagem": "Rio acima da cota de alerta (440 cm, limite 400 cm)",
    "fatores": [
      {
        "descricao": "Rio acima da cota de alerta (440 cm, limite 400 cm)",
        "severidade": "ALERTA",
        "severidade_rotulo": "Alerta"
      }
    ],
    "emitido_em": "2026-01-10T12:00:00Z",
    "encerrado_em": null
  }
}
```

### `GET /estacoes/{codigo}/medicoes`

| Parâmetro | Onde | Obrigatório | Tipo | Restrições | Padrão | Descrição |
|---|---|---|---|---|---|---|
| `codigo` | path | sim | `integer` |  |  |  |
| `grandeza` | query | sim | [`Grandeza`](#grandeza) |  |  |  |
| `inicio` | query | não | `string` (date-time) \| `null` |  |  | ISO 8601 com fuso |
| `fim` | query | não | `string` (date-time) \| `null` |  |  | ISO 8601 com fuso |

**Resposta 200:** [`SerieOut`](#serieout)

Exemplo: `GET /estacoes/90000001/medicoes?grandeza=NIVEL`. Série de nível das últimas 24 h (padrão). Resposta completa em `frontend/src/mocks/medicoes-nivel.json`; trecho:

```json
{
  "codigo_estacao": 90000001,
  "grandeza": "NIVEL",
  "grandeza_rotulo": "Nível",
  "unidade": "cm",
  "inicio": "2026-01-09T12:00:00Z",
  "fim": "2026-01-10T12:00:00Z",
  "medicoes": [
    {
      "data_hora_utc": "2026-01-09T12:00:00Z",
      "valor": 344.0,
      "consistencia": "BRUTO",
      "status_fonte": null
    },
    {
      "data_hora_utc": "2026-01-09T13:00:00Z",
      "valor": 348.0,
      "consistencia": "BRUTO",
      "status_fonte": null
    }
  ]
}
```

Exemplo: `GET /estacoes/90000004/medicoes?grandeza=CHUVA`. Série de chuva das últimas 24 h. Resposta completa em `frontend/src/mocks/medicoes-chuva.json`; trecho:

```json
{
  "codigo_estacao": 90000004,
  "grandeza": "CHUVA",
  "grandeza_rotulo": "Chuva",
  "unidade": "mm",
  "inicio": "2026-01-09T12:00:00Z",
  "fim": "2026-01-10T12:00:00Z",
  "medicoes": [
    {
      "data_hora_utc": "2026-01-09T12:00:00Z",
      "valor": 0.2,
      "consistencia": "BRUTO",
      "status_fonte": null
    },
    {
      "data_hora_utc": "2026-01-09T13:00:00Z",
      "valor": 4.0,
      "consistencia": "BRUTO",
      "status_fonte": null
    }
  ]
}
```

### `GET /estacoes/{codigo}/alertas`

Alertas ativos e encerrados da estação, do mais recente para o mais antigo.

| Parâmetro | Onde | Obrigatório | Tipo | Restrições | Padrão | Descrição |
|---|---|---|---|---|---|---|
| `codigo` | path | sim | `integer` |  |  |  |
| `limite` | query | não | `integer` | ≥ 1, ≤ 500 | `50` |  |

**Resposta 200:** lista de [`AlertaOut`](#alertaout)

Exemplo: `GET /estacoes/90000004/alertas`. Histórico de alertas (ativos e encerrados) de uma estação. Resposta completa em `frontend/src/mocks/alertas-estacao.json`; trecho:

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000002",
    "codigo_estacao": 90000004,
    "severidade": "EMERGENCIA",
    "severidade_rotulo": "Emergência",
    "status": "ATIVO",
    "mensagem": "Chuva acumulada de 96.0 mm em 24 h (limite de emergência: 80.0 mm)",
    "fatores": [
      {
        "descricao": "Chuva acumulada de 96.0 mm em 24 h (limite de emergência: 80.0 mm)",
        "severidade": "EMERGENCIA",
        "severidade_rotulo": "Emergência"
      }
    ],
    "emitido_em": "2026-01-10T12:00:00Z",
    "encerrado_em": null
  }
]
```

### `GET /alertas`

Alertas ativos, do mais grave para o menos grave.

**Resposta 200:** lista de [`AlertaOut`](#alertaout)

Exemplo: `GET /alertas`. Alertas ativos, do mais grave para o menos grave. Resposta completa em `frontend/src/mocks/alertas.json`; trecho:

```json
[
  {
    "id": "00000000-0000-0000-0000-000000000002",
    "codigo_estacao": 90000004,
    "severidade": "EMERGENCIA",
    "severidade_rotulo": "Emergência",
    "status": "ATIVO",
    "mensagem": "Chuva acumulada de 96.0 mm em 24 h (limite de emergência: 80.0 mm)",
    "fatores": [
      {
        "descricao": "Chuva acumulada de 96.0 mm em 24 h (limite de emergência: 80.0 mm)",
        "severidade": "EMERGENCIA",
        "severidade_rotulo": "Emergência"
      }
    ],
    "emitido_em": "2026-01-10T12:00:00Z",
    "encerrado_em": null
  }
]
```

### `GET /municipios/{uf}/{nome}/situacao`

Pior situação entre as estações do município; o nome é comparado sem acentos.

| Parâmetro | Onde | Obrigatório | Tipo | Restrições | Padrão | Descrição |
|---|---|---|---|---|---|---|
| `uf` | path | sim | `string` | tamanho ≥ 2, tamanho ≤ 2 |  |  |
| `nome` | path | sim | `string` | tamanho ≥ 1 |  |  |

**Resposta 200:** [`SituacaoMunicipioOut`](#situacaomunicipioout)

Exemplo: `GET /municipios/RJ/Petr%C3%B3polis/situacao`. Situação de um município: a pior entre as suas estações. Resposta completa em `frontend/src/mocks/municipio-situacao.json`; trecho:

```json
{
  "uf": "RJ",
  "municipio": "Petrópolis",
  "severidade": "EMERGENCIA",
  "severidade_rotulo": "Emergência",
  "estacoes": [
    {
      "codigo": 90000004,
      "nome": "Petrópolis (exemplo)",
      "tipo": "PLUVIOMETRICA",
      "latitude": -22.51,
      "longitude": -43.18,
      "uf": "RJ",
      "municipio": "Petrópolis",
      "rio": null,
      "operando": true,
      "telemetrica": true,
      "grandezas": [
        "CHUVA"
      ],
      "severidade": "EMERGENCIA",
      "severidade_rotulo": "Emergência",
      "alerta": {
        "id": "00000000-0000-0000-0000-000000000002",
        "codigo_estacao": 90000004,
        "severidade": "EMERGENCIA",
        "severidade_rotulo": "Emergência",
        "status": "ATIVO",
        "mensagem": "Chuva acumulada de 96.0 mm em 24 h (limite de emergência: 80.0 mm)",
        "fatores": [
          {
            "descricao": "Chuva acumulada de 96.0 mm em 24 h (limite de emergência: 80.0 mm)",
            "severidade": "EMERGENCIA",
            "severidade_rotulo": "Emergência"
          }
        ],
        "emitido_em": "2026-01-10T12:00:00Z",
        "encerrado_em": null
      }
    }
  ]
}
```

## Erros

Toda resposta de erro tem o formato `{"detail": "<mensagem>"}` (`app/api/erros.py`). Erros de validação trazem também `erros`, a lista detalhada do FastAPI.

| Status | Quando |
|---|---|
| 400 | Erro de regra da aplicação (`ErroAplicacao`). |
| 404 | Estação ou município inexistente (`RecursoNaoEncontrado`). |
| 422 | Parâmetro inválido ou dado que viola o domínio (`DadoInvalido`). |
| 503 | Fonte externa (ANA) indisponível; vem com o cabeçalho `Retry-After`. |

Exemplo 404: `GET /estacoes/1` (`frontend/src/mocks/erro-404.json`):

```json
{
  "detail": "estação 1 não encontrada"
}
```

Exemplo 422: `GET /estacoes/proximas?lat=200&lon=0` (`frontend/src/mocks/erro-422.json`):

```json
{
  "detail": "lat: Input should be less than or equal to 90",
  "erros": [
    {
      "type": "less_than_equal",
      "loc": [
        "query",
        "lat"
      ],
      "msg": "Input should be less than or equal to 90",
      "input": "200",
      "ctx": {
        "le": 90.0
      }
    }
  ]
}
```

## Modelos

<a id="alertaout"></a>

### `AlertaOut`

| Campo | Tipo | Obrigatório |
|---|---|---|
| `id` | `string` (uuid) | sim |
| `codigo_estacao` | `integer` | sim |
| `severidade` | [`Severidade`](#severidade) | sim |
| `severidade_rotulo` | `string` | sim |
| `status` | [`StatusAlerta`](#statusalerta) | sim |
| `mensagem` | `string` | sim |
| `fatores` | lista de [`FatorAvaliacaoOut`](#fatoravaliacaoout) | sim |
| `emitido_em` | `string` (date-time) | sim |
| `encerrado_em` | `string` (date-time) \| `null` | sim |

<a id="estacaoout"></a>

### `EstacaoOut`

| Campo | Tipo | Obrigatório |
|---|---|---|
| `codigo` | `integer` | sim |
| `nome` | `string` | sim |
| `tipo` | [`TipoEstacao`](#tipoestacao) | sim |
| `latitude` | `number` | sim |
| `longitude` | `number` | sim |
| `uf` | `string` | sim |
| `municipio` | `string` | sim |
| `rio` | `string` \| `null` | sim |
| `operando` | `boolean` | sim |
| `telemetrica` | `boolean` | sim |
| `grandezas` | lista de [`Grandeza`](#grandeza) | sim |
| `severidade` | [`Severidade`](#severidade) | sim |
| `severidade_rotulo` | `string` | sim |
| `alerta` | [`AlertaOut`](#alertaout) \| `null` | sim |

<a id="estacaoproximaout"></a>

### `EstacaoProximaOut`

| Campo | Tipo | Obrigatório |
|---|---|---|
| `codigo` | `integer` | sim |
| `nome` | `string` | sim |
| `tipo` | [`TipoEstacao`](#tipoestacao) | sim |
| `latitude` | `number` | sim |
| `longitude` | `number` | sim |
| `uf` | `string` | sim |
| `municipio` | `string` | sim |
| `rio` | `string` \| `null` | sim |
| `operando` | `boolean` | sim |
| `telemetrica` | `boolean` | sim |
| `grandezas` | lista de [`Grandeza`](#grandeza) | sim |
| `severidade` | [`Severidade`](#severidade) | sim |
| `severidade_rotulo` | `string` | sim |
| `alerta` | [`AlertaOut`](#alertaout) \| `null` | sim |
| `distancia_km` | `number` | sim |

<a id="fatoravaliacaoout"></a>

### `FatorAvaliacaoOut`

| Campo | Tipo | Obrigatório |
|---|---|---|
| `descricao` | `string` | sim |
| `severidade` | [`Severidade`](#severidade) | sim |
| `severidade_rotulo` | `string` | sim |

<a id="grandeza"></a>

### `Grandeza`

Valores: `CHUVA`, `NIVEL`, `VAZAO`.

<a id="medicaoout"></a>

### `MedicaoOut`

| Campo | Tipo | Obrigatório |
|---|---|---|
| `data_hora_utc` | `string` (date-time) | sim |
| `valor` | `number` | sim |
| `consistencia` | [`NivelConsistencia`](#nivelconsistencia) | sim |
| `status_fonte` | `string` \| `null` | sim |

<a id="nivelconsistencia"></a>

### `NivelConsistencia`

Valores: `BRUTO`, `CONSISTIDO`.

<a id="serieout"></a>

### `SerieOut`

| Campo | Tipo | Obrigatório |
|---|---|---|
| `codigo_estacao` | `integer` | sim |
| `grandeza` | [`Grandeza`](#grandeza) | sim |
| `grandeza_rotulo` | `string` | sim |
| `unidade` | `string` | sim |
| `inicio` | `string` (date-time) | sim |
| `fim` | `string` (date-time) | sim |
| `medicoes` | lista de [`MedicaoOut`](#medicaoout) | sim |

<a id="severidade"></a>

### `Severidade`

Valores: `NORMAL`, `ATENCAO`, `ALERTA`, `EMERGENCIA`.

<a id="situacaomunicipioout"></a>

### `SituacaoMunicipioOut`

| Campo | Tipo | Obrigatório |
|---|---|---|
| `uf` | `string` | sim |
| `municipio` | `string` | sim |
| `severidade` | [`Severidade`](#severidade) | sim |
| `severidade_rotulo` | `string` | sim |
| `estacoes` | lista de [`EstacaoOut`](#estacaoout) | sim |

<a id="statusalerta"></a>

### `StatusAlerta`

Valores: `ATIVO`, `ENCERRADO`.

<a id="tipoestacao"></a>

### `TipoEstacao`

Valores: `FLUVIOMETRICA`, `PLUVIOMETRICA`.
