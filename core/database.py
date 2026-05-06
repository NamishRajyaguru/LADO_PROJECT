# core/database.py
import sqlite3
import os
from config import DB_PATH, DATA_DIR

def get_connection():
    os.makedirs(DATA_DIR, exist_ok=True)
    return sqlite3.connect(DB_PATH)

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            path          TEXT UNIQUE,
            name          TEXT,
            extension     TEXT,
            size_bytes    INTEGER,
            size_mb       REAL,
            modified_time TEXT,
            created_time  TEXT,
            hash          TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS suggestions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path   TEXT,
            rule_id     TEXT,
            action      TEXT,
            reason      TEXT,
            confidence  REAL,
            risk        TEXT,
            status      TEXT DEFAULT 'pending',
            created_at  TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS actions_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path   TEXT,
            action      TEXT,
            approved_by TEXT,
            timestamp   TEXT,
            reversible  INTEGER DEFAULT 1
        )
    """)

    conn.commit()
    conn.close()

def clear_files():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM files")
    conn.commit()
    conn.close()

def insert_files_batch(records):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executemany("""
        INSERT OR IGNORE INTO files
            (path, name, extension, size_bytes, size_mb, modified_time, created_time)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, records)
    conn.commit()
    conn.close()

def get_all_files():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT path, name, extension, size_bytes, size_mb,
               modified_time, created_time, hash
        FROM files
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def update_file_hash(path, file_hash):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE files SET hash = ? WHERE path = ?", (file_hash, path))
    conn.commit()
    conn.close()

def save_suggestion(suggestion):
    from datetime import datetime
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO suggestions
            (file_path, rule_id, action, reason, confidence, risk, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
    """, (
        suggestion["file"],
        suggestion["rule_id"],
        suggestion["action"],
        suggestion["reason"],
        suggestion["confidence"],
        suggestion["risk"],
        str(datetime.now()),
    ))
    conn.commit()
    conn.close()

def get_summary():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM files")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(size_mb) FROM files")
    total_size = round(cursor.fetchone()[0] or 0, 2)

    cursor.execute("SELECT COUNT(*) FROM files WHERE hash IS NOT NULL AND hash != ''")
    hashed = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM suggestions WHERE status = 'pending'")
    pending = cursor.fetchone()[0]

    conn.close()
    return {
        "total_files":       total,
        "total_size_mb":     total_size,
        "hashed_files":      hashed,
        "pending_suggestions": pending,
    }