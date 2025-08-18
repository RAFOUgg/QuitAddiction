# --- db/models.py ---
# type: ignore

from __future__ import annotations

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime, Integer, String, Boolean, Float, BigInteger, Text

from db.database import Base

class ServerState(Base):
    __tablename    last_worked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_drank_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_slept_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_smoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_urinated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_shower_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sickness_end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_defecated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)rver_state'

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
    notify_on_shop_promo: Mapped[bool] = mapped_column(Boolean, default=True)
    game_minutes_per_day: Mapped[int] = mapped_column(Integer, default=720)
    
    # Game time settings
    game_tick_interval_minutes: Mapped[int] = mapped_column(Integer, default=30)
    
    degradation_rate_hunger: Mapped[float] = mapped_column(Float, default=10.0)
    degradation_rate_thirst: Mapped[float] = mapped_column(Float, default=8.0)
    degradation_rate_bladder: Mapped[float] = mapped_column(Float, default=15.0)
    degradation_rate_energy: Mapped[float] = mapped_column(Float, default=5.0)
    degradation_rate_stress: Mapped[float] = mapped_column(Float, default=3.0)
    degradation_rate_boredom: Mapped[float] = mapped_column(Float, default=7.0)
    degradation_rate_hygiene: Mapped[float] = mapped_column(Float, default=4.0)
    is_test_mode: Mapped[bool] = mapped_column(Boolean, default=False)

    # Notification Role IDs
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


