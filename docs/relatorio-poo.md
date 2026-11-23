# Relatório de conceitos de POO e padrões de projeto

Este documento descreve decisões que já aparecem no backend do projeto. Os exemplos são
trechos reduzidos do código atual; os caminhos indicam onde consultar a implementação
completa.

## Conceitos de programação orientada a objetos

### Abstração

Uma abstração define o que um objeto oferece sem exigir que quem o usa conheça seus
detalhes. `RegraAlerta` descreve as operações que toda regra de alerta precisa fornecer:

```python
class RegraAlerta(ABC):
    @abstractmethod
    def avaliar(self, serie: SerieTemporal) -> Severidade: ...

    @abstractmethod
    def descrever(self, severidade: Severidade, serie: SerieTemporal) -> str: ...
```

O avaliador trabalha com esse contrato; não precisa conhecer os cálculos específicos de
cota ou de chuva. A definição está em `backend/app/dominio/alerta.py`.

### Interfaces e portas

As portas em `backend/app/aplicacao/portas.py` são contratos abstratos. Por exemplo,
`EstacaoRepositorio` descreve como salvar, buscar e listar estações, sem escolher banco
de dados. `EstacaoRepositorioMemoria`, em `backend/app/infra/memoria/repositorios.py`,
implementa o contrato. A inversão de dependência que resulta dessa separação é
explicada na seção de SOLID abaixo.

### Encapsulamento e invariantes

`SerieTemporal` centraliza as regras para adicionar medições: a estação e a grandeza da
medição precisam corresponder à série, e os elementos permanecem ordenados por data.

```python
def adicionar(self, medicao: Medicao) -> None:
    if medicao.codigo_estacao != self.codigo_estacao:
        raise ValueError("medição pertence a outra estação")
    if medicao.grandeza() != self.grandeza:
        raise ValueError(f"série de {self.grandeza} não aceita {medicao.grandeza()}")
    insort(self.medicoes, medicao, key=lambda m: m.data_hora_utc)
```

O método protege os invariantes no caminho normal de atualização. A lista `medicoes`,
porém, é pública; portanto, a classe não impede que um chamador a altere diretamente.
Esse é um limite real do encapsulamento atual e uma possível melhoria futura. Código em
`backend/app/dominio/medicao.py`.

### Herança e polimorfismo

`Medicao` define dados e comportamento comuns. `MedicaoChuva`, `MedicaoNivel` e
`MedicaoVazao` especializam a grandeza e, quando necessário, as validações:

```python
class MedicaoChuva(Medicao):
    def __post_init__(self) -> None:
        super().__post_init__()
        if self.valor < 0:
            raise ValueError("chuva não pode ser negativa")

    def grandeza(self) -> Grandeza:
        return Grandeza.CHUVA
```

O polimorfismo aparece quando o restante do sistema chama `grandeza()` através de uma
referência do tipo `Medicao`: cada subtipo responde de acordo com sua grandeza. A
implementação está em `backend/app/dominio/medicao.py`.

### Composição

`Container`, em `backend/app/api/dependencias.py`, reúne os serviços usados pela API.
`montar_container` cria repositórios, fonte de dados e serviços, e injeta as dependências
nos objetos que precisam delas. O serviço de consulta, por exemplo, recebe repositórios
em vez de criá-los por conta própria. Isso mantém a montagem em um lugar conhecido e
facilita trocar implementações nos testes.

### Imutabilidade

`Coordenada` e `Periodo` são objetos de valor imutáveis (`frozen=True`). Depois de
validados, seus valores não podem ser alterados acidentalmente. Isso ajuda a manter
estáveis operações como distância geográfica e validação de intervalos. Consulte
`backend/app/dominio/geografia.py` e `backend/app/dominio/periodo.py`.

### Exceções nomeadas e tradução na API

As camadas de aplicação e infraestrutura já definem exceções nomeadas. Em
`backend/app/aplicacao/erros.py`, `ErroAplicacao` é a base de `RecursoNaoEncontrado`,
que, por sua vez, é a base de `EstacaoNaoEncontrada` e `MunicipioNaoEncontrado`:

```python
class ErroAplicacao(Exception): ...

class RecursoNaoEncontrado(ErroAplicacao): ...

class EstacaoNaoEncontrada(RecursoNaoEncontrado): ...
```

`backend/app/main.py` registra um handler para `RecursoNaoEncontrado`; assim, as duas
exceções específicas recebem a mesma resposta 404 sem handlers duplicados. O mesmo
arquivo traduz `ErroFonteAna`, definido em `backend/app/infra/fontes/ana.py`, em 502.
O handler trabalha com o contrato da exceção-base e usa a mensagem da instância
concreta, ilustrando polimorfismo. As invariantes do domínio, como grandeza incompatível
em `SerieTemporal`, continuam usando `ValueError`; essas exceções não precisam conhecer
HTTP.

