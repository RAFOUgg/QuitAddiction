# --- db/database.py ---
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# -- Détermination du chemin de la base de données --
# Sauf indication contraire, __file__ est le chemin du fichier database.py lui-même.
CURRENT_DIR_PATH = os.path.dirname(os.path.abspath(__file__))
# Le fichier database.py est dans db/, donc pour remonter au niveau supérieur (QuitAddiction/) :
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR_PATH, os.pardir))

# Le fichier db/quit_addiction.db se trouve DANS le dossier db/
DB_FILE_NAME = 'quit_addiction.db'
DB_PATH = os.path.join(CURRENT_DIR_PATH, DB_FILE_NAME) # chemin = C:\...\BOT DISCORD\QuitAddiction\db\quit_addiction.db

DATABASE_URL = f"sqlite:///{DB_PATH}"

print(f"SQLAlchemy: Chemin DB relatif au fichier actuel ({CURRENT_DIR_PATH}):")
print(f"  Utilisation du fichier DB dans le même dossier : {DB_PATH}")
print(f"SQLAlchemy: URL utilisée pour la DB: {DATABASE_URL}")

try:
    engine = create_engine(DATABASE_URL)
    print("SQLAlchemy: Moteur créé avec succès.")
except Exception as e:
    print(f"SQLAlchemy ERREUR CRITIQUE à la création du moteur: {e}")
    raise 

Base = declarative_base()
print("SQLAlchemy: Base déclarative créée avec succès.")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

_db_initialized = False # Drapeau pour éviter des exécutions multiples de create_all

def init_db():
    """Initialise la base de données en créant les tables si elles n'existent pas."""
    global _db_initialized
    if _db_initialized:
        print("init_db(): Base de données déjà initialisée, retour.")
        return

    print("init_db(): Tentative d'initialisation des tables...")
    try:
        # IMPORTER TOUS VOS MODÈLES ICI AVANT create_all() est ESSENTIEL
        # Ceci enregistre les modèles auprès de Base.metadata pour que create_all() les trouve.
        from db.models import ServerState, PlayerProfile, ActionLog 
        
        print("init_db(): Models (ServerState, PlayerProfile, ActionLog) importés avec succès.")

        print("SQLAlchemy: Appel de Base.metadata.create_all(bind=engine)...")
        Base.metadata.create_all(bind=engine)
        print("SQLAlchemy: create_all() complété.")

        _db_initialized = True
        print("init_db(): Initialisation de la base de données terminée avec succès.")

    except ImportError as ie:
        print(f"ERREUR CRITIQUE init_db(): ImportError – Vérifiez vos imports (notamment dans db/models.py et sa dépendance à Base) : {ie}")
    except NameError as ne:
        print(f"ERREUR CRITIQUE init_db(): NameError – Probablement 'Base' non défini au moment de l'usage dans models.py. Vérifiez les imports : {ne}")
    except Exception as e:
        print(f"ERREUR CRITIQUE init_db(): Exception Générale – {e}")

def get_db():
    """Fournit une session de base de données (à utiliser avec `yield` et `finally`)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()