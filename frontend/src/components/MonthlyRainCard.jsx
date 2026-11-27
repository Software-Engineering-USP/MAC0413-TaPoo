import { useEffect, useState } from "react";
import { obterChuvaMensal } from "../api/cliente";

const classificationClasses = {
  ABAIXO: "station-detail-severity-attention",
  NORMAL: "station-detail-severity-normal",
  ACIMA: "station-detail-severity-alert",
};

const formatoMes = new Intl.DateTimeFormat("pt-BR", {
  month: "long",
  year: "numeric",
});

function formatarMm(valor) {
  return `${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(valor)} mm`;
}

function formatarPercentual(valor) {
  return `${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 }).format(valor)}%`;
}

/** Chuva acumulada no mês corrente comparada à normal do INMET mais próxima. */
export default function MonthlyRainCard({ codigo }) {
  const [estado, setEstado] = useState({ status: "carregando" });

  useEffect(() => {
    const controller = new AbortController();
    setEstado({ status: "carregando" });

    obterChuvaMensal(codigo, { signal: controller.signal })
      .then((chuva) => {
        if (!controller.signal.aborted) setEstado({ status: "ok", chuva });
      })
      .catch((error_) => {
        if (!controller.signal.aborted) {
          setEstado({ status: "erro", mensagem: error_.message });
        }
      });

    return () => controller.abort();
  }, [codigo]);

  const { status, chuva } = estado;
  const mes = chuva && formatoMes.format(new Date(chuva.ano, chuva.mes - 1, 1));

  return (
    <article
      className="station-detail-card"
      aria-busy={status === "carregando"}
    >
      <div className="station-section-heading">
        <div>
          <h3>Chuva do mês{mes ? ` · ${mes}` : ""}</h3>
          <p className="station-detail-muted">
            Acumulado desde o dia 1º comparado à normal climatológica do INMET
            (1991–2020) da estação mais próxima.
          </p>
        </div>
        {status === "ok" && (
          <span
            className={`station-detail-severity ${classificationClasses[chuva.classificacao] || classificationClasses.NORMAL}`}
          >
            {chuva.classificacao_rotulo}
          </span>
        )}
      </div>

      {status === "carregando" && <output>Calculando chuva do mês...</output>}

      {status === "erro" && (
        <output className="station-detail-muted block">
          Comparação indisponível: {estado.mensagem}
        </output>
      )}

      {status === "ok" && (
        <>
          <p>
            <strong>{formatarMm(chuva.acumulado_mm)}</strong> acumulados de{" "}
            {formatarMm(chuva.normal_mm)} esperados no mês
            {chuva.percentual !== null
              ? ` (${formatarPercentual(chuva.percentual)} da normal)`
              : ""}
            .
          </p>
          <p className="station-detail-muted">
            Referência: {chuva.referencia.nome} — {chuva.referencia.uf}, a{" "}
            {new Intl.NumberFormat("pt-BR").format(
              chuva.referencia.distancia_km,
            )}{" "}
            km · {chuva.medicoes}{" "}
            {chuva.medicoes === 1 ? "leitura" : "leituras"} no mês.
          </p>
        </>
      )}
    </article>
  );
}
