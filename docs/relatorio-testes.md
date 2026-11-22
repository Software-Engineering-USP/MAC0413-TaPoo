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

Os commits podem ser examinados com `git show 83a1aa4` e `git show 42322ac`.

## Testes existentes e ferramentas

| Tipo | Exemplos no projeto | Ferramenta/observação |
|---|---|---|
| Domínio | `backend/tests/dominio/` | pytest; invariantes, cálculos e regras sem HTTP ou banco externo |
| Aplicação | `backend/tests/aplicacao/` | pytest; casos de uso com fontes e repositórios controlados |
| API | `backend/tests/api/` | `TestClient` do FastAPI; exercita rotas, códigos HTTP e esquemas |
| Infraestrutura | `backend/tests/infra/` | pytest; ANA usa respostas simuladas, sem depender da rede real |
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
| Falha de transporte ou resposta inválida da ANA | O adaptador traduz a falha para `ErroFonteAna`; a API responde 502 | `backend/tests/infra/test_fonte_ana.py` e testes de API |
| Cidade sem estação correspondente | A API responde 404 na consulta de situação municipal | `backend/tests/api/test_municipios.py` |

Os dados de `FonteFake` são fictícios e servem para desenvolvimento e testes; não
representam medições observadas no Brasil. Para usar a ANA, é preciso configurar as
credenciais localmente. As respostas podem depender da disponibilidade e do formato
do serviço externo. A API consulta medições quando a série é solicitada, o intervalo
permitido é de até 31 dias, e a branch documentada aqui mantém repositórios em memória:
reiniciar o backend apaga os dados coletados. O frontend ainda não tem testes de
componentes. O repositório também não registra uma URL pública de demonstração.

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
