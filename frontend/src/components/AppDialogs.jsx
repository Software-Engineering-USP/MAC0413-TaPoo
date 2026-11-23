import { useEffect, useRef } from "react";
import CivilDefenseWarning from "./CivilDefenseWarning";

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

export function AboutDialog({ open, onClose }) {
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
            Sobre o AquaWatch AI
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
        <p className="text-sm leading-relaxed text-slate-600">
          Os marcadores mostram as estações hidrológicas consultadas na API da
          ANA e a severidade informada. As linhas e áreas do mapa são
          ilustrativas e representam riscos simulados.
        </p>
        <CivilDefenseWarning />
        <div className="space-y-3 rounded-2xl border border-slate-200 p-4">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
            Legenda do mapa
          </h3>
          <div className="flex items-center gap-3 text-sm text-slate-700">
            <span className="h-1.5 w-6 rounded-full bg-sky-600"></span>
            <span>Rios e córregos próximos</span>
          </div>
          <div className="flex items-center gap-3 text-sm text-slate-700">
            <span className="h-3 w-3 rounded-full bg-sky-600"></span>
            <span>Azul: sem risco simulado</span>
          </div>
          <div className="flex items-center gap-3 text-sm text-slate-700">
            <span className="h-3 w-3 rounded-full bg-yellow-400"></span>
            <span>Amarelo: risco baixo</span>
          </div>
          <div className="flex items-center gap-3 text-sm text-slate-700">
            <span className="h-3 w-3 rounded-full bg-orange-500"></span>
            <span>Laranja: risco moderado</span>
          </div>
          <div className="flex items-center gap-3 text-sm text-slate-700">
            <span className="h-3 w-3 rounded-full bg-red-600"></span>
            <span>Vermelho: risco alto</span>
          </div>
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
            A cor e a sigla identificam a severidade informada para cada estação.
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
