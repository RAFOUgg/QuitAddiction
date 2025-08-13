# --- db/models.py (FINAL VERSION) ---

from db.database import Base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, BigInteger, UniqueConstraint, Text
import datetime

class ServerState(Base):
    __tablename__ = "server_state"
    id = Column(Integer, primary_key=True)
    guild_id = Column(String, unique=True, nullable=False)
    admin_role_id = Column(BigInteger, nullable=True)
    game_channel_id = Column(BigInteger, nullable=True)
    game_message_id = Column(BigInteger, nullable=True)
    notification_role_id = Column(BigInteger, nullable=True)
    game_started = Column(Boolean, default=False)
    game_start_time = Column(DateTime, nullable=True)
    game_mode = Column(String, default="medium")
    duration_key = Column(String, nullable=True, default="medium")
    game_tick_interval_minutes = Column(Integer, default=30)
    degradation_rate_hunger = Column(Float, default=10.0)
    degradation_rate_thirst = Column(Float, default=8.0)
    degradation_rate_bladder = Column(Float, default=15.0)
    degradation_rate_energy = Column(Float, default=5.0)
    degradation_rate_stress = Column(Float, default=3.0)
    degradation_rate_boredom = Column(Float, default=7.0)
    notify_on_low_vital_stat = Column(Boolean, default=True)
    is_test_mode = Column(Boolean, default=False)

class PlayerProfile(Base):
    __tablename__ = "player_profile"
    id = Column(Integer, primary_key=True)
    guild_id = Column(String, nullable=False, index=True, unique=True)

    # === SECTION 1: SANTÉ PHYSIQUE DE BASE ===
    health = Column(Float, default=100.0)
    energy = Column(Float, default=100.0)
    pain = Column(Float, default=0.0)
    tox = Column(Float, default=0.0)

    # === SECTION 2: BESOINS IMMÉDIATS (0 = satisfait, 100 = critique) ===
    hunger = Column(Float, default=0.0)
    thirst = Column(Float, default=0.0)
    bladder = Column(Float, default=0.0)
    fatigue = Column(Float, default=0.0)

    # === SECTION 3: ÉTAT MENTAL & ÉMOTIONNEL ===
    sanity = Column(Float, default=100.0)
    stress = Column(Float, default=0.0)
    happiness = Column(Float, default=50.0)
    boredom = Column(Float, default=0.0)
    
    # === SECTION 4: SYMPTÔMES SPÉCIFIQUES (lié à la conso & santé) ===
    nausea = Column(Float, default=0.0)
    dizziness = Column(Float, default=0.0)
    headache = Column(Float, default=0.0)
    dry_mouth = Column(Float, default=0.0)
    sore_throat = Column(Float, default=0.0)
    
    # === SECTION 5: ADDICTION & CONSOMMATION ===
    substance_addiction_level = Column(Float, default=0.0)
    withdrawal_severity = Column(Float, default=0.0)
    intoxication_level = Column(Float, default=0.0)

    # === SECTION 6: AUTRES & MÉTA-DONNÉES ===
    wallet = Column(Integer, default=20)
    
    
    # --- Inventaire ---
    cigarettes = Column(Integer, default=5)
    beers = Column(Integer, default=0)
    water_bottles = Column(Integer, default=2)
    food_servings = Column(Integer, default=1)
    joints = Column(Integer, default=0)

    # --- Cooldowns & Timestamps ---
    last_update = Column(DateTime, default=datetime.datetime.utcnow)
    last_action_at = Column(DateTime, nullable=True) # Pour le cooldown global
    last_eaten_at = Column(DateTime, nullable=True)
    last_drank_at = Column(DateTime, nullable=True)
    last_slept_at = Column(DateTime, nullable=True)
    last_smoked_at = Column(DateTime, nullable=True)
    last_urinated_at = Column(DateTime, nullable=True)

    # --- Flags Narratifs ---
    has_unlocked_joints = Column(Boolean, default=False)

    # --- NOUVEAU CHAMP ---
    recent_logs = Column(Text, default="")

    __table_args__ = (UniqueConstraint('guild_id', name='uq_guild_player'),)


# ActionLog reste inchangé
class ActionLog(Base):
    __tablename__ = "action_log"
    id = Column(Integer, primary_key=True)
    guild_id = Column(String, index=True)
    user_id = Column(String, index=True)
    action = Column(String)
    effect = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)