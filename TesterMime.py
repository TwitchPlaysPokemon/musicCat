# MusicCat Test suite "TesterMime" v0.1

import sys, os, traceback
from menusystem import *
from musiccat import MusicCat
from pprint import pprint

def testwrap(function, *args, **kwargs):
    """A curried wrapper function to display return value and capture exceptions cleanly"""
    def wrapper(*fargs, **fkeywords):
        newkwargs = kwargs.copy()
        newkwargs.update(fkeywords)
        try:
            val = function(*(args+fargs), **newkwargs)
            print(val)
        except Exception as e:
            print(traceback.format_exc())
    return wrapper

def nullfunc(*args, **kwargs):
    pass

def validate_path(path):
    if os.path.isfile(path):
        return path
    else:
        raise ValueError("Nonexistent path")

class TesterMime(object):
    def __init__(self, musiccat):
        self.musiccat = musiccat
        self.cat = self.musiccat.current_category
        play_menu = [
            Choice(1, "Play Song ID", handler=testwrap(nullfunc), subMenu=DataMenu("DISABLED", "Enter song id: ")),
            Choice(2, "Play Next", handler=testwrap(musiccat.play_next_song)),
            Choice(3, "Play Random", handler=self.playrandom),
            Choice(4, "Play Weighted Random", None),
            Choice(5, "Set Category", handler=self.set_category, subMenu=DataMenu("Category", "Enter category: ", valid=lambda cat: cat if cat in MusicCat._categories else None)),
            Choice(0, "Cancel", handler=lambda : False)
            ]

        
        main_menu = [
            Choice(1, "Check Song", handler=testwrap(musiccat.find_song_info), subMenu=DataMenu("Check Song", "Enter song id: ")),
            Choice(2, "Play Song", subMenu=Menu("Play Menu", play_menu)),
            Choice(3, "Rate Song", handler=testwrap(musiccat.rate_command), subMenu=DataMenu("Rate Song", "Enter song id and rating: ")),
            Choice(4, "Bid Song", handler=testwrap(nullfunc), subMenu=DataMenu("Bid Song", "Enter song id and bid: ")),
            Choice(5, "Volume", handler=testwrap(musiccat.set_base_volume), subMenu=DataMenu("Volume", "Set new volume(0-255): ", valid=int)),
            Choice(6, "Import pack", handler=testwrap(musiccat.import_metadata), subMenu=DataMenu("Import", "Enter metadata file path: ", validate_path)),
            Choice(7, "Debug", handler=testwrap(self.debug_output)),
            Choice(0, "Exit", handler=lambda : False)
            ]

        self.mainmenu = Menu("MusicCat Test", main_menu)
        self.mainmenu.waitForInput()
    
    def set_category(self, cat):
        self.cat = cat
    
    def playrandom(self):
        pprint(self.musiccat.play_next_song(self.cat, use_bid=False))
    
    def debug_output(self, *args):
        pprint(self.musiccat.songs)

if __name__ == "__main__":
    import sys, datetime
    root_path = "D:\Projects\TPPRB Music"
    winamp_path = "C:/Program Files (x86)/Winamp/winamp.exe"
    mongo_uri = "mongodb://abylls-server:27017"
    time_before_replay = datetime.timedelta(hours=6)
    minimum_match_ratio = 0.75
    minimum_autocorrect_ratio = 0.92
    base_volume = 150
    library = MusicCat(root_path, time_before_replay, minimum_match_ratio, minimum_autocorrect_ratio, mongo_uri, winamp_path,base_volume)

    TesterMime(library)