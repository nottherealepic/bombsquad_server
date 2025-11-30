# ba_meta require api 8
# ba_meta export bascenev1.GameActivity

from __future__ import annotations
from typing import TYPE_CHECKING, List, Any

import bascenev1 as bs
import random
import math
from bascenev1lib.actor.flag import Flag, FlagPickedUpMessage
from bascenev1lib.actor.playerspaz import PlayerSpaz
from bascenev1lib.actor.spazbot import SpazBotSet, BomberBot, BrawlerBot
from bascenev1lib.actor.popuptext import PopupText
from bascenev1lib.actor.bomb import Blast

if TYPE_CHECKING:
    from typing import Sequence

class Player(bs.Player['Team']):
    """Our player type for this game."""
    def __init__(self) -> None:
        self.survived = True
        self.accumscore = 0 

class Team(bs.Team[Player]):
    """Our team type for this game."""
    def __init__(self) -> None:
        self.score = 0

class MFGame(bs.TeamGameActivity[Player, Team]):
    name = 'Musical Flags'
    description = "Get a Flag or Explode!"
    
    @classmethod
    def get_supported_maps(cls, sessiontype: type[bs.Session]) -> List[str]:
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
        
        self._epic_mode = bool(settings.get('Epic Mode', False))
        if self._epic_mode:
            self.default_music = bs.MusicType.EPIC
        else:
            self.default_music = bs.MusicType.FLAG_CATCHER

        self._round_num = 0
        self._flags: List[Flag] = []
        self._bots = SpazBotSet()
        self._round_in_progress = False
        
        # Lists
        self._tournament_survivors: List[Player] = [] 
        self._eliminated_order: List[Player] = []     
        self._round_active_players: List[Player] = [] 
        self._safe_players_this_round: List[Player] = []

    def on_begin(self) -> None:
        super().on_begin()
        
        # Single Player Check
        valid_players = [p for p in self.players if p.exists()]
        if len(valid_players) < 2:
            bs.broadcastmessage("Skipping: Need 2+ players.", color=(1, 1, 0))
            self.end()
            return

        self._tournament_survivors = list(valid_players)
        
        # Start
        bs.timer(2.0, self.setup_next_round)
        PopupText("GAME START...", position=(0, 5, 0), scale=2.0, color=(1,1,1)).autoretain()

    def on_player_leave(self, player: Player) -> None:
        if player in self._tournament_survivors:
            self._tournament_survivors.remove(player)
        if player in self._round_active_players:
            self._round_active_players.remove(player)
            
            # Handle mid-round leave
            if self._round_in_progress:
                if len(self._round_active_players) == 1:
                    self.start_punishment(self._round_active_players[0])
                elif len(self._round_active_players) == 0:
                    bs.timer(1.0, self.setup_next_round)
        super().on_player_leave(player)

    def setup_next_round(self) -> None:
        # Reset State
        self._round_in_progress = True
        self._bots.clear()
        self._safe_players_this_round = []
        
        for flag in self._flags:
            if flag.node: flag.node.delete()
        self._flags = []
        self._round_active_players = []
        
        # Clean Survivors
        self._tournament_survivors = [p for p in self._tournament_survivors if p.exists()]
        count = len(self._tournament_survivors)

        if count < 2:
            self.end_game_scoring()
            return

        self._round_num += 1
        bs.broadcastmessage(f"ROUND {self._round_num}", color=(1, 1, 0))

        if count == 2:
            self.setup_duel_round()
        else:
            self.setup_circle_round(count)

    def setup_duel_round(self) -> None:
        bs.broadcastmessage("FINAL DUEL!", color=(1, 0, 0), transient=True)
        # Flag Right
        self._flags.append(Flag(position=(10, 2, 0), color=(1, 1, 1), touchable=True))
        
        # Players Left
        for i, player in enumerate(self._tournament_survivors):
            self._round_active_players.append(player)
            z = -1.5 if i == 0 else 1.5
            self.spawn_and_position(player, (-10, 2, z))
            
        PopupText("GO!", position=(0, 5, 0), scale=2.0, color=(0,1,0)).autoretain()

    def setup_circle_round(self, count: int) -> None:
        flag_count = count - 1
        
        # Flags: Large Outer Circle (Radius 8)
        for i in range(flag_count):
            angle = (i / flag_count) * 360
            x = 8.0 * math.cos(math.radians(angle))
            z = 8.0 * math.sin(math.radians(angle))
            flg = Flag(position=(x, 2.5, z), color=(0, 1, 0), touchable=True)
            self._flags.append(flg)
            
        # Players: Small Inner Circle (Radius 1.5)
        # FIX: Using a small circle prevents the "Ghost Attack" physics explosion
        for i, player in enumerate(self._tournament_survivors):
            self._round_active_players.append(player)
            angle = (i / count) * 360
            px = 1.5 * math.cos(math.radians(angle))
            pz = 1.5 * math.sin(math.radians(angle))
            self.spawn_and_position(player, (px, 2.5, pz))

    def spawn_and_position(self, player: Player, position: tuple) -> None:
        spaz = self.spawn_player(player)
        # Controls: Punch/Run allowed. No Bombs. No Pickup.
        spaz.connect_controls_to_player(enable_punch=True, enable_bomb=False, enable_pickup=False)
        
        # Apply Shield and Brief Invincibility to prevent instant death bugs
        spaz.handlemessage(bs.PowerupMessage(poweruptype='shield'))
        spaz.node.invincible = True
        bs.timer(1.0, lambda: setattr(spaz.node, 'invincible', False) if spaz.node else None)
        
        spaz.handlemessage(bs.StandMessage(position))

    def handlemessage(self, msg: Any) -> Any:
        if isinstance(msg, FlagPickedUpMessage):
            # If round ended, ignore flags
            if not self._round_in_progress: return None

            node = msg.node
            flag = msg.flag
            
            try:
                player = node.getdelegate(PlayerSpaz, True).getplayer(Player, True)
            except Exception:
                return None

            if player in self._round_active_players:
                bs.playsound(bs.getsound('corkPop'))
                PopupText("SAFE!", position=node.position, color=(0,1,0), scale=1.6).autoretain()
                
                # Cleanup Flag
                if flag.node: flag.node.delete()
                if flag in self._flags: self._flags.remove(flag)
                
                # Mark Player Safe
                self._round_active_players.remove(player)
                self._safe_players_this_round.append(player)
                
                # Remove Actor (Vanish)
                if node: node.delete()
                
                # Check if 1 Loser Remains
                if len(self._round_active_players) == 1:
                    self.start_punishment(self._round_active_players[0])
            
            return None

        elif isinstance(msg, bs.PlayerDiedMessage):
            # If round isn't in progress (punishment time), deaths are expected
            if not self._round_in_progress: return super().handlemessage(msg)

            player = msg.getplayer(Player)
            
            # Ignore death if player is already safe (prevents double-counting)
            if player in self._safe_players_this_round:
                return None

            if player in self._round_active_players:
                self._round_active_players.remove(player)
                self.eliminate_player(player)
                
                if len(self._round_active_players) == 1:
                    self.start_punishment(self._round_active_players[0])
                elif len(self._round_active_players) == 0:
                    bs.timer(2.0, self.setup_next_round)

        return super().handlemessage(msg)

    def start_punishment(self, loser: Player) -> None:
        if not self._round_in_progress: return
        self._round_in_progress = False # Stop flags from working
        
        bs.broadcastmessage(f"{loser.getname()} ELIMINATED!", color=(1, 0, 0))
        
        # Position Loser at Center
        if loser.actor and loser.actor.node:
            loser.actor.handlemessage(bs.StandMessage(position=(0, 2, 0)))
            loser.actor.node.invincible = True
            bs.timer(0.1, lambda: loser.actor.handlemessage(bs.FreezeMessage()) if loser.actor else None)
            bs.timer(2.0, lambda: loser.actor.handlemessage(bs.ThawMessage()) if loser.actor else None)
            # Turn off invincibility so bots can kill
            bs.timer(2.0, lambda: setattr(loser.actor.node, 'invincible', False) if loser.actor and loser.actor.node else None)
        else:
            # If they fell off, respawn them to suffer
            self.spawn_and_position(loser, (0, 2, 0))
        
        # Spawn Angry Bots
        bs.playsound(bs.getsound('shieldDown'))
        self._bots.spawn_bot(BomberBot, pos=(3, 2, 0), spawn_time=0.5)
        self._bots.spawn_bot(BrawlerBot, pos=(-3, 2, 0), spawn_time=0.5)
        self._bots.spawn_bot(BomberBot, pos=(0, 2, 3), spawn_time=0.5)
        
        self.countdown_tick(5, loser)

    def countdown_tick(self, time: int, victim: Player) -> None:
        if not victim.exists():
            self._bots.clear()
            self.setup_next_round()
            return

        if time > 0:
            PopupText(str(time), position=(0, 5, 0), scale=2.5, color=(1, 0, 0)).autoretain()
            bs.playsound(bs.getsound('tick'))
            bs.timer(1.0, bs.Call(self.countdown_tick, time - 1, victim))
        else:
            self.execute_victim(victim)

    def execute_victim(self, victim: Player) -> None:
        pos = (0, 2, 0)
        if victim.actor and victim.actor.node:
            pos = victim.actor.node.position
            
        # 5x Power Explosion
        bs.Blast(position=pos, blast_radius=10.0, blast_type='tnt').autoretain()
        
        if victim.actor: 
            victim.actor.handlemessage(bs.DieMessage())
            
        self.eliminate_player(victim)
        self._bots.clear()
        bs.timer(3.0, self.setup_next_round)

    def eliminate_player(self, player: Player) -> None:
        if player in self._tournament_survivors:
            self._tournament_survivors.remove(player)
            self._eliminated_order.append(player)

    def end_game_scoring(self) -> None:
        winner = self._tournament_survivors[0] if self._tournament_survivors else None
        
        standings = []
        if winner: standings.append(winner)
        for p in reversed(self._eliminated_order): standings.append(p)
            
        points_map = {0: 10, 1: 7, 2: 5, 3: 3, 4: 1}
        
        bs.broadcastmessage("--- FINAL SCORES ---", color=(0.2, 1, 0.2))
        for i, player in enumerate(standings):
            points = points_map.get(i, 0)
            if points > 0:
                player.team.score += points
                player.accumscore += points
                bs.broadcastmessage(f"#{i+1} {player.getname()}: +{points} pts", color=player.color)
        
        results = bs.GameResults()
        for team in self.teams:
            results.set_team_score(team, team.score)
        self.end(results=results)