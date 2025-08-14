# --- db/models.py (CORRECTED) ---

from db.database import Base  # Importer la Base centralisée
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, BigInteger, UniqueConstraint, Text
import datetime
from typing import Optional

# Les lignes suivantes ont été supprimées car elles recréaient une Base vide,
# ce qui est la cause de l'erreur "no such table".
# from sqlalchemy.orm import declarative_base
# Base = declarative_base()

class ServerState(Base):
    __tablename__ = "server_state"
    id: int = Column(Integer, primary_key=True)
    guild_id: str = Column(String, unique=True, nullable=False)
    admin_role_id: Optional[int] = Column(BigInteger, nullable=True)
    game_channel_id: Optional[int] = Column(BigInteger, nullable=True)
    game_message_id: Optional[int] = Column(BigInteger, nullable=True)
    notification_role_id: Optional[int] = Column(BigInteger, nullable=True)
    game_started: bool = Column(Boolean, default=False)
    game_start_time: Optional[datetime.datetime] = Column(DateTime, nullable=True)
    game_day_start_hour: int = Column(Integer, default=8)
    game_mode: str = Column(String, default="medium")
    duration_key: Optional[str] = Column(String, nullable=True, default="medium")
    game_tick_interval_minutes: int = Column(Integer, default=30)
    degradation_rate_hunger: float = Column(Float, default=10.0)
    degradation_rate_thirst: float = Column(Float, default=8.0)
    degradation_rate_bladder: float = Column(Float, default=15.0)
    degradation_rate_energy: float = Column(Float, default=5.0)
    degradation_rate_stress: float = Column(Float, default=3.0)
    degradation_rate_boredom: float = Column(Float, default=7.0)
    degradation_rate_hygiene: float = Column(Float, default=4.0) # Nouvelle ligne
    notify_on_low_vital_stat: bool = Column(Boolean, default=True)
    is_test_mode: bool = Column(Boolean, default=False)
    notify_vital_low_role_id: Optional[int] = Column(BigInteger, nullable=True)
    notify_critical_role_id: Optional[int] = Column(BigInteger, nullable=True)
    notify_envie_fumer_role_id: Optional[int] = Column(BigInteger, nullable=True)
    notify_friend_message_role_id: Optional[int] = Column(BigInteger, nullable=True)
    notify_shop_promo_role_id: Optional[int] = Column(BigInteger, nullable=True)
    notify_on_critical_event: bool = Column(Boolean, default=True)
    notify_on_envie_fumer: bool = Column(Boolean, default=True)
    notify_on_friend_message: bool = Column(Boolean, default=True)
    notify_on_shop_promo: bool = Column(Boolean, default=True)


