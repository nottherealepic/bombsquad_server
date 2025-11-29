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
# Where to save the codes so the Discord Bot can read them
DATA_FILE = "/root/cfs_data/codes.json" 
SERVER_NAME_TEXT = "👑 CREATE FREE SERVER BY DIVINE 👑"
SUB_TEXT = "Join our Discord to deploy your own server for 60 mins!"

class Player(bs.Player['Team']):
    """Our player type for this game."""

class Team(bs.Team[Player]):
    """Our team type for this game."""

# ba_meta export bascenev1.GameActivity
class DivineLobbyGame(bs.TeamGameActivity[Player, Team]):
    """The Waiting Room / Lobby."""

    name = 'Divine Lobby'
    description = 'Get your code here.'
    
    # We make this game never end automatically (until bot changes it)
    allow_mid_activity_joins = True

    @classmethod
    def get_supported_maps(cls, sessiontype: Type[bs.Session]) -> List[str]:
        # Use a simple map like Hockey or Courtyard
        return ['Hockey Stadium']

    def __init__(self, settings: dict) -> None:
        super().__init__(settings)
        self._text_node: Optional[bs.Node] = None
        self._sub_text_node: Optional[bs.Node] = None
        self.codes = {} # Store codes here: {pb_id: code}

    def on_begin(self) -> None:
        super().on_begin()
        
        # 1. Create the Big Title Text (Animated)
        self._text_node = bs.newnode('text',
                                     attrs={
                                         'text': SERVER_NAME_TEXT,
                                         'scale': 2.0,
                                         'maxwidth': 1200,
                                         'position': (0, 100), # Middle of screen
                                         'shadow': 1.0,
                                         'flatness': 1.0,
                                         'color': (1, 0.8, 0),
                                         'h_align': 'center',
                                         'v_align': 'center'
                                     })
        
        # Animate the color of the title
        bs.animate_array(self._text_node, 'color', 3,
                         {0: (1, 0.8, 0), 1.0: (1, 0.5, 0), 2.0: (1, 1, 0)},
                         loop=True)

        # 2. Create Description Text
        self._sub_text_node = bs.newnode('text',
                                         attrs={
                                             'text': SUB_TEXT,
                                             'scale': 1.2,
                                             'position': (0, 50),
                                             'color': (1, 1, 1),
                                             'h_align': 'center',
                                             'v_align': 'center'
                                         })

    def on_player_join(self, player: Player) -> None:
        # 1. Generate a specific code for this player
        code = str(random.randint(1000, 9999))
        pb_id = player.get_account_id()
        
        if pb_id is None:
            # If they are not signed in
            bs.broadcast_message("Please Sign-In to get a code!", clients=[player.get_input_device().client_id], color=(1,0,0), transient=True)
            return

        # 2. Save to internal dict
        self.codes[pb_id] = code
        
        # 3. Write to JSON file for the Discord Bot
        self.save_codes_to_file()

        # 4. Show the code ONLY to that player
        # We use 'transient=True' so it pops up like a chat message but doesn't stay in log forever
        bs.broadcast_message(f"🔑 YOUR CODE: {code}", clients=[player.get_input_device().client_id], color=(0,1,0), transient=True)
        bs.broadcast_message(f"Type /deploy {code} <Name> in Discord", clients=[player.get_input_device().client_id], color=(1,1,1), transient=True)

    def save_codes_to_file(self):
        # This saves the list of active codes so the bot can verify them
        try:
            with open(DATA_FILE, 'w') as f:
                json.dump(self.codes, f)
        except Exception as e:
            print(f"Error saving codes: {e}")

    # We remove logic that kills players or scores points
    def handlemessage(self, msg: Any) -> Any:
        if isinstance(msg, bs.PlayerDiedMessage):
            # Respawn them instantly if they somehow die
            self.respawn_player(msg.getplayer(Player))
        else:
            super().handlemessage(msg)