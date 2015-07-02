# TPPRB MusicCat Song Library v2.0

from __future__ import print_function
import os, random, datetime
import difflib
import winamp
from pymongo import MongoClient
try:
    from builtins import input
except: # Temporary hack until the builtins future module is properly installed
    input = raw_input

"""
Expected db formats:

pbr_songs:
    {id, path, title, types:[]}
pbr_ratings:
    {username, songid, rating}
pbr_songqueue:
    single {username, songid, tokens}

"""

class MusicCat(object):
    _categories = ["battle", "betting", "result", "warning"]
    _winamppath = "C:/Program Files (x86)/Winamp/winamp.exe" #put your path to winamp.exe here
    _time_before_replay = datetime.time(hour=6) # 6 hours
    #musicpath = "D:/Projects/TPPRB Music/"
    #metafile = "metadata.yaml"
    def __init__(self, mongo_uri):
        self.client = MongoClient(mongo_uri)
        self.songdb = self.client.song_database
        self.songs = self.songdb["pbr_songs"]
        self.song_ratings = self.songdb["pbr_ratings"]
        self.queue = self.songdb["pbr_songqueue"] # Bidding queue
        
        self.next_category = None       # Upcoming category of music allowed to play.
        self.current_category = None    # currently running category
        
        # Initialize WinAmp and insert addl. function
        def _play_solo_file(self, playcommand):
            """playcommand is a list of the executable and song file argument"""
            self.stop()
            self.clearPlaylist()
            p = subprocess.Popen(" ".join(playcommand))
            #time.sleep(10)
            #p.terminate() # Kill it after 5 seconds
        winamp.Winamp.playSoloFile = _play_solo_file
        self.winampplayer = winamp.Winamp()
        
        """
        for k_system in mdata["systems"]:
            system = mdata["systems"][k_system]
            for k_game in system["games"]:
                game = system["games"][k_game]
                self.games[k_game] = game
                #
                for k_song in game["songs"]:
                    self.songs[k_song] = game["songs"][k_song]
                    self.songs[k_song]["system"] = k_system
                    self.songs[k_song]["game"] = k_game
                    self.songs[k_song]["fullpath"] = os.path.join(system["path"], game["path"], self.songs[k_song]["path"])
                """
    
    def quote(s):
        return '"' + s + '"'

    def play_next_song(self, category):
        queued = self.queue.find_one()
        if queued and category in queued["song"]["types"]:
            nextsong = queued["song"]
            # Charge the user their bid
            #bankbot.charge(queued["username"], queued["tokens"])
        else:
            nextsong = get_random(self, category)
        # Update lastplayed timestamp
        nextsong["lastplayed"] = datetime.now()
        self.songs.find_one_and_update({"id":nextsong["id"]}, nextsong)
        
        # And start the song.
        self.winampplayer.playSoloFile([quote(winamppath), quote(nextsong["fullpath"])])
        return nextsong # Return the song for display purposes
    
    def get_random(self, category):
        """Returns song info by random, inside a category
        Must be after replay timelimit"""
        song_category = self.songs.find({"type": {"$in":category}, "lastplayed": {"$lt":datetime.now() - _time_before_replay}})
        return random.choice(song_category)
    
    def get_song_info(self, songid):
        """Fuzzy-match songid to either song id, or full id (game-song)
           Return the song dict of its info, and the songid that matches, in case it was a fuzzy match
        """
        # Try exact match
        song = self.songs.find_one({"id":songid})
        # Try fuzzy match
        if song == None:
            difflib.get_close_matches(songid, self.songs.find())
        
        return songid, song
    
    
    def get_song_path(self, system, game_id, song_id):
        try:
            system = self.mdata["systems"][system]
            game = system["games"][game_id]
            song = game["songs"][song_id]
            return os.path.join(system["path"], game["path"], song["path"])
        except: return ""
    
    def set_next_category(self, category):
        self.next_category = category
    
    def bid(self, user, songid, tokens):
        songid, song = self.get_song_info(songid)
        current_bid = self.queue.find_one()
        if current_bid == None:
            self._set_bid(user, song, tokens)
        elif user.username == current_bid["username"]:
            raise InvalidUser("Same bidder can't outbid themselves")
        elif tokens > current_bid["tokens"]:
            if self.next_category not in song["types"]:
                raise InvalidCategory("{0} is not in the {1} category!".format(song["title"], self.current_category))
            else:
                self.queue.delete_one()
                self._set_bid(user, song, tokens)
    
    def _set_bid(self, user, song, tokens):
        self.queue.insert_one({"username": user.username, "song":songid, "tokens": tokens})
    
    def rate(self, user, songid, rating):
        #TODO: check songid and rating
        self.song_ratings.find_one_and_update({"username": user.username, "songid": songid}, {"username": user.username, "songid": songid, "rating": rating}, upsert=True)
    

if __name__ == "__main__":
    library = MusicCat("mongodb://abylls-server:27017")
    while True:
        category = input("Enter category: ")
        fullid = input("Enter full ID for a song: ")
        print(library.get_song_info(fullid))