"""Manual migrations, with safe error messages; never invoked on web startup."""
import logging
from alembic.config import Config
from alembic import command
from app.core.security import install_log_redaction


def main():
    install_log_redaction()
    try:
        command.upgrade(Config("alembic.ini"), "head")
    except Exception as exc:
        logging.getLogger(__name__).error("Migration failed (%s); check connection and revision", type(exc).__name__)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
