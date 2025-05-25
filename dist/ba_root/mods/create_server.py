# ba_meta require api 9
"""Functionality related to teams mode score screen."""
from __future__ import annotations
import threading

import _bascenev1
import bascenev1
import yaml
import requests
import os
import tomllib
from bascenev1 import DEFAULT_TEAM_NAMES, DEFAULT_TEAM_COLORS, Session
from tools.file_handle import OpenJson


from typing import TYPE_CHECKING, Sequence
import setting

import babase
import bascenev1 as bs
from bascenev1lib.actor.text import Text
from bascenev1._activity import Activity
if TYPE_CHECKING:
    from typing import Optional
from bascenev1._player import EmptyPlayer  # pylint: disable=W0611
from bascenev1._team import EmptyTeam  # pylint: disable=W0611
import _babase
from babase._general import Call
import _thread
import time
import urllib.request
import json
import custom_hooks
from plugins import bombsquad_service
from playersdata import pdata
API = "https://bcs.ballistica.workers.dev"
current_settings = setting.get_settings_data()
DEFAULT_DATA_PATH = os.path.join(
    _babase.env()["python_directory_user"], "defaults" + os.sep
)
SETTINGS_PATH = _babase.env().get("python_directory_user", "") + "/setting.json"
PLAYERS_DATA_PATH = os.path.join(
    _babase.env()["python_directory_user"], "playersdata" + os.sep
)

ip = "unknown"


