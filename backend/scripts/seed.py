"""Seed the database with the two office users.

Idempotent: running it twice changes nothing. Passwords come from the
environment so that no credential is ever committed — `.env.example` documents
both variables, and the script refuses to invent a default.

    python scripts/seed.py

Sample registry records and rules are seeded in a later phase, when the checks
that read them exist.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.db.app import app_session_scope  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.security import hash_password  # noqa: E402

SEED_USERS = (
    {
        "mobile_number": "9000000001",
        "full_name": "Demo Officer",
        "role": "officer",
        "password_env": "SUTRADHAR_SEED_OFFICER_PASSWORD",
    },
    {
        "mobile_number": "9000000002",
        "full_name": "Demo Section Head",
        "role": "dept_head",
        "password_env": "SUTRADHAR_SEED_DEPT_HEAD_PASSWORD",
    },
)


def main() -> int:
    missing = [u["password_env"] for u in SEED_USERS if not os.environ.get(u["password_env"])]
    if missing:
        print("Refusing to seed: these environment variables are not set:", file=sys.stderr)
        for name in missing:
            print(f"  {name}", file=sys.stderr)
        print(
            "\nSet them in .env (see .env.example). Generate values with:\n"
            "  python -c 'import secrets; print(secrets.token_urlsafe(16))'",
            file=sys.stderr,
        )
        return 1

    created, existing = 0, 0
    with app_session_scope() as session:
        for spec in SEED_USERS:
            found = session.scalar(
                select(User).where(User.mobile_number == spec["mobile_number"])
            )
            if found is not None:
                existing += 1
                print(f"  exists   {spec['role']:<10} {spec['mobile_number']}")
                continue
            session.add(
                User(
                    mobile_number=spec["mobile_number"],
                    full_name=spec["full_name"],
                    role=spec["role"],
                    password_hash=hash_password(os.environ[spec["password_env"]]),
                    is_active=True,
                )
            )
            created += 1
            print(f"  created  {spec['role']:<10} {spec['mobile_number']}")

    print(f"\nSeed complete: {created} created, {existing} already present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
