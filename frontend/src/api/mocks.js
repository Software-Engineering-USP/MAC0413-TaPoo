import { ApiError } from "./erros";

const mockAlert = {
  id: "a17b8b5c-5d80-4a36-91d3-b0a98c748f01",
  codigo_estacao: 90000001,
  severidade: "ALERTA",
  severidade_rotulo: "Alerta",
  status: "ATIVO",
  mensagem: "Nível do rio acima da faixa de atenção.",
  fatores: [
    {
      descricao: "Nível elevado do rio",
      severidade: "ALERTA",
      severidade_rotulo: "Alerta",
    },
  ],
  emitido_em: "2026-01-01T12:00:00Z",
  encerrado_em: null,
};

const mockEmergencyAlert = {
  id: "d2bff5c6-4739-4e1b-9856-57af1dc3bd36",
  codigo_estacao: 90000004,
  severidade: "EMERGENCIA",
  severidade_rotulo: "Emerg\u00eancia",
  status: "ATIVO",
  mensagem: "Chuva acumulada acima da faixa de emerg\u00eancia.",
  fatores: [
    {
      descricao: "Chuva acumulada em 24 horas acima do limite extremo",
      severidade: "EMERGENCIA",
      severidade_rotulo: "Emerg\u00eancia",
    },
  ],
  emitido_em: "2026-01-01T12:00:00Z",
  encerrado_em: null,
};

const mockAlerts = [mockEmergencyAlert, mockAlert];

const mockStations = [
  {
    codigo: 90000001,
    nome: "Rio Tiet\u00ea - S\u00e3o Paulo (exemplo)",
    tipo: "FLUVIOMETRICA",
    latitude: -23.52,
    longitude: -46.63,
    uf: "SP",
    municipio: "S\u00e3o Paulo",
    rio: "Rio Tiet\u00ea",
    operando: true,
    telemetrica: true,
    grandezas: ["CHUVA", "NIVEL", "VAZAO"],
    severidade: "ALERTA",
    severidade_rotulo: "Alerta",
    alerta: mockAlert,
  },
  {
    codigo: 90000002,
    nome: "Campinas (exemplo)",
    tipo: "PLUVIOMETRICA",
    latitude: -22.91,
    longitude: -47.06,
    uf: "SP",
    municipio: "Campinas",
    rio: null,
    operando: true,
    telemetrica: true,
    grandezas: ["CHUVA"],
    severidade: "NORMAL",
    severidade_rotulo: "Normal",
    alerta: null,
  },
  {
    codigo: 90000003,
    nome: "Rio das Velhas - Belo Horizonte (exemplo)",
    tipo: "FLUVIOMETRICA",
    latitude: -19.92,
    longitude: -43.94,
    uf: "MG",
    municipio: "Belo Horizonte",
    rio: "Rio das Velhas",
    operando: true,
    telemetrica: true,
    grandezas: ["CHUVA", "NIVEL", "VAZAO"],
    severidade: "NORMAL",
    severidade_rotulo: "Normal",
    alerta: null,
  },
  {
    codigo: 90000004,
    nome: "Petr\u00f3polis (exemplo)",
    tipo: "PLUVIOMETRICA",
    latitude: -22.51,
    longitude: -43.18,
    uf: "RJ",
    municipio: "Petr\u00f3polis",
    rio: null,
    operando: true,
    telemetrica: true,
    grandezas: ["CHUVA"],
    severidade: "EMERGENCIA",
    severidade_rotulo: "Emerg\u00eancia",
    alerta: mockEmergencyAlert,
  },
  {
    codigo: 90000005,
    nome: "Ouro Preto (exemplo)",
    tipo: "PLUVIOMETRICA",
    latitude: -20.39,
    longitude: -43.5,
    uf: "MG",
    municipio: "Ouro Preto",
    rio: null,
    operando: true,
    telemetrica: false,
    grandezas: ["CHUVA"],
    severidade: "NORMAL",
    severidade_rotulo: "Normal",
    alerta: null,
  },
];

const severityRank = {
  NORMAL: 0,
  ATENCAO: 1,
  ALERTA: 2,
  EMERGENCIA: 3,
};

const units = {
  CHUVA: { label: "Chuva", unit: "mm" },
  NIVEL: { label: "Nível", unit: "cm" },
  VAZAO: { label: "Vazão", unit: "m3/s" },
};

