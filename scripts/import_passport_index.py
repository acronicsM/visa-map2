import asyncio
import sys
import os
import io

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
import csv

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, delete

from app.config import settings
from app.models.country import Country
from app.models.passport import Passport
from app.models.visa_policy import VisaPolicy

PASSPORT_INDEX_URL = (
    "https://raw.githubusercontent.com/ilyankou/"
    "passport-index-dataset/master/passport-index-matrix-iso2.csv"
)


def map_visa_category(value: str) -> tuple[str | None, int | None]:
    """
    Маппинг согласно README датасета:
    7-360         — visa free с количеством дней
    visa free     — visa free (дни неизвестны)
    visa on arrival — виза по прилёту
    eta           — электронное разрешение (проще чем e-visa)
    e-visa        — электронная виза
    visa required — виза в посольстве
    no admission  — въезд закрыт
    -1            — паспорт = страна назначения (пропускаем)
    """
    value = value.strip().lower()

    if value == "-1":
        return (None, None)
    elif value == "visa free":
        return ("free", None)
    elif value == "visa on arrival":
        return ("voa", None)
    elif value == "eta":
        return ("evisa", None)
    elif value == "e-visa":
        return ("evisa", None)
    elif value == "visa required":
        return ("embassy", None)
    elif value == "no admission":
        return ("unavailable", None)
    else:
        try:
            days = int(value)
            if 7 <= days <= 360:
                return ("free", days)
            else:
                return ("embassy", None)
        except ValueError:
            return ("embassy", None)


async def import_passport_index():
    print("Скачиваем Passport Index датасет...")

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(PASSPORT_INDEX_URL)
        response.raise_for_status()
        csv_content = response.text

    print(f"Датасет скачан ({len(csv_content)} байт)")

    reader = csv.DictReader(io.StringIO(csv_content))
    rows = list(reader)
    fieldnames = reader.fieldnames

    print(f"Строк в датасете: {len(rows)} паспортов")

    destination_columns = fieldnames[1:]
    print(f"Стран назначения: {len(destination_columns)}")

    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        print("\nЗагружаем справочник стран и паспортов...")

        countries_result = await session.execute(select(Country))
        countries_by_iso2 = {
            c.iso2: c for c in countries_result.scalars().all()
        }

        passports_result = await session.execute(
            select(Passport).where(Passport.type == "regular")
        )
        passports_by_country_id = {
            p.country_id: p for p in passports_result.scalars().all()
        }

        print(f"Стран в БД: {len(countries_by_iso2)}")
        print(f"Паспортов в БД: {len(passports_by_country_id)}")

        print("\nУдаляем старые visa_policies...")
        await session.execute(delete(VisaPolicy))
        await session.commit()
        print("  Старые записи удалены")

        total_added = 0
        total_skipped_passport = 0
        total_skipped_dest = 0
        total_skipped_value = 0

        print("\nЗагружаем визовые режимы...")

        for row_num, row in enumerate(rows):
            passport_iso2 = list(row.values())[0].strip().upper()

            passport_country = countries_by_iso2.get(passport_iso2)
            if not passport_country:
                total_skipped_passport += 1
                continue

            passport = passports_by_country_id.get(passport_country.id)
            if not passport:
                total_skipped_passport += 1
                continue

            batch = []
            for dest_iso2_raw in destination_columns:
                dest_iso2 = dest_iso2_raw.strip().upper()

                dest_country = countries_by_iso2.get(dest_iso2)
                if not dest_country:
                    total_skipped_dest += 1
                    continue

                raw_value = row.get(dest_iso2_raw, "").strip()
                if not raw_value:
                    total_skipped_value += 1
                    continue

                visa_category, max_stay_days = map_visa_category(raw_value)

                if visa_category is None:
                    continue

                policy = VisaPolicy(
                    passport_id=passport.id,
                    destination_id=dest_country.id,
                    visa_category=visa_category,
                    max_stay_days=max_stay_days,
                    verified_by="passport_index_dataset",
                    confidence_level=3,
                )
                batch.append(policy)

            session.add_all(batch)
            total_added += len(batch)

            if (row_num + 1) % 20 == 0:
                await session.flush()
                print(
                    f"  Обработано паспортов: {row_num + 1}/{len(rows)}, "
                    f"записей: {total_added}"
                )

        print("\nСохраняем в БД...")
        await session.commit()

    print(f"\nГотово!")
    print(f"  Добавлено записей:        {total_added}")
    print(f"  Пропущено (нет паспорта): {total_skipped_passport}")
    print(f"  Пропущено (нет страны):   {total_skipped_dest}")
    print(f"  Пропущено (нет значения): {total_skipped_value}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(import_passport_index())