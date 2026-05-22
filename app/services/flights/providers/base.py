from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession


class DirectFlightProvider(Protocol):
    source: str

    async def fetch_direct_countries(
        self,
        db: AsyncSession,
        origin_iatas: list[str],
        active_dest_iso2: set[str],
    ) -> dict[str, bool]: ...
