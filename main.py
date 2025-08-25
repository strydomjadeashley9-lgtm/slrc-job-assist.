# main.py - Complete Job Application Management System
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
import requests
import subprocess
from pathlib import Path

# Configuration
AIRTABLE_API_KEY = os.getenv('AIRTABLE_API_KEY', 'YOUR_AIRTABLE_API_KEY')
AIRTABLE_BASE_ID = os.getenv('AIRTABLE_BASE_ID', 'YOUR_AIRTABLE_BASE_ID')
AIRTABLE_TABLE_NAME = os.getenv('AIRTABLE_TABLE_NAME', 'Job Seekers')

# Create required directories
for directory in ["static", "results", "logs"]:
    if not os.path.exists(directory):
        os.makedirs(directory)

app = FastAPI(title="Job Application Management System")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global state management
system_state = {
    "clients": {},
    "active_searches": {},
    "search_history": [],
    "airtable_connected": False,
    "job_scraper_available": False
}

class AirtableManager:
    def __init__(self):
        self.api_key = AIRTABLE_API_KEY
        self.base_id = AIRTABLE_BASE_ID
        self.table_name = AIRTABLE_TABLE_NAME
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}/{self.table_name}"
        
    def get_headers(self):
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
    
    def test_connection(self):
        try:
            response = requests.get(f"{self.base_url}?maxRecords=1", headers=self.get_headers(), timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Airtable connection failed: {e}")
            return False
    
    def get_all_clients(self):
        try:
            clients = {}
            response = requests.get(self.base_url, headers=self.get_headers(), timeout=30)
            
            if response.status_code != 200:
                print(f"Airtable API error: {response.status_code}")
                return {}
            
            data = response.json()
            records = data.get("records", [])
            print(f"DEBUG: Found {len(records)} records")
            
            for record in records:
                fields = record.get("fields", {})
                client_name = fields.get("Full Name")
                print(f"DEBUG: Processing {client_name}")
                
                if client_name:
                    skills_array = fields.get("Skills", [])
                    profession = skills_array[0] if skills_array and len(skills_array) > 0 else "Professional"
                    
                    clients[client_name] = {
                        "id": record.get("id"),
                        "name": client_name,
                        "profession": profession,
                        "location": fields.get("Location", "Remote"),
                        "job_preferences": fields.get("Job Preferences", ""),
                        "email": fields.get("Email Address", ""),
                        "skills": ", ".join(skills_array) if skills_array else "",
                        "last_updated": datetime.now().isoformat()
                    }
                    print(f"DEBUG: Added {client_name} - {profession}")
            
            print(f"DEBUG: Total clients loaded: {len(clients)}")
            return clients
        except Exception as e:
            print(f"Error fetching clients: {e}")
            return {}

def mock_jobs(client_data):
    profession = client_data.get("profession", "Professional")
    location = client_data.get("location", "Remote")
    jobs = []
    for i, company in enumerate(["TechCorp", "BuildCorp", "ServiceCorp"]):
        jobs.append({
            "company_name": company,
            "job_title": f"{profession} Position",
            "job_description": f"Great opportunity for {profession} in {location}",
            "location": location,
            "salary_range": f"${50000 + i*10000} - ${70000 + i*10000}",
            "application_link": f"https://{company.lower()}.com/apply",
            "posted_date": datetime.now().strftime("%Y-%m-%d"),
            "job_type": "Full-time",
            "requirements": f"{profession} experience required"
        })
    return jobs

def generate_excel(client_name, jobs, search_date):
    try:
        results_dir = Path("results")
        results_dir.mkdir(exist_ok=True)
        
        excel_data = []
        for job in jobs:
            excel_data.append({
                "Company Name": job.get("company_name", ""),
                "Job Title": job.get("job_title", ""),
                "Job Description": job.get("job_description", ""),
                "Location": job.get("location", ""),
                "Salary Range": job.get("salary_range", ""),
                "Application Link": job.get("application_link", ""),
                "Applied": "No",
                "Posted Date": job.get("posted_date", ""),
                "Found Date": search_date
            })
        
        df = pd.DataFrame(excel_data)
        safe_name = "".join(c for c in client_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_name}_jobs_{timestamp}.xlsx"
        filepath = results_dir / filename
        
        df.to_excel(filepath, index=False)
        return str(filepath)
    except Exception as e:
        print(f"Excel error: {e}")
        return None

# Initialize
airtable_manager = AirtableManager()

def initialize_system():
    global system_state
    print("🚀 Initializing Job Application Management System...")
    
    system_state["airtable_connected"] = airtable_manager.test_connection()
    if system_state["airtable_connected"]:
        print("✅ Airtable connection successful")
        system_state["clients"] = airtable_manager.get_all_clients()
        print(f"📋 Loaded {len(system_state['clients'])} clients from Airtable")
    else:
        print("⚠️ Airtable connection failed - using mock data")
        system_state["clients"] = {
            "John Smith": {"name": "John Smith", "profession": "Plumber", "location": "New York", "job_preferences": "residential"}
        }

initialize_system()

@app.get("/", response_class=HTMLResponse)
async def get_index():
    return HTMLResponse("""
<!DOCTYPE html>
<html><head><title>Job Application Management</title><style>
body{font-family:Arial;margin:20px;background:#f5f5f5}
.container{max-width:1000px;margin:0 auto;background:white;padding:20px;border-radius:10px}
select,button{width:100%;padding:10px;margin:10px 0;font-size:16px}
button{background:#007bff;color:white;border:none;cursor:pointer;border-radius:5px}
button:disabled{background:#ccc}
.client-info{background:#e7f3ff;padding:15px;margin:10px 0;border-radius:5px;display:none}
.results{background:#f8f9fa;padding:15px;margin:10px 0;border-radius:5px;max-height:400px;overflow-y:auto}
.job-item{border-bottom:1px solid #ddd;padding:10px 0}
.success{background:#d4edda;color:#155724;padding:10px;border-radius:5px;margin:10px 0;display:none}
</style></head><body>
<div class="container">
<h1>🎯 Job Application Management System</h1>
<select id="client-select" onchange="onClientSelect()"><option value="">Choose a client...</option></select>
<div id="client-info" class="client-info"></div>
<button id="search-btn" onclick="launchSearch()" disabled>🚀 Launch Job Search</button>
<div id="success" class="success"></div>
<div id="results" class="results">Select a client and launch search to see results.</div>
</div>

<script>
let clients = {};

async function loadClients() {
    const response = await fetch('/clients');
    const data = await response.json();
    clients = data.clients;
    
    const select = document.getElementById('client-select');
    select.innerHTML = '<option value="">Choose a client...</option>';
    
    Object.keys(clients).forEach(name => {
        const option = document.createElement('option');
        option.value = name;
        option.textContent = `${name} (${clients[name].profession})`;
        select.appendChild(option);
    });
}

function onClientSelect() {
    const name = document.getElementById('client-select').value;
    const info = document.getElementById('client-info');
    const btn = document.getElementById('search-btn');
    
    if (name && clients[name]) {
        const client = clients[name];
        info.innerHTML = `<h4>${client.name}</h4><p><b>Profession:</b> ${client.profession}</p><p><b>Location:</b> ${client.location}</p>`;
        info.style.display = 'block';
        btn.disabled = false;
    } else {
        info.style.display = 'none';
        btn.disabled = true;
    }
}

async function launchSearch() {
    const name = document.getElementById('client-select').value;
    if (!name) return;
    
    const btn = document.getElementById('search-btn');
    const results = document.getElementById('results');
    const success = document.getElementById('success');
    
    btn.disabled = true;
    btn.textContent = '🔄 Searching...';
    results.textContent = 'Searching for jobs...';
    success.style.display = 'none';
    
    try {
        const response = await fetch('/launch-job-search', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({client_name: name})
        });
        
        const data = await response.json();
        
        if (data.success) {
            success.innerHTML = `✅ Found ${data.job_count} jobs! ${data.excel_file ? '<a href="/download/' + encodeURIComponent(data.excel_file) + '">📥 Download Excel</a>' : ''}`;
            success.style.display = 'block';
            
            let html = '';
            data.jobs.forEach(job => {
                html += `<div class="job-item"><h4>${job.job_title}</h4><p><b>${job.company_name}</b> - ${job.location}</p><p>${job.salary_range}</p><a href="${job.application_link}" target="_blank">Apply Now</a></div>`;
            });
            results.innerHTML = html;
        } else {
            results.innerHTML = `❌ Error: ${data.error}`;
        }
    } catch (error) {
        results.innerHTML = `❌ Network error: ${error.message}`;
    }
    
    btn.disabled = false;
    btn.textContent = '🚀 Launch Job Search';
}

loadClients();
</script>
</body></html>
    """)

@app.get("/clients")
async def get_clients():
    return JSONResponse({"clients": system_state["clients"], "count": len(system_state["clients"])})

@app.post("/launch-job-search")
async def launch_job_search(request: Request):
    try:
        data = await request.json()
        client_name = data.get("client_name")
        
        if not client_name or client_name not in system_state["clients"]:
            raise HTTPException(status_code=400, detail="Invalid client")
        
        client_data = system_state["clients"][client_name]
        search_date = datetime.now().isoformat()
        
        print(f"🔍 Starting search for {client_name}")
        jobs = mock_jobs(client_data)
        excel_file = generate_excel(client_name, jobs, search_date)
        
        return JSONResponse({
            "success": True,
            "client_name": client_name,
            "job_count": len(jobs),
            "jobs": jobs,
            "excel_file": os.path.basename(excel_file) if excel_file else None
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = Path("results") / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(str(file_path), filename=filename)

if __name__ == "__main__":
    print("🚀 Starting Job Application Management System...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
