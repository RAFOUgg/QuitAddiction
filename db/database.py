# --- db/database.py (Corrected) ---
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from utils.logger import get_logger

logger = get_logger(__name__)

# -- CORRECTED: Centralize data in a top-level 'data' directory for easier volume mounting --
# The Dockerfile is now responsible for creating this directory and setting its permissions.
APP_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(APP_ROOT_DIR, 'data')
DB_FILE_NAME = 'quit_addiction.db'
DB_PATH = os.path.join(DATA_DIR, DB_FILE_NAME)

# This line is a safeguard, but the Dockerfile should handle creation and permissions.
os.makedirs(DATA_DIR, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"

logger.info(f"Database path set to: {DB_PATH}")
logger.info(f"Database URL: {DATABASE_URL}")

try:
    # check_same_thread=False is needed for SQLite with multiple threads/async tasks
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    logger.info("SQLAlchemy engine created successfully.")
except Exception as e:
    logger.critical(f"CRITICAL ERROR creating SQLAlchemy engine: {e}")
    raise 

Base = declarative_base()
logger.info("SQLAlchemy declarative base created successfully.")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

_db_initialized = False

def init_db():
    """Initialise la base de données en créant les tables si elles n'existent pas."""
    global _db_initialized
    if _db_initialized:
        logger.info("init_db(): Database already initialized, skipping.")
        return

    logger.info("init_db(): Attempting to initialize tables...")
    try:
        from db.models import ServerState, PlayerProfile, ActionLog 
        
        logger.info("init_db(): Models (ServerState, PlayerProfile, ActionLog) imported successfully.")

        logger.info(f"SQLAlchemy: Tables to be created: {list(Base.metadata.tables.keys())}")
        Base.metadata.create_all(bind=engine)
        logger.info("SQLAlchemy: create_all() completed.")

        _db_initialized = True
        logger.info("init_db(): Database initialization finished successfully.")

    except ImportError as ie:
        logger.critical(f"CRITICAL ERROR init_db(): ImportError – Check your imports (especially in db/models.py and its dependency on Base): {ie}")
    except Exception as e:
        logger.critical(f"CRITICAL ERROR init_db(): General Exception – {e}")

def get_db():
    """Provides a database session (to be used with `yield` and `finally`)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()