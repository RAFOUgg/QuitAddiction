# --- utils/logger.py (Corrected) ---
import logging
from logging.handlers import RotatingFileHandler
import os

# CORRECTED: Point to a centralized data directory.
# The Dockerfile should create 'data/logs' and set permissions.
APP_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LOGS_DIR = os.path.join(APP_ROOT_DIR, 'data', 'logs')

def get_logger(name: str) -> logging.Logger:
    """
    Configures and returns a logger that writes to both console and a rotating file.
    The `name` parameter is typically __name__ from the calling module.
    """
    # This call makes the script robust for non-Docker execution, but the
    # Dockerfile is what truly fixes the permission issue in your container.
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    logger = logging.getLogger(name)
    
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    
    # CORRECTED: Use the full, correct path
    file_handler = RotatingFileHandler(
        os.path.join(LOGS_DIR, 'bot.log'), 
        maxBytes=5*1024*1024,
        backupCount=2,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger