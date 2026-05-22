"""
Поиск рейсов через Google Flights (fast-flights): город(а) отправления → страна назначения.

Не использует FLIGHTS_DATA_SOURCE и не пишет в кеш direct-countries.

Примеры:
  python scripts/fast_flights_search.py --origin Samara,RU --dest-country TR
  python scripts/fast_flights_search.py --origin "Nizhny Novgorod,RU" --dest-country TR
  python scripts/fast_flights_search.py --origin-city "Nizhny Novgorod" --origin-country RU --dest-country TR
  python scripts/fast_flights_search.py --origin Samara,RU --origin Moscow,RU --dest-country TH --date 2026-07-15
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.services.flight_service import CityNotFoundError
from app.services.flights.fast_flights_search import (
    build_origin_inputs,
    configure_quiet_fast_flights_logging,
    search_flights_to_country,
)

configure_quiet_fast_flights_logging(logging.getLogger(__name__))
logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Точный поиск рейсов Google Flights: один или несколько городов "
            "отправления и одна страна назначения."
        ),
    )
    parser.add_argument(
        "--origin",
        action="append",
        default=[],
        metavar="CITY,ISO2",
        help=(
            "Город и ISO2 через запятую. Для названий с пробелами — в кавычках: "
            '"Nizhny Novgorod,RU"'
        ),
    )
    parser.add_argument(
        "--origin-city",
        action="append",
        default=[],
        metavar="CITY",
        help='Город отправления (альтернатива --origin), напр. "Nizhny Novgorod"',
    )
    parser.add_argument(
        "--origin-country",
        action="append",
        default=[],
        metavar="ISO2",
        help="ISO2 страны для каждого --origin-city (или один код для всех)",
    )
    parser.add_argument(
        "--dest-country",
        required=True,
        metavar="ISO2",
        help="ISO2 страны назначения, напр. TR",
    )
    parser.add_argument(
        "--date",
        help="Дата вылета YYYY-MM-DD (по умолчанию today + FLIGHTS_PROBE_DATE_OFFSET_DAYS)",
    )
    parser.add_argument(
        "--max-stops",
        type=int,
        default=0,
        help="Максимум пересадок (0 = только прямые, None = без ограничения)",
    )
    parser.add_argument(
        "--seat",
        default="economy",
        choices=["economy", "premium-economy", "business", "first"],
        help="Класс обслуживания",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Путь для сохранения JSON (иначе stdout)",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Компактный JSON без отступов",
    )
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()
    try:
        origins = build_origin_inputs(
            origin_values=args.origin,
            origin_cities=args.origin_city,
            origin_countries=args.origin_country,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    max_stops = None if args.max_stops < 0 else args.max_stops

    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            try:
                result = await search_flights_to_country(
                    session,
                    origins=origins,
                    dest_country_iso2=args.dest_country,
                    departure_date=args.date,
                    max_stops=max_stops,
                    seat=args.seat,
                    show_progress=True,
                )
            except CityNotFoundError as exc:
                raise SystemExit(str(exc)) from exc
    finally:
        await engine.dispose()

    payload = result.to_dict()
    indent = None if args.compact else 2
    text = json.dumps(payload, ensure_ascii=False, indent=indent)

    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
        logger.info(
            "Сохранено: %s (routes=%s, flights=%s)",
            args.output,
            result.summary["routes_searched"],
            result.summary["total_flights"],
        )
    else:
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")

    logger.info(
        "Поиск завершён: routes_searched=%s routes_with_flights=%s total_flights=%s",
        result.summary["routes_searched"],
        result.summary["routes_with_flights"],
        result.summary["total_flights"],
    )


if __name__ == "__main__":
    asyncio.run(main())
