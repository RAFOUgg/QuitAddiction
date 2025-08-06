# --- db/models.py ---
try:
    from db.database import Base
except ImportError:
    print("CRITICAL ERROR IN MODELS.PY: CANNOT IMPORT Base FROM db.database.py!")
    print("--> Check import paths and ensure no circular dependencies.")
    raise

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey, UniqueConstraint
import datetime

class ServerState(Base):
    __tablename__ = "server_state"
    id = Column(Integer, primary_key=True) # Clé primaire pour SQLAlchemy
    
    guild_id = Column(String, unique=True, nullable=False) # Identifiant unique du serveur Discord
    
    # Configuration du Bot
    admin_role_id = Column(String, nullable=True)       # ID du rôle admin
    game_channel_id = Column(String, nullable=True)     # ID du salon où le bot affiche les infos du jeu
    notification_role_id = Column(String, nullable=True) # ID du rôle pour les notifications (AJOUTÉ)

    # Statut du jeu
    game_started = Column(Boolean, default=False)       # Indique si une partie est en cours
    game_start_time = Column(DateTime, nullable=True)   # Timestamp du début de la partie pour le calcul de durée
    last_update = Column(DateTime, default=datetime.datetime.utcnow) # Timestamp de la dernière mise à jour globale pour le scheduler

    # Paramètres de la partie (difficulté et durée)
    game_mode = Column(String, default="medium")        # Ex: "peaceful", "medium", "hard"
    duration_key = Column(String, nullable=True, default="medium") # Clé de la durée choisie ("short", "medium", "long")

    # Taux de dégradation par "tick" (basés sur le game_mode choisi)
    game_tick_interval_minutes = Column(Integer, default=30) # Durée d'une unité de temps de jeu (en minutes)
    
    # --- NOUVEAUX CHAMPS POUR LES RÔLES DE NOTIFICATION SPÉCIFIQUES ---
    notify_vital_low_role_id = Column(String, nullable=True)      
    notify_critical_role_id = Column(String, nullable=True)       
    notify_envie_fumer_role_id = Column(String, nullable=True)     
    notify_friend_message_role_id = Column(String, nullable=True)  
    notify_shop_promo_role_id = Column(String, nullable=True)      

    # --- NOUVEAUX CHAMPS POUR LES PRÉFÉRENCES DE NOTIFICATION (booléens) ---
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
    degradation_rate_addiction_base = Column(Float, default=0.1) # Taux de base d'augmentation d'addiction par tick
    degradation_rate_toxins_base = Column(Float, default=0.5)  # Taux de base d'augmentation de toxines par tick

    # Statistiques générales du serveur/cuisinier (peuvent être une moyenne ou un état global)
    # Ces valeurs peuvent être dégradées par le scheduler ou améliorées par des actions globales
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

# --- Modèle pour le profil de chaque joueur ---
class PlayerProfile(Base):
    __tablename__ = "player_profile"

    id = Column(Integer, primary_key=True) # Clé primaire pour SQLAlchemy
    
    # Liens avec le serveur et l'utilisateur Discord
    guild_id = Column(String, nullable=False, index=True) # ID du serveur où le joueur existe
    user_id = Column(String, nullable=False, index=True)  # ID de l'utilisateur Discord

    nickname = Column(String, nullable=True) # Le pseudo actuel du joueur dans le jeu

    # Statistiques individuelles du joueur (qui seront affectées par le scheduler et les actions)
    health = Column(Float, default=100.0)
    energy = Column(Float, default=100.0)
    hunger = Column(Float, default=0.0)         # 0 = Plein, 100 = Mort de faim
    thirst = Column(Float, default=0.0)         # 0 = Plein, 100 = Déshydraté
    bladder = Column(Float, default=0.0)        # 0 = Vide, 100 = Besoin urgent
    pain = Column(Float, default=0.0)           # 0 = Aucun, 100 = Intense
    body_temperature = Column(Float, default=37.0) # Température corporelle (peut affecter d'autres choses)
    hygiene = Column(Float, default=0.0)        # 0 = Propre, 100 = Sale (peut affecter SOCIAL, MENT)

    # Santé Mentale & Émotionnelle
    sanity = Column(Float, default=100.0) # Alias pour MENT dans le bot
    stress = Column(Float, default=0.0)         # 0 = Calme, 100 = Panique
    mood = Column(Float, default=0.0)           # Peut être mappé à une échelle (-100 dépressif, 0 neutre, 100 euphorique)
    happiness = Column(Float, default=0.0)      # Bonheur pur, augmente par récompenses positives
    irritability = Column(Float, default=0.0)   # Augmente avec le stress, le manque, affecte interactions
    fear = Column(Float, default=0.0)
    loneliness = Column(Float, default=0.0)     # Augmente en cas de manque d'interaction sociale
    boredom = Column(Float, default=0.0)        # 0 = Stimulé, 100 = Ennuyé à mourir
    concentration = Column(Float, default=100.0)

    # Addiction & Consommation (pour la substance principale du jeu)
    substance_addiction_level = Column(Float, default=0.0) # Niveau de dépendance (0-100)
    withdrawal_severity = Column(Float, default=0.0)      # Gravité des symptômes de sevrage
    intoxication_level = Column(Float, default=0.0)       # Niveau actuel d'intoxication ("trip")

    wallet = Column(Integer, default=0)        # Argent personnel du joueur (si différent du portefeuille global)
    last_update = Column(DateTime, default=datetime.datetime.utcnow) # Dernière mise à jour des stats SPECIFIQUES DU JOUEUR

    # Contraintes pour garantir l'unicité de l'entrée joueur/serveur
    __table_args__ = (
        UniqueConstraint('guild_id', 'user_id', name='uq_guild_user'),
    )

# --- Modèle pour l'historique des actions ---
class ActionLog(Base):
    __tablename__ = "action_log"
    id = Column(Integer, primary_key=True)
    guild_id = Column(String, index=True) # Index pour des recherches plus rapides par serveur
    user_id = Column(String, index=True)  # Index pour des recherches plus rapides par utilisateur
    action = Column(String)               # Description de l'action (ex: "A mangé un snack")
    effect = Column(String)               # Effet de l'action (ex: "+10 FOOD, -5 STRESS")
    timestamp = Column(DateTime, default=datetime.datetime.utcnow) # Quand l'action a eu lieu