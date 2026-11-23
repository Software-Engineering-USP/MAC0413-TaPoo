import { useCallback, useEffect, useRef, useState } from "react";
import {
  AboutDialog,
  ConfirmDialog,
  SavePlaceDialog,
} from "./components/AppDialogs";
import MapView from "./components/MapView";
import MobileNavigation from "./components/MobileNavigation";
import Sidebar from "./components/Sidebar";
import { defaultSavedPlaces, loadSavedPlaces } from "./mapData";

export default function App() {
  const appShellRef = useRef(null);
  const mapRef = useRef(null);
  const mapViewRef = useRef(null);
  const dashboardRef = useRef(null);
  const searchInputRef = useRef(null);

  const [isInfoSheetOpen, setInfoSheetOpen] = useState(false);
  const [isAboutDialogOpen, setAboutDialogOpen] = useState(false);
  const [isSaveDialogOpen, setSaveDialogOpen] = useState(false);
  const [placeName, setPlaceName] = useState("Novo local");
  const [placeToRemove, setPlaceToRemove] = useState(null);
  const [savedPlaces, setSavedPlaces] = useState(loadSavedPlaces);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    try {
      localStorage.setItem("aquaWatchSavedPlaces", JSON.stringify(savedPlaces));
    } catch (error) {
      console.error("Unable to save map locations.", error);
    }
  }, [savedPlaces]);

  const syncInfoSheetState = useCallback(() => {
    const appShell = appShellRef.current;
    const isMobile = window.matchMedia("(max-width: 767px)").matches;
    setInfoSheetOpen(Boolean(isMobile && appShell?.scrollTop > 0));
  }, []);

  useEffect(() => {
    window.addEventListener("resize", syncInfoSheetState);
    return () => window.removeEventListener("resize", syncInfoSheetState);
  }, [syncInfoSheetState]);

  const openInfoSheet = () => {
    const appShell = appShellRef.current;
    const mapView = mapViewRef.current;
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
    appShellRef.current?.scrollTo({ top: 0, behavior: "smooth" });
  };

  const saveCurrentPlace = () => {
    setPlaceName("Novo local");
    setSaveDialogOpen(true);
  };

  const confirmSavePlace = (event) => {
    event.preventDefault();
    const name = placeName.trim();
    const map = mapRef.current;
    if (!name || !map) return;

    const center = map.getCenter();
    setSavedPlaces((places) => [
      ...places,
      {
        name: name.slice(0, 40),
        center: [center.lat, center.lng],
        zoom: map.getZoom(),
      },
    ]);
    setSaveDialogOpen(false);
  };

  const confirmRemovePlace = () => {
    if (placeToRemove === null) return;
    setSavedPlaces((places) => places.filter((_, index) => index !== placeToRemove));
    setPlaceToRemove(null);
  };

  const searchSavedPlaces = (event) => {
    event.preventDefault();
    const input = searchInputRef.current;
    const query = searchQuery.trim().toLocaleLowerCase("pt-BR");
    if (!input || !query) return;

    const place = savedPlaces.find((item) =>
      item.name.toLocaleLowerCase("pt-BR").includes(query),
    );

    if (!place) {
      input.setCustomValidity("Local salvo não encontrado.");
      input.reportValidity();
      return;
    }

    input.setCustomValidity("");
    mapRef.current?.flyTo(place.center, place.zoom);
    input.blur();
  };

  const updateSearchQuery = (value) => {
    searchInputRef.current?.setCustomValidity("");
    setSearchQuery(value);
  };

  const showDefaultLocation = () => {
    mapRef.current?.flyTo(defaultSavedPlaces[0].center, 16);
  };

  return (
    <div
      className="app-shell"
      ref={appShellRef}
      onScroll={syncInfoSheetState}
    >
      <Sidebar
        dashboardRef={dashboardRef}
        onOpenAbout={() => setAboutDialogOpen(true)}
        onCloseInfoSheet={closeInfoSheet}
        savedPlaces={savedPlaces}
        onSavePlace={saveCurrentPlace}
        onSelectPlace={(place) => mapRef.current?.flyTo(place.center, place.zoom)}
        onRequestRemovePlace={setPlaceToRemove}
      />
      <MapView
        mapRef={mapRef}
        mapViewRef={mapViewRef}
        savedPlaces={savedPlaces}
        searchInputRef={searchInputRef}
        searchQuery={searchQuery}
        onSearchChange={updateSearchQuery}
        onSearch={searchSavedPlaces}
        onMyLocation={showDefaultLocation}
      />
      <MobileNavigation
        isInfoSheetOpen={isInfoSheetOpen}
        onShowMap={closeInfoSheet}
        onShowInformation={openInfoSheet}
      />
      <SavePlaceDialog
        open={isSaveDialogOpen}
        name={placeName}
        onNameChange={setPlaceName}
        onSubmit={confirmSavePlace}
        onClose={() => setSaveDialogOpen(false)}
      />
      <ConfirmDialog
        open={placeToRemove !== null}
        message={
          placeToRemove === null
            ? "Tem certeza?"
            : `Remover "${savedPlaces[placeToRemove]?.name ?? ""}" dos locais salvos?`
        }
        onConfirm={confirmRemovePlace}
        onClose={() => setPlaceToRemove(null)}
      />
      <AboutDialog
        open={isAboutDialogOpen}
        onClose={() => setAboutDialogOpen(false)}
      />
    </div>
  );
}
