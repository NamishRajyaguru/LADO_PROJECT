# core/hashing.py
import hashlib
import sqlite3
from collections import defaultdict
from core.database import get_connection, update_file_hash

def hash_file(file_path):
    hasher = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()
    except (PermissionError, FileNotFoundError):
        return None

def find_duplicates(logger):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT size_bytes, COUNT(*) as cnt
        FROM files
        GROUP BY size_bytes
        HAVING cnt > 1
    """)
    duplicate_sizes = [row[0] for row in cursor.fetchall()]

    if not duplicate_sizes:
        logger.info("No duplicate candidates found")
        conn.close()
        return {}

    placeholders = ",".join("?" * len(duplicate_sizes))
    cursor.execute(f"""
        SELECT path, name, size_bytes
        FROM files
        WHERE size_bytes IN ({placeholders})
        AND (hash IS NULL OR hash = '')
    """, duplicate_sizes)
    candidates = cursor.fetchall()
    conn.close()

    logger.info(f"Duplicate detection started - {len(candidates)} candidates to hash")

    hash_groups = defaultdict(list)
    for i, (path, name, size_bytes) in enumerate(candidates):
        if i % 500 == 0:
            logger.debug(f"Hashing progress: {i}/{len(candidates)}")
        file_hash = hash_file(path)
        if file_hash:
            update_file_hash(path, file_hash)
            hash_groups[file_hash].append({
                "path": path,
                "name": name,
                "size_bytes": size_bytes,
            })

    duplicate_clusters = {
        h: files
        for h, files in hash_groups.items()
        if len(files) > 1
    }

    redundant = sum(len(v) - 1 for v in duplicate_clusters.values())
    logger.info(f"Duplicate detection complete - {len(duplicate_clusters):,} clusters, {redundant:,} redundant files")

    return duplicate_clusters