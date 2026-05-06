# config.example.py
# Copy this file to config.py and fill in your values

import os

BASE_DIR       = "C:/Users/YOUR_USERNAME/Documents/LADO_PROJECT"
DATA_DIR       = os.path.join(BASE_DIR, "data")
DB_PATH        = os.path.join(DATA_DIR, "lado.db")
LOG_DIR        = os.path.join(DATA_DIR, "logs")
ARCHIVE_DIR    = os.path.join(DATA_DIR, "archive")
QUARANTINE_DIR = os.path.join(DATA_DIR, "quarantine")

SCAN_TARGETS = [
    "C:/Users/YOUR_USERNAME/Downloads",
    "C:/Users/YOUR_USERNAME/Documents",
    "C:/Users/YOUR_USERNAME/Desktop",
    "C:/Users/YOUR_USERNAME/Pictures",
    "C:/Users/YOUR_USERNAME/Videos",
    "C:/Users/YOUR_USERNAME/Music",
]

LARGE_FILE_MB     = 500
UNUSED_DAYS       = 180
LARGE_UNUSED_MB   = 100
LARGE_UNUSED_DAYS = 90
TEMP_EXTENSIONS   = [".tmp", ".temp", ".cache", ".log"]

CONFIDENCE_AUTO_ACT = 0.95
CONFIDENCE_SUGGEST  = 0.70

LLM_PROVIDER = "groq"
GROQ_API_KEY = "your_groq_api_key_here"
GROQ_MODEL   = "llama3-8b-8192"
OLLAMA_MODEL = "llama3"