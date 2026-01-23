from sqlalchemy import Column, Integer, Float, String, Date, DateTime
from datetime import datetime
from database import Base

class MilkEntry(Base):
    __tablename__ = "milk_entries"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date)
    shift = Column(String)
    qty = Column(Float)
    fat = Column(Float)
    snf = Column(Float)
    clr = Column(Float)
    rate_per_litre = Column(Float)
    amount = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
