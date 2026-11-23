import { useEffect, useRef } from "react";
import { getRiskLevel } from "../mapData";

export default function SavedPlacesCard({
  places,
  onSave,
  onSelect,
  onRemove,
}) {
  const listRef = useRef(null);
  const previousPlaceCountRef = useRef(places.length);

  useEffect(() => {
    const placeWasAdded = places.length > previousPlaceCountRef.current;
    previousPlaceCountRef.current = places.length;
    if (!placeWasAdded) return;
    if (places.length === 0 || !listRef.current) return;

    const isMobile = window.matchMedia("(max-width: 767px)").matches;
    listRef.current.scrollTo({
      [isMobile ? "left" : "top"]: isMobile
        ? listRef.current.scrollWidth
        : listRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [places.length]);

  return (
    <section className="saved-places-track" aria-labelledby="savedPlacesTitle">
      <div className="saved-places-heading">
        <div className="flex items-center gap-2">
          <i className="fa-solid fa-bookmark text-sky-600 text-sm" aria-hidden="true"></i>
          <h2
            id="savedPlacesTitle"
            className="text-[13px] font-bold uppercase tracking-wider text-slate-700"
          >
            Meus Locais Salvos
          </h2>
        </div>
        <button
          type="button"
          onClick={onSave}
          className="save-location-btn desktop-save-location-btn text-xs text-sky-600 font-bold hover:text-sky-800 hover:underline transition"
        >
          + Salvar Local
        </button>
      </div>

      <div
        ref={listRef}
        className="saved-locations-list location-chips flex w-full min-w-0 items-center gap-2 overflow-x-auto text-xs"
      >
        {places.map((place, index) => {
          const riskLevel = getRiskLevel(place.center);
          const riskDescription =
            riskLevel === "safe"
              ? "Sem risco simulado"
              : `Risco ${riskLevel.toLowerCase()}`;

          return (
            <div
              key={`${place.name}-${place.center.join(",")}-${index}`}
              className="saved-place-chip flex items-center justify-between bg-slate-50 border border-slate-100 px-3 py-2 rounded-xl hover:bg-slate-100 hover:border-slate-200 transition group shadow-sm"
            >
              <button
                type="button"
                onClick={() => onSelect(place)}
                className="saved-place-select saved-place-details flex flex-col flex-1 min-w-0 text-left"
              >
                <span
                  className="saved-place-name text-xs font-bold text-slate-700 truncate"
                  title={place.name}
                >
                  {place.name}
                </span>
                <span
                  className={`saved-place-risk text-[10px] font-medium truncate ${riskLevel === "safe" ? "text-slate-400" : "text-red-500"}`}
                >
                  {riskDescription}
                </span>
              </button>
              <button
                type="button"
                onClick={() => onRemove(index)}
                className="saved-place-remove text-slate-300 hover:text-red-500 p-1.5 opacity-0 group-hover:opacity-100 transition focus:opacity-100 ml-2 rounded-lg hover:bg-red-50"
                aria-label={`Remover ${place.name} dos locais salvos`}
                title="Remover local"
              >
                <i className="fa-solid fa-trash text-[11px]" aria-hidden="true"></i>
              </button>
            </div>
          );
        })}
        <button
          type="button"
          onClick={onSave}
          className="save-location-btn mobile-save-location-btn shrink-0 whitespace-nowrap rounded-full border border-sky-200 bg-white px-2.5 py-1 font-semibold text-[11px] text-sky-700 shadow transition hover:bg-sky-50"
        >
          <i className="fa-solid fa-bookmark mr-1 mobile-save-icon" aria-hidden="true"></i>
          <span className="desktop-save-label">+ Salvar Atual</span>
          <span className="mobile-save-label">Salve um local</span>
        </button>
      </div>
    </section>
  );
}
