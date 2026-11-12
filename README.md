# MAC0413---TaPoo

Initial FastAPI + React scaffold for Tapoo project

## Requirements

`uv`, `python`, `npm`

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

## Backend architecture

The backend follows the layers described in `docs/diagramas-de-classe-ana.md`.
Dependencies point inward: `dominio` imports nothing from the other layers.

| Layer | Folder | Contents |
|---|---|---|
| Domain | `app/dominio` | Entities, value objects, alert rules (Strategy) |
| Application | `app/aplicacao` | Ports (abstract classes) and use cases |
| Infrastructure | `app/infra` | Port implementations: in-memory repositories, example data source |
| API | `app/api` | FastAPI routes, response schemas, wiring (`dependencias.py`) |

For now the data is in memory and comes from `FonteFake` (fictional stations
9000000x), loaded once at startup. The ANA adapter and SQL persistence will
replace them in `app/api/dependencias.py` without changes to services or routes.

### Routes (read-only)

| Method | Path | Description |
|---|---|---|
| GET | `/estacoes?uf=&tipo=&apenas_telemetricas=` | List stations |
| GET | `/estacoes/proximas?lat=&lon=&raio_km=50` | Stations within a radius, nearest first |
| GET | `/estacoes/{codigo}` | One station (404 if missing) |
| GET | `/estacoes/{codigo}/medicoes?grandeza=NIVEL&inicio=&fim=` | Time series (default: last 24 h, max 31 days, ISO 8601 with timezone) |
| GET | `/alertas` | Active alerts, most severe first |

## SonarQube

The GitHub Actions workflow runs a SonarQube scan after the backend and frontend
checks. Configure these in the repository settings before enabling the workflow:

- Secret: `SONAR_TOKEN`

The project name and key are defined in `sonar-project.properties`. Coverage is
intentionally excluded for the initial project phase.

## CI/CD

Pull requests and pushes to `main` run the backend checks, frontend build, and
SonarCloud analysis. Docker images are published to GHCR only when a version
tag is pushed or the workflow is started manually.

To publish a versioned image:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The workflow can also be started from GitHub Actions using **Run workflow**.