class CreateServerActivity(Activity[EmptyPlayer, EmptyTeam]):
    """Base class for score screens."""

    def __init__(self, settings: dict):
        super().__init__(settings=settings)
        self._score_display_sound = bs.getsound('scoreHit01')
        self._score_display_sound_small = bs.getsound('scoreHit02')

        self._show_up_next: bool = True
        self._background: Optional[bs.Actor] = None

    def on_transition_in(self) -> None:
        # pylint: disable=cyclic-import
        # FIXME: Don't use bascenev1lib from babase.
        from bascenev1lib.actor import background
        super().on_transition_in()
        self._background = background.Background(fade_time=0.5,
                                                 start_faded=False,
                                                 show_logo=False)

    def on_begin(self) -> None:
        super().on_begin()
        session = self.session
        if self._show_up_next and isinstance(session, bs.MultiTeamSession):
            txt = "create free server now"
            Text(txt,
                 maxwidth=900,
                 h_attach=Text.HAttach.CENTER,
                 v_attach=Text.VAttach.BOTTOM,
                 h_align=Text.HAlign.CENTER,
                 v_align=Text.VAlign.CENTER,
                 position=(0, 53),
                 flash=False,
                 color=(0.3, 0.3, 0.35, 1.0),
                 transition=Text.Transition.FADE_IN,
                 transition_delay=2.0).autoretain()
        # self.add_instructions()
        # self.add_variables_placeholders()
        self.add_credits()
        self.add_promotion()

    def add_promotion(self):
        self.heading = bs.newnode('text', attrs={'text': "CREATE FREE SERVER",
                                                 'position': (0, -90),
                                                 'h_align': 'center',
                                                 'v_attach': 'top',
                                                 'h_attach': 'center',
                                                 'scale': 2

                                                 })
        self.h = bs.newnode('text', attrs={'text': "Youtube : Hey Smoothy \nDiscord : https://discord.gg/ucyaesh\nWeb : https://bombsquad-community.web.app",
                                           'position': (-520, -100),
                                           'color': (0.7, 0.6, 0.5),
                                           'h_attach': 'right'
                                           })
        self.start_h = bs.newnode('text', attrs={'text': "Type passcode to start your server \ngenerate your passcode from discord server",
                                                 'position': (0, -220),
                                                 'scale': 1.3,
                                                 'color': (0.3, 0.7, 0.4),
                                                 'h_align': 'center',
                                                 'v_attach': 'top',
                                                 'h_attach': 'center',
                                                 })
        self.ipport = bs.newnode('text', attrs={'text': "IP:"+ip+" PORT:"+str(bs.get_game_port()),
                                                'position': (0, -160),
                                                'scale': 1,
                                                'color': (0.7, 0.7, 0.4),
                                                'h_align': 'center',
                                                'v_attach': 'top',
                                                'h_attach': 'center',
                                                })

    def add_credits(self):
        self.h = bs.newnode('text', attrs={'text': "By : BCS Community",
                                           'position': (80, -200),

                                           'h_attach': 'left'
                                           })
        self.NAMES = bs.newnode('text', attrs={'text': "Contributors : Mr.Smoothy, Rikko,  Doffy, Snowee, Freaku, NK2, \n "
                                                       +"Vishuu, Loupie, brostos , Brother board and more ..",
                                               'position': (80, -240),

                                               'h_attach': 'left'
                                               })
        self.note = bs.newnode('text', attrs={'text': "*Note: Server will restart after configuration, rejoin back.",
                                              'position': (80, -320),

                                              'h_attach': 'left'
                                              })

    def add_instructions(self):

        self.server_name_heading = bs.newnode('text', attrs={'text': "Party Name:",
                                                             'position': (80, 180),
                                                             'color': (1, 0.4, 0.4),
                                                             'h_attach': 'left'
                                                             })
        self.server_name_instructions = bs.newnode('text', attrs={'text': "eg: /setname pro boxing FFA",
                                                                  'position': (80, 150),
                                                                  'color': (1, 1, 0),
                                                                  'h_attach': 'left'
                                                                  })
        self.playlist_heading = bs.newnode('text', attrs={'text': "Playlist:",
                                                          'position': (80, 80),
                                                          'color': (1, 0.4, 0.4),
                                                          'h_attach': 'left'
                                                          })
        self.playlist_instructions = bs.newnode('text', attrs={'text': "eg: /setplaylist 34234",
                                                               'position': (80, 50),
                                                               'color': (1, 1, 0),
                                                               'h_attach': 'left'
                                                               })
        self.size_heading = bs.newnode('text', attrs={'text': "Party Size:",
                                                      'position': (80, -20),
                                                      'color': (1, 0.4, 0.4),
                                                      'h_attach': 'left'
                                                      })
        self.size_instructions = bs.newnode('text', attrs={'text': "eg: /setsize 8",
                                                           'position': (80, -50),
                                                           'color': (1, 1, 0),
                                                           'h_attach': 'left'
                                                           })

    def add_variables_placeholders(self):
        self.server_name = bs.newnode('text', attrs={'text': "pro boxing FFA",
                                                     'position': (250, 180),
                                                     'color': (0.4, 1, 0.4),
                                                     'h_attach': 'left'
                                                     })
        self.playlist_code = bs.newnode('text', attrs={'text': "12345",
                                                       'position': (250, 80),
                                                       'color': (0.4, 1, 0.4),
                                                       'h_attach': 'left'
                                                       })
        self.part_size = bs.newnode('text', attrs={'text': "8",
                                                   'position': (250, -20),
                                                   'color': (0.4, 1, 0.4),
                                                   'h_attach': 'left'
                                                   })

    def show_player_scores(self,
                           delay: float = 2.5,
                           results: Optional[bs.GameResults] = None,
                           scale: float = 1.0,
                           x_offset: float = 0.0,
                           y_offset: float = 0.0) -> None:
        """Show scores for individual players."""
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-statements

        pass


#  =============    session ======================


class createServerSession(Session):
    def __init__(self) -> None:
        """Set up playlists and launches a babase.Activity to accept joiners."""
        # pylint: disable=cyclic-import

        app = _babase.app
        cfg = app.config

        if self.use_teams:
            team_names = cfg.get('Custom Team Names', DEFAULT_TEAM_NAMES)
            team_colors = cfg.get('Custom Team Colors', DEFAULT_TEAM_COLORS)
        else:
            team_names = None
            team_colors = None

        # print('FIXME: TEAM BASE SESSION WOULD CALC DEPS.')
        depsets: Sequence[bascenev1.DependencySet] = []

        super().__init__(depsets,
                         team_names=team_names,
                         team_colors=team_colors,
                         min_players=1,
                         max_players=self.get_max_players())

        self.setactivity(bs.newactivity(CreateServerActivity))

    def on_player_request(self, player: bs.SessionPlayer):

        return False

    def get_max_players(self) -> int:
        return 3


