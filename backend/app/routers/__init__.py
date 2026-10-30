"""Router registry. Future modules (attendance, leave, payroll, performance) are appended here
so ``main.py`` never needs to change when a phase is added."""

from fastapi import APIRouter

from app.routers import auth, dashboard, departments, designations, employees, roles, users

API_ROUTERS: list[APIRouter] = [
    auth.router,
    users.router,
    roles.router,
    employees.router,
    departments.router,
    designations.router,
    dashboard.router,
]
