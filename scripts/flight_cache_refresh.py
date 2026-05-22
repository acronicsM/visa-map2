import asyncio
import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.cache import close_redis
from app.services.flight_service import list_cities_for_refresh, refresh_direct_countries

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            city_keys = await list_cities_for_refresh(session)
            if not city_keys:
                logger.info("No flight caches require refresh")
                return

            logger.info("Refreshing %s city caches", len(city_keys))
            success = 0
            failed = 0
            for city_key in city_keys:
                result = await refresh_direct_countries(session, city_key)
                if result is None:
                    failed += 1
                    logger.warning("Refresh failed for %s", city_key)
                else:
                    success += 1
                    logger.info(
                        "Refreshed %s (%s), expires %s",
                        city_key,
                        result.source,
                        result.expires_at.isoformat(),
                    )

            logger.info("Refresh complete: success=%s failed=%s", success, failed)
    finally:
        await close_redis()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
