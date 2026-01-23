from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import date
from bson import ObjectId
from collections import defaultdict
import pandas as pd
from fastapi.responses import FileResponse

from database import milk_collection

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- CREATE ----------------
@app.post("/milk-entry")
def create_entry(entry: dict):
    entry["amount"] = entry["qty"] * entry["rate_per_litre"]
    milk_collection.insert_one(entry)
    return {"message": "Entry added"}

# ---------------- READ ALL ----------------
@app.get("/milk-entry")
def get_all():
    data = []
    for e in milk_collection.find().sort("date", -1):
        e["id"] = str(e["_id"])
        del e["_id"]
        data.append(e)
    return data

# ---------------- READ BY DATE ----------------
@app.get("/milk-entry/by-date/{entry_date}")
def by_date(entry_date: str):
    data = []
    for e in milk_collection.find({"date": entry_date}):
        e["id"] = str(e["_id"])
        del e["_id"]
        data.append(e)
    return data

# ---------------- UPDATE ----------------
@app.put("/milk-entry/{entry_id}")
def update(entry_id: str, entry: dict):
    entry["amount"] = entry["qty"] * entry["rate_per_litre"]
    milk_collection.update_one(
        {"_id": ObjectId(entry_id)},
        {"$set": entry}
    )
    return {"message": "Updated"}

# ---------------- DELETE ----------------
@app.delete("/milk-entry/{entry_id}")
def delete(entry_id: str):
    milk_collection.delete_one({"_id": ObjectId(entry_id)})
    return {"message": "Deleted"}

# ---------------- DAILY TOTAL ----------------
@app.get("/reports/daily-total/{entry_date}")
def daily_total(entry_date: str):
    total_qty = 0
    total_amount = 0

    for e in milk_collection.find({"date": entry_date}):
        total_qty += e["qty"]
        total_amount += e["amount"]

    return {
        "date": entry_date,
        "total_qty": total_qty,
        "total_amount": total_amount
    }

# ---------------- MONTHLY REPORT ----------------
@app.get("/reports/monthly/{year}/{month}")
def monthly(year: int, month: int):
    total_qty = 0
    total_amount = 0
    prefix = f"{year}-{month:02d}"

    for e in milk_collection.find({"date": {"$regex": f"^{prefix}"}}):
        total_qty += e["qty"]
        total_amount += e["amount"]

    return {
        "year": year,
        "month": month,
        "total_qty": total_qty,
        "total_amount": total_amount
    }

# ---------------- EXCEL EXPORT ----------------
@app.get("/reports/export-excel")
def export_excel():
    data = []
    for e in milk_collection.find():
        data.append({
            "Date": e["date"],
            "Shift": e["shift"],
            "Qty": e["qty"],
            "Fat": e["fat"],
            "SNF": e["snf"],
            "CLR": e["clr"],
            "Rate": e["rate_per_litre"],
            "Amount": e["amount"]
        })

    df = pd.DataFrame(data)
    file = "milk_report.xlsx"
    df.to_excel(file, index=False)

    return FileResponse(file, filename=file)

# ---------------- DAILY CHART ----------------
@app.get("/charts/daily/{entry_date}")
def daily_chart(entry_date: str):
    result = defaultdict(lambda: {"qty": 0, "amount": 0})

    for e in milk_collection.find({"date": entry_date}):
        shift = e["shift"]
        result[shift]["qty"] += e["qty"]
        result[shift]["amount"] += e["amount"]

    return [
        {"shift": k, "qty": v["qty"], "amount": v["amount"]}
        for k, v in result.items()
    ]

# ---------------- MONTHLY CHART ----------------
@app.get("/charts/monthly/{year}/{month}")
def monthly_chart(year: int, month: int):
    result = defaultdict(lambda: {"qty": 0, "amount": 0})
    prefix = f"{year}-{month:02d}"

    for e in milk_collection.find({"date": {"$regex": f"^{prefix}"}}):
        result[e["date"]]["qty"] += e["qty"]
        result[e["date"]]["amount"] += e["amount"]

    return [
        {"date": k, "qty": v["qty"], "amount": v["amount"]}
        for k, v in sorted(result.items())
    ]
