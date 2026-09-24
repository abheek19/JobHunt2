import os
import schedule
import time
from manager import JobHuntManager
from scouts import run_all_scouts
from agents import JobFilter, CompanyInvestigator, ApplicationTailor, NetworkScout

def load_data(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
    return ""

def process_pipeline():
    print(f"\n--- Starting Pipeline Run at {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
    manager = JobHuntManager()
    filter_agent = JobFilter()
    investigator_agent = CompanyInvestigator()
    tailor_agent = ApplicationTailor()
    network_agent = NetworkScout()
    
    cvs = manager.get_all_cvs()
    if not cvs:
        print("No CVs found in database. Please upload a CV first.")
        return

    # Step 1: Discover Jobs
    print("Step 1: Running Job Scouts...")
    raw_jobs = run_all_scouts()
    manager.add_discovered_jobs(raw_jobs)
    
    # Step 2: Filter Jobs
    pending_jobs = manager.get_jobs_by_status("DISCOVERED")
    print(f"Step 2: Filtering {len(pending_jobs)} jobs against {len(cvs)} CVs...")
    
    for job in pending_jobs:
        job_id = job['id']
        highest_score = 0
        best_classification = "REJECT"
        best_cv_text = ""
        
        for cv in cvs:
            cv_text = cv['content']
            cv_id = cv['id']
            # We use an empty string for preferences for now
            evaluation = filter_agent.evaluate(str(job), cv_text, "")
            
            lines = evaluation.strip().split('\n')
            classification = "REJECT"
            score = 0
            reasoning = evaluation
            
            for line in lines:
                if line.startswith("CLASSIFICATION:"):
                    classification = line.replace("CLASSIFICATION:", "").strip().upper()
                elif line.startswith("SCORE:"):
                    try:
                        score = int(line.replace("SCORE:", "").strip())
                    except:
                        pass
            
            status = "SCREENED"
            if "HIGH MATCH" in classification:
                status = "HIGH MATCH AWAITING RESEARCH"
            
            manager.add_or_update_match(job_id, cv_id, score, status, reasoning)
            
            if score > highest_score:
                highest_score = score
                best_classification = classification
                best_cv_text = cv_text
        
        print(f"[{job_id}] Highest Match: {best_classification} ({highest_score}/100)")
        
        # Advance the job status in the main jobs table if it's a high match overall
        if "HIGH MATCH" in best_classification:
            manager.update_job_status(job_id, "HIGH MATCH AWAITING RESEARCH")
            manager.trigger_high_match_alert(job_id, best_cv_text)
        elif "POSSIBLE MATCH" in best_classification:
            manager.update_job_status(job_id, "SCREENED")
        else:
            manager.update_job_status(job_id, "REJECTED")

    # Step 3-5: Process HIGH MATCH jobs
    high_match_jobs = manager.get_jobs_by_status("HIGH MATCH AWAITING RESEARCH")
    print(f"Step 3: Researching {len(high_match_jobs)} High Match Jobs...")
    
    for job in high_match_jobs:
        job_id = job['id']
        print(f"[{job_id}] Investigating Company...")
        # (Simplified: just using the first CV for drafting, but ideally it should use best_cv)
        best_cv_text = cvs[0]['content'] if cvs else ""
        
        research = investigator_agent.research(str(job))
        manager.save_research(job_id, research)
        
        print(f"[{job_id}] Tailoring Application...")
        tailored_content = tailor_agent.draft(str(job), best_cv_text, research)
        
        manager.save_drafts(job_id, tailored_content, "Cover letter included in draft above.")
        
        print(f"[{job_id}] Scouting Network Connections...")
        # Mock network scout
        # connections = network_agent.find_contacts(str(job), research)
        
        manager.update_job_status(job_id, "APPLICATION READY (AWAITING APPROVAL)")
        print(f"[{job_id}] Prepared and ready for review!")

    print("--- Pipeline Run Complete ---\n")

def run_scheduler():
    """Background task to run the pipeline every 4 hours."""
    # schedule.every(4).hours.do(process_pipeline)
    schedule.every(2).minutes.do(process_pipeline) # For testing
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    # If run directly, run once immediately then start schedule
    process_pipeline()
    run_scheduler()
