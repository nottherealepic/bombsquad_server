import _thread

import _babase
import _bascenev1
from stats import mystats

import bascenev1 as bs
from babase._general import Call
from .handlers import send
import datetime
import requests
import json

WEBHOOK_URL = "https://discord.com/api/webhooks/1432260831504236545/PZI2lC89_ndMfiwbdm-255XFJx30G7GeYpMgVqpWCLGJnS9M8jpPZz-KiKxh0y7ryFmq"

Commands = ['me', 'list', 'uniqeid', 'ping']
CommandAliases = ['stats', 'score', 'rank',
                  'myself', 'l', 'id', 'pb-id', 'pb', 'accountid', 'complain']


def ExcelCommand(command, arguments, clientid, accountid):
    """
    Checks The Command And Run Function

    Parameters:
        command : str
        arguments : str
        clientid : int
        accountid : int

    Returns:
        None
    """
    if command in ['me', 'stats', 'score', 'rank', 'myself']:
        fetch_send_stats(accountid, clientid)

    elif command in ['list', 'l']:
        list(clientid)

    elif command in ['uniqeid', 'id', 'pb-id', 'pb', 'accountid']:
        accountid_request(arguments, clientid, accountid)

    elif command in ['ping']:
        get_ping(arguments, clientid)
        
    elif command in ['complain', 'report']:
        send_complaint(arguments, clientid, accountid)
    
    
    
def send_complaint(arguments, clientid, accountid):
    """Handles /complain or /report command from players."""
    message = " ".join(arguments).strip()
    if not message:
        send("Usage: /complain <your message>", clientid)
        return

    # Try to get player name safely
    try:
        import _bascenev1
        session = _bascenev1.get_foreground_host_session()
        player = session.sessionplayers_by_inputdevice_id[clientid]
        player_name = player.getname(full=True)
    except Exception:
        player_name = f"Player {clientid}"

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Confirm to player in chat
    send("✅ Complaint submitted! Admins will review it soon.", clientid)

    # Create embed for Discord
    embed = {
        "title": "🚨 New Complaint",
        "color": 16711680,  # red
        "fields": [
            {"name": "Player", "value": player_name, "inline": False},
            {"name": "Account ID", "value": str(accountid), "inline": False},
            {"name": "Message", "value": message, "inline": False},
            {"name": "Time", "value": timestamp, "inline": False},
        ]
    }

    # Send to Discord webhook
    payload = {"embeds": [embed]}
    headers = {"Content-Type": "application/json"}

    try:
        requests.post(WEBHOOK_URL, headers=headers, data=json.dumps(payload))
        print(f"[ComplaintBot] Complaint sent by {player_name}")
    except Exception as e:
        print(f"[ComplaintBot] Failed to send complaint: {e}")


def get_ping(arguments, clientid):
    if arguments == [] or arguments == ['']:
        send(f"Your ping {_bascenev1.get_client_ping(clientid)}ms ", clientid)
    elif arguments[0] == 'all':
        pingall(clientid)
    else:
        try:
            session = bs.get_foreground_host_session()

            for index, player in enumerate(session.sessionplayers):
                name = player.getname(full=True, icon=False),
                if player.inputdevice.client_id == int(arguments[0]):
                    ping = _bascenev1.get_client_ping(int(arguments[0]))
                    send(f" {name}'s ping {ping}ms", clientid)
        except:
            return


def stats(ac_id, clientid):
    stats = mystats.get_stats_by_id(ac_id)
    if stats:
        reply = "Score:" + str(stats["scores"]) + "\nGames:" + str(
            stats["games"]) + "\nKills:" + str(
            stats["kills"]) + "\nDeaths:" + str(
            stats["deaths"]) + "\nAvg.:" + str(stats["avg_score"])
    else:
        reply = "Not played any match yet."

    _babase.pushcall(Call(send, reply, clientid), from_other_thread=True)


def fetch_send_stats(ac_id, clientid):
    _thread.start_new_thread(stats, (ac_id, clientid,))


def pingall(clientid):
    """Returns The List Of Players Clientid and index"""

    p = u'{0:^16}{1:^34}ms'
    seprator = '\n______________________________\n'

    list = p.format('Name', 'Ping (ms)') + seprator
    session = bs.get_foreground_host_session()

    for index, player in enumerate(session.sessionplayers):
        list += p.format(player.getname(icon=True),
                         _bascenev1.get_client_ping(
                             int(player.inputdevice.client_id))) + "\n"

    send(list, clientid)


def list(clientid):
    """Returns The List Of Players Clientid and index"""

    p = u'{0:^16}{1:^15}{2:^10}'
    seprator = '\n______________________________\n'

    list = p.format('Name', 'Client ID', 'Player ID') + seprator
    session = bs.get_foreground_host_session()

    for index, player in enumerate(session.sessionplayers):
        list += p.format(player.getname(icon=False),
                         player.inputdevice.client_id, index) + "\n"

    send(list, clientid)


def accountid_request(arguments, clientid, accountid):
    """Returns The Account Id Of Players"""

    if arguments == [] or arguments == ['']:
        send(f"Your account id is {accountid} ", clientid)

    else:
        try:
            session = bs.get_foreground_host_session()
            player = session.sessionplayers[int(arguments[0])]

            name = player.getname(full=True, icon=True)
            accountid = player.get_v1_account_id()

            send(f" {name}'s account id is '{accountid}' ", clientid)
        except:
            return
