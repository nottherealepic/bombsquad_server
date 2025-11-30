# ba_meta require api 8
# ba_meta export bascenev1.GameActivity

from __future__ import annotations
from typing import TYPE_CHECKING, List, Any

import bascenev1 as bs
import random
import math
from bascenev1lib.actor.flag import Flag, FlagPickedUpMessage
from bascenev1lib.actor.playerspaz import PlayerSpaz
# FIXED IMPORTS HERE: Changed TntBot to BomberBot, BrawlerBotLite to BrawlerBot
from bascenev1lib.actor.spazbot import SpazBotSet, BomberBot, BrawlerBot
from bascenev1lib.actor.popuptext import PopupText
from bascenev1lib.actor.bomb import Blast

if TYPE_CHECKING:
    from typing import Sequence

class Player(bs.Player['Team']):
    """Our player type for this game."""
    def __init__(self) -> None:
        self.survived = True

class Team(bs.Team[Player]):
    """Our team type for this game."""
    def __init__(self) -> None:
        self.score = 0

class MusicalFlagsGame(bs.TeamGameActivity[Player, Team]):
    name = 'Musical Flags'
    description = "Get a Flag or Explode!"
    
    @classmethod
    def get_supported_maps(cls, sessiontype: type[bs.Session]) -> List[str]:
        # We need maps with open space for the circles
        return ['Doom Shroom', 'Football Stadium', 'Hockey Arena', 'Courtyard']

    @classmethod
    def get_available_settings(cls, sessiontype: type[bs.Session]) -> list[bs.Setting]:
        return [
            bs.BoolSetting('Epic Mode', default=False),
        ]

    @classmethod
    def supports_session_type(cls, sessiontype: type[bs.Session]) -> bool:
        return issubclass(sessiontype, bs.FreeForAllSession) or issubclass(sessiontype, bs.DualTeamSession)

    def __init__(self, settings: dict):
        super().__init__(settings)
        self.default_music = bs.MusicType.FLAG_CATCHER
        self._round_num = 0
        self._flags: List[Flag] = []
        self._bots = SpazBotSet()
        
        # Track the tournament state
        self._tournament_survivors: List[Player] = [] # Players still in the game
        self._eliminated_order: List[Player] = []     # Players kicked out (for scoring)
        self._round_active_players: List[Player] = [] # Players running in current round

    def on_begin(self) -> None:
        super().on_begin()
        # At start, everyone is a survivor
        self._tournament_survivors = [p for p in self.players if p.exists()]
        self.setup_next_round()

    def on_player_leave(self, player: Player) -> None:
        # If a player leaves, remove them from lists so the game doesn't glitch
        if player in self._tournament_survivors:
            self._tournament_survivors.remove(player)
        if player in self._round_active_players:
            self._round_active_players.remove(player)
            # Check if the round needs to end because someone left
            if len(self._round_active_players) == 1:
                self.start_punishment(self._round_active_players[0])
            elif len(self._round_active_players) == 0:
                bs.timer(1.0, self.setup_next_round)
        super().on_player_leave(player)

    def setup_next_round(self) -> None:
        # 1. Cleanup previous round items
        self._bots.clear()
        for flag in self._flags:
            if flag.node: flag.node.delete()
        self._flags = []
        self._round_active_players = []
        
        # 2. Check valid survivors
        self._tournament_survivors = [p for p in self._tournament_survivors if p.exists()]
        survivor_count = len(self._tournament_survivors)

        # 3. Game Over / Scoring Check
        if survivor_count < 2:
            self.end_game_scoring()
            return

        self._round_num += 1
        bs.broadcastmessage(f"ROUND {self._round_num}", color=(1, 1, 0))

        # 4. Decide Round Type
        if survivor_count == 2:
            self.setup_duel_round()
        else:
            self.setup_circle_round(survivor_count)

    def setup_duel_round(self) -> None:
        # --- FINAL ROUND LOGIC (1v1) ---
        # Players at Edge, Flag at other Edge
        bs.broadcastmessage("FINAL DUEL!", color=(1, 0, 0), transient=True)
        
        p_x = -10.0 # Player spawn X
        f_x = 10.0  # Flag spawn X
        
        # Spawn 1 Flag
        self._flags.append(Flag(position=(f_x, 2, 0), color=(1, 1, 1), touchable=True))
        
        # Spawn 2 Players
        for i, player in enumerate(self._tournament_survivors):
            self._round_active_players.append(player)
            z_pos = -1.0 if i == 0 else 1.0
            self.spawn_player_spaz(player, position=(p_x, 2, z_pos))
            
        PopupText("GO!", position=(0, 5, 0), scale=2.0, color=(0,1,0)).autoretain()

    def setup_circle_round(self, count: int) -> None:
        # --- NORMAL ROUND LOGIC ---
        # Players in Center Pile, Flags in Outer Circle
        flag_count = count - 1
        
        # 1. Spawn Flags in LARGE Outer Circle (Radius 7.0)
        for i in range(flag_count):
            angle = (i / flag_count) * 360
            x = 7.0 * math.cos(math.radians(angle))
            z = 7.0 * math.sin(math.radians(angle))
            flg = Flag(position=(x, 2.5, z), color=(0, 1, 0), touchable=True)
            self._flags.append(flg)
            
        # 2. Spawn ALL Players in EXACT CENTER
        # They will push each other, creating chaos
        for player in self._tournament_survivors:
            self._round_active_players.append(player)
            self.spawn_player_spaz(player, position=(0, 2.5, 0))

    def spawn_player_spaz(self, player: Player, position: tuple) -> None:
        spaz = self.spawn_player(player)
        # Allow punching/running, but no bombs/pickup
        spaz.connect_controls_to_player(enable_punch=True, enable_bomb=False, enable_pickup=False)
        spaz.handlemessage(bs.StandMessage(position))
        
        # Random facing if in center
        angle = random.uniform(0, 360)
        if position[0] == -10: angle = 0 # Face flag in duel
        spaz.handlemessage(bs.StandMessage(position, angle=angle))

    def handlemessage(self, msg: Any) -> Any:
        if isinstance(msg, FlagPickedUpMessage):
            node = msg.node
            flag = msg.flag
            
            try:
                player = node.getdelegate(PlayerSpaz, True).getplayer(Player, True)
            except Exception:
                return None

            if player in self._round_active_players:
                # --- PLAYER IS SAFE ---
                bs.playsound(bs.getsound('corkPop'))
                PopupText("SAFE!", position=node.position, color=(0,1,0), scale=1.6).autoretain()
                
                # Remove Flag
                flag.node.delete()
                if flag in self._flags:
                    self._flags.remove(flag)
                
                # Remove Player from map (Safe)
                self._round_active_players.remove(player)
                node.handlemessage(bs.DieMessage(how=bs.DeathType.GENERIC)) 
                
                # If only 1 player left in the arena -> They are the Loser
                if len(self._round_active_players) == 1:
                    self.start_punishment(self._round_active_players[0])
            
            return None # Don't let them hold the flag

        elif isinstance(msg, bs.PlayerDiedMessage):
            player = msg.getplayer(Player)
            # If they die while running (fall off map)
            if player in self._round_active_players:
                self._round_active_players.remove(player)
                self.eliminate_player(player)
                
                if len(self._round_active_players) == 1:
                    self.start_punishment(self._round_active_players[0])
                elif len(self._round_active_players) == 0:
                     bs.timer(2.0, self.setup_next_round)

        return super().handlemessage(msg)

    # --- KILLING LOGIC ---
    def start_punishment(self, loser: Player) -> None:
        bs.broadcastmessage(f"{loser.getname()} ELIMINATED!", color=(1, 0, 0))
        
        # 1. Teleport to Center
        if loser.actor and loser.actor.node:
             loser.actor.handlemessage(bs.StandMessage(position=(0, 2, 0)))
             # Freeze briefly so they don't run away immediately
             bs.timer(0.1, lambda: loser.actor.handlemessage(bs.FreezeMessage()) if loser.actor else None)
             bs.timer(1.0, lambda: loser.actor.handlemessage(bs.ThawMessage()) if loser.actor else None)
        else:
            self.spawn_player_spaz(loser, (0, 2, 0))
        
        # 2. Spawn Angry Bots (BomberBot and BrawlerBot)
        bs.playsound(bs.getsound('shieldDown'))
        self._bots.spawn_bot(BomberBot, pos=(3, 2, 0), spawn_time=0.5)
        self._bots.spawn_bot(BrawlerBot, pos=(-3, 2, 0), spawn_time=0.5)
        self._bots.spawn_bot(BomberBot, pos=(0, 2, 3), spawn_time=0.5)
        
        # 3. 5 Second Fight Timer
        self.countdown_tick(5, loser)

    def countdown_tick(self, time: int, victim: Player) -> None:
        if time > 0:
            PopupText(str(time), position=(0, 5, 0), scale=2.5, color=(1, 0, 0)).autoretain()
            bs.playsound(bs.getsound('tick'))
            bs.timer(1.0, bs.Call(self.countdown_tick, time - 1, victim))
        else:
            self.execute_victim(victim)

    def execute_victim(self, victim: Player) -> None:
        # 4. Massive Explosion (5x TNT)
        pos = (0, 2, 0)
        if victim.actor and victim.actor.node:
            pos = victim.actor.node.position
            
        # Standard TNT radius is approx 2.0. We use 10.0 for 5x power.
        bs.Blast(position=pos, blast_radius=10.0, blast_type='tnt').autoretain()
        
        if victim.actor:
            victim.actor.handlemessage(bs.DieMessage())
            
        self.eliminate_player(victim)
        self._bots.clear()
        bs.timer(3.0, self.setup_next_round)

    def eliminate_player(self, player: Player) -> None:
        # Add to eliminated list (First added = Last place)
        if player in self._tournament_survivors:
            self._tournament_survivors.remove(player)
            self._eliminated_order.append(player)

    # --- POINT SYSTEM ---
    def end_game_scoring(self) -> None:
        winner = self._tournament_survivors[0] if self._tournament_survivors else None
        
        # Construct Standings: [1st, 2nd, 3rd...]
        standings = []
        if winner:
            standings.append(winner)
        # eliminated_order has first loser (last place) at index 0. We reverse it.
        for p in reversed(self._eliminated_order):
            standings.append(p)
            
        # Points: Top 1->10, Top 2->7, Top 3->5, Top 4->3, Top 5->1
        points_map = {0: 10, 1: 7, 2: 5, 3: 3, 4: 1}
        
        bs.broadcastmessage("--- FINAL SCORES ---", color=(0.2, 1, 0.2))
        
        for i, player in enumerate(standings):
            points = points_map.get(i, 0)
            if points > 0:
                player.team.score += points
                # Accumscore shows up on the end screen player cards
                player.accumscore += points
                bs.broadcastmessage(f"#{i+1} {player.getname()}: +{points} pts", color=player.color)
        
        results = bs.GameResults()
        for team in self.teams:
            results.set_team_score(team, team.score)
        self.end(results=results)