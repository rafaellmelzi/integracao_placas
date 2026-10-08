"""Container entrypoint: one worker, dynamic port, no migrations or demo seeds."""
import os
import logging
import uvicorn
from app.core.security import install_log_redaction


def main():
    install_log_redaction()
    try:
        port = int(os.getenv("PORT", "8000"))
        if not 1 <= port <= 65535:
            raise ValueError("Invalid listening port")
        uvicorn.run("app.main:app", host="0.0.0.0", port=port, workers=1, access_log=False)
    except Exception as exc:
        logging.getLogger(__name__).error("Application startup failed (%s)", type(exc).__name__)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
