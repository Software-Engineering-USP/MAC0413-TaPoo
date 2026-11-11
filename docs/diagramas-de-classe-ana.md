# TaPoo — Diagramas de classe (integração com a API da ANA)

Guia para a criação das classes e da arquitetura do backend. Os diagramas são
uma **proposta** — o código atual ainda é só a estrutura inicial (`backend/app/main.py`).

Fonte: OpenAPI oficial do **Hidro Webservice** da ANA
(`https://www.ana.gov.br/hidrowebservice`, versão `v1.0.3984.2`, consultada em 2026-11-11).

## 0. O que a API da ANA oferece (resumo que guia o modelo)

| Grupo | Endpoint (`/EstacoesTelemetricas/...`) | Filtros principais | Limite por requisição |
|---|---|---|---|
| Autenticação | `OAUth/v1` | headers `Identificador`, `Senha` → token | — |
| Inventário | `HidroInventarioEstacoes/v1` | código da estação **ou** código da bacia **ou** UF | ao menos 1 filtro |
| Telemétricas | `HidroinfoanaSerieTelemetricaAdotada/v1`, `...Detalhada/v1` | código, `Tipo Filtro Data`, `Data de Busca`, `Range Intervalo de busca` | **30 dias** |
| Convencionais | `HidroSerieChuva`, `HidroSerieCotas`, `HidroSerieVazao`, `HidroSerieCurvaDescarga`, `HidroSerieResumoDescarga`, `HidroSeriePerfilTransversal`, `HidroSerieQA`, `HidroSerieSedimentos`, `HidroSerieGranulometria` | código, `Tipo Filtro Data`, data inicial/final | **366 dias** |
| Satélite | `HidrosatInventarioEstacoes/v1`, `HidrosatSerieDados/v1` | código, período | 366 dias |
| Referência | `HidroUF`, `HidroMunicipio`, `HidroBacia`, `HidroSubBacia`, `HidroRio`, `HidroEntidade` | código, data de atualização | sem limite |

Pontos que **influenciam o design**:

- Todo endpoint é `GET` e devolve o mesmo envelope `Devolucao { status, code, message, items }`
  → um único cliente HTTP genérico + leitores (parsers) por endpoint.
- Os endpoints de dados exigem token → componente de autenticação que guarda o token em memória e o renova.
- Os limites de 30/366 dias por requisição → o cliente precisa **fatiar períodos** automaticamente.
- `Tipo Filtro Data` = `DATA_LEITURA | DATA_ULTIMA_ATUALIZACAO` → permite **sincronização
  incremental** (buscar só o que mudou desde a última coleta).
- O código de município da base Hidro **não é o do IBGE** → guardar os dois códigos separadamente.
- O OpenAPI não tipa o conteúdo de `items`. Os nomes de campo dos DTOs abaixo
  (`codigoestacao`, `Cota_Adotada`, ...) seguem o formato que a API costuma devolver, mas
  **precisam ser conferidos com uma resposta real autenticada** antes de implementar a leitura das respostas.

## 1. Visão de camadas (arquitetura)

```mermaid
flowchart LR
    subgraph API["api (FastAPI)"]
        R[Rotas + esquemas Pydantic]
    end
    subgraph APP["aplicacao"]
        S[Serviços / casos de uso]
        P[[Portas: FonteDados, Repositórios]]
    end
    subgraph DOM["dominio"]
        E[Entidades, objetos de valor, regras de alerta]
    end
    subgraph INFRA["infra"]
        ANA[integracoes/ana: cliente, DTOs, mapeadores]
        DB[persistencia: repositórios SQL]
        SCH[agendador]
    end
    R --> S
    S --> E
    S --> P
    ANA -. implementa .-> P
    DB -. implementa .-> P
    SCH --> S
    ANA --> HW[(Hidro Webservice ANA)]
```

Regra de dependência: `dominio` não importa nada das outras camadas; a ANA é apenas
**um adaptador** de `FonteDadosHidrologicos`. Isso permite trocar/adicionar outras fontes
(ex.: CEMADEN, INMET) e testar os serviços com implementações falsas (fakes).

Estrutura de pacotes sugerida:

```
backend/app/
  dominio/        estacao.py, medicao.py, geografia.py, alerta.py, enums.py
  aplicacao/      portas.py, sincronizacao.py, coleta.py, monitoramento.py, consulta.py
  infra/
    integracoes/ana/  config.py, autenticacao.py, cliente.py, endpoints.py, dtos.py, mapeadores.py, periodo.py
    persistencia/     repositorios_sql.py, modelos_orm.py
    agendador.py
  api/            routers/estacoes.py, routers/medicoes.py, routers/alertas.py, schemas.py
  main.py
```

