from fastapi import FastAPI, Request, Form, BackgroundTasks, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import uvicorn
import os
import json
import logging
from datetime import datetime
from pathlib import Path

from config import SEOConfig
from utils import setup_logging
from crawler import SEOCrawler
from analyzer import SEOAnalyzer, SEOScorer
from reporter import ReporterFactory

# Initialize FastAPI
app = FastAPI(title="SEO Analyzer")

# Setup Folders
REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)

templates = Jinja2Templates(directory="templates")

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

def run_analysis_task(url: str, depth: int, timestamp: str):
    """Background task to run the full SEO analysis."""
    # Initialize Config manually for this run
    config = SEOConfig()
    config.base_url = url
    config.max_depth = depth
    config.timestamp = timestamp # Important: Override timestamp to keep consistency

    # Setup Output Dir
    if not os.path.exists(config.output_dir):
        os.makedirs(config.output_dir)

    # Initial Status
    update_job_status(config.output_dir, "starting", 5, "Initializing analysis...")

    # Logging
    setup_logging(config.log_file)
    logging.info(f"Starting background analysis for {url}")

    try:
        # 1. Sitemap Discovery
        update_job_status(config.output_dir, "sitemaps", 10, "Scanning for sitemaps...")
        crawler = SEOCrawler(config)
        sitemaps = crawler.discover_sitemaps()

        if sitemaps:
            config.sitemap_url = sitemaps[0] # Use first found as primary
            logging.info(f"Using sitemap: {config.sitemap_url}")

        # 2. Crawl
        update_job_status(config.output_dir, "crawling", 30, f"Crawling {url} (Depth: {depth})...")
        crawl_file = crawler.execute()

        if not crawl_file:
            logging.error("Crawl returned no file.")
            update_job_status(config.output_dir, "failed", 0, "Crawl failed. Check logs.")
            return

        # 3. Analyze
        update_job_status(config.output_dir, "analyzing", 70, "Analyzing SEO metrics...")
        analyzer = SEOAnalyzer(config)
        df = analyzer.load_data(crawl_file)

        if df is None or len(df) == 0:
            logging.error("No data found in crawl file.")
            update_job_status(config.output_dir, "failed", 0, "No data found in crawl.")
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

    except Exception as e:
        logging.exception(f"Fatal error during analysis task: {e}")
        update_job_status(config.output_dir, "failed", 0, f"Error: {str(e)}")


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

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Dashboard showing form and report history."""
    reports = get_reports_list()
    return templates.TemplateResponse("index.html", {"request": request, "reports": reports})

@app.post("/analyze")
async def analyze(url: str = Form(...), depth: int = Form(3), background_tasks: BackgroundTasks = None):
    """Endpoint to trigger a new analysis."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    background_tasks.add_task(run_analysis_task, url, depth, timestamp)
    # Redirect immediately to the report viewer which will poll for status
    return RedirectResponse(url=f"/report/{timestamp}", status_code=303)

@app.get("/api/status/{report_id}")
async def get_report_status(report_id: str):
    """API to poll the status of a running job."""
    status_path = REPORTS_DIR / report_id / "status.json"
    if not status_path.exists():
        # If folder exists but no status, it might be just starting or broken
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
    # Check existence to throw 404 immediately if invalid
    if not (REPORTS_DIR / report_id / "report.json").exists():
        raise HTTPException(status_code=404, detail="Report not found")

    return templates.TemplateResponse("report.html", {"request": request, "report_id": report_id})

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
