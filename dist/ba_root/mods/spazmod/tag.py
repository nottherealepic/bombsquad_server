import setting
from playersdata import pdata
from stats import mystats

import babase
import bascenev1 as bs

# --- Initialize Settings ---
sett = setting.get_settings_data()


# --- Utility Functions ---

def addtag(node, player, style_override=None):
    """
    Creates and attaches the Tag to the player's node.
    It passes the style_override (e.g., from player data) to the Tag class.
    """
    session_player = player.sessionplayer
    account_id = session_player.get_v1_account_id()
    customtag_ = pdata.get_custom()
    customtag = customtag_['customtag']
    roles = pdata.get_roles()
    p_roles = pdata.get_player_roles(account_id)
    tag = None
    col = (0.5, 0.5, 1) 
    if account_id in customtag:
        tag = customtag[account_id]
    elif p_roles != []:
        for role in roles:
            if role in p_roles:
                tag = roles[role]['tag']
                col = (
                    0.7, 0.7, 0.7) if 'tagcolor' not in roles[role] else \
                    roles[role]['tagcolor']
                break
    if tag:
        # Returns the Tag instance for external use (like calling animate_death_flow)
        return Tag(node, tag, col, style_id=style_override) 
    return None # Return None if no tag was created


def addrank(node, player):
    session_player = player.sessionplayer
    account_id = session_player.get_v1_account_id()
    rank = mystats.getRank(account_id)
    if rank:
        Rank(node, rank)


def addhp(node, spaz):
    def showHP():
        hp = spaz.hitpoints
        if spaz.node.exists():
            HitPoint(owner=node, prefix=str(int(hp)),
                     position=(0, 1.75, 0), shad=1.4)
        else:
            spaz.hptimer = None
    spaz.hptimer = bs.Timer(2, babase.Call(
        showHP), repeat=True)


# --- Primary Tag Class with Multi-Style Animation (FIXED) ---

