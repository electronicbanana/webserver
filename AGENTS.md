# Repository Guidelines

## Project Structure & Module Organization
- `backend/` — Flask API (`app.py`), writes chat history to `messages.json`. A local `venv/` exists for convenience; you may create your own.
- `frontend/` — React + Vite app (`src/`, `index.html`, `vite.config.js`). Built assets go to `dist/`.
- Do not edit generated or vendor folders: `backend/venv/`, `frontend/node_modules/`, `frontend/dist/`.

## Build, Test, and Development Commands
- Backend (quick): `python backend/app.py` (serves on `http://127.0.0.1:5000`).
- Backend (with venv): `cd backend && source venv/bin/activate && python app.py`.
- Frontend dev: `cd frontend && npm install && npm run dev` (Vite proxies `/api` to `:5000`).
- Frontend build: `npm run build` (outputs to `frontend/dist/`).
- Lint frontend: `npm run lint`.

## Coding Style & Naming Conventions
- Python (backend): follow PEP 8, 4‑space indentation, snake_case for files/functions, prefer type hints. Keep handlers small and pure where possible.
- JavaScript/React (frontend): ESLint is configured (`frontend/eslint.config.js`). Use PascalCase for components, camelCase for hooks/props, kebab-case for CSS classes.
- Keep module boundaries clear: API logic in `backend/app.py`; UI logic and fetch calls in `frontend/src/*`.

## Testing Guidelines
- No formal tests yet. Recommended:
  - Backend: Pytest in `backend/tests/` with `test_*.py`; target critical route/unit coverage first.
  - Frontend: Vitest + React Testing Library in `frontend/src/__tests__/*.test.jsx`.
- Aim for ≥80% coverage once frameworks are added. Keep tests deterministic and fast.

## Commit & Pull Request Guidelines
- Use clear, imperative messages; Conventional Commits encouraged: `feat:`, `fix:`, `chore:`, `docs:`.
- Keep subject ≤72 chars; include rationale in the body and link related issues.
- PRs should include: summary, before/after notes, run steps, and screenshots for UI changes. Keep diffs focused and scoped.

## Security & Configuration Tips
- Do not commit secrets or tokens. Add ignores for `backend/venv/`, `frontend/node_modules/`, `frontend/dist/`, `__pycache__/`, and `backend/messages.json` in a root `.gitignore`.
- The Flask dev server (`debug=True`) is for local use only; use a production WSGI server for deployment.

## Agent-Specific Instructions
- Scope: entire repo. Prefer minimal, surgical diffs; avoid touching vendor/generated folders.
- When adding tools or tests, mirror the structure above and document commands.
