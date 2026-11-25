import { useOutletContext } from "react-router";
import SavedPlacesCard from "../components/SavedPlacesCard";

export default function SavedPlacesRoute() {
  const {
    savedPlaces,
    onSavePlace,
    onSelectSavedPlace,
    onRequestRemovePlace,
    onCloseInfoSheet,
  } = useOutletContext();

  return (
    <section className="mobile-saved-places-route">
      <div className="mobile-sheet-handle">
        <button
          type="button"
          onClick={onCloseInfoSheet}
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
      <SavedPlacesCard
        variant="panel"
        places={savedPlaces}
        onSave={onSavePlace}
        onSelect={onSelectSavedPlace}
        onRemove={onRequestRemovePlace}
      />
      {savedPlaces.length === 0 && (
        <p className="saved-places-empty">
          {`Voc\u00ea ainda n\u00e3o salvou nenhum local. Use o bot\u00e3o acima para salvar a \u00e1rea atual do mapa.`}
        </p>
      )}
    </section>
  );
}
