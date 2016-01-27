# -*- coding: UTF-8 -*-
from abc import ABCMeta, abstractmethod
import random, datetime

class NoMatchingSongError(ValueError):
    """Raised when a selectorCat fails to find a fitting song for a given category."""
    def __init__(self, category):
        super(NoMatchingSongError, self).__init__("{} not found.".format(category))

class SelectorCat(metaclass=ABCMeta):
    """A class that implements some form of song selection.

    SelectorCats without properly punny class names are not allowed and are to be told that they have been very bad kitties."""

    @abstractmethod
    def get_next_song(self, category, songs):
        """Put the song-choosing algorithm here. Expected to return something of the form
        {id:"song_id","lastplayed":datetime.datetime(), fullpath: ""} or throw a NoMatchingSongError."""
        pass

    @abstractmethod
    def configure(self,arguments):
        """If an authorized user says !configure in chat, an array containing the arguments will be passed to this function.
        Use this instead of __init__ to pass in initial values.
        """
        pass

    @classmethod
    def __subclasshook__(cls,C):
        """Enable issubclass() to work for any class that implements configure() and get_next_song()"""
        if cls is SelectorCat:
            if any("configure" in B.__dict__ for B in C.__mro__) and any("get_next_song" in B.__dict__ for B in C.__mro__):
                return True
        return NotImplemented

class DefaultCat:
    """A selectorCat that chooses songs randomly, as long as they haven't been played recently. """
    def __init__(self, time_before_replay=datetime.timedelta(hours=6)):
        self.time_before_replay = time_before_replay
    def get_next_song(self, category, songs):
        """ Returns song info by random

        Only picks songs inside a category, that haven't played within self.time_before_replay
        """
        songs_category = [song for song in songs.values() \
                            if category in song["types"] \
                            and song["lastplayed"] < datetime.datetime.now() - self.time_before_replay]
        return random.choice(songs_category)
    def configure(self, arguments):
        #!configure time_before_replay <amthours>
        if arguments[0] == "time_before_replay":
            if arguments[1].isdigit():
                amthours = float(arguments[1])
                self.time_before_replay = datetime.timedelta(hours=amthours)
            else:
                raise ValueError("Unable to parse provided delay.")

class CompletelyRandomCat:
    """A selectorCat that chooses songs completely randomly. More of an example than anything, really."""
    def __init__(self):
        pass
    def get_next_song(self, category, songs):
        songs_category = [song for song in songs.values() \
                            if category in song["types"] ]
        return random.choice(songs_category)
    def configure(self, arguments):
        pass

class SpecificGameCat:
    """Only pick songs from a specific game. Use !configure to add games to this list."""
    def __init__(self):
        self.gameids = []
    def get_next_song(self, category, songs):
        songs_category = [song for song in songs.values() \
                            if category in song["types"] \
                            and song["game"]["id"] in self.gameids]
        if len(songs_category) > 0:
            return random.choice(songs_category)
        else:
            raise NoMatchingSongError(category)
    def configure(self, arguments):
        """Use !configure add <game1> <game2>...  to add the games to the list of games to choose from.
        !configure list should list the games as well, but returning a string might not be the right way of doing it. It's disabled for now.
        """
        if arguments[0] == "add":
            for game in arguments[1:]:
                if game not in self.gameids:
                    self.gameids.append(game)
        elif arguments[0] == "remove":
            for game in arguments[1:]:
                if game in self.gameids:
                    index = self.gameids.index(game)
                    self.gameids[index:index+1] = []
        """
        elif arguments[0] == "list":
            returnstring = "Games songs will be played from: "
            for x in self.games:
                returnstring += x + ","
            return returnstring[0:-1] #remove the comma after the last element
        """

class Catamari:
    """Example selectorCat that only plays one particular song.
    ♫ ┌༼ຈل͜ຈ༽┘ ♪ KATAMARI DO YOUR BEST ♪ └༼ຈل͜ຈ༽┐ ♫"""
    def __init__(self):
        self.targetid="katamari_on_the_rocks"

    def get_next_song(self, category, songs):
        if self.song == None:
            if self.targetid in songs.values():
                self.song = songs["katamari_on_the_rocks"]

        if(category == "betting") and (self.song==None):
          return self.song
        else:
          raise NoMatchingSongError(category)

    def configure(self, arguments):
        pass
