import { useEffect, useMemo, useState } from "react";
import { useOutletContext, useParams } from "react-router";
import {
  obterEstacao,
  obterLimitesEstacao,
  listarMedicoesEstacao,
  obterMetadados,
  usaApiReal,
} from "../api/cliente";
import CivilDefenseWarning from "../components/CivilDefenseWarning";
import MonthlyRainCard from "../components/MonthlyRainCard";

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
      <p className="station-detail-muted">
        Os pontos são espaçados igualmente; intervalos sem leitura não aparecem
        no eixo do tempo.
      </p>
      {latest.atualizado_na_fonte_em && (
        <p className="station-detail-muted">
          Atualização informada pela fonte:{" "}
          {formatDate(latest.atualizado_na_fonte_em)}
        </p>
      )}
    </>
  );
}

function LimitCards({ limites, grandeza, indisponiveis }) {
  const limitesDaGrandeza = limites.filter(
    (item) => item.grandeza === grandeza,
  );
  if (!limitesDaGrandeza.length) {
    return (
      <p className="station-detail-empty">
        {indisponiveis ? (
          "Não foi possível carregar os limites desta estação."
        ) : (
          <>
            Não há limites cadastrados para{" "}
            {granularityLabels[grandeza]?.toLocaleLowerCase("pt-BR") ||
              "esta medição"}{" "}
            nesta estação. A severidade não pode ser calculada por uma cota não
            cadastrada.
          </>
        )}
      </p>
    );
  }

  return limitesDaGrandeza.map((limite) => (
    <div key={limite.tipo}>
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
          <div className="station-limit-item" key={`${limite.tipo}-${label}`}>
            <span>{label}</span>
            <strong>{formatValue(value, limite.unidade)}</strong>
          </div>
        ))}
      </div>
    </div>
  ));
}

function chooseGranularity(current, granularities) {
  if (current && granularities.includes(current)) return current;
  if (granularities.includes("NIVEL")) return "NIVEL";
  return granularities[0] || null;
}

function stationTypeLabel(station) {
  return station.tipo === "FLUVIOMETRICA" ? "Fluviométrica" : "Pluviométrica";
}

function dataOriginLabel(metadados) {
  if (metadados?.origem_dados === "simulado") return "Dados simulados";
  if (metadados?.origem_dados === "real") return "Dados reais";
  return "Origem não informada";
}

