import { useEffect, useMemo, useState } from "react";
import { useNavigate, useOutletContext, useParams } from "react-router";
import {
  obterEstacao,
  obterLimitesEstacao,
  listarMedicoesEstacao,
  obterMetadados,
  usaApiReal,
} from "../api/cliente";
import CivilDefenseWarning from "../components/CivilDefenseWarning";

const granularityLabels = { CHUVA: "Chuva", NIVEL: "Nível", VAZAO: "Vazão" };
const severityClasses = {
  NORMAL: "station-detail-severity-normal",
  ATENCAO: "station-detail-severity-attention",
  ALERTA: "station-detail-severity-alert",
  EMERGENCIA: "station-detail-severity-emergency",
};

function formatDate(value) {
  if (!value) return "Horário indisponível";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatValue(value, unit) {
  return `${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 }).format(value)} ${unit}`;
}

function MeasurementChart({ serie, limite }) {
  const points = serie.medicoes;
  if (!points.length) {
    return (
      <p className="station-detail-empty">Não há medições neste período.</p>
    );
  }

  const values = points.map((item) => item.valor);
  const maximum = Math.max(...values, limite?.emergencia ?? 0);
  const minimum = Math.min(...values, 0);
  const span = Math.max(maximum - minimum, 1);
  const coordinates = points.map((item, index) => {
    const x = points.length === 1 ? 50 : (index / (points.length - 1)) * 100;
    const y = 90 - ((item.valor - minimum) / span) * 80;
    return `${x},${y}`;
  });
  const thresholdLines = limite
    ? [
        ["Atenção", limite.atencao, "attention"],
        ["Alerta", limite.alerta, "alert"],
        ["Emergência", limite.emergencia, "emergency"],
      ].map(([label, value, level]) => ({
        label,
        level,
        y: 90 - ((value - minimum) / span) * 80,
      }))
    : [];
  const latest = points.at(-1);

  return (
    <>
      <div
        className="station-chart-wrap"
        role="img"
        aria-label={`Gráfico de ${serie.grandeza_rotulo}`}
      >
        <svg
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          aria-hidden="true"
        >
          {[25, 50, 75].map((y) => (
            <line
              key={y}
              x1="0"
              x2="100"
              y1={y}
              y2={y}
              className="station-chart-grid"
            />
          ))}
          {thresholdLines.map((line) => (
            <line
              key={line.label}
              x1="0"
              x2="100"
              y1={line.y}
              y2={line.y}
              className={`station-chart-threshold station-chart-threshold-${line.level}`}
            />
          ))}
          <polyline
            points={coordinates.join(" ")}
            className="station-chart-line"
          />
        </svg>
      </div>
      <div className="station-chart-caption">
        <span>
          Última leitura:{" "}
          <strong>{formatValue(latest.valor, serie.unidade)}</strong>
        </span>
        <span>{formatDate(latest.data_hora_utc)}</span>
      </div>
      {thresholdLines.length > 0 && (
        <div
          className="station-chart-legend"
          aria-label="Limites exibidos no gráfico"
        >
          {thresholdLines.map((line) => (
            <span key={line.label}>
              <i
                className={`station-chart-dot station-chart-dot-${line.level}`}
              />
              {line.label}
            </span>
          ))}
        </div>
      )}
      {latest.atualizado_na_fonte_em && (
        <p className="station-detail-muted">
          Atualização informada pela fonte:{" "}
          {formatDate(latest.atualizado_na_fonte_em)}
        </p>
      )}
    </>
  );
}

function LimitCards({ limites, grandeza }) {
  const limite = limites.find((item) => item.grandeza === grandeza);
  if (!limite) {
    return (
      <p className="station-detail-empty">
        Não há limites cadastrados para{" "}
        {granularityLabels[grandeza]?.toLocaleLowerCase("pt-BR") ||
          "esta medição"}{" "}
        nesta estação. A severidade não pode ser calculada por uma cota não
        cadastrada.
      </p>
    );
  }

  return (
    <>
      <p className="station-detail-muted">
        {limite.descricao}
        {limite.janela_horas ? ` · acumulado em ${limite.janela_horas} h` : ""}
      </p>
      <div className="station-limit-grid">
        {[
          ["Atenção", limite.atencao],
          ["Alerta", limite.alerta],
          ["Emergência", limite.emergencia],
        ].map(([label, value]) => (
          <div className="station-limit-item" key={label}>
            <span>{label}</span>
            <strong>{formatValue(value, limite.unidade)}</strong>
          </div>
        ))}
      </div>
    </>
  );
}

export default function StationDetailRoute() {
  const { codigo } = useParams();
  const navigate = useNavigate();
  const { onCloseInfoSheet } = useOutletContext();
  const [station, setStation] = useState(null);
  const [limites, setLimites] = useState([]);
  const [metadados, setMetadados] = useState(null);
  const [serie, setSerie] = useState(null);
  const [grandeza, setGrandeza] = useState(null);
  const [periodoHoras, setPeriodoHoras] = useState(24);
  const [loading, setLoading] = useState(true);
  const [measurementLoading, setMeasurementLoading] = useState(false);
  const [error, setError] = useState("");
  const [measurementError, setMeasurementError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    setSerie(null);
    setStation(null);
    setLimites([]);
    setLoading(true);
    setError("");
    obterEstacao(codigo, { signal: controller.signal })
      .then((stationResult) => {
        setStation(stationResult);
        setGrandeza((current) =>
          current && stationResult.grandezas.includes(current)
            ? current
            : stationResult.grandezas.includes("NIVEL")
              ? "NIVEL"
              : stationResult.grandezas[0] || null,
        );
        return Promise.all([
          obterLimitesEstacao(codigo, { signal: controller.signal }),
          obterMetadados({ signal: controller.signal }),
        ]);
      })
      .then(([limitResult, metadataResult]) => {
        setLimites(limitResult);
        setMetadados(metadataResult);
      })
      .catch((requestError) => {
        if (requestError.name !== "AbortError") setError(requestError.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [codigo]);

  useEffect(() => {
    if (!station || !grandeza) return undefined;
    const controller = new AbortController();
    setSerie(null);
    const fim = new Date();
    const inicio = new Date(fim.getTime() - periodoHoras * 60 * 60 * 1000);
    setMeasurementLoading(true);
    setMeasurementError("");
    listarMedicoesEstacao(codigo, {
      grandeza,
      inicio: inicio.toISOString(),
      fim: fim.toISOString(),
      signal: controller.signal,
    })
      .then(setSerie)
      .catch((requestError) => {
        if (requestError.name !== "AbortError")
          setMeasurementError(requestError.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setMeasurementLoading(false);
      });
    return () => controller.abort();
  }, [codigo, grandeza, periodoHoras, station]);

  const matchingLimit = useMemo(
    () => limites.find((item) => item.grandeza === grandeza),
    [limites, grandeza],
  );

  if (loading)
    return (
      <section className="station-detail">
        <p role="status">Carregando dados da estação...</p>
      </section>
    );
  if (error) {
    return (
      <section className="station-detail">
        <button
          type="button"
          className="station-back-button"
          onClick={() => navigate(-1)}
        >
          ← Voltar
        </button>
        <div className="station-detail-card" role="alert">
          <h2>Não foi possível abrir a estação</h2>
          <p>{error}</p>
        </div>
      </section>
    );
  }
  if (!station) return null;

  const latest = serie?.medicoes?.at(-1);
  const lastUpdated = latest?.atualizado_na_fonte_em || latest?.data_hora_utc;
  const severity = station.severidade || "NORMAL";

  return (
    <section className="station-detail">
      <button
        type="button"
        className="station-back-button"
        onClick={onCloseInfoSheet}
      >
        ← Voltar ao mapa
      </button>
      <header className="station-detail-header">
        <div>
          {(!usaApiReal || metadados?.origem_dados === "simulado") && (
            <span className="demo-data-badge station-demo-badge">
              DEMONSTRAÇÃO · DADOS SIMULADOS
            </span>
          )}
          <p className="station-detail-eyebrow">
            Estação {station.codigo} ·{" "}
            {station.tipo === "FLUVIOMETRICA"
              ? "Fluviométrica"
              : "Pluviométrica"}
          </p>
          <h2>{station.nome}</h2>
          <p className="station-detail-muted">
            {[station.municipio, station.uf].filter(Boolean).join(" — ")}
            {station.rio ? ` · ${station.rio}` : ""}
          </p>
          <p className="station-detail-source">
            {metadados?.origem_dados === "simulado"
              ? "Dados simulados"
              : "Dados reais"}
            {" · última atualização: "}
            {lastUpdated ? formatDate(lastUpdated) : "sem leitura disponível"}
          </p>
        </div>
        <span
          className={`station-detail-severity ${severityClasses[severity] || severityClasses.NORMAL}`}
        >
          {station.severidade_rotulo || "Normal"}
        </span>
      </header>

      {station.alerta ? (
        <article className="station-detail-card station-alert-card">
          <h3>
            <i
              className="fa-solid fa-triangle-exclamation"
              aria-hidden="true"
            />{" "}
            Alerta ativo
          </h3>
          <p>{station.alerta.mensagem}</p>
          <p className="station-detail-muted">
            Classificação calculada pelas regras configuradas no TaPoo; não é um
            alerta oficial da Defesa Civil.
          </p>
          <p className="station-detail-muted">
            Emitido em {formatDate(station.alerta.emitido_em)}
          </p>
          {station.alerta.fatores?.length > 0 && (
            <ul>
              {station.alerta.fatores.map((factor, index) => (
                <li key={`${factor.descricao}-${index}`}>{factor.descricao}</li>
              ))}
            </ul>
          )}
        </article>
      ) : (
        <article className="station-detail-card">
          <h3>Situação atual</h3>
          <p>Nenhum alerta ativo para esta estação.</p>
        </article>
      )}

      <article className="station-detail-card">
        <div className="station-section-heading">
          <div>
            <h3>Medições recentes</h3>
            <p className="station-detail-muted">
              Série do período escolhido, conforme dados disponibilizados pela
              fonte.
            </p>
          </div>
          <div className="station-measure-controls">
            {station.grandezas.length > 0 && (
              <label className="station-measure-select">
                Grandeza
                <select
                  value={grandeza || ""}
                  onChange={(event) => setGrandeza(event.target.value)}
                >
                  {station.grandezas.map((item) => (
                    <option key={item} value={item}>
                      {granularityLabels[item] || item}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <label className="station-measure-select">
              Período
              <select
                value={periodoHoras}
                onChange={(event) =>
                  setPeriodoHoras(Number(event.target.value))
                }
              >
                <option value={24}>24 horas</option>
                <option value={168}>7 dias</option>
                <option value={720}>30 dias</option>
              </select>
            </label>
          </div>
        </div>
        {measurementLoading ? (
          <p role="status">Carregando medições...</p>
        ) : measurementError ? (
          <p role="alert" className="station-detail-error">
            {measurementError}
          </p>
        ) : serie ? (
          <MeasurementChart serie={serie} limite={matchingLimit} />
        ) : (
          <p className="station-detail-empty">
            Esta estação não informa grandezas para consulta.
          </p>
        )}
        {latest && (
          <p className="station-detail-muted">
            Consistência:{" "}
            {latest.consistencia === "CONSISTIDO" ? "consistida" : "bruta"}
            {latest.origem
              ? ` · origem: ${latest.origem.toLocaleLowerCase("pt-BR")}`
              : ""}
            {latest.status_fonte
              ? ` · status da fonte: ${latest.status_fonte}`
              : ""}
          </p>
        )}
      </article>

      <article className="station-detail-card">
        <h3>Limites cadastrados</h3>
        <p className="station-detail-muted">
          A ANA fornece medições, não estas cotas. Os limites são regras
          configuradas no TaPoo e podem ser ilustrativos; confira sua fonte
          antes de usá-los para decisões de segurança.
        </p>
        {grandeza ? (
          <LimitCards limites={limites} grandeza={grandeza} />
        ) : (
          <p className="station-detail-empty">
            Nenhuma medição ou regra disponível.
          </p>
        )}
      </article>

      <article className="station-detail-card">
        <h3>Previsão hidrológica</h3>
        <p className="station-detail-empty">
          A fonte consultada disponibiliza medições observadas, mas não fornece
          previsão para esta estação. O sistema não estima horário de pico nem
          nível futuro.
        </p>
      </article>

      <CivilDefenseWarning />
    </section>
  );
}
