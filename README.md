# MAC0413---TaPoo

Initial FastAPI + React scaffold for Tapoo project

## Requirements

`uv`, `python`, `npm`

## Run with Docker Compose

Before the first run, create the local configuration file if it does not exist,
then start the frontend and backend from the repository root:

```bash
[ -f .env ] || cp .env.example .env
docker compose up --build
```

To enable live ANA data, fill `ANA_IDENTIFICADOR` and `ANA_SENHA` in `.env` first.
With both blank, the backend keeps using its fictional sample source.

Compose also starts a PostgreSQL service (`db`) and the backend stores stations,
measurements and alerts there (`REPO=sql`), so data survives restarts. The database
lives in the `dados-postgres` volume; `docker compose down -v` erases it.
The backend collects new readings for the monitored stations it already knows and
re-evaluates their alerts every `COLETA_INTERVALO_MINUTOS` minutes (default `15`; `0`
turns the background collection off).

Open the frontend at `http://localhost:3000`. The API is available at `http://localhost:8000` and its health check is `http://localhost:8000/health`. Stop the services with `Ctrl+C`; add `-d` to run them in the background.

## Run locally

```bash
cd backend
uv sync --extra dev
uv run pytest -q
uv run uvicorn app.main:app --reload
```

Lint and format (the same checks run in CI):

```bash
cd backend
uv run ruff check .
uv run ruff format .          # apply formatting
uv run ruff format --check .  # check only (CI)
```

```bash
cd frontend
npm install
npm run dev
```

Lint and format (the same checks run in CI):

```bash
cd frontend
npm run lint
npm run format        # apply Prettier
npm run format:check  # check only (CI)
```

API health check: `http://localhost:8000/health`. Interactive docs: `http://localhost:8000/docs`.

The API only accepts browser requests (CORS) from the origins in `CORS_ORIGENS`,
comma-separated. When unset, it allows the local frontend
(`http://localhost:3000` and `http://localhost:5173`); in production, set it to the
public frontend URL, e.g. `CORS_ORIGENS=https://tapoo.example.org`.

## Deploy

The production frontend runs on Vercel and the FastAPI backend runs on Render.
Render builds the backend from `backend/Dockerfile` using the root `render.yaml`
Blueprint.
The Blueprint also creates a Render Postgres database (`tapoo-db`) and points the
API at it with `REPO=sql` and `DATABASE_URL`; tables are created on startup. Both
use Render's free plan, and a free Postgres database expires 30 days after creation
unless it is upgraded.

### First deployment

1. Import this repository into Vercel and set the project root directory to
   `frontend`. Vercel detects Vite and builds the static site.
2. In Render, create a Blueprint connected to this repository and use its root
   `render.yaml`. Provide
   `ANA_IDENTIFICADOR` and `ANA_SENHA` when prompted to enable live ANA data, and
   set `CORS_ORIGENS` to the Vercel production origin (for example,
   `https://tapoo.vercel.app`). Keep these values in Render's environment settings.
3. Copy the Render service URL (for example, `https://tapoo-api.onrender.com`) into
   Vercel's `VITE_API_URL` environment variable for Production, then redeploy the
   frontend. Vite embeds this URL into the frontend at build time.
4. Check `https://<render-service>.onrender.com/health`, then use the deployed
   frontend to confirm it can search stations through the API.

For Vercel Preview deployments, add their origins to `CORS_ORIGENS` if they should
be allowed to call the production API, and set `VITE_API_URL` for the Preview
environment too. `CORS_ORIGENS` accepts comma-separated exact origins. The Render
service health check is configured as `/health` in the Blueprint. Update this
README with the final public frontend and API URLs after deployment.

## Backend architecture

The backend follows the layers described in `docs/diagramas-de-classe-ana.md`.
The object-oriented concepts, station-modeling decision, and design patterns used by
the backend are discussed in [the POO report](docs/relatorio-poo.md).
Testing, refactoring examples, and a manual validation checklist are documented in
[the test report](docs/relatorio-testes.md).
Dependencies point inward: `dominio` imports nothing from the other layers.

| Layer | Folder | Contents |
|---|---|---|
| Domain | `app/dominio` | Entities, value objects, alert rules (Strategy) |
| Application | `app/aplicacao` | Ports (abstract classes) and use cases |
| Infrastructure | `app/infra` | Port implementations: in-memory and SQL repositories (`infra/persistencia`), data sources |
| API | `app/api` | FastAPI routes, response schemas, wiring (`dependencias.py`) |

