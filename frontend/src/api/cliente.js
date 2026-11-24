import {
  mockGetMunicipalitySituation,
  mockGetStation,
  mockHealth,
  mockListActiveAlerts,
  mockListNearbyStations,
  mockListStations,
  mockListStationMeasurements,
} from "./mocks";

const API_URL = (import.meta.env.VITE_API_URL?.trim() || "").replace(
  /\/+$/,
  "",
);

export const usaApiReal = API_URL.length > 0;

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function formatApiDetail(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => item?.msg)
      .filter(Boolean)
      .join(" ");
  }
  return null;
}

async function getJson(path, { params = {}, signal } = {}) {
  const url = new URL(`${API_URL}${path}`);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      url.searchParams.set(key, String(value));
    }
  });

  const response = await fetch(url, { signal });
  if (!response.ok) {
    let detail;
    try {
      detail = formatApiDetail((await response.json()).detail);
    } catch {
      // Mantém a mensagem HTTP se a resposta não tiver JSON válido.
    }
    throw new ApiError(
      detail || `A API retornou um erro (HTTP ${response.status}).`,
      response.status,
    );
  }

  return response.json();
}

/** GET /health */
export function verificarSaude({ signal } = {}) {
  return usaApiReal ? getJson("/health", { signal }) : mockHealth({ signal });
}

/** GET /estacoes */
export function listarEstacoes({
  texto,
  uf,
  tipo,
  apenasTelemetricas = false,
  signal,
} = {}) {
  const params = {
    q: texto === undefined || texto === null ? undefined : texto.trim(),
    uf,
    tipo,
    apenas_telemetricas: apenasTelemetricas,
  };

  return usaApiReal
    ? getJson("/estacoes", { params, signal })
    : mockListStations({
        texto,
        uf,
        tipo,
        apenasTelemetricas,
        signal,
      });
}

/** GET /estacoes/proximas */
export function listarEstacoesProximas({ lat, lon, raioKm = 50, signal } = {}) {
  const params = { lat, lon, raio_km: raioKm };

  return usaApiReal
    ? getJson("/estacoes/proximas", { params, signal })
    : mockListNearbyStations({ lat, lon, raioKm, signal });
}

/** GET /estacoes/{codigo} */
export function obterEstacao(codigo, { signal } = {}) {
  const path = `/estacoes/${encodeURIComponent(codigo)}`;
  return usaApiReal
    ? getJson(path, { signal })
    : mockGetStation(codigo, { signal });
}

/** GET /estacoes/{codigo}/medicoes */
export function listarMedicoesEstacao(
  codigo,
  { grandeza, inicio, fim, signal } = {},
) {
  const path = `/estacoes/${encodeURIComponent(codigo)}/medicoes`;
  const params = { grandeza, inicio, fim };

  return usaApiReal
    ? getJson(path, { params, signal })
    : mockListStationMeasurements(codigo, {
        grandeza,
        inicio,
        fim,
        signal,
      });
}

/** GET /municipios/{uf}/{nome}/situacao */
export function obterSituacaoMunicipio(uf, nome, { signal } = {}) {
  const path = `/municipios/${encodeURIComponent(uf)}/${encodeURIComponent(
    nome,
  )}/situacao`;

  return usaApiReal
    ? getJson(path, { signal })
    : mockGetMunicipalitySituation(uf, nome, { signal });
}

/** GET /alertas */
export function listarAlertasAtivos({ signal } = {}) {
  return usaApiReal
    ? getJson("/alertas", { signal })
    : mockListActiveAlerts({ signal });
}
