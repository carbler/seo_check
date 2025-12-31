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
        self.definitions = SEOAnalyzer(config).get_issue_definitions()

    @abstractmethod
    def generate(self):
        """Generates the report."""
        pass

class JSONReporter(SEOReporter):
    """Generates a comprehensive JSON report for the Viewer."""

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
            'meta': {
                'generated_at': str(datetime.now()),
                'target_url': self.config.base_url,
                'tool': 'TuWorker SEO Analyzer',
                'version': '2.0'
            },
            'summary': {
                'score': self.score,
                'rating': self.rating,
                'penalties': self.penalties,
                'total_pages': self.metrics['http']['total']
            },
            'glossary': self.definitions,
            'metrics': convert_numpy(self.metrics)
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"✓ Report generated: {filename}")


class ReporterFactory:
    """Factory to create the appropriate reporter."""

    @staticmethod
    def create_reporter(config: SEOConfig, metrics, score, rating, penalties) -> SEOReporter:
        # Defaulting to JSON as per new requirement
        return JSONReporter(config, metrics, score, rating, penalties)
