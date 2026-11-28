import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import {
  listarEstacoes,
  listarEstacoesProximas,
  usaApiReal,
} from "../api/cliente";

const stationSeverities = {
  NORMAL: { abbreviation: "N", className: "normal" },
  ATENCAO: { abbreviation: "A", className: "atencao" },
  ALERTA: { abbreviation: "AL", className: "alerta" },
  EMERGENCIA: { abbreviation: "E", className: "emergencia" },
};

const RAIO_BUSCA_PROXIMA_KM = 5;

const stateOptions = [
  ["AC", "Acre"],
  ["AL", "Alagoas"],
  ["AP", "Amapá"],
  ["AM", "Amazonas"],
  ["BA", "Bahia"],
  ["CE", "Ceará"],
  ["DF", "Distrito Federal"],
  ["ES", "Espírito Santo"],
  ["GO", "Goiás"],
  ["MA", "Maranhão"],
  ["MT", "Mato Grosso"],
  ["MS", "Mato Grosso do Sul"],
  ["MG", "Minas Gerais"],
  ["PA", "Pará"],
  ["PB", "Paraíba"],
  ["PR", "Paraná"],
  ["PE", "Pernambuco"],
  ["PI", "Piauí"],
  ["RJ", "Rio de Janeiro"],
  ["RN", "Rio Grande do Norte"],
  ["RS", "Rio Grande do Sul"],
  ["RO", "Rondônia"],
  ["RR", "Roraima"],
  ["SC", "Santa Catarina"],
  ["SP", "São Paulo"],
  ["SE", "Sergipe"],
  ["TO", "Tocantins"],
];

