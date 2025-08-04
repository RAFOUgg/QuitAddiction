from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Construct the database URL
# It's good practice to define the DB file path relative to your project root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, 'quit_addiction.db')
DATABASE_URL = f"sqlite:///{DB_FILE}"

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create a base class for declarative models
Base = declarative_base()

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Function to create all tables
def init_db():
    try:
        # Import your models here so they are registered with Base
        # For example:
        from db.models import ServerState, PlayerProfile, ActionLog # Ensure all your models are imported

        # This command will create tables for all models that inherit from Base
        Base.metadata.create_all(bind=engine)
        print("Tables de la base de données créées (ou déjà existantes).")
    except Exception as e:
        print(f"Erreur lors de l'initialisation de la base de données : {e}")

# Helper function to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()