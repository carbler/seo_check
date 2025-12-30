from abc import ABC, abstractmethod
from datetime import datetime
import json
from config import SEOConfig
from analyzer import SEOAnalyzer

class SEOReporter(ABC):
    """Abstract base class for SEO reporters."""

    def __init__(self, config: SEOConfig, metrics: dict, score: float, rating: str, penalties: list):
        self.config = config
        self.metrics = metrics
        self.score = score
        self.rating = rating
        self.penalties = penalties
        # Helper to access definitions via Analyzer static or instance
        self.definitions = SEOAnalyzer(config).get_issue_definitions()

    @abstractmethod
    def generate(self):
        """Generates the report."""
        pass

class MarkdownReporter(SEOReporter):
    """Generates a Markdown report in a Semrush-style audit format."""

    def generate(self):
        filename = self.config.report_file
        issues = self.metrics.get('issues', {'errors': [], 'warnings': [], 'notices': []})
        http = self.metrics['http']
        page_details = self.metrics.get('page_details', {})

        with open(filename, 'w', encoding='utf-8') as f:
            # HEADER
            f.write(f"# 🔍 TuWorker.com - Site Audit Report\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
            f.write(f"**Base URL**: {self.config.base_url}\n\n")

            # DASHBOARD / EXECUTIVE SUMMARY
            f.write("## 📊 Executive Dashboard\n\n")
            f.write(f"### Site Health Score: {self.score:.0f}/100 ({self.rating})\n")
            f.write(f"**Pages Crawled:** {http['total']}  \n")

            # Issue Counts
            total_errors = sum(i['count'] for i in issues['errors'])
            total_warnings = sum(i['count'] for i in issues['warnings'])
            total_notices = sum(i['count'] for i in issues['notices'])

            f.write("| 🔴 Errors | ⚠️ Warnings | 🔵 Notices |\n")
            f.write("|:---:|:---:|:---:|\n")
            f.write(f"| **{total_errors}** | **{total_warnings}** | **{total_notices}** |\n\n")

            # TOP ISSUES
            f.write("### 🏆 Top Issues\n")
            all_issues = []
            for i in issues['errors']: all_issues.append((i['count'], "🔴 " + i['name']))
            for i in issues['warnings']: all_issues.append((i['count'], "⚠️ " + i['name']))
            # Sort by count desc
            all_issues.sort(key=lambda x: x[0], reverse=True)

            if all_issues:
                for count, name in all_issues[:5]:
                    f.write(f"- **{count}** pages with {name}\n")
            else:
                f.write("No major issues found! 🎉\n")
            f.write("\n---\n\n")

            # --- DETAILED PAGE AUDIT (NEW SECTION) ---
            f.write("## 📑 Detailed Page Audit\n")
            f.write("Below is a detailed breakdown of findings for each crawled page.\n\n")

            # Sort pages: Errors first, then Warnings, then Good
            sorted_pages = sorted(page_details.items(), key=lambda item: 0 if "Critical" in item[1]['status'] else 1 if "Warning" in item[1]['status'] else 2)

            for url, data in sorted_pages:
                status_icon = data['status'].split()[0]
                f.write(f"### {status_icon} {url}\n")
                f.write(f"**Status:** {data['status']} | **Title:** \"{data['title']}\" | **Words:** {data['words']}\n")

                if data['issues']:
                    f.write("\n**Issues Found:**\n")
                    for issue in data['issues']:
                        # Determine icon based on issue type text
                        icon = "🔵"
                        if any(e['name'] in issue for e in issues['errors']): icon = "🔴"
                        elif any(w['name'] in issue for w in issues['warnings']): icon = "⚠️"
                        f.write(f"- {icon} {issue}\n")
                else:
                    f.write("\n✅ No issues detected.\n")
                f.write("\n---\n")

            # --- GLOSSARY (NEW SECTION) ---
            f.write("\n## 📚 Glossary: Understanding Your Report\n")
            f.write("| Issue Type | Description |\n")
            f.write("|---|---|\n")
            for name, desc in self.definitions.items():
                f.write(f"| **{name}** | {desc} |\n")
            f.write("\n---\n")

            # THEMATIC REPORT: CRAWLABILITY
            f.write("## 🕷️ Crawlability & Site Architecture\n")
            f.write(f"- **HTTP Status:** 200 OK ({http['stats'].get(200, 0)}) | Redirects ({len(http['redirects'])}) | Errors ({len(http['broken_links']) + len(http['server_errors'])})\n")

            if http['broken_links']:
                self._write_expandable_section(f, "Broken Links (4xx)", http['broken_links'], lambda x: f"- {x['url']} ({x['status']})")
            if http['redirects']:
                self._write_expandable_section(f, "Redirects (3xx)", http['redirects'], lambda x: f"- {x['url']} ({x['status']})")

            f.write("\n")

            # THEMATIC REPORT: ON-PAGE SEO
            f.write("## 📄 On-Page SEO\n")
            self._write_issue_group(f, issues, ['Duplicate Titles', 'Missing Titles', 'Titles Too Long', 'Titles Too Short'])
            self._write_issue_group(f, issues, ['Missing H1 Tags', 'Duplicate H1 Content'])
            self._write_issue_group(f, issues, ['Missing Meta Descriptions', 'Duplicate Meta Descriptions', 'Meta Desc Too Short', 'Meta Desc Too Long'])
            self._write_issue_group(f, issues, ['Low Word Count', 'Low Text-HTML Ratio'])
            f.write("\n")

            # THEMATIC REPORT: TECHNICAL & PERFORMANCE
            f.write("## ⚡ Technical & Performance\n")
            perf = self.metrics['others']['performance']
            f.write(f"- **Avg Load Time:** {perf['avg_time']:.2f}s\n")
            f.write(f"- **HTTPS:** {len(self.metrics['security']['non_https'])} non-secure pages\n")

            self._write_issue_group(f, issues, ['Slow Load Time', 'Non-HTTPS Pages', 'Images Missing Alt Text'])
            f.write("\n")

            # THEMATIC REPORT: INTERNAL LINKING
            f.write("## 🔗 Internal Linking\n")
            links = self.metrics['links']
            f.write(f"- **Internal Links:** {links['internal']}\n")
            f.write(f"- **External Links:** {links['external']}\n")
            f.write(f"- **Ratio:** {links['ratio']:.2f}\n")
            f.write("\n")

        print(f"✓ Report generated: {filename}")

    def _write_issue_group(self, f, issues, names_to_print):
        """Helper to print specific issues found in the metrics."""
        found = False
        # Search in all categories
        for category in ['errors', 'warnings', 'notices']:
            for issue in issues[category]:
                if issue['name'] in names_to_print:
                    found = True
                    self._write_expandable_section(f, issue['name'], issue['items'], self._default_formatter(issue['name']))

    def _default_formatter(self, issue_name):
        """Returns a formatter function based on the issue type."""
        if 'Duplicate' in issue_name:
            # Expects dict {text: [urls]}
            return lambda item: f"**\"{item[0]}\"**\n" + "".join([f"  - {u}\n" for u in item[1]])
        elif 'Images' in issue_name:
             # Expects dict {url, count}
            return lambda item: f"- {item['url']} ({item['count']} images)"
        elif 'Word' in issue_name:
            return lambda item: f"- {item['url']} ({item['count']} words)"
        elif 'Ratio' in issue_name:
            return lambda item: f"- {item['url']} ({item['ratio']:.1f}%)"
        else:
            # Expects strings or simple dicts with url
            return lambda item: f"- {item if isinstance(item, str) else item.get('url', item)}"

    def _write_expandable_section(self, f, title, items, format_func):
        if not items: return

        # If items is a dict (duplicates), convert to list of tuples for length check
        count = len(items)

        f.write(f"### {title} ({count})\n")
        # For duplicates (dict), we iterate items()
        if isinstance(items, dict):
            iterator = items.items()
        else:
            iterator = items

        for item in iterator:
            f.write(f"{format_func(item)}\n")
        f.write("\n")


class HTMLReporter(SEOReporter):
    """Generates an HTML report."""

    def generate(self):
        filename = self.config.report_file
        # Simplified HTML generation logic (keeping generic for now)
        html_content = f"""
        <html>
        <head><title>SEO Audit - {self.config.base_url}</title></head>
        <body>
            <h1>SEO Audit: {self.config.base_url}</h1>
            <h2>Score: {self.score}/100</h2>
            <p>Check the Markdown report for detailed Semrush-style analysis.</p>
        </body>
        </html>
        """
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✓ Report generated: {filename}")


class JSONReporter(SEOReporter):
    """Generates a JSON report."""

    def generate(self):
        filename = self.config.report_file

        def convert_numpy(obj):
            if hasattr(obj, 'item'):
                return obj.item()
            if isinstance(obj, dict):
                return {k: convert_numpy(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert_numpy(i) for i in obj]
            return obj

        data = {
            'metadata': {
                'date': str(datetime.now()),
                'base_url': self.config.base_url,
                'score': self.score,
                'rating': self.rating,
                'penalties': self.penalties
            },
            'metrics': convert_numpy(self.metrics)
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"✓ Report generated: {filename}")


class ReporterFactory:
    """Factory to create the appropriate reporter."""

    @staticmethod
    def create_reporter(config: SEOConfig, metrics, score, rating, penalties) -> SEOReporter:
        if config.output_format == 'html':
            return HTMLReporter(config, metrics, score, rating, penalties)
        elif config.output_format == 'json':
            return JSONReporter(config, metrics, score, rating, penalties)
        else:
            return MarkdownReporter(config, metrics, score, rating, penalties)
