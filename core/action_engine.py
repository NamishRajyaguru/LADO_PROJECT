from core.database import get_connection
from config import ARCHIVE_DIR, QUARANTINE_DIR
import shutil, os
from pathlib import Path
from datetime import datetime

def archive_file(file_path, logger):
    # Check if file actually exists
    if not os.path.exists(file_path):
        logger.warning(f"File not found, skipping: {file_path}")
        return False
    try:
        # Create archive folder if it doesn't exist
        os.makedirs(ARCHIVE_DIR, exist_ok = True)

        # Build destination path - keep original filename
        filename = os.path.basename(file_path)
        destination = os.path.join(ARCHIVE_DIR, filename)

        # If a file with same name already exists in archive, add timestamp
        if os.path.exists(destination):
            name, ext = os.path.splitext(filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            destination = os.path.join(ARCHIVE_DIR, f"{name}_{timestamp}{ext}")

        shutil.move(file_path, destination)
        logger.info(f"Archived: {file_path} -> {destination}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to archive {file_path}: {e}")
        return False

def quarantine_file(file_path, logger):
    if not os.path.exists(file_path):
        logger.warning(f"File not found, skipping: {file_path}")
        return False
    
    try:
        # Create quarantine folder if it doesn't exist
        os.makedirs(QUARANTINE_DIR, exist_ok = True)

        # Build destination path
        filename = os.path.basename(file_path)
        destination = os.path.join(QUARANTINE_DIR, filename)


        # Handle name collection same way as archive
        if os.path.exists(destination):
            name, ext = os.path.splitext(filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            destination = os.path.join(QUARANTINE_DIR, f"{name}_{timestamp}{ext}")

        shutil.move(file_path, destination)
        logger.info(f"Quarantined: {file_path} -> {destination}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to quarantine {file_path}: {e}")
        return False

def mark_executed(suggestion_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE suggestions SET status = ? WHERE id = ?",
        ("executed", suggestion_id)
    )
    conn.commit()
    conn.close()

def log_action(file_path, action, approved_by="user"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO actions_log
                (file_path, action, approved_by, timestamp, reversible)
            VALUES (?, ?, ?, ?, ?)
    """, (
        file_path,
        action,
        approved_by,
        str(datetime.now()),
        1 # 1 = reversible, file went to archive/quarantine not deleted
    ))
    conn.commit()
    conn.close()

def execute_approved_suggestions(logger):
    conn = get_connection()
    cursor = conn.cursor()

    # Fetch everything that's been approved but not yet executed
    cursor.execute("""
        SELECT id, file_path, action
        FROM suggestions
        WHERE status = 'approved'
    """)
    approved = cursor.fetchall()
    conn.close()

    if not approved:
        logger.info("No approved suggestions to execute")
        return
    
    logger.info(f"Executing {len(approved)} approved suggestions")

    executed = 0
    failed = 0

    for suggestion_id, file_path, action in approved:
        success = False

        if action == "suggest_archive":
            success = archive_file(file_path, logger)

        elif action == "suggest_cleanup":
            success = quarantine_file(file_path, logger)

        elif action == "suggest_delete":
            # Never hard delete - always quarantine first
            success = quarantine_file(file_path, logger)

        if success:
            mark_executed(suggestion_id)
            log_action(file_path, action)
            # Remove from files table so it doesn't get re-suggested
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM files WHERE path = ?", (file_path,))
            conn.commit()
            conn.close()
            executed += 1
        else:
            failed += 1

    logger.info(f"Execution complete - executed: {executed}, failed: {failed}")

def restore_file(file_path, logger):
    """
    Restores a file from quarantine or archive back to its original location.
    Reads the original path from actions_log.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT file_path FROM actions_log
        WHERE file_path = ?
        ORDER BY timestamp DESC LIMIT 1
    """, (file_path,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        logger.warning(f"No action log found for: {file_path}")
        return False

    original_path = row[0]

    # Find where the file currently is
    filename = os.path.basename(original_path)
    quarantine_path = os.path.join(QUARANTINE_DIR, filename)
    archive_path = os.path.join(ARCHIVE_DIR, filename)

    current_location = None
    if os.path.exists(quarantine_path):
        current_location = quarantine_path
    elif os.path.exists(archive_path):
        current_location = archive_path

    if not current_location:
        logger.warning(f"File not found in quarantine or archive: {filename}")
        return False

    try:
        os.makedirs(os.path.dirname(original_path), exist_ok=True)
        shutil.move(current_location, original_path)
        logger.info(f"Restored: {current_location} -> {original_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to restore {filename}: {e}")
        return False