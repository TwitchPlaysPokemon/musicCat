from abc import ABCMeta

class selectorCat:
    """A class that implements some form of song selection.

SelectorCats without properly punny class names are not allowed and are to be told that they have been very bad kitties."""
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_next_song(self,category):
	    """Put the song-choosing algorithm here. Expected to return something of the form
	{id:"song_id","lastplayed":datetime.datetime(), fullpath: ""} """
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
        if cls is selectorCat:
            if any("configure" in B.__dict__ for B in C.__mro__) and any("get_next_song" in B.__dict__ for B in C.__mro__):
                    return True
        return NotImplemented

class defaultCat:
    """A selectorCat that chooses songs randomly, as long as they haven't been played recently. """
    def __init__(musiccat):
        self.songs = musiccat.songs
        self.time_before_replay = musiccat.time_before_replay
    def get_next_song(category):
        """ Returns song info by random

        Only picks songs inside a category, that haven't played within _time_before_replay
        """
        songs_category = [song for song in self.songs.values() \
                            if category in song["types"] \
                            and song["lastplayed"] < datetime.datetime.now() - self.time_before_replay]
        return random.choice(songs_category)
    def configure(arguments):
        #!configure time_before_replay <amthours>
        if arguments[0] == "time_before_replay":
            if arguments[1].isdigit():
                amthours = float(arguments[1])
                self.time_before_replay = datetime.timedelta(hours=amthours)
            else:
                raise ValueError("Unable to parse provided delay.")

class completelyRandomCat:
    """A selectorCat that chooses songs completely randomly. More of an example than anything, really."""
    def __init__(musiccat):
        self.songs = musiccat.songs
    def get_next_song(category):
        songs_category = [song for song in self.songs.values() \
                            if category in song["types"] ]
        return random.choice(songs_category)
    def configure(arguments):
        pass



class Catamari:
    """Example selectorCat that only plays one particular song."""
    def __init__(musiccat):
        self.song = musiccat.song_info.find_one({"_id":"katamari_on_the_rocks"})
    def get_next_song():
        #KATAMARI~ DO YOUR BEST!
        return self.song
    def configure(arguments):
        pass
