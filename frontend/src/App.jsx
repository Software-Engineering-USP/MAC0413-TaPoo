import { useEffect, useState } from "react";
import L from "leaflet";
import { listarEstacoes } from "./api/estacoes.js";

const severidadesEstacao = {
  NORMAL: { abreviacao: "N", classe: "normal" },
  ATENCAO: { abreviacao: "A", classe: "atencao" },
  ALERTA: { abreviacao: "AL", classe: "alerta" },
  EMERGENCIA: { abreviacao: "E", classe: "emergencia" },
};

function iconeEstacao(severidade) {
  const estilo = severidadesEstacao[severidade] || severidadesEstacao.NORMAL;
  return L.divIcon({
    className: `station-marker station-marker-${estilo.classe}`,
    html: `<span aria-hidden="true">${estilo.abreviacao}</span>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  });
}

const emergencyContacts = [
  { number: "112", service: "Emergência" },
  { number: "190", service: "Polícia Militar" },
  { number: "192", service: "SAMU" },
  { number: "193", service: "Corpo de Bombeiros" },
  { number: "199", service: "Defesa Civil" },
];

function CivilDefenseWarning() {
  return (
    <div
      role="note"
      aria-label="Aviso sobre alertas oficiais"
      className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-amber-950"
    >
      <div className="flex items-start gap-2">
        <i
          className="fa-solid fa-triangle-exclamation mt-0.5 text-amber-700"
          aria-hidden="true"
        ></i>
        <p className="flex-1 text-xs font-medium leading-relaxed">
          <strong>Aviso:</strong> Este sistema não substitui os alertas oficiais
          da Defesa Civil. Em uma emergência, acompanhe os canais oficiais.
        </p>
      </div>
    </div>
  );
}

export default function App() {
  const [isInfoSheetOpen, setInfoSheetOpen] = useState(false);

  const openInfoSheet = () => {
    const appShell = document.getElementById("root");
    const mapView = document.querySelector(".mobile-map-view");
    if (!appShell || !mapView) return;

    setInfoSheetOpen(true);
    requestAnimationFrame(() => {
      const scrollOffset =
        mapView.offsetHeight - Math.min(180, appShell.clientHeight * 0.35);
      appShell.scrollTo({ top: scrollOffset, behavior: "smooth" });
    });
  };

  const closeInfoSheet = () => {
    setInfoSheetOpen(false);
    document.getElementById("root")?.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  };

  useEffect(() => {
    const appShell = document.getElementById("root");
    const mapView = document.querySelector(".mobile-map-view");
    if (!appShell || !mapView) return;

    const syncInfoSheetState = () => {
      const isMobile = window.matchMedia("(max-width: 767px)").matches;
      setInfoSheetOpen(isMobile && appShell.scrollTop > 0);
    };

    appShell.addEventListener("scroll", syncInfoSheetState, { passive: true });
    window.addEventListener("resize", syncInfoSheetState);
    syncInfoSheetState();

    return () => {
      appShell.removeEventListener("scroll", syncInfoSheetState);
      window.removeEventListener("resize", syncInfoSheetState);
    };
  }, []);

  useEffect(() => {
    const infoBtn = document.getElementById("infoBtn");
    const infoModal = document.getElementById("infoModal");
    const closeModal = document.getElementById("closeModal");
    const okModalBtn = document.getElementById("okModalBtn");
    const savedLocationsContainer = document.getElementById(
      "savedLocationsContainer",
    );
    const saveLocationBtn = document.getElementById("saveLocationBtn");
    const saveLocationButtons = document.querySelectorAll(".save-location-btn");
    const savedPlaceKey = "aquaWatchSavedPlaces";

    // Custom Modals References
    const promptModal = document.getElementById("promptModal");
    const promptInput = document.getElementById("promptInput");
    const promptOk = document.getElementById("promptOk");
    const promptCancel = document.getElementById("promptCancel");

    const confirmModal = document.getElementById("confirmModal");
    const confirmMessage = document.getElementById("confirmMessage");
    const confirmOk = document.getElementById("confirmOk");
    const confirmCancel = document.getElementById("confirmCancel");

    let promptCallback = null;
    let confirmCallback = null;

    const showPromptModal = (callback) => {
      promptInput.value = "Novo local";
      promptModal.classList.remove("hidden");
      promptInput.focus();
      promptCallback = callback;
    };

    promptOk.addEventListener("click", () => {
      promptModal.classList.add("hidden");
      if (promptCallback) promptCallback(promptInput.value);
    });
    promptCancel.addEventListener("click", () =>
      promptModal.classList.add("hidden"),
    );

    const showConfirmModal = (message, callback) => {
      confirmMessage.textContent = message;
      confirmModal.classList.remove("hidden");
      confirmCallback = callback;
    };

    confirmOk.addEventListener("click", () => {
      confirmModal.classList.add("hidden");
      if (confirmCallback) confirmCallback();
    });
    confirmCancel.addEventListener("click", () =>
      confirmModal.classList.add("hidden"),
    );

    // Leaflet Map Initialization
    const map = L.map("interactiveMap", {
      center: [-23.5613, -46.7303],
      zoom: 14,
      zoomControl: false,
      scrollWheelZoom: true,
    });

    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);

    const floodRiskLayer = L.layerGroup().addTo(map);
    const stationLayer = L.featureGroup().addTo(map);
    const stationSearchStatus = document.getElementById("stationSearchStatus");
    let stationRequest;

    const renderStationMarkers = (stations, ajustarEnquadramento = false) => {
      stationLayer.clearLayers();
      let markersRendered = 0;
      stations.forEach((station) => {
        const latitude = Number(station.latitude);
        const longitude = Number(station.longitude);
        if (
          !Number.isFinite(latitude) ||
          !Number.isFinite(longitude) ||
          latitude < -90 ||
          latitude > 90 ||
          longitude < -180 ||
          longitude > 180 ||
          (latitude === 0 && longitude === 0)
        ) {
          return;
        }

        const severidade = station.severidade_rotulo || "Normal";
        const nome = station.nome || `Estação ${station.codigo}`;
        const marker = L.marker([latitude, longitude], {
          icon: iconeEstacao(station.severidade),
          title: `${nome} — ${severidade}`,
          alt: `${nome}, severidade ${severidade}`,
        });

        const popup = document.createElement("div");
        const titulo = document.createElement("strong");
        titulo.textContent = nome;
        popup.appendChild(titulo);

        const detalhes = [
          station.municipio && station.uf
            ? `${station.municipio} — ${station.uf}`
            : station.uf,
          station.rio && `Rio: ${station.rio}`,
          `Situação: ${severidade}`,
          station.alerta?.mensagem,
        ].filter(Boolean);
        detalhes.forEach((detalhe) => {
          const linha = document.createElement("div");
          linha.textContent = detalhe;
          popup.appendChild(linha);
        });
        marker.bindPopup(popup);
        stationLayer.addLayer(marker);
        markersRendered += 1;
      });

      const bounds = stationLayer.getBounds();
      if (ajustarEnquadramento && bounds.isValid()) {
        map.fitBounds(bounds, { padding: [40, 40], maxZoom: 11 });
      }
      return markersRendered;
    };

    const carregarEstacoes = async (texto = "") => {
      stationRequest?.abort();
      stationRequest = new AbortController();
      if (stationSearchStatus) {
        stationSearchStatus.textContent = texto
          ? "Buscando estações..."
          : "Carregando estações hidrológicas...";
        stationSearchStatus.dataset.state = "loading";
      }

      try {
        const stations = await listarEstacoes({
          texto,
          signal: stationRequest.signal,
        });
        const markersRendered = renderStationMarkers(stations, true);
        if (stationSearchStatus) {
          stationSearchStatus.textContent = markersRendered
            ? `${markersRendered} estação(ões) encontrada(s). Selecione um marcador para ver os detalhes.`
            : stations.length
              ? "Foram encontradas estações sem coordenadas válidas para exibir."
              : "Nenhuma estação encontrada para essa busca.";
          stationSearchStatus.dataset.state = markersRendered
            ? "success"
            : "empty";
        }
      } catch (error) {
        if (error.name === "AbortError") return;
        if (stationSearchStatus) {
          stationSearchStatus.textContent = `Não foi possível carregar as estações: ${error.message}`;
          stationSearchStatus.dataset.state = "error";
        }
      }
    };

    carregarEstacoes();

    // Render Rivers
    const rivers = [
      {
        name: "Rio Pinheiros",
        osmId: "relation/10340362",
        coordinates: [
          [-23.60919, -46.69878],
          [-23.605879, -46.697909],
          [-23.601167, -46.696267],
          [-23.598427, -46.695216],
          [-23.595888, -46.69436],
          [-23.594412, -46.693869],
          [-23.591907, -46.693022],
          [-23.588194, -46.69169],
          [-23.586725, -46.691518],
          [-23.586259, -46.691576],
          [-23.585291, -46.691795],
          [-23.584617, -46.692069],
          [-23.580299, -46.694541],
          [-23.576758, -46.696567],
          [-23.575763, -46.697318],
          [-23.573833, -46.699294],
          [-23.572427, -46.700823],
          [-23.571871, -46.701306],
          [-23.570385, -46.702271],
          [-23.568817, -46.702985],
          [-23.564503, -46.704443],
          [-23.563573, -46.704819],
          [-23.56296, -46.705151],
          [-23.562036, -46.705833],
          [-23.561104, -46.706692],
          [-23.560384, -46.707637],
          [-23.559497, -46.709347],
          [-23.558555, -46.711266],
          [-23.557946, -46.71255],
          [-23.554345, -46.719905],
          [-23.549774, -46.729237],
          [-23.549075, -46.730558],
          [-23.548299, -46.731663],
          [-23.545741, -46.734571],
          [-23.54436, -46.736077],
        ],
      },
      {
        name: "Ribeirão Jaguaré",
        osmId: "way/227219907",
        coordinates: [
          [-23.564569, -46.754547],
          [-23.563861, -46.753346],
          [-23.56354, -46.752346],
          [-23.562849, -46.749749],
          [-23.562193, -46.749133],
          [-23.558944, -46.747835],
          [-23.558523, -46.74738],
          [-23.558284, -46.746143],
          [-23.558497, -46.74465],
          [-23.558301, -46.743522],
          [-23.55708, -46.742001],
          [-23.556876, -46.739712],
          [-23.554078, -46.734562],
          [-23.552664, -46.732923],
          [-23.551259, -46.732523],
          [-23.549704, -46.732499],
          [-23.549547, -46.732431],
        ],
      },
    ];

    rivers.forEach((river) => {
      L.polyline(river.coordinates, {
        color: "#0284c7",
        weight: 3,
        opacity: 0.9,
        lineCap: "round",
      })
        .addTo(floodRiskLayer)
        .bindTooltip(river.name, {
          permanent: true,
          sticky: true,
          direction: "center",
          className: "river-label",
        })
        .bindPopup(
          `<strong>${river.name}</strong><br><a href="https://www.openstreetmap.org/${river.osmId}" target="_blank" rel="noopener noreferrer">OpenStreetMap waterway</a>`,
        );
    });

    // Render Zones
    const floodZones = [
      {
        name: "Margem do Rio Pinheiros — baixo risco ilustrativo",
        coordinates: [
          [-23.55, -46.721],
          [-23.552, -46.717],
          [-23.557, -46.716],
          [-23.559, -46.72],
          [-23.555, -46.723],
        ],
        color: "#eab308",
        level: "Baixo",
      },
      {
        name: "Várzea do Rio Pinheiros — risco ilustrativo",
        coordinates: [
          [-23.554, -46.711],
          [-23.555, -46.707],
          [-23.561, -46.705],
          [-23.562, -46.709],
          [-23.558, -46.713],
        ],
        color: "#f97316",
        level: "Moderado",
      },
      {
        name: "Baixo vale do Córrego Jaguaré — risco ilustrativo",
        coordinates: [
          [-23.558, -46.747],
          [-23.561, -46.744],
          [-23.566, -46.739],
          [-23.57, -46.742],
          [-23.565, -46.748],
        ],
        color: "#dc2626",
        level: "Alto",
      },
    ];

    floodZones.forEach((zone) => {
      L.polygon(zone.coordinates, {
        color: zone.color,
        weight: 2,
        dashArray: "5 5",
        fillColor: zone.color,
        fillOpacity: 0.22,
      })
        .addTo(floodRiskLayer)
        .bindTooltip(zone.name, {
          sticky: true,
          className: "city-label",
        });
    });

    const getRiskLevel = (coordinates) => {
      const [latitude, longitude] = coordinates;
      const containsPoint = (zone) => {
        let inside = false;
        for (
          let i = 0, j = zone.coordinates.length - 1;
          i < zone.coordinates.length;
          j = i++
        ) {
          const [latI, lonI] = zone.coordinates[i];
          const [latJ, lonJ] = zone.coordinates[j];
          const crossesLatitude = latI > latitude !== latJ > latitude;
          const boundaryLongitude =
            ((lonJ - lonI) * (latitude - latI)) / (latJ - latI) + lonI;
          if (crossesLatitude && longitude < boundaryLongitude)
            inside = !inside;
        }
        return inside;
      };
      return floodZones.find(containsPoint)?.level || "safe";
    };

    map.whenReady(() => map.invalidateSize());

    // Modal Handlers
    infoBtn.addEventListener("click", () =>
      infoModal.classList.remove("hidden"),
    );
    closeModal.addEventListener("click", () =>
      infoModal.classList.add("hidden"),
    );
    okModalBtn.addEventListener("click", () =>
      infoModal.classList.add("hidden"),
    );

    // Saved Locations Data
    const defaultSavedPlaces = [
      {
        name: "Universidade de São Paulo, USP",
        center: [-23.5613, -46.7303],
        zoom: 16,
      },
      {
        name: "Margem do Rio Pinheiros",
        center: [-23.554, -46.72],
        zoom: 15,
      },
      {
        name: "Várzea do Rio Pinheiros",
        center: [-23.558, -46.7095],
        zoom: 15,
      },
      {
        name: "Baixo vale do Ribeirão Jaguaré",
        center: [-23.564, -46.744],
        zoom: 15,
      },
    ];
    const isValidPlace = (place) =>
      place &&
      typeof place.name === "string" &&
      Array.isArray(place.center) &&
      place.center.length === 2 &&
      place.center.every(Number.isFinite) &&
      Number.isFinite(place.zoom);
    let savedPlaces = defaultSavedPlaces;

    try {
      const storedValue = localStorage.getItem(savedPlaceKey);
      if (storedValue === null) {
        localStorage.setItem(savedPlaceKey, JSON.stringify(defaultSavedPlaces));
      } else {
        const storedPlaces = JSON.parse(storedValue);
        if (Array.isArray(storedPlaces) && storedPlaces.every(isValidPlace)) {
          savedPlaces = storedPlaces;
        } else {
          localStorage.setItem(
            savedPlaceKey,
            JSON.stringify(defaultSavedPlaces),
          );
        }
      }
    } catch (error) {
      console.error("Unable to load saved map locations.", error);
    }

    const savedPlaceMarkers = new Map();

    const savedPlaceIcon = (riskLevel) => {
      const riskClasses = {
        Baixo: "low",
        Moderado: "moderate",
        Alto: "high",
      }[riskLevel];
      const riskClassName = riskClasses ? `risk-${riskClasses}` : "";
      return L.divIcon({
        className: ["city-marker", "saved-place-marker", riskClassName]
          .filter(Boolean)
          .join(" "),
        iconSize: [20, 20],
        iconAnchor: [10, 10],
      });
    };

    const handleSavedPlaceRemoval = (event) => {
      const removeButton =
        event.target instanceof Element
          ? event.target.closest("[data-remove-place]")
          : null;
      if (!removeButton) return;

      event.stopPropagation();
      const index = Number(removeButton.dataset.removePlace);
      const place = savedPlaces[index];
      if (!place) return;

      showConfirmModal(`Remover "${place.name}" dos locais salvos?`, () => {
        savedPlaces.splice(index, 1);
        localStorage.setItem(savedPlaceKey, JSON.stringify(savedPlaces));
        renderSavedPlaces();
      });
    };

    savedLocationsContainer.addEventListener("click", handleSavedPlaceRemoval);

    const renderSavedPlaces = () => {
      savedLocationsContainer
        .querySelectorAll(".saved-place-chip")
        .forEach((chip) => chip.remove());
      savedPlaceMarkers.forEach((marker) => marker.remove());
      savedPlaceMarkers.clear();

      savedPlaces.forEach((place, index) => {
        // Create a saved-location chip
        const row = document.createElement("div");
        row.className =
          "saved-place-chip flex items-center justify-between bg-slate-50 border border-slate-100 px-3 py-2 rounded-xl hover:bg-slate-100 hover:border-slate-200 transition cursor-pointer group shadow-sm";

        const nameContainer = document.createElement("div");
        nameContainer.className = "flex flex-col flex-1 min-w-0";

        const nameSpan = document.createElement("span");
        nameSpan.className = "text-xs font-bold text-slate-700 truncate";
        nameSpan.textContent = place.name;
        nameSpan.title = place.name;

        const riskLevel = getRiskLevel(place.center);
        const riskDescription =
          riskLevel === "safe"
            ? "Sem risco simulado"
            : `Risco ${riskLevel.toLowerCase()}`;

        const subtitleSpan = document.createElement("span");
        subtitleSpan.className = `text-[10px] font-medium truncate ${riskLevel === "safe" ? "text-slate-400" : "text-red-500"}`;
        subtitleSpan.textContent = riskDescription;

        nameContainer.appendChild(nameSpan);
        nameContainer.appendChild(subtitleSpan);

        nameContainer.addEventListener("click", () => {
          map.flyTo(place.center, place.zoom);
        });

        const deleteBtn = document.createElement("button");
        deleteBtn.className =
          "text-slate-300 hover:text-red-500 p-1.5 opacity-0 group-hover:opacity-100 transition focus:opacity-100 ml-2 rounded-lg hover:bg-red-50";
        deleteBtn.innerHTML = '<i class="fa-solid fa-trash text-[11px]"></i>';
        deleteBtn.title = "Remover local";
        deleteBtn.dataset.removePlace = index;

        row.appendChild(nameContainer);
        row.appendChild(deleteBtn);
        savedLocationsContainer.insertBefore(row, saveLocationBtn);

        // Map Marker Logic
        const riskDescriptionFull =
          riskLevel === "safe"
            ? "Sem risco indicado nas áreas simuladas"
            : `Risco ${riskLevel.toLowerCase()} simulado`;

        const marker = L.marker(place.center, {
          icon: savedPlaceIcon(riskLevel),
        })
          .addTo(map)
          .bindTooltip(place.name, {
            permanent: true,
            direction: "top",
            offset: [0, -8],
            className: "city-label",
          })
          .bindPopup(
            `<strong>${place.name.replace(
              /[&<>"']/g,
              (character) =>
                ({
                  "&": "&amp;",
                  "<": "&lt;",
                  ">": "&gt;",
                  '"': "&quot;",
                  "'": "&#39;",
                })[character],
            )}</strong><br>${riskDescriptionFull}`,
          );
        savedPlaceMarkers.set(index, marker);
      });
    };

    renderSavedPlaces();

    // Save location functionality using Custom Modal
    const handleSaveLocation = () => {
      showPromptModal((name) => {
        if (!name?.trim()) return;

        const center = map.getCenter();
        const place = {
          name: name.trim().slice(0, 40),
          center: [center.lat, center.lng],
          zoom: map.getZoom(),
        };
        savedPlaces.push(place);
        localStorage.setItem(savedPlaceKey, JSON.stringify(savedPlaces));
        renderSavedPlaces();

        // Keep the new saved location in view
        setTimeout(() => {
          const isMobile = window.matchMedia("(max-width: 767px)").matches;
          savedLocationsContainer.scrollTo({
            [isMobile ? "left" : "top"]: isMobile
              ? savedLocationsContainer.scrollWidth
              : savedLocationsContainer.scrollHeight,
            behavior: "smooth",
          });
        }, 50);
      });
    };
    saveLocationButtons.forEach((button) =>
      button.addEventListener("click", handleSaveLocation),
    );

    document
      .querySelector("#myLocationBtn")
      .addEventListener("click", () =>
        map.flyTo(defaultSavedPlaces[0].center, 16),
      );

    const searchInput = document.getElementById("searchInput");
    const stationSearchForm = document.getElementById("stationSearchForm");
    const handleStationSearch = (event) => {
      event.preventDefault();
      const query = searchInput.value.trim();
      if (query && query.length < 2) {
        stationSearchStatus.textContent = "Digite pelo menos 2 caracteres.";
        stationSearchStatus.dataset.state = "error";
        searchInput.focus();
        return;
      }
      carregarEstacoes(query);
      searchInput.blur();
    };
    stationSearchForm.addEventListener("submit", handleStationSearch);

    return () => {
      savedLocationsContainer.removeEventListener(
        "click",
        handleSavedPlaceRemoval,
      );
      saveLocationButtons.forEach((button) =>
        button.removeEventListener("click", handleSaveLocation),
      );
      stationSearchForm.removeEventListener("submit", handleStationSearch);
      stationRequest?.abort();
      map.remove();
    };
  }, []);

  return (
    <>
      <aside className="app-sidebar w-full md:w-[450px] shrink-0 h-full flex flex-col bg-slate-50 border-r border-slate-200 z-20 shadow-[4px_0_24px_rgba(15,23,42,0.06)] relative">
        <header className="app-header shrink-0 bg-white px-6 pt-5 pb-4 border-b border-slate-200 flex items-center justify-between z-10 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="app-brand-icon w-10 h-10 rounded-xl bg-sky-50 border border-sky-200 flex items-center justify-center text-sky-600 shadow-sm">
              <i className="fa-solid me-0.5 fa-droplet text-lg"></i>
            </div>
            <div>
              <h1 className="app-title font-bold text-slate-900 tracking-tight text-xl leading-tight">
                AquaWatch{" "}
                <span className="text-sky-600 text-[10px] font-bold px-1.5 py-0.5 bg-sky-50 rounded border border-sky-100 align-middle ml-1">
                  WEB
                </span>
              </h1>
            </div>
          </div>
          <button
            id="infoBtn"
            className="w-10 h-10 rounded-full hover:bg-slate-100 flex items-center justify-center text-slate-400 hover:text-slate-600 transition"
            title="Informações do Sistema"
          >
            <i className="fa-regular fa-circle-question text-xl"></i>
          </button>
        </header>

        <div className="saved-places-track">
          <div className="saved-places-heading">
            <div className="flex items-center gap-2">
              <i className="fa-solid fa-bookmark text-sky-600 text-sm"></i>
              <h3 className="text-[13px] font-bold uppercase tracking-wider text-slate-700">
                Meus Locais Salvos
              </h3>
            </div>
            <button
              type="button"
              className="save-location-btn desktop-save-location-btn text-xs text-sky-600 font-bold hover:text-sky-800 hover:underline transition"
            >
              + Salvar Local
            </button>
          </div>
          <div
            id="savedLocationsContainer"
            className="location-chips flex w-full min-w-0 items-center gap-2 overflow-x-auto text-xs"
          >
            <button
              id="saveLocationBtn"
              className="save-location-btn mobile-save-location-btn shrink-0 whitespace-nowrap rounded-full border border-sky-200 bg-white px-2.5 py-1 font-semibold text-[11px] text-sky-700 shadow transition hover:bg-sky-50"
              type="button"
            >
              <i className="fa-solid fa-bookmark mr-1 mobile-save-icon"></i>
              <span className="desktop-save-label">+ Salvar Atual</span>
              <span className="mobile-save-label">Salve um local</span>
            </button>
          </div>
        </div>

        <div
          id="dashboardSheet"
          className="dashboard-sheet min-h-0 flex-1 overflow-y-auto p-5 space-y-5"
        >
          <div className="mobile-sheet-handle">
            <button
              type="button"
              onClick={closeInfoSheet}
              aria-label="Voltar ao mapa"
              className="flex w-full flex-col items-center gap-2 text-slate-400"
            >
              <span className="h-1 w-10 rounded-full bg-slate-300"></span>
              <span className="text-[11px] font-semibold text-slate-500">
                Voltar ao mapa{" "}
                <i className="fa-solid fa-chevron-down ml-1 text-[9px]"></i>
              </span>
            </button>
          </div>

          <div className="high-risk-warning bg-red-50/90 border border-red-200 rounded-2xl p-5 shadow-sm relative overflow-hidden">
            <div className="flex items-center justify-between mb-2">
              <span className="inline-flex items-center px-3 py-1 rounded-full text-[11px] font-bold bg-red-600 text-white shadow-xs">
                <span className="w-1.5 h-1.5 rounded-full bg-white mr-2 animate-ping"></span>
                ALTO RISCO DE ENCHENTE
              </span>
              <span className="text-[11px] uppercase font-bold text-red-700/60 tracking-wider">
                Atualizado há 12m
              </span>
            </div>
            <p className="text-[15px] font-bold text-slate-900 mt-2">
              Bacia do Rio Itajaí-Açu (Blumenau)
            </p>
            <p className="text-xs text-slate-600 mt-1 leading-relaxed">
              Previsão de precipitação elevada acumulada nas próximas 24h. Risco
              de transbordamento contínuo nas áreas de várzea.
            </p>
          </div>

          <CivilDefenseWarning />

          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
              <div className="flex items-center gap-2">
                <i className="fa-solid fa-location-dot text-sky-600 text-lg"></i>
                <h2
                  className="text-base font-bold text-slate-800"
                  id="selectedCityName"
                >
                  Blumenau, SC
                </h2>
              </div>
              <span className="text-[11px] bg-slate-100 text-slate-600 px-2.5 py-1 rounded-full font-medium">
                Bacia Itajaí-Açu
              </span>
            </div>

            <div className="dashboard-grid grid grid-cols-2 gap-4">
              <div className="dashboard-grid-card bg-slate-50 p-3 rounded-xl border border-slate-100">
                <span className="text-[11px] font-medium text-slate-400 block mb-1">
                  CONDIÇÃO ATUAL
                </span>
                <div className="flex items-center gap-3">
                  <i className="fa-solid fa-cloud-showers-heavy text-slate-600 text-2xl"></i>
                  <div>
                    <p className="text-sm font-bold text-slate-800">
                      Chuva Intensa
                    </p>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      48mm nas úl. 6h
                    </p>
                  </div>
                </div>
              </div>

              <div className="dashboard-grid-card bg-slate-50 p-3 rounded-xl border border-slate-100">
                <span className="text-[11px] font-medium text-slate-400 block mb-1">
                  NÍVEL DO RIO
                </span>
                <div className="flex items-center gap-3">
                  <i className="fa-solid fa-water text-sky-600 text-2xl"></i>
                  <div>
                    <p
                      className="text-sm font-bold text-slate-800"
                      id="riverLevel"
                    >
                      8,42 metros
                    </p>
                    <p className="text-[11px] text-red-600 font-bold flex items-center mt-0.5">
                      <i className="fa-solid fa-arrow-trend-up mr-1"></i>{" "}
                      Emergência
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Previsão de Nível de Risco
              </h3>
              <span className="text-[11px] font-bold text-red-600 bg-red-50 px-2 py-0.5 rounded border border-red-100">
                Pico previsto: Dom 08h
              </span>
            </div>

            <div className="relative flex items-center justify-between px-3 py-3">
              <div className="absolute left-7 right-7 top-1/2 transform -translate-y-1/2 h-1 bg-slate-100 z-0"></div>
              <div className="absolute left-7 w-2/3 top-1/2 transform -translate-y-1/2 h-1 bg-gradient-to-r from-red-500 via-red-500 to-orange-400 z-0 rounded-full"></div>

              <div className="relative z-10 flex flex-col items-center">
                <div className="w-6 h-6 rounded-full bg-red-600 border-2 border-white shadow-sm flex items-center justify-center">
                  <div className="w-2 h-2 rounded-full bg-white"></div>
                </div>
                <span className="text-xs font-bold text-slate-800 mt-2">
                  Hoje
                </span>
                <span className="text-[11px] text-slate-400">14h</span>
              </div>

              <div className="relative z-10 flex flex-col items-center">
                <div className="w-7 h-7 rounded-full bg-red-600 border-2 border-white shadow-md flex items-center justify-center ring-4 ring-red-100">
                  <i className="fa-solid fa-triangle-exclamation text-[10px] text-white"></i>
                </div>
                <span className="text-xs font-bold text-red-600 mt-1.5">
                  Sáb
                </span>
                <span className="text-[11px] text-red-500 font-bold">08h</span>
              </div>

              <div className="relative z-10 flex flex-col items-center">
                <div className="w-6 h-6 rounded-full bg-orange-500 border-2 border-white shadow-sm"></div>
                <span className="text-xs font-bold text-slate-800 mt-2">
                  Dom
                </span>
                <span className="text-[11px] text-slate-400">20h</span>
              </div>

              <div className="relative z-10 flex flex-col items-center">
                <div className="w-6 h-6 rounded-full bg-yellow-400 border-2 border-white shadow-sm"></div>
                <span className="text-xs font-bold text-slate-800 mt-2">
                  Seg
                </span>
                <span className="text-[11px] text-slate-400">12h</span>
              </div>
            </div>
          </div>

          <div className="dashboard-grid grid grid-cols-2 gap-4">
            <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2.5">
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                    Alertas Ativos
                  </span>
                  <span className="w-2.5 h-2.5 rounded-full bg-red-500"></span>
                </div>
                <h4 className="text-[13px] font-bold text-slate-800">
                  1 Alerta Ativo
                </h4>
                <p className="text-[11px] text-slate-500 mt-1 leading-snug">
                  Inundação gradual no bairro Vorstadt.
                </p>
              </div>
              <button className="mt-4 w-full py-2 bg-slate-50 hover:bg-slate-100 text-slate-700 font-semibold text-[11px] rounded-xl transition border border-slate-200">
                Ver detalhes
              </button>
            </div>

            <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2.5">
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                    Histórico
                  </span>
                  <i className="fa-solid fa-chart-line text-slate-400 text-sm"></i>
                </div>
                <h4 className="text-[13px] font-bold text-slate-800">
                  Cheias Anteriores
                </h4>
                <p className="text-[11px] text-slate-500 mt-1 leading-snug">
                  Nível similar registrado em 2011 e 1983.
                </p>
              </div>
              <div className="mt-4 flex items-center justify-between text-[11px] text-slate-600 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-100">
                <span className="font-medium">Máx &apos;83: 15.3m</span>
              </div>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <i className="fa-solid fa-users text-slate-500 text-sm"></i>
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600">
                  Relatos da Comunidade
                </h3>
              </div>
              <span className="text-xs text-sky-600 font-bold cursor-pointer hover:underline">
                + Informar
              </span>
            </div>

            <div className="space-y-4">
              <div className="flex items-start gap-3 text-[13px] pb-3 border-b border-slate-100">
                <div className="w-2.5 h-2.5 rounded-full bg-red-500 mt-1 shrink-0"></div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-800">
                      Rua Almirante Tamandaré
                    </span>
                    <span className="text-[11px] text-slate-400 font-medium">
                      há 18 min
                    </span>
                  </div>
                  <p className="text-slate-500 text-xs mt-1">
                    Água começando a cobrir a pista próximo à ponte.
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3 text-[13px]">
                <div className="w-2.5 h-2.5 rounded-full bg-orange-400 mt-1 shrink-0"></div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-800">
                      Bairro Itoupava Norte
                    </span>
                    <span className="text-[11px] text-slate-400 font-medium">
                      há 42 min
                    </span>
                  </div>
                  <p className="text-slate-500 text-xs mt-1">
                    Bueiros transbordando na via principal.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white border border-red-100 rounded-2xl p-5 shadow-sm relative overflow-hidden">
            <div className="absolute -right-4 -bottom-4 text-red-500/5 text-7xl font-bold select-none pointer-events-none">
              <i className="fa-solid fa-truck-medical"></i>
            </div>
            <div className="flex items-center gap-2.5 mb-3">
              <i className="fa-solid fa-truck-medical text-red-600 text-lg"></i>
              <h3 className="text-sm font-bold uppercase tracking-wider text-red-800">
                Acionar Autoridades
              </h3>
            </div>
            <p className="text-xs text-slate-500 mb-4 leading-relaxed">
              Em caso de alagamento, risco de desabamento ou emergência
              imediata, contate os órgãos responsáveis.
            </p>
            <div className="dashboard-grid grid grid-cols-2 gap-3 relative z-10">
              {emergencyContacts.map(({ number, service }) => (
                <a
                  key={number}
                  href={`tel:${number}`}
                  aria-label={`Ligar para ${service}, ${number}`}
                  className="flex min-h-20 flex-col items-center justify-center rounded-xl border border-red-100 bg-red-50 p-3 text-center"
                >
                  <span className="text-lg font-bold leading-tight text-red-800">
                    {number}
                  </span>
                  <span className="mt-1 text-xs font-semibold text-slate-800">
                    {service}
                  </span>
                </a>
              ))}
            </div>
          </div>

          <section
            aria-labelledby="safetyGuidanceHeading"
            className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm"
          >
            <div className="flex items-center gap-2 mb-3">
              <i
                className="fa-solid fa-circle-info text-sky-600"
                aria-hidden="true"
              ></i>
              <h3
                id="safetyGuidanceHeading"
                className="text-sm font-bold uppercase tracking-wider text-slate-700"
              >
                Orientações de segurança
              </h3>
            </div>
            <ul className="space-y-3 text-xs leading-relaxed text-slate-600">
              <li className="flex items-start gap-2">
                <span className="mt-1 text-sky-600" aria-hidden="true">
                  •
                </span>
                <span>
                  Siga as orientações das autoridades locais, como a Defesa
                  Civil e o Corpo de Bombeiros.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="mt-1 text-sky-600" aria-hidden="true">
                  •
                </span>
                <span>
                  Evite contato com água e lama de enchentes. Se for inevitável
                  passar por uma área inundada, use botas impermeáveis e luvas;
                  proteja cortes e arranhões.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="mt-1 text-sky-600" aria-hidden="true">
                  •
                </span>
                <span>
                  Não consuma alimentos que tiveram contato com a água da
                  inundação ou lama. Para beber, use água segura e siga as
                  orientações sanitárias.
                </span>
              </li>
            </ul>
            <div className="mt-4 border-t border-slate-100 pt-3">
              <h4 className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                Fontes oficiais
              </h4>
              <ul className="mt-2 space-y-2 text-xs">
                <li>
                  <a
                    href="https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/e/enchentes"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sky-700 underline decoration-sky-300 underline-offset-2 hover:text-sky-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600"
                  >
                    Ministério da Saúde — Enchentes
                  </a>
                </li>
                <li>
                  <a
                    href="https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/e/enchentes/cuidados-com-a-leptospirose"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sky-700 underline decoration-sky-300 underline-offset-2 hover:text-sky-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600"
                  >
                    Ministério da Saúde — Cuidados com a leptospirose
                  </a>
                </li>
                <li>
                  <a
                    href="https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/e/enchentes/cuidados-com-a-agua"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sky-700 underline decoration-sky-300 underline-offset-2 hover:text-sky-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600"
                  >
                    Ministério da Saúde — Cuidados com a água
                  </a>
                </li>
              </ul>
            </div>
          </section>
        </div>
      </aside>

      <main className="app-main mobile-map-view flex-1 h-full relative z-0 bg-[#eaf4f8]">
        <div className="map-search-controls">
          <form
            id="stationSearchForm"
            role="search"
            className="relative flex items-center"
          >
            <i className="fa-solid fa-magnifying-glass absolute left-3.5 text-slate-400 text-sm"></i>
            <input
              type="text"
              id="searchInput"
              aria-label="Buscar estação por cidade, nome ou rio"
              placeholder="Buscar estação, cidade ou rio..."
              className="w-full rounded-2xl border border-slate-200 bg-white py-3 pl-10 pr-24 text-sm shadow-lg transition placeholder:text-slate-400 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
            />
            <button
              type="button"
              id="myLocationBtn"
              className="absolute right-12 p-1 text-slate-400 hover:text-sky-600"
              title="Minha localização"
              aria-label="Ir para minha localização salva"
            >
              <i className="fa-solid fa-location-arrow text-xs"></i>
            </button>
            <button
              type="submit"
              className="absolute right-2 rounded-xl bg-sky-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-sky-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2"
            >
              Buscar
            </button>
          </form>
          <p
            id="stationSearchStatus"
            className="mt-2 rounded-xl bg-white/95 px-3 py-2 text-xs text-slate-600 shadow"
            role="status"
            aria-live="polite"
            data-state="loading"
          >
            Carregando estações hidrológicas...
          </p>
        </div>
        <div
          id="interactiveMap"
          className="interactive-map"
          role="application"
          aria-label="Mapa interativo de risco de inundação"
        ></div>
      </main>

      <nav className="mobile-bottom-nav" aria-label="Navegação principal">
        <button
          type="button"
          onClick={closeInfoSheet}
          aria-controls="dashboardSheet"
          aria-pressed={!isInfoSheetOpen}
          className={!isInfoSheetOpen ? "active" : ""}
        >
          <i className="fa-solid fa-map-location-dot"></i>
          <span>Mapa</span>
        </button>
        <button
          type="button"
          onClick={openInfoSheet}
          aria-controls="dashboardSheet"
          aria-expanded={isInfoSheetOpen}
          aria-pressed={isInfoSheetOpen}
          className={isInfoSheetOpen ? "active" : ""}
        >
          <i className="fa-solid fa-circle-info"></i>
          <span>Informações</span>
        </button>
      </nav>

      <div
        id="promptModal"
        className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 hidden flex items-center justify-center p-4"
      >
        <div className="bg-white rounded-2xl max-w-xs w-full p-5 shadow-2xl space-y-4 border border-slate-100">
          <h3 className="font-bold text-slate-900 text-sm" id="promptTitle">
            Nome para este local
          </h3>
          <input
            type="text"
            id="promptInput"
            className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:border-sky-500"
            placeholder="Ex: Minha Casa"
          />
          <div className="flex gap-2 justify-end mt-4">
            <button
              id="promptCancel"
              className="px-4 py-2 text-xs font-semibold text-slate-500 hover:bg-slate-100 rounded-lg transition"
            >
              Cancelar
            </button>
            <button
              id="promptOk"
              className="px-4 py-2 text-xs font-semibold text-white bg-sky-600 hover:bg-sky-700 rounded-lg transition"
            >
              Salvar
            </button>
          </div>
        </div>
      </div>

      <div
        id="confirmModal"
        className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 hidden flex items-center justify-center p-4"
      >
        <div className="bg-white rounded-2xl max-w-xs w-full p-5 shadow-2xl space-y-4 border border-slate-100">
          <h3 className="font-bold text-slate-900 text-sm" id="confirmMessage">
            Tem certeza?
          </h3>
          <div className="flex gap-2 justify-end mt-4">
            <button
              id="confirmCancel"
              className="px-4 py-2 text-xs font-semibold text-slate-500 hover:bg-slate-100 rounded-lg transition"
            >
              Cancelar
            </button>
            <button
              id="confirmOk"
              className="px-4 py-2 text-xs font-semibold text-white bg-red-600 hover:bg-red-700 rounded-lg transition"
            >
              Remover
            </button>
          </div>
        </div>
      </div>

      <div
        id="infoModal"
        className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 hidden flex items-center justify-center p-4"
      >
        <div className="bg-white rounded-3xl max-w-sm w-full p-6 shadow-2xl space-y-5 border border-slate-100">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-slate-900 text-lg">
              Sobre o AquaWatch
            </h3>
            <button
              id="closeModal"
              className="text-slate-400 hover:text-slate-600 transition"
            >
              <i className="fa-solid fa-xmark text-xl"></i>
            </button>
          </div>
          <p className="text-sm text-slate-600 leading-relaxed">
            A plataforma apresenta as estações hidrológicas e os níveis de
            severidade calculados pelo sistema a partir dos dados disponíveis na
            API da ANA. A atualização depende da disponibilidade de cada estação
            e do serviço de dados.
          </p>
          <CivilDefenseWarning />
          <div className="rounded-2xl border border-slate-200 p-4 space-y-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Severidade das estações ANA
            </h4>
            <div className="space-y-2">
              {[
                ["station-marker-normal", "N", "Normal — sem alerta ativo"],
                ["station-marker-atencao", "A", "Atenção"],
                ["station-marker-alerta", "AL", "Alerta"],
                ["station-marker-emergencia", "E", "Emergência"],
              ].map(([markerClass, abbreviation, label]) => (
                <div
                  key={markerClass}
                  className="flex items-center gap-3 text-sm text-slate-700"
                >
                  <span
                    className={`legend-station-marker ${markerClass}`}
                    aria-hidden="true"
                  >
                    {abbreviation}
                  </span>
                  <span>{label}</span>
                </div>
              ))}
            </div>
            <p className="text-xs leading-relaxed text-slate-500">
              A cor e a sigla identificam a severidade informada pela API. As
              áreas e linhas do mapa são ilustrações e não representam alertas
              oficiais.
            </p>
          </div>
          <button
            id="okModalBtn"
            className="w-full py-3 bg-slate-900 text-white font-semibold text-sm rounded-xl hover:bg-slate-800 transition"
          >
            Entendido
          </button>
        </div>
      </div>
    </>
  );
}