function normalizedText(value) {
  return String(value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("pt-BR");
}

function throwIfAborted(signal) {
  if (signal?.aborted)
    throw new DOMException("Requisição cancelada.", "AbortError");
}

function mockResult(signal, callback) {
  return Promise.resolve().then(() => {
    throwIfAborted(signal);
    return callback();
  });
}

function notFound(message) {
  return new ApiError(message, 404);
}

function validationError(message) {
  return new ApiError(message, 422);
}

export function mockHealth({ signal } = {}) {
  return mockResult(signal, () => ({ status: "ok" }));
}

export function mockGetMetadata({ signal } = {}) {
  return mockResult(signal, () => ({ origem_dados: "simulado" }));
}

export function mockListStations({
  texto,
  uf,
  tipo,
  apenasTelemetricas = false,
  signal,
} = {}) {
  return mockResult(signal, () => {
    const trimmedQuery = texto == null ? undefined : texto.trim();
    if (
      (trimmedQuery !== undefined && trimmedQuery.length < 2) ||
      trimmedQuery?.length > 100
    ) {
      throw validationError("A busca deve ter entre 2 e 100 caracteres.");
    }
    if (uf && uf.length !== 2) {
      throw validationError("Informe uma sigla de estado com 2 caracteres.");
    }
    if (tipo && !["FLUVIOMETRICA", "PLUVIOMETRICA"].includes(tipo)) {
      throw validationError("Tipo de estação inválido.");
    }

    const queryWords = normalizedText(trimmedQuery).split(" ").filter(Boolean);

    return mockStations.filter((station) => {
      if (uf && station.uf !== uf.toUpperCase()) return false;
      if (tipo && station.tipo !== tipo) return false;
      if (apenasTelemetricas && !station.telemetrica) return false;
      if (queryWords.length === 0) return true;

      const searchableText = normalizedText(
        [station.nome, station.municipio, station.rio]
          .filter(Boolean)
          .join(" "),
      );
      return queryWords.every((word) => searchableText.includes(word));
    });
  });
}

function distanceInKm(latitudeA, longitudeA, latitudeB, longitudeB) {
  const radians = (degrees) => (degrees * Math.PI) / 180;
  const latitudeDelta = radians(latitudeB - latitudeA);
  const longitudeDelta = radians(longitudeB - longitudeA);
  const haversine =
    Math.sin(latitudeDelta / 2) ** 2 +
    Math.cos(radians(latitudeA)) *
      Math.cos(radians(latitudeB)) *
      Math.sin(longitudeDelta / 2) ** 2;

  return 6371 * 2 * Math.atan2(Math.sqrt(haversine), Math.sqrt(1 - haversine));
}

export function mockListNearbyStations({ lat, lon, raioKm = 50, signal } = {}) {
  return mockResult(signal, () => {
    if (
      !Number.isFinite(Number(lat)) ||
      !Number.isFinite(Number(lon)) ||
      Number(lat) < -90 ||
      Number(lat) > 90 ||
      Number(lon) < -180 ||
      Number(lon) > 180 ||
      !Number.isFinite(Number(raioKm)) ||
      Number(raioKm) <= 0 ||
      Number(raioKm) > 1000
    ) {
      throw validationError("Coordenadas ou raio inválidos.");
    }

    return mockStations
      .map((station) => ({
        ...station,
        distancia_km: distanceInKm(
          Number(lat),
          Number(lon),
          station.latitude,
          station.longitude,
        ),
      }))
      .filter((station) => station.distancia_km <= Number(raioKm))
      .sort((first, second) => first.distancia_km - second.distancia_km);
  });
}

export function mockGetStation(codigo, { signal } = {}) {
  return mockResult(signal, () => {
    const station = mockStations.find((item) => item.codigo === Number(codigo));
    if (!station) throw notFound(`Estação ${codigo} não encontrada.`);
    return station;
  });
}

export function mockGetMonthlyRain(codigo, { signal } = {}) {
  return mockResult(signal, () => {
    const station = mockStations.find((item) => item.codigo === Number(codigo));
    if (!station) throw notFound(`Estação ${codigo} não encontrada.`);
    if (!station.grandezas.includes("CHUVA")) {
      throw validationError(`A estação ${codigo} não mede chuva.`);
    }
    const agora = new Date();
    return {
      codigo_estacao: station.codigo,
      ano: agora.getFullYear(),
      mes: agora.getMonth() + 1,
      acumulado_mm: 182.4,
      medicoes: 640,
      normal_mm: 141.2,
      percentual: 129.2,
      classificacao: "ACIMA",
      classificacao_rotulo: "Acima do normal",
      referencia: {
        codigo: "83781",
        nome: "SÃO PAULO (MIRANTE)",
        uf: "SP",
        latitude: -23.5,
        longitude: -46.62,
        distancia_km: 3.2,
      },
    };
  });
}

export function mockGetStationLimits(codigo, { signal } = {}) {
  return mockResult(signal, () => {
    const station = mockStations.find((item) => item.codigo === Number(codigo));
    if (!station) throw notFound(`Estação ${codigo} não encontrada.`);
    const limitsByStation = {
      90000001: [
        {
          grandeza: "NIVEL",
          tipo: "COTA",
          descricao: "Cotas ilustrativas de referência",
          unidade: "cm",
          janela_horas: null,
          atencao: 300,
          alerta: 400,
          emergencia: 500,
        },
      ],
      90000002: [
        {
          grandeza: "CHUVA",
          tipo: "CHUVA_ACUMULADA",
          descricao: "Limites de chuva de demonstração",
          unidade: "mm",
          janela_horas: 24,
          atencao: 30,
          alerta: 50,
          emergencia: 80,
        },
      ],
      90000003: [
        {
          grandeza: "NIVEL",
          tipo: "COTA",
          descricao: "Cotas ilustrativas de referência",
          unidade: "cm",
          janela_horas: null,
          atencao: 250,
          alerta: 320,
          emergencia: 400,
        },
      ],
      90000004: [
        {
          grandeza: "CHUVA",
          tipo: "CHUVA_ACUMULADA",
          descricao: "Limites de chuva acumulada",
          unidade: "mm",
          janela_horas: 24,
          atencao: 30,
          alerta: 50,
          emergencia: 80,
        },
        {
          grandeza: "CHUVA",
          tipo: "CHUVA_PREVISTA",
          descricao: "Limites de chuva prevista",
          unidade: "mm",
          janela_horas: 24,
          atencao: 30,
          alerta: 50,
          emergencia: 80,
        },
      ],
    };
    return limitsByStation[station.codigo] || [];
  });
}

export function mockListStationMeasurements(
  codigo,
  { grandeza, inicio, fim, signal } = {},
) {
  return mockResult(signal, () => {
    const station = mockStations.find((item) => item.codigo === Number(codigo));
    if (!station) throw notFound(`Estação ${codigo} não encontrada.`);
    const unit = units[grandeza];
    if (!unit || !station.grandezas.includes(grandeza)) {
      throw validationError(
        "Grandeza inválida ou não disponível para a estação.",
      );
    }

    const end = fim ? new Date(fim) : new Date();
    const start = inicio
      ? new Date(inicio)
      : new Date(end.getTime() - 24 * 60 * 60 * 1000);
    const duration = end.getTime() - start.getTime();
    const maxDuration = 31 * 24 * 60 * 60 * 1000;
    if (
      Number.isNaN(start.getTime()) ||
      Number.isNaN(end.getTime()) ||
      duration < 0 ||
      duration > maxDuration
    ) {
      throw validationError("Período inválido para consultar medições.");
    }

    const hour = 60 * 60 * 1000;
    const measurements = [];
    const valueByGrandeza = {
      CHUVA: (index) => (index % 4) * 0.5,
      NIVEL: (index) => 430 + (index % 7) * 2,
      VAZAO: (index) => 18 + (index % 5) * 1.5,
    };
    for (
      let timestamp = start.getTime();
      timestamp <= end.getTime();
      timestamp += hour
    ) {
      const index = measurements.length;
      const value = valueByGrandeza[grandeza](index);

      measurements.push({
        data_hora_utc: new Date(timestamp).toISOString(),
        valor: value,
        consistencia: index % 2 === 0 ? "CONSISTIDO" : "BRUTO",
        status_fonte: "DADO_FICTICIO",
        origem: "TELEMETRICA",
        atualizado_na_fonte_em: new Date(timestamp).toISOString(),
      });
    }

    return {
      codigo_estacao: station.codigo,
      grandeza,
      grandeza_rotulo: unit.label,
      unidade: unit.unit,
      inicio: start.toISOString(),
      fim: end.toISOString(),
      medicoes: measurements,
    };
  });
}

export function mockGetMunicipalitySituation(uf, nome, { signal } = {}) {
  return mockResult(signal, () => {
    const stations = mockStations
      .filter(
        (station) =>
          station.uf === uf.toUpperCase() &&
          normalizedText(station.municipio) === normalizedText(nome),
      )
      .sort(
        (first, second) =>
          severityRank[second.severidade] - severityRank[first.severidade] ||
          first.codigo - second.codigo,
      );
    if (stations.length === 0) {
      throw notFound(`Município ${nome}, ${uf.toUpperCase()} não encontrado.`);
    }

    const worstStation = stations.reduce(
      (worst, station) =>
        severityRank[station.severidade] > severityRank[worst.severidade]
          ? station
          : worst,
      stations[0],
    );

    return {
      uf: uf.toUpperCase(),
      municipio: stations[0].municipio,
      severidade: worstStation.severidade,
      severidade_rotulo: worstStation.severidade_rotulo,
      estacoes: stations,
    };
  });
}

export function mockListActiveAlerts({ signal } = {}) {
  return mockResult(signal, () => mockAlerts);
}

export function mockListStationAlertHistory(
  codigo,
  { limite = 50, signal } = {},
) {
  return mockResult(signal, () => {
    const station = mockStations.find((item) => item.codigo === Number(codigo));
    if (!station)
      throw notFound(`Esta\u00e7\u00e3o ${codigo} n\u00e3o encontrada.`);
    if (
      !Number.isInteger(Number(limite)) ||
      Number(limite) < 1 ||
      Number(limite) > 500
    ) {
      throw validationError("O limite deve estar entre 1 e 500.");
    }
    return mockAlerts
      .filter((alert) => alert.codigo_estacao === station.codigo)
      .slice(0, Number(limite));
  });
}