## 2. Domínio — estações e geografia

Espelha o inventário e as tabelas de referência da ANA, mas com nomes e tipos próprios.

```mermaid
classDiagram
    class Estacao {
      +int codigo
      +str nome
      +TipoEstacao tipo
      +Coordenada coordenada
      +float altitude_m
      +float area_drenagem_km2
      +bool operando
      +bool telemetrica
      +datetime atualizado_em
      +mede(grandeza: Grandeza) bool
    }
    class Coordenada {
      <<objeto de valor>>
      +float latitude
      +float longitude
      +distancia_km(outra: Coordenada) float
    }
    class UnidadeFederativa {
      +int codigo
      +str sigla
      +str nome
    }
    class Municipio {
      +int codigo_hidro
      +int codigo_ibge
      +str nome
    }
    class Bacia {
      +int codigo
      +str nome
    }
    class SubBacia {
      +int codigo
      +str nome
    }
    class Rio {
      +int codigo
      +str nome
    }
    class Entidade {
      +int codigo
      +str sigla
      +str nome
    }
    class TipoEstacao {
      <<enumeração>>
      FLUVIOMETRICA
      PLUVIOMETRICA
    }

    Estacao *-- Coordenada
    Estacao --> TipoEstacao
    Estacao "*" --> "1" Municipio : localizada em
    Municipio "*" --> "1" UnidadeFederativa
    Estacao "*" --> "1" SubBacia
    SubBacia "*" --> "1" Bacia
    Estacao "*" --> "0..1" Rio : monitora
    Estacao "*" --> "1" Entidade : responsavel
    Estacao "*" --> "1" Entidade : operadora
```

## 3. Domínio — medições e séries temporais

As séries telemétricas (adotada) trazem chuva, nível e vazão na mesma linha; as convencionais
vêm em endpoints separados. O domínio normaliza tudo em **uma medição por grandeza**.

```mermaid
classDiagram
    class Medicao {
      <<abstrata>>
      +int codigo_estacao
      +datetime data_hora_utc
      +float valor
      +OrigemDado origem
      +NivelConsistencia consistencia
      +str status_fonte
      +datetime atualizado_na_fonte_em
      +grandeza()* Grandeza
      +unidade()* str
    }
    class MedicaoChuva {
      +grandeza() Grandeza
      +unidade() str
    }
    class MedicaoNivel {
      +grandeza() Grandeza
      +unidade() str
    }
    class MedicaoVazao {
      +grandeza() Grandeza
      +unidade() str
    }
    class SerieTemporal {
      +int codigo_estacao
      +Grandeza grandeza
      +list~Medicao~ medicoes
      +adicionar(m: Medicao)
      +no_periodo(p: Periodo) SerieTemporal
      +ultimo() Medicao
      +maximo() Medicao
      +acumulado(janela: timedelta) float
      +variacao(janela: timedelta) float
    }
    class Periodo {
      <<objeto de valor>>
      +datetime inicio
      +datetime fim
      +duracao() timedelta
      +dividir(max_dias: int) list~Periodo~
    }
    class Grandeza {
      <<enumeração>>
      CHUVA
      NIVEL
      VAZAO
    }
    class OrigemDado {
      <<enumeração>>
      TELEMETRICA
      CONVENCIONAL
      SATELITE
    }
    class NivelConsistencia {
      <<enumeração>>
      BRUTO
      CONSISTIDO
    }

    Medicao <|-- MedicaoChuva
    Medicao <|-- MedicaoNivel
    Medicao <|-- MedicaoVazao
    SerieTemporal "1" o-- "0..*" Medicao
    SerieTemporal ..> Periodo
    Medicao --> OrigemDado
    Medicao --> NivelConsistencia
    SerieTemporal --> Grandeza
```

> `Periodo.dividir()` é reaproveitado pelo cliente ANA para respeitar os limites de 30/366 dias.

## 4. Domínio — monitoramento e alertas

A ANA **não** fornece cotas de alerta/inundação nem severidade: isso é regra do TaPoo,
configurada por estação. As regras usam o padrão **Strategy**.