function stationIcon(severity) {
  const style = stationSeverities[severity] || stationSeverities.NORMAL;
  return L.divIcon({
    className: `station-marker station-marker-${style.className}`,
    html: `<span aria-hidden="true">${style.abbreviation}</span>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  });
}

function stationCoordinates(station) {
  const latitude = Number(station.latitude);
  const longitude = Number(station.longitude);
  const invalidCoordinates =
    !Number.isFinite(latitude) ||
    !Number.isFinite(longitude) ||
    latitude < -90 ||
    latitude > 90 ||
    longitude < -180 ||
    longitude > 180 ||
    (latitude === 0 && longitude === 0);

  return invalidCoordinates ? null : [latitude, longitude];
}

function stationMarker(station, onSelectStation) {
  const coordinates = stationCoordinates(station);
  if (!coordinates) return null;

  const severity = station.severidade_rotulo || "Normal";
  const name = station.nome || `Estação ${station.codigo}`;
  const popup = document.createElement("div");
  const title = document.createElement("strong");
  title.textContent = name;
  popup.appendChild(title);

  const municipality = [station.municipio, station.uf]
    .filter(Boolean)
    .join(" — ");
  const details = [
    municipality,
    station.rio && `Rio: ${station.rio}`,
    `Situação: ${severity}`,
    station.alerta?.mensagem,
  ].filter(Boolean);
  details.forEach((detail) => {
    const row = document.createElement("div");
    row.textContent = detail;
    popup.appendChild(row);
  });

  return L.marker(coordinates, {
    icon: stationIcon(station.severidade),
    title: `${name} — ${severity}`,
    alt: `${name}, severidade ${severity}`,
  })
    .bindPopup(popup)
    .on("click", () => onSelectStation?.(station));
}

function stationSearchSummary(
  total,
  withCoordinates,
  withoutCoordinates,
  shown,
  uf,
) {
  if (total === 0) return "Nenhuma estação encontrada.";
  if (withCoordinates === 0) {
    return `Foram encontradas ${total} estações, mas nenhuma tem coordenadas válidas para exibir.`;
  }
  if (withCoordinates > shown && withoutCoordinates > 0) {
    return `Exibindo ${shown} de ${withCoordinates} estações com coordenadas válidas em ${uf}; ${withoutCoordinates} sem coordenadas válidas.`;
  }
  if (withCoordinates > shown) {
    return `Exibindo ${shown} de ${withCoordinates} estações com coordenadas válidas em ${uf}. Refine a busca para ver outras.`;
  }
  if (withoutCoordinates > 0) {
    return `${shown} estação(ões) exibida(s) em ${uf}; ${withoutCoordinates} sem coordenadas válidas.`;
  }
  return `${shown} estação(ões) encontrada(s) em ${uf}. Selecione um marcador para ver os detalhes.`;
}

function savedPlaceIcon() {
  return L.divIcon({
    className: "saved-place-marker",
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  });
}

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, (character) => {
    const entities = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return entities[character];
  });
}

export default function MapView({
  mapRef,
  mapViewRef,
  savedPlaces,
  searchInputRef,
  searchQuery,
  onSearchChange,
  onSearch,
  onSelectStation,
}) {
  const mapContainerRef = useRef(null);
  const stationLayerRef = useRef(null);
  const stationRequestRef = useRef(null);
  const [selectedUf, setSelectedUf] = useState("SP");
  const [searchStatus, setSearchStatus] = useState({
    message: "",
    state: "empty",
  });
  const [isLocating, setIsLocating] = useState(false);
  const searchIndicator =
    searchStatus.message &&
    {
      loading: {
        icon: "fa-spinner fa-spin text-sky-700",
      },
      error: { icon: "fa-circle-exclamation text-red-600" },
      empty: {
        icon: "fa-circle-info text-amber-600",
      },
    }[searchStatus.state];

  useEffect(() => {
    const mobileBreakpoint = window.matchMedia("(max-width: 767px)");
    const mapInstance = L.map(mapContainerRef.current, {
      center: [-23.5613, -46.7303],
      zoom: 14,
      zoomControl: false,
      scrollWheelZoom: !mobileBreakpoint.matches,
    });

    const syncScrollWheelZoom = () => {
      if (mobileBreakpoint.matches) {
        mapInstance.scrollWheelZoom.disable();
      } else {
        mapInstance.scrollWheelZoom.enable();
      }
    };
    window.addEventListener("resize", syncScrollWheelZoom);

    mapRef.current = mapInstance;

    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(mapInstance);

    stationLayerRef.current = L.featureGroup().addTo(mapInstance);

    mapInstance.whenReady(() => mapInstance.invalidateSize());

    return () => {
      window.removeEventListener("resize", syncScrollWheelZoom);
      stationRequestRef.current?.abort();
      stationLayerRef.current = null;
      mapRef.current = null;
      mapInstance.remove();
    };
  }, [mapRef]);

  const handleSearch = async (event) => {
    event.preventDefault();
    stationRequestRef.current?.abort();
    setIsLocating(false);

    const query = searchQuery.trim();
    onSelectStation?.(null);
    const normalizedQuery = query.toLocaleLowerCase("pt-BR");
    const matchingPlaces =
      query.length >= 2
        ? savedPlaces.filter((place) =>
            place.name.toLocaleLowerCase("pt-BR").includes(normalizedQuery),
          )
        : [];

    if (matchingPlaces.length === 1) {
      const place = matchingPlaces[0];
      onSearch(event);
      setSearchStatus({
        message: `Mapa centralizado em “${place.name}”.`,
        state: "success",
      });
      return;
    }

    if (query.length < 2) {
      setSearchStatus({
        message: "Informe ao menos 2 caracteres para pesquisar.",
        state: "error",
      });
      searchInputRef.current?.focus();
      return;
    }

    const request = new AbortController();
    stationRequestRef.current = request;
    setSearchStatus({
      message: `Buscando “${query}” em ${selectedUf}...`,
      state: "loading",
    });

    try {
      const stations = await listarEstacoes({
        texto: query,
        uf: selectedUf,
        apenasTelemetricas: true,
        signal: request.signal,
      });
      if (request.signal.aborted) return;

      const stationsWithCoordinates = stations.filter((station) =>
        stationCoordinates(station),
      );
      const stationsWithoutCoordinates =
        stations.length - stationsWithCoordinates.length;
      const stationsToShow =
        stationsWithCoordinates.length > 100
          ? Array.from(
              { length: 100 },
              (_, index) =>
                stationsWithCoordinates[
                  Math.floor((index * stationsWithCoordinates.length) / 100)
                ],
            )
          : stationsWithCoordinates;
      const layer = stationLayerRef.current;
      if (!layer) return;

      layer.clearLayers();
      stationsToShow.forEach((station) => {
        const marker = stationMarker(station, onSelectStation);
        if (marker) layer.addLayer(marker);
      });

      const bounds = layer.getBounds();
      if (bounds.isValid()) {
        mapRef.current?.fitBounds(bounds, { padding: [40, 40], maxZoom: 11 });
      }

      setSearchStatus({
        message: stationSearchSummary(
          stations.length,
          stationsWithCoordinates.length,
          stationsWithoutCoordinates,
          layer.getLayers().length,
          selectedUf,
        ),
        state: layer.getLayers().length > 0 ? "success" : "empty",
      });
      searchInputRef.current?.blur();
    } catch (error) {
      if (error.name === "AbortError") return;
      setSearchStatus({
        message: `Não foi possível carregar as estações: ${error.message}`,
        state: "error",
      });
    }
  };

  const handleNearbySearch = () => {
    stationRequestRef.current?.abort();
    onSelectStation?.(null);
    setIsLocating(false);
    searchInputRef.current?.setCustomValidity("");
    onSearchChange("");

    if (!navigator.geolocation) {
      setSearchStatus({
        message: "Este navegador não oferece suporte à localização.",
        state: "error",
      });
      return;
    }

    const request = new AbortController();
    stationRequestRef.current = request;
    setIsLocating(true);
    setSearchStatus({
      message: "Obtendo sua localização…",
      state: "loading",
    });
    stationLayerRef.current?.clearLayers();

    navigator.geolocation.getCurrentPosition(
      async ({ coords }) => {
        if (request.signal.aborted) return;

        setSearchStatus({
          message: `Buscando estações em até ${RAIO_BUSCA_PROXIMA_KM} km…`,
          state: "loading",
        });

        try {
          const stations = await listarEstacoesProximas({
            lat: coords.latitude,
            lon: coords.longitude,
            raioKm: RAIO_BUSCA_PROXIMA_KM,
            signal: request.signal,
          });
          if (request.signal.aborted) return;

          const layer = stationLayerRef.current;
          const map = mapRef.current;
          if (!layer || !map) return;

          const locationMarker = L.circleMarker(
            [coords.latitude, coords.longitude],
            {
              radius: 8,
              color: "#ffffff",
              weight: 3,
              fillColor: "#0284c7",
              fillOpacity: 1,
            },
          ).bindPopup("Sua localização");
          layer.addLayer(locationMarker);

          const stationsWithCoordinates = stations.filter((station) =>
            stationCoordinates(station),
          );
          stationsWithCoordinates.forEach((station) => {
            const marker = stationMarker(station, onSelectStation);
            if (marker) {
              marker.bindTooltip(`${station.distancia_km} km`, {
                direction: "top",
                offset: [0, -14],
              });
              layer.addLayer(marker);
            }
          });

          const bounds = layer.getBounds();
          if (bounds.isValid()) {
            map.fitBounds(bounds, { padding: [40, 40], maxZoom: 12 });
          }

          const stationCount = layer.getLayers().length - 1;
          const stationCountLabel = new Intl.NumberFormat("pt-BR").format(
            stationCount,
          );
          setSearchStatus({
            message:
              stationCount === 0
                ? `Nenhuma estação encontrada em até ${RAIO_BUSCA_PROXIMA_KM} km da sua localização.`
                : `${stationCountLabel} ${stationCount === 1 ? "estação encontrada" : "estações encontradas"} em até ${RAIO_BUSCA_PROXIMA_KM} km da sua localização.`,
            state: stationCount === 0 ? "empty" : "success",
          });
          searchInputRef.current?.blur();
        } catch (error) {
          if (error.name === "AbortError") return;
          setSearchStatus({
            message: `Não foi possível carregar as estações próximas: ${error.message}`,
            state: "error",
          });
        } finally {
          if (!request.signal.aborted) setIsLocating(false);
        }
      },
      (error) => {
        if (request.signal.aborted) return;

        const messages = {
          1: "Permita o acesso à localização para encontrar estações próximas.",
          2: "Não foi possível determinar sua localização. Tente novamente.",
          3: "A localização demorou demais. Tente novamente.",
        };
        setSearchStatus({
          message:
            messages[error.code] || "Não foi possível obter sua localização.",
          state: "error",
        });
        setIsLocating(false);
      },
      { enableHighAccuracy: false, timeout: 15000, maximumAge: 60000 },
    );
  };

  const handleUfChange = (event) => {
    const uf = event.target.value;
    setSelectedUf(uf);
    stationRequestRef.current?.abort();
    onSelectStation?.(null);
    setIsLocating(false);
    stationLayerRef.current?.clearLayers();
    searchInputRef.current?.setCustomValidity("");
    onSearchChange("");
    setSearchStatus({
      message: "",
      state: "empty",
    });
  };

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return undefined;

    const markers = savedPlaces.map((place) => {
      return L.marker(place.center, {
        icon: savedPlaceIcon(),
      })
        .addTo(map)
        .bindTooltip(escapeHtml(place.name), {
          permanent: true,
          direction: "top",
          offset: [0, -8],
          className: "city-label",
        })
        .bindPopup(`<strong>${escapeHtml(place.name)}</strong>`);
    });

    return () => {
      markers.forEach((marker) => {
        if (map.hasLayer(marker)) map.removeLayer(marker);
      });
    };
  }, [mapRef, savedPlaces]);

  return (
    <main
      ref={mapViewRef}
      className="app-main mobile-map-view flex-1 h-full relative z-0 bg-[#eaf4f8]"
    >
      <div className="map-search-controls">
        <div className="map-state-filter mb-2 flex items-center gap-2 rounded-2xl bg-white px-3 py-2 text-xs shadow-lg">
          <label
            htmlFor="stateInput"
            className="shrink-0 font-semibold text-slate-600"
          >
            Estado das estações
          </label>
          <select
            id="stateInput"
            value={selectedUf}
            onChange={handleUfChange}
            className="min-w-0 flex-1 rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-sm text-slate-800 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
          >
            {stateOptions.map(([uf, name]) => (
              <option key={uf} value={uf}>
                {name} ({uf})
              </option>
            ))}
          </select>
          {!usaApiReal && (
            <span
              className="demo-data-badge"
              title="Dados de demonstração: não representam alertas reais."
              aria-label="Dados de demonstração"
            >
              DEMO
            </span>
          )}
        </div>
        <form
          role="search"
          className="map-search-form relative flex items-center"
          onSubmit={handleSearch}
        >
          <i
            className={`fa-solid ${searchIndicator?.icon || "fa-magnifying-glass text-slate-400"} absolute left-3.5 text-sm`}
            title={searchIndicator ? searchStatus.message : undefined}
            aria-hidden="true"
          />
          <input
            ref={searchInputRef}
            type="text"
            value={searchQuery}
            onChange={(event) => onSearchChange(event.target.value)}
            aria-label="Buscar local salvo, estação por cidade, nome ou rio"
            placeholder="Local salvo, município, estação ou rio..."
            maxLength={100}
            className="w-full rounded-2xl border border-slate-200 bg-white py-3 pl-10 pr-28 text-sm shadow-lg transition placeholder:text-slate-400 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
          />
          <button
            type="button"
            onClick={handleNearbySearch}
            disabled={isLocating}
            className="absolute right-20 rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-sky-700 disabled:cursor-wait disabled:opacity-60"
            title="Encontrar estações perto de mim"
            aria-label="Encontrar estações perto de mim"
          >
            <i
            className={`fa-solid ${
              isLocating ? "fa-spinner fa-spin" : "fa-location-arrow"
            } text-xs`}
              aria-hidden="true"
            />
          </button>
          <button
            type="submit"
            className="absolute right-2 rounded-xl bg-sky-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-sky-800"
          >
            Buscar
          </button>
        </form>
        {["loading", "error", "empty"].includes(searchStatus.state) &&
          searchStatus.message && (
            <output
              className={`map-search-feedback map-search-feedback-${searchStatus.state}`}
              aria-live={
                searchStatus.state === "error" ? "assertive" : "polite"
              }
            >
              <i
                className={`fa-solid ${searchIndicator?.icon || "fa-circle-info"}`}
                aria-hidden="true"
              />
              {searchStatus.message}
            </output>
          )}
      </div>
      <div
        ref={mapContainerRef}
        className="interactive-map"
        role="application"
        aria-label="Mapa interativo de estações hidrológicas e locais salvos"
      />
    </main>
  );
}
