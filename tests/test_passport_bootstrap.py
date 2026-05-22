from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.schemas.passport_bootstrap import PassportBootstrapResponse
from app.schemas.travel_cost import BudgetTier, TravelCurrencyListResponse
from app.schemas.visa_policy import VisaMapItem
from app.services.passport_bootstrap_service import get_passport_bootstrap


def _sample_bootstrap(home_iso2: str = "RU") -> PassportBootstrapResponse:
    return PassportBootstrapResponse(
        home_iso2=home_iso2,
        visa_map=[
            VisaMapItem(
                id=uuid4(),
                iso2="DE",
                visa_category="free",
                confidence_level=3,
            )
        ],
        scores_by_tier={
            BudgetTier.cheap: {"DE": 0.8},
            BudgetTier.normal: {"DE": 1.0},
            BudgetTier.expensive: {"DE": 1.2},
        },
        currencies=TravelCurrencyListResponse(
            currencies=["USD", "EUR", "RUB"],
            default_currency="RUB",
        ),
    )


@pytest.mark.asyncio
async def test_get_passport_bootstrap_cache_hit():
    payload = _sample_bootstrap().model_dump(mode="json")
    with patch(
        "app.services.passport_bootstrap_service.cache_get",
        new=AsyncMock(return_value=payload),
    ) as cache_get:
        result = await get_passport_bootstrap(AsyncMock(), "RU")

    cache_get.assert_awaited_once()
    assert result is not None
    assert result.home_iso2 == "RU"
    assert set(result.scores_by_tier.keys()) == {
        BudgetTier.cheap,
        BudgetTier.normal,
        BudgetTier.expensive,
    }


@pytest.mark.asyncio
async def test_get_passport_bootstrap_country_not_found():
    with (
        patch(
            "app.services.passport_bootstrap_service.cache_get",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.services.passport_bootstrap_service.get_country_by_iso2",
            new=AsyncMock(return_value=None),
        ),
    ):
        result = await get_passport_bootstrap(AsyncMock(), "ZZ")

    assert result is None


@pytest.mark.asyncio
async def test_get_passport_bootstrap_loads_and_caches():
    sample = _sample_bootstrap()
    with (
        patch(
            "app.services.passport_bootstrap_service.cache_get",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.services.passport_bootstrap_service.get_country_by_iso2",
            new=AsyncMock(return_value=object()),
        ),
        patch(
            "app.services.passport_bootstrap_service.get_visa_map",
            new=AsyncMock(
                return_value=[
                    {
                        "id": sample.visa_map[0].id,
                        "iso2": "DE",
                        "visa_category": "free",
                        "confidence_level": 3,
                    }
                ]
            ),
        ),
        patch(
            "app.services.passport_bootstrap_service._fetch_scores_by_tier",
            new=AsyncMock(return_value=sample.scores_by_tier),
        ),
        patch(
            "app.services.passport_bootstrap_service.get_travel_cost_currencies",
            new=AsyncMock(return_value=sample.currencies),
        ),
        patch(
            "app.services.passport_bootstrap_service.cache_set",
            new=AsyncMock(),
        ) as cache_set,
        patch(
            "app.services.passport_bootstrap_service._warm_travel_cost_tier_caches",
            new=AsyncMock(),
        ),
    ):
        result = await get_passport_bootstrap(AsyncMock(), "RU")

    assert result is not None
    assert len(result.visa_map) == 1
    assert result.scores_by_tier[BudgetTier.normal]["DE"] == 1.0
    assert cache_set.await_count == 1


@pytest.mark.asyncio
async def test_passport_bootstrap_router_not_found():
    from app.routers.passport_bootstrap import passport_bootstrap

    with patch(
        "app.routers.passport_bootstrap.get_passport_bootstrap",
        new=AsyncMock(return_value=None),
    ):
        with pytest.raises(HTTPException) as exc:
            await passport_bootstrap("ZZ", AsyncMock())

    assert exc.value.status_code == 404
