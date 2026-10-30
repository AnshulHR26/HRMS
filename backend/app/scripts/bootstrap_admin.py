"""Create the initial ADMIN account from environment variables (idempotent).

Usage::

    BOOTSTRAP_ADMIN_PASSWORD='...' python -m app.scripts.bootstrap_admin
    python -m app.scripts.bootstrap_admin --reset-password   # rotate the password
"""

import argparse
import sys

from app.core.config import settings
from app.core.roles import RoleName
from app.core.security import hash_password, validate_password_strength
from app.database.session import SessionLocal
from app.models import User
from app.services.auth_service import get_user_by_login, normalise_user_id
from app.services.user_service import get_role


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset-password", action="store_true", help="overwrite the existing password")
    args = parser.parse_args()

    password = settings.BOOTSTRAP_ADMIN_PASSWORD
    if not password:
        print("ERROR: set BOOTSTRAP_ADMIN_PASSWORD (env var or backend/.env)", file=sys.stderr)
        return 1
    try:
        validate_password_strength(password)
    except ValueError as exc:
        print(f"ERROR: BOOTSTRAP_ADMIN_PASSWORD rejected: {exc}", file=sys.stderr)
        return 1

    login = normalise_user_id(settings.BOOTSTRAP_ADMIN_USER_ID)
    with SessionLocal() as db:
        existing = get_user_by_login(db, login)
        if existing is not None:
            if args.reset_password:
                existing.password_hash = hash_password(password)
                existing.token_version += 1
                existing.is_active = True
                db.commit()
                print(f"Admin '{login}': password reset.")
            else:
                print(f"Admin '{login}' already exists — nothing to do.")
            return 0

        db.add(
            User(
                user_id=login,
                password_hash=hash_password(password),
                role=get_role(db, RoleName.ADMIN),
                is_active=True,
            )
        )
        db.commit()
        print(f"Admin '{login}' created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
