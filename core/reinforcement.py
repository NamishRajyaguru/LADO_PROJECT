# core/reinforcement.py
import sqlite3
from datetime import datetime
from core.database import get_connection

# ── How aggressively feedback shifts confidence ────────────────────
LEARN_RATE    = 0.05   # each approval adds 5% to multiplier
DECAY_RATE    = 0.08   # each rejection subtracts 8% (rejections matter more)
MAX_MULT      = 2.0    # confidence can at most double
MIN_MULT      = 0.2    # confidence can at most drop to 20% of base


def record_feedback(rule_id, outcome, file_path=None):
    """
    Called whenever a suggestion is approved or rejected.
    outcome: 'approved' or 'rejected'
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Log the raw event
    cursor.execute("""
        INSERT INTO rule_feedback (rule_id, outcome, file_path, timestamp)
        VALUES (?, ?, ?, ?)
    """, (rule_id, outcome, file_path, str(datetime.now())))

    # Update the aggregated confidence row
    cursor.execute("""
        INSERT INTO rule_confidence (rule_id, base, multiplier, approvals, rejections, last_updated)
        VALUES (?, 1.0, 1.0, 0, 0, ?)
        ON CONFLICT(rule_id) DO NOTHING
    """, (rule_id, str(datetime.now())))

    if outcome == "approved":
        cursor.execute("""
            UPDATE rule_confidence
            SET approvals    = approvals + 1,
                multiplier   = MIN(?, multiplier + ?),
                last_updated = ?
            WHERE rule_id = ?
        """, (MAX_MULT, LEARN_RATE, str(datetime.now()), rule_id))

    elif outcome == "rejected":
        cursor.execute("""
            UPDATE rule_confidence
            SET rejections   = rejections + 1,
                multiplier   = MAX(?, multiplier - ?),
                last_updated = ?
            WHERE rule_id = ?
        """, (MIN_MULT, DECAY_RATE, str(datetime.now()), rule_id))

    conn.commit()
    conn.close()


def get_multiplier(rule_id):
    """Returns the current confidence multiplier for a rule. Default 1.0."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT multiplier FROM rule_confidence WHERE rule_id = ?",
            (rule_id,)
        )
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 1.0
    except:
        return 1.0


def get_all_multipliers():
    """Returns dict of {rule_id: multiplier} for all rules."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT rule_id, multiplier FROM rule_confidence")
        rows = cursor.fetchall()
        conn.close()
        return {row[0]: row[1] for row in rows}
    except:
        return {}


def get_feedback_summary():
    """Returns a summary of all rule feedback for display."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT rule_id, approvals, rejections, multiplier, last_updated
            FROM rule_confidence
            ORDER BY rule_id
        """)
        rows = cursor.fetchall()
        conn.close()
        return rows
    except:
        return []