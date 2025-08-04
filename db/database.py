# --- db/database.py ---
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# -- Détermination du chemin de la base de données --
# Sauf indication contraire, __file__ est le chemin du fichier database.py lui-même.
CURRENT_FILE_PATH = os.path.abspath(__file__) 

# Le fichier database.py est dans db/, donc pour remonter au niveau supérieur (QuitAddiction/BOT DISCORD) :
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_FILE_PATH, os.pardir, os.pardir)) 
# Ici, PROJECT_ROOT pointera vers : C:\Users\Rafi\Documents\.0AATAF\.Projet\Dev\BOT DISCORD\

# Votre base de données quit_addiction.db se trouve DANS le dossier db/
DB_FILE_NAME = 'quit_addiction.db'
DB_PATH = os.path.join(CURRENT_FILE_PATH, DB_FILE_NAME) # chemin RELATIF vers db/quit_addiction.db

DATABASE_URL = f"sqlite:///{DB_PATH}" # Le chemin sera alors : sqlite:///C:\Users\Rafi\Documents\.0AATAF\.Projet\Dev\BOT DISCORD\QuitAddiction\db\quit_addiction.db

print(f"SQLAlchemy: Chemin du fichier DB identifié comme: {DB_PATH}")
print(f"SQLAlchemy: URL utilisée pour la DB: {DATABASE_URL}")

try:
    engine = create_engine(DATABASE_URL)
    print("SQLAlchemy: Moteur créé avec succès.")
except Exception as e:
    print(f"SQLAlchemy ERREUR CRITIQUE à la création du moteur: {e}")
    raise # Arrête le processus si le moteur ne peut pas être créé

# --- Base de données unique pour tous les modèles ---
# Ceci DOIT être le seul endroit où `declarative_base()` est appelé et où `Base` est exporté.
try:
    Base = declarative_base()
    print("SQLAlchemy: Base déclarative créée avec succès.")
except Exception as e:
    print(f"SQLAlchemy ERREUR CRITIQUE lors de la création de declarative_base: {e}")
    # Si c'est ici que l'erreur se produit, le problème est plus profond (SQLAlchemy installé ?)
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Flag pour s'assurer que create_all n'est appelée qu'une fois.
_db_initialized = False

def init_db():
    global _db_initialized
    if _db_initialized:
        print("init_db(): Déjà initialisé.")
        return

    print("init_db(): Tentative d'initialisation des tables...")
    try:
        # --- IMPORTANT : IMPORT DES MODÈLES POUR LES ENREGISTRER CHEZ BASE ---
        # C'est l'import qui va lire `models.py` et lier les classes `Base` au `MetaData` de `Base`.
        # Si `models.py` lui-même essaie d'importer `Base` et que celui-ci n'est pas encore prêt dans `database.py`, c'est le NameError.
        
        # Pour palier à `NameError: name 'Base' is not defined` il faut que la définition `Base = declarative_base()` 
        # SOIT FAITE ET EXPORTÉE par `database.py` AVANT QUE `models.py` n'essaye de l'utiliser lors de son import.
        
        # Le mécanisme standard et robuste est que `models.py` IMPORTE `Base` de `database.py`.
        # Donc, vérifiez l'import dans `db/models.py`.

        # Cet import CI est censé marcher, car `Base` devrait déjà être défini AVANT qu'init_db() ne soit appelé.
        # Si Base n'est pas défini ici, c'est que la définition dans database.py elle-même a un problème.
        from db.models import ServerState, PlayerProfile, ActionLog 

        print("init_db(): Models importés depuis db.models.")

        print("SQLAlchemy: Appel de Base.metadata.create_all(bind=engine)...")
        Base.metadata.create_all(bind=engine)
        print("SQLAlchemy: create_all() complété.")

        _db_initialized = True
        print("init_db(): Initialisation de la base de données terminée avec succès.")

    except ImportError as ie:
        print(f"ERREUR CRITIQUE init_db(): ImportError. Vérifiez la structure de vos fichiers DB et les imports :")
        print(f"  Current file path: {CURRENT_FILE_PATH}")
        print(f"  Project root path: {PROJECT_ROOT}")
        print(f"  DB path: {DB_PATH}")
        print(f"  Erreur détaillée: {ie}")
        # Souvent le problème est dans l'import `from db.database import Base` dans `db/models.py`
    except NameError as ne:
        print(f"ERREUR CRITIQUE init_db(): NameError – 'Base' non défini.")
        print(f"  Cause la plus probable : l'importation de `Base` depuis db/database.py dans db/models.py échoue,")
        print(f"  OU la définition de Base dans db/database.py elle-même est incorrecte ou trop tardive.")
        print(f"  Détail : {ne}")
    except Exception as e:
        print(f"ERREUR CRITIQUE init_db(): Exception Générale non gérée : {e}")

# Helper pour avoir une session.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()