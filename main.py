import os
import asyncio
import logging
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import requests
import pandas as pd
from scraper import run_scraper

# Logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# FastAPI
app = FastAPI(title="Job Search Assistant", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Airtable config
AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_CLIENTS_TABLE = os.getenv("AIRTABLE_CLIENTS_TABLE", "Job Seekers")

clients_cache = {}

def fetch_clients():
    """Fetch clients from Airtable"""
    global clients_cache
    try:
        url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_CLIENTS_TABLE}"
        headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}"}
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json().get("records", [])
        clients_cache = {
            rec["fields"]["Full Name"]: {
                "name": rec["fields"].get("Full Name", ""),
                "profession": rec["fields"].get("Profession", ""),
                "location": "New Zealand",   # force NZ
                "id": rec["id"]
            }
            for rec in data if "fields" in rec and "Full Name" in rec["fields"]
        }
        logger.info(f"✅ Loaded {len(clients_cache)} clients")
    except Exception as e:
        logger.error(f"❌ Airtable fetch error: {e}")
        clients_cache = {}
    return clients_cache

@app.on_event("startup")
async def startup_event():
    fetch_clients()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "clients": list(clients_cache.values()),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
    })

@app.get("/search_jobs")
async def search_jobs(client: str):
    if client not in clients_cache:
        return JSONResponse({"error": "Client not found"}, status_code=404)
    client_info = clients_cache[client]
    query = f"{client_info['profession']} jobs in New Zealand"
    logger.info(f"🔍 Running scraper for {client}: {query}")
    try:
        jobs = await asyncio.to_thread(run_scraper, query)
    except Exception as e:
        logger.error(f"Scraper error: {e}")
        jobs = []
    # Xray string
    companies = [j["company"] for j in jobs if j.get("company")]
    xray = f'site:linkedin.com/in ("{client_info["profession"]}") ("' + '" OR "'.join(companies[:8]) + '")'
    return {
        "client": client,
        "jobs": jobs,
        "xray": xray,
        "query": query,
        "count": len(jobs),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/export/{client}")
async def export_jobs(client: str):
    if client not in clients_cache:
        return JSONResponse({"error": "Client not found"}, status_code=404)
    query = f"{clients_cache[client]['profession']} jobs in New Zealand"
    jobs = await asyncio.to_thread(run_scraper, query)
    if not jobs:
        return JSONResponse({"error": "No jobs to export"}, status_code=404)
    df = pd.DataFrame(jobs)
    fname = f"jobs_{client.replace(' ','_')}_{datetime.now().date()}.xlsx"
    path = os.path.join("logs", fname)
    df.to_excel(path, index=False)
    return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=fname)

@app.get("/refresh_clients")
async def refresh_clients():
    data = fetch_clients()
    return {"success": True, "count": len(data)}

@app.get("/logs")
async def get_logs():
    try:
        with open("logs/app.log") as f:
            return {"logs": f.readlines()[-100:]}
    except:
        return {"logs": []}
