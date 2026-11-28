import { useEffect, useState } from "react";
import { listarMedicoesEstacao } from "../api/cliente";

const severityStyles = {
  NORMAL: "text-emerald-700 bg-emerald-50",
  ATENCAO: "text-amber-700 bg-amber-50",
  ALERTA: "text-orange-700 bg-orange-50",
  EMERGENCIA: "text-red-700 bg-red-50",
};

function formatValue(value, digits = 1) {
  return new Intl.NumberFormat("pt-BR", {
    maximumFractionDigits: digits,
  }).format(value);
}

function formatMeasurementTime(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function loadSeries(codigo, grandeza, inicio, fim, signal) {
  return listarMedicoesEstacao(codigo, {
    grandeza,
    inicio: inicio.toISOString(),
    fim: fim.toISOString(),
    signal,
  });
}

export default function SelectedStationStatus({ station }) {
  const [measurements, setMeasurements] = useState({ status: "idle" });

  useEffect(() => {
    if (!station) {
      setMeasurements({ status: "idle" });
      return undefined;
    }

    const controller = new AbortController();
    const fim = new Date();
    const inicio = new Date(fim.getTime() - 6 * 60 * 60 * 1000);
    const grandezas = station.grandezas ?? [];

    async function loadMeasurements() {
      setMeasurements({ status: "loading" });
      const [chuva, nivel] = await Promise.all(
        ["CHUVA", "NIVEL"].map(async (grandeza) => {
          if (!grandezas.includes(grandeza)) {
            return { grandeza, series: null, error: null };
          }
          try {
            const series = await loadSeries(
              station.codigo,
              grandeza,
              inicio,
              fim,
              controller.signal,
            );
            return { grandeza, series, error: null };
          } catch (error) {
            if (error.name === "AbortError") throw error;
            return { grandeza, series: null, error };
          }
        }),
      );

      if (!controller.signal.aborted) {
        setMeasurements({ status: "success", chuva, nivel });
      }
    }

    loadMeasurements().catch((error) => {
      if (!controller.signal.aborted && error.name !== "AbortError") {
        setMeasurements({ status: "error" });
      }
    });

    return () => controller.abort();
  }, [station]);

  if (!station) {
    return (
      <section className="dashboard-card rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-base font-bold text-slate-800">
          {"Situa\u00e7\u00e3o da esta\u00e7\u00e3o"}
        </h2>
        <p className="mt-2 text-sm text-slate-500">
          {
            "Selecione uma esta\u00e7\u00e3o no mapa para consultar a condi\u00e7\u00e3o atual e o n\u00edvel do rio."
          }
        </p>
      </section>
    );
  }

  const severityClass =
    severityStyles[station.severidade] ?? severityStyles.NORMAL;
  const chuva = measurements.status === "success" ? measurements.chuva : null;
  const nivel = measurements.status === "success" ? measurements.nivel : null;
  const chuvaLeituras = chuva?.series?.medicoes ?? [];
  const nivelLeituras = nivel?.series?.medicoes ?? [];
  const chuvaAcumulada = chuvaLeituras.reduce(
    (total, leitura) => total + leitura.valor,
    0,
  );
  const nivelAtual = nivelLeituras.at(-1);
  const nivelInicial = nivelLeituras[0];
  const variacaoNivel =
    nivelLeituras.length > 1 ? nivelAtual.valor - nivelInicial.valor : null;

  return (
    <section className="dashboard-card rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-2 border-b border-slate-100 pb-3">
        <div>
          <h2 className="text-base font-bold text-slate-800">
            {station.nome || `Esta\u00e7\u00e3o ${station.codigo}`}
          </h2>
          <p className="mt-1 text-xs text-slate-500">
            {[station.municipio, station.uf].filter(Boolean).join(", ")}
            {station.rio ? ` \u00b7 ${station.rio}` : ""}
          </p>
        </div>
        <span
          className={`rounded-full px-2.5 py-1 text-xs font-bold ${severityClass}`}
        >
          {station.severidade_rotulo || "Normal"}
        </span>
      </div>

      {station.alerta?.mensagem && (
        <p className="mb-4 rounded-xl bg-slate-50 p-3 text-xs leading-relaxed text-slate-700">
          {station.alerta.mensagem}
        </p>
      )}

      <div className="dashboard-grid grid grid-cols-2 gap-4">
        <div className="dashboard-grid-card rounded-xl border border-slate-100 bg-slate-50 p-3">
          <span className="mb-1 block text-[11px] font-medium text-slate-400">
            {"CHUVA NAS \u00daLTIMAS 6H"}
          </span>
          <div className="flex items-center gap-3">
            <i className="fa-solid fa-cloud-showers-heavy text-2xl text-slate-600" />
            <div>
              {measurements.status === "loading" ? (
                <p className="text-sm text-slate-500">Carregando...</p>
              ) : chuva?.error ? (
                <p className="text-xs text-amber-700">
                  {"Medi\u00e7\u00e3o indispon\u00edvel"}
                </p>
              ) : chuva?.series ? (
                <p className="text-sm font-bold text-slate-800">
                  {chuvaLeituras.length
                    ? `${formatValue(chuvaAcumulada)} mm`
                    : "Sem leitura recente"}
                </p>
              ) : (
                <p className="text-xs text-slate-500">
                  {"Esta esta\u00e7\u00e3o n\u00e3o mede chuva"}
                </p>
              )}
              {chuvaLeituras.length > 0 && (
                <p className="mt-0.5 text-[11px] text-slate-500">
                  Atualizado{" "}
                  {formatMeasurementTime(chuvaLeituras.at(-1).data_hora_utc)}
                </p>
              )}
            </div>
          </div>
        </div>

        <div className="dashboard-grid-card rounded-xl border border-slate-100 bg-slate-50 p-3">
          <span className="mb-1 block text-[11px] font-medium text-slate-400">
            {"N\u00cdVEL DO RIO"}
          </span>
          <div className="flex items-center gap-3">
            <i className="fa-solid fa-water text-2xl text-sky-600" />
            <div>
              {measurements.status === "loading" ? (
                <p className="text-sm text-slate-500">Carregando...</p>
              ) : nivel?.error ? (
                <p className="text-xs text-amber-700">
                  {"Medi\u00e7\u00e3o indispon\u00edvel"}
                </p>
              ) : nivel?.series ? (
                <p className="text-sm font-bold text-slate-800">
                  {nivelAtual
                    ? `${formatValue(nivelAtual.valor / 100, 2)} m`
                    : "Sem leitura recente"}
                </p>
              ) : (
                <p className="text-xs text-slate-500">
                  {"Esta esta\u00e7\u00e3o n\u00e3o mede n\u00edvel do rio"}
                </p>
              )}
              {nivelAtual && (
                <p className="mt-0.5 text-[11px] text-slate-500">
                  Medido {formatMeasurementTime(nivelAtual.data_hora_utc)}
                </p>
              )}
              {variacaoNivel !== null && (
                <p className="mt-0.5 text-[11px] text-slate-500">
                  {"Varia\u00e7\u00e3o: "}
                  {variacaoNivel > 0 ? "+" : ""}
                  {formatValue(variacaoNivel)} cm em 6h
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {measurements.status === "error" && (
        <p className="mt-3 text-xs text-amber-700" role="status">
          {
            "N\u00e3o foi poss\u00edvel carregar as medi\u00e7\u00f5es recentes."
          }
        </p>
      )}
    </section>
  );
}
