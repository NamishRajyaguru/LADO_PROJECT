# core/agent.py
from core.logger import setup_logger
from core.database import create_tables
from core.scanner import run_full_scan
from core.hashing import find_duplicates
from core.action_engine import execute_approved_suggestions
from core.policy_engine import run_policy_engine


def run_full_cycle(logger=None):
    """
    Runs LADO's full pipeline on demand: scan, hash, execute any
    approved suggestions, then regenerate fresh suggestions.
    Used by the real-time watcher and the chat 'run a scan' command.
    """
    if logger is None:
        logger = setup_logger()

    create_tables()
    run_full_scan(logger)
    find_duplicates(logger)
    execute_approved_suggestions(logger)
    run_policy_engine(logger)
    return logger