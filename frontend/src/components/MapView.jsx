import { useEffect, useRef } from "react";
import L from "leaflet";
import { floodZones, getRiskLevel, rivers } from "../mapData";

function savedPlaceIcon(riskLevel) {
  const riskClasses = {
    Baixo: "low",
    Moderado: "moderate",
    Alto: "high",
  };
  const riskClassName = riskClasses[riskLevel]
    ? `risk-${riskClasses[riskLevel]}`
    : "";

  return L.divIcon({
    className: ["city-marker", "saved-place-marker", riskClassName]
      .filter(Boolean)
      .join(" "),
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
  onMyLocation,
}) {
  const mapContainerRef = useRef(null);

  useEffect(() => {
    const mapInstance = L.map(mapContainerRef.current, {
      center: [-23.5613, -46.7303],
      zoom: 14,
      zoomControl: false,
      scrollWheelZoom: true,
    });

    mapRef.current = mapInstance;

    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(mapInstance);

    const floodRiskLayer = L.layerGroup().addTo(mapInstance);

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

    mapInstance.whenReady(() => mapInstance.invalidateSize());

    return () => {
      mapRef.current = null;
      mapInstance.remove();
    };
  }, [mapRef]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return undefined;

    const markers = savedPlaces.map((place) => {
      const riskLevel = getRiskLevel(place.center);
      const riskDescription =
        riskLevel === "safe"
          ? "Sem risco indicado nas áreas simuladas"
          : `Risco ${riskLevel.toLowerCase()} simulado`;

      return L.marker(place.center, {
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
          `<strong>${escapeHtml(place.name)}</strong><br>${riskDescription}`,
        );
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
        <form
          className="map-search-form relative flex items-center"
          onSubmit={onSearch}
        >
          <i className="fa-solid fa-magnifying-glass absolute left-3.5 text-slate-400 text-sm"></i>
          <input
            ref={searchInputRef}
            type="text"
            value={searchQuery}
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Buscar cidade ou rio..."
            className="w-full rounded-2xl border border-slate-200 bg-white py-3 pl-10 pr-10 text-sm shadow-lg transition placeholder:text-slate-400 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-100"
          />
          <button
            type="button"
            onClick={onMyLocation}
            className="absolute right-3 p-1 text-slate-400 hover:text-sky-600"
            title="Minha localização"
          >
            <i className="fa-solid fa-location-arrow text-xs"></i>
          </button>
        </form>
      </div>
      <div
        ref={mapContainerRef}
        className="interactive-map"
        role="application"
        aria-label="Mapa interativo de risco de inundação"
      />
    </main>
  );
}
