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

API health check: `http://localhost:8000/health`.

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
