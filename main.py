from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from supabase import create_client, Client
from datetime import datetime

app = FastAPI()

# Supabase Credentials (Apna yahan daal dena)
SUPAPSE_URL = "https://ozstskgokzppbfbbubyp.supabase.co"
SUPAPSE_KEY = "sb_publishable_JDP0BufPA7MpgLSi8wffMg_i7_64gVO"

supabase: Client = create_client(SUPAPSE_URL, SUPAPSE_KEY)

templates = Jinja2Templates(directory="templates")

@app.get("/")
async def read_root(request: Request):
    # Supabase se transactions fetch karo
    try:
        response = supabase.table("transactions").select("*").order("date", desc=True).execute()
        transactions = response.data or []
    except Exception as e:
        transactions = []

    # Total Balance, Gives, Takes calculate karo
    total_gives = sum([abs(float(t["amount"])) for t in transactions if float(t["amount"]) >= 0])
    total_takes = sum([abs(float(t["amount"])) for t in transactions if float(t["amount"]) < 0])
    total_balance = total_takes - total_gives

    return templates.TemplateResponse("index.html", {
        "request": request,
        "transactions": transactions,
        "total_balance": total_balance,
        "total_gives": total_gives,
        "total_takes": total_takes
    })

@app.post("/add")
async def add_transaction(
    date: str = Form(...),
    amount: float = Form(...),
    reason: str = Form(...)
):
    payload = {
        "date": date,
        "amount": amount,
        "reason": reason,
        "screenshot": ""
    }
    supabase.table("transactions").insert(payload).execute()
    return RedirectResponse(url="/", status_code=303)

@app.post("/delete/{item_id}")
async def delete_transaction(item_id: str):
    supabase.table("transactions").delete().eq("id", item_id).execute()
    return RedirectResponse(url="/", status_code=303)
