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

# pip3 dependencies
import Levenshtein
import yaml
from pymongo import MongoClient

# standard modules
import os
import random
import datetime
import subprocess
import logging
import sys
from bson import CodecOptions, SON

# TPP modules
# import tokens, chat
import winamp
import selectorcats
import bidcat

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
        super(BadMatchError, self).__init__("{} not found. Closest match: {}".format(songid, match))
        self.songid = songid
        self.match = match


class NoMatchError(ValueError):
    """Raised when a song id fails to match a song with any confidence"""
    def __init__(self, songid):
        super(BadMatchError, self).__init__("{} not found.".format(songid))
        self.songid = songid


class InvalidCategoryError(ValueError):
    """Raised when a category is specified and doesn't match a song"""
    def __init__(self, songid, category):
        super(InvalidCategoryError, self).__init__("{} is not a valid category for {}".format(category, songid))
        self.songid = songid
        self.category = category


class InsufficientBidError(ValueError):
    """Raised when a user's bid fails to beat an existing bid"""
    def __init__(self, bid, current_bid):
        super(InsufficientBidError, self).__init__("{} does not beat {}".format(bid, current_bid))
        self.bid = bid
        self.current_bid = current_bid


class MusicCat(object):
    _categories = ["betting", "warning", "battle", "result", "break"]

    def __init__(self, config_filename="config.yaml"):
        full_config_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), config_filename)
        try:
            config = yaml.load(open(full_config_path))
        except:
            raise FileNotFoundError("Config file " + config_filename + " not found!")

        try:
            self.root_path = config["root_path"] # path to metadata files
            self.base_volume = config["master_winamp_volume"]
            self.default_song_volume = config["default_song_volume"] # will be used if a song has no volume
            self.debug_enabled = config["debug"]
            self.no_bidding_on_warning = config["no_bidding_on_warning"]
            hours = int(config["default_time_before_replay_hrs"]) # error here means value isn't a number; still means invalid config file
            self.time_before_replay = datetime.timedelta(hours=hours)
            self.minimum_autocorrect_ratio = config["min_fuzzymatch_accept_ratio"]
            self.minimum_match_ratio = config["min_fuzzymatch_warn_ratio"]
            self.winamp_path = config["winamp_path"]
        except KeyError as e:
            raise ValueError("Config file missing required parameter '{}'".format(e.args[0])) from e
        except ValueError as e:
            raise ValueError("Unable to parse a number from config file") from e

        default_selectorcat_class = selectorcats.defaultCat

        mongo_uri = config["mongo_uri"]
        client = MongoClient(mongo_uri)
        self.songdb = client.pbr_database
        self.song_ratings = self.songdb["pbr_ratings"].with_options(codec_options=CodecOptions(document_class=SON))
        self.song_info = self.songdb["pbr_songinfo"].with_options(codec_options=CodecOptions(document_class=SON))

        self.log = logging.getLogger("musicCat")

        self.current_category = MusicCat._categories[0]
        self.current_song = None
        self.last_song = None
        self.current_song_volume = 1.0 # will be overridden when it's time to play a song

        self.bid_queue = {}
        # Bidding queue, for each category: {category: {song: songid, username: name, bid: amount}}
        for category in MusicCat._categories:
                bid_queue[category] = bidcat.Auction()

        self.load_metadata(self.root_path)

        # After self.load_metadata() is called, initialize the selectorcats from the class
        self.selectorcat = default_selectorcat_class()
        self.default_selectorcat = default_selectorcat_class()

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

        if self.song_info:
            bulkOperation = self.song_info.initialize_unordered_bulk_op() # prepare to update self.song_info

        gameid = gamedata["id"]
        system = gamedata["platform"]
        songs = gamedata.pop("songs")
        for song in songs:
            if song["id"] in self.songs or song["id"] in newsongs:
                raise StandardError("Song {} already exists! Not importing {}".format(song["id"], metafilename))
            song["fullpath"] = os.path.join(path, song["path"])
            song["game"] = gamedata
            song["lastplayed"] = datetime.datetime.now() - self.time_before_replay
            if "type" in song: # Convert single type to a stored list
                song["types"] = [song.pop("type")]

            # queue an operation to update self.song_info
            if self.song_info:
                bulkOperation.find({'_id': song["id"]}).upsert().update({'$setOnInsert': {'volume_multiplier': self.default_song_volume}})

            newsongs[song["id"]] = song

        # do all the updates at once
        if self.song_info:
            bulkOperation.execute()

        # All data successfully imported; apply to existing metadata
        self.songs.update(newsongs)

    def next_category(self):
        """Returns the category that follows the currently-playing category"""
        next_ind = MusicCat._categories.index(self.current_category) + 1
        if next_ind == len(_categories):
            next_ind = 0
        return _categories[next_ind]

    def find_song_info(self, songid):
        """ Fuzzy-match songid to either song id, or full id (game-song)

        Return the song dict of its info, and the songid that matches, in case it was a fuzzy match
        Raises error on no match.
        """
        if songid.find("-") > 0: # Dash separates game and song id
            gameid, songid = songid.split("-")
        # Try exact match
        song = self.songs.get(songid, None)

        # Try fuzzy match
        if song is None:
            best_ratio = 0
            best_match = None
            for s in self.songs:
                ratio = Levenshtein.ratio(songid, s)
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = s
            if best_ratio < self.minimum_autocorrect_ratio: # No close enough match, tell user closest match
                raise BadMatchError(songid, best_match)
            elif best_ratio < self.minimum_match_ratio: # No match close enough to be reliable
                raise NoMatchError(songid)
            else: # close enough to autocorrect for them.
                song = best_match
        return song

    def play_next_song(self, category, use_bid=True):
        """ Automatically play next song from bid queue, or randomly

        If a song was queued from a bid, play that (and remove from bid_queue)
        Otherwise, pick a song randomly for the given category.
        Returns the info for the played song, for display status purposes.
        """
        if category in self.bid_queue and use_bid:
            queued = self.bid_queue.pop(category)
            nextsong = queued["song"]
            # Charge the user their bid
            tokens.adjust_tokens(queued["username"], -queued["tokens"])
        else:
            # Otherwise, let the selectorCat decide a random song for this category.
            try:
                nextsong = self.selectorcat.get_next_song(category, self.songs)
            except selectorcats.NoMatchingSongError:
                # If there isn't a song that matches (such as a game with no warning music) use the default selectorCat
                nextsong = self.default_selectorcat.get_next_song(category)
        # Update lastplayed timestamp
        nextsong["lastplayed"] = datetime.datetime.now()
        # fetch volume
        if self.song_info:
            matching_song = self.song_info.find_one({"_id": nextsong["id"]})
            if matching_song:
                # assuming that we only want the first match anyways
                self.current_song_volume = matching_song.volume_multiplier
                self.update_winamp_volume()
            else:
                # Volume data should be fed into the database when the metadata files are loaded, but just in case
                self.log.warn("Volume for Song ID {} not found!".format(nextsong["id"]))
                self.current_song_volume = default_song_volume

        # And start the song.
        self.current_category = category
        self.current_song = nextsong
        self.play_file(nextsong["fullpath"])
        self.log.info("Now playing {}".format(nextsong))
        return nextsong # Return the song for display purposes

    def bid_command(self, userdata, args):
        """Handle a bid command
        userdata: a dict containing {username: String}
        args: A string: "songid tokens" separated by a space.
        May throw a ValueError, InvalidCategoryError, or InsufficientBidError (from the self.bid() call)
        """
        user = userdata["username"]
        songid, tokens = args.split(" ")
        try:
            tokens = int(tokens)
        except:
            raise ValueError("Invalid amount of tokens!")
        nextcategory = self.next_category()
        songinfo = self.find_song_info(songid)

        # if you bid during betting (when the next category is technically warning), treat the next category as battle
        if not self.no_bidding_on_warning and (nextcategory == "warning"):
            nextcategory = "battle"

        category_is_ok = False
        if nextcategory in songinfo['types']:
            category_is_ok = True

        if category_is_ok:
            self.bid(user, songid, tokens, nextcategory)
        else:
            raise InvalidCategoryError(nextcategory, songid)

    def bid(self, user, songid, tokens, category=None):
        """Attempt to place bid to queue song, for a user

        Tokens is assumed validated by the caller
        Songid might be invalid; will attempt fuzzy match
        Song must be in the upcoming category
        bid() will raise an error if bid fails, or song is invalid.
        """
        song = self.find_song_info(songid)
        if category not in song["types"]:
            raise InvalidCategoryError(songid, category)
        if category is None:  # Default to the first type in the song's list.
            category = song["types"][0]
        current_bid = self.queue.get(category, None)
        if current_bid is None:  # autowin!
            self._set_bid(user, song, tokens)
        elif user.username == current_bid["username"]:
            raise ValueError("Same bidder can't outbid themselves")
        elif tokens <= current_bid["tokens"]:
            raise InsufficientBidError(bid, current_bid["tokens"])
        else:
            self.bid_queue[category] = {"username": user.username, "song": song["id"], "tokens": tokens}
            self.log.info("{} placed bid of {} for {}".format(user.username, tokens, song["id"]))

    def rate_command(self, user, args):
        """Store an user's rating in the database, parsing the command.
        user: a string
        args: A string: "<songid> <rating>" separated by a space. """
        songid, rating = args.split(" ")
        self.rate(user, songid, rating)    # error checking is all done in here

    def rate(self, user, songid, rating):
        """ Set a user's rating of a given song"""
        songid, song = self.find_song_info(songid)
        if type(rating) != int or rating < 0 or rating >= 5:
            raise ValueError("Rating must be between 0 and 5.")
        self.song_ratings.find_one_and_update({"username": user.username, "songid": songid}, {"username": user.username, "songid": songid, "rating": rating}, upsert=True)
        self.log.info("{} rated songid {} with a rating of {}".format(user.username, songid, rating))

    def set_base_volume(self, basevolume):
        """Set the base volume for winamp"""
        self.base_volume = basevolume
        self.update_winamp_volume()

    def set_current_song_volume(self, songid, volume):
        """Update the database with the volume for the given song."""
        if (volume < 0.0) or (volume > 2.0):
            raise ValueError("Volume multiplier must be between 0 and 2.")
        updatedSong = self.song_info.update({'_id': songid}, {'_id': songid, "volume_multiplier": volume})
        if updatedSong is None:
            raise StandardError("Song ID {} not found!".format(songid))
        elif songid == currentsongid:
            self.current_song_volume = volume
            self.update_winamp_volume()
            self.log.info("Set volume_multiplier for {} to {}".format(songid, volume))

    def update_winamp_volume(self):
        """Update winamp's volume from self.base_volume and the song's volume_multiplier"""
        winamp_volume = int(self.base_volume * self.current_song_volume)
        winamp_volume = min(max(winamp_volume, 0), 255)  # clamp to 0-255
        self.winamp.setVolume(winamp_volume)
        # log("set winamp volume to "+str(winamp_volume))

    def set_cooldown(self, time_in_minutes):
        self.time_before_replay = datetime.timedelta(minutes=time_in_minutes)

if __name__ == "__main__":
    import sys

    # Load config from config file
    config_filename = "config.yaml"
    library = MusicCat(config_filename)
    while True:
        try:
            category = input("Enter category: ")
            fullid = input("Enter ID for a song: ")
            print(library.find_song_info(fullid))
        except Exception as e:
            print(e)