class Tag(object):
    def __init__(self, owner=None, tag="somthing", col=(1, 1, 1), style_id=None):
        self.node = owner
        self.mnodes = []
        self.char_nodes = []
        self.tag_string = tag
        self.current_style = style_id if style_id is not None else 1
        
        if '\\' in tag:
            tag = tag.replace('\\d', ('\ue048'))
            tag = tag.replace('\\c', ('\ue043'))
            tag = tag.replace('\\h', ('\ue049'))
            tag = tag.replace('\\s', ('\ue046'))
            tag = tag.replace('\\n', ('\ue04b'))
            tag = tag.replace('\\f', ('\ue04f'))
            tag = tag.replace('\\g', ('\ue027'))
            tag = tag.replace('\\i', ('\ue03a'))
            tag = tag.replace('\\m', ('\ue04d'))
            tag = tag.replace('\\t', ('\ue01f'))
            tag = tag.replace('\\bs', ('\ue01e'))
            tag = tag.replace('\\j', ('\ue010'))
            tag = tag.replace('\\e', ('\ue045'))
            tag = tag.replace('\\l', ('\ue047'))
            tag = tag.replace('\\a', ('\ue020'))
            tag = tag.replace('\\b', ('\ue00c'))

        self.tag_string_formatted = tag
        self.tag_color_static = col
        
        if sett["enableTagAnimation"]:
            self._setup_char_nodes()
            self.switch_style(style_id=self.current_style) 
        else:
            self._setup_static_node()


    def _setup_char_nodes(self):
        """Creates individual text and math nodes for per-character animation."""
        tag = self.tag_string_formatted
        self.char_scale = 0.015 
        self.char_width = 0.25 
        
        total_width = len(tag) * self.char_width
        start_x = -total_width / 2.0 
        current_x = start_x
        
        for char in tag:
            char_center_x = current_x + self.char_width / 2.0 

            # MATH NODE is owned by self.node to follow the character's torso position
            mnode = bs.newnode('math', owner=self.node,
                               attrs={'input1': (char_center_x, 1.5, 0), 'operation': 'add'})
            self.node.connectattr('torso_position', mnode, 'input2')
            self.mnodes.append(mnode)
            
            # TEXT NODE is NOT owned by self.node and uses is_area_display: True 
            # to prevent physics bugs that cause the player to stick.
            char_text = bs.newnode('text', 
                                   attrs={'text': char, 
                                          'in_world': True, 
                                          'is_area_display': True, 
                                          'shadow': 1.0,
                                          'flatness': 1.0, 
                                          'color': (1, 1, 1), 
                                          'scale': self.char_scale, 
                                          'h_align': 'center'})
            mnode.connectattr('output', char_text, 'position')
            self.char_nodes.append(char_text)
            
            current_x += self.char_width


    def _setup_static_node(self):
        """Creates a single static text node (for non-animated mode)."""
        mnode = bs.newnode('math', owner=self.node,
                           attrs={'input1': (0, 1.5, 0), 'operation': 'add'})
        self.node.connectattr('torso_position', mnode, 'input2')
        self.mnodes.append(mnode)
        
        self.tag_text = bs.newnode('text',
                                   attrs={'text': self.tag_string_formatted, 
                                          'in_world': True,
                                          'is_area_display': True, # CRITICAL FIX
                                          'shadow': 1.0, 
                                          'flatness': 1.0, 
                                          'color': tuple(self.tag_color_static),
                                          'scale': 0.01, 
                                          'h_align': 'center'})
        mnode.connectattr('output', self.tag_text, 'position')
        self.char_nodes.append(self.tag_text)
    

    def switch_style(self, style_id):
        """
        Switches the current tag animation style.
        Style 1: Sea Wave (L -> R)
        Style 2: Fire Wave (R -> L)
        Style 3: Heartbeat (Center -> Edge Pulse)
        """
        if not self.char_nodes:
            return

        self.current_style = style_id
        
        # 1. Stop all current color animations
        for char_node in self.char_nodes:
            # Force stop and reset color
            babase.animate(char_node, 'color', {0: (1.0, 1.0, 1.0)}, repeat=False, end_time=0.0)
            
        tag_length = len(self.char_nodes)
        animation_duration = 1.0
        delay_per_character = 0.05
        
        premium_colors = {
            0.0: (3.0, 0.5, 0.0), # Fiery Orange/Red Glow
            0.2: (2.0, 2.0, 0.0), # Bright Yellow Glow
            0.4: (0.0, 3.0, 3.0), # Aqua/Cyan Glow
            0.6: (1.5, 0.0, 3.0), # Electric Magenta/Purple Glow
            0.8: (0.0, 3.0, 0.0), # Neon Green Glow
            animation_duration: (3.0, 0.5, 0.0) # Loop back
        }

        # --- Style 1: Sea Wave (Left -> Right) ---
        if style_id == 1:
            for i, char_node in enumerate(self.char_nodes):
                start_delay = i * delay_per_character
                bs.animate_array(node=char_node, attr='color', size=3, keys={
                    t + start_delay: color for t, color in premium_colors.items()
                }, loop=True)

        # --- Style 2: Fire Wave (Right -> Left) ---
        elif style_id == 2:
            for i, char_node in enumerate(self.char_nodes):
                reverse_index = tag_length - 1 - i
                start_delay = reverse_index * delay_per_character
                bs.animate_array(node=char_node, attr='color', size=3, keys={
                    t + start_delay: color for t, color in premium_colors.items()
                }, loop=True)

        # --- Style 3: Heartbeat (Center -> Edge Pulse) ---
        elif style_id == 3:
            center_index = (tag_length - 1) / 2.0
            
            for i, char_node in enumerate(self.char_nodes):
                distance_from_center = abs(i - center_index)
                start_delay = distance_from_center * delay_per_character
                
                heartbeat_colors = {
                    0.0: (1.0, 1.0, 1.0), # White
                    0.4: (3.0, 0.0, 0.0), # Bright Red Pulse
                    0.8: (1.0, 1.0, 1.0), # White
                    animation_duration: (1.0, 1.0, 1.0)
                }

                bs.animate_array(node=char_node, attr='color', size=3, keys={
                    t + start_delay: color for t, color in heartbeat_colors.items()
                }, loop=True)


    def animate_death_flow(self):
        """
        Triggers a spectacular color flow and fade-out upon player death.
        Saves the next style ID (logic not shown but implied).
        """
        if not sett["enableTagAnimation"]:
            self.delete_mnodes()
            return
            
        # --- High-Energy Death Flow Colors ---
        death_keys = {
            0.0: (5.0, 5.0, 0.0),   # SUPER Bright Yellow/White Start
            0.05: (5.0, 0.0, 5.0),  # Electric Magenta Flash
            0.10: (0.0, 0.0, 0.0),  # Fade to black (simulates turning off)
            0.20: (5.0, 5.0, 5.0)   # Final, massive white burst
        }
        
        for i, char_node in enumerate(self.char_nodes):
            babase.animate(char_node, 'scale', {0: char_node.scale}, repeat=False) 
            start_delay = i * 0.03 
            
            bs.animate_array(node=char_node, attr='color', size=3, keys={
                t + start_delay: color for t, color in death_keys.items()
            })
            
            bs.Timer(0.3 + start_delay, char_node.delete)
        
        # Delete math nodes after all characters are gone
        bs.Timer(0.3 + len(self.char_nodes) * 0.04, self.delete_mnodes)
        
        # Calculate the next style ID for the player's next spawn
        next_style = (self.current_style % 3) + 1
        
    def delete_mnodes(self):
        """Cleans up the math nodes after the text nodes are gone."""
        for mnode in self.mnodes:
            mnode.delete()


