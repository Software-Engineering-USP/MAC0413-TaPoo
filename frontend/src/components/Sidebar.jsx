import SavedPlacesCard from "./SavedPlacesCard";

export default function Sidebar({
  children,
  onOpenAbout,
  savedPlaces,
  onSavePlace,
  onSelectPlace,
  onRequestRemovePlace,
}) {
  return (
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
            onClick={onOpenAbout}
            className="system-info-button w-10 h-10 rounded-full hover:bg-slate-100 flex items-center justify-center text-slate-400 hover:text-slate-600 transition"
            title="Informações do Sistema"
          >
            <i className="fa-regular fa-circle-question text-xl"></i>
          </button>
      </header>

      <SavedPlacesCard
        places={savedPlaces}
        onSave={onSavePlace}
        onSelect={onSelectPlace}
        onRemove={onRequestRemovePlace}
      />
      <div
        id="dashboardSheet"
        className="dashboard-sheet min-h-0 flex-1 overflow-y-auto p-5"
      >
        {children}
      </div>
    </aside>
  );
}
