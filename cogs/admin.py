# cogs/admin.py (parties modifiées et ajoutées)

from discord.ext import commands
import discord
from discord import app_commands, ui # Important pour les select menus
from db.database import SessionLocal
from db.models import ServerState, PlayerProfile # On aura besoin de PlayerProfile pour l'init peut-être
import datetime
import math # Pour des calculs de conversion/arrondi si besoin

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- Commande /config principale ---
    @app_commands.command(name="config", description="Configure les paramètres du bot et du jeu pour le serveur.")
    @app_commands.default_permissions(administrator=True)
    async def config(self, interaction: discord.Interaction):
        guild_id_str = str(interaction.guild.id)
        db = SessionLocal()
        state = db.query(ServerState).filter_by(guild_id=guild_id_str).first()

        if not state:
            state = ServerState(guild_id=guild_id_str)
            db.add(state)
            db.commit()
            state = db.query(ServerState).filter_by(guild_id=guild_id_str).first()

        # Envoyer le message de configuration avec le menu principal
        await interaction.response.send_message(
            embed=self.generate_config_menu_embed(state),
            view=self.generate_config_menu_view(guild_id_str),
            ephemeral=True
        )
        db.close()

    # --- Embeds pour le menu principal de configuration ---
    def generate_config_menu_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(
            title="⚙️ Configuration du Bot et du Jeu",
            description="Sélectionnez une section à configurer ci-dessous.",
            color=discord.Color.blue()
        )
        # Infos serveur
        admin_role_mention = f"<@&{state.admin_role_id}>" if state.admin_role_id else "Non défini"
        game_channel_mention = f"<#{state.game_channel_id}>" if state.game_channel_id else "Non défini"
        game_status = "En cours" if state.game_started else "Non lancée"

        embed.add_field(name="👑 Rôle Admin", value=admin_role_mention, inline=True)
        embed.add_field(name="🎮 Salon de Jeu", value=game_channel_mention, inline=True)
        embed.add_field(name="▶️ Statut du Jeu", value=game_status, inline=False)

        # Infos jeu
        interval_desc = f"{state.game_tick_interval_minutes} minutes" if state.game_tick_interval_minutes else "Défaut"
        embed.add_field(name="⏰ Intervalle Tick (min)", value=interval_desc, inline=True)
        embed.add_field(name="⬇️ Dégrad. Faim/Tick", value=f"{state.degradation_rate_hunger:.1f}", inline=True)
        embed.add_field(name="⬇️ Dégrad. Soif/Tick", value=f"{state.degradation_rate_thirst:.1f}", inline=True)
        embed.add_field(name="⬇️ Dégrad. Vessie/Tick", value=f"{state.degradation_rate_bladder:.1f}", inline=False)
        embed.add_field(name="⬇️ Dégrad. Énergie/Tick", value=f"{state.degradation_rate_energy:.1f}", inline=True)
        embed.add_field(name="⬆️ Dégrad. Stress/Tick", value=f"{state.degradation_rate_stress:.1f}", inline=True)
        embed.add_field(name="⬆️ Dégrad. Ennui/Tick", value=f"{state.degradation_rate_boredom:.1f}", inline=True)

        embed.set_footer(text="Naviguez en utilisant les boutons ci-dessous.")
        return embed

    # --- View pour le menu principal de configuration ---
    def generate_config_menu_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None) # Timeout=None pour les views persistantes
        # Sections de configuration existantes
        view.add_item(self.ConfigButton("⚙️ Bot & Connexion", guild_id, "bot_settings", discord.ButtonStyle.secondary))
        view.add_item(self.ConfigButton("🎮 Paramètres Jeu", guild_id, "game_settings", discord.ButtonStyle.secondary))
        
        # Afficher le bouton Stats s'il est pertinent
        db = SessionLocal()
        state = db.query(ServerState).filter_by(guild_id=guild_id).first()
        db.close()
        if state and state.game_started:
            view.add_item(self.StatsButton("📊 Statistiques", guild_id, discord.ButtonStyle.primary))
        
        # Bouton Lancer/Arrêter
        # Ce bouton devrait être plus intelligent : désactivé si pas configuré, ou avec option pour arrêter
        view.add_item(self.StartGameButton("▶️ Lancer la partie", guild_id, discord.ButtonStyle.success))
        return view

    # --- Bouton pour naviguer entre les sections de configuration ---
    class ConfigButton(ui.Button):
        def __init__(self, label: str, guild_id: str, config_type: str, style: discord.ButtonStyle):
            super().__init__(label=label, style=style, row=0) # row=0 pour aligner les premiers boutons en haut
            self.guild_id = guild_id
            self.config_type = config_type # "bot_settings" ou "game_settings"

        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()
            cog = interaction.client.get_cog("AdminCog")

            if self.config_type == "bot_settings":
                await interaction.response.edit_message(
                    embed=cog.generate_bot_settings_embed(state),
                    view=cog.generate_bot_settings_view(self.guild_id)
                )
            elif self.config_type == "game_settings":
                await interaction.response.edit_message(
                    embed=cog.generate_game_settings_embed(state),
                    view=cog.generate_game_settings_view(self.guild_id)
                )
            db.close()

    # --- Classes et méthodes pour la configuration Bot (rôle, canal) ---
    def generate_bot_settings_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(
            title="⚙️ Configuration du Bot",
            description="Adaptez les paramètres du bot pour ce serveur.",
            color=discord.Color.blue()
        )
        admin_role_mention = f"<@&{state.admin_role_id}>" if state.admin_role_id else "Non défini"
        game_channel_mention = f"<#{state.game_channel_id}>" if state.game_channel_id else "Non défini"

        embed.add_field(name="👑 Rôle Admin", value=admin_role_mention, inline=False)
        embed.add_field(name="🎮 Salon de Jeu Principal", value=game_channel_mention, inline=False)
        embed.set_footer(text="Utilisez les menus déroulants pour sélectionner les options.")
        return embed

    def generate_bot_settings_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.RoleSelect(guild_id)) # Pour sélectionner le rôle admin
        view.add_item(self.ChannelSelect(guild_id)) # Pour sélectionner le salon de jeu
        view.add_item(self.BackButton("⬅ Retour au Menu Principal", guild_id, discord.ButtonStyle.secondary))
        return view

    # Select Menu pour Rôle Admin (identique à avant)
    class RoleSelect(ui.RoleSelect):
        def __init__(self, guild_id: str):
            super().__init__(placeholder="Sélectionnez un rôle admin...", min_values=1, max_values=1, row=0)
            self.guild_id = guild_id

        async def callback(self, interaction: discord.Interaction):
            selected_role = self.values[0]
            guild_id_str = str(self.guild_id)
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=guild_id_str).first()
            if not state:
                state = ServerState(guild_id=guild_id_str)
                db.add(state)
            state.admin_role_id = str(selected_role.id)
            db.commit()

            cog = interaction.client.get_cog("AdminCog")
            await interaction.response.edit_message(
                embed=cog.generate_bot_settings_embed(state),
                view=cog.generate_bot_settings_view(self.guild_id)
            )
            db.close()

    # Select Menu pour Salon de Jeu (identique à avant)
    class ChannelSelect(ui.ChannelSelect):
        def __init__(self, guild_id: str):
            super().__init__(placeholder="Sélectionnez le salon de jeu...", channel_types=[discord.ChannelType.text], min_values=1, max_values=1, row=1) # row=1 pour la deuxième ligne
            self.guild_id = guild_id

        async def callback(self, interaction: discord.Interaction):
            selected_channel = self.values[0]
            guild_id_str = str(self.guild_id)
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=guild_id_str).first()
            if not state:
                state = ServerState(guild_id=guild_id_str)
                db.add(state)
            state.game_channel_id = str(selected_channel.id)
            db.commit()

            cog = interaction.client.get_cog("AdminCog")
            await interaction.response.edit_message(
                embed=cog.generate_bot_settings_embed(state),
                view=cog.generate_bot_settings_view(self.guild_id)
            )
            db.close()

    # --- Classes et méthodes pour la configuration du JEU ---
    def generate_game_settings_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(
            title="🎮 Paramètres du Jeu",
            description="Ajustez la difficulté et les intervalles de temps.",
            color=discord.Color.green()
        )
        # Affichage des taux actuels
        interval_desc = f"{state.game_tick_interval_minutes} minutes" if state.game_tick_interval_minutes is not None else "30 minutes (Défaut)"
        embed.add_field(name="⏰ Intervalle d'une \"Unité de Temps\" (Tick)", value=interval_desc, inline=False)
        embed.add_field(name="Faim par Tick", value=f"{state.degradation_rate_hunger:.1f}", inline=True)
        embed.add_field(name="Soif par Tick", value=f"{state.degradation_rate_thirst:.1f}", inline=True)
        embed.add_field(name="Vessie par Tick", value=f"{state.degradation_rate_bladder:.1f}", inline=True)
        embed.add_field(name="Énergie par Tick", value=f"{state.degradation_rate_energy:.1f}", inline=True)
        embed.add_field(name="Stress par Tick", value=f"{state.degradation_rate_stress:.1f}", inline=True)
        embed.add_field(name="Ennui par Tick", value=f"{state.degradation_rate_boredom:.1f}", inline=True)

        embed.set_footer(text="Utilisez les boutons pour modifier les valeurs.")
        return embed

    def generate_game_settings_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        # Utilisation de TextInput pour permettre la modification des valeurs
        view.add_item(self.GameSettingButton("⏰ Intervalle Tick", guild_id, "game_tick_interval_minutes", "number"))
        view.add_item(self.GameSettingButton("💧 Taux Faim", guild_id, "degradation_rate_hunger", "number"))
        view.add_item(self.GameSettingButton("🥤 Taux Soif", guild_id, "degradation_rate_thirst", "number"))
        view.add_item(self.GameSettingButton("💨 Taux Vessie", guild_id, "degradation_rate_bladder", "number"))
        view.add_item(self.GameSettingButton("⚡ Taux Énergie", guild_id, "degradation_rate_energy", "number"))
        view.add_item(self.GameSettingButton("😥 Taux Stress", guild_id, "degradation_rate_stress", "number"))
        view.add_item(self.GameSettingButton("😴 Taux Ennui", guild_id, "degradation_rate_boredom", "number"))
        
        view.add_item(self.BackButton("⬅ Retour au Menu Principal", guild_id, discord.ButtonStyle.secondary))
        return view

    # --- Bouton pour lancer le modal de modification ---
    class GameSettingButton(ui.Button):
        def __init__(self, label: str, guild_id: str, setting_key: str, input_type: str, style: discord.ButtonStyle = discord.ButtonStyle.grey, row: int = 0):
            super().__init__(label=label, style=style, row=row)
            self.guild_id = guild_id
            self.setting_key = setting_key
            self.input_type = input_type # 'number', 'text', etc.

        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()
            db.close()

            if not state:
                await interaction.response.send_message("Erreur: Impossible de trouver l'état du serveur pour modifier les paramètres.", ephemeral=True)
                return

            # Créer et envoyer un modal pour que l'utilisateur entre la nouvelle valeur
            modal = self.create_modal(state)
            await interaction.response.send_modal(modal)

        def create_modal(self, state: ServerState) -> ui.Modal:
            db = SessionLocal()
            current_value = getattr(state, self.setting_key, "")
            db.close()

            # Obtenir un placeholder approprié pour le champ
            placeholder_val = f"Actuellement: {current_value:.1f}" if isinstance(current_value, float) else f"Actuellement: {current_value}"
            if self.setting_key == "game_tick_interval_minutes":
                placeholder_val = f"Actuellement: {current_value} minutes"

            modal = ui.Modal(title=f"Modifier '{self.setting_key.replace('_', ' ').title()}'")
            
            modal.add_item(ui.TextInput(
                label=f"Nouvelle valeur pour {self.setting_key.replace('_', ' ').title()}",
                placeholder=placeholder_val,
                custom_id=f"modal_input_{self.setting_key}", # Pour identifier quel champ est modifié
                style=discord.TextStyle.short, # Ou .paragraph si besoin
                required=True
            ))
            return modal

    # Classe qui gère la soumission du Modal
    class GameSettingModalSubmit(ui.Modal):
        def __init__(self, setting_key: str, guild_id: str):
            super().__init__(title=f"Modifier la valeur pour '{setting_key.replace('_', ' ').title()}'")
            self.setting_key = setting_key
            self.guild_id = guild_id
            # Identifiant unique pour ce modal basé sur la clé et le serveur
            self.custom_id = f"modal_submit_{self.setting_key}_{self.guild_id}"
            
            # Créer dynamiquement le TextInput, on aurait pu le faire directement dans le init
            # pour plus de flexibilité, mais pour cette démo, on assume que l'identifiant est géré dans GameSettingButton
            
        async def on_submit(self, interaction: discord.Interaction):
            # On doit récupérer la valeur depuis les champs du modal
            # Comme les champs sont créés dynamiquement et on les appelle 'modal_input_clé',
            # il faut récupérer celui qui correspond à notre setting_key.
            # Ceci est une façon de faire : trouver le composant via son custom_id
            input_value = ""
            for component in interaction.data.get('components', []):
                if component.get('custom_id', '').startswith('modal_input_'):
                    input_value = component['components'][0]['value']
                    break

            if not input_value:
                await interaction.response.send_message("Erreur: Impossible de récupérer la valeur entrée.", ephemeral=True)
                return

            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()

            if not state:
                await interaction.response.send_message("Erreur: Impossible de trouver l'état du serveur.", ephemeral=True)
                db.close()
                return

            try:
                # Tenter de convertir la valeur selon le type attendu (défini dans GameSettingButton si besoin)
                if self.setting_key in ["game_tick_interval_minutes", "degradation_rate_hunger",
                                        "degradation_rate_thirst", "degradation_rate_bladder",
                                        "degradation_rate_energy", "degradation_rate_stress",
                                        "degradation_rate_boredom"]: # Clés numériques
                    
                    # Pour des valeurs spécifiques comme les taux de dégradation qui sont souvent en décimal
                    if '.' in input_value:
                        new_value = float(input_value)
                    else:
                        new_value = int(input_value)
                        
                    # Ajout de contraintes basiques
                    if self.setting_key == "game_tick_interval_minutes" and new_value < 1:
                        new_value = 1 # Intervalle minimum d'1 minute
                    elif self.setting_key.startswith("degradation_rate_") and new_value < 0:
                        new_value = 0 # Taux de dégradation ne peut pas être négatif
                    
                else: # Cas par défaut ou pour du texte si besoin
                    new_value = input_value

                setattr(state, self.setting_key, new_value) # Applique la nouvelle valeur au state
                db.commit()

                cog = interaction.client.get_cog("AdminCog")
                # MAJ l'embed avec les nouvelles valeurs
                await interaction.response.edit_message(
                    embed=cog.generate_game_settings_embed(state),
                    view=cog.generate_game_settings_view(self.guild_id)
                )

            except ValueError:
                await interaction.response.send_message(f"Entrée invalide. Veuillez entrer une valeur numérique pour '{self.setting_key.replace('_', ' ').title()}'.", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"Erreur lors de la sauvegarde: {e}", ephemeral=True)
            finally:
                db.close()

    # --- Bouton pour retourner au menu principal de configuration ---
    class BackButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle):
            super().__init__(label=label, style=style, row=3) # row=3 pour le mettre plus bas
            self.guild_id = guild_id

        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()
            cog = interaction.client.get_cog("AdminCog")
            
            await interaction.response.edit_message(
                embed=cog.generate_config_menu_embed(state),
                view=cog.generate_config_menu_view(self.guild_id)
            )
            db.close()

    # --- Bouton pour lancer la partie (inchangé dans sa fonction) ---
    class StartGameButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle):
            super().__init__(label=label, style=style, row=2) # row=2 pour placer ce bouton en bas de la première colonne
            self.guild_id = guild_id

        async def callback(self, interaction: discord.Interaction):
            guild_id_str = str(self.guild_id)
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=guild_id_str).first()

            if not state:
                await interaction.response.send_message("Erreur: Paramètres du serveur non trouvés. Utilisez `/config` d'abord.", ephemeral=True)
                db.close()
                return

            if not state.admin_role_id or not state.game_channel_id:
                await interaction.response.send_message("La configuration est incomplète. Veuillez définir un rôle admin ET un salon de jeu.", ephemeral=True)
                db.close()
                return
            
            if state.game_started:
                # Optionnel : Proposer un bouton pour arrêter la partie ici si l'admin veut arrêter
                await interaction.response.send_message("Une partie est déjà en cours sur ce serveur.", ephemeral=True)
                db.close()
                return

            # Lancer la partie
            state.game_started = True
            state.game_start_time = datetime.datetime.utcnow()
            state.last_update = datetime.datetime.utcnow() # Initialiser last_update pour le Scheduler
            db.commit()

            main_embed_cog = interaction.client.get_cog("MainEmbed")
            if not main_embed_cog:
                await interaction.response.send_message("Erreur interne : Le cog MainEmbed n'a pas été trouvé.", ephemeral=True)
                db.close()
                return

            game_embed = main_embed_cog.generate_menu_embed(state)
            game_view = main_embed_cog.generate_main_menu(guild_id_str)

            try:
                game_channel = interaction.guild.get_channel(int(state.game_channel_id))
                if not game_channel:
                    await interaction.response.send_message(f"Le salon de jeu configuré (ID: {state.game_channel_id}) n'a pas été trouvé ou est inaccessible.", ephemeral=True)
                    state.game_started = False # Annuler le lancement si le channel est perdu
                    state.game_start_time = None
                    state.last_update = None
                    db.commit()
                    db.close()
                    return
                
                await game_channel.send(f"✨ La partie commence ! Le cuisinier est prêt.\nUtilisez `/game` ou les boutons pour interagir.", embed=game_embed, view=game_view)
                await interaction.response.send_message(f"La partie a été lancée avec succès dans {game_channel.mention} !", ephemeral=True)
            
            except Exception as e:
                await interaction.response.send_message(f"Une erreur est survenue lors du lancement de la partie: {e}", ephemeral=True)
                state.game_started = False
                state.game_start_time = None
                state.last_update = None
                db.commit()
            finally:
                db.close()

    # --- Bouton Statistiques (inchangé) ---
    class StatsButton(ui.Button):
        def __init__(self, label: str, guild_id: str, style: discord.ButtonStyle):
            super().__init__(label=label, style=style, row=2) #row=2, pour la même ligne que StartGameButton
            self.guild_id = guild_id

        async def callback(self, interaction: discord.Interaction):
            db = SessionLocal()
            state = db.query(ServerState).filter_by(guild_id=str(self.guild_id)).first()
            cog = interaction.client.get_cog("AdminCog")

            await interaction.response.edit_message(
                embed=cog.generate_game_stats_embed(state),
                view=cog.generate_game_stats_view(self.guild_id)
            )
            db.close()

    # --- Génération Embed et View pour les Statistiques ---
    def generate_game_stats_embed(self, state: ServerState) -> discord.Embed:
        embed = discord.Embed(
            title="📊 Statistiques de la partie en cours",
            description="Informations générales sur la partie et les paramètres.",
            color=discord.Color.gold()
        )
        if state.game_start_time:
            now = datetime.datetime.utcnow()
            duration = now - state.game_start_time
            days, seconds = divmod(duration.total_seconds(), 86400)
            hours, seconds = divmod(seconds, 3600)
            minutes, seconds = divmod(seconds, 60)
            duration_str = f"{int(days)}j {int(hours)}h {int(minutes)}m" if days > 0 or hours > 0 else f"{int(minutes)}m"
            embed.add_field(name="Durée écoulée", value=duration_str, inline=False)
        else:
            embed.add_field(name="Durée écoulée", value="Aucun début enregistré.", inline=False)
        
        # Afficher aussi les paramètres du jeu actuels ici pour une vue d'ensemble
        interval_desc = f"{state.game_tick_interval_minutes} min" if state.game_tick_interval_minutes else "30 min"
        embed.add_field(name="⏰ Intervalle Tick", value=interval_desc, inline=True)
        embed.add_field(name="Faim/Tick", value=f"{state.degradation_rate_hunger:.1f}", inline=True)
        embed.add_field(name="Soif/Tick", value=f"{state.degradation_rate_thirst:.1f}", inline=True)
        embed.add_field(name="Vessie/Tick", value=f"{state.degradation_rate_bladder:.1f}", inline=True)
        embed.set_footer(text="Les données des joueurs seront affichées dans un futur update.")
        return embed

    def generate_game_stats_view(self, guild_id: str) -> discord.ui.View:
        view = discord.ui.View(timeout=None)
        view.add_item(self.BackButton("⬅ Retour au Menu Config", guild_id, discord.ButtonStyle.secondary))
        # Potentiel bouton pour arrêter la partie : nécessite une confirmation, réservé aux admins
        return view

async def setup(bot):
    await bot.add_cog(AdminCog(bot))