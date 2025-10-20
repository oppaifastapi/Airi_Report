from pydantic import BaseModel, Field
from typing import Optional

class PriceRow(BaseModel):
    ticker: str = Field(..., description="Ticker symbol")
    close: Optional[float] = None
    prev_close: Optional[float] = None
    change_pct: Optional[float] = None
    marketcap: Optional[float] = None
    volume: Optional[float] = None

class SummaryItem(BaseModel):
    ticker: str
    status: str
    detail: str | None = None
