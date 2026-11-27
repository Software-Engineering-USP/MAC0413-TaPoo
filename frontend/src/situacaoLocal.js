/** Situação de um local salvo a partir das estações reais em volta dele. */

export const RAIO_LOCAL_KM = 10;

const ORDEM_SEVERIDADE = ["NORMAL", "ATENCAO", "ALERTA", "EMERGENCIA"];

export function chaveLocal(place) {
  return place.center.join(",");
}

/** Resume as estações próximas pela severidade mais alta entre elas. */
export function resumirSituacao(estacoes) {
  if (!estacoes.length) return { estado: "sem-estacoes" };

  const pior = estacoes.reduce((atual, estacao) =>
    ORDEM_SEVERIDADE.indexOf(estacao.severidade) >
    ORDEM_SEVERIDADE.indexOf(atual.severidade)
      ? estacao
      : atual,
  );
  return {
    estado: "ok",
    severidade: pior.severidade,
    rotulo: pior.severidade_rotulo,
    estacoes: estacoes.length,
  };
}

export function descreverSituacao(situacao) {
  switch (situacao?.estado) {
    case "ok": {
      const estacoes =
        situacao.estacoes === 1 ? "1 estação" : `${situacao.estacoes} estações`;
      return `${situacao.rotulo} · ${estacoes} em ${RAIO_LOCAL_KM} km`;
    }
    case "sem-estacoes":
      return `Sem estações em ${RAIO_LOCAL_KM} km`;
    case "erro":
      return "Situação indisponível";
    default:
      return "Consultando estações próximas…";
  }
}

/** Sufixo de classe CSS: a severidade em minúsculas, ou o estado da consulta. */
export function classeSituacao(situacao) {
  return situacao?.estado === "ok"
    ? situacao.severidade.toLowerCase()
    : (situacao?.estado ?? "carregando");
}
