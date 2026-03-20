import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.config import settings
from app.models.rss_source import RssSource
from app.models.rss_keyword import RssKeyword
from app.models.country import Country

RSS_SOURCES = [
    # Россия — news_agency
    {
        "name": "Лента.ру",
        "url": "https://lenta.ru/rss",
        "lang": "ru",
        "source_type": "news_agency",
        "priority": 1,
        "requires_filter": True,
        "fetch_frequency": "hourly",
        "country_iso2": "RU",
        "keywords": ["виза", "визовый", "безвизовый", "въезд", "загранпаспорт", "консульство", "посольство", "визовый режим", "запрет въезда"],
    },
    {
        "name": "ТАСС",
        "url": "https://tass.ru/rss/v2.xml",
        "lang": "ru",
        "source_type": "news_agency",
        "priority": 1,
        "requires_filter": True,
        "fetch_frequency": "hourly",
        "country_iso2": "RU",
        "keywords": ["виза", "визовый", "безвизовый", "въезд", "загранпаспорт", "консульство", "посольство", "визовый режим", "запрет въезда"],
    },
    {
        "name": "РБК",
        "url": "https://rssexport.rbc.ru/rbcnews/news/30/full.rss",
        "lang": "ru",
        "source_type": "news_agency",
        "priority": 1,
        "requires_filter": True,
        "fetch_frequency": "hourly",
        "country_iso2": "RU",
        "keywords": ["виза", "визовый", "безвизовый", "въезд", "консульство", "визовый режим"],
    },
    {
        "name": "RT",
        "url": "https://www.rt.com/rss/",
        "lang": "en",
        "source_type": "news_agency",
        "priority": 2,
        "requires_filter": True,
        "fetch_frequency": "daily",
        "country_iso2": "RU",
        "keywords": ["visa", "visa-free", "travel ban", "entry ban", "immigration", "passport"],
    },
    {
        "name": "Ведомости",
        "url": "https://www.vedomosti.ru/rss/news.xml",
        "lang": "ru",
        "source_type": "news_agency",
        "priority": 2,
        "requires_filter": True,
        "fetch_frequency": "daily",
        "country_iso2": "RU",
        "keywords": ["виза", "визовый", "безвизовый", "въезд", "консульство"],
    },
    # Германия — news_agency
    {
        "name": "Die Zeit",
        "url": "http://newsfeed.zeit.de/index",
        "lang": "de",
        "source_type": "news_agency",
        "priority": 1,
        "requires_filter": True,
        "fetch_frequency": "daily",
        "country_iso2": "DE",
        "keywords": ["visum", "visumfrei", "einreise", "reisebeschränkung", "einreiseverbot", "reisewarnung", "grenzschließung"],
    },
    {
        "name": "Spiegel International",
        "url": "https://www.spiegel.de/international/index.rss",
        "lang": "en",
        "source_type": "news_agency",
        "priority": 1,
        "requires_filter": True,
        "fetch_frequency": "daily",
        "country_iso2": "DE",
        "keywords": ["visa", "visa-free", "travel ban", "entry ban", "immigration", "border closure"],
    },
    {
        "name": "Deutschland.de",
        "url": "https://www.deutschland.de/de/feed-news/rss.xml",
        "lang": "de",
        "source_type": "official",
        "priority": 1,
        "requires_filter": False,
        "fetch_frequency": "daily",
        "country_iso2": "DE",
        "keywords": None,
    },
    # США — news_agency
    {
        "name": "New York Times",
        "url": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        "lang": "en",
        "source_type": "news_agency",
        "priority": 1,
        "requires_filter": True,
        "fetch_frequency": "daily",
        "country_iso2": "US",
        "keywords": ["visa", "visa-free", "travel ban", "entry ban", "immigration", "passport", "border"],
    },
    {
        "name": "Washington Times",
        "url": "https://www.washingtontimes.com/rss/headlines/news/",
        "lang": "en",
        "source_type": "news_agency",
        "priority": 2,
        "requires_filter": True,
        "fetch_frequency": "daily",
        "country_iso2": "US",
        "keywords": ["visa", "visa-free", "travel ban", "immigration", "passport"],
    },
    # Турция — news_agency
    {
        "name": "Haberler",
        "url": "https://rss.haberler.com/rssnew.aspx",
        "lang": "tr",
        "source_type": "news_agency",
        "priority": 1,
        "requires_filter": True,
        "fetch_frequency": "daily",
        "country_iso2": "TR",
        "keywords": ["vize", "vizesiz", "pasaport", "giriş yasağı", "seyahat yasağı", "sınır"],
    },
    {
        "name": "CNN Türk",
        "url": "https://www.cnnturk.com/feed/rss/turkiye/news",
        "lang": "tr",
        "source_type": "news_agency",
        "priority": 1,
        "requires_filter": True,
        "fetch_frequency": "daily",
        "country_iso2": "TR",
        "keywords": ["vize", "vizesiz", "pasaport", "giriş yasağı", "seyahat"],
    },
    # ОАЭ — news_agency
    {
        "name": "Emarat Al Youm",
        "url": "https://www.emaratalyoum.com/1.533091?ot=ot.AjaxPageLayout",
        "lang": "ar",
        "source_type": "news_agency",
        "priority": 1,
        "requires_filter": True,
        "fetch_frequency": "daily",
        "country_iso2": "AE",
        "keywords": ["تأشيرة", "دخول", "جواز سفر", "حظر السفر", "تأشيرة مجانية"],
    },
    # Беларусь — news_agency
    {
        "name": "БелТА",
        "url": "https://belta.by/rss/",
        "lang": "ru",
        "source_type": "news_agency",
        "priority": 1,
        "requires_filter": True,
        "fetch_frequency": "daily",
        "country_iso2": "BY",
        "keywords": ["виза", "визовый", "безвизовый", "въезд", "консульство", "посольство"],
    },
    # Глобальные агрегаторы — aggregator
    {
        "name": "Google News — визы RU",
        "url": "https://news.google.com/rss/search?q=визовый+режим&hl=ru&gl=RU&ceid=RU:ru",
        "lang": "ru",
        "source_type": "aggregator",
        "priority": 1,
        "requires_filter": False,
        "fetch_frequency": "daily",
        "country_iso2": None,
        "keywords": None,
    },
    {
        "name": "Google News — visa EN",
        "url": "https://news.google.com/rss/search?q=visa+free+travel+ban&hl=en&gl=US&ceid=US:en",
        "lang": "en",
        "source_type": "aggregator",
        "priority": 1,
        "requires_filter": False,
        "fetch_frequency": "daily",
        "country_iso2": None,
        "keywords": None,
    },
    {
        "name": "Google News — vize TR",
        "url": "https://news.google.com/rss/search?q=vize+pasaport&hl=tr&gl=TR&ceid=TR:tr",
        "lang": "tr",
        "source_type": "aggregator",
        "priority": 2,
        "requires_filter": False,
        "fetch_frequency": "daily",
        "country_iso2": None,
        "keywords": None,
    },
    {
        "name": "Bing News — visa",
        "url": "https://www.bing.com/news/search?format=RSS&q=visa+free+travel+ban",
        "lang": "en",
        "source_type": "aggregator",
        "priority": 2,
        "requires_filter": False,
        "fetch_frequency": "daily",
        "country_iso2": None,
        "keywords": None,
    },
    {
        "name": "GDELT — visa",
        "url": "https://api.gdeltproject.org/api/v2/doc/doc?query=visa%20travel%20ban&mode=artlist&format=rss&maxrecords=25",
        "lang": "en",
        "source_type": "aggregator",
        "priority": 3,
        "requires_filter": False,
        "fetch_frequency": "daily",
        "country_iso2": None,
        "keywords": None,
    },
]

