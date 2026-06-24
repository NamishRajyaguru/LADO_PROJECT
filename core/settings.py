import os
import json
from config import DATA_DIR

SETTINGS_PATH = os.path.join(DATA_DIR, "settings.json")

DEFAULT_SETTINGS = {
    "theme": "dark"
}

def load_settings():
    """
    Loads settings from the JSON file. 
    Safely falls back to DEFAULT_SETTINGS if file is missing, corrupted, or invalid.
    """
    if not os.path.exists(SETTINGS_PATH):
        # Automatically create it with defaults
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()
        
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Merge with defaults to ensure all keys exist
        settings = DEFAULT_SETTINGS.copy()
        if isinstance(data, dict):
            for k, v in data.items():
                settings[k] = v
                
        # Validate critical values
        if settings.get("theme") not in ["dark", "light"]:
            settings["theme"] = "dark"
            
        return settings
    except Exception:
        # Fallback to dark theme safely if file is corrupted
        return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    """
    Saves the provided settings dictionary to the JSON file.
    """
    try:
        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        print(f"Error saving settings: {e}")
