# --- db/models.py (CORRECTED WITH NEW ATTRIBUTES) ---

from db.database import Base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, BigInteger, UniqueConstraint, Text
import datetime
from typing import Optional

class ServerState(Base):
    __tablename__ = "server_state"
    id: int = Column(Integer, primary_key=True)
    guild_id: str = Column(String, unique=True, nullable=False)
    admin_role_id: Optional[int] = Column(BigInteger, nullable=True)
    notification_role_id: Optional[int] = Column(BigInteger, nullable=True)
    game_channel_id: Optional[int] = Column(BigInteger, nullable=True)
    game_message_id: Optional[int] = Column(BigInteger, nullable=True)
    game_started: bool = Column(Boolean, default=False)
    game_start_time: Optional[datetime.datetime] = Column(DateTime, nullable=True)
    game_day_start_hour: int = Column(Integer, default=8)
    game_mode: str = Column(String, default="medium")
    duration_key: Optional[str] = Column(String, nullable=True, default="medium")
    game_minutes_per_day: int = Column(Integer, default=720)
    
    # CORRECTION: Ajout de la colonne manquante
    game_tick_interval_minutes: int = Column(Integer, default=30)
    
    degradation_rate_hunger: float = Column(Float, default=10.0)
    degradation_rate_thirst: float = Column(Float, default=8.0)
    degradation_rate_bladder: float = Column(Float, default=15.0)
    degradation_rate_energy: float = Column(Float, default=5.0)
    degradation_rate_stress: float = Column(Float, default=3.0)
    degradation_rate_boredom: float = Column(Float, default=7.0)
    degradation_rate_hygiene: float = Column(Float, default=4.0)
    is_test_mode: bool = Column(Boolean, default=False)

    # Notification Role IDs
    notify_vital_low_role_id: Optional[int] = Column(BigInteger, nullable=True)
    notify_critical_role_id: Optional[int] = Column(BigInteger, nullable=True)
    notify_craving_role_id: Optional[int] = Column(BigInteger, nullable=True)
    notify_friend_message_role_id: Optional[int] = Column(BigInteger, nullable=True)
    notify_shop_promo_role_id: Optional[int] = Column(BigInteger, nullable=True)

    # Notification Toggles
    notify_on_low_vital_stat: bool = Column(Boolean, default=True)
    notify_on_critical_event: bool = Column(Boolean, default=True)
    notify_on_craving: bool = Column(Boolean, default=True)
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
    bowels: float = Column(Float, default=0.0)

    # === SECTION 3: ÉTAT MENTAL & ÉMOTIONNEL ===
    sanity: float = Column(Float, default=100.0)
    stress: float = Column(Float, default=0.0)
    happiness: float = Column(Float, default=50.0)
    boredom: float = Column(Float, default=0.0)
    
    # === SECTION 4: SYMPTÔMES SPÉCIFIQUES ===
    nausea: float = Column(Float, default=0.0)
    dizziness: float = Column(Float, default=0.0)
    headache: float = Column(Float, default=0.0)
    dry_mouth: float = Column(Float, default=0.0)
    sore_throat: float = Column(Float, default=0.0)
    stomachache: float = Column(Float, default=0.0)
    
    # === SECTION 5: ADDICTION & CONSOMMATION ===
    substance_addiction_level: float = Column(Float, default=0.0)
    substance_tolerance: float = Column(Float, default=0.0)
    withdrawal_severity: float = Column(Float, default=0.0)
    intoxication_level: float = Column(Float, default=0.0)
    guilt: float = Column(Float, default=0.0)
    craving_nicotine: float = Column(Float, default=0.0, nullable=False)
    craving_alcohol: float = Column(Float, default=0.0, nullable=False)
    craving_cannabis: float = Column(Float, default=0.0, nullable=False)
    sex_drive: float = Column(Float, default=10.0, nullable=False)

    # === SECTION 6: STATS DE VIE ET LONG TERME ===
    willpower: float = Column(Float, default=80.0)
    hygiene: float = Column(Float, default=100.0)
    job_performance: float = Column(Float, default=75.0)
    immune_system: float = Column(Float, default=100.0)
    is_sick: bool = Column(Boolean, default=False)

    # === SECTION 7: AUTRES & MÉTA-DONNÉES ===
    wallet: int = Column(Integer, default=20)
    show_stats_in_view: bool = Column(Boolean, default=False)
    
    # NOUVEAU: Ajout du flag pour l'inventaire
    show_inventory_in_view: bool = Column(Boolean, default=False)
    
    recent_logs: str = Column(Text, default="")
    
    # --- Inventaire ---
    food_servings: int = Column(Integer, default=1)
    water_bottles: int = Column(Integer, default=5)
    soda_cans: int = Column(Integer, default=1)
    cigarettes: int = Column(Integer, default=5)
    e_cigarettes: int = Column(Integer, default=0)
    beers: int = Column(Integer, default=0)
    tacos: int = Column(Integer, default=0)
    salad_servings: int = Column(Integer, default=0)
    wine_bottles: int = Column(Integer, default=0)
    joints: int = Column(Integer, default=0)

    # --- Notifications Config ---
    notifications_config: str = Column(Text, default="")
    notification_history: str = Column(Text, default="")

    # --- Timestamps & Cooldowns ---
    last_update: datetime.datetime = Column(DateTime, default=datetime.datetime.utcnow)
    last_action_at: Optional[datetime.datetime] = Column(DateTime, nullable=True)
    last_action: Optional[str] = Column(String, nullable=True)
    last_action_time: Optional[datetime.datetime] = Column(DateTime, nullable=True)
    #... (autres timestamps)
    last_eaten_at: Optional[datetime.datetime] = Column(DateTime, nullable=True)
    last_drank_at: Optional[datetime.datetime] = Column(DateTime, nullable=True)
    last_slept_at: Optional[datetime.datetime] = Column(DateTime, nullable=True)
    last_smoked_at: Optional[datetime.datetime] = Column(DateTime, nullable=True)
    last_urinated_at: Optional[datetime.datetime] = Column(DateTime, nullable=True)
    last_shower_at: Optional[datetime.datetime] = Column(DateTime, nullable=True)
    sickness_end_time: Optional[datetime.datetime] = Column(DateTime, nullable=True)
    last_defecated_at: Optional[datetime.datetime] = Column(DateTime, nullable=True)

    # --- Flags Narratifs ---
    has_unlocked_smokeshop: bool = Column(Boolean, default=False)
    messages: str = Column(Text, default="")

    __table_args__ = (UniqueConstraint('guild_id', name='uq_guild_player'),)

class ActionLog(Base):
    __tablename__ = "action_log"
    id: int = Column(Integer, primary_key=True)
    guild_id: str = Column(String, index=True)
    user_id: str = Column(String, index=True)
    action: str = Column(String)
    effect: str = Column(String)
    timestamp: datetime.datetime = Column(DateTime, default=datetime.datetime.utcnow)