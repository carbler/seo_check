# 🕷️ SEO Analyzer

A professional, Python-based Technical SEO Audit tool wrapped in a modern CLI and Web Interface.

This tool crawls any target website, analyzes critical SEO metrics (On-page, Performance, Links, Content), and generates detailed, interactive reports similar to Semrush or Ahrefs.

---

## 🚀 Features

- **Deep Crawling:** Uses `advertools` to crawl websites recursively with configurable depth.
- **Comprehensive Analysis:**
  - **On-Page:** Title, H1, Meta Descriptions, Canonical tags.
  - **Content:** Word count, Text-to-HTML ratio, Thin content detection.
  - **Technical:** HTTP Status codes (4xx/5xx), Redirects, HTTPS security.
  - **Performance:** Response time analysis.
  - **Links:** Internal vs. External link ratio.
- **Interactive Web Dashboard:**
  - **FastAPI** backend to manage scans.
  - **Background Tasks** for non-blocking execution.
  - **Report History** to revisit past audits.
- **Professional Reports:**
  - "Semrush-style" dashboard.
  - Categorized issues (🔴 Critical, ⚠️ Warnings, 🔵 Notices).
  - Detailed per-page audit explorer.
  - No database required (File-based JSON storage).

---

## 🛠️ Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd seo-analyzer
    ```

2.  **Install the package:**
    ```bash
    pip install .
    ```
    Or for development:
    ```bash
    pip install -e .
    ```

---

## 🚦 Usage

### CLI Commands

The tool provides a command-line interface `seo-check`.

#### 1. Analyze a Website
Run a quick analysis directly from your terminal:

```bash
seo-check analyze https://example.com --depth 3
```
Or simply run `seo-check analyze` for interactive mode.

#### 2. View Reports (Web Server)
Start the local web server to view generated reports in a nice dashboard:

```bash
seo-check serve
```
Then open **http://localhost:8000** in your browser.

---

## 📂 Project Structure

```
├── src/seo_check/      # Source code package
│   ├── app.py          # FastAPI Application entry point
│   ├── config.py       # Configuration & SEO Thresholds
│   ├── crawler.py      # Crawling logic (advertools)
│   ├── analyzer.py     # Data processing & Issue detection logic
│   ├── reporter.py     # Report generation logic (JSON export)
│   ├── main.py         # CLI Entry point
│   └── templates/      # HTML Templates (Jinja2)
├── setup.py            # Package installation script
├── MANIFEST.in         # Package data configuration
└── requirements.txt    # Project dependencies
```

## ⚙️ Configuration

You can tweak SEO thresholds (e.g., what counts as a "Long Title") directly in `src/seo_check/config.py`:

```python
# config.py
title_max_length: int = 60
slow_page_threshold: float = 3.0
min_word_count: int = 250
```

---

## 📝 Requirements

- Python 3.8+
- Modern Web Browser (Chrome/Firefox/Edge) for the report viewer.

## 🤝 Contributing

Feel free to submit issues or pull requests to improve the analysis logic or the web interface!
