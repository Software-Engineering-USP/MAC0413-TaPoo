import { useOutletContext } from "react-router";
import DashboardContent from "../components/DashboardContent";

export default function DashboardRoute() {
  const { onCloseInfoSheet, selectedStation } = useOutletContext();

  return (
    <DashboardContent
      onCloseInfoSheet={onCloseInfoSheet}
      selectedStation={selectedStation}
    />
  );
}
