import setting
from playersdata import pdata
from stats import mystats

import babase
import bascenev1 as bs

# --- Initialize Settings ---
# Assumes these modules are available in the game environment
sett = setting.get_settings_data()


# --- Utility Functions ---

def addtag(node, player):
    session_player = player.sessionplayer
    account_id = session_player.get_v1_account_id()
    customtag_ = pdata.get_custom()
    customtag = customtag_['customtag']
    roles = pdata.get_roles()
    p_roles = pdata.get_player_roles(account_id)
    tag = None
    col = (0.5, 0.5, 1)  # default color for custom tags
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
        # Pass the created tag instance back to the caller (e.g., the Spaz class)
        # to allow calling tag.animate_death_flow() later.
        Tag(node, tag, col)


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


# --- Primary Tag Class with Per-Character Animation ---

class Tag(object):
    def __init__(self, owner=None, tag="somthing", col=(1, 1, 1)):
        self.node = owner
        self.mnodes = []
        self.char_nodes = []
        
        # Icon replacement logic (applied to the whole string)
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

        if sett["enableTagAnimation"]:
            # --- TRUE LEFT-TO-RIGHT GRADIENT ANIMATION ---
            
            # CRITICAL SPACING FIX: These values ensure letters are spaced correctly.
            char_scale = 0.015 
            char_width = 0.5
            
            total_width = len(tag) * char_width
            start_x = -total_width / 2.0  # X position of the left edge of the first char
            
            current_x = start_x
            animation_duration = 1.2  
            delay_per_character = 0.05  
            
            for i, char in enumerate(tag):
                # Calculate the center position for this character
                char_center_x = current_x + char_width / 2.0 

                # 1. Create a math node for this character's unique position
                mnode = bs.newnode('math',
                                   owner=self.node,
                                   attrs={
                                       'input1': (char_center_x, 1.5, 0),
                                       'operation': 'add'
                                   })
                self.node.connectattr('torso_position', mnode, 'input2')
                self.mnodes.append(mnode)
                
                # 2. Create the text node for this single character
                char_text = bs.newnode('text',
                                       owner=self.node,
                                       attrs={
                                           'text': char,
                                           'in_world': True,
                                           'shadow': 1.0,
                                           'flatness': 1.0,
                                           'color': (1, 1, 1), 
                                           'scale': char_scale,
                                           'h_align': 'center' 
                                       })
                mnode.connectattr('output', char_text, 'position')
                self.char_nodes.append(char_text)
                
                # 3. Apply the delayed, multi-color wave animation
                start_delay = i * delay_per_character
                
                bs.animate_array(node=char_text, attr='color', size=3, keys={
                    start_delay + 0.0: (2.0, 0.0, 2.0),   # Purple
                    start_delay + 0.2: (0.0, 2.0, 2.0),   # Cyan
                    start_delay + 0.4: (2.0, 2.0, 0.0),   # Yellow/Gold
                    start_delay + 0.6: (2.0, 0.5, 0.5),   # Red
                    start_delay + 0.8: (0.5, 2.0, 0.5),   # Green
                    start_delay + animation_duration: (2.0, 0.0, 2.0)    # Loop back
                }, loop=True)
                
                # 4. Update X position for the next character
                current_x += char_width
            
        else:
            # --- Non-Animated fallback (Original single-node logic) ---
            mnode = bs.newnode('math',
                               owner=self.node,
                               attrs={
                                   'input1': (0, 1.5, 0),
                                   'operation': 'add'
                               })
            self.node.connectattr('torso_position', mnode, 'input2')
            self.mnodes.append(mnode)
            
            self.tag_text = bs.newnode('text',
                                       owner=self.node,
                                       attrs={
                                           'text': tag,
                                           'in_world': True,
                                           'shadow': 1.0,
                                           'flatness': 1.0,
                                           'color': tuple(col),
                                           'scale': 0.01,
                                           'h_align': 'center'
                                       })
            mnode.connectattr('output', self.tag_text, 'position')
            self.char_nodes.append(self.tag_text)

    def animate_death_flow(self):
        """
        Triggers a new, cool, fast color flow and fade-out upon player death.
        This function should be called from the player's Spaz class when it receives a DieMessage.
        """
        if not sett["enableTagAnimation"]:
            # If animation is disabled, just delete the tag immediately
            self.delete_mnodes()
            return
            
        # Animation Keys: Fast cycle with a fade to black/transparent
        death_keys = {
            0.0: (2.0, 2.0, 0.0),   # Yellow
            0.05: (2.0, 0.0, 2.0),  # Magenta flash
            0.10: (0.0, 0.0, 0.0),  # Fade to black (simulates turning off)
            0.20: (2.0, 2.0, 2.0)   # Final white burst
        }
        
        # Apply the death animation to each character with a sequential delay
        for i, char_node in enumerate(self.char_nodes):
            # Stop any current animation loop
            # Note: babase.animate is used here just to cancel the array animation
            babase.animate(char_node, 'scale', {0: char_node.scale}, repeat=False) 
            
            start_delay = i * 0.04 
            
            # Apply the color flow animation
            bs.animate_array(node=char_node, attr='color', size=3, keys={
                t + start_delay: color for t, color in death_keys.items()
            })
            
            # Set a final deletion timer to remove the node after the animation finishes
            bs.Timer(0.3 + start_delay, char_node.delete)
        
        # Delete all associated math nodes after the last character's delay
        bs.Timer(0.3 + len(self.char_nodes) * 0.04, self.delete_mnodes)
        
    def delete_mnodes(self):
        """Cleans up the math nodes after the text nodes are gone."""
        for mnode in self.mnodes:
            mnode.delete()


# --- Rank Class ---

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


# --- HitPoint Class ---

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