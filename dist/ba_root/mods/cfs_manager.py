# ba_meta require api 9
import babase
import bascenev1 as bs
import json
import os
import time

# --- CONFIG ---
MY_PORT = 43211 
DATA_FILE = f"/home/ubuntu/cfs_data/server_{MY_PORT}.json"
LOBBY_PLAYLIST = "Divine_Lobby"   
GAME_PLAYLIST = "Team Deathmatch" 

class CFSManager:
    def __init__(self):
        self.status = "IDLE"
        self.owner_id = None
        self.last_force_start = 0
        
        # Check file every 2 seconds
        babase.AppTimer(2.0, self.loop_logic, repeat=True)

    def loop_logic(self):
        # 1. CHECK IF WE NEED TO FORCE START THE UI
        # If we are in IDLE mode, we want the Divine UI running, NOT the default Lobby.
        if self.status == "IDLE":
            self.ensure_lobby_running()

        # 2. CHECK JSON FILE FOR UPDATES
        if not os.path.exists(DATA_FILE):
            return

        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)

            if data.get('status') == 'ACTIVE' and self.status == 'IDLE':
                self.deploy(data)
            elif data.get('status') == 'IDLE' and self.status == 'ACTIVE':
                self.reset()
        except Exception as e:
            print(f"CFS Error: {e}")

    def ensure_lobby_running(self):
        # This function checks if the server is stuck in the "Waiting for players" screen
        session = bs.get_foreground_host_session()
        
        # We check if the current activity is a LOBBY (the team selection screen)
        # If it is, we force end it so the Divine UI starts.
        # We also check time to prevent spamming commands
        current_time = time.time()
        if current_time - self.last_force_start < 5.0:
            return

        # NOTE: This accesses internal session data to find the Lobby
        # In API 9, the gathering activity is usually handled by the session.
        # If the session exists but we aren't in our Divine Game yet:
        activity = babase.app.foreground_activity
        
        # If the current activity name is NOT our UI, push it forward
        if activity and activity.name != 'Divine Lobby UI':
            print("Force starting Divine UI...")
            try:
                # Set the playlist to ensure we load the right thing
                babase.app.server_self.set_playlist(LOBBY_PLAYLIST)
                
                # If we are in a session, try to end the current activity (Lobby)
                if session:
                    # This forces the "Gathering" phase to end immediately
                    session.end() 
            except:
                pass
            self.last_force_start = current_time

    def deploy(self, data):
        self.status = "ACTIVE"
        self.owner_id = data['owner_id']
        new_name = data['server_name']

        bs.broadcastmessage(f"✅ Server Deployed: {new_name}", color=(0,1,0))
        bs.internal.set_server_name(new_name)
        
        cfg = babase.app.config
        cfg['Admins'] = [self.owner_id]
        cfg.commit()

        # Switch to Game Playlist
        babase.app.server_self.set_playlist(GAME_PLAYLIST)
        if bs.get_foreground_host_session():
            bs.get_foreground_host_session().end()

        babase.AppTimer(3600, self.expire_session)

    def expire_session(self):
        bs.broadcastmessage("Time Limit Reached!", color=(1,0,0))
        self.update_json_status("IDLE")
        self.reset()

    def reset(self):
        self.status = "IDLE"
        bs.internal.set_server_name("👑 Create Free Server by Divine")
        
        cfg = babase.app.config
        cfg['Admins'] = []
        cfg.commit()
        
        session = bs.get_foreground_host_session()
        if session:
            for player in session.sessionplayers:
                player.remove_from_game()

        # Force Playlist back to Lobby
        babase.app.server_self.set_playlist(LOBBY_PLAYLIST)
        if bs.get_foreground_host_session():
            bs.get_foreground_host_session().end()

    def update_json_status(self, status):
        data = {"status": status, "port": MY_PORT}
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f)

CFSManager()