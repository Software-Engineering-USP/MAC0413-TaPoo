import CivilDefenseWarning from "./CivilDefenseWarning";
import ActiveAlertsPanel from "./ActiveAlertsPanel";

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

      <ActiveAlertsPanel />

      <CivilDefenseWarning />

      <div className="dashboard-card bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
          <div className="flex items-center gap-2">
            <i className="fa-solid fa-location-dot text-sky-600 text-lg"></i>
            <h2
              className="text-base font-bold text-slate-800"
              id="selectedCityName"
            >
              Blumenau, SC
            </h2>
          </div>
          <span className="text-[11px] bg-slate-100 text-slate-600 px-2.5 py-1 rounded-full font-medium">
            Bacia Itajaí-Açu
          </span>
        </div>

        <div className="dashboard-grid grid grid-cols-2 gap-4">
          <div className="dashboard-grid-card bg-slate-50 p-3 rounded-xl border border-slate-100">
            <span className="text-[11px] font-medium text-slate-400 block mb-1">
              CONDIÇÃO ATUAL
            </span>
            <div className="flex items-center gap-3">
              <i className="fa-solid fa-cloud-showers-heavy text-slate-600 text-2xl"></i>
              <div>
                <p className="text-sm font-bold text-slate-800">
                  Chuva Intensa
                </p>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  48mm nas úl. 6h
                </p>
              </div>
            </div>
          </div>

          <div className="dashboard-grid-card bg-slate-50 p-3 rounded-xl border border-slate-100">
            <span className="text-[11px] font-medium text-slate-400 block mb-1">
              NÍVEL DO RIO
            </span>
            <div className="flex items-center gap-3">
              <i className="fa-solid fa-water text-sky-600 text-2xl"></i>
              <div>
                <p className="text-sm font-bold text-slate-800" id="riverLevel">
                  8,42 metros
                </p>
                <p className="text-[11px] text-red-600 font-bold flex items-center mt-0.5">
                  <i className="fa-solid fa-arrow-trend-up mr-1"></i> Emergência
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="dashboard-card bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
            Previsão de Nível de Risco
          </h3>
          <span className="text-[11px] font-bold text-red-600 bg-red-50 px-2 py-0.5 rounded border border-red-100">
            Pico previsto: Dom 08h
          </span>
        </div>

        <div className="relative flex items-center justify-between px-3 py-3">
          <div className="absolute left-7 right-7 top-1/2 transform -translate-y-1/2 h-1 bg-slate-100 z-0"></div>
          <div className="absolute left-7 w-2/3 top-1/2 transform -translate-y-1/2 h-1 bg-gradient-to-r from-red-500 via-red-500 to-orange-400 z-0 rounded-full"></div>

          <div className="relative z-10 flex flex-col items-center">
            <div className="w-6 h-6 rounded-full bg-red-600 border-2 border-white shadow-sm flex items-center justify-center">
              <div className="w-2 h-2 rounded-full bg-white"></div>
            </div>
            <span className="text-xs font-bold text-slate-800 mt-2">Hoje</span>
            <span className="text-[11px] text-slate-400">14h</span>
          </div>

          <div className="relative z-10 flex flex-col items-center">
            <div className="w-7 h-7 rounded-full bg-red-600 border-2 border-white shadow-md flex items-center justify-center ring-4 ring-red-100">
              <i className="fa-solid fa-triangle-exclamation text-[10px] text-white"></i>
            </div>
            <span className="text-xs font-bold text-red-600 mt-1.5">Sáb</span>
            <span className="text-[11px] text-red-500 font-bold">08h</span>
          </div>

          <div className="relative z-10 flex flex-col items-center">
            <div className="w-6 h-6 rounded-full bg-orange-500 border-2 border-white shadow-sm"></div>
            <span className="text-xs font-bold text-slate-800 mt-2">Dom</span>
            <span className="text-[11px] text-slate-400">20h</span>
          </div>

          <div className="relative z-10 flex flex-col items-center">
            <div className="w-6 h-6 rounded-full bg-yellow-400 border-2 border-white shadow-sm"></div>
            <span className="text-xs font-bold text-slate-800 mt-2">Seg</span>
            <span className="text-[11px] text-slate-400">12h</span>
          </div>
        </div>
      </div>

      <div className="dashboard-grid grid gap-4">
        <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2.5">
              <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                Histórico
              </span>
              <i className="fa-solid fa-chart-line text-slate-400 text-sm"></i>
            </div>
            <h4 className="text-[13px] font-bold text-slate-800">
              Cheias Anteriores
            </h4>
            <p className="text-[11px] text-slate-500 mt-1 leading-snug">
              Nível similar registrado em 2011 e 1983.
            </p>
          </div>
          <div className="mt-4 flex items-center justify-between text-[11px] text-slate-600 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-100">
            <span className="font-medium">Máx &apos;83: 15.3m</span>
          </div>
        </div>
      </div>

      <div className="dashboard-card bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <i className="fa-solid fa-users text-slate-500 text-sm"></i>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600">
              Relatos da Comunidade
            </h3>
          </div>
          <span className="text-xs text-sky-600 font-bold cursor-pointer hover:underline">
            + Informar
          </span>
        </div>

        <div className="space-y-4">
          <div className="flex items-start gap-3 text-[13px] pb-3 border-b border-slate-100">
            <div className="w-2.5 h-2.5 rounded-full bg-red-500 mt-1 shrink-0"></div>
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-800">
                  Rua Almirante Tamandaré
                </span>
                <span className="text-[11px] text-slate-400 font-medium">
                  há 18 min
                </span>
              </div>
              <p className="text-slate-500 text-xs mt-1">
                Água começando a cobrir a pista próximo à ponte.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3 text-[13px]">
            <div className="w-2.5 h-2.5 rounded-full bg-orange-400 mt-1 shrink-0"></div>
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-800">
                  Bairro Itoupava Norte
                </span>
                <span className="text-[11px] text-slate-400 font-medium">
                  há 42 min
                </span>
              </div>
              <p className="text-slate-500 text-xs mt-1">
                Bueiros transbordando na via principal.
              </p>
            </div>
          </div>
        </div>
      </div>

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
