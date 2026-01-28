from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from bson import ObjectId
from io import BytesIO
import pandas as pd

from database import milk_collection
from database import cow_health_collection

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
    entry["amount"] = round(entry["qty"] * entry["rate_per_litre"], 2)
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
def update_milk_entry(entry_id: str, entry: dict):
    entry["amount"] = round(entry["qty"] * entry["rate_per_litre"], 2)

    milk_collection.update_one(
        {"_id": ObjectId(entry_id)},
        {"$set": entry}
    )

    return {"message": "Milk entry updated"}


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
        "total_qty": round(total_qty, 2),
        "total_amount": round(total_amount, 2)
    }

# ---------------- DAILY CHART ----------------
@app.get("/charts/daily/{entry_date}")
def daily_chart(entry_date: str):
    pipeline = [
        {"$match": {"date": entry_date}},
        {
            "$group": {
                "_id": "$shift",
                "qty": {"$sum": "$qty"},
                "amount": {"$sum": "$amount"},
                "fat": {"$avg": "$fat"},
                "snf": {"$avg": "$snf"},
                "clr": {"$avg": "$clr"},
                "rate_per_litre": {"$avg": "$rate_per_litre"},
            }
        }
    ]

    return [
        {
            "shift": d["_id"],
            "qty": round(d["qty"], 2),
            "amount": round(d["amount"], 2),
            "fat": round(d["fat"], 2),
            "snf": round(d["snf"], 2),
            "clr": round(d["clr"], 2),
            "rate_per_litre": round(d["rate_per_litre"], 2),
        }
        for d in milk_collection.aggregate(pipeline)
    ]

# ---------------- MONTHLY RANGE CHART ----------------
@app.get("/charts/monthly-range")
def monthly_chart_range(
    from_date: str = Query(
        ...,
        examples={"from": {"value": "2026-01-01"}}
    ),
    to_date: str = Query(
        ...,
        examples={"to": {"value": "2026-01-31"}}
    )
):
    pipeline = [
        {
            "$match": {
                "date": {"$gte": from_date, "$lte": to_date}
            }
        },
        {
            "$group": {
                "_id": "$date",
                "qty": {"$sum": "$qty"},
                "amount": {"$sum": "$amount"},
                "fat": {"$avg": "$fat"},
                "snf": {"$avg": "$snf"},
                "clr": {"$avg": "$clr"},
                "rate_per_litre": {"$avg": "$rate_per_litre"},
            }
        },
        {"$sort": {"_id": 1}}
    ]

    return [
        {
            "date": d["_id"],
            "qty": round(d["qty"], 2),
            "amount": round(d["amount"], 2),
            "fat": round(d["fat"], 2),
            "snf": round(d["snf"], 2),
            "clr": round(d["clr"], 2),
            "rate_per_litre": round(d["rate_per_litre"], 2),
        }
        for d in milk_collection.aggregate(pipeline)
    ]

@app.get("/reports/export-excel-range")
def export_excel_range(
    from_date: str = Query(..., description="Start date YYYY-MM-DD"),
    to_date: str = Query(..., description="End date YYYY-MM-DD"),
):
    data = []

    for e in milk_collection.find({
        "date": {"$gte": from_date, "$lte": to_date}
    }).sort("date", 1):
        data.append({
            "Date": e.get("date"),
            "Shift": e.get("shift"),
            "Quantity": round(e.get("qty", 0), 2),
            "Fat": round(e.get("fat", 0), 2),
            "SNF": round(e.get("snf", 0), 2),
            "CLR": round(e.get("clr", 0), 2),
            "Rate": round(e.get("rate_per_litre", 0), 2),
            "Amount": round(e.get("amount", 0), 2),
            "Note": e.get("note", "")
        })

    df = pd.DataFrame(data)

    output = BytesIO()
    df.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)

    filename = f"milk_report_{from_date}_to_{to_date}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

# ---------------- BULK DELETE ----------------
@app.post("/milk-entry/bulk-delete")
def bulk_delete(ids: list[str]):
    milk_collection.delete_many({
        "_id": {"$in": [ObjectId(i) for i in ids]}
    })
    return {"message": "Deleted"}


# range export excel on chart page

@app.get("/milk-entry/monthly")
def get_monthly_entries(
    year: int = Query(..., example=2026),
    month: int = Query(..., example=1)
):
    prefix = f"{year}-{month:02d}"
    data = []

    for e in milk_collection.find(
        {"date": {"$regex": f"^{prefix}"}}
    ).sort("date", 1):
        e["id"] = str(e["_id"])
        del e["_id"]

        e["qty"] = round(e.get("qty", 0), 2)
        e["fat"] = round(e.get("fat", 0), 2)
        e["snf"] = round(e.get("snf", 0), 2)
        e["clr"] = round(e.get("clr", 0), 2)
        e["rate_per_litre"] = round(e.get("rate_per_litre", 0), 2)
        e["amount"] = round(e.get("amount", 0), 2)

        data.append(e)

    return data   # ✅ ARRAY ONLY


