# 20260807 1230

# Fresh full pipeline
python main.py

# Resume after interruption
python main.py --resume

# Ingest only, skip previously-failed files
python main.py --phases ingest --resume --skip-failed --max-failures 10

# Legacy entry points still work
python ingestion.py --resume
python db/ingest.py
python image_to_text/ocr.py

--- --- --- --- --- --- --- --- --- --- --- 

# 20260807 1310

# EasyOCR with auto-detected GPU (default)
python main.py

# PaddleOCR with auto-detected GPU
python main.py --ocr-engine paddle

# Resume process using PaddleOCR with auto-detected GPU
python main.py --resume --ocr-engine paddle

# Force CPU
   

# Force GPU, explicit paddle Python path
python main.py --ocr-engine paddle --gpu --paddle-python "C:\...\envs\paddleocr\python.exe"

-------------------------------------


Good question — and the answer has two parts, because your project now spans two environments.

You must run main.py from the myenv environment
The pipeline (main.py, ingest.py, similarity.py, etc.) needs torch, sentence-transformers, sqlite-vector, flask — all installed in myenv. So activate it first:

Also make sure you're in the project directory:

You do not need to switch to paddleocr env for that command
The --ocr-engine paddle flag makes main.py automatically launch PaddleOCR as a subprocess in the paddleocr env. It finds that env's Python via auto-detection (find_paddle_python()) — pointing at ...\envs\paddleocr\python.exe — and runs paddle_ocr_worker.py inside it. This is exactly why we separated the envs, so they never conflict.

So the command still runs from myenv; Paddle does its work in a child process under paddleocr.

One thing to verify
Auto-detection looks for the paddleocr env at:
C:\Users\ashjain11\AppData\Local\anaconda3\envs\paddleocr\python.exe

That path exists on your machine, so it should work. If you ever want to be explicit/about it, pass the path directly:

Quick rule of thumb
Task	Which env
Run pipeline (main.py / ingestion.py / db/ingest.py)	myenv
PaddleOCR backend (auto-launched)	paddleocr (automatic, don't switch)
Manually test Paddle itself	paddleocr
Quick rule of thumb
Task	Which env
Run pipeline (main.py / ingestion.py / db/ingest.py)	myenv
PaddleOCR backend (auto-launched)	paddleocr (automatic, don't switch)
Manually test Paddle itself	paddleocr

--- --- --- --- ---

# 20260807 1715

# Default mode — resume (processes only new/unfinished files):
python main.py

# Force fresh start (reprocess everything, rotated DB):
python main.py --fresh

# OCR-only on new batch:
python main.py --phases ocr

# PaddleOCR with GPU:
python main.py --ocr-engine paddle --gpu