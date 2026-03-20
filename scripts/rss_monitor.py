import asyncio
import sys
import os
import logging
import warnings
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

warnings.filterwarnings("ignore", message=".*Unverified HTTPS.*")

import httpx

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.config import settings
from app.models.rss_source import RssSource
from app.models.news_trigger import NewsTrigger
from app.models.country import Country

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def load_config(session: AsyncSession) -> tuple[list, dict]:
    """
    Загружает из БД:
    - активные RSS источники
    - словарь названий стран → iso2
    """
    sources_result = await session.execute(
        select(RssSource)
        .where(RssSource.is_active == True)
        .order_by(RssSource.priority)
    )
    sources = sources_result.scalars().all()

    countries_result = await session.execute(
        select(Country.iso2, Country.name_ru, Country.name_en, Country.name_native)
        .where(Country.is_active == True)
    )

    country_names = {}
    for iso2, name_ru, name_en, name_native in countries_result.all():
        if name_ru:
            country_names[name_ru.lower()] = iso2
        if name_en:
            country_names[name_en.lower()] = iso2
        if name_native and name_native != name_en:
            country_names[name_native.lower()] = iso2

    return sources, country_names


def is_relevant(
    title: str,
    description: str,
    keywords: list[str],
) -> bool:
    """Фильтрует новость по ключевым словам источника"""
    text = f"{title} {description}".lower()
    return any(kw.lower() in text for kw in keywords)


def extract_countries(
    title: str,
    description: str,
    country_names: dict,
) -> list[str]:
    """Извлекает iso2 коды стран из текста"""
    text = f"{title} {description}".lower()
    found = set()
    for name, iso2 in country_names.items():
        if len(name) < 4:
            continue
        if name in text:
            found.add(iso2)
    return sorted(found)


async def fetch_rss(url: str, client: httpx.AsyncClient) -> list[dict]:
    """Скачивает и парсит RSS ленту"""
    try:
        response = await client.get(url, timeout=15)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        items = []

        for item in root.findall(".//item"):
            title_el = item.find("title")
            desc_el = item.find("description")
            link_el = item.find("link")

            title = title_el.text if title_el is not None else ""
            description = desc_el.text if desc_el is not None else ""
            link = link_el.text if link_el is not None else ""

            if title and title.strip():
                items.append({
                    "title": title.strip(),
                    "description": (description or "").strip()[:500],
                    "link": link.strip(),
                })

        return items

    except ET.ParseError as e:
        logger.warning(f"Ошибка парсинга XML {url}: {e}")
        return []
    except Exception as e:
        logger.warning(f"Ошибка при получении {url}: {e}")
        return []


async def is_duplicate(session: AsyncSession, source_url: str) -> bool:
    """Проверяет не создавали ли мы уже триггер для этой ссылки"""
    if not source_url:
        return False
    result = await session.execute(
        select(NewsTrigger).where(NewsTrigger.source_url == source_url)
    )
    return result.scalar_one_or_none() is not None


async def run_monitor(dry_run: bool = False):
    logger.info("Запускаем RSS мониторинг...")
    logger.info(f"Режим: {'dry_run (без записи)' if dry_run else 'запись в БД'}")

    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        sources, country_names = await load_config(session)

        logger.info(f"Активных источников: {len(sources)}")
        logger.info(f"Названий стран:      {len(country_names)}")

        total_fetched = 0
        total_relevant = 0
        total_created = 0
        total_duplicates = 0
        total_no_keywords = 0

        async with httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0 (compatible; VisaMapBot/1.0)"},
            follow_redirects=True,
            verify=False,
        ) as client:

            for source in sources:
                logger.info(f"\nЧитаем [{source.source_type}]: {source.name}")
                items = await fetch_rss(source.url, client)
                total_fetched += len(items)

                if not items:
                    continue

                logger.info(f"  Получено: {len(items)} новостей")

                # Получаем ключевые слова источника
                source_keywords = source.keywords or []

                relevant_count = 0
                for item in items:

                    # Для агрегаторов и official — всё релевантно
                    if not source.requires_filter:
                        pass
                    else:
                        # Для news_agency — фильтруем по keywords источника
                        if not source_keywords:
                            total_no_keywords += 1
                            continue
                        if not is_relevant(
                            item["title"],
                            item["description"],
                            source_keywords,
                        ):
                            continue

                    total_relevant += 1
                    relevant_count += 1

                    countries = extract_countries(
                        item["title"],
                        item["description"],
                        country_names,
                    )

                    logger.info(f"  + {item['title'][:80]}")
                    if countries:
                        logger.info(f"    Страны: {countries}")

                    if dry_run:
                        continue

                    if await is_duplicate(session, item["link"]):
                        total_duplicates += 1
                        continue

                    trigger = NewsTrigger(
                        headline=item["title"],
                        source_name=source.name,
                        source_url=item["link"] or None,
                        status="new",
                        affected_countries=countries if countries else None,
                        notes=f"Авто-импорт из RSS. {item['description'][:200]}"
                        if item["description"] else "Авто-импорт из RSS",
                        detected_at=datetime.now(timezone.utc),
                    )
                    session.add(trigger)
                    total_created += 1

                if not dry_run:
                    source.last_fetched_at = datetime.now(timezone.utc)

                logger.info(f"  Релевантных: {relevant_count}")

        if not dry_run:
            await session.commit()

    logger.info(f"\n{'='*50}")
    logger.info(f"ИТОГО:")
    logger.info(f"  Новостей получено:        {total_fetched}")
    logger.info(f"  Релевантных:              {total_relevant}")
    logger.info(f"  Пропущено (нет keywords): {total_no_keywords}")
    if not dry_run:
        logger.info(f"  Триггеров создано:        {total_created}")
        logger.info(f"  Дубликатов:               {total_duplicates}")

    await engine.dispose()


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    asyncio.run(run_monitor(dry_run=dry_run))