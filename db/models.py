# --- db/models.py ---
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship
from db.database import Base # Import Base from your database module
import datetime

class ServerState(Base):
    __tablename__ = "server_state"
    id = Column(Integer, primary_key=True)
    guild_id = Column(String, unique=True)
    admin_role_id = Column(String, nullable=True) # Ajouter cette ligne
    game_channel_id = Column(String, nullable=True) # Ajouter cette ligne
    game_started = Column(Boolean, default=False) # Ajouter cette ligne
    game_start_time = Column(DateTime, nullable=True)
    phys = Column(Float, default=100)
    ment = Column(Float, default=100)
    happy = Column(Float, default=80)
    stress = Column(Float, default=20)
    food = Column(Float, default=100)
    water = Column(Float, default=100)
    energy = Column(Float, default=100)
    addiction = Column(Float, default=0)
    pain = Column(Float, default=0)
    bladder = Column(Float, default=0)
    trip = Column(Float, default=0)
    tox = Column(Float, default=0)
    wallet = Column(Integer, default=0)
    last_update = Column(DateTime, default=datetime.datetime.utcnow)

class PlayerProfile(Base):
    __tablename__ = "player_profile"

    id = Column(Integer, primary_key=True) # Primary key for SQLAlchemy

    # Liens avec le serveur et l'utilisateur Discord
    guild_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)

    # Informations de base
    nickname = Column(String, nullable=True) # Le pseudo actuel du joueur dans le jeu

    # Statistiques essentielles (remplaçant ou complétant celles de ServerState si elles sont par joueur)
    health = Column(Float, default=100.0)
    energy = Column(Float, default=100.0)
    hunger = Column(Float, default=0.0) # 0 = plein, 100 = mort de faim
    thirst = Column(Float, default=0.0) # 0 = plein, 100 = déshydraté
    body_temperature = Column(Float, default=37.0) # En degrés Celsius
    hygiene = Column(Float, default=0.0) # 0 = propre, 100 = sale
    pain = Column(Float, default=0.0) # Intensité de la douleur, 0 = aucune
    bladder = Column(Float, default=0.0) # Besoin d'uriner, 0 = vide, 100 = besoin urgent

    # Santé Mentale & Émotionnelle
    sanity = Column(Float, default=100.0)
    stress = Column(Float, default=0.0) # 0 = calme, 100 = panique totale
    mood = Column(Float, default=0.0) # Peut être mappé à une échelle (ex: -50 dépression, 0 neutre, +50 joie)
    happiness = Column(Float, default=0.0) # Niveau de bonheur intrinsèque
    irritability = Column(Float, default=0.0) # Escalade la négativité, 0 = calme
    fear = Column(Float, default=0.0)
    loneliness = Column(Float, default=0.0)
    boredom = Column(Float, default=0.0)
    concentration = Column(Float, default=100.0)

    # Addiction & Consommation
    # Exemples: Gérer chaque substance courante ou une "score général d'addiction"
    drug_addiction = Column(Float, default=0.0) # Score d'addiction global, à affiner
    withdrawal_severity = Column(Float, default=0.0) # Intensité des symptômes de sevrage

    # État d'intoxication ou "trip"
    intoxication_level = Column(Float, default=0.0) # Niveau de drogue ou stimulant dans le corps

    # Statistiques de Progression
    wallet = Column(Integer, default=0) # Le portefeuille
    last_update = Column(DateTime, default=datetime.datetime.utcnow) # Dernière fois que les stats ont été calculées/mises à jour

    # Optionnel : Liens avec d'autres modèles si nécessaire
    # server_state = relationship("ServerState", back_populates="players") # Si ServerState avait une liste de players

    # Constraints and Indexes
    __table_args__ = (
        UniqueConstraint('guild_id', 'user_id', name='uq_guild_user'),
    )

class ActionLog(Base):
    __tablename__ = "action_log"
    id = Column(Integer, primary_key=True)
    guild_id = Column(String)
    user_id = Column(String)
    action = Column(String)
    effect = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)