# Decisões de modelagem

Registro curto das decisões de modelagem do backend: o contexto, a decisão tomada e as consequências. Cada uma aponta para o código em que aparece.

## 1. `Estacao` concreta com `TipoEstacao`, e não subclasses

**Contexto.** A ANA tem estações pluviométricas (medem chuva) e fluviométricas (medem nível e vazão). Estações telemétricas medem chuva também, qualquer que seja o tipo. Uma alternativa seria a hierarquia `Estacao` → `EstacaoPluviometrica` / `EstacaoFluviometrica`.

**Decisão.** `Estacao` é uma classe concreta (`backend/app/dominio/estacao.py`) com o campo `tipo: TipoEstacao` (`dominio/enums.py`). O que cada estação mede sai de uma tabela, `_GRANDEZAS_POR_TIPO`, combinada com a flag `telemetrica`, dentro de `Estacao.mede()`.

**Por quê.**
- **O tipo é um dado, não um comportamento.** As duas variantes têm os mesmos atributos e as mesmas operações. A única diferença é o conjunto de grandezas, e uma tabela resolve isso. Uma subclasse não teria nenhum método próprio para sobrescrever.
- **A regra depende de duas dimensões.** O resultado de `mede()` depende de tipo × telemetria. Com herança, isso pediria quatro classes ou um `if` dentro de cada subclasse. A tabela mais uma linha cobre todos os casos.
- **O tipo vem de fora.** A ANA envia o tipo como texto (`Tipo_Estacao`), e o ORM o guarda numa coluna (`modelos_orm.py`). Com subclasses, `FonteAna._mapear_estacao`, `EstacaoRepositorioSql._para_estacao` e os fakes precisariam de uma fábrica para escolher a classe, e o ORM precisaria de herança de tabela única com discriminador.
- **O comportamento variável já está em outro lugar.** O polimorfismo do domínio fica nas regras de alerta (`RegraAlerta` → `RegraCotaReferencia`, `RegraChuvaAcumulada`, padrão Strategy) e nas medições (`Medicao` → `MedicaoChuva` / `MedicaoNivel` / `MedicaoVazao`). Nesses casos cada subclasse muda de fato uma regra: como avaliar, qual unidade usar, quais valores são válidos.

**Consequências.**
- (+) Mapear a ANA e o SQL fica direto, sem fábrica nem discriminador. Um tipo novo, se surgir, é uma linha no enum e na tabela.
- (−) O sistema de tipos não impede, por exemplo, pedir a cota de uma estação pluviométrica. Essa checagem acontece em tempo de execução (`mede()` e `RegraAlerta._validar_serie`).
- Se um dia os tipos ganharem comportamentos realmente diferentes, por exemplo uma curva-chave só nas fluviométricas, vale reavaliar. Mesmo assim, a primeira opção seria **composição** (`Estacao` com um componente `CurvaChave | None`) e não herança.

## 2. `Municipio` como value object

**Contexto.** `Estacao` guardava `uf` e `municipio` como dois textos soltos. A regra "o mesmo município se reconhece com ou sem acento, em qualquer caixa, dentro da mesma UF" ficava espalhada por `FiltroEstacoes`, `ConsultarDados.situacao_municipio` e `SituacaoMunicipio`.

**Decisão.** `Municipio(nome, uf)` (`backend/app/dominio/municipio.py`) é um value object imutável:
- valida o nome (não pode ser vazio) e a UF (2 letras, em maiúsculas);
- define igualdade e hash pela `chave` `(uf, nome normalizado)`, então `Municipio("São Paulo", "SP") == Municipio("sao  paulo", "sp")`;
- oferece `corresponde(nome, uf)` para comparar com o texto que o usuário digita;
- guarda a grafia original em `nome`, que é a usada na exibição.

`Estacao` passa a ter um campo `municipio: Municipio`. `Estacao.uf` vira uma property que lê `municipio.uf`. `SituacaoMunicipio` recebe o `Municipio` e recusa estações de outro município.

**Por que value object e não entidade.** Ainda não temos uma identidade estável para o município: o código IBGE não vem na resposta que usamos da ANA, e não existe uma tabela de referência sincronizada. Dois municípios com a mesma UF e o mesmo nome normalizado são, para o sistema, o mesmo município. Essa é justamente a definição de um value object.

**Consequências.**
- (+) A regra de comparação fica num lugar só, e o domínio garante que uma `Estacao` sempre tem UF e município válidos.
- (+) O contrato da API e as colunas do banco não mudaram: `EstacaoOut` e `SituacaoMunicipioOut` continuam expondo `uf` e `municipio` como texto, e `EstacaoModelo` continua com as colunas `uf` e `municipio`.
- (−) Na ANA, um registro sem `UF_Estacao` recebe a UF consultada (`FonteAna._carregar_estacoes_uf`). Na busca por código, um registro sem UF passa a ser inválido.
- Quando houver código IBGE, `Municipio` pode ganhar o campo `codigo_ibge` e virar entidade sem mudar quem o usa.
