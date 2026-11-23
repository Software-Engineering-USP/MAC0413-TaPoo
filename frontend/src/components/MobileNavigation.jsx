export default function MobileNavigation({
  isInfoSheetOpen,
  onShowMap,
  onShowInformation,
}) {
  return (
    <nav className="mobile-bottom-nav" aria-label="Navegação principal">
      <button
        type="button"
        onClick={onShowMap}
        aria-controls="dashboardSheet"
        aria-pressed={!isInfoSheetOpen}
        className={!isInfoSheetOpen ? "active" : ""}
      >
        <i className="fa-solid fa-map-location-dot" aria-hidden="true"></i>
        <span>Mapa</span>
      </button>
      <button
        type="button"
        onClick={onShowInformation}
        aria-controls="dashboardSheet"
        aria-expanded={isInfoSheetOpen}
        aria-pressed={isInfoSheetOpen}
        className={isInfoSheetOpen ? "active" : ""}
      >
        <i className="fa-solid fa-circle-info" aria-hidden="true"></i>
        <span>Informações</span>
      </button>
    </nav>
  );
}
