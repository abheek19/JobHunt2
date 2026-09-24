import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from fastapi import FastAPI, BackgroundTasks, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import shutil

from manager import JobHuntManager
from main import process_pipeline

app = FastAPI(title="JobHunt Dashboard API")

# Serve static files (HTML, JS, CSS)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_dashboard():
    return FileResponse("static/index.html")

@app.get("/api/jobs")
def get_jobs():
    manager = JobHuntManager()
    jobs = manager.get_all_jobs()
    return {"jobs": jobs}

@app.get("/api/cvs")
def get_cvs():
    manager = JobHuntManager()
    cvs = manager.get_all_cvs()
    # Don't send full content to frontend, just metadata
    cv_list = [{"id": cv["id"], "filename": cv["filename"], "upload_time": cv["upload_time"]} for cv in cvs]
    return {"cvs": cv_list}

@app.get("/api/job/{job_id}/draft")
def get_draft(job_id: str):
    """Returns tailored CV and CL if available."""
    try:
        with open(f"data/drafts/{job_id}_cv.md", "r", encoding='utf-8') as f:
            cv = f.read()
        with open(f"data/drafts/{job_id}_cl.md", "r", encoding='utf-8') as f:
            cl = f.read()
        return {"status": "success", "cv": cv, "cover_letter": cl}
    except Exception as e:
        return {"status": "error", "message": "Drafts not found."}

@app.post("/api/trigger")
def trigger_pipeline(background_tasks: BackgroundTasks):
    """Manually triggers the job hunting pipeline in the background."""
    background_tasks.add_task(process_pipeline)
    return {"status": "success", "message": "Pipeline triggered successfully."}

@app.post("/api/upload_cv")
async def upload_cv(file: UploadFile = File(...)):
    """Accepts a CV file and saves it to the SQLite database."""
    try:
        content_bytes = await file.read()
        # Decode text (ignoring errors for non-text files to prevent crashes)
        content = content_bytes.decode('utf-8', errors='ignore')
        manager = JobHuntManager()
        manager.add_cv(file.filename, content)
        return {"status": "success", "message": "CV Uploaded and Saved to Database successfully."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
