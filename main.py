import os
import json
import pandas as pd
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import requests
from apscheduler.schedulers.background import BackgroundScheduler

# Your scraper function
from scraper import run_scraper

load_dotenv()

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME")

clients_data = {}
RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)

scheduler = BackgroundScheduler()


def fetch_clients_from_airtable():
    """Load clients from Airtable and store in clients_data"""
    global clients_data
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    headers = {"Authorization": f"Bearer {AIRTABLE_API_KEY}"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print("❌ Airtable error:", response.status_code, response.text)
        return

    records = response.json().get("records", [])
    clients_data = {}

    for record in records:
        fields = record.get("fields", {})
        name = fields.get("Name")
        profession = fields.get("Profession", "Unknown")
        location = fields.get("Location", "New Zealand")
        scrape_time = fields.get("Scrape Time", "08:00")  # default 8am
        cv_keywords = fields.get("CV Keywords", "")

        if name:
            clients_data[name] = {
                "name": name,
                "profession": profession,
                "location": location,
                "scrape_time": scrape_time,
                "cv_keywords": cv_keywords,
                "last_run": "Never",
                "last_count": 0
            }
    print(f"📦 Clients loaded: {len(clients_data)}")


def scheduled_scrape(client):
    """Run scraper for one client and save to their CSV"""
    query = f"{client['profession']} jobs {client['location']}"
    jobs = run_scraper(query)

    # Filter by CV keywords if present
    keywords = [k.strip().lower() for k in client.get("cv_keywords", "").split(",") if k.strip()]
    if keywords:
        jobs = [
            job for job in jobs
            if any(k in (job.get("title", "") + job.get("description", "")).lower() for k in keywords)
        ]

    # Save to client-specific CSV
    safe_name = client['name'].replace(" ", "_")
    filename = os.path.join(RESULTS_DIR, f"{safe_name}.csv")

    df = pd.DataFrame([
        {
            "Job Title": job.get("title"),
            "Company Name": job.get("company"),
            "Application Weblink": job.get("link"),
            "Location": job.get("location")
        }
        for job in jobs
    ])
    df.to_csv(filename, index=False)

    # Update client metadata
    client["last_run"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
    client["last_count"] = len(jobs)

    print(f"✅ Scraped {len(jobs)} jobs for {client['name']} -> {filename}")


@app.on_event("startup")
def startup_event():
    """On startup: fetch clients and schedule jobs"""
    fetch_clients_from_airtable()
    for client in clients_data.values():
        try:
            hour, minute = client["scrape_time"].split(":")
            scheduler.add_job(
                scheduled_scrape,
                "cron",
                hour=int(hour),
                minute=int(minute),
                args=[client]
            )
            print(f"⏰ Scheduled {client['name']} at {client['scrape_time']}")
        except Exception as e:
            print(f"⚠️ Could not schedule {client['name']}: {e}")
    scheduler.start()


# ------------------------
# HOMEPAGE
# ------------------------
@app.get("/", response_class=HTMLResponse)
async def root():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SLRC Job Assist</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { margin: 0; font-family: Arial, sans-serif; }
            .hero {
                background: url('https://images.unsplash.com/photo-1503387762-592deb58ef4e?auto=format&fit=crop&w=1600&q=80') no-repeat center center;
                background-size: cover;
                height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                text-align: center;
            }
            .hero h1 { font-size: 3rem; font-weight: bold; }
            .hero p { font-size: 1.25rem; margin-bottom: 20px; }
            .btn-custom {
                padding: 15px 30px;
                font-size: 1.2rem;
                margin: 10px;
            }
        </style>
    </head>
    <body>
        <div class="hero">
            <div>
                <h1>SLRC Job Assist</h1>
                <p>Smart Job Finder & Client Matching Dashboard</p>
                <a href="/jobs" class="btn btn-success btn-custom">Jobs Page</a>
                <a href="/status" class="btn btn-warning btn-custom">Status Dashboard</a>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# ------------------------
# JOBS PAGE
# ------------------------
@app.get("/jobs", response_class=HTMLResponse)
async def jobs_page():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SLRC Job Assist - Jobs</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { background-color: #f8f9fa; }
            .hero {
                background: url('https://images.unsplash.com/photo-1523289333742-be1143f6b766?auto=format&fit=crop&w=1600&q=80') no-repeat center center;
                background-size: cover;
                padding: 60px 20px;
                color: white;
                text-align: center;
            }
            .hero h1 { font-weight: bold; font-size: 2.5rem; }
            .xray-box {
                background: #fff3cd;
                border: 1px solid #ffeeba;
                padding: 15px;
                margin-top: 20px;
                font-family: monospace;
            }
        </style>
        <script>
            async function loadClients() {
                const res = await fetch('/api/clients');
                const data = await res.json();
                const datalist = document.getElementById('clients');
                data.forEach(c => {
                    const option = document.createElement('option');
                    option.value = c;
                    datalist.appendChild(option);
                });
            }

            async function runSearch() {
                const client = document.getElementById('client').value;
                const query = document.getElementById('query').value;
                const res = await fetch(`/api/scrape?client=${encodeURIComponent(client)}&query=${encodeURIComponent(query)}`);
                const data = await res.json();

                if (data.error) {
                    alert(data.error);
                    return;
                }

                let html = `<table class="table table-hover mt-4"><thead class="table-dark"><tr><th>Company</th><th>Title</th><th>Apply</th><th>Location</th></tr></thead><tbody>`;
                data.jobs.forEach(job => {
                    html += `<tr>
                                <td>${job.company || ""}</td>
                                <td>${job.title || ""}</td>
                                <td><a class="btn btn-sm btn-primary" href="${job.link}" target="_blank">Apply</a></td>
                                <td>${job.location || ""}</td>
                             </tr>`;
                });
                html += "</tbody></table>";
                document.getElementById('results').innerHTML = html;

                // Show X-ray string
                document.getElementById('xray').innerHTML = "<h5>X-Ray Search</h5><div class='xray-box'>" + data.xray + "</div>";
            }

            async function downloadCSV() {
                const client = document.getElementById('client').value;
                if (!client) { alert("Please enter client name"); return; }
                window.location = '/download?client=' + encodeURIComponent(client);
            }

            window.onload = loadClients;
        </script>
    </head>
    <body>
        <div class="hero">
            <h1>SLRC Job Assist</h1>
            <p>Smart Job Finder & Client Matching</p>
        </div>
        <div class="container mt-4">
            <div class="card p-4 shadow-sm">
                <div class="row g-3">
                    <div class="col-md-4">
                        <label class="form-label">Client</label>
                        <input list="clients" id="client" class="form-control" placeholder="Start typing client name">
                        <datalist id="clients"></datalist>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label">Custom Query (optional)</label>
                        <input id="query" class="form-control" placeholder="Leave blank to auto-use client profession">
                    </div>
                    <div class="col-md-2 d-flex align-items-end">
                        <button onclick="runSearch()" class="btn btn-success w-100">Search</button>
                    </div>
                </div>
                <div class="mt-3">
                    <button onclick="downloadCSV()" class="btn btn-warning">Download CSV</button>
                </div>
            </div>
            <div id="results" class="mt-4"></div>
            <div id="xray" class="mt-4"></div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# ------------------------
# STATUS PAGE
# ------------------------
@app.get("/status", response_class=HTMLResponse)
async def status_page():
    rows = ""
    for c in clients_data.values():
        safe_name = c['name'].replace(" ", "_")
        rows += f"""
        <div class="col-md-4">
            <div class="card shadow-sm mb-4">
                <div class="card-body">
                    <h5 class="card-title">{c['name']}</h5>
                    <p class="card-text">
                        <strong>Profession:</strong> {c['profession']}<br>
                        <strong>Location:</strong> {c['location']}<br>
                        <strong>Scrape Time:</strong> {c['scrape_time']}<br>
                        <strong>Last Run:</strong> {c['last_run']}<br>
                        <strong>Jobs Found:</strong> {c['last_count']}
                    </p>
                    <a href='/api/run_now?client={safe_name}' class="btn btn-sm btn-primary">Run Now</a>
                    <a href='/download?client={safe_name}' class="btn btn-sm btn-warning">Download CSV</a>
                </div>
            </div>
        </div>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Status Page</title>
        <meta http-equiv="refresh" content="60">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-light">
        <div class="container py-4">
            <h1 class="mb-4">Scraper Status</h1>
            <p>Auto-refresh every 60 seconds</p>
            <div class="row">
                {rows}
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# ------------------------
# API ENDPOINTS
# ------------------------
@app.get("/api/clients")
async def api_clients():
    return list(clients_data.keys())


@app.get("/api/scrape")
async def api_scrape(client: str, query: str = ""):
    client_info = clients_data.get(client)
    if not client_info:
        return JSONResponse(content={"error": "Client not found"}, status_code=404)

    # If query is blank, auto-generate using client profession + location
    if not query.strip():
        query = f"{client_info['profession']} jobs {client_info['location']}"

    jobs = run_scraper(query)

    # Save to client-specific CSV
    safe_name = client_info['name'].replace(" ", "_")
    filename = os.path.join(RESULTS_DIR, f"{safe_name}.csv")

    df = pd.DataFrame([
        {
            "Job Title": job.get("title"),
            "Company Name": job.get("company"),
            "Application Weblink": job.get("link"),
            "Location": job.get("location")
        }
        for job in jobs
    ])
    df.to_csv(filename, index=False)

    # Update status
    client_info["last_run"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")
    client_info["last_count"] = len(jobs)

    # Build X-ray search string
    company_names = [job["company"] for job in jobs if job.get("company")]
    xray = f'site:linkedin.com/in ("{client_info["profession"]}") ("{" OR ".join(company_names)}")'

    return {"jobs": jobs, "count": len(jobs), "query_used": query, "xray": xray}


@app.get("/api/run_now")
async def run_now(client: str):
    client = client.replace("_", " ")
    client_info = clients_data.get(client)
    if not client_info:
        return JSONResponse(content={"error": "Client not found"}, status_code=404)

    scheduled_scrape(client_info)
    return RedirectResponse(url="/status")


@app.get("/download")
async def download_csv(client: str):
    safe_name = client.replace(" ", "_")
    filename = os.path.join(RESULTS_DIR, f"{safe_name}.csv")
    if not os.path.exists(filename):
        return JSONResponse(content={"error": "No CSV file found for this client"}, status_code=404)
    return FileResponse(filename, filename=f"{safe_name}.csv", media_type="text/csv")
