class Scheduler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pending_effects = [] # Peut-être non utilisé pour l'instant.
    
    async def cog_load(self): # Définie comme async
        """Se lance quand le cog est chargé."""
        self.tick.start()
        print("Scheduler tick started.")

    def cog_unload(self):
        """Annule la tâche quand le cog est déchargé."""
        self.tick.cancel()
        print("Scheduler tick cancelled.")

    @tasks.loop(minutes=1) # C'est le intervalle auquel la LOOP s'exécute. Le CALENDRIER des dégradations se fait INSIDE.
    async def tick(self):
        current_time = datetime.datetime.utcnow()
        db = SessionLocal()
        try:
            # 1. Chercher les 'ServerState' où une partie est lancée
            server_states = db.query(ServerState).filter(ServerState.game_started == True).all()
            
            for server_state in server_states:
                # Logique pour calculer combien de ticks DÉGRADATIONS appliquer basé sur server_state.last_update et server_state.game_tick_interval_minutes
                time_since_last_update = current_time - (server_state.last_update or current_time) # Handle first run safely
                interval_minutes = server_state.game_tick_interval_minutes or 30 # Default interval if none
                
                num_ticks_to_apply = math.floor(time_since_last_update.total_seconds() / 60 / interval_minutes)
                
                if num_ticks_to_apply > 0:
                    # Charger les players de ce serveur
                    player_profiles = db.query(PlayerProfile).filter_by(guild_id=server_state.guild_id).all()
                    
                    for player in player_profiles:
                        # Appliquer les dégradations 'num_ticks_to_apply' fois, ou de manière plus fluide sur delta_time
                        # Pour simplicité: appliquer l'effet total des ticks calculés
                        
                        # Détermination des taux par MINUTE (taux par TICK / min par TICK)
                        hunger_change = (server_state.degradation_rate_hunger / interval_minutes) * num_ticks_to_apply if interval_minutes else 0
                        thirst_change = (server_state.degradation_rate_thirst / interval_minutes) * num_ticks_to_apply if interval_minutes else 0
                        bladder_change = (server_state.degradation_rate_bladder / interval_minutes) * num_ticks_to_apply if interval_minutes else 0
                        energy_change = -(server_state.degradation_rate_energy / interval_minutes) * num_ticks_to_apply if interval_minutes else 0
                        stress_change = (server_state.degradation_rate_stress / interval_minutes) * num_ticks_to_apply if interval_minutes else 0
                        boredom_change = (server_state.degradation_rate_boredom / interval_minutes) * num_ticks_to_apply if interval_minutes else 0
                        
                        # ... appliquez ces changements à player ...
                        player.hunger = min(100.0, player.hunger + hunger_change)
                        # etc. pour tous les attributs

                        # Créer un state_dict pour chain_reactions (et appliquer les réactions)
                        # ... cette partie doit être construite avec les nouvelles valeurs du joueur...
                        state_for_calc = { ... } # remplir avec player attributes
                        chain_reactions(state_for_calc) # Modifier state_for_calc
                        # MAJ le player avec les résultats de chain_reactions
                        # ... (max/min clampages des valeurs) ...
                        player.last_update = current_time # Mise à jour de la dernière fois qu'on a interagi avec CE joueur.

                # Si on a appliqué des ticks pour ce serveur, MAJ son last_update
                # Si num_ticks_to_apply > 0: 
                server_state.last_update = current_time # Pour ce serveur


            db.commit()

        except Exception as e:
            print(f"Erreur dans Scheduler.tick: {e}")
            db.rollback()
        finally:
            db.close()

    # Ajoutez le `@tick.before_loop` comme prévu
    @tasks.loop(minutes=1) # Ceci signifie que la fonction tick sera DÉCLENCHÉE chaque minute
    async def tick(self): # Cette fonction DOIT EXISTER et être lancée

    @tick.before_loop
    async def before_tick(self):
        await self.bot.wait_until_ready()
        print("Scheduler prêt pour le tick.")


async def setup(bot):
    await bot.add_cog(Scheduler(bot))