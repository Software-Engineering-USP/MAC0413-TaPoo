# Relatório de testes, refatorações e validação manual

Este documento registra exemplos verificáveis no código atual e um roteiro de
validação manual. A lista de verificações manuais é um procedimento para executar;
ela não significa que uma demonstração em produção tenha sido feita.

## Refatorações com antes e depois

### Handler síncrono para uma resposta síncrona

No commit `83a1aa4` (`refactor(api): make 404 exception handler synchronous`), o
handler de estação inexistente deixou de ser `async`:

```diff
- async def _estacao_nao_encontrada(_: Request, erro: Exception) -> JSONResponse:
+ def _estacao_nao_encontrada(_: Request, erro: Exception) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(erro)})
```

O handler não aguardava nenhuma operação assíncrona. A remoção de `async` torna a
assinatura compatível com o trabalho executado sem sugerir uma espera que não existe;
status e corpo da resposta permanecem os mesmos.

### Remoção de configuração duplicada de resposta

No commit `42322ac` (`refactor(api): drop redundant response_model from routes`), as
rotas deixaram de repetir o modelo já declarado no tipo de retorno:

```diff
- @router.get("", response_model=list[AlertaOut])
+ @router.get("")
  def alertas_ativos(consulta: Consulta) -> list[AlertaOut]:
```

O FastAPI infere o modelo de resposta pela anotação `-> list[AlertaOut]`. A mudança
remove uma segunda declaração do mesmo contrato, mantendo a validação e o esquema
OpenAPI gerados pelo framework. O padrão foi aplicado às rotas de estações e alertas.

Os commits podem ser examinados com `git show 83a1aa4` e `git show 42322ac`. O diff
acima registra uma refatoração histórica; atualmente, os handlers estão centralizados em
`backend/app/api/erros.py`, registrados por `registrar_handlers()`, e não implementados
em `main.py`.

## Testes existentes e ferramentas

