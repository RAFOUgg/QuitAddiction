# --- db/models.py ---
# type: ignore

from __future__ import annotations

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime, Integer, String, Boolean, Float, BigInteger, Text

from db.database import Base

class ServerState(Base):
    __tablename__ = 'server_state'

    # === Core Fields ===
    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    admin_role_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    notification_role_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    game_channel_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    game_message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    game_started: Mapped[bool] = mapped_column(Boolean, default=False)
    game_start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    game_day_start_hour: Mapped[int] = mapped_column(Integer, default=8)
    game_mode: Mapped[str] = mapped_column(String, default="medium")
    duration_key: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="medium")
    
    # === Game Configuration ===
    # Timing
    game_minutes_per_day: Mapped[int] = mapped_column(Integer, default=720)
    game_tick_interval_minutes: Mapped[int] = mapped_column(Integer, default=30)
    
    # Degradation Rates
    degradation_rate_hunger: Mapped[float] = mapped_column(Float, default=10.0)
    degradation_rate_thirst: Mapped[float] = mapped_column(Float, default=8.0)
    degradation_rate_bladder: Mapped[float] = mapped_column(Float, default=15.0)
    degradation_rate_energy: Mapped[float] = mapped_column(Float, default=5.0)
    degradation_rate_stress: Mapped[float] = mapped_column(Float, default=3.0)
    degradation_rate_boredom: Mapped[float] = mapped_column(Float, default=7.0)
    degradation_rate_hygiene: Mapped[float] = mapped_column(Float, default=4.0)
    
    # Game State
    is_test_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # === Notification Configuration ===
    # Role IDs
    notify_vital_low_role_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    notify_critical_role_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    notify_craving_role_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    notify_friend_message_role_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    notify_shop_promo_role_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Notification Toggles
    notify_on_low_vital_stat: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_critical_event: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_craving: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_friend_message: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_shop_promo: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Core fields
    id: Mapped[int] = mapped_column("id", Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column("guild_id", String, unique=True, nullable=False)
    admin_role_id: Mapped[Optional[int]] = mapped_column("admin_role_id", BigInteger, nullable=True)
    notification_role_id: Mapped[Optional[int]] = mapped_column("notification_role_id", BigInteger, nullable=True)
    game_channel_id: Mapped[Optional[int]] = mapped_column("game_channel_id", BigInteger, nullable=True)
    game_message_id: Mapped[Optional[int]] = mapped_column("game_message_id", BigInteger, nullable=True)
    game_started: Mapped[bool] = mapped_column("game_started", Boolean, default=False)
    game_start_time: Mapped[Optional[datetime]] = mapped_column("game_start_time", DateTime, nullable=True)
    game_day_start_hour: Mapped[int] = mapped_column("game_day_start_hour", Integer, default=8)
    game_mode: Mapped[str] = mapped_column("game_mode", String, default="medium")
    duration_key: Mapped[Optional[str]] = mapped_column("duration_key", String, nullable=True, default="medium")
    
    # Game timing configuration
    game_minutes_per_day: Mapped[int] = mapped_column("game_minutes_per_day", Integer, default=720)
    game_tick_interval_minutes: Mapped[int] = mapped_column("game_tick_interval_minutes", Integer, default=30)
    
    # Degradation rates
    degradation_rate_hunger: Mapped[float] = mapped_column("degradation_rate_hunger", Float, default=10.0)
    degradation_rate_thirst: Mapped[float] = mapped_column("degradation_rate_thirst", Float, default=8.0)
    degradation_rate_bladder: Mapped[float] = mapped_column("degradation_rate_bladder", Float, default=15.0)
    degradation_rate_energy: Mapped[float] = mapped_column("degradation_rate_energy", Float, default=5.0)
    degradation_rate_stress: Mapped[float] = mapped_column("degradation_rate_stress", Float, default=3.0)
    degradation_rate_boredom: Mapped[float] = mapped_column("degradation_rate_boredom", Float, default=7.0)
    degradation_rate_hygiene: Mapped[float] = mapped_column("degradation_rate_hygiene", Float, default=4.0)
    is_test_mode: Mapped[bool] = mapped_column("is_test_mode", Boolean, default=False)
    
    # Notification Role IDs
    notify_vital_low_role_id: Mapped[Optional[int]] = mapped_column("notify_vital_low_role_id", BigInteger, nullable=True)
    notify_critical_role_id: Mapped[Optional[int]] = mapped_column("notify_critical_role_id", BigInteger, nullable=True)
    notify_craving_role_id: Mapped[Optional[int]] = mapped_column("notify_craving_role_id", BigInteger, nullable=True)
    notify_friend_message_role_id: Mapped[Optional[int]] = mapped_column("notify_friend_message_role_id", BigInteger, nullable=True)
    notify_shop_promo_role_id: Mapped[Optional[int]] = mapped_column("notify_shop_promo_role_id", BigInteger, nullable=True)

    # Notification Toggles
    notify_on_low_vital_stat: Mapped[bool] = mapped_column("notify_on_low_vital_stat", Boolean, default=True)
    notify_on_critical_event: Mapped[bool] = mapped_column("notify_on_critical_event", Boolean, default=True)
    notify_on_craving: Mapped[bool] = mapped_column("notify_on_craving", Boolean, default=True)
    notify_on_friend_message: Mapped[bool] = mapped_column("notify_on_friend_message", Boolean, default=True)
    notify_on_shop_promo: Mapped[bool] = mapped_column("notify_on_shop_promo", Boolean, default=True)
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
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, nullable=False, index=True, unique=True)

    # === SYSTEM STATE ===
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    last_tick: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    last_save: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    last_autonomous_action: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    willpower_last_check: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    game_version: Mapped[str] = mapped_column(String, default="1.0.0")
    tutorial_stage: Mapped[int] = mapped_column(Integer, default=0)
    flags: Mapped[str] = mapped_column(String, default="")  # JSON string for various flags

    # === SYSTEM STATE ===
    created_at: datetime.datetime = Column(DateTime, default=datetime.datetime.utcnow)
    last_tick: datetime.datetime = Column(DateTime, default=datetime.datetime.utcnow)
    last_save: datetime.datetime = Column(DateTime, default=datetime.datetime.utcnow)
    last_autonomous_action: datetime.datetime = Column(DateTime, nullable=True)
    willpower_last_check: datetime.datetime = Column(DateTime, nullable=True)
    game_version: str = Column(String, default="1.0.0")
    tutorial_stage: int = Column(Integer, default=0)
    flags: str = Column(String, default="")  # JSON string for various flags

    # === SECTION 1: PHYSICAL HEALTH CORE ===
    health: float = Column(Float, default=100.0)
    energy: float = Column(Float, default=100.0)
    stamina: float = Column(Float, default=100.0)
    pain: float = Column(Float, default=0.0)
    immune_system: float = Column(Float, default=100.0)
    toxicity: float = Column(Float, default=0.0)
    body_temperature: float = Column(Float, default=37.0)  # In Celsius
    blood_pressure: float = Column(Float, default=120.0)   # Systolic
    heart_rate: float = Column(Float, default=70.0)       # BPM

    # === SECTION 2: IMMEDIATE NEEDS (0 = satisfied, 100 = critical) ===
    hunger: float = Column(Float, default=0.0)
    thirst: float = Column(Float, default=0.0)
    bladder: float = Column(Float, default=0.0)
    fatigue: float = Column(Float, default=0.0)
    boredom: float = Column(Float, default=0.0)
    bowels: float = Column(Float, default=0.0)
    comfort: float = Column(Float, default=100.0)
    temperature_comfort: float = Column(Float, default=100.0)
    sleep_quality: float = Column(Float, default=100.0)
    
    # === SECTION 3: MENTAL & EMOTIONAL STATE ===
    # Core Mood Components (ces composants forment l'humeur générale)
    emotional_stability: float = Column(Float, default=50.0)  # Stabilité émotionnelle générale
    contentment: float = Column(Float, default=50.0)         # Satisfaction/bien-être général
    mood_volatility: float = Column(Float, default=25.0)     # Tendance aux changements d'humeur
    emotional_resilience: float = Column(Float, default=50.0) # Capacité à gérer le stress

    # États Émotionnels Positifs (0-100)
    happiness: float = Column(Float, default=50.0)           # Bonheur immédiat
    joy: float = Column(Float, default=50.0)                 # Joie profonde
    satisfaction: float = Column(Float, default=50.0)        # Satisfaction personnelle
    enthusiasm: float = Column(Float, default=50.0)          # Enthousiasme/motivation
    serenity: float = Column(Float, default=50.0)            # Calme intérieur

    # États Émotionnels Négatifs (0-100)
    anxiety: float = Column(Float, default=0.0)              # Anxiété
    depression: float = Column(Float, default=0.0)           # Dépression
    stress: float = Column(Float, default=0.0)               # Stress
    anger: float = Column(Float, default=0.0)                # Colère
    fear: float = Column(Float, default=0.0)                 # Peur
    frustration: float = Column(Float, default=0.0)          # Frustration
    irritability: float = Column(Float, default=0.0)         # Irritabilité

    # === SECTION 3.1: ÉTAT MENTAL ET COGNITIF ===
    mental_clarity: float = Column(Float, default=100.0)    # Clarté mentale
    concentration: float = Column(Float, default=100.0)     # Capacité de concentration
    memory_function: float = Column(Float, default=100.0)   # Fonction mémorielle
    decision_making: float = Column(Float, default=100.0)   # Prise de décision
    creativity: float = Column(Float, default=50.0)         # Créativité
    cognitive_load: float = Column(Float, default=0.0)      # Charge cognitive
    confusion: float = Column(Float, default=0.0)          # Niveau de confusion mentale
    disorientation: float = Column(Float, default=0.0)     # Niveau de désorientation

    # === SECTION 3.2: ÉTATS SOCIAUX ET ENVIRONNEMENTAUX ===
    social_anxiety: float = Column(Float, default=20.0)     # Anxiété sociale
    social_energy: float = Column(Float, default=100.0)     # Énergie sociale
    environmental_stress: float = Column(Float, default=0.0) # Stress environnemental
    sensory_overload: float = Column(Float, default=0.0)    # Surcharge sensorielle
    loneliness: float = Column(Float, default=0.0)          # Sentiment de solitude
    social_comfort: float = Column(Float, default=50.0)     # Confort en situation sociale
    social_awareness: float = Column(Float, default=70.0)   # Conscience sociale
    
    # === SECTION 4: PHYSICAL SYMPTOMS ===
    # General Discomfort
    nausea: float = Column(Float, default=0.0)
    dizziness: float = Column(Float, default=0.0)
    headache: float = Column(Float, default=0.0)
    muscle_tension: float = Column(Float, default=0.0)
    joint_pain: float = Column(Float, default=0.0)
    back_pain: float = Column(Float, default=0.0)
    
    # Addiction-Related Symptoms
    dry_mouth: float = Column(Float, default=0.0)
    sore_throat: float = Column(Float, default=0.0)
    chest_tightness: float = Column(Float, default=0.0)
    breathing_difficulty: float = Column(Float, default=0.0)
    tremors: float = Column(Float, default=0.0)
    cold_sweats: float = Column(Float, default=0.0)
    
    # Digestive Issues
    stomachache: float = Column(Float, default=0.0)
    nausea_intensity: float = Column(Float, default=0.0)
    appetite: float = Column(Float, default=100.0)
    digestion: float = Column(Float, default=100.0)
    
    # === SECTION 5: ADDICTION & CONSUMPTION ===
    # Substance Dependencies
    nicotine_addiction: float = Column(Float, default=0.0, nullable=False)
    alcohol_addiction: float = Column(Float, default=0.0, nullable=False)
    cannabis_addiction: float = Column(Float, default=0.0, nullable=False)
    caffeine_addiction: float = Column(Float, default=0.0, nullable=False)
    
    # Addiction Mechanics
    substance_tolerance: float = Column(Float, default=0.0)
    withdrawal_severity: float = Column(Float, default=0.0)
    physical_dependence: float = Column(Float, default=0.0)
    psychological_dependence: float = Column(Float, default=0.0)
    recovery_progress: float = Column(Float, default=0.0)
    relapse_risk: float = Column(Float, default=0.0)
    
    # Cravings & Triggers
    craving_nicotine: float = Column(Float, default=0.0, nullable=False)
    craving_alcohol: float = Column(Float, default=0.0, nullable=False)
    craving_cannabis: float = Column(Float, default=0.0, nullable=False)
    trigger_sensitivity: float = Column(Float, default=50.0)
    stress_trigger_level: float = Column(Float, default=0.0)
    social_trigger_level: float = Column(Float, default=0.0)
    
    # Mental States Related to Addiction
    guilt: float = Column(Float, default=0.0)
    shame: float = Column(Float, default=0.0)
    hopelessness: float = Column(Float, default=0.0)
    determination: float = Column(Float, default=100.0)

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
    
    # === SECTION 8.1: GESTION DU SOMMEIL ===
    sleep_quality: float = Column(Float, default=100.0)  # Qualité du sommeil (affecte la récupération)
    sleep_minutes_today: int = Column(Integer, default=0)  # Minutes de sommeil aujourd'hui
    sleep_quota_needed: int = Column(Integer, default=480)  # Minutes de sommeil nécessaires (8h par défaut)
    last_sleep_check: Optional[datetime.datetime] = Column(DateTime, nullable=True)  # Pour le calcul du quota
    insomnia: float = Column(Float, default=0.0)  # Difficulté à dormir (augmente avec stress/santé mentale basse)
    
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
    last_action_by: str = Column(String, nullable=True)
    
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