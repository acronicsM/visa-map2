import asyncio
import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.services.flights.import_openflights import import_openflights_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        stats = await import_openflights_data(session)
        logger.info(
            "Import complete: airports=%s routes=%s hubs=%s",
            stats["airports_upserted"],
            stats["routes_upserted"],
            stats["hub_airports_upserted"],
        )


if __name__ == "__main__":
    asyncio.run(main())
