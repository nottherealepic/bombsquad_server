# ba_meta require api 9
from __future__ import annotations
from typing import TYPE_CHECKING

import babase
import bascenev1 as bs
import random
import json
import os

if TYPE_CHECKING:
    from typing import Any, List, Type, Optional

# --- CONFIGURATION ---
DATA_FILE = "/home/ubuntu/cfs_data/codes.json" 
SERVER_TITLE = "DIVINE'S FREE SERVER FACTORY"
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

    def on_begin(self) -> None:
        super().on_begin()
        
        # 1. THE BLACKOUT (Hide the 3D Map)
        self.globalsnode.tint = (0, 0, 0) 
        self.globalsnode.ambient_color = (0, 0, 0)
        self.globalsnode.vignette_outer = (0, 0, 0)
        self.globalsnode.vignette_inner = (0, 0, 0)

        # 2. HEADER TEXT
        # Title
        bs.newnode('text', attrs={
            'text': SERVER_TITLE,
            'scale': 1.6,
            'position': (0, 250), # High up
            'color': (1, 1, 1),
            'h_align': 'center',
            'v_align': 'center',
            'shadow': 1.0,
            'maxwidth': 800
        })
        # IP & Port
        bs.newnode('text', attrs={
            'text': SERVER_IP_TEXT,
            'scale': 1.0,
            'position': (0, 210),
            'color': (0.7, 0.7, 0.7),
            'h_align': 'center',
            'v_align': 'center'
        })
        # Discord
        bs.newnode('text', attrs={
            'text': DISCORD_TEXT,
            'scale': 1.1,
            'position': (0, 180),
            'color': (0.5, 0.5, 1), # Light Blue
            'h_align': 'center',
            'v_align': 'center'
        })

        # 3. THE GREY BOX (Background for instructions)
        # We use the built-in 'softRect' texture to make the box
        box_width = 900
        box_height = 350
        bs.newnode('image', attrs={
            'texture': bs.gettexture('softRect'),
            'position': (0, 0),
            'scale': (box_width, box_height),
            'opacity': 0.8,
            'color': (0.2, 0.2, 0.25), # Dark Blue-Grey
            'absolute_scale': False
        })
        
        # 4. INSTRUCTIONS INSIDE THE BOX
        self.create_instruction_text("How to Make This Server Yours?", 80, scale=1.3, color=(1, 1, 0))
        self.create_instruction_text("1. Join the Discord Server", 40)
        self.create_instruction_text("2. Look for the Code in your Chat (bottom left)", 10)
        self.create_instruction_text("3. Go to #create-free-server channel", -20)
        self.create_instruction_text("4. Type: /deploy <code-displayed-here> <ServerName>", -50)
        self.create_instruction_text("5. Wait for the bot to confirm!", -80)
        self.create_instruction_text("Congrats! You will be Owner for 60 mins.", -120, color=(1, 0.5, 0))

        # 5. FOOTER (Red Bar look)
        bs.newnode('image', attrs={
            'texture': bs.gettexture('softRect'),
            'position': (0, -200),
            'scale': (1000, 80),
            'opacity': 0.9,
            'color': (0.5, 0.1, 0.1), # Dark Red
        })
        
        # Footer Text
        bs.newnode('text', attrs={
            'text': FOOTER_TEXT,
            'scale': 1.0,
            'position': (0, -200),
            'color': (1, 1, 1),
            'h_align': 'center',
            'v_align': 'center'
        })

        # Bomb Icons (Left and Right of footer)
        bs.newnode('image', attrs={
            'texture': bs.gettexture('characterIconBomber'),
            'position': (-300, -200),
            'scale': (60, 60),
            'tint_color': (1, 0.5, 0.5)
        })
        bs.newnode('image', attrs={
            'texture': bs.gettexture('characterIconBomber'),
            'position': (300, -200),
            'scale': (60, 60),
            'tint_color': (1, 0.5, 0.5)
        })

    def create_instruction_text(self, text, y, scale=0.9, color=(0.9, 0.9, 0.9)):
        bs.newnode('text', attrs={
            'text': text,
            'scale': scale,
            'position': (0, y),
            'color': color,
            'h_align': 'center',
            'v_align': 'center',
            'shadow': 0.5
        })

    def spawn_player(self, player: Player) -> bs.Actor:
        # RETURN NONE = No character spawns, camera stays fixed on UI
        return None 

    def on_player_join(self, player: Player) -> None:
        # --- CODE GENERATION LOGIC ---
        try:
            pb_id = player.sessionplayer.get_v1_account_id()
        except:
            pb_id = None

        if pb_id is None:
            bs.broadcastmessage("⚠ Please Sign-In to get a code!", 
                               clients=[player.sessionplayer.inputdevice.client_id], 
                               color=(1,0,0), transient=True)
            return

        code = str(random.randint(1000, 9999))
        self.codes[pb_id] = code
        self.save_codes_to_file()

        # Send Code to Player Chat (Private)
        client_id = player.sessionplayer.inputdevice.client_id
        bs.broadcastmessage(f"🔑 YOUR CODE: {code}", clients=[client_id], color=(0,1,0), transient=True)
        
        # Show Big Code on screen just for them
        self.show_floating_code(code)

    def show_floating_code(self, code):
        # Flashes the code on screen
        t = bs.newnode('text', attrs={
            'text': f"YOUR OTP CODE: {code}",
            'position': (0, -300), # Bottom of screen
            'scale': 2.0,
            'color': (0, 1, 0),
            'h_align': 'center'
        })
        bs.animate(t, 'scale', {0: 0.0, 0.2: 2.0, 5.0: 2.0, 5.5: 0.0})
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