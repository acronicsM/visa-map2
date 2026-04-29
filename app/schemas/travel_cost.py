from enum import Enum



from pydantic import BaseModel, field_validator, model_validator





class BudgetTier(str, Enum):

    cheap = "cheap"

    normal = "normal"

    expensive = "expensive"





class TravelCostMatrixEntry(BaseModel):

    dest_iso2: str

    score_cheap: float | None = None

    score_normal: float | None = None

    score_expensive: float | None = None





class TravelCostMapResponse(BaseModel):

    home_iso2: str

    budget_tier: BudgetTier

    scores: dict[str, float]





class TravelCostUploadResponse(BaseModel):

    imported_count: int





class TravelCostScoreBandsResponse(BaseModel):

    """

    Интервалы относительного score (к дому) для подписей и раскраски карты.



    Семантика (k = len(thresholds)):

    - score < thresholds[0] → bands[0];

    - для i = 1..k-1: thresholds[i-1] <= score <= thresholds[i] → bands[i];

    - score > thresholds[k-1] → bands[k].



    При пустом `thresholds` — один интервал на любой score.

    """



    thresholds: list[float]

    labels: list[str]

    colors: list[str]



    @field_validator("thresholds")

    @classmethod

    def _thresholds_finite(cls, v: list[float]) -> list[float]:

        for x in v:

            if x != x:  # NaN

                raise ValueError("thresholds не должны содержать NaN")

        return v



    @model_validator(mode="after")

    def _lengths_and_order(self) -> "TravelCostScoreBandsResponse":

        t, labels, colors = self.thresholds, self.labels, self.colors

        if len(labels) != len(colors):

            raise ValueError("labels и colors должны иметь одинаковую длину")

        if not t:

            if len(labels) != 1:

                raise ValueError(

                    "При пустых thresholds нужна ровно одна пара label/color"

                )

            return self

        if len(labels) != len(t) + 1:

            raise ValueError("Ожидается len(labels) == len(thresholds) + 1")

        for i in range(1, len(t)):

            if t[i] <= t[i - 1]:

                raise ValueError("thresholds должны строго возрастать")

        return self


