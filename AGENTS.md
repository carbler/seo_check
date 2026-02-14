# AGENTS.md

> **Purpose:** This file guides AI agents and developers working on the `seo_check` repository. It defines the approved workflow, commands, and style norms required to ship reliable SEO reporting.

## 1. Project Context
`seo_check` is a dual-mode Python application (CLI + Web) built for comprehensive SEO auditing.
- **CLI:** Interactive terminal experience powered by `rich`, supporting crawls, reporting, and scoring.
- **Web:** FastAPI + Jinja2 dashboard that streams crawl reports via WebSockets.
- **Core Stack:** `advertools`/Scrapy for crawling, `pandas` for analysis, `FastAPI`/`uvicorn` for serving dashboards.

## 2. Environment & Commands

### Setup & Dependencies
All work happens from the repository root. Install runtime dependencies in editable mode:
```bash
pip install -e .
```
For development, ensure `pytest`, `httpx`, and other extras referenced in `pyproject.toml` are installed.

### CLI vs Web Modes
**CLI mode** exposes `python -m seo_check.main analyze <URL>` plus a `serve` command for lightweight dashboards.
```bash
# Analyze a site
python -m seo_check.main analyze https://example.com --depth 2

# View help
python -m seo_check.main --help
```

**Web server mode** launches the FastAPI renderer. Use hot reload locally:
```bash
# Serve the dashboard
python -m seo_check.main serve
# OR direct uvicorn launch
uvicorn seo_check.app:app --reload
```

### Build & Packaging
Packaging uses the `pyproject.toml` metadata (setuptools + wheel).
```bash
python -m build
```
Verify the generated distributions in `dist/` before tagging a release.

### Testing
Pytest is the testing framework. Configuration in `pyproject.toml` applies `-v --tb=short`.

**Run all tests:**
```bash
pytest
```

**Run a specific test file:**
```bash
pytest tests/test_analyzer.py
```

**Run a single test case (Critical for targeted debugging):**
```bash
pytest tests/test_analyzer.py::test_analyzer_happy_path
```

**Test Categories:**
- **Unit:** `tests/test_analyzer.py` (Mocks DataFrames to test logic without crawling)
- **Integration:** `tests/test_cli.py` (Tests CLI arguments and outputs)
- **Service:** `tests/test_integrations.py` (Tests external API integrations)

### Manual Verification
For verifying WebSocket connectivity without a browser, use the included utility script:
```bash
python src/seo_check/verify_ws_connection.py
```

## 3. Code Style & Guidelines

### Linting & Formatting
No automated linter or formatter is enforced in CI, but the repository follows strict **PEP 8** conventions.
- **Indentation:** 4 spaces per level, no tabs.
- **Line length:** Favor readability (~100 char max). Use implicit continuations for longer structures.
- **Imports:** Must be grouped in 3 blocks and alphabetized within each group:
  1. Standard Library (`import json`, `import logging`)
  2. Third-Party (`import pandas as pd`, `import uvicorn`)
  3. Local Application (`from .config import SEOConfig`, `from .utils import to_list`)

### Type Hints & Documentation
- **Typing:** Mandatory for all functions and methods. Use `typing` generics (`List`, `Dict`, `Optional`, `Any`) or built-ins (`list`, `dict`) consistently.
  ```python
  def calculate_score(self, metrics: Dict[str, Any]) -> Tuple[float, str]:
      ...
  ```
- **Docstrings:** Required for every public class and method. Describe responsibilities, arguments, and return format.
  ```python
  def load_data(self, crawl_file: str) -> pd.DataFrame:
      """Loads crawl data JSON lines into a DataFrame."""
  ```

### Naming Conventions
- Classes: `PascalCase` (`SEOAnalyzer`, `ReporterFactory`).
- Functions/methods/variables: `snake_case` (`analyze_http_status`, `broken_links`).
- Constants: `UPPER_CASE` with descriptive names (`DEFAULT_TIMEOUT`).
- Private helpers: prefixed with `_` (`_categorize_issues`).

### Error Handling & Logging
- Use `logging` instead of `print` in library code. Log exceptions with context.
  ```python
  try:
      df = pd.read_json(crawl_file, lines=True)
  except Exception as e:
      logging.error(f"Error loading data: {e}", exc_info=True)
      return pd.DataFrame()
  ```
- CLI feedback is rendered through `rich.console.Console()` for consistent colors/status.
- Catch only specific exceptions you can remediate; bubble others to the CLI/web layer.

### Async vs Blocking
- Async functions (crawler, FastAPI) must stay async.
- Heavy Pandas workloads run inside `asyncio.to_thread` to avoid blocking the event loop.
- Keep blocking operations within sync helpers to avoid thread starvation.

## 4. Architecture & Patterns

### Directory Layout
- `src/seo_check/`: application code.
  - `main.py`: CLI entry.
  - `app.py`: FastAPI/Jinja2 dashboard.
  - `crawler.py`: Async crawl orchestrator.
  - `analyzer.py`: Pandas-based metrics and scoring.
  - `reporter.py`: JSON/HTML report generation.
  - `checks/`: domain-specific analyzers (meta, schema, performance, etc.).

### Data Flow
1. Input via CLI or Web request.
2. `SEOCrawler` writes a JSON Lines crawl file.
3. `SEOAnalyzer` loads the file, runs check modules, and organizes metrics by area.
4. `SEOScorer` applies thresholds + fairness offsets to compute a 0-100 score.
5. `ReporterFactory` emits JSON/HTML for CLI output or the `/report/<id>` endpoint.

### Scoring Fairness (Analyzer)
- The analyzer filters the crawl data (`df_valid = df[df['status'] == 200]`) before running semantic checks (H1, Titles, Meta, Content, etc.).
- This ensures that 404/5xx pages do not trigger semantic penalties (missing titles, H1, metadata, etc.), preventing "double jeopardy" where a broken page is penalized twice.
- **Rule:** When adding new semantic checks, ensure they use `df_valid` unless they specifically need to analyze broken pages.
- Critical penalties (broken links, SSL invalidity) remain separate and are calculated on the full dataset.

## 5. File System Practices
- Favor `pathlib.Path` over `os.path`.
- Report/state files live under `reports/<timestamp>/`; CLI/web share the same structure.
- Always confirm the parent directory exists before writing using `path.parent.mkdir(parents=True, exist_ok=True)`.

## 6. Release & Commit Workflow
- **Changes:** Run `git status` and `git diff` before staging.
- **Commits:** One commit per logical change. Message format: `type: description` (e.g., `fix: Handle fairness logic for partially crawled sites`).
- **Versioning:** Tag the branch with semantic versioning (e.g., `v0.1.3`) for production releases.
- **Verification:** Before pushing, run the relevant tests. Never push broken code to `main`.
- **Security:** Never commit secrets, API keys, or generated artifacts (`*.pyc`, `dist/`).

## 7. Cursor & Copilot Rules
- There are no `.cursor` or `.cursorrules/` directives in this repository.
- No `.github/copilot-instructions.md` exists; default to best practices noted here.