| Tipo | Exemplos no projeto | Ferramenta/observação |
|---|---|---|
| Domínio | `backend/tests/dominio/` | pytest; invariantes, cálculos, exceções nomeadas e regras sem HTTP ou banco externo |
| Aplicação | `backend/tests/aplicacao/` | pytest; casos de uso com fontes e repositórios controlados |
| API | `backend/tests/api/` | `TestClient` do FastAPI; rotas, erros HTTP (`test_erros.py`), ciclo de coleta (`test_ciclo_coleta.py`) e CORS (`test_cors.py`) |
| Infraestrutura | `backend/tests/infra/` | pytest; adaptador ANA com respostas simuladas, agendador e contrato dos repositórios em memória, SQLite e PostgreSQL (`test_repositorios_contrato.py`) |
| Configuração | `backend/tests/test_configuracao.py` | pytest; variáveis ANA, seleção de repositório, URL do banco e intervalo de coleta |
| Frontend | `frontend/src/` | Ainda não há suíte automatizada de componentes; Vitest/Testing Library é uma issue aberta (#109) |

No backend, `pytest-cov` mede linhas e ramos do pacote `app`. O workflow
`.github/workflows/ci-cd.yml` gera o relatório de cobertura em `backend/coverage.xml`
e `backend/pyproject.toml` define `fail_under = 80`. Isso é um limite mínimo do CI,
não uma afirmação de que todas as execuções tenham exatamente 80%: a porcentagem real
é a que aparece no resumo de cada execução.

O SonarCloud recebe esse XML por `sonar.python.coverage.reportPaths`. O arquivo
`sonar-project.properties` exclui `frontend/**` da cobertura porque o frontend ainda
não possui testes automatizados. O Quality Gate do SonarCloud e o limite de cobertura
do pytest são verificações relacionadas, mas distintas: um não deve ser descrito como
se fosse o outro.

O workflow também executa Ruff (`ruff check` e `ruff format --check`) no backend e
ESLint, Prettier e build no frontend. `httpx` fornece o transporte usado pelo
`TestClient`; os testes de fontes externas usam respostas simuladas em vez de chamadas
à ANA.

## Casos relevantes e limitações atuais

| Cenário | Resultado esperado | Onde há cobertura automatizada |
|---|---|---|
| API inicializa e responde ao health check | `GET /health` retorna `{"status":"ok"}` | `backend/tests/test_main.py` |
| Estações podem ser listadas e filtradas | `GET /estacoes` aceita filtros documentados e devolve situação | `backend/tests/api/test_estacoes.py` |
| Estação inexistente | `GET /estacoes/{codigo}` responde 404 | `backend/tests/api/test_estacoes.py` |
| Série válida | `GET /estacoes/{codigo}/medicoes?grandeza=NIVEL` devolve a série | `backend/tests/api/test_estacoes.py` |
| Período inválido ou maior que 31 dias | A API responde 422 | `backend/tests/api/test_estacoes.py` |
| Invariante do domínio violada | `DadoInvalido` é traduzida para 422 | `backend/tests/dominio/` e `backend/tests/api/test_erros.py` |
| Recurso não encontrado ou erro da aplicação | A API responde 404 ou 400 conforme a classe da exceção | `backend/tests/api/test_erros.py`, `test_estacoes.py` e `test_municipios.py` |
| Falha de transporte ou resposta inválida da ANA | `ErroFonteAna` herda de `FonteIndisponivel`; a API responde 503 com `Retry-After` | `backend/tests/infra/test_fonte_ana.py`, `backend/tests/api/test_erros.py` e `test_estacoes.py` |
| Ciclo de coleta e atualização de alertas | A coleta pode emitir alertas e ciclos seguintes evitam buscar dados sem mudança | `backend/tests/api/test_ciclo_coleta.py` |
| Agendador periódico | Inicia, encerra e lida com falhas sem parar os ciclos seguintes | `backend/tests/infra/test_agendador.py` |
| CORS e configuração | Origens, repositório e intervalo de coleta respeitam as variáveis configuradas | `backend/tests/api/test_cors.py` e `backend/tests/test_configuracao.py` |
| Contrato dos repositórios | O contrato comum é verificado em memória, SQLite e PostgreSQL | `backend/tests/infra/test_repositorios_contrato.py` |
| Histórico de alertas | Ordem cronológica e limite são verificados nos repositórios em memória e SQL | `backend/tests/infra/test_memoria.py` e `test_repositorios_contrato.py` |
| Cidade sem estação correspondente | A API responde 404 na consulta de situação municipal | `backend/tests/api/test_municipios.py` |

Os dados de `FonteFake` são fictícios e servem para desenvolvimento e testes; não
representam medições observadas no Brasil. Para usar a ANA, é preciso configurar as
credenciais localmente. As respostas podem depender da disponibilidade e do formato
do serviço externo. A API consulta medições quando a série é solicitada, o intervalo
permitido é de até 31 dias. Fora do Docker Compose, `REPO=memoria` é o padrão e os dados
coletados se perdem quando o backend reinicia; com `REPO=sql`, os repositórios usam
SQLite ou PostgreSQL conforme `DATABASE_URL`. O Compose seleciona PostgreSQL e guarda os
dados no volume `dados-postgres`. O PostgreSQL gratuito do deploy Render tem prazo de
expiração, descrito no README. O frontend ainda não tem testes de componentes. O
repositório também não registra uma URL pública de demonstração.

## Roteiro de verificação manual

O roteiro abaixo pode ser executado localmente com `docker compose up --build`. Ele
não exige credenciais ANA: sem credenciais o backend usa a fonte fictícia.

1. Abra `http://localhost:3000` e confirme que o frontend carrega.
2. Abra `http://localhost:8000/health` e confirme a resposta `{"status":"ok"}`.
3. Abra `http://localhost:8000/docs` e confira as rotas publicadas.
4. Consulte `http://localhost:8000/estacoes` e verifique se a lista de exemplo é
   apresentada.
5. Escolha um código retornado pela lista e consulte
   `http://localhost:8000/estacoes/{codigo}`; confira os dados da estação e sua
   severidade.
6. Consulte
   `http://localhost:8000/estacoes/{codigo}/medicoes?grandeza=NIVEL` e confirme a
   série. Substitua o código pelo valor retornado pela API.
7. Consulte um código inexistente e confirme o 404. Informe um período invertido ou
   superior a 31 dias na rota de medições e confirme o 422.
8. Na interface, confira o comportamento em viewport desktop e móvel. Registre
   separadamente qualquer erro visual ou de interação: a UI atual ainda contém dados
   ilustrativos e não deve ser interpretada como painel hidrológico plenamente
   integrado.

Para validar a integração com a ANA, use credenciais válidas em `.env` e repita as
consultas com uma estação disponível. Essa etapa é separada do roteiro local com
`FonteFake`; não se deve afirmar que a fonte real foi validada apenas porque a API
local iniciou.
