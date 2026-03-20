import asyncio
import sys
import os
import logging
import warnings
from collections import defaultdict
from urllib.parse import urlparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

warnings.filterwarnings("ignore", message=".*Unverified HTTPS.*")

import httpx
from xml.etree import ElementTree as ET

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.config import settings
from app.models.country import Country
from app.models.source_discovery_log import SourceDiscoveryLog
from app.models.rss_source import RssSource

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

SEARCH_MODE_DISCOVERY = "{country} президент парламент министр бюджет правительство"
SEARCH_MODE_VISA = "({country} OR РФ) (режим OR правила OR порядок) (въезд OR выезд OR граница OR виза) (изменение OR отмена OR возобновление)"

ISO639_EXCEPTIONS = {
    "zho": "zh", "jpn": "ja", "kor": "ko", "heb": "he",
    "ara": "ar", "hin": "hi", "ben": "bn", "vie": "vi",
    "tha": "th", "msa": "ms", "fas": "fa", "kat": "ka",
    "hye": "hy", "aze": "az", "kaz": "kk", "uzb": "uz",
    "mon": "mn", "ind": "id", "nld": "nl", "ces": "cs",
    "ron": "ro", "hun": "hu", "ukr": "uk", "srp": "sr",
    "hrv": "hr", "bul": "bg", "slk": "sk", "slv": "sl",
    "est": "et", "lav": "lv", "lit": "lt", "isl": "is",
    "mlt": "mt", "sqi": "sq", "mkd": "mk", "bos": "bs",
    "cat": "ca", "eus": "eu", "glg": "gl", "cym": "cy",
    "gle": "ga", "swa": "sw", "amh": "am", "hau": "ha",
    "som": "so", "nep": "ne", "sin": "si", "khm": "km",
    "lao": "lo", "mya": "my", "urd": "ur", "tgl": "tl",
}


def iso639_3_to_1(code: str) -> str:
    return ISO639_EXCEPTIONS.get(code, code[:2])


def extract_domain(url: str) -> str | None:
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain if domain else None
    except Exception:
        return None


def build_query_url(
    country: Country,
    mode: str = SEARCH_MODE_DISCOVERY,
) -> str:
    """
    Строит URL для Google News RSS.
    Использует название страны на родном языке если доступно.
    """
    country_name = country.name_en

    if country.name_translations and country.primary_language:
        native_name = country.name_translations.get(country.primary_language)
        if native_name:
            country_name = native_name

    query = mode.format(country=country_name)
    encoded = query.replace(" ", "+")
    hl = iso639_3_to_1(country.primary_language or "eng")
    gl = country.iso2.upper()

    logger.info(f"  Название страны для запроса: {country_name}")
    logger.info(f"  Запрос: {query}")

    return (
        f"https://news.google.com/rss/search"
        f"?q={encoded}&hl={hl}&gl={gl}&ceid={gl}:{hl}"
    )


async def fetch_urls(url: str, client: httpx.AsyncClient) -> list[str]:
    """
    Скачивает Google News RSS и возвращает список URL источников.
    Реальный URL источника находится в теге <source url="...">.
    """
    try:
        response = await client.get(url, timeout=15)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        urls = []
        for item in root.findall(".//item"):
            source_el = item.find("source")
            if source_el is not None:
                source_url = source_el.get("url", "").strip()
                if source_url:
                    urls.append(source_url)
        return urls
    except Exception as e:
        logger.warning(f"Ошибка: {e}")
        return []


