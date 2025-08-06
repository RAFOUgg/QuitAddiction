# --- utils/logger.py ---
import logging
from logging.handlers import RotatingFileHandler
import os

# Create the logs directory if it doesn't exist (Your code already did this well)
LOGS_DIR = 'logs'
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# IMPROVEMENT 1: Use a factory function instead of a global logger.
# This allows each file in your project to get its own named logger.
def get_logger(name: str) -> logging.Logger:
    """
    Configures and returns a logger that writes to both console and a rotating file.
    The `name` parameter is typically __name__ from the calling module.
    """
    logger = logging.getLogger(name)
    
    # This check prevents adding handlers multiple times if the function is called again for the same logger.
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.INFO) # Set the minimum level of messages to handle
    
    # Create a standard formatter for all handlers
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # --- IMPROVEMENT 2: Add a Console Handler ---
    # This handler sends logs to the console, so you can see them with `docker-compose logs`.
    # THIS IS THE MOST CRITICAL CHANGE FOR DOCKER.
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    
    # --- File Handler (from your original code, which is great) ---
    # This handler saves logs to a file, which is persisted by your Docker volume.
    file_handler = RotatingFileHandler(
        os.path.join(LOGS_DIR, 'bot.log'), 
        maxBytes=5*1024*1024, # 5 MB per file
        backupCount=2,        # Keep 2 old log files
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger