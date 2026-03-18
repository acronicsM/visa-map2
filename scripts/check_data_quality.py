import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func, text

from app.config import settings
from app.models.country import Country
from app.models.passport import Passport
from app.models.visa_policy import VisaPolicy


async def check_quality():
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:

        print("=" * 60)
        print("ОТЧЁТ О КАЧЕСТВЕ ДАННЫХ")
        print("=" * 60)

        # 1. Общая статистика
        total_countries = await session.execute(
            select(func.count(Country.id))
        )
        active_countries = await session.execute(
            select(func.count(Country.id)).where(Country.is_active == True)
        )
        total_passports = await session.execute(
            select(func.count(Passport.id))
        )
        total_policies = await session.execute(
            select(func.count(VisaPolicy.id))
        )
        countries_with_geom = await session.execute(
            select(func.count(Country.id)).where(Country.geom.isnot(None))
        )

        print(f"\n1. ОБЩАЯ СТАТИСТИКА")
        print(f"   Стран всего:          {total_countries.scalar()}")
        print(f"   Стран активных:       {active_countries.scalar()}")
        print(f"   Стран с геометрией:   {countries_with_geom.scalar()}")
        print(f"   Паспортов:            {total_passports.scalar()}")
        print(f"   Визовых режимов:      {total_policies.scalar()}")

        # 2. Распределение по категориям виз
        print(f"\n2. РАСПРЕДЕЛЕНИЕ ВИЗ ПО КАТЕГОРИЯМ")
        categories = await session.execute(
            select(VisaPolicy.visa_category, func.count(VisaPolicy.id))
            .group_by(VisaPolicy.visa_category)
            .order_by(func.count(VisaPolicy.id).desc())
        )
        for cat, count in categories.all():
            bar = "█" * (count // 500)
            print(f"   {cat:<12} {count:>6}  {bar}")

        # 3. Топ-10 паспортов по количеству безвизовых стран
        print(f"\n3. ТОП-10 ПАСПОРТОВ (безвизовый доступ)")
        top_passports = await session.execute(text("""
            SELECT c.iso2, c.name_ru, COUNT(*) as free_count
            FROM visa_policies vp
            JOIN passports p ON p.id = vp.passport_id
            JOIN countries c ON c.id = p.country_id
            WHERE vp.visa_category = 'free'
            GROUP BY c.iso2, c.name_ru
            ORDER BY free_count DESC
            LIMIT 10
        """))
        for iso2, name, count in top_passports.all():
            bar = "█" * (count // 5)
            print(f"   {iso2} {name:<30} {count:>4}  {bar}")

        # 4. Топ-10 худших паспортов
        print(f"\n4. ТОП-10 ПАСПОРТОВ (наименьший безвизовый доступ)")
        worst_passports = await session.execute(text("""
            SELECT c.iso2, c.name_ru, COUNT(*) as free_count
            FROM visa_policies vp
            JOIN passports p ON p.id = vp.passport_id
            JOIN countries c ON c.id = p.country_id
            WHERE vp.visa_category = 'free'
            GROUP BY c.iso2, c.name_ru
            ORDER BY free_count ASC
            LIMIT 10
        """))
        for iso2, name, count in worst_passports.all():
            bar = "█" * (count // 2)
            print(f"   {iso2} {name:<30} {count:>4}  {bar}")

        # 5. Страны без геометрии (активные)
        print(f"\n5. АКТИВНЫЕ СТРАНЫ БЕЗ ГЕОМЕТРИИ")
        no_geom = await session.execute(
            select(Country.iso2, Country.name_ru, Country.region)
            .where(Country.is_active == True)
            .where(Country.geom.is_(None))
            .order_by(Country.region, Country.name_ru)
        )
        rows = no_geom.all()
        if rows:
            for iso2, name, region in rows:
                print(f"   [{iso2}] {name} ({region})")
        else:
            print("   Все активные страны имеют геометрию!")

        # 6. Проверка симметрии (A→B есть, B→A?)
        print(f"\n6. ПРОВЕРКА ДАННЫХ ДЛЯ ПРИОРИТЕТНЫХ ПАСПОРТОВ")
        priority = ["RU", "DE", "US", "CN", "IN", "TR", "GB", "UA"]
        for iso2 in priority:
            count = await session.execute(text(f"""
                SELECT COUNT(*)
                FROM visa_policies vp
                JOIN passports p ON p.id = vp.passport_id
                JOIN countries c ON c.id = p.country_id
                WHERE c.iso2 = '{iso2}'
            """))
            n = count.scalar()
            status = "OK" if n > 150 else "МАЛО ДАННЫХ"
            print(f"   {iso2}: {n} записей — {status}")

        # 7. Аномалии — страны с подозрительно малым числом записей
        print(f"\n7. ПАСПОРТА С МАЛЫМ ЧИСЛОМ ЗАПИСЕЙ (< 100)")
        few_records = await session.execute(text("""
            SELECT c.iso2, c.name_ru, COUNT(*) as cnt
            FROM visa_policies vp
            JOIN passports p ON p.id = vp.passport_id
            JOIN countries c ON c.id = p.country_id
            GROUP BY c.iso2, c.name_ru
            HAVING COUNT(*) < 100
            ORDER BY cnt ASC
            LIMIT 10
        """))
        rows = few_records.all()
        if rows:
            for iso2, name, cnt in rows:
                print(f"   [{iso2}] {name}: {cnt} записей")
        else:
            print("   Аномалий не найдено")

        print(f"\n{'=' * 60}")
        print("Проверка завершена")
        print("=" * 60)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check_quality())