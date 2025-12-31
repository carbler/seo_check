# 🕷️ SEO Analyzer

A professional, Python-based Technical SEO Audit tool wrapped in a modern Web Interface.

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

2.  **Create a virtual environment (Recommended):**
    ```bash
    python -m venv myvenv
    source myvenv/bin/activate  # On Windows: myvenv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

---

## 🚦 Usage

### 1. Start the Web Server
Run the FastAPI application using Uvicorn:

```bash
python app.py
```
*Or manually:* `uvicorn app:app --host 0.0.0.0 --port 8000 --reload`

### 2. Access the Dashboard
Open your browser and navigate to:
👉 **http://localhost:8000**

### 3. Run an Audit
1.  Enter the **Target URL** (e.g., `https://example.com`).
2.  Set the **Max Depth** (e.g., `3` for a quick scan, `10` for deep crawl).
3.  Click **Analyze**.
4.  The scan runs in the background. Refresh the page after a few seconds/minutes to see the new report appear in the **Report History**.

### 4. View Report
Click **"View Report"** on any entry in the history table to open the interactive dashboard.

---

## 📂 Project Structure

```
├── app.py              # FastAPI Application entry point
├── config.py           # Configuration & SEO Thresholds
├── crawler.py          # Crawling logic (advertools)
├── analyzer.py         # Data processing & Issue detection logic
├── reporter.py         # Report generation logic (JSON export)
├── templates/          # HTML Templates (Jinja2)
│   ├── index.html      # Main Dashboard
│   └── report.html     # Interactive Report Viewer
├── reports/            # Generated artifacts (JSON, Logs, Crawl Data)
└── requirements.txt    # Project dependencies
```

## ⚙️ Configuration

You can tweak SEO thresholds (e.g., what counts as a "Long Title") directly in `config.py`:

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
