# Fontes de dados

## Decisões

- **Medições hidrológicas observadas:** HidroWebService da ANA, por meio dos
  endpoints de inventário de estações e série telemétrica adotada. A integração
  está isolada em `backend/app/infra/fontes/ana.py`.
- **Previsão de chuva:** API de previsão do Open-Meteo, consultando precipitação
  horária por coordenada. A integração está em
  `backend/app/infra/fontes/openmeteo.py`.
- **Demonstração e execução offline:** `FonteSimulada` carrega estações, perfis
  horários e limiares fictícios de `backend/app/infra/fontes/dados/cenario-demo.json`.
  Esse arquivo não é uma captura da ANA e não valida o contrato real do serviço.

`FONTE=ana` seleciona a ANA e exige `ANA_IDENTIFICADOR` e `ANA_SENHA`.
`FONTE=simulada` seleciona o cenário JSON sem chamadas de rede; `FONTE=fake` é
mantido como alias por compatibilidade. Sem `FONTE`, credenciais ANA completas
selecionam a ANA e a ausência delas seleciona o cenário simulado.

## Contrato e tratamento de falhas

Os adaptadores convertem as respostas externas para as entidades do domínio e
implementam as portas de `backend/app/aplicacao/portas.py`. Credenciais ficam em
variáveis de ambiente ou no `.env` local, não nos arquivos de exemplo. Falhas de
comunicação ou respostas inválidas são convertidas em `FonteIndisponivel` (ou em
`ErroFonteAna`, que a especializa), para que rotas e serviços não dependam do
formato de erro de cada provedor.

As respostas de teste em `backend/tests/fixtures/ana/` são exemplos montados a
partir dos mocks existentes. Até haver capturas reais autorizadas, elas não devem
ser descritas como respostas verificadas da API.
