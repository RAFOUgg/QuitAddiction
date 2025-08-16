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

    # === SECTION 6.1: STATISTIQUES DE TRAVAIL ===
    total_minutes_late: int = Column(Integer, default=0)
    total_break_time: int = Column(Integer, default=0)
    total_work_time: int = Column(Integer, default=0)
    work_days_streak: int = Column(Integer, default=0)
    last_break_start: DateTime = Column(DateTime, nullable=True)

    # === SECTION 7: AUTRES & MÉTA-DONNÉES ===
    wallet: int = Column(Integer, default=20)
    show_stats_in_view: bool = Column(Boolean, default=False)
    show_inventory_in_view: bool = Column(Boolean, default=False)
    show_schedule_in_view: bool = Column(Boolean, default=False)
    recent_logs: str = Column(Text, default="")

    # === SECTION 8: STATUTS ACTUELS ===
    is_working: bool = Column(Boolean, default=False, nullable=False)
    is_on_break: bool = Column(Boolean, default=False, nullable=False)
    is_sleeping: bool = Column(Boolean, default=False, nullable=False)
    missed_work_days: int = Column(Integer, default=0, nullable=False)
    last_worked_at: Optional[datetime.datetime] = Column(DateTime, nullable=True)
    first_day_reward_given: bool = Column(Boolean, default=False, nullable=False)
    lateness_minutes: int = Column(Integer, default=0, nullable=False)
    has_completed_first_work_day: bool = Column(Boolean, default=False, nullable=False)
    
    # --- INVENTAIRE BASE ---
    food_servings = Column(Integer, default=1)
    water_bottles = Column(Integer, default=5)
    soda_cans = Column(Integer, default=1)
    cigarettes = Column(Integer, default=5)
    e_cigarettes = Column(Integer, default=0)
    beers = Column(Integer, default=0)
    tacos = Column(Integer, default=0)
    salad_servings = Column(Integer, default=0)
    wine_bottles = Column(Integer, default=0)
    joints = Column(Integer, default=0)

    # --- INVENTAIRE SMOKE SHOP ---
    weed_grams = Column(Integer, default=0)
    hash_grams = Column(Integer, default=0)
    cbd_grams = Column(Integer, default=0)
    tobacco_grams = Column(Integer, default=0)
    rolling_papers = Column(Integer, default=0)
    toncs = Column(Integer, default=0)
    has_grinder = Column(Boolean, default=False)
    has_bong = Column(Boolean, default=False)
    has_chillum = Column(Boolean, default=False)
    has_vaporizer = Column(Boolean, default=False)

    # --- HISTORIQUE DES CRAFTS ---
    joints_crafted = Column(Integer, default=0)
    bong_uses = Column(Integer, default=0)
    chillum_uses = Column(Integer, default=0)
    vaporizer_uses = Column(Integer, default=0)

    # --- Notifications Config ---

    # --- INVENTAIRE SMOKE SHOP ---
    weed_grams: int = Column(Integer, default=0)
    hash_grams: int = Column(Integer, default=0)
    cbd_grams: int = Column(Integer, default=0)
    tobacco_grams: int = Column(Integer, default=0)
    rolling_papers: int = Column(Integer, default=0)
    toncs: int = Column(Integer, default=0)
    has_grinder: bool = Column(Boolean, default=False)
    has_bong: bool = Column(Boolean, default=False)
    has_chillum: bool = Column(Boolean, default=False)
    has_vaporizer: bool = Column(Boolean, default=False)

    # --- HISTORIQUE DES CRAFTS ---
    joints_crafted: int = Column(Integer, default=0)
    bong_uses: int = Column(Integer, default=0)
    chillum_uses: int = Column(Integer, default=0)
    vaporizer_uses: int = Column(Integer, default=0)

    # --- Notifications Config ---
    notifications_config: str = Column(Text, default="")
    notification_history: str = Column(Text, default="")

    # --- Timestamps & Cooldowns ---
    last_update: datetime.datetime = Column(DateTime, default=datetime.datetime.utcnow)
    last_action_at: Optional[datetime.datetime] = Column(DateTime, nullable=True)
    last_action: Optional[str] = Column(String, nullable=True)
    last_action_time: Optional[datetime.datetime] = Column(DateTime, nullable=True)
    action_cooldown_end_time: Optional[datetime.datetime] = Column(DateTime, nullable=True)
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
    
    # --- Téléphone ---
    phone_uses_today: int = Column(Integer, default=0)
    last_phone_reset_at: Optional[datetime.datetime] = Column(DateTime, nullable=True)

    __table_args__ = (UniqueConstraint('guild_id', name='uq_guild_player'),)

class ActionLog(Base):
    __tablename__ = "action_log"
    id: int = Column(Integer, primary_key=True)
    guild_id: str = Column(String, index=True)
    user_id: str = Column(String, index=True)
    action: str = Column(String)
    effect: str = Column(String)
    timestamp: datetime.datetime = Column(DateTime, default=datetime.datetime.utcnow)