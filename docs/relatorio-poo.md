# Relatório de conceitos de POO e padrões de projeto

Este documento descreve decisões que já aparecem no backend do TaPoo. Os exemplos são
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

### Interfaces e inversão de dependência

As portas em `backend/app/aplicacao/portas.py` são contratos abstratos. Por exemplo,
`EstacaoRepositorio` descreve como salvar, buscar e listar estações, sem escolher banco
de dados. `EstacaoRepositorioMemoria`, em `backend/app/infra/memoria/repositorios.py`,
implementa o contrato. Assim, os serviços dependem da interface da aplicação, e a
infraestrutura fornece uma implementação substituível.

### Encapsulamento e invariantes

`SerieTemporal` centraliza as regras para adicionar medições: a estação e a grandeza da
medição precisam corresponder à série, e os elementos permanecem ordenados por data.

```python
def adicionar(self, medicao: Medicao) -> None:
    if medicao.codigo_estacao != self.codigo_estacao:
        raise ValueError("medição pertence a outra estação")
    if medicao.grandeza() != self.grandeza:
        raise ValueError("grandeza incompatível com a série")
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

### Exceções como parte do modelo

Exceções de domínio representam situações inválidas ou indisponibilidade de uma fonte
externa. Por exemplo, as validações de medições rejeitam valores que não fazem sentido
para aquela grandeza. A camada de API traduz erros conhecidos em respostas HTTP; a
exceção não precisa conhecer HTTP. Consulte `backend/app/dominio/` e
`backend/app/main.py`.

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
| Problema | Avaliar situações hidrológicas por critérios que variam: cota, chuva acumulada, subida rápida. |
| Contrato | `RegraAlerta`, com `avaliar` e `descrever`. |
| Implementações | `RegraCotaReferencia`, `RegraChuvaAcumulada` e `RegraSubidaRapida`. |
| Alternativas | Um único avaliador com condicionais para cada tipo de regra. |
| Trade-off | Novas regras podem ser adicionadas sem concentrar todas as condições em um método; há mais classes e a ordem de composição das regras ainda precisa ser configurada. |
| Onde fica | `backend/app/dominio/alerta.py`. |

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

## Síntese

O projeto usa contratos abstratos, composição e polimorfismo para separar domínio,
serviços e infraestrutura. A herança aparece onde os objetos realmente variam — as
medições — enquanto estações usam enum e composição porque seus dados e operações são
majoritariamente comuns. Os padrões apresentados são identificados pelo papel que
desempenham no código, com limites e alternativas registrados para evitar chamar toda
abstração de um padrão de projeto.