RSS_KEYWORDS = [
    # Русский — визовая тематика
    {"word": "виза", "lang": "ru"},
    {"word": "визовый", "lang": "ru"},
    {"word": "безвизовый", "lang": "ru"},
    {"word": "безвизовое", "lang": "ru"},
    {"word": "въезд", "lang": "ru"},
    {"word": "пересечение границы", "lang": "ru"},
    {"word": "пограничный контроль", "lang": "ru"},
    {"word": "загранпаспорт", "lang": "ru"},
    {"word": "визовый режим", "lang": "ru"},
    {"word": "туристический режим", "lang": "ru"},
    {"word": "посольство закрыто", "lang": "ru"},
    {"word": "консульство", "lang": "ru"},
    {"word": "запрет въезда", "lang": "ru"},
    {"word": "ограничения въезда", "lang": "ru"},
    {"word": "электронная виза", "lang": "ru"},
    {"word": "виза по прилёту", "lang": "ru"},
    # Английский — визовая тематика
    {"word": "visa", "lang": "en"},
    {"word": "visa-free", "lang": "en"},
    {"word": "visa free", "lang": "en"},
    {"word": "entry ban", "lang": "en"},
    {"word": "travel ban", "lang": "en"},
    {"word": "border closure", "lang": "en"},
    {"word": "immigration", "lang": "en"},
    {"word": "embassy closed", "lang": "en"},
    {"word": "consulate", "lang": "en"},
    {"word": "travel restriction", "lang": "en"},
    {"word": "visa requirement", "lang": "en"},
    {"word": "e-visa", "lang": "en"},
    {"word": "visa on arrival", "lang": "en"},
    {"word": "passport", "lang": "en"},
    {"word": "eta", "lang": "en"},
    # Немецкий
    {"word": "visum", "lang": "de"},
    {"word": "visumfrei", "lang": "de"},
    {"word": "einreise", "lang": "de"},
    {"word": "reisebeschränkung", "lang": "de"},
    # Китайский
    {"word": "签证", "lang": "zh"},
    {"word": "免签", "lang": "zh"},
    # Арабский
    {"word": "تأشيرة", "lang": "ar"},
    {"word": "دخول", "lang": "ar"},
    # Турецкий
    {"word": "vize", "lang": "tr"},
    {"word": "vizesiz", "lang": "tr"},
    {"word": "giriş yasağı", "lang": "tr"},
]


