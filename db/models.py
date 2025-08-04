# --- db/models.py ---
import sqlalchemy # Imports sqlalchemy comme ceci si Base vient d'un autre fichier
import datetime
# --- Astuce pour l'IDE : Permet l'autocomplétion sans créer de cycle d'import runtime --
try:
    # Ceci EST L'IMPORT CLÉ QUI EST SUSPECT. Assurez-vous qu'il fonctionne.
    from db.database import Base
except ImportError:
    # Ce bloc est pour les IDEs seulement, le code réel doit s'appuyer sur l'import qui est juste au dessus.
    print("AVERTISSEMENT: Le bloc try-except dans models.py est actif, potentiellement à cause d'un problème d'importation avec Base.")
    class MockBase: # Classe mock pour l'autocomplétion si l'import échoue.
        metadata = type('MockMetaData', (object,), {'create_all': lambda x: None})
    Base = MockBase()
class ServerState(Base):
    __tablename__ = "server_state"
    id = Column(Integer, primary_key=True)
    guild_id = Column(String, unique=True, nullable=False)
    admin_role_id = Column(String, nullable=True)
    game_channel_id = Column(String, nullable=True)
    game_started = Column(Boolean, default=False)
    game_start_time = Column(DateTime, nullable=True)

    # --- NOUVEAUX PARAMÈTRES DE JEU CONFIGURES PAR LE SERVEUR ---

    # Intervalle des "ticks" de simulation (en minutes). C'est la durée d'une "unité de temps" du jeu.
    # Chaque tick, les statistiques de base se dégradent.
    game_tick_interval_minutes = Column(Integer, default=30) # Par défaut, une unité de temps dure 30 minutes

    # --- TAUX DE DÉGRADATION PAR TICK (ajuster ces valeurs pour la difficulté du jeu) ---
    # Ces valeurs sont par tick d'intervalle. S'ils sont pour 30min, la dégradation est donc X / 30 par minute.

    # Besoins primaires
    degradation_rate_hunger = Column(Float, default=10.0)   # Augmente la faim de 10 unités par tick (soit ~0.33/min)
    degradation_rate_thirst = Column(Float, default=8.0)    # Augmente la soif de 8 unités par tick (~0.26/min)
    degradation_rate_bladder = Column(Float, default=15.0)  # Augmente la vessie de 15 unités par tick (0.5/min)

    # Statut mentaux/physiques (dégradation naturelle)
    degradation_rate_energy = Column(Float, default=5.0)    # Diminue l'énergie de 5 unités par tick (~0.17/min)
    degradation_rate_stress = Column(Float, default=3.0)    # Augmente le stress de 3 unités par tick (~0.1/min)
    degradation_rate_boredom = Column(Float, default=7.0)   # Augmente l'ennui de 7 unités par tick (~0.23/min)

    # Taux d'addiction/toxines
    # Les taux d'addiction et toxines peuvent être influencés par les actions du joueur,
    # mais aussi par des taux "naturels" si on veut simuler une exposition lente.
    # Pour l'instant, je laisse ceux-là bas pour le début.
    degradation_rate_addiction_base = Column(Float, default=0.1) # Légère augmentation naturelle d'addiction ? Ou pas du tout ?
    degradation_rate_toxins_base = Column(Float, default=0.5)  # Légère augmentation naturelle de toxines ?

    # Note: les autres statistiques (health, sanity, happy, etc.) sont plutôt des _conséquences_
    # de la dégradation des autres besoins ou des réactions en chaîne,
    # donc ils ne sont pas nécessairement directement "dégradés" par un taux temporel.
    # Leur dégradation naturelle viendra de chain_reactions.
    # Statistiques de base du cuisinier
    phys = Column(Float, default=100.0) # Mettre .0 pour clarifier que ce sont des flottants
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

    # Statistiques de progression
    wallet = Column(Integer, default=0)
    last_update = Column(DateTime, default=datetime.datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('guild_id', name='uq_guild_server_state'), # Ensure guild_id is unique here
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