```mermaid
classDiagram
    class RegraAlerta {
      <<abstrata>>
      +int id
      +int codigo_estacao
      +bool ativa
      +avaliar(serie: SerieTemporal)* Severidade
      +descrever(severidade: Severidade)* str
    }
    class RegraCotaReferencia {
      +float cota_atencao_cm
      +float cota_alerta_cm
      +float cota_inundacao_cm
      +avaliar(serie) Severidade
    }
    class RegraChuvaAcumulada {
      +timedelta janela
      +float limite_moderado_mm
      +float limite_alto_mm
      +float limite_extremo_mm
      +avaliar(serie) Severidade
    }
    class RegraSubidaRapida {
      +timedelta janela
      +float variacao_maxima_cm
      +avaliar(serie) Severidade
    }
    class Alerta {
      +UUID id
      +int codigo_estacao
      +Severidade severidade
      +str mensagem
      +datetime emitido_em
      +datetime encerrado_em
      +StatusAlerta status
      +Medicao medicao_gatilho
      +escalar(nova: Severidade)
      +encerrar(quando: datetime)
    }
    class AvaliadorAlertas {
      +list~RegraAlerta~ regras
      +avaliar(serie: SerieTemporal, ativo: Alerta) Alerta
    }
    class Severidade {
      <<enumeração>>
      NORMAL
      ATENCAO
      ALERTA
      EMERGENCIA
    }
    class StatusAlerta {
      <<enumeração>>
      ATIVO
      ENCERRADO
    }

    RegraAlerta <|-- RegraCotaReferencia
    RegraAlerta <|-- RegraChuvaAcumulada
    RegraAlerta <|-- RegraSubidaRapida
    AvaliadorAlertas o-- "1..*" RegraAlerta
    AvaliadorAlertas ..> SerieTemporal : lê
    AvaliadorAlertas ..> Alerta : cria / atualiza
    Alerta --> Severidade
    Alerta --> StatusAlerta
    RegraAlerta ..> Severidade
```

## 5. Infra — cliente da API da ANA (adaptador)

```mermaid
classDiagram
    class AnaConfig {
      +str base_url
      +str identificador
      +str senha
      +float timeout_s
      +int max_tentativas
    }
    class TokenAna {
      <<objeto de valor>>
      +str valor
      +datetime expira_em
      +expirado(agora: datetime) bool
    }
    class AutenticadorAna {
      -TokenAna token_atual
      +obter_token() TokenAna
      +invalidar()
      -autenticar() TokenAna
    }
    class ClienteHttpAna {
      +get(caminho: str, params: dict) RespostaAna
      -com_retentativa(req) RespostaAna
    }
    class RespostaAna {
      <<DTO>>
      +str status
      +int code
      +str message
      +list~dict~ items
      +sucesso() bool
    }
    class ErroApiAna {
      <<exceção>>
      +int code
      +str message
    }
    class InventarioAna {
      +listar_estacoes(uf: UF, codigo_bacia: int, atualizado_desde: date) list~EstacaoAnaDTO~
      +buscar_estacao(codigo: int) EstacaoAnaDTO
    }
    class SerieTelemetricaAna {
      +MAX_DIAS = 30
      +adotada(codigo: int, periodo: Periodo, filtro: TipoFiltroData) list~LeituraTelemetricaDTO~
      +detalhada(codigo: int, periodo: Periodo, filtro: TipoFiltroData) list~LeituraTelemetricaDTO~
    }
    class SerieConvencionalAna {
      +MAX_DIAS = 366
      +chuva(codigo, periodo, filtro) list~SerieMensalDTO~
      +cotas(codigo, periodo, filtro) list~SerieMensalDTO~
      +vazao(codigo, periodo, filtro) list~SerieMensalDTO~
    }
    class ReferenciaAna {
      +ufs() list~dict~
      +municipios() list~dict~
      +bacias() list~dict~
      +sub_bacias() list~dict~
      +rios() list~dict~
      +entidades() list~dict~
    }
    class EstacaoAnaDTO {
      <<DTO>>
      +int codigoestacao
      +str Estacao_Nome
      +str Tipo_Estacao
      +float Latitude
      +float Longitude
      +str UF_Estacao
      +str Municipio_Nome
      +str Bacia_Nome
      +str Rio_Nome
      +str Operando
      +str Tipo_Estacao_Telemetrica
    }
    class LeituraTelemetricaDTO {
      <<DTO>>
      +int codigoestacao
      +str Data_Hora_Medicao
      +float Chuva_Adotada
      +str Chuva_Adotada_Status
      +float Cota_Adotada
      +str Cota_Adotada_Status
      +float Vazao_Adotada
      +str Vazao_Adotada_Status
      +str Data_Atualizacao
    }
    class SerieMensalDTO {
      <<DTO>>
      +int codigoestacao
      +str Data_Hora_Dado
      +int Nivel_Consistencia
      +dict valores_por_dia
    }
    class MapeadorAna {
      +para_estacao(dto: EstacaoAnaDTO) Estacao
      +para_medicoes(dto: LeituraTelemetricaDTO) list~Medicao~
      +expandir_mensal(dto: SerieMensalDTO, g: Grandeza) list~Medicao~
    }
    class TipoFiltroData {
      <<enumeração>>
      DATA_LEITURA
      DATA_ULTIMA_ATUALIZACAO
    }
    class IntervaloBusca {
      <<enumeração>>
      MINUTO_5 ... MINUTO_30
      HORA_1 ... HORA_24
      DIAS_2 ... DIAS_30
    }

    AutenticadorAna --> AnaConfig
    AutenticadorAna --> TokenAna
    ClienteHttpAna --> AutenticadorAna : cabeçalho Authorization
    ClienteHttpAna ..> RespostaAna
    ClienteHttpAna ..> ErroApiAna : lança
    InventarioAna --> ClienteHttpAna
    SerieTelemetricaAna --> ClienteHttpAna
    SerieConvencionalAna --> ClienteHttpAna
    ReferenciaAna --> ClienteHttpAna
    InventarioAna ..> EstacaoAnaDTO
    SerieTelemetricaAna ..> LeituraTelemetricaDTO
    SerieTelemetricaAna ..> IntervaloBusca
    SerieConvencionalAna ..> SerieMensalDTO
    SerieTelemetricaAna ..> TipoFiltroData
    SerieConvencionalAna ..> TipoFiltroData
    MapeadorAna ..> EstacaoAnaDTO
    MapeadorAna ..> LeituraTelemetricaDTO
    MapeadorAna ..> SerieMensalDTO
```

