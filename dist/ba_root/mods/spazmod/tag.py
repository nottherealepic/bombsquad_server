import setting
from playersdata import pdata
from stats import mystats

import babase
import bascenev1 as bs

sett = setting.get_settings_data()


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


class Tag(object):
    def __init__(self, owner=None, tag="somthing", col=(1, 1, 1)):
        self.node = owner

        mnode = bs.newnode('math',
                           owner=self.node,
                           attrs={
                               'input1': (0, 1.5, 0),
                               'operation': 'add'
                           })
        self.node.connectattr('torso_position', mnode, 'input2')
        
        # Icon replacement logic
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
        
        # --- HIGH-ENERGY WAVE SIMULATION ANIMATION START ---
        # A 2.0 second cycle with 9 keyframes to create complex, dazzling color transitions.
        # High-value colors (>1.0) provide the bright, glowing 'premium' look.
        if sett["enableTagAnimation"]:
            bs.animate_array(node=self.tag_text, attr='color', size=3, keys={
                0.0: (2.0, 0.5, 1.5),  # Deep Pink/Red (Wave Start)
                0.2: (0.5, 2.0, 2.0),  # Bright Cyan/Aqua (Wave Crest)
                0.4: (2.0, 2.0, 0.5),  # Bright Yellow/Gold (Sunlight on Wave)
                0.6: (0.5, 1.5, 0.5),  # Green/Lime (Randomized Color)
                0.8: (2.0, 0.0, 0.0),  # Strong Red (Burst Effect)
                1.1: (1.0, 1.0, 2.0),  # Light Blue/White (Wave Foam)
                1.4: (2.0, 1.5, 0.0),  # Bright Orange/Gold (Sunset Color)
                1.7: (0.0, 2.0, 0.0),  # Vibrant Green
                2.0: (2.0, 0.5, 1.5)   # Loop back to Deep Pink/Red
            }, loop=True)
        # --- HIGH-ENERGY WAVE SIMULATION ANIMATION END ---


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