def update_ip():
    global ip
    try:
        r = urllib.request.urlopen("https://api.ipify.org/?format=json")
        ip = json.loads(r.read())["ip"]
    except:
        pass
    try:
        req = urllib.request.Request(
            f'{API}/serveravailable')
        req.add_header('servername', ip+":"+str(bs.get_game_port()))
        f = urllib.request.urlopen(req, data=urllib.parse.urlencode({
                                   "nothing": "nothing"}).encode())
    except:
        pass


def validate(display_string, pbid, passcode):
    try:
        req = urllib.request.Request(
            f'{API}/verifypasscode')
        req.add_header('passcode', passcode)
        # req.add_header('servername', str(server_name_v.encode('utf-8'))+f' {ip} {str(bs.get_game_port())}')
        # req.add_header("playerid", str(owner["name"].encode('utf-8'))+" -  "+ owner["id"])
        print("sending request to master server with passcode "+passcode)
        f = requests.post(f'{API}/verifypasscode', json={
            "servername": f'{display_string} {ip} {str(bs.get_game_port())}',
            "playerid": pbid,
        }, headers={'passcode': passcode})

        rescode = f.status_code
        if rescode == 200:
            json_response = f.json()
            return json_response["password"]
        return None
    except Exception as e:
        print(e)
        return None


def get_server_api():
    try:
        print("making request to get api")
        f = requests.post(f'{API}/getapi', json={
            "address": f'{ip}:{str(bs.get_game_port())}',
        })
        if f.status_code == 200:
            api_link = f.text
            return f'https://imayushsaini.github.io/ballistica-ui/?api={api_link}'
        else:
            return 'https://discord.gg/ucyaesh'
    except Exception as e:
        print(e)
        return 'https://discord.gg/ucyaesh'


def reset_server():
    bs.set_public_party_max_size(3)
    _bascenev1.set_public_party_name("CREATE FREE SERVER")
    _bascenev1.set_public_party_stats_url('https://discord.gg/ucyaesh')
    update_ip()
    babase.pushcall(Call(bs.new_host_session, createServerSession))
    resetProfiles()


def resetProfiles():
    # clear cache , update files , load files
    pdata.CacheData.custom = {}
    pdata.CacheData.roles = {}
    pdata.CacheData.blacklist = {}
    pdata.CacheData.profiles = {}
    print("starting profiles reset")
    with OpenJson(PLAYERS_DATA_PATH + "profiles.json") as profiles_file:
        profiles_file.dump(profiles, indent=4)
        pdata.get_profiles()
    with OpenJson(PLAYERS_DATA_PATH + "custom.json") as custom_file:
        custom_file.dump(custom, indent=4)
        pdata.get_custom()
    with OpenJson(PLAYERS_DATA_PATH + "roles.json") as roles_file:
        roles_file.dump(roles, indent=4)
        pdata.get_roles()
    with OpenJson(PLAYERS_DATA_PATH + "blacklist.json") as roles_file:
        roles_file.dump(blacklist, indent=4)
        pdata.get_blacklist()
    with OpenJson(SETTINGS_PATH) as settings_file:
        settings_file.dump(default_settings, indent=4)
    print("SERVER reset done")


def start(display_string, pbid, passcode):
    print("lets start")
    password = validate(display_string, pbid, passcode)

    if not password:
        bs.chatmessage("Invalid passcode , or passcode expired")
        bs.chatmessage('get new passcode from discord server')
        return
    else:
        print("got password"+password)
    server_name = f'{display_string} \'s Server'

    bs.get_foreground_host_session().end()

    # _thread.start_new_thread(withDelay, (DualTeamSession,))
    _bascenev1.set_admins(pbid)

    bs.chatmessage("Your server is nearly ready")
    bs.chatmessage(f"Server Name: {display_string}'s Server")
    bs.chatmessage("IP:"+ip + " PORT:"+str(bs.get_game_port()))
    bs.chatmessage("configuring your server.....")
    bs.chatmessage(
        "server will restart after configuration, hold on and join back")
    print("get server ready ...............")
    _thread.start_new_thread(get_server_ready, (password, server_name, pbid,))


