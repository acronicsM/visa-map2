import logging
import sys


def setup_logging() -> None:
    log_format = "%(asctime)s %(levelname)-8s %(name)s — %(message)s"
    date_format = "%H:%M:%S"

    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Убираем лишний шум от SQLAlchemy в продакшне
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)