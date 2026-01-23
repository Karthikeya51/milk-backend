from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
import pandas as pd
from fastapi.responses import FileResponse

import models, schemas
from database import engine, SessionLocal

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# CREATE
@app.post("/milk-entry")
def create_entry(entry: schemas.MilkEntryCreate, db: Session = Depends(get_db)):
    amount = entry.qty * entry.rate_per_litre
    db_entry = models.MilkEntry(**entry.dict(), amount=amount)
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry

# READ ALL
@app.get("/milk-entry")
def get_all(db: Session = Depends(get_db)):
    return db.query(models.MilkEntry).order_by(models.MilkEntry.date.desc()).all()

# READ BY DATE
@app.get("/milk-entry/by-date/{entry_date}")
def by_date(entry_date: date, db: Session = Depends(get_db)):
    return db.query(models.MilkEntry).filter(models.MilkEntry.date == entry_date).all()

# UPDATE
@app.put("/milk-entry/{entry_id}")
def update(entry_id: int, entry: schemas.MilkEntryCreate, db: Session = Depends(get_db)):
    e = db.query(models.MilkEntry).filter(models.MilkEntry.id == entry_id).first()
    if not e:
        return {"error": "Not found"}

    for k, v in entry.dict().items():
        setattr(e, k, v)
    e.amount = entry.qty * entry.rate_per_litre
    db.commit()
    return e

# DELETE
@app.delete("/milk-entry/{entry_id}")
def delete(entry_id: int, db: Session = Depends(get_db)):
    e = db.query(models.MilkEntry).filter(models.MilkEntry.id == entry_id).first()
    if not e:
        return {"error": "Not found"}
    db.delete(e)
    db.commit()
    return {"message": "Deleted"}

# DAILY TOTAL
@app.get("/reports/daily-total/{entry_date}")
def daily_total(entry_date: date, db: Session = Depends(get_db)):
    r = db.query(
        func.sum(models.MilkEntry.qty),
        func.sum(models.MilkEntry.amount)
    ).filter(models.MilkEntry.date == entry_date).first()

    return {
        "date": entry_date,
        "total_qty": r[0] or 0,
        "total_amount": r[1] or 0
    }

# MONTHLY REPORT
@app.get("/reports/monthly/{year}/{month}")
def monthly(year: int, month: int, db: Session = Depends(get_db)):
    r = db.query(
        func.sum(models.MilkEntry.qty),
        func.sum(models.MilkEntry.amount)
    ).filter(
        func.strftime("%Y", models.MilkEntry.date) == str(year),
        func.strftime("%m", models.MilkEntry.date) == f"{month:02d}"
    ).first()

    return {
        "year": year,
        "month": month,
        "total_qty": r[0] or 0,
        "total_amount": r[1] or 0
    }

# EXCEL EXPORT
@app.get("/reports/export-excel")
def export_excel(db: Session = Depends(get_db)):
    entries = db.query(models.MilkEntry).all()
    data = [{
        "Date": e.date,
        "Shift": e.shift,
        "Qty": e.qty,
        "Fat": e.fat,
        "SNF": e.snf,
        "CLR": e.clr,
        "Rate": e.rate_per_litre,
        "Amount": e.amount
    } for e in entries]

    df = pd.DataFrame(data)
    file = "milk_report.xlsx"
    df.to_excel(file, index=False)

    return FileResponse(file, filename=file)

@app.get("/charts/daily/{entry_date}")
def daily_chart(entry_date: date, db: Session = Depends(get_db)):
    data = (
        db.query(
            models.MilkEntry.shift,
            func.sum(models.MilkEntry.qty).label("qty"),
            func.sum(models.MilkEntry.amount).label("amount")
        )
        .filter(models.MilkEntry.date == entry_date)
        .group_by(models.MilkEntry.shift)
        .all()
    )

    return [
        {"shift": d.shift, "qty": d.qty, "amount": d.amount}
        for d in data
    ]

@app.get("/charts/monthly/{year}/{month}")
def monthly_chart(year: int, month: int, db: Session = Depends(get_db)):
    data = (
        db.query(
            models.MilkEntry.date,
            func.sum(models.MilkEntry.qty).label("qty"),
            func.sum(models.MilkEntry.amount).label("amount")
        )
        .filter(
            func.strftime("%Y", models.MilkEntry.date) == str(year),
            func.strftime("%m", models.MilkEntry.date) == f"{month:02d}"
        )
        .group_by(models.MilkEntry.date)
        .order_by(models.MilkEntry.date)
        .all()
    )

    return [
        {"date": d.date, "qty": d.qty, "amount": d.amount}
        for d in data
    ]