### Persistence

`REPO` chooses where stations, measurements and alerts are stored:

| `REPO` | Storage | Notes |
|---|---|---|
| `memoria` (default outside compose) | Process memory | Lost on restart; used by the tests |
| `sql` (default in compose) | Database at `DATABASE_URL` | SQLAlchemy; PostgreSQL in compose, `sqlite:///tapoo.db` when `DATABASE_URL` is blank |

`app/infra/persistencia/modelos_orm.py` maps the tables and `repositorios_sql.py`
implements the same ports as the in-memory repositories (`EstacaoRepositorioSql`,
`MedicaoRepositorioSql`, `AlertaRepositorioSql`). Measurements are upserted by their
natural key `(codigo_estacao, grandeza, data_hora_utc, origem)`, and dates are stored
in UTC. Tables are created on startup if missing; there are no migrations yet. The
simulated stations, measurement profiles, and alert thresholds are loaded from
`backend/app/infra/fontes/dados/cenario-demo.json`.

The repository contract tests (`tests/infra/test_repositorios_contrato.py`) run
against memory and SQLite, and also against PostgreSQL when `TEST_DATABASE_URL` is
set, as in CI:

```bash
docker run -d --rm --name tapoo-pg -e POSTGRES_USER=tapoo -e POSTGRES_PASSWORD=tapoo \
  -e POSTGRES_DB=tapoo_teste -p 5432:5432 postgres:17-alpine
TEST_DATABASE_URL=postgresql://tapoo:tapoo@localhost:5432/tapoo_teste uv run pytest
```

### Data sources

`FONTE` selects the hydrological source: `ana` uses the ANA API and requires both
`ANA_IDENTIFICADOR` and `ANA_SENHA`; `fake` and `simulada` use fictional stations
9000000x from the JSON scenario. `fake` remains an alias for `simulada`. If `FONTE` is
blank, the backend selects ANA when credentials are present and the simulated source
otherwise. Unknown values fail at startup instead of silently choosing a source. Do
not commit `.env`; `.env.example` lists the available settings.

`FonteAna` loads the ANA inventory and fetches a station's adopted measurements when
its time-series route is requested. The API token is cached until shortly before
expiration. Rainfall alerts also use hourly precipitation forecasts from Open-Meteo;
forecast failures are logged and do not stop collection for other stations.

The ANA inventory is fetched by UF on the first station-list request, not during
startup, so a slow ANA response does not prevent the backend from becoming healthy.
Successful UF inventories are cached for the lifetime of the process. The service
does not automatically request time series for every Brazilian station; measurements
are fetched on demand through the station series route. ANA timestamps omit a
timezone in the documented response; the adapter currently interprets these values
in `America/Sao_Paulo` before converting them to UTC.

### Routes (read-only)

| Method | Path | Description |
|---|---|---|
| GET | `/estacoes?uf=&tipo=&apenas_telemetricas=&q=` | List stations, each with its current `severidade` and active `alerta`. `q` searches the station name, municipality and river, ignoring accents and case; without `uf` it only searches stations already loaded |
| GET | `/estacoes/proximas?lat=&lon=&raio_km=50` | Stations within a radius, nearest first |
| GET | `/estacoes/{codigo}` | One station (404 if missing) |
| GET | `/estacoes/{codigo}/alertas?limite=50` | Alert history of one station (active and closed), newest first |
| GET | `/estacoes/{codigo}/medicoes?grandeza=NIVEL&inicio=&fim=` | Time series (default: last 24 h, max 31 days, ISO 8601 with timezone) |
| GET | `/alertas` | Active alerts, most severe first |
| GET | `/municipios/{uf}/{nome}/situacao` | Worst severity among the municipality's stations (name matched ignoring accents and case; 404 if none) |

## SonarQube

The GitHub Actions workflow runs a SonarQube scan after the backend and frontend
checks. Configure these in the repository settings before enabling the workflow:

- Secret: `SONAR_TOKEN`

The project name and key are defined in `sonar-project.properties`. The backend job
uploads `coverage.xml` for the scan and fails if total coverage (lines and branches)
drops below 80%. The threshold is `fail_under` in `[tool.coverage.report]` of
`backend/pyproject.toml`, so `uv run pytest --cov` enforces it locally too.

## CI/CD

Pull requests and pushes to `main` run the backend checks, frontend build, and
SonarCloud analysis. Render builds the backend image from the repository when
deploying; CI does not publish container images.
