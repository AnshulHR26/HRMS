# HRMS — Setup & Operations Guide

This guide covers installing, configuring, running, testing and deploying the HRMS
(React + TypeScript · FastAPI · PostgreSQL · SQLAlchemy 2.0 · Alembic).

---

## 1. Prerequisites

| Tool | Version | Check |
|---|---|---|
| Python | 3.12 or newer | `python3 --version` |
| PostgreSQL | 14 or newer (16 recommended) | `psql --version` |
| Node.js | 20 LTS or newer (22 recommended) | `node --version` |
| npm | 10+ | `npm --version` |
| Docker + Compose (optional) | Docker 24+, Compose v2 | `docker compose version` |
| Git | any | `git --version` |

### Installing PostgreSQL

* **macOS (Homebrew):** `brew install postgresql@16 && brew services start postgresql@16`
* **Ubuntu/Debian:** `sudo apt install postgresql && sudo systemctl enable --now postgresql`
* **Windows:** use the EDB installer from postgresql.org and keep "Command Line Tools" ticked.
* **Docker only:** `docker compose up db` starts the database from `docker-compose.yml`.

---

## 2. Database setup

Create one application role and two databases: the app database, plus a disposable one for the tests.

```bash
# Linux: run as the postgres OS user  (macOS Homebrew: your own user is a superuser)
sudo -u postgres psql <<'SQL'
CREATE USER hrms WITH PASSWORD 'choose-a-strong-password' CREATEDB;
CREATE DATABASE hrms OWNER hrms;
CREATE DATABASE hrms_test OWNER hrms;
SQL
```

Check the connection:

```bash
psql "postgresql://hrms:choose-a-strong-password@localhost:5432/hrms" -c "select 1"
```

> The test suite **drops and recreates the `public` schema of `hrms_test`** on every run.
> Never point `TEST_DATABASE_URL` at a database whose data you want to keep.

---

## 3. Backend setup

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

### 3.1 Environment variables (`backend/.env`)

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `DATABASE_URL` | yes | — | `postgresql+psycopg://hrms:<pw>@localhost:5432/hrms` |
| `TEST_DATABASE_URL` | for tests | `…/hrms_test` | Disposable test database |
| `JWT_SECRET_KEY` | yes | — | ≥ 32 chars. Generate: `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `JWT_ALGORITHM` | no | `HS256` | Pinned; other algorithms are rejected |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | `30` | Token and cookie lifetime |
| `ENVIRONMENT` | no | `development` | `development`, `test` or `production` (demo seeding is refused in production) |
| `CORS_ORIGINS` | no | `http://localhost:5173` | Comma-separated list of allowed browser origins |
| `COOKIE_SECURE` | no | `false` | Set `true` behind HTTPS |
| `COOKIE_SAMESITE` | no | `lax` | `lax`, `strict` or `none` (`none` requires `COOKIE_SECURE=true`) |
| `LOGIN_MAX_FAILED_ATTEMPTS` | no | `5` | Failed logins before a temporary lock |
| `LOGIN_LOCKOUT_MINUTES` | no | `15` | Lock duration |
| `BOOTSTRAP_ADMIN_USER_ID` | no | `admin` | Initial admin login ID |
| `BOOTSTRAP_ADMIN_PASSWORD` | for bootstrap | — | 8+ chars, with letters and digits |
| `DEMO_USER_PASSWORD` | for demo seed | — | Shared password for every demo account |

### 3.2 Create the schema (Alembic)

```bash
alembic upgrade head        # creates tables, indexes, the employee ID sequence and the 3 roles
alembic current             # -> 0001_initial_schema (head)
```

Useful migration commands:

```bash
alembic history
alembic downgrade -1
alembic revision --autogenerate -m "describe change"   # after editing models
alembic check               # fails if models and migrations have drifted
```

### 3.3 Create the first administrator

The admin is created by a controlled bootstrap script, never by a default credential:

```bash
python -m app.scripts.bootstrap_admin                     # idempotent
python -m app.scripts.bootstrap_admin --reset-password    # rotate the password from .env
```

### 3.4 Optional demo data (development only)

```bash
python -m app.scripts.seed_demo
```

This creates 5 departments, 10 designations and 11 employees, including 2 HR users,
reporting lines and a mix of employment types. Every record goes through the real service layer,
so validation and Employee ID generation are exercised. Running it twice is safe.

