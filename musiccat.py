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
    _winamppath = "C:/Program Files (x86)/Winamp/winamp.exe"
    _mongo_uri = "mongodb://abylls-server:27017"
    _time_before_replay = datetime.time(hour=6)
    def __init__(self):
        self.client = MongoClient(_mongo_uri)
        self.songdb = self.client.song_database
        self.songs = self.songdb["pbr_songs"]
        self.song_ratings = self.songdb["pbr_ratings"]
        self.queue = self.songdb["pbr_songqueue"] # Bidding queue
        
        self.next_category = None       # Upcoming category of music allowed to play.
        self.current_category = None    # currently running category
        
        # Initialize WinAmp and insert addl. function
        def _playSoloFile(self, songfile):
            """ Runs Winamp to play given song file"""
            self.stop()
            self.clearPlaylist()
            p = subprocess.Popen('"{0}" "{1}"'.format(_winamppath, songfile))
        winamp.Winamp.playSoloFile = _play_solo_file
        self.winampplayer = winamp.Winamp()
        

    def play_next_song(self, category):
        """ Automatically play next song from bid queue, or randomly
        
        If a song was queued from a bid, play that (and remove from queue)
        Otherwise, pick a song randomly for the given category.
        Returns the info for the played song, for display status purposes.
        """
        queued = self.queue.find_one_and_delete() # Pull the current bid if there is one
        if queued and category in queued["song"]["types"]: # confirm it's for this category
            nextsong = queued["song"]
            # Charge the user their bid
            #bankbot.charge(queued["username"], queued["tokens"])
        else:
            #Otherwise, pick a random song for this category.
            nextsong = get_random(self, category)
        # Update lastplayed timestamp
        nextsong["lastplayed"] = datetime.now()
        self.songs.find_one_and_update({"id":nextsong["id"]}, nextsong)
        
        # And start the song.
        self.winampplayer.playSoloFile(nextsong["fullpath"])
        return nextsong # Return the song for display purposes
    
    def get_random(self, category):
        """ Returns song info by random
        
        Only picks songs inside a category, that haven't played within _time_before_replay
        """
        song_category = self.songs.find({"type": {"$in":category}, "lastplayed": {"$lt":datetime.now() - _time_before_replay}})
        return random.choice(song_category)
    
    def get_song_info(self, songid):
        """ Fuzzy-match songid to either song id, or full id (game-song)
        
        Return the song dict of its info, and the songid that matches, in case it was a fuzzy match
        Raises error on no match.
        """
        # Try exact match
        song = self.songs.find_one({"id":songid})
        # Try fuzzy match
        if song == None:
            match = difflib.get_close_matches(songid, self.songs.find(), 1, 0.8)
            if len(match) == 1:
                songid = match["id"]
                song = match
            else:
                raise ValueError("SongID {0} failed to match any song.".format(songid))
        return songid, song
      except: return ""
    
    def set_next_category(self, category):
        self.next_category = category
    
    def bid(self, user, songid, tokens):
        """ Attempt to place bid to queue song, for a user
        
        Tokens is assumed validated by the caller
        Songid might be invalid; will attempt fuzzy match
        Song must be in the upcoming category
        bid() will raise an error if bid fails, or song is invalid.
        """
        songid, song = self.get_song_info(songid)
        current_bid = self.queue.find_one()
        if current_bid == None:
            self._set_bid(user, song, tokens)
        elif user.username == current_bid["username"]:
            raise ValueError("Same bidder can't outbid themselves")
        elif tokens > current_bid["tokens"]:
            if self.next_category not in song["types"]:
                raise ValueError("{0} is not in the {1} category!".format(song["title"], self.current_category))
            else:
                self.queue.delete_one()
                self._set_bid(user, song, tokens)
        else: raise ValueError("Bid failed")
    
    def _set_bid(self, user, song, tokens):
        self.queue.insert_one({"username": user.username, "song":songid, "tokens": tokens})
    
    def rate(self, user, songid, rating):
        """ Set a user's rating of a given song"""
        songid, song = self.get_song_info(songid)
        if type(rating) != int or rating < 0 or rating >= 5:
            raise ValueError("Rating must be between 0 and 5.")
        self.song_ratings.find_one_and_update({"username": user.username, "songid": songid}, {"username": user.username, "songid": songid, "rating": rating}, upsert=True)
    

if __name__ == "__main__":
    library = MusicCat()
    while True:
        category = input("Enter category: ")
        fullid = input("Enter ID for a song: ")
        print(library.get_song_info(fullid))