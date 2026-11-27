import ActiveAlertsCard from "./ActiveAlertsCard";
import CivilDefenseWarning from "./CivilDefenseWarning";

const emergencyContacts = [
  { number: "112", service: "Emergência" },
  { number: "190", service: "Polícia Militar" },
  { number: "192", service: "SAMU" },
  { number: "193", service: "Corpo de Bombeiros" },
  { number: "199", service: "Defesa Civil" },
];

export default function DashboardContent({ onCloseInfoSheet }) {
  return (
    <>
      <div className="mobile-sheet-handle">
        <button
          type="button"
          onClick={onCloseInfoSheet}
          aria-label="Voltar ao mapa"
          className="flex w-full flex-col items-center gap-2 text-slate-400"
        >
          <span className="h-1 w-10 rounded-full bg-slate-300"></span>
          <span className="text-[11px] font-semibold text-slate-500">
            Voltar ao mapa{" "}
            <i className="fa-solid fa-chevron-down ml-1 text-[9px]"></i>
          </span>
        </button>
      </div>

      <ActiveAlertsCard />

      <CivilDefenseWarning />

      <div className="dashboard-card bg-white border border-red-100 rounded-2xl p-5 shadow-sm relative overflow-hidden">
        <div className="absolute -right-4 -bottom-4 text-red-500/5 text-7xl font-bold select-none pointer-events-none">
          <i className="fa-solid fa-truck-medical"></i>
        </div>
        <div className="flex items-center gap-2.5 mb-3">
          <i className="fa-solid fa-truck-medical text-red-600 text-lg"></i>
          <h3 className="text-sm font-bold uppercase tracking-wider text-red-800">
            Acionar Autoridades
          </h3>
        </div>
        <p className="text-xs text-slate-500 mb-4 leading-relaxed">
          Em caso de alagamento, risco de desabamento ou emergência imediata,
          contate os órgãos responsáveis.
        </p>
        <div className="dashboard-grid grid grid-cols-2 gap-3 relative z-10">
          {emergencyContacts.map(({ number, service }) => (
            <a
              key={number}
              href={`tel:${number}`}
              aria-label={`Ligar para ${service}, ${number}`}
              className="flex min-h-20 flex-col items-center justify-center rounded-xl border border-red-100 bg-red-50 p-3 text-center"
            >
              <span className="text-lg font-bold leading-tight text-red-800">
                {number}
              </span>
              <span className="mt-1 text-xs font-semibold text-slate-800">
                {service}
              </span>
            </a>
          ))}
        </div>
      </div>

      <section
        aria-labelledby="safetyGuidanceHeading"
        className="dashboard-card bg-white border border-slate-200 rounded-2xl p-5 shadow-sm"
      >
        <div className="flex items-center gap-2 mb-3">
          <i
            className="fa-solid fa-circle-info text-sky-600"
            aria-hidden="true"
          ></i>
          <h3
            id="safetyGuidanceHeading"
            className="text-sm font-bold uppercase tracking-wider text-slate-700"
          >
            Orientações de segurança
          </h3>
        </div>
        <ul className="space-y-3 text-xs leading-relaxed text-slate-600">
          <li className="flex items-start gap-2">
            <span className="mt-1 text-sky-600" aria-hidden="true">
              •
            </span>
            <span>
              Siga as orientações das autoridades locais, como a Defesa Civil e
              o Corpo de Bombeiros.
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1 text-sky-600" aria-hidden="true">
              •
            </span>
            <span>
              Evite contato com água e lama de enchentes. Se for inevitável
              passar por uma área inundada, use botas impermeáveis e luvas;
              proteja cortes e arranhões.
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1 text-sky-600" aria-hidden="true">
              •
            </span>
            <span>
              Não consuma alimentos que tiveram contato com a água da inundação
              ou lama. Para beber, use água segura e siga as orientações
              sanitárias.
            </span>
          </li>
        </ul>
        <div className="mt-4 border-t border-slate-100 pt-3">
          <h4 className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
            Fontes oficiais
          </h4>
          <ul className="mt-2 space-y-2 text-xs">
            <li>
              <a
                href="https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/e/enchentes"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sky-700 underline decoration-sky-300 underline-offset-2 hover:text-sky-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600"
              >
                Ministério da Saúde — Enchentes
              </a>
            </li>
            <li>
              <a
                href="https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/e/enchentes/cuidados-com-a-leptospirose"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sky-700 underline decoration-sky-300 underline-offset-2 hover:text-sky-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600"
              >
                Ministério da Saúde — Cuidados com a leptospirose
              </a>
            </li>
            <li>
              <a
                href="https://www.gov.br/saude/pt-br/assuntos/saude-de-a-a-z/e/enchentes/cuidados-com-a-agua"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sky-700 underline decoration-sky-300 underline-offset-2 hover:text-sky-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-600"
              >
                Ministério da Saúde — Cuidados com a água
              </a>
            </li>
          </ul>
        </div>
      </section>
    </>
  );
}
