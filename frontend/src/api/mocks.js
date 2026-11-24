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

const mockStations = [
  {
    codigo: 90000001,
    nome: "Estação Rio Pinheiros",
    tipo: "FLUVIOMETRICA",
    latitude: -23.5613,
    longitude: -46.7303,
    uf: "SP",
    municipio: "São Paulo",
    rio: "Pinheiros",
    operando: true,
    telemetrica: true,
    grandezas: ["NIVEL", "VAZAO"],
    severidade: "ALERTA",
    severidade_rotulo: "Alerta",
    alerta: mockAlert,
  },
  {
    codigo: 90000002,
    nome: "Estação Ribeirão Jaguaré",
    tipo: "FLUVIOMETRICA",
    latitude: -23.564,
    longitude: -46.744,
    uf: "SP",
    municipio: "São Paulo",
    rio: "Jaguaré",
    operando: true,
    telemetrica: true,
    grandezas: ["NIVEL"],
    severidade: "ATENCAO",
    severidade_rotulo: "Atenção",
    alerta: null,
  },
  {
    codigo: 90000003,
    nome: "Estação Rio Tietê",
    tipo: "FLUVIOMETRICA",
    latitude: -23.525,
    longitude: -46.625,
    uf: "SP",
    municipio: "São Paulo",
    rio: "Tietê",
    operando: true,
    telemetrica: true,
    grandezas: ["NIVEL", "VAZAO"],
    severidade: "NORMAL",
    severidade_rotulo: "Normal",
    alerta: null,
  },
  {
    codigo: 90000004,
    nome: "Estação Rio das Velhas",
    tipo: "FLUVIOMETRICA",
    latitude: -19.9167,
    longitude: -43.9345,
    uf: "MG",
    municipio: "Belo Horizonte",
    rio: "Rio das Velhas",
    operando: true,
    telemetrica: true,
    grandezas: ["NIVEL", "VAZAO"],
    severidade: "NORMAL",
    severidade_rotulo: "Normal",
    alerta: null,
  },
  {
    codigo: 90000005,
    nome: "Estação Pluviométrica Central",
    tipo: "PLUVIOMETRICA",
    latitude: -23.5489,
    longitude: -46.6388,
    uf: "SP",
    municipio: "São Paulo",
    rio: null,
    operando: true,
    telemetrica: true,
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
  const error = new Error(message);
  error.name = "ApiError";
  error.status = 404;
  return error;
}

function validationError(message) {
  const error = new Error(message);
  error.name = "ApiError";
  error.status = 422;
  return error;
}

export function mockHealth({ signal } = {}) {
  return mockResult(signal, () => ({ status: "ok" }));
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

    const query = normalizedText(trimmedQuery);

    return mockStations.filter((station) => {
      if (uf && station.uf !== uf.toUpperCase()) return false;
      if (tipo && station.tipo !== tipo) return false;
      if (apenasTelemetricas && !station.telemetrica) return false;
      if (!query) return true;

      return [station.nome, station.municipio, station.rio].some((value) =>
        normalizedText(value).includes(query),
      );
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
    for (
      let timestamp = start.getTime();
      timestamp <= end.getTime();
      timestamp += hour
    ) {
      const index = measurements.length;
      const value =
        grandeza === "CHUVA"
          ? (index % 4) * 0.5
          : grandeza === "NIVEL"
            ? 430 + (index % 7) * 2
            : 18 + (index % 5) * 1.5;

      measurements.push({
        data_hora_utc: new Date(timestamp).toISOString(),
        valor: value,
        consistencia: index % 2 === 0 ? "CONSISTIDO" : "BRUTO",
        status_fonte: "DADO_FICTICIO",
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
    const stations = mockStations.filter(
      (station) =>
        station.uf === uf.toUpperCase() &&
        normalizedText(station.municipio) === normalizedText(nome),
    );
    if (stations.length === 0) {
      throw notFound(`Município ${nome}, ${uf.toUpperCase()} não encontrado.`);
    }

    const worstStation = stations.reduce((worst, station) =>
      severityRank[station.severidade] > severityRank[worst.severidade]
        ? station
        : worst,
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
  return mockResult(signal, () => [mockAlert]);
}
