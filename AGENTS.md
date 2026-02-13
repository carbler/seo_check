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
For ad-hoc testing or development, ensure `pytest`, `httpx`, and other extras referenced in `pyproject.toml` are installed by re-running the command.

### CLI vs Web Modes
**CLI mode** exposes `python -m seo_check.main analyze <URL>` plus a `serve` command for lightweight dashboards.
```bash
python -m seo_check.main analyze https://example.com --depth 2
python -m seo_check.main --help
```
**Web server mode** launches the FastAPI renderer. Use hot reload locally:
```bash
python -m seo_check.main serve
uvicorn seo_check.app:app --reload
```

### Build & Packaging
Packaging uses the `pyproject.toml` metadata (setuptools + wheel).
```bash
python -m build
```
Verify the generated distributions in `dist/` before tagging a release.

### Testing
Pytest is the lone testing framework. The config in `pyproject.toml` already applies `-v --tb=short`.
```bash
pytest
pytest tests/test_analyzer.py
pytest tests/test_analyzer.py::test_analyzer_happy_path
```
To rerun a targeted test, specify the file and test name:
```bash
pytest tests/test_cli.py::test_cli_entry
```
Capture logs or prints with `-s`, duplicate output with `-v`, and run failing tests in isolation for reliability.

### Linting & Formatting
No automated linter or formatter is enforced, but the repository follows strict **PEP 8**/type-safe conventions.
- **Imports:** Grouped in 3 blocks—standard library, third-party, local package—and alphabetized within each group.
- **Indentation:** 4 spaces per level, no tabs.
- **Line length:** Favor readability (~100 char max). Use implicit continuations for longer structures.

## 3. Code Style & Guidelines

### Type Hints & Documentation
- **Typing:** Mandatory for functions/methods; prefer `typing.Dict`, `List`, `Optional`, `Any`, `Tuple` from `typing`.
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
- Private helpers: prefixed with `_`.

### Error Handling & Logging
- Use `logging` instead of `print` in library code. Log exceptions with context.
  ```python
  logging.error("Fetch failed", exc_info=True)
  ```
- CLI feedback is rendered through `rich.console.Console()` for consistent colors/status.
- Catch only the specific exceptions you can remediate; bubble others to the CLI/web layer.

### Async vs Blocking
- Async functions (crawler, FastAPI) must stay async; heavy Pandas workloads run inside `asyncio.to_thread`.
- Keep blocking operations within sync helpers to avoid thread starvation.

### Scoring Fairness (Analyzer)
- The scoring routine in `analyzer.calculate()` applies a fairness multiplier so 404/5xx pages do not over-inflate semantic penalties (titles, H1, metadata, alt text, etc.). Respect the multiplier when adding new penalties.
- Critical penalties (broken links, SSL) remain untampered: they still impact the total per config thresholds.

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

## 5. File System Practices
- Favor `pathlib.Path` for paths.
- Report/state files live under `reports/<timestamp>/`; CLI/web share the same structure.
- Always confirm the parent directory exists before writing.

## 6. Testing Strategy
- Unit tests (mainly `tests/test_analyzer.py`) mock a small DataFrame to exercise classification logic.
- Integration tests (`tests/test_cli.py`, `tests/test_integrations.py`) validate CLI API and service output structure.
- Use fixtures for shared crawl data; avoid disk IO when possible.

## 7. Cursor & Copilot Rules
- There are no `.cursor` or `.cursorrules/` directives in this repository.
- No `.github/copilot-instructions.md` exists; default to best practices noted here.

## 8. Release & Commit Workflow
- When you make changes, `git status` then `git diff` before staging.
- Commit once per logical change. Message should focus on *why* (e.g., “Make scoring fairer for partially crawled sites”).
- Tag the branch with semantic versioning (e.g., `v0.1.3`) if the change goes to production.
- Before pushing, run the necessary tests (`pytest tests/<file>::<test>`). Push to `origin/main` (or the deployment target) after successful tests.
- Never commit secrets or generated artifacts (pip wheel, `*.pyc`).

## 9. Troubleshooting & Tips
- Use `python -m seo_check.main analyze` plus `--depth` to replicate issues before touching scoring logic.
- Inspect `reports/<timestamp>/report.json` to see the final score/penalties to cross-check fairness tweaks.
- If you add a new check, update the alignments in `metrics['issues']` to ensure per-page diagnostics keep working.

----
*Updated for AI Agent Context - 2026*
