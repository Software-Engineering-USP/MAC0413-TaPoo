import { NavLink } from "react-router";

export default function MobileNavigation({
  isInfoSheetOpen,
  isLocationsOpen,
  onCloseSheet,
}) {
  return (
    <nav className="mobile-bottom-nav" aria-label="Navegação principal">
      <NavLink
        to="/"
        end
        aria-controls="dashboardSheet"
        onClick={(event) => {
          if (isInfoSheetOpen || isLocationsOpen) {
            event.preventDefault();
            onCloseSheet();
          }
        }}
        className={({ isActive }) => (isActive ? "active" : "")}
      >
        <i className="fa-solid fa-map-location-dot" aria-hidden="true"></i>
        <span>Mapa</span>
      </NavLink>
      <NavLink
        to="/locais"
        aria-controls="dashboardSheet"
        aria-expanded={isLocationsOpen}
        className={({ isActive }) => (isActive ? "active" : "")}
      >
        <i className="fa-solid fa-bookmark" aria-hidden="true"></i>
        <span>Locais</span>
      </NavLink>
      <NavLink
        to="/informacoes"
        aria-controls="dashboardSheet"
        aria-expanded={isInfoSheetOpen}
        className={({ isActive }) => (isActive ? "active" : "")}
      >
        <i className="fa-solid fa-circle-info" aria-hidden="true"></i>
        <span>Informações</span>
      </NavLink>
    </nav>
  );
}
