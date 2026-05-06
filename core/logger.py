import logging
import os 
from datetime import datetime 
from config import LOG_DIR 

def setup_logger():
    os.makedirs(LOG_DIR, exist_ok = True)

    log_filename = datetime.now().strftime("%Y-%m-%d") + ".log"
    log_path = os.path.join(LOG_DIR, log_filename)

    logger = logging.getLogger("LADO")

    if logger.hasHandlers():
        logger.handlers.clear()    # wipe any existing handlers first
                               # then rebuild fresh every time
    
    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(log_path, encoding = "utf-8")
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger