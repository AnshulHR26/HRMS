# HRMS — Enterprise Human Resource Management System

React + TypeScript frontend · **FastAPI** backend · **PostgreSQL** · SQLAlchemy 2.0 · Alembic · JWT · Pytest

Phases 1–4 are implemented: authentication, role-based access control, employee management,
and department/designation management. Phases 5–8 (attendance, leave, payroll, performance)
have architectural hooks only. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

> Full step-by-step installation, configuration and troubleshooting: **[SETUP.md](SETUP.md)**.

## Quick start (local)

```bash
# 1. Database
createuser -P hrms            # choose a password
createdb -O hrms hrms
createdb -O hrms hrms_test    # used by the test suite

# 2. Backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# create backend/.env with DATABASE_URL, TEST_DATABASE_URL, JWT_SECRET_KEY,
# BOOTSTRAP_ADMIN_PASSWORD, DEMO_USER_PASSWORD (see SETUP.md §3.1)
alembic upgrade head
python -m app.scripts.bootstrap_admin
python -m app.scripts.seed_demo          # optional demo data (dev only)
uvicorn app.main:app --reload            # http://localhost:8000/docs

# 3. Frontend (new terminal)
cd frontend
npm install                               # frontend/.env: VITE_API_BASE_URL, VITE_PROXY_TARGET (SETUP.md §4)
npm run dev                               # http://localhost:5173

# 4. Tests
cd backend && pytest
```

## Demo accounts (after `seed_demo`)

| Role | User ID | Password |
|---|---|---|
| Admin | value of `BOOTSTRAP_ADMIN_USER_ID` (default `admin`) | `BOOTSTRAP_ADMIN_PASSWORD` |
| HR | `hr.manager`, `hr.exec` | `DEMO_USER_PASSWORD` |
| Employee | `employee` (Ananya Iyer), `arjun.mehta`, `vikram.singh`, … | `DEMO_USER_PASSWORD` |

No credentials are hardcoded: every password comes from environment variables.

## Security model in one paragraph

Passwords are hashed with Argon2id. Login returns an HS256 JWT (with `sub`, `role`, `jti`, `ver`, `exp`),
which is also set as an **httpOnly, SameSite=Lax cookie**. JavaScript cannot read the cookie, so XSS cannot steal the token.
Cookie-authenticated writes must echo a CSRF double-submit token. Swagger and API clients use
`Authorization: Bearer`. Logout deny-lists the token's `jti`. Password changes, role changes and deactivation
bump `users.token_version`, which revokes every outstanding token. All authorization happens in FastAPI
dependencies (`require_admin`, `require_hr_or_admin`, `require_employee`) and service-level policy checks.
The React route guards only shape the UI.

## Repository layout

```
backend/   FastAPI app (routers → services → models), Alembic migrations, pytest suite
frontend/  Vite + React + TypeScript SPA
docs/      Architecture, ER diagram, API map, phase plan
```
