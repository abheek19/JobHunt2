import time
import requests
import re
from bs4 import BeautifulSoup

class JobScout:
    """Base class for Job Scouts."""
    def __init__(self, name):
        self.name = name

    def fetch_jobs(self):
        print(f"[{self.name}] Scanning for jobs...")
        try:
            return self.scrape()
        except Exception as e:
            print(f"[{self.name}] Error scraping: {e}")
            return []

    def scrape(self):
        raise NotImplementedError

class IndiaRemoteScout(JobScout):
    def __init__(self):
        super().__init__("Scout A (India Remote & Worldwide API)")
        
    def scrape(self):
        # Using Remotive API which returns actual live jobs
        # We search for python and filter for India or Worldwide
        url = "https://remotive.com/api/remote-jobs?search=python"
        response = requests.get(url, timeout=10)
        jobs_data = response.json().get('jobs', [])
        
        valid_locations = ['india', 'worldwide', 'apac', 'asia']
        
        jobs = []
        for j in jobs_data:
            req_loc = str(j.get('candidate_required_location')).lower()
            if any(loc in req_loc for loc in valid_locations):
                # Clean description (remove HTML tags)
                raw_desc = j.get('description', '')
                clean_desc = BeautifulSoup(raw_desc, "html.parser").get_text()[:500] + "..."
                
                jobs.append({
                    "Company": j.get('company_name', 'Unknown'),
                    "Position": j.get('title', 'Unknown Role'),
                    "Location": "Remote (India)",
                    "Posted Time": j.get('publication_date', 'Recently')[:10],
                    "Source": "Remotive API",
                    "URL": j.get('url', '#'),
                    "Salary": j.get('salary', 'Not Specified'),
                    "Experience Required": clean_desc
                })
                
        # Limit to 5 so we don't spam the Gemini API
        return jobs[:5]

def run_all_scouts():
    """Runs all specialized scouts and aggregates results."""
    # We only run India-specific scouts to strictly adhere to the requirement
    scouts = [IndiaRemoteScout()]
    all_jobs = []
    for scout in scouts:
        try:
            jobs = scout.fetch_jobs()
            all_jobs.extend(jobs)
        except Exception as e:
            print(f"Error running {scout.name}: {e}")
    return all_jobs
