import os
from sqlalchemy import create_engine, Column, Integer, String, BigInteger, Float
from sqlalchemy.orm import declarative_base, sessionmaker

# --- Configuration de la Base de Données ---

# On crée un dossier 'data' s'il n'existe pas pour stocker notre fichier de base de données
if not os.path.exists('data'):
    os.makedirs('data')

# L'URL de connexion pointe vers un fichier quitaddiction.db dans le dossier /data
DATABASE_URL = "sqlite:///data/quitaddiction.db"

# Le "moteur" est le point d'entrée principal de SQLAlchemy pour communiquer avec la DB
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} # Requis pour SQLite avec des applications multi-threads comme un bot
)

# La "Session" est notre handle pour effectuer des transactions avec la DB
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# "Base" est une classe de base que nos modèles de table vont hériter
Base = declarative_base()


# --- Définition des Modèles (Tables) ---

class ServerConfig(Base):
    """Table pour stocker la configuration spécifique à chaque serveur (guild)."""
    __tablename__ = 'server_configs'
    
    guild_id = Column(BigInteger, primary_key=True, autoincrement=False)
    staff_role_id = Column(BigInteger, nullable=True)
    main_channel_id = Column(BigInteger, nullable=True)
    counting_channel_id = Column(BigInteger, nullable=True)
    last_counter_id = Column(BigInteger, nullable=True)
    current_count = Column(Integer, default=0, nullable=False)

    def __repr__(self):
        return f"<ServerConfig(guild_id={self.guild_id})>"

class Cook(Base):
    """Table pour stocker l'état du Cuisinier pour chaque serveur."""
    __tablename__ = 'cook'
    
    guild_id = Column(BigInteger, primary_key=True, autoincrement=False)
    energy = Column(Integer, default=100, nullable=False)
    thirst = Column(Integer, default=100, nullable=False)
    hunger = Column(Integer, default=100, nullable=False)
    sleep = Column(Integer, default=100, nullable=False)
    craving = Column(Integer, default=0, nullable=False)
    wallet = Column(Float, default=0.0, nullable=False)

    def __repr__(self):
        return f"<Cook(guild_id={self.guild_id}, energy={self.energy})>"