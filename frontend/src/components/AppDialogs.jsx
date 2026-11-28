import { useEffect, useRef, useState } from "react";
import { obterMetadados, usaApiReal } from "../api/cliente";
import CivilDefenseWarning from "./CivilDefenseWarning";
import { RAIO_LOCAL_KM } from "../situacaoLocal";

export function SavePlaceDialog({
  open,
  name,
  onNameChange,
  onSubmit,
  onClose,
}) {
  const inputRef = useRef(null);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-sm">
      <form
        className="w-full max-w-xs space-y-4 rounded-2xl border border-slate-100 bg-white p-5 shadow-2xl"
        onSubmit={onSubmit}
      >
        <h2 className="text-sm font-bold text-slate-900">
          Nome para este local
        </h2>
        <input
          ref={inputRef}
          type="text"
          value={name}
          onChange={(event) => onNameChange(event.target.value)}
          className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus:border-sky-500 focus:outline-none"
          placeholder="Ex: Minha Casa"
          maxLength={40}
          required
        />
        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-xs font-semibold text-slate-500 transition hover:bg-slate-100"
          >
            Cancelar
          </button>
          <button
            type="submit"
            className="rounded-lg bg-sky-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-sky-700"
          >
            Salvar
          </button>
        </div>
      </form>
    </div>
  );
}

export function ConfirmDialog({ open, message, onConfirm, onClose }) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-sm">
      <div
        role="alertdialog"
        aria-modal="true"
        className="w-full max-w-xs space-y-4 rounded-2xl border border-slate-100 bg-white p-5 shadow-2xl"
      >
        <h2 className="text-sm font-bold text-slate-900">{message}</h2>
        <div className="mt-4 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-xs font-semibold text-slate-500 transition hover:bg-slate-100"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="rounded-lg bg-red-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-red-700"
          >
            Remover
          </button>
        </div>
      </div>
    </div>
  );
}

const ORIGENS = {
  real: "Dados reais da ANA.",
  simulado:
    "Dados simulados: estações e alertas fictícios, só para demonstração.",
};

/** Origem dos dados da API (`/metadados`); `null` enquanto não se sabe. */
function useOrigemDados(open) {
  const [origem, setOrigem] = useState(null);

  useEffect(() => {
    if (!open) return undefined;
    const controller = new AbortController();
    obterMetadados({ signal: controller.signal })
      .then((metadados) => {
        if (!controller.signal.aborted) setOrigem(metadados.origem_dados);
      })
      .catch(() => {
        if (!controller.signal.aborted) setOrigem("desconhecida");
      });
    return () => controller.abort();
  }, [open]);

  return origem;
}

function descreverOrigem(origem) {
  if (!usaApiReal) {
    return "Modo demonstração: o front está usando dados fictícios embutidos, sem consultar a API.";
  }
  if (origem === null) return "Consultando a origem dos dados…";
  return ORIGENS[origem] || "Não foi possível confirmar a origem dos dados.";
}

export function AboutDialog({ open, onClose }) {
  const origem = useOrigemDados(open);
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-sm">
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="aboutTitle"
        className="max-h-[90dvh] w-full max-w-sm space-y-5 overflow-y-auto rounded-3xl border border-slate-100 bg-white p-6 shadow-2xl"
      >
        <div className="flex items-center justify-between">
          <h2 id="aboutTitle" className="text-lg font-bold text-slate-900">
            Sobre o AquaWatch
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fechar informações do sistema"
            className="text-slate-400 transition hover:text-slate-600"
          >
            <i className="fa-solid fa-xmark text-xl" aria-hidden="true"></i>
          </button>
        </div>
        <div className="space-y-2 text-sm leading-relaxed text-slate-600">
          <p>
            As estações e a situação de cada uma vêm do inventário e das
            medições telemétricas da ANA (Agência Nacional de Águas). Os alertas
            saem das regras de cota e de chuva cadastradas para cada estação; a
            chuva do mês é comparada às normais climatológicas do INMET
            (1991–2020).
          </p>
          <p>
            A cor de cada local salvo é a pior situação entre as estações da ANA
            num raio de {RAIO_LOCAL_KM} km. Os rios desenhados no mapa são só
            referência visual (OpenStreetMap).
          </p>
          <output className="block rounded-xl bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-700">
            {descreverOrigem(origem)}
          </output>
        </div>
        <CivilDefenseWarning />
        <div className="space-y-3 rounded-2xl border border-slate-200 p-4">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
            Legenda do mapa
          </h3>
          <div className="flex items-center gap-3 text-sm text-slate-700">
            <span className="h-1.5 w-6 rounded-full bg-sky-600"></span>
            <span>Rios e córregos (referência)</span>
          </div>
          <h4 className="pt-2 text-xs font-bold uppercase tracking-wider text-slate-500">
            Locais salvos
          </h4>
          {[
            ["bg-sky-700", "Normal"],
            ["bg-yellow-400", "Atenção"],
            ["bg-orange-700", "Alerta"],
            ["bg-red-600", "Emergência"],
            ["bg-slate-400", "Sem estações por perto ou consultando"],
          ].map(([colorClass, label]) => (
            <div
              key={colorClass}
              className="flex items-center gap-3 text-sm text-slate-700"
            >
              <span
                className={`h-3 w-3 rounded-full ${colorClass}`}
                aria-hidden="true"
              ></span>
              <span>{label}</span>
            </div>
          ))}
          <h4 className="pt-2 text-xs font-bold uppercase tracking-wider text-slate-500">
            Severidade das estações ANA
          </h4>
          {[
            ["station-marker-normal", "N", "Normal — sem alerta ativo"],
            ["station-marker-atencao", "A", "Atenção"],
            ["station-marker-alerta", "AL", "Alerta"],
            ["station-marker-emergencia", "E", "Emergência"],
          ].map(([markerClass, abbreviation, label]) => (
            <div
              key={markerClass}
              className="flex items-center gap-3 text-sm text-slate-700"
            >
              <span
                className={`legend-station-marker ${markerClass}`}
                aria-hidden="true"
              >
                {abbreviation}
              </span>
              <span>{label}</span>
            </div>
          ))}
          <p className="text-xs leading-relaxed text-slate-500">
            A cor e a sigla identificam a severidade informada para cada
            estação.
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="w-full rounded-xl bg-slate-900 py-3 text-sm font-semibold text-white transition hover:bg-slate-800"
        >
          Entendido
        </button>
      </section>
    </div>
  );
}
