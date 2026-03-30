import asyncio
import os
import random
import sys
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.models.country import Country

SAFETY_LEVELS = ("safe", "unsafe", "dangerous")
COST_LEVELS = ("low", "medium", "high")
COST_BY_LEVEL = {
    "low": (30, 80),
    "medium": (80, 180),
    "high": (180, 400),
}


async def seed_safety_cost() -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    safety_stats: Counter[str] = Counter()
    cost_stats: Counter[str] = Counter()
    updated_total = 0
    now = datetime.now(timezone.utc)

    async with async_session() as session:
        result = await session.execute(select(Country))
        countries = result.scalars().all()

        for country in countries:
            safety_level = random.choice(SAFETY_LEVELS)
            cost_level = random.choice(COST_LEVELS)
            cost_min, cost_max = COST_BY_LEVEL[cost_level]

            country.safety_level = safety_level
            country.cost_level = cost_level
            country.cost_per_day_usd = random.randint(cost_min, cost_max)
            country.safety_updated_at = now
            country.cost_updated_at = now

            safety_stats[safety_level] += 1
            cost_stats[cost_level] += 1
            updated_total += 1

        await session.commit()

    await engine.dispose()

    print(
        f"Обновлено {updated_total} стран: "
        f"безопасность {dict(safety_stats)}, "
        f"стоимость {dict(cost_stats)}"
    )


if __name__ == "__main__":
    asyncio.run(seed_safety_cost())
