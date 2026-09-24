import sqlite3
import os
from datetime import datetime
from notifications import NotificationManager

class JobHuntManager:
    """Manages the SQLite database for CVs, Jobs, and Matches."""
    
    def __init__(self, db_path="jobhunt.db"):
        self.db_path = db_path
        self.notifier = NotificationManager()
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create CVs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cvs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                content TEXT,
                upload_time TEXT
            )
        ''')
        
        # Create Jobs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                company TEXT,
                position TEXT,
                location TEXT,
                posted_time TEXT,
                source TEXT,
                url TEXT,
                description TEXT,
                salary TEXT,
                status TEXT DEFAULT 'DISCOVERED'
            )
        ''')
        
        # Create Job Matches table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS job_matches (
                job_id TEXT,
                cv_id INTEGER,
                match_score INTEGER DEFAULT 0,
                status TEXT DEFAULT 'PENDING',
                reasoning TEXT,
                PRIMARY KEY (job_id, cv_id),
                FOREIGN KEY (job_id) REFERENCES jobs(id),
                FOREIGN KEY (cv_id) REFERENCES cvs(id)
            )
        ''')
        
        conn.commit()
        conn.close()

    def add_cv(self, filename, content):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        
        # Discard previous CVs to only keep the latest
        cursor.execute("DELETE FROM cvs")
        cursor.execute("DELETE FROM job_matches") # Reset matches since the CV changed
        
        cursor.execute(
            "INSERT INTO cvs (filename, content, upload_time) VALUES (?, ?, ?)",
            (filename, content, now)
        )
        conn.commit()
        conn.close()

    def get_all_cvs(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cvs ORDER BY upload_time DESC")
        cvs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return cvs

    def add_discovered_jobs(self, raw_jobs):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y%m%d%H%M%S")
        
        for idx, job in enumerate(raw_jobs):
            job_id = f"JOB_{now}_{idx}"
            try:
                cursor.execute('''
                    INSERT INTO jobs (id, company, position, location, posted_time, source, url, description, salary, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    job_id, job.get('Company', ''), job.get('Position', ''),
                    job.get('Location', ''), job.get('Posted Time', ''),
                    job.get('Source', ''), job.get('URL', ''),
                    job.get('Experience Required', ''), job.get('Salary', ''),
                    'DISCOVERED'
                ))
            except sqlite3.IntegrityError:
                pass # Job might already exist
        conn.commit()
        conn.close()

    def get_jobs_by_status(self, status):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE status = ?", (status,))
        jobs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jobs

    def get_all_jobs(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Join with job_matches to get the highest score for the job if it exists
        cursor.execute('''
            SELECT j.*, 
                   MAX(m.match_score) as "Match Score", 
                   MAX(m.status) as match_status 
            FROM jobs j 
            LEFT JOIN job_matches m ON j.id = m.job_id 
            GROUP BY j.id
            ORDER BY j.posted_time DESC
        ''')
        jobs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        # Override job status with match_status if it exists and is more advanced
        for job in jobs:
            if job['match_status'] and job['match_status'] != 'PENDING':
                job['Status'] = job['match_status']
            else:
                job['Status'] = job['status']
                
            # Formatting for frontend
            job['Company'] = job['company']
            job['Position'] = job['position']
            job['Location'] = job['location']
            job['URL'] = job['url']
            job['Salary'] = job['salary']
            job['Experience Required'] = job['description']
            
        return jobs

    def update_job_status(self, job_id, status):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
        conn.commit()
        conn.close()

    def add_or_update_match(self, job_id, cv_id, match_score, status, reasoning):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO job_matches (job_id, cv_id, match_score, status, reasoning) 
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(job_id, cv_id) DO UPDATE SET 
            match_score=excluded.match_score, 
            status=excluded.status, 
            reasoning=excluded.reasoning
        ''', (job_id, cv_id, match_score, status, reasoning))
        conn.commit()
        conn.close()

    def save_drafts(self, job_id, draft_cv, cover_letter):
        # We can just store these as files in data/drafts/ for simplicity, 
        # or update the jobs table. Let's use files to avoid DB bloat.
        os.makedirs("data/drafts", exist_ok=True)
        with open(f"data/drafts/{job_id}_cv.md", "w", encoding='utf-8') as f:
            f.write(draft_cv)
        with open(f"data/drafts/{job_id}_cl.md", "w", encoding='utf-8') as f:
            f.write(cover_letter)

    def save_research(self, job_id, research_data):
        os.makedirs("data/drafts", exist_ok=True)
        with open(f"data/drafts/{job_id}_research.md", "w", encoding='utf-8') as f:
            f.write(research_data)

    def trigger_high_match_alert(self, job_id, cv_text):
        admin_number = os.getenv("ADMIN_MOBILE_NUMBER")
        if admin_number:
            self.notifier.send_sms(admin_number, f"🔥 HIGH MATCH ALERT: Job {job_id} matches highly! Check dashboard.")
            
        contact_info = self.notifier.extract_contacts_from_cv(cv_text)
        email = contact_info.get("email")
        if email:
            self.notifier.send_email(
                email,
                "High Match Job Discovered!",
                f"We found a High Match for you! Check your dashboard for Job ID: {job_id}"
            )
