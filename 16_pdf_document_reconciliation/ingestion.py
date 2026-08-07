"""
Thin wrapper � delegates to main.py for backward compatibility.
Run with: python ingestion.py [--resume] [--phases ocr,ingest,similarity] ...
"""

from main import main

if __name__ == "__main__":
    main()