# ba_meta require api 9
from __future__ import annotations
from typing import TYPE_CHECKING

import babase
import bauiv1 as bui
import bascenev1 as bs
import random
import json
import os

if TYPE_CHECKING:
    from typing import Any, List, Type, Optional

# --- CONFIGURATION ---
# We use the home folder so we don't get Permission Denied errors
DATA_FILE = "/home/ubuntu/cfs_data/codes.json" 
SERVER_NAME_TEXT = "👑 CREATE FREE SERVER BY DIVINE 👑"
SUB_TEXT = "Join Discord to Deploy | Your Code is in Chat"

class Player(bs.Player['Team']):
    """Our player type for this game."""

class Team(bs.Team[Player]):
    """Our team type for this game."""

# ba_meta export bascenev1.GameActivity
class DivineLobbyGame(bs.TeamGameActivity[Player, Team]):
    """The Waiting Room / Lobby."""

    name = 'Divine Lobby'
    description = 'Get your code here.'
    allow_mid_activity_joins = True

    @classmethod
    def get_supported_maps(cls, sessiontype: Type[bs.Session]) -> List[str]:
        return ['Hockey Stadium']

    def __init__(self, settings: dict) -> None:
        super().__init__(settings)
        self._text_node: Optional[bs.Node] = None
        self.codes = {} 

    def on_begin(self) -> None:
        super().on_begin()
        
        # --- VISUALS: MAKE IT BLACK ---
        self.globalsnode.tint = (0, 0, 0) 
        self.globalsnode.ambient_color = (0, 0, 0)
        self.globalsnode.vignette_outer = (0, 0, 0)
        self.globalsnode.vignette_inner = (0, 0, 0)

        # --- TITLE TEXT ---
        self._text_node = bs.newnode('text',
                                     attrs={
                                         'text': SERVER_NAME_TEXT,
                                         'scale': 2.0,
                                         'maxwidth': 1000,
                                         'position': (0, 3), 
                                         'shadow': 1.0,
                                         'flatness': 1.0,
                                         'color': (1, 0.8, 0),
                                         'h_align': 'center',
                                         'v_align': 'center'
                                     })
        
        bs.animate_array(self._text_node, 'color', 3,
                         {0: (1, 0, 0), 0.5: (1, 1, 0), 1.0: (0, 1, 0), 
                          1.5: (0, 1, 1), 2.0: (0, 0, 1), 2.5: (1, 0, 1), 3.0: (1, 0, 0)},
                         loop=True)

        # --- SUB TEXT ---
        bs.newnode('text',
                   attrs={
                       'text': SUB_TEXT,
                       'scale': 1.1,
                       'position': (0, 1),
                       'color': (1, 1, 1),
                       'h_align': 'center',
                       'v_align': 'center'
                   })

    def spawn_player(self, player: Player) -> bs.Actor:
        return None 

    def on_player_join(self, player: Player) -> None:
        try:
            pb_id = player.sessionplayer.get_v1_account_id()
        except Exception:
            pb_id = None

        if pb_id is None:
            # Send message only to that specific player
            bs.broadcastmessage("⚠ Please Sign-In to get a code!", 
                               clients=[player.sessionplayer.inputdevice.client_id], 
                               color=(1,0,0), transient=True)
            return

        # Generate Code
        code = str(random.randint(1000, 9999))
        
        self.codes[pb_id] = code
        self.save_codes_to_file()

        # --- SEND CODE PRIVATELY ---
        # FIX: Changed broadcast_message to broadcastmessage
        client_id = player.sessionplayer.inputdevice.client_id
        
        bs.broadcastmessage(f"🔑 YOUR CODE: {code}", clients=[client_id], color=(0,1,0), transient=True)
        bs.broadcastmessage(f"Type /deploy {code} <Name> in Discord", clients=[client_id], color=(1,1,1), transient=True)
        
        self.show_personal_code_on_screen(code, player)

    def show_personal_code_on_screen(self, code, player):
        t = bs.newnode('text',
                       attrs={
                           'text': f"CODE: {code}",
                           'position': (0, -2),
                           'scale': 3.0,
                           'color': (0, 1, 0),
                           'h_align': 'center'
                       })
        bs.animate(t, 'scale', {0: 0.0, 0.2: 3.0, 5.0: 3.0, 5.5: 0.0})
        # Using a timer to delete the node after 5.5 seconds
        bs.timer(5.5, t.delete)

    def save_codes_to_file(self):
        current_data = {}
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r') as f:
                    current_data = json.load(f)
            except:
                pass
        
        current_data.update(self.codes)
        
        try:
            with open(DATA_FILE, 'w') as f:
                json.dump(current_data, f)
        except Exception as e:
            print(f"Error saving codes: {e}")

    def handlemessage(self, msg: Any) -> Any:
        super().handlemessage(msg)