async def discover_for_country(
    country: Country,
    session: AsyncSession,
    client: httpx.AsyncClient,
    top_n: int = 5,
    mode: str = "discovery",
) -> dict:
    """
    Находит топ локальных доменов для страны.
    Локальность определяется по ccTLD страны.
    Показывает статус каждого домена: уже в базе или новый.
    Скрипт только показывает — не добавляет и не удаляет.
    """
    if not country.country_tld:
        logger.warning(f"[{country.iso2}] Нет ccTLD — пропускаем")
        return {"status": "no_tld"}

    # Загружаем домены которые уже есть в rss_sources
    existing_result = await session.execute(select(RssSource.url))
    existing_domains = set()
    for (url,) in existing_result.all():
        domain = extract_domain(url)
        if domain:
            existing_domains.add(domain)

    search_template = (
        SEARCH_MODE_DISCOVERY if mode == "discovery"
        else SEARCH_MODE_VISA
    )
    query_url = build_query_url(country, search_template)

    logger.info(
        f"\n[{country.iso2}] {country.name_en} "
        f"(TLD: {country.country_tld}, lang: {country.primary_language})"
    )

    urls = await fetch_urls(query_url, client)

    if not urls:
        logger.warning(f"[{country.iso2}] Нет результатов")
        log = SourceDiscoveryLog(
            country_id=country.id,
            query_used=query_url,
            total_results=0,
            domains_found=None,
            top_domains=None,
            status="no_results",
        )
        session.add(log)
        return {"status": "no_results"}

    # Считаем только домены с ccTLD страны
    local_counts: dict[str, int] = defaultdict(int)
    all_counts: dict[str, int] = defaultdict(int)

    for url in urls:
        domain = extract_domain(url)
        if not domain:
            continue
        all_counts[domain] += 1
        if domain.endswith(country.country_tld):
            local_counts[domain] += 1

    logger.info(
        f"[{country.iso2}] Получено URL: {len(urls)}, "
        f"локальных доменов (TLD={country.country_tld}): {len(local_counts)}"
    )

    # Если локальных нет — показываем топ всех доменов для справки
    if not local_counts:
        logger.info(f"[{country.iso2}] Локальных доменов не найдено")
        logger.info(f"[{country.iso2}] Топ всех доменов (без фильтра TLD):")
        top_all = sorted(all_counts.items(), key=lambda x: -x[1])[:top_n]
        for domain, count in top_all:
            status = "в базе" if domain in existing_domains else "новый"
            logger.info(
                f"  [{status}] {domain:<40} {count:>3} упоминаний"
            )

        log = SourceDiscoveryLog(
            country_id=country.id,
            query_used=query_url,
            total_results=len(urls),
            domains_found={d: c for d, c in top_all},
            top_domains=None,
            status="no_local_domains",
        )
        session.add(log)
        return {"status": "no_local_domains", "total": len(urls)}

    # Топ локальных доменов
    top = sorted(local_counts.items(), key=lambda x: -x[1])[:top_n]

    logger.info(f"[{country.iso2}] Топ-{top_n} локальных источников:")

    top_with_status = {}
    new_count = 0
    for domain, count in top:
        in_db = domain in existing_domains
        status = "в базе" if in_db else "НОВЫЙ"
        marker = "✓" if in_db else "★"
        top_with_status[domain] = {
            "count": count,
            "status": status,
            "in_db": in_db,
        }
        logger.info(
            f"  {marker} {domain:<40} {count:>3} упоминаний  [{status}]"
        )
        if not in_db:
            new_count += 1

    if new_count:
        logger.info(
            f"[{country.iso2}] Новых источников для рассмотрения: {new_count}"
        )

    # Сохраняем в БД
    log = SourceDiscoveryLog(
        country_id=country.id,
        query_used=query_url,
        total_results=len(urls),
        domains_found={
            d: c for d, c in
            sorted(local_counts.items(), key=lambda x: -x[1])[:20]
        },
        top_domains=top_with_status,
        status="done",
    )
    session.add(log)

    return {
        "status": "done",
        "total": len(urls),
        "local_domains": len(local_counts),
        "new_sources": new_count,
    }


async def run_discovery(
    iso2_list: list[str] | None = None,
    delay_seconds: int = 10,
    top_n: int = 5,
    mode: str = "discovery",
):
    """
    Основная функция обнаружения источников.

    iso2_list     — список стран. None = все активные.
    delay_seconds — пауза между запросами (защита от бана).
    top_n         — сколько топ доменов показывать и сохранять.
    mode          — discovery (общие новости) или visa (визовая тематика).
    """
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        query = select(Country).where(Country.is_active == True)
        if iso2_list:
            query = query.where(
                Country.iso2.in_([iso2.upper() for iso2 in iso2_list])
            )
        else:
            query = query.order_by(Country.name_en)

        result = await session.execute(query)
        countries = result.scalars().all()

        logger.info(f"Стран для обработки: {len(countries)}")
        logger.info(f"Пауза между запросами: {delay_seconds}с")
        logger.info(f"Топ доменов на страну: {top_n}")
        logger.info(f"Режим поиска: {mode}")

        async with httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0 (compatible; VisaMapBot/1.0)"},
            follow_redirects=True,
            verify=False,
        ) as client:

            success = 0
            no_tld = 0
            no_results = 0
            total_new = 0

            for i, country in enumerate(countries):
                if i > 0:
                    logger.info(f"Пауза {delay_seconds}с...")
                    await asyncio.sleep(delay_seconds)

                try:
                    res = await discover_for_country(
                        country, session, client, top_n, mode
                    )
                    if res["status"] == "done":
                        success += 1
                        total_new += res.get("new_sources", 0)
                    elif res["status"] == "no_tld":
                        no_tld += 1
                    else:
                        no_results += 1
                except Exception as e:
                    logger.error(f"[{country.iso2}] Ошибка: {e}")
                    no_results += 1

                await session.commit()

                logger.info(
                    f"Прогресс: {i+1}/{len(countries)} "
                    f"(успешно: {success}, нет TLD: {no_tld}, "
                    f"нет результатов: {no_results})"
                )

    logger.info(f"\n{'='*55}")
    logger.info(f"ИТОГО:")
    logger.info(f"  Успешно обработано:    {success}")
    logger.info(f"  Нет ccTLD:             {no_tld}")
    logger.info(f"  Нет результатов:       {no_results}")
    logger.info(f"  Новых источников (★):  {total_new}")
    logger.info(f"\nРезультаты сохранены в таблицу source_discovery_log")
    logger.info(f"Источники помеченные ★ можно добавить в rss_sources вручную")

    await engine.dispose()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Обнаружение локальных новостных источников для стран"
    )
    parser.add_argument(
        "--countries", nargs="+",
        help="Список iso2 кодов (по умолчанию все активные страны)",
        default=None,
    )
    parser.add_argument(
        "--delay", type=int, default=10,
        help="Пауза между запросами в секундах (default: 10)",
    )
    parser.add_argument(
        "--top", type=int, default=5,
        help="Топ N доменов на страну (default: 5)",
    )
    parser.add_argument(
        "--mode",
        choices=["discovery", "visa"],
        default="discovery",
        help="Режим: discovery (общие новости) или visa (визовая тематика)",
    )
    args = parser.parse_args()

    asyncio.run(run_discovery(
        iso2_list=args.countries,
        delay_seconds=args.delay,
        top_n=args.top,
        mode=args.mode,
    ))