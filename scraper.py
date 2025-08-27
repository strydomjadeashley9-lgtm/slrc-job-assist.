import requests
import os
from datetime import datetime

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

def run_scraper(query: str):
    """Fetch jobs from SerpAPI Google Jobs API"""
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_jobs",
        "q": query,
        "hl": "en",
        "gl": "nz",  # force New Zealand
        "api_key": GOOGLE_API_KEY
    }
    res = requests.get(url, params=params, timeout=20)
    if res.status_code != 200:
        return []
    results = res.json().get("jobs_results", [])
    jobs = []
    for r in results:
        jobs.append({
            "company": r.get("company_name", ""),
            "title": r.get("title", ""),
            "location": r.get("location", ""),
            "link": r.get("apply_link", ""),
            "date": r.get("detected_extensions", {}).get("posted_at", datetime.now().strftime("%Y-%m-%d"))
        })
    return jobs
