# TPPBR MusicCat Song Library
# Dependencies: pyyaml, python-Levenshtein, pypiwin32 (windows-only)
# see also setup.py, python-Levenshtein needs compilation or manual installation via binary.
# Please install all with pip3

# (note: if installing python-Levenshtein complains about vcvarsall.bat,
#  see http://stackoverflow.com/a/33163704)

from __future__ import print_function
try:
    from builtins import input
except: # Temporary hack until the builtins future module is properly installed
    input = raw_input

# pip3 dependencies
import Levenshtein
import yaml

# standard modules
import os
import subprocess
import logging
from collections import namedtuple

import winamp

class NoMatchError(ValueError):
    """Raised when a song id fails to match a song with any confidence"""
    def __init__(self, songid):
        super(NoMatchError, self).__init__("Song ID {} not found.".format(songid))
        self.songid = songid

Song = namedtuple("Song", ("id", "title", "path", "types", "game", "fullpath"))
Game = namedtuple("Game", ("id", "title", "platform", "year", "series", "path"))

class MusicCat(object):

    def __init__(self, library_path, winamp_path):
        self.library_path = library_path
        self.winamp_path = winamp_path
        self.songs = {}
        self.winamp = winamp.Winamp()
        self.log = logging.getLogger("musicCat")
        self.paused = False

        self.refresh_song_list()

    def refresh_song_list(self):
        """ Clears songlist and loads all metadata.yaml files under self.library_path"""
        self.songs = {}
        for root, dirs, files in os.walk(self.library_path):
            for filename in files:
                if filename.endswith(".yaml"):
                    metafilename = os.path.join(root, filename)
                    try:
                        self._import_metadata(metafilename)
                    except Exception as e:
                        self.log.error("Exception while loading file {}: {}".format(metafilename, e))
        if len(self.songs) == 0:
            self.log.warn("No metadata found! MusicCat isn't going to do very much. (Current music library location: {} )".format(self.library_path))
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

    def _import_metadata(self, metafilename):
        """Import metadata given a metadata filename. Assumed to be one game per metadata file."""
        with open(metafilename) as metafile:
            gamedata = yaml.load(metafile)
        path = os.path.dirname(metafilename)
        newsongs = {}

        songs = gamedata.pop("songs")
        game = Game(**gamedata)

        for song in songs:
            song["fullpath"] = os.path.join(path, song["path"])
            song["game"] = game

            # Convert single type to a stored list
            if "type" in song:
                song["types"] = [song.pop("type")]
            
            newsong = Song(**song)

            #some sanity checks
            if newsong.id in self.songs:
                self.log.warn("Songid conflict! {} exists twice, once in {} and once in {}!".format(newsong.id, self.songs[newsong.id].game.id, game.id))
            if newsong.id in newsongs:
                self.log.warn("Songid conflict! {} exists twice in the same game, {}.".format(newsong.id, game.id))
            if not os.path.isfile(newsong.fullpath):
                self.log.error("Songid {} doesn't have a BRSTM file at {}!".format(newsong.id, newsong.fullpath))
            #add to song list!
            self.songs[newsong.id] = newsong

    def _play_file(self, songfile):
        """ Runs Winamp to play given song file. 
            Though this may appear to, using subprocess.Popen does not leak memory because winamp makes the processes all exit."""
        self.winamp.stop()
        self.winamp.clearPlaylist()
        p = subprocess.Popen('"{0}" "{1}"'.format(self.winamp_path, songfile))

    def search(self,songid):
        """Search through all songs in self.songs; return any IDs close to what is typed out.
        Returns an array of tuples of the form (songid, matchratio), where matchratio goes from 0 to 1; 1 being a better match. This array is also pre-sorted by match ratio."""
        #Try exact match
        song = self.songs.get(songid, None)

        if song is not None:
            return [(song, 1.0)]
        else:
            #If that didn't work, get all songs that seem close enough
            return sorted([(s,Levenshtein.ratio(songid, s.id)) for s in self.songs.values()], key=lambda s: s[1], reverse=True)

    def play_song(self, songid):
        """ Play a song. May raise a NoMatchError if the songid doesn't exist."""
        if songid not in self.songs:
            raise NoMatchError(songid)
        nextsong = self.songs[songid]
        self.current_song = nextsong
        self._play_file(nextsong.fullpath)
        self.log.info("Now playing {}".format(nextsong))

    def set_volume(self, volume):
        """Update winamp's volume. Volume goes from 0 to 1"""
        if (volume < 0) or (volume > 1):
            raise ValueError("Volume must be between 0 and 1")
        #winamp expects a volume from 0 to 255
        self.winamp.setVolume(volume*255)

    def pause(self):
        self.winamp.pause()
        self.paused = True

    def unpause(self):
        #winamp.play() will restart the song from the beginning if not paused.
        #If you want to restart the song, just call play_song with the same song.
        if self.paused:
            self.winamp.play()
            self.paused = False

    def amt_songs(self, category=None):
        """Return the total number of songs (or the amount of songs in a specific category if one is given).
        For most purposes, using len(musiccat.songs) is preferred."""
        if category == None:
            amtsongs = len(self.songs)
        else:
            amtsongs = len([songid for songid in self.songs if category in self.songs[songid].types])
        return amtsongs

def rtfm():
    print("""Usage:
    musiccat.py count [category]     prints the total amount of songs found. filtered by a category if supplied
    musiccat.py play <song_id>       plays the song identified by the given song id
    musiccat.py pause                pauses the current song (resumes if already paused)
    musiccat.py unpause              resumes the current song (restarts the song if already running)
    musiccat.py volume <volume>      sets the volume, float between 0.0 and 1.0
    musiccat.py search <keyword>...  searches for a song by keywords and returns the best match""")

def main():
    #assumed windows-only for now
    import sys
    
    winamp_path = ''
    if 'PROGRAMFILES(X86)' in os.environ:
        winamp_path = os.environ['PROGRAMFILES(X86)'] + r"\Winamp\winamp.exe"
    musiccat = MusicCat(".", winamp_path)

    #command-line access
    #run "musiccat.py search <songid> to call musiccat.search("songid"), for example
    #or "musiccat.py amt_songs"
    if len(sys.argv) < 2:
        rtfm()
        return
    
    command = sys.argv[1]
    args = sys.argv[2:]
    if command == "count":
        category = None
        if args:
            category = args[0]
            count = sum(1 for song in musiccat.songs.values() if category in song.types)
            print("Number of songs in category %s: %d" % (category, count))
        else:
            print("Number of songs: %d" % len(musiccat.songs))
    elif command == "play" and args:
        try:
            musiccat.play_song(args[0])
        except NoMatchError:
            print("No song with that id")
    elif command == "pause":
        musiccat.pause()
    elif command == "unpause":
        musiccat.unpause()
    elif command == "volume" and args:
        try:
            volume = float(args[0])
            if not 0.0 <= volume <= 1.0:
                raise ValueError("Invalid volume range")
            musiccat.set_volume(volume)
        except ValueError:
            print("Volume must be a float between 0.0 and 1.0")
    elif command == "search" and args:
        songs = musiccat.search(" ".join(args))
        if not songs:
            print("No songs found.")
        else:
            # maximum of 5 results
            limit = 5
            count = len(songs)
            best = songs[:limit]
            print("Found %d songs, best matches first:" % count)
            for song, score in best:
                print("%4.0f%%: %s (%s)" % (score*100, song.title, song.game.title))
            if count > limit:
                print("and %d more" % (count - limit))
    else:
        rtfm()

if __name__ == "__main__":
    main()
