from pydantic import BaseModel

from app.schemas.travel_cost import BudgetTier, TravelCurrencyListResponse
from app.schemas.visa_policy import VisaMapItem


class PassportBootstrapResponse(BaseModel):
    home_iso2: str
    visa_map: list[VisaMapItem]
    scores_by_tier: dict[BudgetTier, dict[str, float]]
    currencies: TravelCurrencyListResponse
