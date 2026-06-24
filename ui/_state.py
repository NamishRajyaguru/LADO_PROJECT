# Shared app state — survives tab switches
scan_proc      = None
scan_active    = False
scan_log       = []
from core.settings import load_settings
last_scan_time = load_settings().get("last_scan_time", "")
chat_messages  = []   # list of ("role", "text") tuples
last_mentioned_file = None