# montly export
@app.get("/reports/export-excel-monthly")
def export_excel_monthly(
    year: int = Query(..., example=2026),
    month: int = Query(..., example=1)
):
    prefix = f"{year}-{month:02d}"
    data = []

    for e in milk_collection.find(
        {"date": {"$regex": f"^{prefix}"}}
    ).sort("date", 1):
        data.append({
            "Date": e.get("date"),
            "Shift": e.get("shift"),
            "Quantity": round(e.get("qty", 0), 2),
            "Fat": round(e.get("fat", 0), 2),
            "SNF": round(e.get("snf", 0), 2),
            "CLR": round(e.get("clr", 0), 2),
            "Rate": round(e.get("rate_per_litre", 0), 2),
            "Amount": round(e.get("amount", 0), 2),
            "Note": e.get("note", "")
        })

    df = pd.DataFrame(data)

    output = BytesIO()
    df.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)

    filename = f"milk_report_{year}_{month:02d}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )



from bson import ObjectId



@app.post("/cow-health")
def create_cow_health(entry: dict):
    required_fields = [
        "date",
        "shift",
        "cow_name",
        "cow_temperature",
        "milk_given",
        "medicine_given"
    ]

    for field in required_fields:
        if field not in entry or entry[field] in ["", None]:
            return {
                "error": f"{field} is required"
            }

    cow_health_collection.insert_one(entry)
    return {"message": "Cow health entry added"}


@app.get("/cow-health")
def get_all_cow_logs():
    data = []
    for e in cow_health_collection.find().sort("date", -1):
        e["id"] = str(e["_id"])
        del e["_id"]
        data.append(e)
    return data

@app.delete("/cow-health/{log_id}")
def delete_cow_log(log_id: str):
    cow_health_collection.delete_one({"_id": ObjectId(log_id)})
    return {"message": "Deleted"}

def safe_round(value, digits=2):
    return round(value, digits) if isinstance(value, (int, float)) else 0.0


@app.get("/cow-health/monthly")
def get_cow_health_monthly(
    year: int = Query(...),
    month: int = Query(...)
):
    prefix = f"{year}-{month:02d}"
    data = []

    for e in cow_health_collection.find(
        {"date": {"$regex": f"^{prefix}"}}
    ).sort("date", 1):

        data.append({
            "id": str(e["_id"]),
            "date": e.get("date"),
            "shift": e.get("shift"),
            "cow_name": e.get("cow_name"),
            "cow_temperature": safe_round(e.get("cow_temperature")),
            "milk_given": safe_round(e.get("milk_given")),
            "medicine_given": e.get("medicine_given", False),
            "note": e.get("note", "")
        })

    return {
        "year": year,
        "month": month,
        "count": len(data),
        "data": data
    }

    prefix = f"{year}-{month:02d}"
    data = []

    for e in cow_health_collection.find(
        {"date": {"$regex": f"^{prefix}"}}
    ).sort("date", 1):
        e["id"] = str(e["_id"])
        del e["_id"]

        e["cow_temperature"] = round(e.get("cow_temperature", 0), 2)
        e["milk_given"] = round(e.get("milk_given", 0), 2)

        data.append(e)

    return {
        "year": year,
        "month": month,
        "count": len(data),
        "data": data
    }

@app.put("/cow-health/{entry_id}")
def update_cow_health(entry_id: str, entry: dict):
    entry["cow_temperature"] = round(float(entry["cow_temperature"]), 2)
    entry["milk_given"] = round(float(entry["milk_given"]), 2)

    cow_health_collection.update_one(
        {"_id": ObjectId(entry_id)},
        {"$set": entry}
    )
    return {"message": "Updated"}

@app.delete("/cow-health/{entry_id}")
def delete_cow_health(entry_id: str):
    cow_health_collection.delete_one({"_id": ObjectId(entry_id)})
    return {"message": "Deleted"}

@app.get("/reports/export-cow-health-monthly")
def export_cow_health_excel(
    year: int = Query(...),
    month: int = Query(...)
):
    prefix = f"{year}-{month:02d}"
    data = []

    for e in cow_health_collection.find(
        {"date": {"$regex": f"^{prefix}"}}
    ).sort("date", 1):
        data.append({
            "Date": e.get("date"),
            "Shift": e.get("shift"),
            "Cow Name": e.get("cow_name"),
            "Temperature": round(e.get("cow_temperature", 0), 2),
            "Milk Given": round(e.get("milk_given", 0), 2),
            "Medicine Given": "Yes" if e.get("medicine_given") else "No",
            "Note": e.get("note", "")
        })

    df = pd.DataFrame(data)
    output = BytesIO()
    df.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)

    filename = f"cow_health_{year}_{month:02d}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@app.post("/cow-health/bulk-delete")
def bulk_delete(ids: list[str]):
    cow_health_collection.delete_many({
        "_id": {"$in": [ObjectId(i) for i in ids]}
    })
    return {"message": "Deleted"}

@app.put("/cow-health/{id}")
def update_cow_health(id: str, payload: dict):
    payload["cow_temperature"] = round(payload["cow_temperature"], 1)
    payload["milk_given"] = round(payload["milk_given"], 1)

    cow_health_collection.update_one(
        {"_id": ObjectId(id)},
        {"$set": payload}
    )
    return {"message": "Updated"}