| Login | Role | Name |
|---|---|---|
| `admin` (or your bootstrap ID) | ADMIN | system account |
| `hr.manager` | HR | Priya Sharma |
| `hr.exec` | HR | Rahul Verma |
| `employee` | EMPLOYEE | Ananya Iyer (reports to Arjun Mehta) |
| `arjun.mehta`, `vikram.singh`, `sneha.patel`, `kavya.reddy`, `rohan.das`, `meera.nair`, `aditya.kumar`, `farhan.ali` | EMPLOYEE | — |

### 3.5 Run the API

```bash
uvicorn app.main:app --reload --port 8000
```

* Swagger UI: <http://localhost:8000/docs>
* ReDoc: <http://localhost:8000/redoc>
* OpenAPI JSON: <http://localhost:8000/api/v1/openapi.json>
* Health check: <http://localhost:8000/health>

**Using Swagger:** run `POST /api/v1/auth/login`, copy `access_token`, click **Authorize**
and paste the token.

**Using curl:**

```bash
TOKEN=$(curl -s localhost:8000/api/v1/auth/login -H 'Content-Type: application/json' \
  -d '{"user_id":"admin","password":"<your password>"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -s localhost:8000/api/v1/employees?page_size=5 -H "Authorization: Bearer $TOKEN"
```

---

## 4. Frontend setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev                    # http://localhost:5173
```

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `/api/v1` | API base path as the browser sees it |
| `VITE_PROXY_TARGET` | `http://localhost:8000` | Where the Vite dev server forwards `/api` |

The dev server proxies `/api` to FastAPI, so the browser treats the UI and the API as one origin.
That keeps the httpOnly cookie first-party, and you don't need cross-site cookie settings in development.

Other scripts:

```bash
npm run typecheck     # tsc --noEmit
npm run build         # type-check and produce dist/
npm run preview       # serve the production build on :4173 (also proxies /api)
```

---

## 5. Running the tests

```bash
cd backend
source .venv/bin/activate
pytest                     # whole suite
pytest -v tests/test_auth.py
pytest -k "deactivated"    # by keyword
```

The suite runs against **real PostgreSQL**, not SQLite. It builds the schema by running the
Alembic migrations, so the migrations get tested too. Tables are truncated between tests.

| File | Covers |
|---|---|
| `test_auth.py` | Mandatory cases 1–7, plus cookie/CSRF, logout revocation, lockout, password change, Argon2 |
| `test_authorization.py` | Cases 8–16, plus privilege-escalation and self-modification guards |
| `test_employees.py` | Cases 17–23, plus pagination/search/filter/sort, manager cycles, 404s |
| `test_org_and_database.py` | Department/designation CRUD, reassign-then-delete, cases 24–26, dashboards, OpenAPI |

---

## 6. Docker

```bash
cp .env.docker.example .env        # edit every secret
docker compose up --build
```

| Service | URL | Notes |
|---|---|---|
| frontend (nginx) | <http://localhost:8080> | Serves the SPA and proxies `/api` to the backend |
| backend | <http://localhost:8000/docs> | Runs `alembic upgrade head` and the admin bootstrap on start |
| db | `localhost:5432` | Data persists in the `pgdata` volume |

Set `SEED_DEMO_DATA=true` (with `DEMO_USER_PASSWORD`) to load the demo data on start.
To reset everything, run `docker compose down -v`.

---

## 7. Roles & permissions (enforced by the backend)

| Capability | ADMIN | HR | EMPLOYEE |
|---|:-:|:-:|:-:|
| Sign in, view own dashboard and profile | ✓ | ✓ | ✓ |
| Update own phone and address | ✓ | ✓ | ✓ |
| Employee directory, search, filter, view any profile | ✓ | ✓ | — |
| Create and update employees | ✓ | ✓ (not ADMIN-linked profiles) | — |
| Deactivate or reactivate employees | ✓ | ✓ (not ADMIN-linked profiles) | — |
| Create accounts with role EMPLOYEE | ✓ | ✓ | — |
| Create HR or ADMIN accounts, assign roles | ✓ | — | — |
| Enable/disable accounts and reset passwords | ✓ | EMPLOYEE accounts only | — |
| View departments and designations | ✓ | ✓ | own only (via profile) |
| Create, edit, reassign and delete departments/designations | ✓ | — | — |
| Admin dashboard | ✓ | — | — |
| HR dashboard | ✓ | ✓ | — |

