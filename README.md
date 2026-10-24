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

```bash
cd frontend
npm install
npm run dev
```

API health check: `http://localhost:8000/health`.

## SonarQube

The GitHub Actions workflow runs a SonarQube scan after the backend and frontend
checks. Configure these in the repository settings before enabling the workflow:

- Secret: `SONAR_TOKEN`

The project name and key are defined in `sonar-project.properties`. Coverage is
intentionally excluded for the initial project phase.