class PlayerProfile(Base):
    __tablename__ = "player_profile"
    id: int = Column(Integer, primary_key=True)
    guild_id: str = Column(String, nullable=False, index=True, unique=True)

    # === SECTION 1: SANTÉ PHYSIQUE DE BASE ===
    health: float = Column(Float, default=100.0)
    energy: float = Column(Float, default=100.0)
    pain: float = Column(Float, default=0.0)
    tox: float = Column(Float, default=0.0)

    # === SECTION 2: BESOINS IMMÉDIATS (0 = satisfait, 100 = critique) ===
    hunger: float = Column(Float, default=0.0)
    thirst: float = Column(Float, default=0.0)
    bladder: float = Column(Float, default=0.0)
    fatigue: float = Column(Float, default=0.0)

    # === SECTION 3: ÉTAT MENTAL & ÉMOTIONNEL ===
    sanity: float = Column(Float, default=100.0)
    stress: float = Column(Float, default=0.0)
    happiness: float = Column(Float, default=50.0)
    boredom: float = Column(Float, default=0.0)
    
    # --- NEW: Physical/Mental states for visuals ---
    stomachache: float = Column(Float, default=0.0)  # Mal de ventre
    headache: float = Column(Float, default=0.0)     # Already present, but ensure it's used
    urge_to_pee: float = Column(Float, default=0.0)  # Envie pressante
    craving: float = Column(Float, default=0.0)      # Envie de fumer/boire
    craving_nicotine = Column(Float, default=0.0, nullable=False)
    craving_alcohol = Column(Float, default=0.0, nullable=False)
    craving_cannabis = Column(Float, default=0.0, nullable=False)
    sex_drive = Column(Float, default=10.0, nullable=False) # Le cuisinier a des besoins...

    # === SECTION 4: SYMPTÔMES SPÉCIFIQUES (lié à la conso & santé) ===
    nausea: float = Column(Float, default=0.0)
    dizziness: float = Column(Float, default=0.0)
    headache: float = Column(Float, default=0.0)
    dry_mouth: float = Column(Float, default=0.0)
    sore_throat: float = Column(Float, default=0.0)
    
    # === SECTION 5: ADDICTION & CONSOMMATION ===
    substance_addiction_level: float = Column(Float, default=0.0)
    substance_tolerance: float = Column(Float, default=0.0) # NOUVEAU
    withdrawal_severity: float = Column(Float, default=0.0)
    intoxication_level: float = Column(Float, default=0.0)
    guilt: float = Column(Float, default=0.0) # NOUVEAU

    # === SECTION 6: STATS DE VIE ET LONG TERME (NOUVEAU) ===
    willpower: float = Column(Float, default=80.0)   # Volonté / Maîtrise de soi
    hygiene: float = Column(Float, default=100.0) # Hygiène
    job_performance: float = Column(Float, default=75.0) # Performance au travail
    immune_system: float = Column(Float, default=100.0)  # Système immunitaire
    is_sick: bool = Column(Boolean, default=False)  # Est actuellement malade

    # === SECTION 7: AUTRES & MÉTA-DONNÉES ===
    wallet: int = Column(Integer, default=20)  # 20€ par défaut
    
    # --- Inventaire ---
    food_servings: int = Column(Integer, default=1)  # 1 sandwich
    water_bottles: int = Column(Integer, default=5)  # 5 bouteilles d'eau
    soda_cans: int = Column(Integer, default=1)    # 1 soda
    cigarettes: int = Column(Integer, default=5)    # 5 cigarettes
    beers: int = Column(Integer, default=0)
    joints: int = Column(Integer, default=0)
    tacos: int = Column(Integer, default=0)
    e_cigarettes: int = Column(Integer, default=0)
    whisky_bottles: int = Column(Integer, default=0)
    wine_bottles: int = Column(Integer, default=0)
    salad_servings: int = Column(Integer, default=0)
    orange_juice: int = Column(Integer, default=0)
    vaporizer: int = Column(Integer, default=0)
    chilum: int = Column(Integer, default=0)
    bhang: int = Column(Integer, default=0)

    # --- Notifications Config ---
    notifications_config: str = Column(Text, default="")  # JSON string stockant la config des notifs
    notification_history: str = Column(Text, default="")  # Historique des notifications

    # --- Cooldowns & Timestamps ---
    last_update: datetime.datetime = Column(DateTime, default=datetime.datetime.utcnow)
    last_action_at: Optional[datetime.datetime] = Column(DateTime, nullable=True)
    last_eaten_at: Optional[datetime.datetime] = Column(DateTime, nullable=True)
    last_drank_at: Optional[datetime.datetime] = Column(DateTime, nullable=True)
    last_slept_at: Optional[datetime.datetime] = Column(DateTime, nullable=True)
    last_smoked_at: Optional[datetime.datetime] = Column(DateTime, nullable=True)
    last_urinated_at: Optional[datetime.datetime] = Column(DateTime, nullable=True)
    last_shower_at: Optional[datetime.datetime] = Column(DateTime, nullable=True) # NOUVEAU
    sickness_end_time: Optional[datetime.datetime] = Column(DateTime, nullable=True) # NOUVEAU

    # --- Flags Narratifs ---
    has_unlocked_joints: bool = Column(Boolean, default=False)
    has_unlocked_smokeshop: bool = Column(Boolean, default=False)
    messages: str = Column(Text, default="")

    # --- Logging pour le mode test ---
    recent_logs: str = Column(Text, default="")

    # --- For image switching ---
    last_action: str = Column(String, default=None)
    last_action_time: datetime.datetime = Column(DateTime, nullable=True)
    show_stats_in_view: bool = Column(Boolean, default=False)
    image_hidden_in_view: bool = Column(Boolean, default=False)

    __table_args__ = (UniqueConstraint('guild_id', name='uq_guild_player'),)


class ActionLog(Base):
    __tablename__ = "action_log"
    id: int = Column(Integer, primary_key=True)
    guild_id: str = Column(String, index=True)
    user_id: str = Column(String, index=True)
    action: str = Column(String)
    effect: str = Column(String)
    timestamp: datetime.datetime = Column(DateTime, default=datetime.datetime.utcnow)
