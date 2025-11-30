# musical_flags.py
# Created based on user request for a Musical Chairs style Flag game.

import ba
import random
import math
from bastd.actor.flag import Flag
from bastd.actor.spazbot import SpazBotSet, TntBot, BunnyBot
from bastd.actor.popuptext import PopupText

class MusicalFlagsGame(ba.TeamGameActivity):
    name = 'Musical Flags'
    description = 'Run to the flags! Last one standing explodes.'
    available_settings = [ba.IntSetting('Rounds', default=10)]
    score_config = ba.ScoreConfig(label='Points', score_type=ba.ScoreType.POINTS, none_is_winner=False)

    # Map support: We prefer open maps to make circles.
    @classmethod
    def get_supported_maps(cls, sessiontype):
        return ['Hockey Arena', 'Football Stadium', 'Courtyard']

    def __init__(self, settings):
        super().__init__(settings)
        self._rounds_to_play = settings.get('Rounds', 10)
        self._round_num = 0
        self._flags = []
        self._safe_players = []
        self._active_players = [] # Players currently in the round
        self._eliminated_players = [] # Track order of elimination for scoring
        self._bots = None
        self._check_timer = None
        self._loser_player = None

    def on_begin(self):
        super().on_begin()
        self.setup_next_round()

    def setup_next_round(self):
        # Clear previous entities
        for flag in self._flags:
            if flag.node: flag.node.delete()
        self._flags = []
        self._safe_players = []
        self._active_players = []
        
        # Clean up bots
        if self._bots:
            self._bots.clear()
            self._bots = None

        # Get living players
        living_players = [p for p in self.players if p.exists()]
        
        # Game Over Logic
        if len(living_players) < 2:
            self.end_game_with_scores()
            return

        self._round_num += 1
        ba.screenmessage(f"ROUND {self._round_num}", color=(1, 1, 0))

        # Spawn Players
        self.spawn_players_for_round(living_players)
        
        # Spawn Flags (Count = Players - 1)
        self.spawn_flags(len(living_players))

        # Start checking for collisions
        self._check_timer = ba.Timer(0.1, self.check_flag_collisions, repeat=True)

    def spawn_players_for_round(self, players):
        # Final Round Logic (1v1) - Spawn at edge
        if len(players) == 2:
            p1_pos = (-10, 1, 0)
            p2_pos = (-10, 1, 2) # Slightly offset so they don't stack
            for i, player in enumerate(players):
                self.spawn_player(player)
                # Force position
                pos = p1_pos if i == 0 else p2_pos
                if player.actor:
                    player.actor.handlemessage(ba.StandMessage(position=pos))
                    # Remove bomb/punch ability for pure running speed test? 
                    # Keeping them enables PVP which makes it chaotic (fun).
        else:
            # Normal Round - Circle Spawn
            # We spawn them slightly outside the flag circle
            radius = 6.0
            angle_step = 360.0 / len(players)
            for i, player in enumerate(players):
                angle = math.radians(i * angle_step)
                x = radius * math.cos(angle)
                z = radius * math.sin(angle)
                self.spawn_player(player)
                if player.actor:
                    player.actor.handlemessage(ba.StandMessage(position=(x, 1, z)))
                
            self._active_players = list(players)

    def spawn_flags(self, player_count):
        flag_count = player_count - 1
        if flag_count < 1: return

        # Final Round Logic - Flag on opposite edge
        if player_count == 2:
            # Players are at X = -10, Flag goes to X = 10
            p = (10, 1, 0)
            flag = Flag(position=p, color=(1, 1, 1), touchable=False) # False so they can't pick it up standard way
            self._flags.append(flag)
            PopupText("RUN!", position=(0, 5, 0), scale=2.0, color=(1,0,0)).autoretain()
        else:
            # Normal Round - Circle Center
            radius = 2.0 # Small circle in center
            angle_step = 360.0 / flag_count
            
            for i in range(flag_count):
                angle = math.radians(i * angle_step)
                x = radius * math.cos(angle)
                z = radius * math.sin(angle)
                flag = Flag(position=(x, 1, z), color=(0, 1, 0), touchable=False)
                self._flags.append(flag)

    def check_flag_collisions(self):
        # We manually check distance because we don't want players to PICK UP the flag,
        # we want them to vanish when they TOUCH it.
        
        if not self._active_players: return

        # Check every active player against every flag
        for player in list(self._active_players):
            if not player.actor or not player.actor.node:
                continue

            p_pos = player.actor.node.position
            
            for flag in list(self._flags):
                if not flag.node: continue
                
                f_pos = flag.node.position
                
                # Distance formula
                dist = math.sqrt((p_pos[0]-f_pos[0])**2 + (p_pos[2]-f_pos[2])**2)
                
                if dist < 1.5: # Close enough to touch
                    self.player_secured_flag(player, flag)

    def player_secured_flag(self, player, flag):
        ba.playsound(ba.getsound('corkPop'))
        PopupText("SAFE!", position=player.actor.node.position, color=(0,1,0), scale=1.5).autoretain()
        
        # Remove flag
        flag.node.delete()
        self._flags.remove(flag)
        
        # Remove player from active map (Hide them/make safe)
        self._safe_players.append(player)
        self._active_players.remove(player)
        if player.actor:
            player.actor.node.delete() # Remove their body from the map
            
        # CHECK IF ROUND ENDS (Only 1 player left active)
        if len(self._active_players) == 1:
            self.start_elimination_phase()

    def start_elimination_phase(self):
        # Stop checking collisions
        self._check_timer = None
        
        loser = self._active_players[0]
        self._loser_player = loser
        
        ba.screenmessage(f"{loser.getname()} FAILED TO GET A FLAG!", color=(1, 0, 0))
        ba.playsound(ba.getsound('shieldDown'))

        if loser.actor and loser.actor.node:
            # 1. Teleport to center
            loser.actor.handlemessage(ba.StandMessage(position=(0, 1, 0)))
            loser.actor.node.invincible = True # Brief invincibility so they don't die instantly
            ba.timer(1.0, lambda: setattr(loser.actor.node, 'invincible', False))

            # 2. Spawn Angry Bots
            self._bots = SpazBotSet()
            # Spawning 3 angry bots
            ba.timer(0.5, lambda: self._bots.spawn_bot(TntBot, pos=(3, 1, 0), spawn_time=0.1))
            ba.timer(0.5, lambda: self._bots.spawn_bot(BunnyBot, pos=(-3, 1, 0), spawn_time=0.1))
            ba.timer(0.5, lambda: self._bots.spawn_bot(TntBot, pos=(0, 1, 3), spawn_time=0.1))

            # 3. 5 Seconds Countdown
            self.show_countdown(5)
            
            # 4. Explode after 5 seconds
            ba.timer(5.0, self.execute_loser)

    def show_countdown(self, time):
        if time > 0:
            PopupText(str(time), position=(0, 5, 0), scale=2.0, color=(1,0,0)).autoretain()
            ba.playsound(ba.getsound('tick'))
            ba.timer(1.0, lambda: self.show_countdown(time - 1))

    def execute_loser(self):
        if self._loser_player and self._loser_player.exists():
            # Create massive explosion
            pos = (0,1,0)
            if self._loser_player.actor and self._loser_player.actor.node:
                pos = self._loser_player.actor.node.position
            
            # 5x Power Explosion (Standard TNT is roughly blast_radius 2.0)
            ba.Blast(position=pos, blast_radius=10.0, blast_type='tnt').autoretain()
            
            # Kill the player if blast didn't
            if self._loser_player.actor:
                self._loser_player.actor.handlemessage(ba.DieMessage())

            # Add to elimination list for scoring later
            self._eliminated_players.append(self._loser_player)

        # Clean up bots
        if self._bots:
            self._bots.clear()

        # Start Next Round after delay
        ba.timer(3.0, self.setup_next_round)

    def end_game_with_scores(self):
        # The last player remaining is the winner
        winner = None
        for p in self.players:
            if p not in self._eliminated_players:
                winner = p
                break
        
        # Create final standings list: [Winner, 2nd Place (Last eliminated), 3rd Place...]
        standings = []
        if winner:
            standings.append(winner)
        
        # Add eliminated players in reverse order (last eliminated = 2nd place)
        for p in reversed(self._eliminated_players):
            standings.append(p)

        # Point System: Top 1=10, Top 2=7, Top 3=5, Top 4=3, Top 5=1
        points_map = {0: 10, 1: 7, 2: 5, 3: 3, 4: 1}

        for rank, player in enumerate(standings):
            points = points_map.get(rank, 0) # Default 0 if outside top 5
            if points > 0:
                # Add to team score
                player.team.accum_score += points
                # Update player stats for end screen
                player.accumscore += points

        self.end_game()