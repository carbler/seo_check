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
app = FastAPI(title="TuWorker SEO Analyzer")

# Setup Folders
REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- Service Logic ---

def run_analysis_task(url: str, depth: int):
    """Background task to run the full SEO analysis."""
    # Create specific timestamp for this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Initialize Config manually for this run
    config = SEOConfig()
    config.base_url = url
    config.max_depth = depth
    config.timestamp = timestamp # Important: Override timestamp to keep consistency

    # Ensure sitemap
    if not config.sitemap_url and url:
        config.sitemap_url = url.rstrip('/') + '/sitemap.xml'

    # Setup Output Dir
    if not os.path.exists(config.output_dir):
        os.makedirs(config.output_dir)

    # Logging
    setup_logging(config.log_file)
    logging.info(f"Starting background analysis for {url}")

    try:
        # 1. Crawl
        crawler = SEOCrawler(config)
        crawl_file = crawler.execute()

        if not crawl_file:
            logging.error("Crawl returned no file.")
            return

        # 2. Analyze
        analyzer = SEOAnalyzer(config)
        df = analyzer.load_data(crawl_file)

        if df is None or len(df) == 0:
            logging.error("No data found in crawl file.")
            return

        metrics = analyzer.analyze(df)

        # 3. Score
        scorer = SEOScorer(config)
        score, rating, penalties = scorer.calculate(metrics)

        # 4. Report (Force JSON for Web View)
        config.output_format = 'json'
        reporter = ReporterFactory.create_reporter(config, metrics, score, rating, penalties)
        reporter.generate()

        logging.info("Analysis completed successfully.")

    except Exception as e:
        logging.exception(f"Fatal error during analysis task: {e}")


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
    background_tasks.add_task(run_analysis_task, url, depth)
    return RedirectResponse(url="/?status=started", status_code=303)

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
