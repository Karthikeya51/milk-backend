from pydantic import BaseModel
from datetime import date

class MilkEntryCreate(BaseModel):
    date: date
    shift: str
    qty: float
    fat: float
    snf: float
    clr: float
    rate_per_litre: float
