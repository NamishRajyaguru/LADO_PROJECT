# core/policy_engine.py
from config import (
    LARGE_FILE_MB, UNUSED_DAYS, LARGE_UNUSED_MB,
    LARGE_UNUSED_DAYS, TEMP_EXTENSIONS, CONFIDENCE_SUGGEST
)
from core.database import get_all_files, save_suggestion, get_connection
from datetime import datetime
from core.reinforcement import get_all_multipliers

RULES = [
    {
        "id":         "large_file",
        "condition":  lambda f: (
            f["size_mb"] > 500
            and f["extension"] not in [".exe", ".dll", ".sys", ".iso", ".msi"]
        ),
        "action":     "suggest_archive",
        "reason":     "File is over 500MB and not a system file — consider archiving",
        "confidence": 0.75,
        "risk":       "low",
    },
    {
        "id":         "unused_file",
        "condition":  lambda f: (
            f["days_since_modified"] > 180
            and f["size_mb"] > 50
            and f["extension"] not in [
                ".dll", ".exe", ".sys", ".ini", ".dat",
                ".cfg", ".log", ".db", ".sqlite", ".pyc"
            ]
        ),
        "action":     "suggest_archive",
        "reason":     "Large file unused for 6+ months — likely safe to archive",
        "confidence": 0.70,
        "risk":       "low",
    },
    {
        "id":         "duplicate_file",
        "condition":  lambda f: (
            f["is_duplicate"] is True
            and f["size_mb"] > 10
        ),
        "action":     "suggest_cleanup",
        "reason":     "Identical copy exists elsewhere — over 10MB wasted",
        "confidence": 0.95,
        "risk":       "medium",
    },
    {
        "id":         "large_unused",
        "condition":  lambda f: (
            f["size_mb"] > 200
            and f["days_since_modified"] > 90
            and f["extension"] not in [".dll", ".exe", ".sys", ".iso"]
        ),
        "action":     "suggest_archive",
        "reason":     "Large file sitting unused for 3+ months",
        "confidence": 0.85,
        "risk":       "low",
    },
    {
        "id":         "temp_file",
        "condition":  lambda f: (
            f["extension"] in [".tmp", ".temp"]
            and f["size_mb"] > 1
        ),
        "action":     "suggest_delete",
        "reason":     "Temporary file over 1MB — likely safe to remove",
        "confidence": 0.80,
        "risk":       "low",
    },
]

def prepare_file(db_record):
    path, name, extension, size_bytes, size_mb, modified_time, created_time, file_hash = db_record
    try:
        modified_dt = datetime.strptime(modified_time, "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        modified_dt = datetime.strptime(modified_time, "%Y-%m-%d %H:%M:%S")

    return {
        "path":                path,
        "name":                name,
        "extension":           extension,
        "size_bytes":          size_bytes,
        "size_mb":             size_mb or 0.0,
        "days_since_modified": (datetime.now() - modified_dt).days,
        "is_duplicate":        bool(file_hash),
    }

def evaluate_file(file_dict, multipliers=None):
    if multipliers is None:
        multipliers = {}
    suggestions = []
    for rule in RULES:
        try:
            if rule["condition"](file_dict):
                if rule["confidence"] >= CONFIDENCE_SUGGEST:
                    suggestions.append({
                        "rule_id":    rule["id"],
                        "action":     rule["action"],
                        "reason":     rule["reason"],
                        "confidence": rule["confidence"],
                        "risk":       rule["risk"],
                        "file":       file_dict["path"],
                    })
        except Exception:
            pass
    suggestions.sort(key=lambda s: s["confidence"], reverse=True)
    return suggestions

def run_policy_engine(logger):
    # Clear previous suggestions
    conn = get_connection()
    conn.execute("DELETE FROM suggestions WHERE status = 'pending'")
    conn.commit()
    conn.close()

    logger.info("Policy engine started")

    # Load learned multipliers
    multipliers = get_all_multipliers()
    if multipliers:
        logger.info(f"Loaded {len(multipliers)} learned confidence adjustments")

    all_files = get_all_files()
    all_suggestions = []

    for db_record in all_files:
        file_dict = prepare_file(db_record)
        suggestions = evaluate_file(file_dict, multipliers)
        all_suggestions.extend(suggestions)

    # Batch insert all suggestions at once
    from datetime import datetime
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executemany("""
        INSERT INTO suggestions
            (file_path, rule_id, action, reason, confidence, risk, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
    """, [
        (
            s["file"],
            s["rule_id"],
            s["action"],
            s["reason"],
            s["confidence"],
            s["risk"],
            str(datetime.now()),
        )
        for s in all_suggestions
    ])
    conn.commit()
    conn.close()

    logger.info(f"Policy engine complete — {len(all_suggestions):,} suggestions generated")
    return all_suggestions