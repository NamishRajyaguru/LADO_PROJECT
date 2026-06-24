# main.py
from core.logger import setup_logger
from core.database import create_tables, get_summary
from core.scanner import run_full_scan
from core.hashing import find_duplicates
from core.policy_engine import run_policy_engine
from core.llm import summarize_scan, answer_user_question, reset_conversation
from core.action_engine import execute_approved_suggestions

def run_lado():
    # ── 1. Setup ───────────────────────────────────────────────
    logger = setup_logger()
    logger.info("=" * 50)
    logger.info("LADO starting up")
    logger.info("=" * 50)

    # ── 2. Initialize database ─────────────────────────────────
    create_tables()
    logger.info("Database initialized")

    # ── 3. Scan ────────────────────────────────────────────────
    run_full_scan(logger)

    # ── 4. Detect duplicates ───────────────────────────────────
    find_duplicates(logger)

    # ── 5. Run policy engine ───────────────────────────────────
    execute_approved_suggestions(logger)
    run_policy_engine(logger)

    # ── 6. Print summary ───────────────────────────────────────
    summary = get_summary()
    logger.info("=" * 50)
    logger.info("LADO run complete")
    logger.info(f"  Total files:         {summary['total_files']:,}")
    logger.info(f"  Total size:          {summary['total_size_mb']:,} MB")
    logger.info(f"  Hashed files:        {summary['hashed_files']:,}")
    logger.info(f"  Pending suggestions: {summary['pending_suggestions']:,}")
    logger.info("=" * 50)

    reset_conversation()

    # LLM explains what just happened
    print("\n── LADO says ─────────────────────────────────────")
    print(summarize_scan(summary))
    print("──────────────────────────────────────────────────\n")

    # Simple interactive loop — user can ask questions
    try:
        while True:
            question = input("Ask LADO anything (or press Enter to exit): ").strip()
            if not question:
                break

            # Read last 30 lines of today's log as context
            import os
            from config import LOG_DIR
            from datetime import datetime
            log_file = os.path.join(LOG_DIR, datetime.now().strftime("%Y-%m-%d") + ".log")
            try:
                with open(log_file, "r") as f:
                    lines = f.readlines()
                    recent_logs = "".join(lines[-30:])
            except:
                recent_logs = "No logs available"

            print("\nLADO:", answer_user_question(question, recent_logs))
            print()
    except (EOFError, KeyboardInterrupt):
        pass



if __name__ == "__main__":
    run_lado()