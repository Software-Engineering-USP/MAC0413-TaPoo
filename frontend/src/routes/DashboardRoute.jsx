import { useOutletContext } from "react-router";
import DashboardContent from "../components/DashboardContent";

export default function DashboardRoute() {
  const { onCloseInfoSheet } = useOutletContext();

  return <DashboardContent onCloseInfoSheet={onCloseInfoSheet} />;
}
