# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install in editable (dev) mode
pip install -e .

# Run all tests
pytest

# Run a single test
pytest tests/test_analyzer.py::test_analyzer_happy_path

# Analyze a site (CLI)
python -m seo_check.main analyze https://example.com --depth 2

# Start the web dashboard
python -m seo_check.main serve
# OR with hot reload:
uvicorn seo_check.app:app --reload

# Build distributions
python -m build

# Verify WebSocket connectivity
python src/seo_check/verify_ws_connection.py
```

## Architecture

`seo_check` is a dual-mode Python SEO auditor (CLI + FastAPI web dashboard). The core pipeline is:

**Crawl → Analyze → Score → Report**

1. `SEOCrawler` (`crawler.py`) spawns a **subprocess** (via `crawl_runner.py`) to run an advertools/Scrapy crawl, writing results to a JSON Lines file. The subprocess isolation avoids Twisted reactor restart conflicts.
2. `SEOAnalyzer` (`analyzer.py`) loads the `.jl` file into a pandas DataFrame, runs all check modules, and assembles a nested metrics dict.
3. `SEOScorer` applies penalty thresholds to produce a 0–100 score.
4. `ReporterFactory` (`reporter.py`) emits a JSON report saved under `reports/<timestamp>/`.

### Scoring Fairness Rule
Semantic checks (H1, Title, Meta, Content, etc.) **must** use `df_valid = df[df['status'] == 200]` so that 404/5xx pages don't accumulate semantic penalties on top of HTTP errors. Critical checks (broken links, SSL) run on the full DataFrame. Every new semantic check should follow this pattern.

### Check Modules (`src/seo_check/checks/`)
Each file is a standalone module for one analysis area: `http`, `meta`, `content`, `performance`, `security`, `links`, `social`, `schema`, `structure`. Add new analysis areas here.

### Web App (`app.py`)
FastAPI + Jinja2 + WebSockets. `ConnectionManager` handles WebSocket lifecycle. Analysis jobs run as background tasks; clients poll `/api/status/{report_id}` or listen on `/ws/{report_id}` for real-time updates.

### Configuration (`config.py`)
`SEOConfig` is a dataclass holding all thresholds (title length, word count, slow-page cutoff) and penalty weights. Change scoring sensitivity here, not in `analyzer.py`.

## Code Style

- PEP 8, ~100 char line length, 4-space indent.
- Imports: stdlib → third-party → local, each group alphabetized.
- Type hints required on all functions; docstrings required on all public classes/methods.
- Naming: `PascalCase` classes, `snake_case` functions/vars, `UPPER_CASE` constants, `_prefix` private helpers.
- Use `pathlib.Path` everywhere (not `os.path`).
- Async functions stay async; heavy pandas work goes in `asyncio.to_thread()`.
- Use `logging` (not `print`) in library code; CLI output goes through `rich.console.Console()`.

## Commit Format

`type: description` — e.g., `fix: Handle fairness logic for partially crawled sites`
