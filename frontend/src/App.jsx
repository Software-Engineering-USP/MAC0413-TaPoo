import { useCallback, useEffect, useRef, useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router";
import {
  AboutDialog,
  ConfirmDialog,
  SavePlaceDialog,
} from "./components/AppDialogs";
import MapView from "./components/MapView";
import MobileNavigation from "./components/MobileNavigation";
import Sidebar from "./components/Sidebar";
import useSituacaoLocais from "./hooks/useSituacaoLocais";
import { defaultSavedPlaces, loadSavedPlaces } from "./mapData";

export default function App() {
  const appShellRef = useRef(null);
  const mapRef = useRef(null);
  const mapViewRef = useRef(null);
  const searchInputRef = useRef(null);
  const routeChangeFromScrollRef = useRef(false);
  const programmaticScrollTargetRef = useRef(null);
  const programmaticScrollTimeoutRef = useRef(null);

  const [isAboutDialogOpen, setAboutDialogOpen] = useState(false);
  const [isSaveDialogOpen, setSaveDialogOpen] = useState(false);
  const [placeName, setPlaceName] = useState("Novo local");
  const [placeToRemove, setPlaceToRemove] = useState(null);
  const [savedPlaces, setSavedPlaces] = useState(loadSavedPlaces);
  const [searchQuery, setSearchQuery] = useState("");
  const situacoes = useSituacaoLocais(savedPlaces);
  const location = useLocation();
  const navigate = useNavigate();
  const isInfoSheetOpen = location.pathname === "/informacoes";
  const isLocationsOpen = location.pathname === "/locais";
  const isSheetOpen = isInfoSheetOpen || isLocationsOpen;

  useEffect(() => {
    try {
      localStorage.setItem("aquaWatchSavedPlaces", JSON.stringify(savedPlaces));
    } catch (error) {
      console.error("Unable to save map locations.", error);
    }
  }, [savedPlaces]);

  const clearProgrammaticScrollTarget = useCallback(() => {
    programmaticScrollTargetRef.current = null;
    if (programmaticScrollTimeoutRef.current !== null) {
      window.clearTimeout(programmaticScrollTimeoutRef.current);
      programmaticScrollTimeoutRef.current = null;
    }
  }, []);

  const scrollToInfoSheet = useCallback(
    (shouldOpen) => {
      const appShell = appShellRef.current;
      const mapView = mapViewRef.current;
      if (
        !appShell ||
        !mapView ||
        !window.matchMedia("(max-width: 767px)").matches
      ) {
        return;
      }

      const requestedTarget = shouldOpen
        ? mapView.offsetHeight - Math.min(180, appShell.clientHeight * 0.35)
        : 0;
      const maxScrollTop = Math.max(
        0,
        appShell.scrollHeight - appShell.clientHeight,
      );
      const scrollTarget = Math.min(Math.max(0, requestedTarget), maxScrollTop);

      if (Math.abs(appShell.scrollTop - scrollTarget) < 2) {
        clearProgrammaticScrollTarget();
        return;
      }

      clearProgrammaticScrollTarget();
      programmaticScrollTargetRef.current = scrollTarget;
      programmaticScrollTimeoutRef.current = window.setTimeout(
        clearProgrammaticScrollTarget,
        1500,
      );
      appShell.scrollTo({ top: scrollTarget, behavior: "smooth" });
    },
    [clearProgrammaticScrollTarget],
  );

  const handleShellScroll = () => {
    const appShell = appShellRef.current;
    if (!appShell || !window.matchMedia("(max-width: 767px)").matches) return;

    if (routeChangeFromScrollRef.current) return;

    const scrollTarget = programmaticScrollTargetRef.current;
    if (scrollTarget !== null) {
      if (Math.abs(appShell.scrollTop - scrollTarget) < 2) {
        clearProgrammaticScrollTarget();
      }
      return;
    }

    if (appShell.scrollTop > 0 && !isSheetOpen) {
      routeChangeFromScrollRef.current = true;
      navigate("/informacoes");
    } else if (appShell.scrollTop <= 1 && isSheetOpen) {
      routeChangeFromScrollRef.current = true;
      navigate("/");
    }
  };

  useEffect(() => {
    if (routeChangeFromScrollRef.current) {
      routeChangeFromScrollRef.current = false;
      return;
    }

    scrollToInfoSheet(isSheetOpen);
  }, [location.pathname, isSheetOpen, scrollToInfoSheet]);

  useEffect(() => {
    const appShell = appShellRef.current;
    if (!appShell) return undefined;

    appShell.addEventListener("scrollend", clearProgrammaticScrollTarget);
    appShell.addEventListener("touchstart", clearProgrammaticScrollTarget, {
      passive: true,
    });
    appShell.addEventListener("wheel", clearProgrammaticScrollTarget, {
      passive: true,
    });

    return () => {
      appShell.removeEventListener("scrollend", clearProgrammaticScrollTarget);
      appShell.removeEventListener("touchstart", clearProgrammaticScrollTarget);
      appShell.removeEventListener("wheel", clearProgrammaticScrollTarget);
      clearProgrammaticScrollTarget();
    };
  }, [clearProgrammaticScrollTarget]);

  useEffect(() => {
    const handleResize = () => scrollToInfoSheet(isSheetOpen);
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [isSheetOpen, scrollToInfoSheet]);

  const closeInfoSheet = () => {
    routeChangeFromScrollRef.current = true;
    clearProgrammaticScrollTarget();
    if (appShellRef.current) appShellRef.current.scrollTop = 0;
    navigate("/", { replace: true });
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
    setSavedPlaces((places) =>
      places.filter((_, index) => index !== placeToRemove),
    );
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

  const selectSavedPlace = (place) => {
    mapRef.current?.flyTo(place.center, place.zoom);
    if (window.matchMedia("(max-width: 767px)").matches) navigate("/");
  };

  return (
    <div className="app-shell" ref={appShellRef} onScroll={handleShellScroll}>
      <Sidebar
        onOpenAbout={() => setAboutDialogOpen(true)}
        savedPlaces={savedPlaces}
        situacoes={situacoes}
        onSavePlace={saveCurrentPlace}
        onSelectPlace={(place) =>
          mapRef.current?.flyTo(place.center, place.zoom)
        }
        onRequestRemovePlace={setPlaceToRemove}
      >
        <Outlet
          context={{
            onCloseInfoSheet: closeInfoSheet,
            savedPlaces,
            situacoes,
            onSavePlace: saveCurrentPlace,
            onSelectSavedPlace: selectSavedPlace,
            onRequestRemovePlace: setPlaceToRemove,
          }}
        />
      </Sidebar>
      <MapView
        mapRef={mapRef}
        mapViewRef={mapViewRef}
        savedPlaces={savedPlaces}
        situacoes={situacoes}
        searchInputRef={searchInputRef}
        searchQuery={searchQuery}
        onSearchChange={updateSearchQuery}
        onSearch={searchSavedPlaces}
        onMyLocation={showDefaultLocation}
      />
      <MobileNavigation
        isInfoSheetOpen={isInfoSheetOpen}
        isLocationsOpen={isLocationsOpen}
        onCloseSheet={closeInfoSheet}
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
