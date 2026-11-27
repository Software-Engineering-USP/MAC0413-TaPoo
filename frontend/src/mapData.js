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

export const rivers = [
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
