"""
Real-time file watcher using watchdog.
Monitors SCAN_TARGETS folders and triggers backend scan on new/modified files.
"""
import threading, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

try:
    from config import SCAN_TARGETS, DB_PATH
except:
    SCAN_TARGETS = []
    DB_PATH = None

try:
    from core.scanner import scan_files
    from core.database import init_db
    from core.policy_engine import run_policy_engine
    from core.logger import setup_logger
    BACKEND_AVAILABLE = True
except:
    BACKEND_AVAILABLE = False

# ── Callback registry — dashboard registers here to get notified ──
_on_change_callbacks = []

def register_callback(fn):
    """Dashboard calls this to get notified when files change."""
    if fn not in _on_change_callbacks:
        _on_change_callbacks.append(fn)

def unregister_callback(fn):
    if fn in _on_change_callbacks:
        _on_change_callbacks.remove(fn)

def _notify_all():
    for fn in _on_change_callbacks:
        try: fn()
        except: pass


class LADOEventHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self._debounce_timer = None
        self._debounce_delay = 3.0  # wait 3s after last event before scanning

    def on_created(self, event):
        if not event.is_directory:
            self._debounce()

    def on_modified(self, event):
        if not event.is_directory:
            self._debounce()

    def _debounce(self):
        # cancel existing timer, restart it — avoids flooding on bulk copies
        if self._debounce_timer:
            self._debounce_timer.cancel()
        self._debounce_timer = threading.Timer(
            self._debounce_delay, self._run_scan)
        self._debounce_timer.daemon = True
        self._debounce_timer.start()

    def _run_scan(self):
        if not BACKEND_AVAILABLE: return
        try:
            logger = setup_logger()
            conn = init_db(logger)
            scan_files(conn, logger)
            run_policy_engine(conn, logger)
            conn.close()
            _notify_all()
        except Exception as e:
            print(f"[Watcher] Scan error: {e}")


# ── Singleton observer ────────────────────────────────────────────
_observer = None

def start_watcher():
    global _observer
    if not WATCHDOG_AVAILABLE:
        print("[Watcher] watchdog not installed — run: pip install watchdog")
        return False
    if not SCAN_TARGETS:
        print("[Watcher] No SCAN_TARGETS configured")
        return False
    if _observer and _observer.is_alive():
        return True  # already running

    handler = LADOEventHandler()
    _observer = Observer()
    for path in SCAN_TARGETS:
        if os.path.exists(path):
            _observer.schedule(handler, path, recursive=True)
            print(f"[Watcher] Watching: {path}")
        else:
            print(f"[Watcher] Path not found, skipping: {path}")

    _observer.daemon = True
    _observer.start()
    print("[Watcher] Started")
    return True

def stop_watcher():
    global _observer
    if _observer and _observer.is_alive():
        _observer.stop()
        _observer.join(timeout=2)
    _observer = None

def is_running():
    return _observer is not None and _observer.is_alive()