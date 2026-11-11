# Rastreador de Desastres Naturais — opções de diagrama de classes UML

O repositório ainda é apenas a estrutura inicial da aplicação, então estes diagramas descrevem um modelo de domínio proposto, e não uma implementação existente. Eles assumem que **ANA** é a *Agência Nacional de Águas e Saneamento Básico*. Adaptadores específicos de cada API mantêm o domínio independente da ANA, do OpenStreetMap e de qualquer provedor de dados meteorológicos.

## 1. Domínio principal — sem contas de usuário

Use esta opção quando a primeira versão apenas importa e exibe dados públicos de riscos.

```mermaid
classDiagram
    class EventoDeRisco {
      +UUID id
      +TipoDeRisco tipo
      +String titulo
      +String descricao
      +DateTime iniciadoEm
      +DateTime atualizadoEm
      +Severidade severidade
      +StatusEvento status
    }
    class EventoDeInundacao {
      +Decimal nivelAguaMetros
      +Decimal vazaoRioM3s
      +String nomeRio
    }
    class EventoDeChuva {
      +Decimal precipitacaoMm
      +JanelaDeTempo periodo
    }
    class Localizacao {
      +UUID id
      +Decimal latitude
      +Decimal longitude
      +String nomeLocal
      +String municipio
      +String siglaUF
    }
    class Observacao {
      +UUID id
      +DateTime observadoEm
      +Decimal valor
      +String unidade
      +String metrica
    }
    class FonteDeDados {
      +UUID id
      +String nome
      +String provedor
      +String idRegistroNaFonte
      +String urlFonte
      +DateTime obtidoEm
    }
    class Alerta {
      +UUID id
      +String mensagem
      +Severidade severidade
      +DateTime emitidoEm
      +DateTime expiraEm
      +StatusAlerta status
    }
    class TipoDeRisco {
      <<enumeração>>
      INUNDACAO
      CHUVA_FORTE
      DESLIZAMENTO
      SECA
      OUTRO
    }
    class Severidade {
      <<enumeração>>
      BAIXA
      MODERADA
      ALTA
      EXTREMA
    }
    class StatusEvento {
      <<enumeração>>
      ATIVO
      RESOLVIDO
      DESCONHECIDO
    }
    class StatusAlerta {
      <<enumeração>>
      ATIVO
      EXPIRADO
      CANCELADO
    }

    EventoDeRisco <|-- EventoDeInundacao
    EventoDeRisco <|-- EventoDeChuva
    EventoDeRisco "1" --> "1" Localizacao : ocorre em
    EventoDeRisco "1" o-- "0..*" Observacao : medições
    EventoDeRisco "1" --> "1..*" FonteDeDados : baseado em
    EventoDeRisco "1" --> "0..*" Alerta : pode gerar
```

## 2. Com usuários e relatos da comunidade

Acrescente esta parte se as pessoas puderem se cadastrar, salvar locais, receber alertas ou enviar/confirmar relatos. O relato de um usuário fica separado de uma medição oficial para que a origem e a confiabilidade continuem claras.

```mermaid
classDiagram
    class Usuario {
      +UUID id
      +String nome
      +String email
      +DateTime criadoEm
      +StatusUsuario status
    }
    class LocalSalvo {
      +UUID id
      +String rotulo
      +Decimal raioKm
    }
    class PreferenciaDeNotificacao {
      +UUID id
      +Boolean ativa
      +Severidade severidadeMinima
      +String canal
    }
    class RelatoDeUsuario {
      +UUID id
      +TipoDeRisco tipo
      +String descricao
      +DateTime relatadoEm
      +StatusRelato status
      +String urlMidia
    }
    class ConfirmacaoDeRelato {
      +UUID id
      +Boolean confirmaRisco
      +DateTime criadoEm
    }
    class EventoDeRisco {
      +UUID id
      +TipoDeRisco tipo
      +Severidade severidade
      +StatusEvento status
    }
    class Localizacao {
      +UUID id
      +Decimal latitude
      +Decimal longitude
      +String nomeLocal
    }

    Usuario "1" *-- "0..*" LocalSalvo : salva
    LocalSalvo "*" --> "1" Localizacao : aponta para
    Usuario "1" *-- "0..*" PreferenciaDeNotificacao : configura
    Usuario "1" --> "0..*" RelatoDeUsuario : envia
    RelatoDeUsuario "*" --> "1" Localizacao : relatado em
    RelatoDeUsuario "0..*" --> "0..1" EventoDeRisco : pode estar ligado a
    Usuario "1" --> "0..*" ConfirmacaoDeRelato : confirma
    ConfirmacaoDeRelato "*" --> "1" RelatoDeUsuario : sobre
    class StatusUsuario {
      <<enumeração>>
      ATIVO
      SUSPENSO
    }
    class StatusRelato {
      <<enumeração>>
      ENVIADO
      VERIFICADO
      REJEITADO
    }
```

