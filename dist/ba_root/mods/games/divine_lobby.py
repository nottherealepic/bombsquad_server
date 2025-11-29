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
DATA_FILE = "/root/cfs_data/codes.json" 
SERVER_NAME_TEXT = "👑 CREATE FREE SERVER BY DIVINE 👑"
SUB_TEXT = "Join Discord to Deploy | Your Code is in Chat"

class Player(bs.Player['Team']):
    """Our player type for this game."""

class Team(bs.Team[Player]):
    """Our team type for this game."""

# ba_meta export bascenev1.GameActivity
class DivineLobbyGame(bs.TeamGameActivity[Player, Team]):
    """The Waiting Room / Lobby."""

    name = 'CREATE A FREE SERVER BY DIVINE'
    description = 'Get your code here.'
    allow_mid_activity_joins = True

    @classmethod
    def get_supported_maps(cls, sessiontype: Type[bs.Session]) -> List[str]:
        # We use Hockey because it loads fast, but we will hide it
        return ['Hockey Stadium']

    def __init__(self, settings: dict) -> None:
        super().__init__(settings)
        self._text_node: Optional[bs.Node] = None
        self.codes = {} 

    def on_begin(self) -> None:
        super().on_begin()
        
        # --- VISUALS: MAKE IT BLACK ---
        # This turns off the lights so the map is invisible (Black Void)
        self.globalsnode.tint = (0, 0, 0) 
        self.globalsnode.ambient_color = (0, 0, 0)
        self.globalsnode.vignette_outer = (0, 0, 0)
        self.globalsnode.vignette_inner = (0, 0, 0)

        # --- TITLE TEXT ---
        # Position (0, 2) raises it up a bit in 3D space so it's center screen
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
        
        # Rainbow Animation for Title
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
        # OVERRIDE: We do NOT spawn a spaz/character.
        # This keeps the camera fixed and prevents fighting.
        return None 

    def on_player_join(self, player: Player) -> None:
        # --- FIX FOR THE ERROR ---
        # We use sessionplayer to get the account ID
        try:
            pb_id = player.sessionplayer.get_v1_account_id()
        except Exception:
            pb_id = None

        if pb_id is None:
            # Send message only to that specific player client
            bs.broadcast_message("⚠ Please Sign-In to get a code!", 
                               clients=[player.sessionplayer.inputdevice.client_id], 
                               color=(1,0,0), transient=True)
            return

        # Generate Code
        code = str(random.randint(1000, 9999))
        
        # Save to Dictionary and File
        self.codes[pb_id] = code
        self.save_codes_to_file()

        # --- SEND CODE PRIVATELY ---
        # transient=True makes it pop up like a notification, not clutter chat log
        client_id = player.sessionplayer.inputdevice.client_id
        
        bs.broadcast_message(f"🔑 YOUR CODE: {code}", clients=[client_id], color=(0,1,0), transient=True)
        bs.broadcast_message(f"Type /deploy {code} <Name> in Discord", clients=[client_id], color=(1,1,1), transient=True)
        
        # Also print to screen center for 5 seconds specifically for them (using a text node)
        self.show_personal_code_on_screen(code, player)

    def show_personal_code_on_screen(self, code, player):
        # This creates a floating text just for that player that fades out
        # Note: In standard BS, 3D nodes are visible to everyone. 
        # We rely on the broadcast message above for privacy, 
        # but this effect looks cool for videos.
        t = bs.newnode('text',
                       attrs={
                           'text': f"CODE: {code}",
                           'position': (0, -2),
                           'scale': 3.0,
                           'color': (0, 1, 0),
                           'h_align': 'center'
                       })
        bs.animate(t, 'scale', {0: 0.0, 0.2: 3.0, 5.0: 3.0, 5.5: 0.0})
        bs.timer(5.5, t.delete)

    def save_codes_to_file(self):
        # Load existing codes first to not wipe others
        current_data = {}
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, 'r') as f:
                    current_data = json.load(f)
            except:
                pass
        
        # Merge new codes
        current_data.update(self.codes)
        
        # Save back
        try:
            with open(DATA_FILE, 'w') as f:
                json.dump(current_data, f)
        except Exception as e:
            print(f"Error saving codes: {e}")

    def handlemessage(self, msg: Any) -> Any:
        # Ignore death messages etc
        super().handlemessage(msg)