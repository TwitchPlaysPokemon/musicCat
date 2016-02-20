# TPPBR MusicCat Song Library v2.3
# Dependencies: pyyaml, python-Levenshtein, pymongo, pypiwin32
# Please install all with pip3

# (note: if installing python-Levenshtein complains about vcvarsall.bat,
#  see http://stackoverflow.com/a/33163704)

from __future__ import print_function
try:
    from builtins import input
except: # Temporary hack until the builtins future module is properly installed
    input = raw_input

from Levenshtein import ratio
import yaml

# standard modules
import os
import subprocess
import logging
import sys

import winamp

"""
Expected db formats:
pbr_ratings:
   {_id={username, songid}, rating: song rating, last_listened: datetime user last listened}
pbr_songinfo:
   {_id=songid, volume_multiplier: volume multiplier}
"""


class BadMatchError(ValueError):
    """Raised when a song id matches to a song with poor confidence."""
    def __init__(self, songid, match):
        super(BadMatchError, self).__init__("Song ID {} not found. Closest match: {}".format(songid, match))
        self.songid = songid
        self.match = match


class NoMatchError(ValueError):
    """Raised when a song id fails to match a song with any confidence"""
    def __init__(self, songid):
        super(NoMatchError, self).__init__("Song ID {} not found.".format(songid))
        self.songid = songid


class InsufficientBidError(ValueError):
    """Raised when an user's bid fails to beat an existing bid"""
    def __init__(self, bid, current_bid):
        super(InsufficientBidError, self).__init__("{} does not beat {}".format(bid, current_bid))
        self.bid = bid
        self.current_bid = current_bid


class MusicCat(object):
    def __init__(self, library_root, winamp_path):
        full_config_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), config_filename)
        self.root_path = library_root

        self.log = logging.getLogger("musicCat")

        self.base_volume = 1.0 # will be overridden when it's time to play a song

        self.load_metadata(self.root_path)

        # Initialize WinAmp and insert addl. function
        self.winamp = winamp.Winamp()

    def play_file(self, songfile):
        """ Runs Winamp to play given song file"""
        self.winamp.stop()
        self.winamp.clearPlaylist()
        p = subprocess.Popen('"{0}" "{1}"'.format(self.winamp_path, songfile))

    def load_metadata(self, root_path):
        """ Clears songlist and loads all metadata.yaml files under the root directory"""
        self.songs = {}
        for root, dirs, files in os.walk(root_path):
            for filename in files:
                if filename.endswith(".yaml"):
                    metafilename = os.path.join(root, filename)
                    try:
                        self.import_metadata(metafilename)
                    except Exception as e:
                        print("Exception while loading file {}: {}".format(metafilename, e))

    """
    Metadata.yaml format:
     - id: gameid
       title:
       series:
       year:
       platform:
       path: # No longer used
       songs:
        - id:
          title:
          path:
          type: type
          types: [type, type] #one or the other, depending on multiple
    """

    def import_metadata(self, metafilename):
        """Import metadata given a metadata filename. Assumed to be one game per metadata file."""
        with open(metafilename) as metafile:
            gamedata = yaml.load(metafile)
        path = os.path.dirname(metafilename)
        newsongs = {}
        songs = gamedata.pop("songs") #remove, since gamedata will be inserted to the song and we don't want circular references
        for song in songs:
            if song["id"] in self.songs or song["id"] in newsongs:
                raise StandardError("Song {} already exists! Not importing {}".format(song["id"], metafilename))
            song["fullpath"] = os.path.join(path, song["path"])
            song["game"] = gamedata
            if "type" in song: # Convert single type to a stored list
                song["types"] = [song.pop("type")]
            newsongs[song["id"]] = song

        # All data successfully imported; apply to existing library
        self.songs.update(newsongs)

    def calc_score(self, string, song):
        id_score = ratio(string, song["id"])
        title_score = ratio(string, song["title"])
        fullname_score = ratio(string, song["game"]["id"]+"-"+song["id"])
        score = max(id_score, title_score, fullname_score)
        return (song["id"], score)
    
    def find_matches(self, inputstring):
        """ Fuzzy match a string to all songs, and sort them by score"""
        matches = [self.calc_score(inputstring, song) for song in self.songs]
        matches.sort(key = lambda x: x[2])
        return matches

    def play_song(self, song_id):
        """ Play a song by id.

        Returns the info for the played song, for display status purposes.
        """
        nextsong = self.songs[song_id]
        
        # And start the song.
        self.play_file(nextsong["fullpath"])
        self.log.info("Now playing {}".format(nextsong["title"]))
        return nextsong # Return the song for display purposes

    def set_volume(self, volume):
        """Set the base volume for winamp"""
        self.base_volume = volume
        winamp_volume = self.base_volume * 255
        winamp_volume = min(max(winamp_volume, 0), 255)  # clamp to 0-255
        self.winamp.setVolume(winamp_volume)


if __name__ == "__main__":
    import sys

    library_path = "."
    winamp_path = "%PROGRAMFILES%/Winamp"
    library = MusicCat(library_path, winamp_path)
    while True:
        try:
            category = input("Enter category: ")
            fullid = input("Enter ID for a song: ")
            print(library.find_song_info(fullid))
        except Exception as e:
            print(e)
