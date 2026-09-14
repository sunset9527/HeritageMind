"""Create or promote an administrator with explicitly supplied environment variables.

Run in the API container:
docker compose --profile production exec -T -e HM_ADMIN_USERNAME=operator -e HM_ADMIN_EMAIL=operator@example.com -e HM_ADMIN_PASSWORD='a-strong-password' api python -m src.bootstrap_admin
"""

import os

from src.database import SessionLocal, init_db
from src.services.admin_bootstrap import bootstrap_admin


def main() -> None:
    init_db()
    with SessionLocal() as db:
        result = bootstrap_admin(
            db,
            username=os.getenv("HM_ADMIN_USERNAME", ""),
            email=os.getenv("HM_ADMIN_EMAIL", ""),
            password=os.getenv("HM_ADMIN_PASSWORD", ""),
        )
    print(f"Administrator {'created' if result.created else 'verified'}: {result.user.username}")


if __name__ == "__main__":
    main()
