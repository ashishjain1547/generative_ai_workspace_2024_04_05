"""
Similarity report — compute top-K matches per document using sqlite-vector's
native vector_full_scan.  Results are streamed per-row (not materialising
a full N×N matrix) and optionally saved as JSON.
"""

import json
from datetime import datetime

from config import TABLE_NAME, VECTOR_COLUMN, TOP_K, LOGS_DIR
from checkpoint import set_phase_status, save_state


def compute_top_k_matches(conn, k: int = TOP_K) -> dict:
    """Compute top-K similar documents per document using vector_full_scan.

    Returns: {
        "doc_names": [...],
        "top_matches": {doc_name: [{"document": ..., "score": ...}, ...]}
    }

    This is memory-efficient: only k+1 rows per document are held in Python,
    not the full N×N matrix.
    """
    cur = conn.cursor()
    cur.execute(
        f"SELECT id, document_name, embedding FROM {TABLE_NAME} ORDER BY id"
    )
    rows = cur.fetchall()
    n = len(rows)
    ids = [r[0] for r in rows]
    names = [r[1] for r in rows]

    top_matches = {}

    for i in range(n):
        emb_blob = rows[i][2]

        # k+1 = top k matches + self (self will be at distance 0)
        dist_rows = cur.execute(
            f"SELECT rowid, distance "
            f"FROM vector_full_scan('{TABLE_NAME}','{VECTOR_COLUMN}',?,?)",
            (emb_blob, k + 1),
        ).fetchall()

        dist_map = {r[0]: r[1] for r in dist_rows}

        # Build top-k (exclude self)
        ranked = []
        for j in range(n):
            if ids[j] == ids[i]:
                continue
            dist = dist_map.get(ids[j], 1.0)
            sim = round(1.0 - dist, 6)
            ranked.append((sim, names[j]))

        ranked.sort(reverse=True)
        top_matches[names[i]] = [
            {"document": doc, "score": score}
            for score, doc in ranked[:k]
        ]

    return {"doc_names": names, "top_matches": top_matches}


def save_similarity_report(result: dict) -> str:
    """Save the similarity report to a timestamped JSON file.  Returns the file path."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = LOGS_DIR / f"similarity_report_{ts}.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return str(path)


def print_similarity_summary(result: dict):
    """Print top-3 matches per document to console."""
    names = result["doc_names"]
    top = result["top_matches"]
    for name in names:
        matches = top.get(name, [])[:3]
        print(f"\n📄 {name}")
        for m in matches:
            print(f"   {m['score']:.4f}  ←  {m['document']}")


def run_similarity_phase(conn, state: dict, *, k: int = TOP_K):
    """Run the similarity report phase with checkpoint."""
    print("=" * 60)
    print("PHASE 3: SIMILARITY REPORT")
    print("=" * 60)

    set_phase_status(state, "similarity", "in_progress")
    save_state(state)

    try:
        result = compute_top_k_matches(conn, k=k)
        report_path = save_similarity_report(result)
        print(f"[OK] Similarity report saved → {report_path}")
        print_similarity_summary(result)

        set_phase_status(state, "similarity", "completed")
        mark_done_in_similarity(state)
        save_state(state)
    except Exception as e:
        print(f"[FAIL] Similarity phase failed: {e}")
        raise


def mark_done_in_similarity(state: dict):
    """Mark the similarity phase as completed (no per-file tracking needed)."""
    pass  # similarity is not per-file; completion is tracked via phase status
