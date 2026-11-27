import { useEffect, useState } from "react";
import { Link } from "react-router";
import { listarAlertasAtivos } from "../api/cliente";

const LIMITE_EXIBIDO = 5;

const ORDEM_SEVERIDADE = ["NORMAL", "ATENCAO", "ALERTA", "EMERGENCIA"];

const severityClasses = {
  NORMAL: "station-detail-severity-normal",
  ATENCAO: "station-detail-severity-attention",
  ALERTA: "station-detail-severity-alert",
  EMERGENCIA: "station-detail-severity-emergency",
};

const formatoData = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "short",
  timeStyle: "short",
});

function formatarEmissao(valor) {
  const data = new Date(valor);
  return Number.isNaN(data.getTime()) ? "" : formatoData.format(data);
}

/** Do mais grave para o menos grave; empate pelo mais recente. */
function ordenarAlertas(alertas) {
  return [...alertas].sort(
    (a, b) =>
      ORDEM_SEVERIDADE.indexOf(b.severidade) -
        ORDEM_SEVERIDADE.indexOf(a.severidade) ||
      String(b.emitido_em).localeCompare(String(a.emitido_em)),
  );
}

export default function ActiveAlertsCard() {
  const [estado, setEstado] = useState({ status: "carregando", alertas: [] });

  useEffect(() => {
    const controller = new AbortController();

    listarAlertasAtivos({ signal: controller.signal })
      .then((alertas) => {
        if (!controller.signal.aborted) {
          setEstado({ status: "ok", alertas: ordenarAlertas(alertas) });
        }
      })
      .catch((error_) => {
        if (!controller.signal.aborted) {
          setEstado({ status: "erro", alertas: [], mensagem: error_.message });
        }
      });

    return () => controller.abort();
  }, []);

  const { status, alertas } = estado;
  const exibidos = alertas.slice(0, LIMITE_EXIBIDO);
  const restantes = alertas.length - exibidos.length;

  return (
    <section
      aria-labelledby="activeAlertsHeading"
      aria-busy={status === "carregando"}
      className="dashboard-card bg-white border border-slate-200 rounded-2xl p-5 shadow-sm"
    >
      <div className="flex items-center justify-between mb-3">
        <h2
          id="activeAlertsHeading"
          className="text-xs font-bold uppercase tracking-wider text-slate-500"
        >
          Alertas ativos
        </h2>
        {status === "ok" && (
          <span className="text-[11px] font-semibold text-slate-500">
            {alertas.length === 1 ? "1 alerta" : `${alertas.length} alertas`}
          </span>
        )}
      </div>

      {status === "carregando" && (
        <output className="block text-xs text-slate-500">
          <i
            className="fa-solid fa-spinner fa-spin mr-1.5"
            aria-hidden="true"
          />
          <span>Consultando alertas…</span>
        </output>
      )}

      {status === "erro" && (
        <p className="text-xs text-red-700" role="alert">
          Não foi possível carregar os alertas: {estado.mensagem}
        </p>
      )}

      {status === "ok" && alertas.length === 0 && (
        <p className="text-xs text-slate-600">
          Nenhum alerta ativo nas estações monitoradas agora.
        </p>
      )}

      {exibidos.length > 0 && (
        <ul className="space-y-3">
          {exibidos.map((alerta) => (
            <li
              key={alerta.id}
              className="border-b border-slate-100 pb-3 last:border-0 last:pb-0"
            >
              <div className="flex items-start justify-between gap-3">
                <Link
                  to={`/estacoes/${alerta.codigo_estacao}`}
                  className="text-[13px] font-bold text-slate-800 hover:text-sky-700 hover:underline"
                >
                  Estação {alerta.codigo_estacao}
                </Link>
                <span
                  className={`station-detail-severity ${severityClasses[alerta.severidade] || severityClasses.NORMAL}`}
                >
                  {alerta.severidade_rotulo}
                </span>
              </div>
              <p className="mt-1 text-xs text-slate-600">{alerta.mensagem}</p>
              <p className="mt-0.5 text-[11px] text-slate-400">
                Emitido em {formatarEmissao(alerta.emitido_em)}
              </p>
            </li>
          ))}
        </ul>
      )}

      {restantes > 0 && (
        <p className="mt-3 text-[11px] text-slate-500">
          E mais {restantes} {restantes === 1 ? "alerta" : "alertas"}.
        </p>
      )}
    </section>
  );
}
