# --- db/database.py ---
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# --- Détermination CORRECTE du chemin de la base de données ---
# Sauf indication contraire, __file__ est le chemin du fichier database.py lui-même.
CURRENT_DIR_PATH = os.path.dirname(os.path.abspath(__file__))
# Le fichier database.py se trouve dans le dossier db/, et le fichier DB
# quit_addiction.db se trouve AU MÊME NIVEAU que le dossier db/ (donc à la racine de votre projet "QuitAddiction").
# Oh, ATTENDEZ : dans l'image que vous m'avez fournie, le fichier `quit_addiction.db` EST DANS le dossier `db/`.
# C'est un point crucial. Si `quit_addiction.db` est DANS `db/` , le chemin précédent était FAUX.

# Si quit_addiction.db EST DANS LE MEME DOSSIER que database.py et models.py:
DB_FILE_NAME = 'quit_addiction.db'
DB_PATH = os.path.join(CURRENT_DIR_PATH, DB_FILE_NAME) #chemin = C:\...\BOT DISCORD\QuitAddiction\db\quit_addiction.db

# Si quit_addiction.db EST à la RACINE DU PROJET (au même niveau que le dossier db/)
# Ce qui est souvent mieux géré pour éviter des surprises avec __file__
# Dans ce cas :
# PROJECT_ROOT_PATH = os.path.abspath(os.path.join(CURRENT_DIR_PATH, os.pardir)) # Remonte à QuitAddiction/
# DB_PATH = os.path.join(PROJECT_ROOT_PATH, DB_FILE_NAME) # chemin = C:\...\BOT DISCORD\QuitAddiction\quit_addiction.db

# LOGIQUE RECONNUE: L'image montre `quit_addiction.db` DANS `db/`.
# On va donc utiliser la première approche : le fichier est dans le même dossier que les autres fichiers .py du dossier `db`.
print(f"SQLAlchemy: Chemin DB relatif au fichier actuel ({CURRENT_DIR_PATH}):")
print(f"  Utilisation du fichier DB dans le même dossier : {DB_PATH}")
DATABASE_URL = f"sqlite:///{DB_PATH}"


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

_db_initialized = False

def init_db():
    global _db_initialized
    if _db_initialized:
        print("init_db(): Déjà initialisé.")
        return

    print("init_db(): Tentative d'initialisation des tables...")
    try:
        # --- IMPORTS DE MODÈLES ---
        # C'est ici que nous nous assurons que SQLAlchemy "voit" vos modèles.
        # La faute `NameError: name 'Column' is not defined` EST dans `models.py`,
        # elle SURVIENT parce que LORS DE L'IMPORTATION DE MODELS.PY par init_db(),
        # db/models.py NE PEUT PAS trouver `Base`, ET QU'IL NE TROUVE PAS NON PLUS `Column` (et d'autres)
        # à cause du `try-except` ASTUCIEUX pour les IDEs.
        
        # SI la structure `db/database.py` et `db/models.py` est bien séparée pour les responsabilités (comme expliqué avant):
        # database.py : define Base, export Base, manage engine, define SessionLocal, call metadata.create_all
        # models.py : IMPORT Base FROM database.py, define model classes USING Base
        
        # Si l'erreur est `name 'Column' is not defined` C'EST QUE LE MODÈLE IMPORTE UN OBJET QUI N'EXISTE PAS.
        # Cet objet peut être `Base` (car pas encore défini ou exporté de database.py quand models.py est chargé),
        # OU les éléments de `sqlalchemy` (Column, Integer, etc.) s'ils ne sont pas bien importés DANS MODELS.PY
        # LORS DE SON ÉVALUATION INITIALE (avant le try-except pour l'IDE).

        # REVENONS AU CONFLIT CRUCIAL BASE / MODELS.PY :
        # Le problème principal EST probablement l'interaction des imports entre database.py et models.py.

        # Re-vérifions: db/database.py doit avoir:
        # from sqlalchemy.orm import declarative_base
        # Base = declarative_base() <-- CECI DOIT ÊTRE LA.

        # db/models.py doit avoir :
        # from db.database import Base <-- Ceci est le lien le plus sensible.

        # Essayons le pattern D'IMPORT DE DATABASE DANS MODELS LE PLUS SIMPLE :
        # Si vous avez un `try-except` qui `MockBase`, ceci DÉTRUIT la définition réelle.
        # ON VA LE RETIRER POUR L'INSTANT pour tester si l'import réel fonctionne sans lui.
        
        # ----- FIN DU POTENTIEL CONFLIT DE MODELS.PY ----

        # Pour que create_all fonctionne, les modèles DOIVENT être connus. L'IMPORT FAIT CELA.
        # Assurez-vous que db/models.py IMPORT CORRECTEMENT Base DE db/database.py.
        
        from db.models import ServerState, PlayerProfile, ActionLog 
        
        print("init_db(): Models (ServerState, PlayerProfile, ActionLog) importés avec succès.")

        print("SQLAlchemy: Appel de Base.metadata.create_all(bind=engine)...")
        Base.metadata.create_all(bind=engine)
        print("SQLAlchemy: create_all() complété.")

        _db_initialized = True
        print("init_db(): Initialisation de la base de données terminée avec succès.")

    except ImportError as ie:
        print(f"ERREUR CRITIQUE init_db(): ImportError – Vérifiez vos imports :")
        print(f"  CURRENT_FILE_PATH = {CURRENT_FILE_PATH}")
        print(f"  DB_PATH = {DB_PATH}")
        print(f"  Import Error Détail: {ie}")
        print("--> Est-ce que `from db.models import ...` fonctionne bien?")
        print("--> Assurez-vous que `from db.database import Base` dans `models.py` ne pose pas de conflit et que `Base` est bien défini ici.")

    except NameError as ne:
        print(f"ERREUR CRITIQUE init_db(): NameError – 'Base' ou un autre composant SQLAlchemy ('Column' ?) non défini.")
        print(f"  Détail: {ne}")
        print("--> Vérifiez IMPÉRATIVEMENT l'importation de `Base` dans db/models.py")
        print("--> et assurez-vous qu'il n'y a pas d'autres appels qui requièrent des choses de SQLAlchemy avant que `Base` soit bien défini et exporté par `db/database.py`.")
    except Exception as e:
        print(f"ERREUR CRITIQUE init_db(): Exception Générale : {e}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()