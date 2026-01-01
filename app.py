from fastapi import FastAPI, Request, Form, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from config import SEOConfig
from utils import setup_logging
from crawler import SEOCrawler
from analyzer import SEOAnalyzer, SEOScorer
from reporter import ReporterFactory

# Initialize FastAPI
app = FastAPI(title="SEO Analyzer")

# Add CORS Middleware to allow WebSocket connections from any origin (e.g. 0.0.0.0)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Folders
REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)

templates = Jinja2Templates(directory="templates")

# --- WebSocket Manager ---
class ConnectionManager:
    def __init__(self):
        # map report_id -> list of websockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, report_id: str):
        await websocket.accept()
        if report_id not in self.active_connections:
            self.active_connections[report_id] = []
        self.active_connections[report_id].append(websocket)

    def disconnect(self, websocket: WebSocket, report_id: str):
        if report_id in self.active_connections:
            if websocket in self.active_connections[report_id]:
                self.active_connections[report_id].remove(websocket)
            if not self.active_connections[report_id]:
                del self.active_connections[report_id]

    async def broadcast(self, message: dict, report_id: str):
        if report_id in self.active_connections:
            for connection in self.active_connections[report_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass

manager = ConnectionManager()

# --- Service Logic ---

def update_job_status(output_dir, stage, percent, message):
    """Updates the status.json file for the frontend poller."""
    status_file = os.path.join(output_dir, "status.json")
    data = {
        "stage": stage,
        "percent": percent,
        "message": message,
        "updated_at": str(datetime.now())
    }
    with open(status_file, 'w') as f:
        json.dump(data, f)

async def run_analysis_task(url: str, depth: int, timestamp: str):
    """Background task to run the full SEO analysis."""
    # Initialize Config manually for this run
    config = SEOConfig()
    config.base_url = url
    config.max_depth = depth
    config.timestamp = timestamp

    # Setup Output Dir
    if not os.path.exists(config.output_dir):
        os.makedirs(config.output_dir)

    # Initial Status
    update_job_status(config.output_dir, "starting", 5, "Initializing analysis...")
    await manager.broadcast({"type": "log", "message": "Initializing analysis..."}, timestamp)

    # Logging
    setup_logging(config.log_file)
    logging.info(f"Starting background analysis for {url}")

    try:
        # 1. Sitemap Discovery
        update_job_status(config.output_dir, "sitemaps", 10, "Scanning for sitemaps...")
        await manager.broadcast({"type": "log", "message": "Scanning for sitemaps..."}, timestamp)

        crawler = SEOCrawler(config)
        sitemaps = crawler.discover_sitemaps()

        if sitemaps:
            config.sitemap_url = sitemaps[0]
            logging.info(f"Using sitemap: {config.sitemap_url}")
            await manager.broadcast({"type": "log", "message": f"Found sitemap: {config.sitemap_url}"}, timestamp)

        # 2. Crawl
        update_job_status(config.output_dir, "crawling", 30, f"Crawling {url} (Depth: {depth})...")
        await manager.broadcast({"type": "log", "message": f"Starting crawl of {url} (Depth: {depth})"}, timestamp)

        # We pass the manager and timestamp to execute to stream updates
        crawl_file = await crawler.execute(manager, timestamp)

        if not crawl_file:
            logging.error("Crawl returned no file.")
            update_job_status(config.output_dir, "failed", 0, "Crawl failed. Check logs.")
            await manager.broadcast({"type": "error", "message": "Crawl failed."}, timestamp)
            return

        # 3. Analyze
        update_job_status(config.output_dir, "analyzing", 70, "Analyzing SEO metrics...")
        await manager.broadcast({"type": "log", "message": "Processing data..."}, timestamp)

        analyzer = SEOAnalyzer(config)
        df = analyzer.load_data(crawl_file)

        if df is None or len(df) == 0:
            logging.error("No data found in crawl file.")
            update_job_status(config.output_dir, "failed", 0, "No data found in crawl.")
            await manager.broadcast({"type": "error", "message": "No data found."}, timestamp)
            return

        metrics = analyzer.analyze(df)

        # Add sitemaps to metrics for reporting
        metrics['sitemaps'] = sitemaps

        # 4. Score
        scorer = SEOScorer(config)
        score, rating, penalties = scorer.calculate(metrics)

        # 5. Report (Force JSON for Web View)
        update_job_status(config.output_dir, "reporting", 90, "Generating report...")
        config.output_format = 'json'
        reporter = ReporterFactory.create_reporter(config, metrics, score, rating, penalties)
        reporter.generate()

        update_job_status(config.output_dir, "completed", 100, "Analysis complete!")
        logging.info("Analysis completed successfully.")
        await manager.broadcast({"type": "complete", "message": "Analysis finished!"}, timestamp)

    except Exception as e:
        logging.exception(f"Fatal error during analysis task: {e}")
        update_job_status(config.output_dir, "failed", 0, f"Error: {str(e)}")
        await manager.broadcast({"type": "error", "message": f"Error: {str(e)}"}, timestamp)


def get_reports_list():
    """Scans the reports directory for generated JSON reports."""
    reports = []
    if not REPORTS_DIR.exists():
        return reports

    for item in sorted(REPORTS_DIR.iterdir(), reverse=True):
        if item.is_dir():
            json_path = item / "report.json"
            if json_path.exists():
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        reports.append({
                            'id': item.name,
                            'date': data['meta']['generated_at'],
                            'url': data['meta']['target_url'],
                            'score': data['summary']['score'],
                            'rating': data['summary']['rating'],
                            'pages': data['summary']['total_pages']
                        })
                except Exception:
                    continue # Skip broken reports
    return reports

# --- Routes ---

@app.websocket("/ws/{report_id}")
async def websocket_endpoint(websocket: WebSocket, report_id: str):
    await manager.connect(websocket, report_id)
    try:
        while True:
            # Just keep connection open to send messages from server
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, report_id)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Dashboard showing form and report history."""
    reports = get_reports_list()
    return templates.TemplateResponse("index.html", {"request": request, "reports": reports})

@app.post("/analyze")
async def analyze(url: str = Form(...), depth: int = Form(3), background_tasks: BackgroundTasks = None):
    """Endpoint to trigger a new analysis."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Using asyncio.create_task instead of BackgroundTasks because we need to await broadcast inside it
    # But FastAPI BackgroundTasks are not awaitable.
    # We will use a wrapper or just fire and forget loop.create_task
    # Note: For production properly, use Celery/Redis. For this scope, create_task is fine.
    asyncio.create_task(run_analysis_task(url, depth, timestamp))

    return RedirectResponse(url=f"/report/{timestamp}", status_code=303)