## Decisão de modelagem: `Estacao` e `TipoEstacao`

Hoje, `Estacao` é uma única entidade e registra seu tipo com `TipoEstacao`. O método
`mede` consulta o tipo e considera também se a estação é telemétrica:

```python
_GRANDEZAS_POR_TIPO = {
    TipoEstacao.PLUVIOMETRICA: frozenset({Grandeza.CHUVA}),
    TipoEstacao.FLUVIOMETRICA: frozenset({Grandeza.NIVEL, Grandeza.VAZAO}),
}

def mede(self, grandeza: Grandeza) -> bool:
    grandezas = _GRANDEZAS_POR_TIPO[self.tipo]
    if self.telemetrica:
        grandezas = grandezas | {Grandeza.CHUVA}
    return grandeza in grandezas
```

O código real está em `backend/app/dominio/estacao.py`.

### Por que manter uma entidade com enum agora

- As estações compartilham os mesmos dados principais: código, nome, coordenadas,
  município, UF e estado operacional.
- O comportamento específico atual é pequeno e cabe na regra `mede`.
- A ANA fornece um tipo categórico no inventário; armazená-lo como enum preserva essa
  informação sem criar subclasses que, por enquanto, quase não teriam comportamento
  próprio.
- A telemetria altera as grandezas medidas de forma independente do tipo. Subclasses
  como `EstacaoFluviometricaTelemetrica` e
  `EstacaoFluviometricaConvencional` começariam a combinar dimensões diferentes e
  poderiam multiplicar as classes necessárias.

### O que se perderia com subclasses

Subclasses poderiam tornar diferenças de comportamento explícitas e evitar uma tabela
de decisão caso cada tipo passasse a ter validações e operações próprias. No estado
atual, porém, elas aumentariam a hierarquia sem remover a variação independente da
telemetria. Herança seria mais útil se os tipos tivessem contratos e comportamentos
realmente distintos, não apenas nomes diferentes.

### Quando rever a decisão

Se novas fontes trouxerem capacidades que não correspondam ao enum atual, ou se cada
tipo passar a ter regras próprias extensas, a entidade pode evoluir para composição,
por exemplo, com capacidades ou sensores associados à estação. Isso permitiria
representar combinações sem criar uma subclasse para cada combinação. Essa evolução
deve ser motivada por requisitos concretos; hoje a combinação de `TipoEstacao`,
`telemetrica` e `mede` é mais simples.

## Catálogo de padrões presentes no código

### Strategy — regras de alerta

| Ficha | Descrição |
|---|---|
| Problema | Avaliar situações hidrológicas por critérios que variam: cota e chuva acumulada. |
| Contrato | `RegraAlerta`, com `avaliar` e `descrever`. |
| Implementações | `RegraCotaReferencia` e `RegraChuvaAcumulada`. |
| Alternativas | Um único avaliador com condicionais para cada tipo de regra. |
| Trade-off | Novas regras podem ser adicionadas sem concentrar todas as condições em um método; há mais classes e a ordem de composição das regras ainda precisa ser configurada. |
| Onde fica | `backend/app/dominio/alerta.py`. |

A subida rápida ainda não é uma regra de alerta implementada. `SerieTemporal.variacao`,
em `backend/app/dominio/medicao.py`, fornece uma operação que poderia ser usada por uma
futura estratégia desse tipo.

### Repository — acesso a dados

| Ficha | Descrição |
|---|---|
| Problema | Separar os casos de uso dos detalhes de armazenar e consultar estações, medições e alertas. |
| Contratos | `EstacaoRepositorio`, `MedicaoRepositorio`, `AlertaRepositorio` e `RegraRepositorio`. |
| Implementações atuais | Repositórios em memória em `backend/app/infra/memoria/repositorios.py`. |
| Alternativas | Acessar diretamente estruturas em memória nos serviços ou acoplar os serviços a um banco específico. |
| Trade-off | A porta facilita substituição e testes, mas precisa permanecer alinhada às operações que os casos de uso realmente precisam. |
| Onde fica | Contratos em `backend/app/aplicacao/portas.py`; implementações em `backend/app/infra/memoria/repositorios.py`. |

### Adapter — fontes hidrológicas

