# --- db/database.py (REVISED) ---
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from utils.logger import get_logger

logger = get_logger(__name__)

APP_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(APP_ROOT_DIR, 'data')
DB_FILE_NAME = 'quit_addiction.db'
DB_PATH = os.path.join(DATA_DIR, DB_FILE_NAME)
os.makedirs(DATA_DIR, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"

logger.info(f"Database path set to: {DB_PATH}")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base est simplement défini ici. Les modèles l'importeront.
Base = declarative_base()

# La fonction init_db() a été retirée d'ici. La création se fait maintenant dans bot.py.