@app.get("/api/status/{report_id}")
async def get_report_status(report_id: str):
    """API to poll the status of a running job."""
    status_path = REPORTS_DIR / report_id / "status.json"
    if not status_path.exists():
        if (REPORTS_DIR / report_id).exists():
            return JSONResponse({"stage": "starting", "percent": 0, "message": "Initializing..."})
        raise HTTPException(status_code=404, detail="Analysis not found")

    with open(status_path, 'r') as f:
        return JSONResponse(json.load(f))

@app.get("/api/reports/{report_id}")
async def get_report_json(report_id: str):
    """API to fetch the JSON data for a specific report."""
    file_path = REPORTS_DIR / report_id / "report.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return JSONResponse(content=data)

@app.get("/report/{report_id}", response_class=HTMLResponse)
async def view_report(request: Request, report_id: str):
    """Render the report viewer page."""
    if not (REPORTS_DIR / report_id).exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return templates.TemplateResponse("report.html", {"request": request, "report_id": report_id})

# --- New Detail Views ---

@app.get("/report/{report_id}/issue/{issue_name}", response_class=HTMLResponse)
async def view_issue_detail(request: Request, report_id: str, issue_name: str):
    """Render the issue details table."""
    file_path = REPORTS_DIR / report_id / "report.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Find the specific issue
    target_issue = None
    all_issues = data['metrics']['issues']['errors'] + \
                 data['metrics']['issues']['warnings'] + \
                 data['metrics']['issues']['notices']

    # Decode URL safe name if needed, but for now simple matching
    # issue_name coming from URL might need decoding
    from urllib.parse import unquote
    issue_name = unquote(issue_name)

    for issue in all_issues:
        if issue['name'] == issue_name:
            target_issue = issue
            break

    if not target_issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    return templates.TemplateResponse("issue_detail.html", {
        "request": request,
        "report_id": report_id,
        "issue": target_issue,
        "report_date": data['meta']['generated_at']
    })

@app.get("/report/{report_id}/page", response_class=HTMLResponse)
async def view_page_detail(request: Request, report_id: str, url: str):
    """Render the single page analysis."""
    file_path = REPORTS_DIR / report_id / "report.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    page_data = data['metrics']['page_details'].get(url)
    if not page_data:
        raise HTTPException(status_code=404, detail="Page not found in report")

    # Pass Config thresholds for comparison logic
    config = SEOConfig()
    return templates.TemplateResponse("page_detail.html", {
        "request": request,
        "report_id": report_id,
        "url": url,
        "data": page_data,
        "config": config
    })

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
