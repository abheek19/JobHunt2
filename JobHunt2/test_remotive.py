import requests
response = requests.get("https://remotive.com/api/remote-jobs?search=python")
jobs = response.json().get('jobs', [])
india_jobs = [j for j in jobs if 'india' in str(j.get('candidate_required_location')).lower() or j.get('candidate_required_location') == 'Worldwide']
print("Total remote Python jobs:", len(jobs))
print("Available in India:", len(india_jobs))
if india_jobs:
    print(india_jobs[0]['title'], india_jobs[0]['company_name'])
