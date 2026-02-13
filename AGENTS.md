# AGENTS.md

> **Purpose:** This file guides AI agents and developers working on the `seo_check` repository. It defines standard commands, code style, and architectural patterns to ensure consistency.

## 1. Project Context
`seo_check` is a dual-mode Python application (CLI & Web) for comprehensive SEO auditing.
- **CLI:** Interactive terminal interface powered by `rich`.
- **Web:** Dashboard powered by `FastAPI`, `Jinja2`, and `WebSockets`.
- **Core Stack:** `advertools` (crawling), `pandas` (data processing), `uvicorn` (server).

## 2. Environment & Commands

### Setup
Ensure you are in the project root.
```bash
# Install package in editable mode
pip install -e .
```

### Running the Application
**CLI Mode:**
```bash
# Analyze a URL
python -m seo_check.main analyze https://example.com --depth 2

# Show help
python -m seo_check.main --help
```

**Web Server Mode:**
```bash
# Start server
python -m seo_check.main serve

# Development (with auto-reload)
uvicorn seo_check.app:app --reload
```

### Testing
We use `pytest` for all testing. Ensure `pytest` is installed (`pip install pytest`).

```bash
# Run all tests
pytest

# Run a specific test file
pytest tests/test_analyzer.py

# Run a specific test function
pytest tests/test_analyzer.py::test_analyzer_happy_path

# Run with output capture disabled (to see prints)
pytest -s

# Run verbose
pytest -v
```

### Linting & Formatting
No formal linter config is present, but strict adherence to **PEP 8** is required.
- **Imports:** Grouped and sorted:
  1. Standard Library (`os`, `sys`, `typing`)
  2. Third-party (`pandas`, `fastapi`, `rich`)
  3. Local Application (`.config`, `.utils`)
- **Indentation:** 4 spaces.

## 3. Code Style & Guidelines

### Type Hints & Documentation
- **Typing:** Mandatory for function signatures. Use `typing` module (`List`, `Dict`, `Optional`, `Any`).
  ```python
  def calculate_score(self, metrics: Dict[str, Any]) -> Tuple[float, str]:
      ...
  ```
- **Docstrings:** Required for classes and methods. Explain *what* it does and *return* values.
  ```python
  def load_data(self, file_path: str) -> pd.DataFrame:
      """Loads crawl data from JSON lines file into a DataFrame."""
      ...
  ```

### Naming Conventions
- **Classes:** `PascalCase` (e.g., `SEOAnalyzer`, `PageSpeedTest`).
- **Functions/Methods:** `snake_case` (e.g., `analyze_headers`, `get_status`).
- **Variables:** `snake_case` (e.g., `page_count`, `broken_links`).
- **Private Methods:** Prefix with `_` (e.g., `_process_images`).
- **Constants:** `UPPER_CASE` (e.g., `DEFAULT_TIMEOUT`, `MAX_RETRIES`).

### Error Handling & Logging
- **Logging:** Use the `logging` module. Do **not** use `print` for debug/error info in library code.
  ```python
  import logging
  logging.error(f"Failed to fetch {url}: {e}")
  ```
- **CLI Output:** Use `rich.console.Console` for user feedback in CLI commands.
  ```python
  from rich.console import Console
  console = Console()
  console.print("[green]Success![/green]")
  ```
- **Exceptions:** Catch specific exceptions where possible. Fail gracefully in the Analyzer (return empty/default metrics) rather than crashing the entire report generation.

## 4. Architecture & Patterns

### Directory Structure
- `src/seo_check/`: Main package.
  - `main.py`: CLI entry point.
  - `app.py`: FastAPI web application.
  - `crawler.py`: Crawling logic (async).
  - `analyzer.py`: Data analysis logic (Pandas).
  - `scorer.py`: Scoring algorithm.
  - `reporter.py`: Report generation (JSON/HTML).
  - `templates/`: Jinja2 templates for web view.

### Async vs Sync
- **FastAPI & Crawler:** Use `async/await`.
- **Pandas/Analysis:** Synchronous/blocking.
- **Bridge:** When calling heavy blocking code (like `analyzer.analyze`) from an async endpoint, use `asyncio.to_thread`.
  ```python
  df = await asyncio.to_thread(analyzer.load_data, file_path)
  ```

### Data Flow
1. **Input:** URL + Options.
2. **Crawl:** Generates a JSON Lines file (managed by `SEOCrawler`).
3. **Load:** `SEOAnalyzer` reads JSON into `pandas.DataFrame`.
4. **Analyze:** Methods like `_analyze_http_status` process the DataFrame and return a `dict` of metrics.
5. **Score:** `SEOScorer` evaluates metrics against thresholds (in `config.py`) to produce a final 0-100 score.
6. **Report:** `ReporterFactory` formats the results.

## 5. File System Operations
- **Paths:** Always use `pathlib.Path` for path manipulation.
- **Absolute Paths:** When interacting with the file system tools (in the agent context), always verify paths exist before reading.

## 6. Testing Strategy
- **Unit Tests:** Focus on `analyzer.py` logic. Create DataFrames manually to simulate crawl results.
- **Mocking:** Mock network calls (crawling) when testing `crawler.py` or full application flows.
- **Fixtures:** Use `pytest` fixtures for common setups (e.g., `analyzer` instance, sample `DataFrame`).

---
*Created for AI Agent Context - 2024*
