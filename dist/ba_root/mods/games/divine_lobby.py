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
DATA_FILE = "/home/ubuntu/cfs_data/codes.json" 
SERVER_TITLE = "DIVINE FREE SERVER FACTORY" 
SERVER_IP_TEXT = "Server IP: 123.45.67.89   PORT: 43211"
DISCORD_TEXT = "Join Our Discord: discord.gg/yourlink"
FOOTER_TEXT = "Created by: Divine | System: Auto-Deploy"

class Player(bs.Player['Team']):
    """Our player type for this game."""

class Team(bs.Team[Player]):
    """Our team type for this game."""

# ba_meta export bascenev1.GameActivity
class DivineLobbyGame(bs.TeamGameActivity[Player, Team]):
    """The UI-Based Waiting Room."""

    name = 'Divine Lobby UI'
    description = 'Join Discord to deploy.'
    allow_mid_activity_joins = True

    @classmethod
    def get_supported_maps(cls, sessiontype: Type[bs.Session]) -> List[str]:
        return ['Hockey Stadium']

    def __init__(self, settings: dict) -> None:
        super().__init__(settings)
        self.codes = {} 
        # Create a timer to remind players of their code every 8 seconds
        self._code_reminder_timer = bs.Timer(8.0, self.remind_codes, repeat=True)

    def on_begin(self) -> None:
        super().on_begin()
        
        # 1. FORCE DARKNESS
        self.globalsnode.tint = (0, 0, 0) 
        self.globalsnode.ambient_color = (0, 0, 0)
        self.globalsnode.vignette_outer = (0, 0, 0)
        self.globalsnode.vignette_inner = (0, 0, 0)

        # 2. BLACK BACKGROUND
        bs.newnode('image', attrs={
            'texture': bs.gettexture('softRect'),
            'position': (0, 0),
            'scale': (2000, 1000),
            'color': (0, 0, 0),
            'opacity': 1.0,
            'absolute_scale': False
        })

        # 3. TEXT UI
        bs.newnode('text', attrs={
            'text': SERVER_TITLE,
            'scale': 1.5,
            'position': (0, 260),
            'color': (1, 1, 1),
            'h_align': 'center',
            'v_align': 'center',
            'shadow': 1.0,
            'maxwidth': 800
        })
        bs.newnode('text', attrs={
            'text': SERVER_IP_TEXT,
            'scale': 0.9,
            'position': (0, 230),
            'color': (0.7, 0.7, 0.7),
            'h_align': 'center',
            'v_align': 'center'
        })
        bs.newnode('text', attrs={
            'text': DISCORD_TEXT,
            'scale': 1.0,
            'position': (0, 200),
            'color': (0.4, 0.6, 1.0),
            'h_align': 'center',
            'v_align': 'center'
        })

        # 4. INSTRUCTION BOX
        bs.newnode('image', attrs={
            'texture': bs.gettexture('softRect'),
            'position': (0, 30),
            'scale': (900, 350),
            'opacity': 0.2,
            'color': (1, 1, 1),
            'absolute_scale': False
        })
        
        # Instructions
        self.create_instruction_text("How to Make This Server Yours?", 110, scale=1.2, color=(1, 0.8, 0))
        self.create_instruction_text("1. Join the Discord Server", 70)
        self.create_instruction_text("2. Look for the Code in your Chat Box", 40)
        self.create_instruction_text("3. Go to #create-free-server channel", 10)
        self.create_instruction_text("4. Type: /deploy <code> <ServerName>", -20)
        self.create_instruction_text("5. Wait for the bot to confirm!", -50)
        self.create_instruction_text("Congrats! You will be Owner for 60 mins.", -90, color=(1, 0.5, 0))

        # 5. FOOTER
        bs.newnode('image', attrs={
            'texture': bs.gettexture('softRect'),
            'position': (0, -220),
            'scale': (1200, 100),
            'opacity': 1.0,
            'color': (0.6, 0.1, 0.1),
        })
        
        bs.newnode('text', attrs={
            'text': FOOTER_TEXT,
            'scale': 1.0,
            'position': (0, -220),
            'color': (1, 1, 1),
            'h_align': 'center',
            'v_align': 'center',
            'shadow': 1.0
        })

    def create_instruction_text(self, text, y, scale=0.9, color=(0.9, 0.9, 0.9)):
        bs.newnode('text', attrs={
            'text': text,
            'scale': scale,
            'position': (0, y),
            'color': color,
            'h_align': 'center',
            'v_align': 'center',
            'shadow': 0.8
        })

    def spawn_player(self, player: Player) -> bs.Actor:
        return None 

    def on_player_join(self, player: Player) -> None:
        self.process_player_code(player)

    def process_player_code(self, player: Player):
        # Get Account ID
        try:
            pb_id = player.sessionplayer.get_v1_account_id()
        except:
            pb_id = None

        if pb_id is None:
            client_id = player.sessionplayer.inputdevice.client_id
            bs.broadcastmessage("⚠ PLEASE SIGN IN TO GET CODE ⚠", clients=[client_id], color=(1,0,0), transient=True)
            return

        # Reuse existing code if they have one, else new
        if pb_id in self.codes:
            code = self.codes[pb_id]
        else:
            code = str(random.randint(1000, 9999))
            self.codes[pb_id] = code
            self.save_codes_to_file()

        # Send Code Immediately
        self.send_code_to_client(player, code)

    def remind_codes(self):
        # Loop through all players and remind them of their code
        for player in self.players:
            if player.is_alive(): # 'is_alive' checks if they are still in game
                try:
                    pb_id = player.sessionplayer.get_v1_account_id()
                    if pb_id and pb_id in self.codes:
                        self.send_code_to_client(player, self.codes[pb_id])
                except:
                    pass

    def send_code_to_client(self, player, code):
        client_id = player.sessionplayer.inputdevice.client_id
        
        # 1. Send to Screen (Top Pop-up)
        bs.broadcastmessage(f"YOUR CODE: {code}", clients=[client_id], color=(0,1,0), transient=True)
        
        # 2. Send to Chat History (Blue Box) - transient=False puts it in history
        bs.broadcastmessage(f"🔑 CODE: {code} | Use /deploy in Discord", clients=[client_id], color=(1,1,1), transient=False)

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