function useStationDetails(codigo) {
  const [station, setStation] = useState(null);
  const [limites, setLimites] = useState([]);
  const [limitesIndisponiveis, setLimitesIndisponiveis] = useState(false);
  const [metadados, setMetadados] = useState(null);
  const [grandeza, setGrandeza] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    setStation(null);
    setLimites([]);
    setLimitesIndisponiveis(false);
    setMetadados(null);
    setLoading(true);
    setError("");

    async function carregarDetalhes() {
      try {
        const stationResult = await obterEstacao(codigo, {
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        setStation(stationResult);
        setGrandeza((current) =>
          chooseGranularity(current, stationResult.grandezas),
        );

        const [limitResult, metadataResult] = await Promise.allSettled([
          obterLimitesEstacao(codigo, { signal: controller.signal }),
          obterMetadados({ signal: controller.signal }),
        ]);
        if (controller.signal.aborted) return;
        setLimites(limitResult.status === "fulfilled" ? limitResult.value : []);
        setLimitesIndisponiveis(limitResult.status === "rejected");
        setMetadados(
          metadataResult.status === "fulfilled" ? metadataResult.value : null,
        );
      } catch (requestError) {
        if (!controller.signal.aborted) setError(requestError.message);
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    void carregarDetalhes();
    return () => controller.abort();
  }, [codigo]);

  return {
    station,
    limites,
    limitesIndisponiveis,
    metadados,
    grandeza,
    setGrandeza,
    loading,
    error,
  };
}

function useStationMeasurements(codigo, station, grandeza, periodoHoras) {
  const [serie, setSerie] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    setSerie(null);
    setError("");
    if (!station || String(station.codigo) !== String(codigo) || !grandeza) {
      setLoading(false);
      return () => controller.abort();
    }

    const fim = new Date();
    const inicio = new Date(fim.getTime() - periodoHoras * 60 * 60 * 1000);
    setLoading(true);

    async function carregarMedicoes() {
      try {
        const resultado = await listarMedicoesEstacao(codigo, {
          grandeza,
          inicio: inicio.toISOString(),
          fim: fim.toISOString(),
          signal: controller.signal,
        });
        if (!controller.signal.aborted) setSerie(resultado);
      } catch (requestError) {
        if (!controller.signal.aborted) setError(requestError.message);
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }

    void carregarMedicoes();
    return () => controller.abort();
  }, [codigo, grandeza, periodoHoras, station]);

  return { serie, loading, error };
}

function MeasurementResult({ loading, error, serie, limite }) {
  if (loading) return <output>Carregando medições...</output>;
  if (error) {
    return (
      <p role="alert" className="station-detail-error">
        {error}
      </p>
    );
  }
  if (!serie) {
    return (
      <p className="station-detail-empty">
        Esta estação não informa grandezas para consulta.
      </p>
    );
  }
  return <MeasurementChart serie={serie} limite={limite} />;
}

export default function StationDetailRoute() {
  const { codigo } = useParams();
  const { onCloseInfoSheet } = useOutletContext();
  const [periodoHoras, setPeriodoHoras] = useState(24);
  const {
    station,
    limites,
    limitesIndisponiveis,
    metadados,
    grandeza,
    setGrandeza,
    loading,
    error,
  } = useStationDetails(codigo);
  const measurements = useStationMeasurements(
    codigo,
    station,
    grandeza,
    periodoHoras,
  );
  const {
    serie,
    loading: measurementLoading,
    error: measurementError,
  } = measurements;

  const matchingLimit = useMemo(
    () =>
      limites.find(
        (item) => item.grandeza === grandeza && item.tipo === "COTA",
      ),
    [limites, grandeza],
  );

  if (loading)
    return (
      <section className="station-detail">
        <output>Carregando dados da estação...</output>
      </section>
    );
  if (error) {
    return (
      <section className="station-detail">
        <button
          type="button"
          className="station-back-button"
          onClick={onCloseInfoSheet}
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
  const typeLabel = stationTypeLabel(station);
  const sourceLabel = dataOriginLabel(metadados);

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
            Estação {station.codigo} · {typeLabel}
          </p>
          <h2>{station.nome}</h2>
          <p className="station-detail-muted">
            {[station.municipio, station.uf].filter(Boolean).join(" — ")}
            {station.rio ? ` · ${station.rio}` : ""}
          </p>
          <p className="station-detail-source">
            {sourceLabel}
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
                <span>Grandeza</span>
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
              <span>Período</span>
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
        <MeasurementResult
          loading={measurementLoading}
          error={measurementError}
          serie={serie}
          limite={matchingLimit}
        />
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

      {station.grandezas.includes("CHUVA") && (
        <MonthlyRainCard codigo={station.codigo} />
      )}

      <article className="station-detail-card">
        <h3>Limites cadastrados</h3>
        <p className="station-detail-muted">
          A ANA fornece medições, não estas cotas. Os limites são regras
          configuradas no TaPoo e podem ser ilustrativos; confira sua fonte
          antes de usá-los para decisões de segurança.
        </p>
        {grandeza ? (
          <LimitCards
            limites={limites}
            grandeza={grandeza}
            indisponiveis={limitesIndisponiveis}
          />
        ) : (
          <p className="station-detail-empty">
            Nenhuma medição ou regra disponível.
          </p>
        )}
      </article>

      <article className="station-detail-card">
        <h3>Previsão hidrológica</h3>
        <p className="station-detail-empty">
          A previsão de chuva pode ser considerada pelas regras de alerta e
          aparecerá nos fatores quando contribuir para um alerta. A série
          horária de previsão ainda não é exibida nesta tela.
        </p>
      </article>

      <CivilDefenseWarning />
    </section>
  );
}
