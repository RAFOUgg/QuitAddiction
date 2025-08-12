# --- db/models.py (CORRECTED AND CLEANED) ---
try:
    from db.database import Base
except ImportError:
    print("CRITICAL ERROR IN MODELS.PY: CANNOT IMPORT Base FROM db.database.py!")
    print("--> Check import paths and ensure no circular dependencies.")
    raise

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, BigInteger, UniqueConstraint
import datetime

class ServerState(Base):
    __tablename__ = "server_state"
    id = Column(Integer, primary_key=True)
    guild_id = Column(String, unique=True, nullable=False)
    
    # --- CONFIGURATION DU JEU ---
    admin_role_id = Column(BigInteger, nullable=True)
    game_channel_id = Column(BigInteger, nullable=True)
    game_message_id = Column(BigInteger, nullable=True)
    
    # Statut du jeu
    game_started = Column(Boolean, default=False)
    game_start_time = Column(DateTime, nullable=True)
    
    # Paramètres de la partie
    game_mode = Column(String, default="medium")
    duration_key = Column(String, nullable=True, default="medium")
    game_tick_interval_minutes = Column(Integer, default=30)
    
    # Taux de dégradation (dépendent du mode de jeu)
    degradation_rate_hunger = Column(Float, default=10.0)
    degradation_rate_thirst = Column(Float, default=8.0)
    degradation_rate_bladder = Column(Float, default=15.0)
    degradation_rate_energy = Column(Float, default=5.0)
    degradation_rate_stress = Column(Float, default=3.0)
    degradation_rate_boredom = Column(Float, default=7.0)
    
    # --- CONFIGURATION DES NOTIFICATIONS ---
    notify_vital_low_role_id = Column(String, nullable=True)      
    notify_critical_role_id = Column(String, nullable=True)       
    notify_envie_fumer_role_id = Column(String, nullable=True)     
    notify_friend_message_role_id = Column(String, nullable=True)  
    notify_shop_promo_role_id = Column(String, nullable=True)      

    # --- PRÉFÉRENCES DE NOTIFICATION ---
    notify_on_low_vital_stat = Column(Boolean, nullable=False, default=True) 
    notify_on_critical_event = Column(Boolean, nullable=False, default=True) 
    notify_on_envie_fumer = Column(Boolean, nullable=False, default=True) 
    notify_on_friend_message = Column(Boolean, nullable=False, default=True) 
    notify_on_shop_promo = Column(Boolean, nullable=False, default=False) 

    # Taux de dégradation des besoins vitaux (peut être ajusté par le game_mode)
    degradation_rate_hunger = Column(Float, default=10.0)
    degradation_rate_thirst = Column(Float, default=8.0)
    degradation_rate_bladder = Column(Float, default=15.0)
    degradation_rate_energy = Column(Float, default=5.0)
    degradation_rate_stress = Column(Float, default=3.0)
    degradation_rate_boredom = Column(Float, default=7.0)

    # --- STATUTS DU JOUEUR ---
    phys = Column(Float, default=100.0) 
    ment = Column(Float, default=100.0)
    happy = Column(Float, default=80.0)
    stress = Column(Float, default=20.0)
    food = Column(Float, default=100.0)
    water = Column(Float, default=100.0)
    energy = Column(Float, default=100.0)
    addiction = Column(Float, default=0.0) # Niveau général d'addiction
    pain = Column(Float, default=0.0)      # Niveau de douleur
    bladder = Column(Float, default=0.0)   # Besoin d'uriner (0=vide, 100=urgent)
    trip = Column(Float, default=0.0)      # État d'intoxication / trip
    tox = Column(Float, default=0.0)       # Toxines accumulées

    wallet = Column(Integer, default=0)    # Argent global du serveur (ou du cuisinier)

    # Constraint pour garantir qu'un guild_id est unique dans cette table
    __table_args__ = (
        UniqueConstraint('guild_id', name='uq_guild_server_state'),
    )

class PlayerProfile(Base):
    __tablename__ = "player_profile"
    id = Column(Integer, primary_key=True)
    
    # Clé composite pour identifier un personnage unique par serveur
    guild_id = Column(String, nullable=False, index=True)
    
    # --- STATS VITALES & PHYSIQUES ---
    health = Column(Float, default=100.0)
    energy = Column(Float, default=100.0)
    hunger = Column(Float, default=0.0)
    thirst = Column(Float, default=0.0)
    bladder = Column(Float, default=0.0)
    pain = Column(Float, default=0.0)
    tox = Column(Float, default=0.0)

    # --- STATS MENTALES & ÉMOTIONNELLES ---
    sanity = Column(Float, default=100.0)
    stress = Column(Float, default=0.0)
    happiness = Column(Float, default=50.0)
    boredom = Column(Float, default=0.0)

    # --- ADDICTION & CONSOMMATION ---
    substance_addiction_level = Column(Float, default=0.0)
    withdrawal_severity = Column(Float, default=0.0)
    intoxication_level = Column(Float, default=0.0)

    # --- AUTRES ---
    wallet = Column(Integer, default=20)
    last_update = Column(DateTime, default=datetime.datetime.utcnow)

    # NOTE : 'user_id' est retiré pour l'instant car le bot gère UN personnage par serveur.
    # On l'identifiera par le guild_id.
    __table_args__ = (
        UniqueConstraint('guild_id', name='uq_guild_player'),
    )

# --- Modèle pour l'historique des actions ---
class ActionLog(Base):
    __tablename__ = "action_log"
    id = Column(Integer, primary_key=True)
    guild_id = Column(String, index=True)
    user_id = Column(String, index=True)
    action = Column(String)
    effect = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)