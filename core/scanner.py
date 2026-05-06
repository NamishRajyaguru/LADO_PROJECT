import datetime 
from pathlib import Path
from core.database import insert_files_batch
from config import SCAN_TARGETS

def scan_directory(folder_path, logger):
    root = Path(folder_path)
    records = []
    skipped = 0

    for item in root.rglob("*"):
        if not item.is_file():
            continue
        try:
            stat = item.stat()
            records.append((
                str(item),
                item.name,
                item.suffix.lower(),
                stat.st_size,
                round(stat.st_size / (1024 * 1024), 2),
                str(datetime.datetime.fromtimestamp(stat.st_mtime)),
                str(datetime.datetime.fromtimestamp(stat.st_ctime)),
            ))
        except PermissionError:
            logger.warning(f"Permission denied - skipped: {item}")
            skipped += 1
        except Exception as e:
            logger.error(f"Error raeding {item}: {e}")
            skipped += 1

    insert_files_batch(records)
    logger.info(f"Scan complete - inserted: {len(records)}, skipped: {skipped}")
    return len(records)

def run_full_scan(logger):
    logger.info("Full scan started")
    total = 0
    for folder in SCAN_TARGETS:
        if Path(folder).exists():
            logger.info(f"Scanning: {folder}")
            total += scan_directory(folder, logger)
        else:
            logger.warning(f"Scan target not found, skipping: {folder}")
    logger.info(f"Full scan complete - total files indexed: {total:,}")
    return total