## 3. Aplicação e integração com APIs externas

Use esta visão de projeto para o backend. O agendador solicita as importações; os adaptadores de cada provedor traduzem os dados externos para o modelo principal. O OpenStreetMap é modelado como provedor de geocodificação e dados de mapa, não como fonte de medições de risco.

```mermaid
classDiagram
    class AgendadorDeImportacao {
      +agendarImportacao(fonte: ProvedorDeDados)
      +executarImportacoesPendentes()
    }
    class ProvedorDeDados {
      <<interface>>
      +buscarEventos(limites, desde) List~RegistroExternoDeRisco~
    }
    class ProvedorAguasAna {
      +buscarEventos(limites, desde)
    }
    class ProvedorMeteorologico {
      +buscarEventos(limites, desde)
    }
    class ProvedorOpenStreetMap {
      +geocodificar(nomeLocal) Localizacao
      +buscarLocal(latitude, longitude) Local
    }
    class RegistroExternoDeRisco {
      +String idExterno
      +String tipo
      +DateTime dataHora
      +Map atributosBrutos
    }
    class MapeadorDeRisco {
      +paraDominio(registro: RegistroExternoDeRisco) EventoDeRisco
    }
    class RepositorioDeRiscos {
      <<interface>>
      +salvar(evento: EventoDeRisco)
      +buscarNaArea(limites) List~EventoDeRisco~
    }
    class RepositorioDeRiscosSql {
      +salvar(evento: EventoDeRisco)
      +buscarNaArea(limites)
    }
    class ServicoDeAlertas {
      +avaliar(evento: EventoDeRisco)
      +criarAlerta(evento: EventoDeRisco) Alerta
    }
    class EventoDeRisco
    class Alerta

    ProvedorDeDados <|.. ProvedorAguasAna
    ProvedorDeDados <|.. ProvedorMeteorologico
    AgendadorDeImportacao --> ProvedorDeDados : invoca
    AgendadorDeImportacao --> MapeadorDeRisco : converte registros
    ProvedorDeDados ..> RegistroExternoDeRisco : retorna
    MapeadorDeRisco ..> RegistroExternoDeRisco : traduz
    MapeadorDeRisco ..> EventoDeRisco : cria
    AgendadorDeImportacao --> RepositorioDeRiscos : persiste
    RepositorioDeRiscos <|.. RepositorioDeRiscosSql
    RepositorioDeRiscosSql --> EventoDeRisco : armazena
    AgendadorDeImportacao --> ServicoDeAlertas : avalia atualizações
    ServicoDeAlertas --> Alerta : cria
    ProvedorOpenStreetMap ..> Localizacao : resolve locais
```

## Ponto de partida sugerido

Para uma primeira entrega de diagrama de classes, combine o diagrama 1 com as fronteiras de integração do diagrama 3. Inclua o diagrama 2 apenas se contas de usuário ou relatos da comunidade fizerem parte dos requisitos planejados. Mantenha `EventoDeRisco` genérico e crie subclasses apenas para riscos com dados realmente diferentes; leituras de chuva, por exemplo, podem ser observações em vez de eventos independentes, dependendo da API.

### Notas de modelagem

- Guarde o provedor e o identificador do registro no provedor para os dados importados, de modo que os registros possam ser rastreados e não sejam duplicados.
- Guarde as datas e horas em um fuso horário consistente (normalmente UTC) e mantenha também a data/hora informada pela fonte.
- Trate a severidade como uma classificação normalizada da aplicação; mantenha os valores originais do provedor no registro importado ou na observação quando necessário.
- Para os dados da ANA, confirme quais conjuntos de dados e campos estão disponíveis antes de fixar `nivelAguaMetros`, `vazaoRioM3s` ou a frequência de atualização como requisitos.
