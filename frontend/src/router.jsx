import { createBrowserRouter, Navigate } from "react-router";
import App from "./App";
import DashboardRoute from "./routes/DashboardRoute";
import SavedPlacesRoute from "./routes/SavedPlacesRoute";
import StationDetailRoute from "./routes/StationDetailRoute";

const router = createBrowserRouter([
  {
    path: "/",
    Component: App,
    children: [
      { index: true, Component: DashboardRoute },
      { path: "informacoes", Component: DashboardRoute },
      { path: "locais", Component: SavedPlacesRoute },
      { path: "estacoes/:codigo", Component: StationDetailRoute },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);

export default router;
