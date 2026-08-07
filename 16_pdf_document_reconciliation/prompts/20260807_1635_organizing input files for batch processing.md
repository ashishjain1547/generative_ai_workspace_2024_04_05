# ROLE
Expert AI Engineer

# TASK
Modify code to adapt to reorganization of input directory to enable batch processing

# NEW INPUT FILES AND FOLDERS ORGANIZATION

- This remains same (in config.py):
BASE_DIR = Path(__file__).resolve().parent 

- Main input location remains the same: BASE_DIR / input

- Children of "BASE_DIR / input" will be directories named in the format: YYYYMMDD_HHMM

- Main input files will be placed in further subdirectories (with any / whatever names) or as files themselves in: BASE_DIR / input / YYYYMMDD_HHMM 

# KEY STEP OF LOGGING

Maintain a CSV file in:
C:\Users\ashjain11\OneDrive - Publicis Groupe\Desktop\16_pdf_document_reconciliation\logs

That has columns:
SNO, TIMESTAMP_PROCESSED, RELATIVE_PATH_WINDOWS, RELATIVE_PATH_LINUX, OCR_REQUIRED, OCR_DONE, ENCODING_AND_INGESTION_DONE

SNO: Integer
TIMESTAMP_PROCESSED: Timestamp when file was processed
RELATIVE_PATH_WINDOWS: Relative path to BASE_DIR in Windows format
RELATIVE_PATH_LINUX: Relative path to BASE_DIR in Linux format (Git Bash compatible)
OCR_REQUIRED: Whether file required OCR (YES/NO)
OCR_DONE: Whether OCR completed for this file or not (YES/NO/NA) -- NA when OCR_REQUIRED == NO
ENCODING_AND_INGESTION_DONE: Whether encoding and ingestion completed for this file or not (YES/NO/NA)
#_OF_FILE_PROCESSED: Incremental count to identify which iteration is it for this file. Each run (if not resuming) creates a new row and increments this value "#_OF_FILE_PROCESSED" and this value "TIMESTAMP_PROCESSED"

# ** USE THIS FILE TO RUN IN DEFAULT MODE OF "RESUME" **