class PlayerProfile(Base):
    __tablename__ = "player_profile"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, nullable=False, index=True, unique=True)

    # === SYSTEM STATE ===
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_tick: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_save: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_autonomous_action: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    willpower_last_check: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    game_version: Mapped[str] = mapped_column(String, default="1.0.0")
    tutorial_stage: Mapped[int] = mapped_column(Integer, default=0)
    flags: Mapped[str] = mapped_column(String, default="")  # JSON string for various flags

    # === SYSTEM STATE ===
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_tick: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_save: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_autonomous_action: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    willpower_last_check: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    game_version: Mapped[str] = mapped_column(String, default="1.0.0")
    tutorial_stage: Mapped[int] = mapped_column(Integer, default=0)
    flags: Mapped[str] = mapped_column(String, default="")  # JSON string for various flags

    # === SECTION 1: PHYSICAL HEALTH CORE ===
    health: Mapped[float] = mapped_column(Float, default=100.0)
    energy: Mapped[float] = mapped_column(Float, default=100.0)
    stamina: Mapped[float] = mapped_column(Float, default=100.0)
    pain: Mapped[float] = mapped_column(Float, default=0.0)
    immune_system: Mapped[float] = mapped_column(Float, default=100.0)
    toxicity: Mapped[float] = mapped_column(Float, default=0.0)
    body_temperature: Mapped[float] = mapped_column(Float, default=37.0)  # In Celsius
    blood_pressure: Mapped[float] = mapped_column(Float, default=120.0)   # Systolic
    heart_rate: Mapped[float] = mapped_column(Float, default=70.0)       # BPM

    # === SECTION 2: IMMEDIATE NEEDS (0 = satisfied, 100 = critical) ===
    hunger: Mapped[float] = mapped_column(Float, default=0.0)
    thirst: Mapped[float] = mapped_column(Float, default=0.0)
    bladder: Mapped[float] = mapped_column(Float, default=0.0)
    fatigue: Mapped[float] = mapped_column(Float, default=0.0)
    boredom: Mapped[float] = mapped_column(Float, default=0.0)
    bowels: Mapped[float] = mapped_column(Float, default=0.0)
    comfort: Mapped[float] = mapped_column(Float, default=100.0)
    temperature_comfort: Mapped[float] = mapped_column(Float, default=100.0)
    sleep_quality: Mapped[float] = mapped_column(Float, default=100.0)
    
    # === SECTION 3: MENTAL & EMOTIONAL STATE ===
    # Core Mood Components (ces composants forment l'humeur générale)
    emotional_stability: Mapped[float] = mapped_column(Float, default=50.0)  # Stabilité émotionnelle générale
    contentment: Mapped[float] = mapped_column(Float, default=50.0)         # Satisfaction/bien-être général
    mood_volatility: Mapped[float] = mapped_column(Float, default=25.0)     # Tendance aux changements d'humeur
    emotional_resilience: Mapped[float] = mapped_column(Float, default=50.0) # Capacité à gérer le stress

    # États Émotionnels Positifs (0-100)
    happiness: Mapped[float] = mapped_column(Float, default=50.0)           # Bonheur immédiat
    joy: Mapped[float] = mapped_column(Float, default=50.0)                 # Joie profonde
    satisfaction: Mapped[float] = mapped_column(Float, default=50.0)        # Satisfaction personnelle
    enthusiasm: Mapped[float] = mapped_column(Float, default=50.0)          # Enthousiasme/motivation
    serenity: Mapped[float] = mapped_column(Float, default=50.0)            # Calme intérieur

    # États Émotionnels Négatifs (0-100)
    anxiety: Mapped[float] = mapped_column(Float, default=0.0)              # Anxiété
    depression: Mapped[float] = mapped_column(Float, default=0.0)           # Dépression
    stress: Mapped[float] = mapped_column(Float, default=0.0)               # Stress
    anger: Mapped[float] = mapped_column(Float, default=0.0)                # Colère
    fear: Mapped[float] = mapped_column(Float, default=0.0)                 # Peur
    frustration: Mapped[float] = mapped_column(Float, default=0.0)          # Frustration
    irritability: Mapped[float] = mapped_column(Float, default=0.0)         # Irritabilité

    # === SECTION 3.1: ÉTAT MENTAL ET COGNITIF ===
    mental_clarity: Mapped[float] = mapped_column(Float, default=100.0)    # Clarté mentale
    concentration: Mapped[float] = mapped_column(Float, default=100.0)     # Capacité de concentration
    memory_function: Mapped[float] = mapped_column(Float, default=100.0)   # Fonction mémorielle
    decision_making: Mapped[float] = mapped_column(Float, default=100.0)   # Prise de décision
    creativity: Mapped[float] = mapped_column(Float, default=50.0)         # Créativité
    cognitive_load: Mapped[float] = mapped_column(Float, default=0.0)      # Charge cognitive
    confusion: Mapped[float] = mapped_column(Float, default=0.0)          # Niveau de confusion mentale
    disorientation: Mapped[float] = mapped_column(Float, default=0.0)     # Niveau de désorientation

    # === SECTION 3.2: ÉTATS SOCIAUX ET ENVIRONNEMENTAUX ===
    social_anxiety: Mapped[float] = mapped_column(Float, default=20.0)     # Anxiété sociale
    social_energy: Mapped[float] = mapped_column(Float, default=100.0)     # Énergie sociale
    environmental_stress: Mapped[float] = mapped_column(Float, default=0.0) # Stress environnemental
    sensory_overload: Mapped[float] = mapped_column(Float, default=0.0)    # Surcharge sensorielle
    loneliness: Mapped[float] = mapped_column(Float, default=0.0)          # Sentiment de solitude
    social_comfort: Mapped[float] = mapped_column(Float, default=50.0)     # Confort en situation sociale
    social_awareness: Mapped[float] = mapped_column(Float, default=70.0)   # Conscience sociale
    
    # === SECTION 4: PHYSICAL SYMPTOMS ===
    # General Discomfort
    nausea: Mapped[float] = mapped_column(Float, default=0.0)
    dizziness: Mapped[float] = mapped_column(Float, default=0.0)
    headache: Mapped[float] = mapped_column(Float, default=0.0)
    muscle_tension: Mapped[float] = mapped_column(Float, default=0.0)
    joint_pain: Mapped[float] = mapped_column(Float, default=0.0)
    back_pain: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Addiction-Related Symptoms
    dry_mouth: Mapped[float] = mapped_column(Float, default=0.0)
    sore_throat: Mapped[float] = mapped_column(Float, default=0.0)
    chest_tightness: Mapped[float] = mapped_column(Float, default=0.0)
    breathing_difficulty: Mapped[float] = mapped_column(Float, default=0.0)
    tremors: Mapped[float] = mapped_column(Float, default=0.0)
    cold_sweats: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Digestive Issues
    stomachache: Mapped[float] = mapped_column(Float, default=0.0)
    nausea_intensity: Mapped[float] = mapped_column(Float, default=0.0)
    appetite: Mapped[float] = mapped_column(Float, default=100.0)
    digestion: Mapped[float] = mapped_column(Float, default=100.0)
    
    # === SECTION 5: ADDICTION & CONSUMPTION ===
    # Substance Dependencies
    nicotine_addiction: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    alcohol_addiction: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cannabis_addiction: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    caffeine_addiction: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    
    # Addiction Mechanics
    substance_tolerance: Mapped[float] = mapped_column(Float, default=0.0)
    withdrawal_severity: Mapped[float] = mapped_column(Float, default=0.0)
    physical_dependence: Mapped[float] = mapped_column(Float, default=0.0)
    psychological_dependence: Mapped[float] = mapped_column(Float, default=0.0)
    recovery_progress: Mapped[float] = mapped_column(Float, default=0.0)
    relapse_risk: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Cravings & Triggers
    craving_nicotine: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    craving_alcohol: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    craving_cannabis: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    trigger_sensitivity: Mapped[float] = mapped_column(Float, default=50.0)
    stress_trigger_level: Mapped[float] = mapped_column(Float, default=0.0)
    social_trigger_level: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Mental States Related to Addiction
    guilt: Mapped[float] = mapped_column(Float, default=0.0)
    shame: Mapped[float] = mapped_column(Float, default=0.0)
    hopelessness: Mapped[float] = mapped_column(Float, default=0.0)
    determination: Mapped[float] = mapped_column(Float, default=100.0)

    # === SECTION 6: STATS DE VIE ET LONG TERME ===
    willpower: Mapped[float] = mapped_column(Float, default=80.0)
    hygiene: Mapped[float] = mapped_column(Float, default=100.0)
    job_performance: Mapped[float] = mapped_column(Float, default=75.0)
    immune_system: Mapped[float] = mapped_column(Float, default=100.0)
    is_sick: Mapped[bool] = mapped_column(Boolean, default=False)

    # === SECTION 6.1: STATISTIQUES DE TRAVAIL ===
    total_minutes_late: Mapped[int] = mapped_column(Integer, default=0)
    total_break_time: Mapped[int] = mapped_column(Integer, default=0)
    total_work_time: Mapped[int] = mapped_column(Integer, default=0)
    work_days_streak: Mapped[int] = mapped_column(Integer, default=0)
    last_break_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # === SECTION 7: AUTRES & MÉTA-DONNÉES ===
    wallet: Mapped[int] = mapped_column(Integer, default=20)
    show_stats_in_view: Mapped[bool] = mapped_column(Boolean, default=False)
    show_inventory_in_view: Mapped[bool] = mapped_column(Boolean, default=False)
    show_schedule_in_view: Mapped[bool] = mapped_column(Boolean, default=False)
    recent_logs: Mapped[str] = mapped_column(Text, default="")

    # === SECTION 8: STATUTS ACTUELS ===
    is_working: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_on_break: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_sleeping: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    missed_work_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_worked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    first_day_reward_given: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    lateness_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    has_completed_first_work_day: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # === SECTION 8.1: GESTION DU SOMMEIL ===
    sleep_quality: Mapped[float] = mapped_column(Float, default=100.0)  # Qualité du sommeil (affecte la récupération)
    sleep_minutes_today: Mapped[int] = mapped_column(Integer, default=0)  # Minutes de sommeil aujourd'hui
    sleep_quota_needed: Mapped[int] = mapped_column(Integer, default=480)  # Minutes de sommeil nécessaires (8h par défaut)
    last_sleep_check: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # Pour le calcul du quota
    insomnia: Mapped[float] = mapped_column(Float, default=0.0)  # Difficulté à dormir (augmente avec stress/santé mentale basse)
    
    # --- INVENTAIRE BASE ---
    food_servings: Mapped[int] = mapped_column(Integer, default=1)
    water_bottles: Mapped[int] = mapped_column(Integer, default=5)
    soda_cans: Mapped[int] = mapped_column(Integer, default=1)
    cigarettes: Mapped[int] = mapped_column(Integer, default=5)
    e_cigarettes: Mapped[int] = mapped_column(Integer, default=0)
    beers: Mapped[int] = mapped_column(Integer, default=0)
    tacos: Mapped[int] = mapped_column(Integer, default=0)
    salad_servings: Mapped[int] = mapped_column(Integer, default=0)
    wine_bottles: Mapped[int] = mapped_column(Integer, default=0)
    joints: Mapped[int] = mapped_column(Integer, default=0)

    # --- INVENTAIRE SMOKE SHOP ---
    weed_grams: Mapped[int] = mapped_column(Integer, default=0)
    hash_grams: Mapped[int] = mapped_column(Integer, default=0)
    cbd_grams: Mapped[int] = mapped_column(Integer, default=0)
    tobacco_grams: Mapped[int] = mapped_column(Integer, default=0)
    rolling_papers: Mapped[int] = mapped_column(Integer, default=0)
    toncs: Mapped[int] = mapped_column(Integer, default=0)
    has_grinder: Mapped[bool] = mapped_column(Boolean, default=False)
    has_bong: Mapped[bool] = mapped_column(Boolean, default=False)
    has_chillum: Mapped[bool] = mapped_column(Boolean, default=False)
    has_vaporizer: Mapped[bool] = mapped_column(Boolean, default=False)

    # --- HISTORIQUE DES CRAFTS ---
    joints_crafted: Mapped[int] = mapped_column(Integer, default=0)
    bong_uses: Mapped[int] = mapped_column(Integer, default=0)
    chillum_uses: Mapped[int] = mapped_column(Integer, default=0)
    vaporizer_uses: Mapped[int] = mapped_column(Integer, default=0)

    # --- Notifications Config ---
    notifications_config: Mapped[str] = mapped_column(Text, default="")
    notification_history: Mapped[str] = mapped_column(Text, default="")

    # --- Timestamps & Cooldowns ---
    last_update: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_action_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_action: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_action_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    action_cooldown_end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    #... (autres timestamps)
    last_eaten_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_drank_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_slept_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_smoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_urinated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_shower_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sickness_end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_defecated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # --- Flags Narratifs ---
    has_unlocked_smokeshop: Mapped[bool] = mapped_column(Boolean, default=False)
    messages: Mapped[str] = mapped_column(Text, default="")
    last_action_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # --- Téléphone ---
    phone_uses_today: Mapped[int] = mapped_column(Integer, default=0)
    last_phone_reset_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (UniqueConstraint('guild_id', name='uq_guild_player'),)

class ActionLog(Base):
    __tablename__ = "action_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[str] = mapped_column(String, index=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    action: Mapped[str] = mapped_column(String)
    effect: Mapped[str] = mapped_column(String)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)