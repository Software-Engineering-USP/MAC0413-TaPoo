export default function CivilDefenseWarning() {
  return (
    <div
      role="note"
      aria-label="Aviso sobre alertas oficiais"
      className="dashboard-card rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-amber-950"
    >
      <div className="flex items-start gap-2">
        <i
          className="fa-solid fa-triangle-exclamation mt-0.5 text-amber-700"
          aria-hidden="true"
        ></i>
        <p className="flex-1 text-xs font-medium leading-relaxed">
          <strong>Aviso:</strong> Este sistema não substitui os alertas oficiais
          da Defesa Civil. Em uma emergência, acompanhe os canais oficiais.
        </p>
      </div>
    </div>
  );
}
