try:
    from db.database import Base 
except ImportError:
    print("ERREUR DANS MODELS.PY: IMPOSSIBLE D'IMPORTER Base DE db.database.py ! Le chemin est-il correct depuis ce dossier?")
    raise # Ce bloc doit normalement laisser le chemin tel quel, ou utiliser le mock SEULEMENT pour les IDEs. Le problème runtime vient du chemin.

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey, UniqueConstraint # <-- Assurez-vous que TOUT ceci est importé ICI
import datetime

class ServerState(Base):
    __tablename__ = "server_state"
    id = Column(Integer, primary_key=True) 
    guild_id = Column(String, unique=True, nullable=False) 
    admin_role_id = Column(String, nullable=True) 
    game_channel_id = Column(String, nullable=True)
    game_started = Column(Boolean, default=False)
    duration_key = Column(String, nullable=True, default="medium")
    game_mode = Column(String, default="medium")
    game_tick_interval_minutes = Column(Integer, default=30) 
    game_start_time = Column(DateTime, nullable=True)
    degradation_rate_hunger = Column(Float, default=10.0)
    degradation_rate_thirst = Column(Float, default=8.0)
    degradation_rate_bladder = Column(Float, default=15.0)
    degradation_rate_energy = Column(Float, default=5.0)
    degradation_rate_stress = Column(Float, default=3.0)
    degradation_rate_boredom = Column(Float, default=7.0)
    degradation_rate_addiction_base = Column(Float, default=0.1)
    degradation_rate_toxins_base = Column(Float, default=0.5)
    # Et les autres champs (phys, ment, happy, etc.) qui étaient déjà là
    phys = Column(Float, default=100.0) 
    ment = Column(Float, default=100.0)
    happy = Column(Float, default=80.0)
    stress = Column(Float, default=20.0)
    food = Column(Float, default=100.0)
    water = Column(Float, default=100.0)
    energy = Column(Float, default=100.0)
    addiction = Column(Float, default=0.0)
    pain = Column(Float, default=0.0)
    bladder = Column(Float, default=0.0)
    trip = Column(Float, default=0.0)
    tox = Column(Float, default=0.0)
    wallet = Column(Integer, default=0)
    last_update = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('guild_id', name='uq_guild_server_state'),
    )


class PlayerProfile(Base):
    __tablename__ = "player_profile"

    id = Column(Integer, primary_key=True)
    guild_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)

    nickname = Column(String, nullable=True)

    # Statistiques du joueur, elles représentent l'état de la personne
    # Ces variables sont MUTES par les dégradations (calculées via ServerState) et les actions.
    health = Column(Float, default=100.0)
    energy = Column(Float, default=100.0)
    hunger = Column(Float, default=0.0)         # 0 = P, 100 = M
    thirst = Column(Float, default=0.0)         # 0 = P, 100 = M
    bladder = Column(Float, default=0.0)        # 0 = V, 100 = URGENT
    pain = Column(Float, default=0.0)           # 0 = Aucun, 100 = Intense
    body_temperature = Column(Float, default=37.0) # Température corporelle
    hygiene = Column(Float, default=0.0)        # 0 = Propre, 100 = Sale

    sanity = Column(Float, default=100.0)
    stress = Column(Float, default=0.0)         # 0 = Calme, 100 = Panique
    mood = Column(Float, default=0.0)           # Peut être mappé à une échelle
    happiness = Column(Float, default=0.0)      # Nettement positif quand haut
    irritability = Column(Float, default=0.0)   # Augmente avec le stress et la négativité
    fear = Column(Float, default=0.0)
    loneliness = Column(Float, default=0.0)
    boredom = Column(Float, default=0.0)        # 0 = Stimulé, 100 = Ennuyé à mourir
    concentration = Column(Float, default=100.0)

    # Addiction & Consommation
    # Ici on va définir un état plus fin
    # Vous pourriez avoir une liste d'addictions et pour chacune un level/tolerance/sevrage.
    # Pour l'instant, on simplifie :
    substance_addiction_level = Column(Float, default=0.0) # Score général d'addiction pour *la* substance du jeu
    withdrawal_severity = Column(Float, default=0.0)      # Gravité du sevrage pour _cette_ addiction
    intoxication_level = Column(Float, default=0.0)       # Niveau actuel d'intoxication ("trip")

    wallet = Column(Integer, default=0)
    last_update = Column(DateTime, default=datetime.datetime.utcnow) # Derniere mise a jour DES STATS DU JOUEUR SPECIFIQUES

    __table_args__ = (
        UniqueConstraint('guild_id', 'user_id', name='uq_guild_user'),
    )

class ActionLog(Base):
    __tablename__ = "action_log"
    id = Column(Integer, primary_key=True)
    guild_id = Column(String, index=True) # Ajoutez index ici aussi
    user_id = Column(String, index=True) # Et ici
    action = Column(String)
    effect = Column(String) # Peut-être useful to log the effects string
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)