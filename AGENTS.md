# Instruction
「THINK HARD」

# Repository Guidelines

## Project Structure & Module Organization
- `backend/`: FastAPI app, database models/schemas, API routers, and background workers.
- `web/`: React + Vite UI (MUI). Dev runs via nginx proxy to Vite; production builds served by nginx.
- `kmp/`: Kotlin Multiplatform (shared + desktop/android). Shared models, network, use-cases, and UI.
- `services/`: gRPC microservices (resize, ai-detection, filter, camera-stream).
- `deploy/compose/`: Docker Compose files (`docker-compose.yml`, `docker-compose.dev.yml`).
- `scripts/`: Convenience scripts (build, run, status, health checks).
- `docs/`: Design docs (DB/API/UI) that define contracts and behavior.

## Build, Test, and Development Commands
- Compose (prod-like): `./scripts/run-compose.sh up` — builds (if needed) and starts core services.
- Compose (dev, hot reload UI): `./scripts/run-compose.sh dev` — UI at `http://localhost:3000` (nginx → Vite).
- Build images: `./scripts/build_services.sh` — builds backend/web/services images used by Compose.
- Web UI: `cd web && npm ci && npm run build` — produces static bundle.
- Backend (local): `uvicorn app.main:app --reload --port 8000` (inside `backend/`).
- KMP: `cd kmp && ./gradlew build` (common tests) • Desktop run: `./gradlew :desktopApp:run`.

## Coding Style & Naming Conventions
- Python: 4-space indent, type hints; Pydantic/SQLAlchemy models use `metadata_` for DB column "metadata".
- Kotlin: Kotlin style conventions; prefer explicit names (e.g., `productCode`), avoid one-letter vars.
- TypeScript/React: Functional components, hooks-first; keep modules small and typed.
- Naming: Prefer `product_code` (backend, DB) and `productCode` (KMP/TS). Avoid `product_type`.

## Testing Guidelines
- KMP: common tests via `./gradlew test`. Place tests under `kmp/shared/src/commonTest/...`.
- Web/Backend: add focused tests near modules (if applicable). Keep small, fast, and deterministic.
- Test naming: mirror source path and describe behavior (e.g., `InspectionModelsTest.kt`).

## Commit & Pull Request Guidelines
- Commits: concise, imperative subject (<= 72 chars), meaningful body when needed (what/why). Group related changes.
- PRs: include purpose, linked issues, test evidence (logs/screenshots), and rollout notes. Keep scope tight.

## Security & Configuration Tips
- Secrets: do not commit tokens/keys; use env vars. Backend JWT `SECRET_KEY` must be set in production.
- Web dev: access via `http://localhost:3000` (nginx). Vite HMR is proxied; `3001` is internal by default.
