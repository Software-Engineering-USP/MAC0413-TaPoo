export const defaultSavedPlaces = [
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

export function isValidPlace(place) {
  return (
    place &&
    typeof place.name === "string" &&
    Array.isArray(place.center) &&
    place.center.length === 2 &&
    place.center.every(Number.isFinite) &&
    Number.isFinite(place.zoom)
  );
}

export function loadSavedPlaces() {
  try {
    const storedValue = localStorage.getItem("aquaWatchSavedPlaces");
    if (storedValue === null) return defaultSavedPlaces;

    const storedPlaces = JSON.parse(storedValue);
    if (Array.isArray(storedPlaces) && storedPlaces.every(isValidPlace)) {
      return storedPlaces;
    }
  } catch (error) {
    console.error("Unable to load saved map locations.", error);
  }

  return defaultSavedPlaces;
}