Additional guards: nobody can change their own role, status or employment status, and the last
active ADMIN cannot be demoted or deactivated. Employees requesting another employee's record get
`403`, even for IDs that don't exist, so the API can't be used to discover which IDs exist.

---

## 8. Authentication design & token-storage trade-offs

| Option | XSS exposure | CSRF exposure | Chosen? |
|---|---|---|---|
| `localStorage` + Bearer header | **High.** Any injected script can read the token and replay it from anywhere | None | ✗ |
| In-memory only | Medium. Lost on refresh, so it needs a refresh-token cookie anyway | None | ✗ |
| **httpOnly cookie + CSRF double-submit** | **Low.** Scripts cannot read the token | Mitigated by SameSite=Lax plus the `X-CSRF-Token` header | ✓ |

How it works:

1. `POST /auth/login` sets `hrms_access_token` (httpOnly) and `hrms_csrf` (readable) cookies.
   It also returns the token in JSON for API clients.
2. Axios sends cookies (`withCredentials`) and copies `hrms_csrf` into `X-CSRF-Token` on POST/PUT/PATCH/DELETE.
   The backend compares the two values in constant time.
3. Every protected request: signature and `exp` are verified (HS256 only), the `jti` is checked against
   `revoked_tokens`, `token_version` must match the user row, and the user must be active.
4. Logout stores the `jti` in `revoked_tokens` until it would have expired anyway. Expired rows are purged lazily.
5. Password change, password reset, role change and deactivation increment `token_version`,
   which signs the user out everywhere at once.
6. After 5 failed logins the account is locked for 15 minutes (both configurable). Existing sessions keep working,
   so an attacker cannot lock someone out of an active session.

---

## 9. Production checklist

* `ENVIRONMENT=production`, a fresh random `JWT_SECRET_KEY`, strong database credentials kept in a secrets manager.
* Serve over HTTPS only; set `COOKIE_SECURE=true`. Keep the UI and API on the same site, or set `COOKIE_SAMESITE=none` and an exact `CORS_ORIGINS`.
* Never run `seed_demo` in production (the script refuses). Rotate the bootstrap admin password after first login.
* Run `alembic upgrade head` as a deployment step, before starting new app instances.
* Run several Uvicorn workers behind a reverse proxy, e.g. `uvicorn app.main:app --workers 4 --proxy-headers`.
* Schedule backups (`pg_dump`). Add rate limiting at the proxy for `/api/v1/auth/login`.
* Add centralised logging and monitoring, and purge `revoked_tokens` rows past `expires_at` periodically.

---

## 10. Troubleshooting

| Symptom | Fix |
|---|---|
| `ValidationError: JWT_SECRET_KEY` on start | `.env` missing or the secret is shorter than 32 characters |
| `psycopg.OperationalError: connection refused` | PostgreSQL isn't running, or `DATABASE_URL` has the wrong host or port |
| `password authentication failed for user "hrms"` | Fix the password in `DATABASE_URL`, or run `ALTER USER hrms WITH PASSWORD '...'` |
| `relation "users" does not exist` | Run `alembic upgrade head` |
| `Role ADMIN is not configured` | Migrations weren't applied to this database |
| Login works in Swagger but the UI shows "Cannot reach the server" | The backend isn't on `VITE_PROXY_TARGET`, or the Vite server needs a restart after editing `.env` |
| UI writes fail with `403 CSRF token missing or invalid` | Cookies were blocked or cleared. Sign in again and keep the UI and API on the same origin |
| `ACCOUNT_LOCKED` | Wait `LOGIN_LOCKOUT_MINUTES`, or have an admin reset the password |
| Tests fail with `permission denied for schema public` | The test DB must be owned by the `hrms` user (`CREATE DATABASE hrms_test OWNER hrms`) |

---

## 11. Extending with phases 5–8

1. Add `app/models/<module>.py` with FKs to `employees.id`, and import it in `app/models/__init__.py`.
2. `alembic revision --autogenerate -m "<module>"`, review the file, then `alembic upgrade head`.
3. Add `schemas/<module>.py`, `services/<module>_service.py`, `routers/<module>.py`.
4. Append the router to `API_ROUTERS` in `app/routers/__init__.py`. `main.py` doesn't change.
5. Reuse the dependencies: `OwnEmployee` for self-service, `HRorAdminUser` for approvals,
   and `reporting_manager_id` for manager approval chains.
6. Add the pages, then add their sidebar entries in `frontend/src/components/navigation.ts`.
