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
            self.slow_motion = True
            self.default_music = bs.MusicType.EPIC
        else:
            self.default_music = bs.MusicType.FLAG_CATCHER

        self._round_num = 0
        self._flags: List[Flag] = []
        self._bots = SpazBotSet()
        self._punishment_active = False
        
        # Game State Lists
        self._tournament_survivors: List[Player] = [] 
        self._eliminated_order: List[Player] = []     
        self._round_active_players: List[Player] = [] 

    def on_begin(self) -> None:
        super().on_begin()
        
        # --- CHECK PLAYER COUNT ---
        # If only 1 player, end immediately to prevent free points
        valid_players = [p for p in self.players if p.exists()]
        if len(valid_players) < 2:
            bs.broadcastmessage("Not enough players (Need 2+)", color=(1, 0, 0))
            self.end()
            return

        self._tournament_survivors = list(valid_players)
        
        # Delay start slightly so people realize what's happening
        bs.timer(2.0, self.setup_next_round)
        PopupText("PREPARE...", position=(0, 5, 0), scale=2.0, color=(1,1,1)).autoretain()

    def on_player_leave(self, player: Player) -> None:
        # Safe cleanup to prevent "God Level Bug"
        if player in self._tournament_survivors:
            self._tournament_survivors.remove(player)
        
        if player in self._round_active_players:
            self._round_active_players.remove(player)
            
            # If the round is running and this person leaving triggers the end
            if not self._punishment_active:
                if len(self._round_active_players) == 1:
                    self.start_punishment(self._round_active_players[0])
                elif len(self._round_active_players) == 0:
                    # Everyone left/died? Restart round.
                    bs.timer(1.0, self.setup_next_round)
                    
        super().on_player_leave(player)

    def setup_next_round(self) -> None:
        self._punishment_active = False
        self._bots.clear()
        
        # Clear old flags
        for flag in self._flags:
            if flag.node: flag.node.delete()
        self._flags = []
        self._round_active_players = []
        
        # Validate survivors
        self._tournament_survivors = [p for p in self._tournament_survivors if p.exists()]
        survivor_count = len(self._tournament_survivors)

        # Game Over Check
        if survivor_count < 2:
            self.end_game_scoring()
            return

        self._round_num += 1
        bs.broadcastmessage(f"ROUND {self._round_num}", color=(1, 1, 0))

        if survivor_count == 2:
            self.setup_duel_round()
        else:
            self.setup_circle_round(survivor_count)

    def setup_duel_round(self) -> None:
        # 1v1 Logic: Edge to Edge
        bs.broadcastmessage("FINAL DUEL!", color=(1, 0, 0), transient=True)
        p_x = -10.0 
        f_x = 10.0 
        
        self._flags.append(Flag(position=(f_x, 2, 0), color=(1, 1, 1), touchable=True))
        
        for i, player in enumerate(self._tournament_survivors):
            self._round_active_players.append(player)
            z_pos = -1.5 if i == 0 else 1.5
            self.spawn_and_position_player(player, position=(p_x, 2, z_pos))
            
        bs.playsound(bs.getsound('whistle'))
        PopupText("GO!", position=(0, 5, 0), scale=2.0, color=(0,1,0)).autoretain()

    def setup_circle_round(self, count: int) -> None:
        # Normal Logic: Flags Outside, Players Center
        flag_count = count - 1
        
        # Spawn Flags in Circle (Radius 7)
        for i in range(flag_count):
            angle = (i / flag_count) * 360
            x = 7.0 * math.cos(math.radians(angle))
            z = 7.0 * math.sin(math.radians(angle))
            flg = Flag(position=(x, 2.5, z), color=(0, 1, 0), touchable=True)
            self._flags.append(flg)
            
        # Spawn Players in Center (with jitter to prevent physics explosion)
        for player in self._tournament_survivors:
            self._round_active_players.append(player)
            # Jitter: Random offset so they don't spawn INSIDE each other perfectly
            jx = random.uniform(-0.5, 0.5)
            jz = random.uniform(-0.5, 0.5)
            self.spawn_and_position_player(player, position=(jx, 2.5, jz))

    def spawn_and_position_player(self, player: Player, position: tuple) -> None:
        spaz = self.spawn_player(player)
        spaz.connect_controls_to_player(enable_punch=True, enable_bomb=False, enable_pickup=False)
        spaz.handlemessage(bs.StandMessage(position))
        
        # Face direction
        angle = random.uniform(0, 360)
        if position[0] == -10: angle = 0 # Duel facing
        spaz.handlemessage(bs.StandMessage(position, angle=angle))

    def handlemessage(self, msg: Any) -> Any:
        if isinstance(msg, FlagPickedUpMessage):
            # If in punishment phase, ignore flag touches
            if self._punishment_active:
                return None

            node = msg.node
            flag = msg.flag
            
            try:
                player = node.getdelegate(PlayerSpaz, True).getplayer(Player, True)
            except Exception:
                return None

            if player in self._round_active_players:
                bs.playsound(bs.getsound('corkPop'))
                PopupText("SAFE!", position=node.position, color=(0,1,0), scale=1.6).autoretain()
                
                # Remove Flag
                if flag.node: flag.node.delete()
                if flag in self._flags:
                    self._flags.remove(flag)
                
                # Hide Player (Success)
                self._round_active_players.remove(player)
                if node: node.delete() # Remove body immediately
                
                # Check Win Condition
                if len(self._round_active_players) == 1:
                    self.start_punishment(self._round_active_players[0])
            
            return None

        elif isinstance(msg, bs.PlayerDiedMessage):
            # If punishment is active, ignore death messages (victim logic handles itself)
            if self._punishment_active:
                return super().handlemessage(msg)

            player = msg.getplayer(Player)
            if player in self._round_active_players:
                # Player died during the run (fell off map)
                self._round_active_players.remove(player)
                self.eliminate_player(player)
                bs.broadcastmessage(f"{player.getname()} fell!", color=(1,0,0))
                
                if len(self._round_active_players) == 1:
                    self.start_punishment(self._round_active_players[0])
                elif len(self._round_active_players) == 0:
                     bs.timer(2.0, self.setup_next_round)

        return super().handlemessage(msg)

    def start_punishment(self, loser: Player) -> None:
        if self._punishment_active: return
        self._punishment_active = True
        
        bs.broadcastmessage(f"{loser.getname()} FAILED!", color=(1, 0, 0))
        
        # Teleport Loser to Center
        if loser.actor and loser.actor.node:
             loser.actor.handlemessage(bs.StandMessage(position=(0, 2, 0)))
             bs.timer(0.1, lambda: loser.actor.handlemessage(bs.FreezeMessage()) if loser.actor else None)
             bs.timer(1.0, lambda: loser.actor.handlemessage(bs.ThawMessage()) if loser.actor else None)
        else:
            self.spawn_and_position_player(loser, (0, 2, 0))
        
        # Spawn Bots
        bs.playsound(bs.getsound('shieldDown'))
        self._bots.spawn_bot(BomberBot, pos=(3, 2, 0), spawn_time=0.5)
        self._bots.spawn_bot(BrawlerBot, pos=(-3, 2, 0), spawn_time=0.5)
        self._bots.spawn_bot(BomberBot, pos=(0, 2, 3), spawn_time=0.5)
        
        # Start Countdown
        self.countdown_tick(5, loser)

    def countdown_tick(self, time: int, victim: Player) -> None:
        # If victim left during countdown, stop to prevent crash
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
        if winner:
            standings.append(winner)
        for p in reversed(self._eliminated_order):
            standings.append(p)
            
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