async def seed():
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        # Загружаем страны для маппинга iso2 → id
        countries_result = await session.execute(select(Country))
        countries_by_iso2 = {
            c.iso2: c for c in countries_result.scalars().all()
        }

        # Seed RSS источников
        print("Добавляем RSS источники...")
        sources_added = 0
        for data in RSS_SOURCES:
            existing = await session.execute(
                select(RssSource).where(RssSource.url == data["url"])
            )
            if existing.scalar_one_or_none():
                print(f"  Пропускаем (уже есть): {data['name']}")
                continue

            country_iso2 = data.pop("country_iso2")
            country_id = None
            if country_iso2:
                country = countries_by_iso2.get(country_iso2)
                if country:
                    country_id = country.id

            source = RssSource(**data, country_id=country_id)
            session.add(source)
            sources_added += 1
            print(f"  Добавлен: {data['name']}")

        # Seed ключевых слов
        print("\nДобавляем ключевые слова...")
        keywords_added = 0
        for data in RSS_KEYWORDS:
            existing = await session.execute(
                select(RssKeyword).where(RssKeyword.word == data["word"])
            )
            if existing.scalar_one_or_none():
                continue

            keyword = RssKeyword(**data)
            session.add(keyword)
            keywords_added += 1

        await session.commit()

        print(f"\nГотово!")
        print(f"  RSS источников добавлено: {sources_added}")
        print(f"  Ключевых слов добавлено:  {keywords_added}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())