| Ficha | Descrição |
|---|---|
| Problema | Converter APIs e dados externos para as entidades e medições do domínio. |
| Contrato | `FonteDadosHidrologicos`. |
| Implementações | `FonteAna` adapta o HidroWeb; `FonteFake` fornece dados de exemplo usando o mesmo contrato. |
| Alternativas | Fazer cada serviço entender os formatos da ANA ou espalhar conversões pelas rotas. |
| Trade-off | O restante do sistema recebe modelos próprios e pode usar outra fonte; o adaptador precisa acompanhar mudanças no formato externo. |
| Onde fica | Porta em `backend/app/aplicacao/portas.py`; adaptadores em `backend/app/infra/fontes/`. |

### Injeção de dependências e Composition Root

| Ficha | Descrição |
|---|---|
| Problema | Decidir em um lugar quais implementações concretas compõem a aplicação e entregar cada dependência ao serviço que precisa dela. |
| Mecanismo | `montar_container` instancia fontes e repositórios e injeta-os em serviços. FastAPI entrega os serviços às rotas por dependências. |
| Alternativas | Instanciar dependências dentro de cada rota ou serviço. |
| Trade-off | A composição explícita facilita testes e substituição; o arquivo de composição conhece as implementações concretas e precisa ser atualizado quando a configuração muda. |
| Onde fica | `backend/app/api/dependencias.py` e `backend/app/main.py`. |

### Factory — construção de regras de exemplo

`regras_de_exemplo()` em `backend/app/infra/fontes/fake.py` centraliza a criação das
regras e cotas usadas pela fonte de demonstração. É uma função fábrica pequena: esconde
os detalhes de construção e devolve uma coleção pronta. Ela não é uma fábrica geral de
fontes. A seleção entre `FonteAna` e `FonteFake` ainda ocorre diretamente em
`montar_container`; portanto, o projeto não tem hoje uma `FonteFactory` separada.

| Ficha | Descrição |
|---|---|
| Problema | Criar um conjunto coerente de regras de demonstração sem repetir sua construção. |
| Alternativas | Construir cada regra no ponto de uso ou criar uma fábrica extensível para vários perfis de configuração. |
| Trade-off | A função é simples e suficiente para os dados de exemplo; se surgirem múltiplos perfis configuráveis, uma fábrica explícita poderá ser mais adequada. |
| Onde fica | `backend/app/infra/fontes/fake.py`; uso em `backend/app/api/dependencias.py`. |

## Princípios de projeto e boas práticas

### Responsabilidade única e coesão

As classes de aplicação concentram um caso de uso. `ColetarMedicoes` coordena buscar,
salvar e monitorar medições; `ConsultarDados` reúne operações de consulta. A conversão
do formato da ANA fica no adaptador `FonteAna`, e as rotas HTTP ficam em
`backend/app/api/routers/`. Essa divisão mantém responsabilidades relacionadas juntas
e reduz a necessidade de uma única classe conhecer todo o sistema.

Isso não significa que cada classe deva ter somente um método. O critério é se as
operações mudam pelas mesmas razões: por exemplo, alterações no protocolo da ANA devem
ficar no adaptador, sem exigir mudanças em `ConsultarDados`.

### Aberto para extensão e fechado para modificação

`AvaliadorAlertas` trabalha com objetos `RegraAlerta`. Uma nova regra pode implementar
esse contrato sem transformar o avaliador numa sequência de condicionais por tipo. As
estratégias atuais são `RegraCotaReferencia` e `RegraChuvaAcumulada`; uma estratégia de
subida rápida seria uma extensão possível, mas ainda não existe no código.

O princípio não exige evitar toda mudança em código existente. Se a nova regra exigir
uma nova grandeza ou uma nova forma de obter dados, os contratos e os casos de uso
relacionados também podem precisar evoluir.

### Substituição de Liskov

As subclasses de `Medicao` oferecem `grandeza()` e podem ser usadas como medições em
`SerieTemporal`. O código consumidor não precisa distinguir chuva, nível e vazão para
armazenar ou ordenar as medições. As validações particulares — como chuva e vazão não
negativas — tornam explícitas as condições específicas de cada subtipo.

Esse exemplo mostra a intenção de substituição, não uma prova formal de que toda
subclasse futura será compatível. Novos subtipos devem preservar as operações e
invariantes esperadas pelos consumidores de `Medicao`.

### Segregação de interfaces

Os contratos da aplicação são separados por papel: fontes hidrológicas, repositórios de
estações, de medições, de alertas e de regras. Os serviços recebem apenas as portas que
usam. Isso evita que uma implementação de repositório tenha de conhecer a API externa
da ANA.