# --- Rank Class (Kept the same) ---

class Rank(object):
    def __init__(self, owner=None, rank=99):
        self.node = owner
        mnode = bs.newnode('math',
                           owner=self.node,
                           attrs={
                               'input1': (0, 1.2, 0),
                               'operation': 'add'
                           })
        self.node.connectattr('torso_position', mnode, 'input2')
        if (rank == 1):
            rank = '\ue01f' + "#" + str(rank) + '\ue01f'
        elif (rank == 2):
            rank = '\ue01f' + "#" + str(rank) + '\ue01f'
        elif (rank == 3):
            rank = '\ue01f' + "#" + str(rank) + '\ue01f'
        else:
            rank = "#" + str(rank)

        self.rank_text = bs.newnode('text',
                                    owner=self.node,
                                    attrs={
                                        'text': rank,
                                        'in_world': True,
                                        'shadow': 1.0,
                                        'flatness': 1.0,
                                        'color': (1, 1, 1),
                                        'scale': 0.01,
                                        'h_align': 'center'
                                    })
        mnode.connectattr('output', self.rank_text, 'position')


# --- HitPoint Class (Kept the same) ---

class HitPoint(object):
    def __init__(self, position=(0, 1.5, 0), owner=None, prefix='0', shad=1.2):
        self.position = position
        self.node = owner
        m = bs.newnode('math', owner=self.node, attrs={
            'input1': self.position, 'operation': 'add'})
        self.node.connectattr('torso_position', m, 'input2')
        prefix = int(prefix) / 10
        preFix = u"\ue047" + str(prefix) + u"\ue047"
        self._Text = bs.newnode('text',
                                owner=self.node,
                                attrs={
                                    'text': preFix,
                                    'in_world': True,
                                    'shadow': shad,
                                    'flatness': 1.0,
                                    'color': (1, 1, 1) if int(
                                        prefix) >= 20 else (1.0, 0.2, 0.2),
                                    'scale': 0.01,
                                    'h_align': 'center'})
        m.connectattr('output', self._Text, 'position')

        def a():
            self._Text.delete()
            m.delete()

        self.timer = bs.Timer(2, babase.Call(
            a))