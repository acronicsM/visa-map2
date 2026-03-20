import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.config import settings
from app.models.rss_source import RssSource

# Обновляем старые записи которые были добавлены без новых полей
UPDATES = [
    {
        "url": "https://tass.ru/rss/v2.xml",
        "source_type": "news_agency",
        "requires_filter": True,
        "fetch_frequency": "hourly",
        "keywords": ["виза", "визовый", "безвизовый", "въезд", "загранпаспорт", "консульство", "посольство", "визовый режим"],
    },
    {
        "url": "https://www.mid.ru/ru/rss/",
        "source_type": "official",
        "requires_filter": False,
        "fetch_frequency": "daily",
        "keywords": None,
    },
    {
        "url": "https://feeds.reuters.com/reuters/worldNews",
        "source_type": "news_agency",
        "requires_filter": True,
        "fetch_frequency": "daily",
        "keywords": ["visa", "visa-free", "travel ban", "entry ban", "immigration", "passport", "border"],
    },
    {
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "source_type": "news_agency",
        "requires_filter": True,
        "fetch_frequency": "daily",
        "keywords": ["visa", "visa-free", "travel ban", "entry ban", "immigration", "passport"],
    },
    {
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
        "source_type": "news_agency",
        "requires_filter": True,
        "fetch_frequency": "daily",
        "keywords": ["visa", "visa-free", "travel ban", "entry ban", "immigration", "passport"],
    },
    {
        "url": "https://www.interfax.ru/rss.asp",
        "source_type": "news_agency",
        "requires_filter": True,
        "fetch_frequency": "daily",
        "keywords": ["виза", "визовый", "безвизовый", "въезд", "консульство", "посольство"],
    },
    {
        "url": "https://www.ukrinform.ru/rss/block-world",
        "source_type": "news_agency",
        "requires_filter": True,
        "fetch_frequency": "daily",
        "keywords": ["виза", "візовий", "безвізовий", "в'їзд", "консульство", "посольство"],
    },
    {
        "url": "https://www.inform.kz/rss/",
        "source_type": "news_agency",
        "requires_filter": True,
        "fetch_frequency": "daily",
        "keywords": ["виза", "визовый", "безвизовый", "въезд", "консульство"],
    },
    {
        "url": "https://rss.dw.com/rdf/rss-ru-all",
        "source_type": "news_agency",
        "requires_filter": True,
        "fetch_frequency": "daily",
        "keywords": ["виза", "визовый", "безвизовый", "въезд", "консульство", "посольство"],
    },
    {
        "url": "https://feeds.euronews.com/news/ru",
        "source_type": "news_agency",
        "requires_filter": True,
        "fetch_frequency": "daily",
        "keywords": ["виза", "визовый", "безвизовый", "въезд", "консульство", "посольство"],
    },
    {
        "url": "https://ria.ru/export/rss2/world/index.xml",
        "source_type": "news_agency",
        "requires_filter": True,
        "fetch_frequency": "hourly",
        "keywords": ["виза", "визовый", "безвизовый", "въезд", "загранпаспорт", "консульство", "посольство", "визовый режим"],
    },
]


async def fix():
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        updated = 0
        not_found = 0

        for data in UPDATES:
            result = await session.execute(
                select(RssSource).where(RssSource.url == data["url"])
            )
            source = result.scalar_one_or_none()

            if not source:
                print(f"  Не найден: {data['url']}")
                not_found += 1
                continue

            source.source_type = data["source_type"]
            source.requires_filter = data["requires_filter"]
            source.fetch_frequency = data["fetch_frequency"]
            source.keywords = data["keywords"]
            updated += 1
            print(f"  Обновлён: {source.name}")

        await session.commit()
        print(f"\nГотово! Обновлено: {updated}, не найдено: {not_found}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(fix())