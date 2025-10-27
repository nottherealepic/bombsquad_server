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
    def __init__(self, owner=None, tag="SOMETHING", col=(1, 1, 1)):
        self.node = owner

        # Position node slightly above the player's head
        mnode = bs.newnode(
            'math',
            owner=self.node,
            attrs={'input1': (0, 1.6, 0), 'operation': 'add'}
        )
        self.node.connectattr('torso_position', mnode, 'input2')

        # Replace special icons in tag
        replacements = {
            '\\d': '\ue048', '\\c': '\ue043', '\\h': '\ue049', '\\s': '\ue046',
            '\\n': '\ue04b', '\\f': '\ue04f', '\\g': '\ue027', '\\i': '\ue03a',
            '\\m': '\ue04d', '\\t': '\ue01f', '\\bs': '\ue01e', '\\j': '\ue010',
            '\\e': '\ue045', '\\l': '\ue047', '\\a': '\ue020', '\\b': '\ue00c'
        }
        for k, v in replacements.items():
            tag = tag.replace(k, v)

        # Main visible text (the actual tag)
        self.tag_text = bs.newnode(
            'text',
            owner=self.node,
            attrs={
                'text': tag,
                'in_world': True,
                'shadow': 1.2,
                'flatness': 0.7,
                'color': tuple(col),
                'scale': 0.013,
                'h_align': 'center'
            }
        )

        # Soft glow layer for smooth light effect
        self.glow = bs.newnode(
            'text',
            owner=self.node,
            attrs={
                'text': tag,
                'in_world': True,
                'shadow': 0.0,
                'flatness': 1.0,
                'color': (col[0]*0.5, col[1]*0.5, col[2]*0.5),
                'scale': 0.017,
                'opacity': 0.4,
                'h_align': 'center'
            }
        )

        # Attach both layers to position math node
        mnode.connectattr('output', self.tag_text, 'position')
        mnode.connectattr('output', self.glow, 'position')

        # === ✨ Animation Magic ===
        if sett.get("enableTagAnimation", True):
            # Floating (up-down wave motion)
            float_anim = bs.newnode('math', owner=self.node, attrs={
                'input1': (0, 0.1, 0),  # small vertical amplitude
                'operation': 'add'
            })
            self.node.connectattr('torso_position', float_anim, 'input2')

            # Animate Y offset (sinusoidal float)
            bs.animate_array(
                node=float_anim,
                attr='input1',
                size=3,
                keys={
                    0.0: (0, 0.10, 0),
                    0.5: (0, 0.15, 0),
                    1.0: (0, 0.10, 0),
                    1.5: (0, 0.05, 0),
                    2.0: (0, 0.10, 0)
                },
                loop=True
            )

            float_anim.connectattr('output', self.tag_text, 'position')
            float_anim.connectattr('output', self.glow, 'position')

            # Wave / moving-light color animation
            bs.animate_array(
                node=self.tag_text,
                attr='color',
                size=3,
                keys={
                    0.0: (1.5, 0.3, 0.3),
                    0.5: (0.3, 1.3, 0.3),
                    1.0: (0.3, 0.3, 1.5),
                    1.5: (1.3, 1.3, 0.3),
                    2.0: (1.5, 0.3, 1.5),
                    2.5: tuple(col)
                },
                loop=True
            )

            # Glow intensity pulsing
            bs.animate(
                self.glow,
                'opacity',
                {0.0: 0.2, 0.6: 0.8, 1.2: 0.2},
                loop=True
            )


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
