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

# --- CONFIGURATION (NO EMOJIS TO PREVENT ERRORS) ---
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

    def on_begin(self) -> None:
        super().on_begin()
        
        # 1. FORCE DARKNESS (Lighting)
        self.globalsnode.tint = (0, 0, 0) 
        self.globalsnode.ambient_color = (0, 0, 0)
        self.globalsnode.vignette_outer = (0, 0, 0)
        self.globalsnode.vignette_inner = (0, 0, 0)

        # 2. BLACK BACKGROUND LAYER (To hide the map fog)
        # We create a massive black square behind everything
        bs.newnode('image', attrs={
            'texture': bs.gettexture('softRect'),
            'position': (0, 0),
            'scale': (2000, 1000),
            'color': (0, 0, 0),
            'opacity': 1.0,
            'absolute_scale': False
        })

        # 3. TITLE SECTION
        bs.newnode('text', attrs={
            'text': SERVER_TITLE,
            'scale': 1.5,
            'position': (0, 260),
            'color': (1, 1, 1), # WHITE
            'h_align': 'center',
            'v_align': 'center',
            'shadow': 1.0,
            'maxwidth': 800
        })
        bs.newnode('text', attrs={
            'text': SERVER_IP_TEXT,
            'scale': 0.9,
            'position': (0, 230),
            'color': (0.7, 0.7, 0.7), # LIGHT GREY
            'h_align': 'center',
            'v_align': 'center'
        })
        bs.newnode('text', attrs={
            'text': DISCORD_TEXT,
            'scale': 1.0,
            'position': (0, 200),
            'color': (0.4, 0.6, 1.0), # BLUE
            'h_align': 'center',
            'v_align': 'center'
        })

        # 4. THE GREY INSTRUCTION BOX
        # Using 'softRect' with low opacity for the glass effect
        bs.newnode('image', attrs={
            'texture': bs.gettexture('softRect'),
            'position': (0, 30),
            'scale': (900, 350),
            'opacity': 0.2, # Transparent
            'color': (1, 1, 1), # White tint but low opacity makes it look glass/grey
            'absolute_scale': False
        })
        
        # 5. INSTRUCTIONS TEXT (Must be bright to be readable)
        self.create_instruction_text("How to Make This Server Yours?", 110, scale=1.2, color=(1, 0.8, 0)) # GOLD
        self.create_instruction_text("1. Join the Discord Server", 70)
        self.create_instruction_text("2. Look for the Code in your Chat (bottom left)", 40)
        self.create_instruction_text("3. Go to #create-free-server channel", 10)
        self.create_instruction_text("4. Type: /deploy <code> <ServerName>", -20)
        self.create_instruction_text("5. Wait for the bot to confirm!", -50)
        self.create_instruction_text("Congrats! You will be Owner for 60 mins.", -90, color=(1, 0.5, 0)) # ORANGE

        # 6. RED FOOTER BAR
        bs.newnode('image', attrs={
            'texture': bs.gettexture('softRect'),
            'position': (0, -220),
            'scale': (1200, 100),
            'opacity': 1.0,
            'color': (0.6, 0.1, 0.1), # DEEP RED
        })
        
        # Footer Text
        bs.newnode('text', attrs={
            'text': FOOTER_TEXT,
            'scale': 1.0,
            'position': (0, -220),
            'color': (1, 1, 1),
            'h_align': 'center',
            'v_align': 'center',
            'shadow': 1.0
        })

        # 7. BOMB ICONS ON FOOTER
        # We use tint_color to make them visible on the red bar
        bs.newnode('image', attrs={
            'texture': bs.gettexture('characterIconBomber'),
            'position': (-350, -220),
            'scale': (70, 70),
            'tint_color': (1, 0.8, 0.8), # Light reddish tint
            'absolute_scale': False
        })
        bs.newnode('image', attrs={
            'texture': bs.gettexture('characterIconBomber'),
            'position': (350, -220),
            'scale': (70, 70),
            'tint_color': (1, 0.8, 0.8),
            'absolute_scale': False
        })

    def create_instruction_text(self, text, y, scale=0.9, color=(0.9, 0.9, 0.9)):
        bs.newnode('text', attrs={
            'text': text,
            'scale': scale,
            'position': (0, y),
            'color': color,
            'h_align': 'center',
            'v_align': 'center',
            'shadow': 0.8 # Shadow helps readability
        })

    def spawn_player(self, player: Player) -> bs.Actor:
        # No character spawning
        return None 

    def on_player_join(self, player: Player) -> None:
        try:
            pb_id = player.sessionplayer.get_v1_account_id()
        except:
            pb_id = None

        if pb_id is None:
            # Use broadcastmessage (no underscore)
            bs.broadcastmessage("Please Sign-In to get a code!", 
                               clients=[player.sessionplayer.inputdevice.client_id], 
                               color=(1,0,0), transient=True)
            return

        code = str(random.randint(1000, 9999))
        self.codes[pb_id] = code
        self.save_codes_to_file()

        # Send Code to Player Chat (Private)
        client_id = player.sessionplayer.inputdevice.client_id
        bs.broadcastmessage(f"YOUR CODE: {code}", clients=[client_id], color=(0,1,0), transient=True)
        
        # Show Big Code on screen just for them
        self.show_floating_code(code)

    def show_floating_code(self, code):
        # Flashes the code on screen
        t = bs.newnode('text', attrs={
            'text': f"YOUR OTP CODE: {code}",
            'position': (0, -120), # Just above the footer
            'scale': 2.0,
            'color': (0, 1, 0),
            'h_align': 'center',
            'shadow': 1.0
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