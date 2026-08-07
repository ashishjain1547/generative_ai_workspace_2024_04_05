"""
Database helpers: rotation, vector extension, schema, BLOB utilities.
"""

import os
import sqlite3
import struct
import importlib.resources
from datetime import datetime
from pathlib import Path

from config import DB_DIR, DB_PATH, TABLE_NAME, VECTOR_COLUMN, EMBEDDING_DIM


# ═══════════════════════════════════════════════════════════════════════
#  DB rotation
# ═══════════════════════════════════════════════════════════════════════

def rotate_db_file(fresh: bool = True):
    """Timestamp the existing DB so the current run starts fresh.
    When fresh=False (resume mode), the DB is left untouched.
    """
    if fresh and DB_PATH.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        archived = DB_DIR / f"pdf_reconciliation_{ts}.db"
        os.rename(str(DB_PATH), str(archived))
        print(f"[OK] Archived previous DB → {archived.name}")


# ═══════════════════════════════════════════════════════════════════════
#  sqlite-vector extension
# ═══════════════════════════════════════════════════════════════════════

def load_vector_extension(conn: sqlite3.Connection):
    """Load the sqlite-vector extension into the given connection."""
    try:
        ext_path = importlib.resources.files("sqlite_vector.binaries") / "vector"
        conn.enable_load_extension(True)
        conn.load_extension(str(ext_path))
        conn.enable_load_extension(False)
        version = conn.execute("SELECT vector_version()").fetchone()[0]
        backend = conn.execute("SELECT vector_backend()").fetchone()[0]
        print(f"[OK] sqlite-vector v{version} loaded (backend: {backend})")
    except Exception as e:
        print(f"[WARN] Could not load sqlite-vector extension: {e}")
        raise


def create_db(conn: sqlite3.Connection):
    """Create the SQLite table if it does not exist."""
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_name TEXT NOT NULL UNIQUE,
            embedding BLOB NOT NULL
        )
    """)
    conn.commit()
    print(f"[OK] Table '{TABLE_NAME}' ready.")


def init_vector_extension(conn: sqlite3.Connection):
    """Initialize the vector extension for the table/column."""
    conn.execute(f"""
        SELECT vector_init(
            '{TABLE_NAME}',
            '{VECTOR_COLUMN}',
            'dimension={EMBEDDING_DIM},type=FLOAT32,distance=COSINE'
        )
    """)
    conn.commit()
    print(f"[OK] vector_init on {TABLE_NAME}.{VECTOR_COLUMN} "
          f"(dim={EMBEDDING_DIM}, distance=COSINE)")


# ═══════════════════════════════════════════════════════════════════════
#  BLOB helpers (fallback for non-vector-extension computations)
# ═══════════════════════════════════════════════════════════════════════

def blob_to_floats(blob: bytes) -> list[float]:
    """Unpack a BLOB of float32 values into a list of floats."""
    n = len(blob) // 4
    return list(struct.unpack(f"{n}f", blob))


def floats_to_blob(values: list[float]) -> bytes:
    """Pack a list of floats into a BLOB of float32 values."""
    return struct.pack(f"{len(values)}f", *values)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