def get_server_ready(password, server_name, owner_id):
    save_new_password(password)
    pdata.CacheData.roles["owner"]["ids"].append(owner_id)
    with OpenJson(PLAYERS_DATA_PATH + "roles.json") as roles_file:
        roles_file.dump(pdata.CacheData.roles, indent=4)
    print(" player role cache dumped")
    # update server name at last , as it will restart server.
    server_config = default_config
    server_config["party_name"] = server_name
    # stats_url = get_server_api()
    # server_config['stats_url'] = stats_url  custom_hooks will add stats url is we service enabled
    bombsquad_service.update_server_config(server_config)


def save_new_password(password: str):
    current_settings["ballistica_web"]["server_password"] = password
    bombsquad_service.update_server_settings(current_settings)
    print("new server password saved in settings")


def exit_server():
    bs.chatmessage("Time Up , create new server  ")
    bs.chatmessage("Join discord , https://discord.gg/ucyaesh")
    _babase.quit()


org_filter_chat = custom_hooks.filter_chat_message


def newFilterChat(msg, clientid):
    chat_parse(msg, clientid)
    return org_filter_chat(msg, clientid)


custom_hooks.filter_chat_message = newFilterChat


def chat_parse(msg: str, client_id):
    if bs.get_foreground_host_activity().__class__.__name__ == "CreateServerActivity":
        act = bs.get_foreground_host_activity()
        if msg.isdigit():
            for ros in bs.get_game_roster():
                if ros['client_id'] == client_id:
                    display_string = ros['display_string']
                    account_id = ros["account_id"]
                    start(display_string, account_id, msg.strip())
        else:
            print("message is not a valid digit"+str(msg))


#  mgr.cmd("import _babase,ba;from createServer import createServerSession;bs.new_host_session(createServerSession)")
# babase._servermanager me createServer.reset_server()
# settings.json
# disable /ban command
# reset complete profiles.json / and other json
# increase server exit time to 160
# disable ideal kick
roles = {}
custom = {}
profiles = {}
blacklist = {}
default_settings = {}
default_config = {}


def load_defaults():
    global roles
    global custom
    global profiles
    global blacklist
    global default_settings
    global default_config
    print("loading default configuration")
    with open(DEFAULT_DATA_PATH + "profiles.json", "r") as f:
        profiles = json.load(f)
    with open(DEFAULT_DATA_PATH + "roles.json", "r") as f:
        roles = json.load(f)
    with open(DEFAULT_DATA_PATH + "blacklist.json", "r") as f:
        blacklist = json.load(f)
    with open(DEFAULT_DATA_PATH + "custom.json", "r") as f:
        custom = json.load(f)
    with open(DEFAULT_DATA_PATH + "settings.json", "r") as f:
        default_settings = json.load(f)
    with open(DEFAULT_DATA_PATH + "config.toml", "rb") as f:
        default_config = tomllib.load(f)


# ba_meta export plugin
class EntryPoint(babase.Plugin):

    def on_app_running(self) -> None:
        self.t0 = bs.AppTimer(30, babase.Call(self.check_remaining_time))
        self.t1 = bs.AppTimer(60 * 30, babase.Call(self.check_remaining_time),
                           repeat=True)

    def get_remaining_time(self, server_key: str, callback):
        try:
            print("making request to get passcode")
            f = requests.post(f'{API}/getpasscode', json={
                "token": server_key,
            })
            if f.status_code == 200:
                json_response = f.json()
                print(json_response)
                callback(json_response["minutesLeft"])
            elif f.status_code == 403:
                print("got 403 response means 0")
                callback(0)
            else:
                print("fallback to 60")
                callback(60)
        except Exception as e:
            print(e)
            callback(60)

    def on_response(self, duration: float):
        print(duration)
        if duration <= 0:
            print("duration less then 0, resetting server")
            load_defaults()  # multithread me please
            print("load default done")
            time.sleep(4)
            babase.pushcall(
                babase.Call(
                    reset_server
                ),
                from_other_thread=True,
            )

    def check_remaining_time(self):
        if bs.get_foreground_host_activity().__class__.__name__ != "CreateServerActivity":
            t = threading.Thread(target=self.get_remaining_time, args=(
                current_settings["ballistica_web"]["server_password"], self.on_response))
            t.start()
