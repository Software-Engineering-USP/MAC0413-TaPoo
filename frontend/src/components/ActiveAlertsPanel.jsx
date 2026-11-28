import { useEffect, useState } from "react";
import { listarAlertasAtivos, obterEstacao } from "../api/cliente";

const severityRank = { NORMAL: 0, ATENCAO: 1, ALERTA: 2, EMERGENCIA: 3 };

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? ""
    : date.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
}

function formatStationName(alert, station) {
  if (!station) return `Esta\u00e7\u00e3o ${alert.codigo_estacao}`;
  return `${station.nome} - ${station.municipio}`;
}

export default function ActiveAlertsPanel() {
  const [state, setState] = useState({
    status: "loading",
    alerts: [],
    stations: {},
  });

  useEffect(() => {
    const controller = new AbortController();

    async function loadAlerts() {
      try {
        const alerts = await listarAlertasAtivos({ signal: controller.signal });
        const ordered = [...alerts].sort(
          (a, b) =>
            (severityRank[b.severidade] ?? 0) -
              (severityRank[a.severidade] ?? 0) ||
            new Date(b.emitido_em) - new Date(a.emitido_em),
        );
        const codes = [...new Set(ordered.map((alert) => alert.codigo_estacao))];
        const stationEntries = await Promise.all(
          codes.map(async (code) => {
            try {
              return [code, await obterEstacao(code, { signal: controller.signal })];
            } catch (error) {
              if (error.name === "AbortError") throw error;
              return [code, null];
            }
          }),
        );

        if (!controller.signal.aborted) {
          setState({
            status: "success",
            alerts: ordered,
            stations: Object.fromEntries(stationEntries),
          });
        }
      } catch (error) {
        if (!controller.signal.aborted && error.name !== "AbortError") {
          setState({ status: "error", alerts: [], stations: {} });
        }
      }
    }

    loadAlerts();
    return () => controller.abort();
  }, []);

  const { status, alerts, stations } = state;
  const highRisk = alerts.find(
    (alert) => (severityRank[alert.severidade] ?? 0) >= severityRank.ALERTA,
  );
  const riskClass = highRisk
    ? "bg-red-50/90 border-red-200 text-red-800"
    : "bg-amber-50 border-amber-200 text-amber-800";
  const riskBadgeClass = highRisk
    ? "bg-red-600"
    : "bg-amber-600";

  return (
    <>
      <section
        className={`dashboard-card high-risk-warning rounded-2xl border p-5 shadow-sm ${riskClass}`}
        aria-live="polite"
      >
        <div className="flex items-center justify-between gap-3">
          <span
            className={`inline-flex items-center rounded-full px-3 py-1 text-[11px] font-bold text-white ${riskBadgeClass}`}
          >
            {status === "loading"
              ? "VERIFICANDO RISCO"
              : status === "error"
                ? "RISCO INDISPON\u00cdVEL"
                : highRisk
                  ? "ALTO RISCO DE ENCHENTE"
                  : "SEM ALERTA DE ALTO RISCO"}
          </span>
          {highRisk && (
            <span className="text-[11px] font-bold uppercase">
              {highRisk.severidade_rotulo}
            </span>
          )}
        </div>
        <p className="mt-3 text-sm font-semibold">
          {status === "loading" && "Carregando alertas ativos..."}
          {status === "error" &&
            "N\u00e3o foi poss\u00edvel consultar os alertas ativos. Verifique os canais oficiais da Defesa Civil."}
          {status === "success" && highRisk && highRisk.mensagem}
          {status === "success" &&
            !highRisk &&
            "N\u00e3o h\u00e1 alertas ativos classificados como alerta ou emerg\u00eancia."}
        </p>
        {highRisk && (
          <p className="mt-2 text-xs opacity-75">
            {formatStationName(highRisk, stations[highRisk.codigo_estacao])}
            {highRisk.emitido_em && ` \u00b7 Emitido em ${formatDate(highRisk.emitido_em)}`}
          </p>
        )}
      </section>

      <section
        className="dashboard-card rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
        aria-live="polite"
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
            Alertas Ativos
          </h3>
          <span
            className={`h-2.5 w-2.5 rounded-full ${status === "error" ? "bg-amber-400" : alerts.length ? "bg-red-500" : "bg-emerald-500"}`}
            aria-hidden="true"
          />
        </div>
        {status === "loading" && (
          <p className="text-sm text-slate-500">Carregando alertas...</p>
        )}
        {status === "error" && (
          <p className="text-sm text-amber-700">
            N\u00e3o foi poss\u00edvel carregar os alertas. Tente novamente mais tarde.
          </p>
        )}
        {status === "success" && alerts.length === 0 && (
          <p className="text-sm text-slate-500">
            Nenhum alerta ativo no momento.
          </p>
        )}
        {status === "success" && alerts.length > 0 && (
          <ul className="space-y-3">
            {alerts.map((alert) => (
              <li
                key={alert.id}
                className="rounded-xl border border-slate-100 bg-slate-50 p-3"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-bold text-slate-800">
                    {alert.severidade_rotulo} \u00b7{" "}
                    {formatStationName(alert, stations[alert.codigo_estacao])}
                  </span>
                  <span className="shrink-0 text-[10px] text-slate-400">
                    {formatDate(alert.emitido_em)}
                  </span>
                </div>
                <p className="mt-1 text-xs leading-relaxed text-slate-600">
                  {alert.mensagem}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
