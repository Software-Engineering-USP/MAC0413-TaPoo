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
Dependencies point inward: `dominio` imports nothing from the other layers.

| Layer | Folder | Contents |
|---|---|---|
| Domain | `app/dominio` | Entities, value objects, alert rules (Strategy) |
| Application | `app/aplicacao` | Ports (abstract classes) and use cases |
| Infrastructure | `app/infra` | Port implementations: in-memory repositories, example data source |
| API | `app/api` | FastAPI routes, response schemas, wiring (`dependencias.py`) |

Stations and measurements use in-memory repositories for now. With blank ANA
credentials, the backend uses `FonteFake` (fictional stations 9000000x). When
`ANA_IDENTIFICADOR` and `ANA_SENHA` are set in the repository-root `.env`, it uses
`FonteAna` to load the ANA inventory and fetch a station's adopted measurements
when its time-series route is requested. The API token is cached until shortly
before expiration. Do not commit `.env`; `.env.example` lists the required keys.

The ANA inventory is fetched by UF on the first station-list request, not during
startup, so a slow ANA response does not prevent the backend from becoming healthy.
Successful UF inventories are cached for the lifetime of the process. The service
does not automatically request time series for every Brazilian station; measurements
are fetched on demand through the station series route. Data is still held in memory,
so persistence and scheduled refresh remain future work. ANA timestamps omit a
timezone in the documented response; the adapter currently interprets these values
in `America/Sao_Paulo` before converting them to UTC.

### Routes (read-only)

| Method | Path | Description |
|---|---|---|
| GET | `/estacoes?uf=&tipo=&apenas_telemetricas=&q=` | List stations, each with its current `severidade` and active `alerta`. `q` searches the station name, municipality and river, ignoring accents and case; without `uf` it only searches stations already loaded |
| GET | `/estacoes/proximas?lat=&lon=&raio_km=50` | Stations within a radius, nearest first |
| GET | `/estacoes/{codigo}` | One station (404 if missing) |
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