Notas de implementação:

- `ClienteHttpAna` recebe `401` → chama `AutenticadorAna.invalidar()` e tenta uma vez de novo.
- `SerieTelemetricaAna` / `SerieConvencionalAna` usam `Periodo.dividir(MAX_DIAS)` e concatenam
  os resultados; nunca expõem o limite a quem chama.
- `LeituraTelemetricaDTO` vira até **três** `Medicao` (chuva, nível, vazão), ignorando valores nulos.
- `SerieMensalDTO` (convencionais) chega como uma linha por mês com colunas por dia
  (`Chuva_01`…`Chuva_31`, `Cota_01`…) → `expandir_mensal` gera uma `Medicao` por dia.
- Converter `Data_Hora_Medicao` (horário local da fonte) para UTC no mapeador.
- Credenciais (`Identificador`/`Senha`) vêm de variáveis de ambiente, nunca do código.

## 6. Aplicação — portas, serviços e adaptadores

```mermaid
classDiagram
    class FonteDadosHidrologicos {
      <<interface>>
      +listar_estacoes(filtro: FiltroEstacoes) list~Estacao~
      +buscar_medicoes(codigo: int, periodo: Periodo, alteradas_desde: datetime) list~Medicao~
    }
    class FonteAna {
      +listar_estacoes(filtro) list~Estacao~
      +buscar_medicoes(codigo, periodo, alteradas_desde) list~Medicao~
    }
    class EstacaoRepositorio {
      <<interface>>
      +salvar_varias(estacoes: list~Estacao~)
      +por_codigo(codigo: int) Estacao
      +buscar(filtro: FiltroEstacoes) list~Estacao~
      +monitoradas() list~Estacao~
    }
    class MedicaoRepositorio {
      <<interface>>
      +salvar_varias(medicoes: list~Medicao~)
      +serie(codigo: int, g: Grandeza, p: Periodo) SerieTemporal
      +ultima_atualizacao(codigo: int) datetime
    }
    class AlertaRepositorio {
      <<interface>>
      +salvar(alerta: Alerta)
      +ativo_da_estacao(codigo: int) Alerta
      +ativos() list~Alerta~
    }
    class RegraRepositorio {
      <<interface>>
      +da_estacao(codigo: int) list~RegraAlerta~
    }
    class SincronizarEstacoes {
      +executar(filtro: FiltroEstacoes) int
    }
    class ColetarMedicoes {
      +executar(codigo: int) int
      +executar_todas() int
    }
    class MonitorarEstacoes {
      +executar(codigo: int) Alerta
    }
    class ConsultarDados {
      +estacoes_proximas(c: Coordenada, raio_km: float) list~Estacao~
      +serie(codigo: int, g: Grandeza, p: Periodo) SerieTemporal
      +alertas_ativos() list~Alerta~
    }
    class FiltroEstacoes {
      <<objeto de valor>>
      +str uf
      +int codigo_bacia
      +TipoEstacao tipo
      +bool apenas_telemetricas
    }
    class AgendadorColeta {
      +iniciar()
      +parar()
    }

    FonteDadosHidrologicos <|.. FonteAna
    FonteAna --> InventarioAna
    FonteAna --> SerieTelemetricaAna
    FonteAna --> SerieConvencionalAna
    FonteAna --> MapeadorAna

    SincronizarEstacoes --> FonteDadosHidrologicos
    SincronizarEstacoes --> EstacaoRepositorio
    ColetarMedicoes --> FonteDadosHidrologicos
    ColetarMedicoes --> MedicaoRepositorio
    ColetarMedicoes --> EstacaoRepositorio
    ColetarMedicoes --> MonitorarEstacoes : após coletar
    MonitorarEstacoes --> MedicaoRepositorio
    MonitorarEstacoes --> RegraRepositorio
    MonitorarEstacoes --> AlertaRepositorio
    MonitorarEstacoes --> AvaliadorAlertas
    ConsultarDados --> EstacaoRepositorio
    ConsultarDados --> MedicaoRepositorio
    ConsultarDados --> AlertaRepositorio
    AgendadorColeta --> ColetarMedicoes
    AgendadorColeta --> SincronizarEstacoes
```

