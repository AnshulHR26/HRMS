<h1 align="center">HRMS — Human Resource Management System</h1>

<p align="center">
  A secure, role-based HR platform for managing employees, departments and user accounts.<br>
  Built with <b>FastAPI</b>, <b>PostgreSQL</b> and <b>React + TypeScript</b>.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/React_18-TypeScript-3178C6?logo=react&logoColor=white" alt="React + TypeScript">
  <img src="https://img.shields.io/badge/Vite-646CFF?logo=vite&logoColor=white" alt="Vite">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License">
</p>

> 🚧 **Work in progress.** Phases 1–4 (authentication, roles, employees, organisation structure and dashboards) are done. Attendance, leave, payroll and more are planned for Phases 5–8.

---

## 📑 Contents

- [Features](#-features)
- [Tech stack](#️-tech-stack)
- [Project structure](#-project-structure)
- [Getting started](#-getting-started)
- [Environment variables](#-environment-variables)
- [Running the tests](#-running-the-tests)
- [Demo accounts](#-demo-accounts)
- [Roles and permissions](#-roles-and-permissions)
- [Authentication design](#-authentication-design)
- [API overview](#-api-overview)
- [Troubleshooting](#-troubleshooting)
- [Roadmap](#️-roadmap)
- [License](#-license)

---

## ✨ Features

- **Three roles — Admin, HR and Employee** — with every rule enforced on the backend, not just hidden in the UI
- **Employee management** — create, update and deactivate employees, with auto-generated IDs (`EMP-00001`, `EMP-00002`, …)
- **Directory** with search, filters, sorting and pagination
- **Departments and designations** — full CRUD, plus reassigning employees before a delete
- **Reporting lines** — each employee can have a reporting manager, with cycle detection
- **Self-service** — employees see their own dashboard and profile and can edit their phone and address
- **Role-based dashboards** — separate Admin, HR and Employee views
- **Secure login** — Argon2id password hashing, JWT in an httpOnly cookie, CSRF protection, account lockout after repeated failed logins, and sign-out-everywhere on password or role changes
- **Database migrations** with Alembic
- **Automated test suite** with pytest against a real PostgreSQL database

## 🛠️ Tech stack

| Layer | Technologies |
|---|---|
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic |
| Database | PostgreSQL 14+ (16 recommended) |
| Auth & security | JWT (HS256), Argon2id, httpOnly cookies, CSRF double-submit |
| Frontend | React 18, TypeScript, Vite, Axios |
| Testing | Pytest |

## 📁 Project structure

```
hrms/
├── backend/
│   ├── app/            # FastAPI app: models, schemas, services, routers, scripts
│   ├── alembic/        # Database migrations
│   ├── tests/          # Pytest suite
│   ├── alembic.ini
│   ├── pytest.ini
│   └── requirements.txt
├── frontend/
│   ├── src/            # React + TypeScript source
│   ├── public/
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── docs/
├── README.md
├── SETUP.md            # Detailed setup guide
└── LICENSE
```

## 🚀 Getting started

For the full step-by-step guide, see **[SETUP.md](SETUP.md)**.

### Prerequisites

| Tool | Version | Check |
|---|---|---|
| Python | 3.12 or newer | `python --version` |
| PostgreSQL | 14+ (16 recommended) | `psql --version` |
| Node.js / npm | 20 LTS+ / 10+ | `node --version` |

### 1. Clone the repository

```bash
git clone https://github.com/AnshulHR26/HRMS.git
cd HRMS
```

### 2. Create the database

Create one application user and two databases — one for the app and a disposable one for the tests:

```sql
CREATE USER hrms WITH PASSWORD 'choose-a-strong-password' CREATEDB;
CREATE DATABASE hrms OWNER hrms;
CREATE DATABASE hrms_test OWNER hrms;
```

> ⚠️ The test suite drops and recreates the `public` schema of `hrms_test` on every run. Never point `TEST_DATABASE_URL` at data you want to keep.

### 3. Backend

Create `backend/.env` with the values from [Environment variables](#-environment-variables), then:

**Windows (PowerShell)**

```powershell
cd backend
python -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass -Force
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

alembic upgrade head                 # tables, indexes, EMP-ID sequence, the 3 roles
python -m app.scripts.bootstrap_admin
python -m app.scripts.seed_demo      # optional, development only

uvicorn app.main:app --reload --port 8000
```

**macOS / Linux**

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

alembic upgrade head
python -m app.scripts.bootstrap_admin
python -m app.scripts.seed_demo      # optional, development only

uvicorn app.main:app --reload --port 8000
```

Once it's running:

| URL | What it is |
|---|---|
| http://localhost:8000/docs | Swagger UI — log in, click **Authorize**, paste the token |
| http://localhost:8000/redoc | API reference |
| http://localhost:8000/health | Liveness and database check |

### 4. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

Other scripts: `npm run typecheck` (TypeScript check) and `npm run build` (production bundle in `dist/`).

The Vite dev server proxies `/api` to the backend (`VITE_PROXY_TARGET` in `frontend/.env`, e.g. `http://localhost:8000`), so the browser treats the UI and the API as one origin and the login cookie stays first-party.

## 🔐 Environment variables

Set these in `backend/.env`. No secret is hardcoded in the code, and `.env` files are ignored by Git.

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | required | `postgresql+psycopg://hrms:<password>@localhost:5432/hrms` |
| `TEST_DATABASE_URL` | …/hrms_test | Disposable test database |
| `JWT_SECRET_KEY` | required | 32+ characters. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | Token and cookie lifetime |
| `ENVIRONMENT` | development | `development`, `test` or `production` |
| `CORS_ORIGINS` | http://localhost:5173 | Comma-separated list of exact origins |
| `COOKIE_SECURE` / `COOKIE_SAMESITE` | false / lax | Set `COOKIE_SECURE=true` behind HTTPS |
| `LOGIN_MAX_FAILED_ATTEMPTS` / `LOGIN_LOCKOUT_MINUTES` | 5 / 15 | Brute-force lockout |
| `BOOTSTRAP_ADMIN_USER_ID` / `BOOTSTRAP_ADMIN_PASSWORD` | admin / — | Initial admin (8+ characters, letters and digits) |
| `DEMO_USER_PASSWORD` | — | Password for every demo account |

## 🧪 Running the tests

From `backend/`, with the virtual environment active:

```bash
pytest                         # full suite, real PostgreSQL
pytest -v tests/test_auth.py   # one file
pytest -k deactivated          # tests matching a keyword
```

The test database is built by running the Alembic migrations, so the migrations are tested too.

| File | Covers |
|---|---|
| `test_auth.py` | Login, cookies and CSRF, logout revocation, lockout, password change, Argon2 |
| `test_authorization.py` | Role checks, privilege escalation and self-modification guards |
| `test_employees.py` | Employee CRUD, pagination, search, filters, sorting, manager cycles |
| `test_org_and_database.py` | Department and designation CRUD, reassign-then-delete, dashboards |

## 👥 Demo accounts

Created by `python -m app.scripts.seed_demo` (development only):

| User ID | Role | Person | Password |
|---|---|---|---|
| `admin` | ADMIN | System account | `BOOTSTRAP_ADMIN_PASSWORD` |
| `hr.manager` | HR | Priya Sharma | `DEMO_USER_PASSWORD` |
| `hr.exec` | HR | Rahul Verma | `DEMO_USER_PASSWORD` |
| `employee` | EMPLOYEE | Ananya Iyer | `DEMO_USER_PASSWORD` |
| `arjun.mehta` + 7 more | EMPLOYEE | Engineering, Finance, Sales, Ops | `DEMO_USER_PASSWORD` |

The seed creates 5 departments, 10 designations and 11 employees with reporting lines.

## 🛡️ Roles and permissions

| Capability | Admin | HR | Employee |
|---|:---:|:---:|:---:|
| Own dashboard and profile; edit own phone and address | ✅ | ✅ | ✅ |
| Employee directory, search, filter, view any profile | ✅ | ✅ | — |
| Create, update and deactivate employees | ✅ | ✅ (not Admin-linked) | — |
| Create EMPLOYEE accounts | ✅ | ✅ | — |
| Create HR or Admin accounts; assign roles | ✅ | — | — |
| Enable/disable accounts; reset passwords | ✅ | EMPLOYEE only | — |
| View departments and designations | ✅ | ✅ | own only |
| Manage, reassign and delete departments/designations | ✅ | — | — |
| Admin dashboard | ✅ | — | — |
| HR dashboard | ✅ | ✅ | — |

Nobody can change their own role or status, and the last active Admin can't be demoted.

## 🔑 Authentication design

1. Login checks the Argon2id password hash, issues a JWT and sets two cookies: `hrms_access_token` (httpOnly) and `hrms_csrf`.
2. The frontend sends the cookie automatically and echoes the CSRF value in an `X-CSRF-Token` header on every write. Swagger and API clients can use `Authorization: Bearer <token>` instead.
3. Every request checks the token signature, expiry, a revoked-token list, the user's token version and whether the account is still active.
4. Logout revokes the token. Password changes, resets, role changes and deactivation sign the user out on every device.
5. After 5 failed logins the account is locked for 15 minutes.

## 🌐 API overview

All endpoints are under `/api/v1`. Errors always have the same shape: `{"error": {"code", "message", "details"}}`.

| Endpoint | Access |
|---|---|
| `POST /auth/login` · `GET /auth/me` · `POST /auth/logout` · `POST /auth/change-password` | Public / signed in |
| `GET, POST /employees` · `GET, PUT /employees/{EMP-ID}` · `PATCH /employees/{EMP-ID}/status` | HR, Admin |
| `GET, PATCH /employees/me` · `GET /dashboard/me` | Any user with a profile |
| `GET, POST /users` · `PATCH /users/{id}` · `POST /users/{id}/reset-password` | Admin; HR limited to EMPLOYEE accounts |
| `PATCH /users/{id}/role` · `GET /dashboard/admin` | Admin |
| `GET /departments` · `GET /designations` · `GET /dashboard/hr` · `GET /roles` | HR, Admin |
| `POST, PUT, DELETE` departments and designations · `…/reassign-employees` | Admin |

## 🧰 Troubleshooting

| Problem | Fix |
|---|---|
| Validation error on `JWT_SECRET_KEY` at start | `backend/.env` is missing, or the secret is shorter than 32 characters |
| `connection refused` | PostgreSQL isn't running, or the host/port in `DATABASE_URL` is wrong |
| `relation "users" does not exist` | Run `alembic upgrade head` |
| UI shows "Cannot reach the server" | The backend isn't running on `VITE_PROXY_TARGET`. Start uvicorn, and restart Vite after editing `.env` |
| `403 CSRF token missing or invalid` | Cookies were blocked or cleared. Sign in again |
| `ACCOUNT_LOCKED` | Wait for the lockout window, or have an admin reset the password |
| Tests: `permission denied for schema public` | `hrms_test` must be owned by the `hrms` user |

## 🗺️ Roadmap

- [x] **Phase 1–4** — Authentication, roles and permissions, employee management, departments and designations, dashboards
- [ ] **Phase 5–8** — Attendance, leave management with manager approvals, payroll, and more HR modules

## 📄 License

This project is licensed under the [MIT License](LICENSE).

## 👤 Author

**Anshul** — Python Developer · FastAPI & Data

[![GitHub](https://img.shields.io/badge/GitHub-AnshulHR26-181717?logo=github)](https://github.com/AnshulHR26)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Anshul-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/anshul-953281210/)
