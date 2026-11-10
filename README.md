# MAC0413---TaPoo

Initial FastAPI + React scaffold for Tapoo project

## Requirements

`uv`, `python`, `npm`

## Run with Docker Compose

From the repository root, start the frontend and backend with:

```bash
docker compose up --build
```

Open the frontend at `http://localhost:3000`. The API is available at `http://localhost:8000` and its health check is `http://localhost:8000/health`. Stop the services with `Ctrl+C`; add `-d` to run them in the background.

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