As portas ainda têm mais de uma operação quando elas pertencem ao mesmo papel — por
exemplo, buscar e listar são responsabilidades relacionadas de `EstacaoRepositorio`.
O objetivo não é criar uma interface para cada método, mas evitar contratos grandes que
obriguem implementações a oferecer capacidades sem relação entre si.

### Inversão de dependência

`ColetarMedicoes` recebe `FonteDadosHidrologicos`, `EstacaoRepositorio` e
`MedicaoRepositorio` no construtor. Ele depende de abstrações da aplicação, enquanto a
composição em `backend/app/api/dependencias.py` escolhe as implementações concretas.
Assim, os testes podem injetar fontes e repositórios falsos sem alterar o caso de uso.
As portas e o contrato `EstacaoRepositorio` estão apresentados na seção “Interfaces e
portas”.

### Nomes, exceções e acoplamento

Os nomes do domínio são em português e descrevem conceitos do problema — por exemplo,
`EstacaoRepositorio`, `Periodo` e `RegraCotaReferencia`. Métodos que executam ações usam
verbos como `salvar_varias`, `buscar_medicoes` e `avaliar`.

As entidades validam suas próprias invariantes. `Periodo` rejeita intervalos inválidos;
`MedicaoChuva` rejeita chuva negativa. Essas validações do domínio usam `ValueError`,
enquanto a aplicação e o adaptador ANA também possuem exceções nomeadas, descritas na
seção “Exceções nomeadas e tradução na API”. As rotas não duplicam essas validações: a
API traduz os erros conhecidos em respostas HTTP.

## Padrões considerados e não adotados

Uma solução deve ser escolhida para resolver uma necessidade presente. Os padrões
abaixo não são proibidos; apenas não são necessários para o fluxo atual.

### Singleton

Um Singleton faria uma única instância global de um objeto. O projeto compõe as
dependências em `montar_container` e entrega essa instância às rotas e serviços. Esse
arranjo deixa o ciclo de vida explícito e permite criar containers isolados nos testes,
sem estado global compartilhado. Um Singleton só seria justificável se houvesse uma
necessidade concreta de garantir unicidade fora desse ponto de composição.

### Observer

Observer permite que vários interessados recebam notificações quando um objeto muda.
No fluxo atual, `ColetarMedicoes` chama diretamente `MonitorarEstacoes`, que avalia as
regras e salva alertas. Há um caminho conhecido e síncrono, então uma lista de
observadores adicionaria registro, despacho e tratamento de falhas sem benefício claro.
Se no futuro alertas precisarem notificar vários canais independentes (por exemplo,
e-mail, painel e mensagens), um evento ou mecanismo de publicação poderá ser avaliado.

### Herança para cada tipo de estação

Criar uma subclasse para cada combinação de tipo e telemetria aumentaria a hierarquia
sem comportamento distinto suficiente para justificá-la. A decisão atual e seus
critérios para revisão estão detalhados na seção “Decisão de modelagem: `Estacao` e
`TipoEstacao`”.

## Processo de desenvolvimento e revisão

### Fluxo de mudanças

O repositório organiza o trabalho em branches e pull requests direcionados à `main`.
Uma revisão deve comparar a mudança com a issue, observar se o escopo está delimitado,
examinar os casos de erro e verificar se os testes cobrem o comportamento alterado.
Comentários devem apontar o arquivo e o cenário reproduzível; mudanças pedidas devem
ser verificadas novamente na versão atualizada do PR.

### Verificações automatizadas

O workflow `.github/workflows/ci-cd.yml` executa os seguintes passos em pull requests
para `main`:

| Parte | Verificações configuradas |
|---|---|
| Backend | `uv sync --locked --extra dev`, `uv run ruff check .`, `uv run ruff format --check .` e `uv run pytest --cov=app` |
| Frontend | `npm ci`, `npm run lint`, `npm run format:check` e `npm run build` |
| Qualidade | SonarCloud roda depois dos jobs de backend e frontend; a cobertura mínima do backend é 80% |

O Ruff verifica problemas estáticos e formatação Python; ESLint verifica problemas no
JavaScript/React; Prettier confere formatação; pytest executa a suíte do backend; e o
build confirma que o frontend pode ser empacotado. Essas verificações complementam a
revisão de comportamento, mas não substituem a avaliação dos requisitos da issue.

## Síntese

O projeto usa contratos abstratos, composição e polimorfismo para separar domínio,
serviços e infraestrutura. A herança aparece onde os objetos realmente variam — as
medições — enquanto estações usam enum e composição porque seus dados e operações são
majoritariamente comuns. Os padrões apresentados são identificados pelo papel que
desempenham no código, com limites e alternativas registrados para evitar chamar toda
abstração de um padrão de projeto.