Os repositórios SQL (`EstacaoRepositorioSql`, etc.) implementam as interfaces acima na camada
`infra/persistencia`; as rotas FastAPI dependem apenas dos serviços (via `Depends`).

## 7. Fluxo de coleta incremental (sequência)

```mermaid
sequenceDiagram
    participant AG as AgendadorColeta
    participant CM as ColetarMedicoes
    participant MR as MedicaoRepositorio
    participant FA as FonteAna
    participant ST as SerieTelemetricaAna
    participant HTTP as ClienteHttpAna
    participant AUT as AutenticadorAna
    participant ANA as Hidro Webservice
    participant MO as MonitorarEstacoes

    AG->>CM: executar_todas()
    loop cada estação monitorada
        CM->>MR: ultima_atualizacao(codigo)
        CM->>FA: buscar_medicoes(codigo, periodo, alteradas_desde)
        FA->>ST: adotada(codigo, periodo, DATA_ULTIMA_ATUALIZACAO)
        loop cada fatia de até 30 dias
            ST->>HTTP: get(HidroinfoanaSerieTelemetricaAdotada/v1, params)
            HTTP->>AUT: obter_token()
            AUT-->>HTTP: token (guardado ou novo via OAUth/v1)
            HTTP->>ANA: GET + Authorization Bearer
            ANA-->>HTTP: Devolucao {status, code, message, items}
        end
        ST-->>FA: LeituraTelemetricaDTO[]
        FA-->>CM: Medicao[] (via MapeadorAna)
        CM->>MR: salvar_varias(medicoes) (insere ou atualiza por estação+grandeza+data_hora)
        CM->>MO: executar(codigo)
    end
```

## Decisões de modelagem

- **Inserir ou atualizar (upsert) pela chave natural** `(codigo_estacao, grandeza, data_hora_utc, origem)`: a ANA reenvia
  dados quando são corrigidos; a coleta incremental por `DATA_ULTIMA_ATUALIZACAO` depende disso.
- **Guardar o status/consistência da fonte** em `Medicao` — dados brutos telemétricos podem ser
  revisados depois; alertas devem saber se se basearam em dado bruto.
- **Começar pelas telemétricas** (adotada): são as únicas próximas do tempo real e servem para
  alertas. Convencionais servem para histórico/estatística e podem ficar para uma segunda fase.
- **HidroSat, qualidade da água, sedimentos, perfil transversal, curva de descarga** ficam fora do
  modelo inicial; adicioná-los é criar um novo método no adaptador + nova subclasse de `Medicao`
  se for uma grandeza nova.
- **Usuários/relatos da comunidade** (ver `docs/class-diagrams.md`, diagrama 2) são independentes
  da ANA e podem ser acoplados depois via `Estacao`/`Coordenada`.
