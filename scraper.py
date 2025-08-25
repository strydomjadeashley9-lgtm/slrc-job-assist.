import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd

# Load environment variables from scraper.env ONLY
load_dotenv(dotenv_path="scraper.env", override=True)

# Grab environment variables
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

LOG_FILE = "scraper.log"


def log(message: str):
    """Append logs to scraper.log with timestamp."""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()} - {message}\n")


def run_scraper(query: str, location: str = "New Zealand"):
    """
    Run a Google Jobs scraper via SerpAPI.
    Returns job results as a list of dicts.
    """
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_jobs",
        "q": f"{query} {location}",
        "hl": "en",
        "api_key": GOOGLE_API_KEY
    }

    log(f"Running scraper for query: {query} in {location}")
    print(f"🔍 Searching jobs for: {query} in {location} ...")

    jobs = []

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()

        results = response.json()
        log("Raw API response:\n" + json.dumps(results, indent=2))

        jobs = results.get("jobs_results", [])
        log(f"Found {len(jobs)} jobs for query: {query}")

    except Exception as e:
        log(f"Error during scraping: {e}")
        print(f"⚠️ Error during scraping: {e}")

    return jobs


def save_jobs_to_csv(jobs: list, filename="jobs.csv"):
    """
    Save scraped jobs to a CSV file.
    Appends new jobs and skips duplicates (based on Application Weblink).
    """
    if not jobs:
        print("⚠️ No jobs to save.")
        return

    new_df = pd.DataFrame([
        {
            "Job Title": job.get("title"),
            "Company Name": job.get("company_name"),
            "Application Weblink": job.get("job_apply_link"),
            "Location": job.get("location")
        }
        for job in jobs
    ])

    # If file exists, merge and drop duplicates
    if os.path.exists(filename):
        old_df = pd.read_csv(filename)
        combined = pd.concat([old_df, new_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=["Application Weblink"], keep="first")
        combined.to_csv(filename, index=False)
        added = len(combined) - len(old_df)
        print(f"✅ Added {added} new jobs (skipped duplicates). Total: {len(combined)}")
    else:
        new_df.to_csv(filename, index=False)
        print(f"✅ Saved {len(new_df)} jobs to {filename}")


if __name__ == "__main__":
    print("DEBUG: Using SerpAPI key:", GOOGLE_API_KEY)  # confirm key in use
    query = input("Enter job search query (e.g., plumber): ")
    jobs = run_scraper(query)
    save_jobs_to_csv(jobs)
