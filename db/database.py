# db/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os

# --- Configuration de la base de données ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bot.db") # Par défaut, utilise un fichier SQLite
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# --- Fonctions pour la base de données ---

def init_db():
    """
    Cette fonction est responsable de la création des tables de la base de données
    si elles n'existent pas. Elle est appelée une seule fois au démarrage du bot.
    """
    # Ici, vous devrez importer tous vos modèles SQLAlchemy
    # par exemple : from .models import ServerState, PlayerProfile, ActionLog
    # L'importation doit être faite pour que Base.metadata.create_all fonctionne.
    # Si vos modèles sont dans db/models.py, vous pouvez les importer comme ceci :
    from . import models

    # Crée toutes les tables définies dans vos modèles SQLAlchemy
    Base.metadata.create_all(bind=engine)
    print("Tables de la base de données créées (ou déjà existantes).")

# Si vous avez d'autres fonctions utilitaires pour la DB, elles iraient ici.