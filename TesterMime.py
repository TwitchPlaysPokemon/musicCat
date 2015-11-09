# MusicCat Test suite "TesterMime" v0.1

import sys, os, traceback
from menusystem import *
from musiccat import MusicCat
import selectorcats
from pprint import pprint

def testwrap(function, *args, **kwargs):
    """A curried wrapper function to display return value and capture exceptions cleanly"""
    def wrapper(*fargs, **fkeywords):
        newkwargs = kwargs.copy()
        newkwargs.update(fkeywords)
        try:
            val = function(*(args+fargs), **newkwargs)
            pprint(val)
        except Exception as e:
            print(traceback.format_exc())
    return wrapper
t = testwrap

def nullfunc(*args, **kwargs):
    pass

def validate_path(path):
    if os.path.isfile(path):
        return path
    else:
        raise ValueError("Nonexistent path")

class PBRUser(object):
    def __init__(self, name, tokens=10):
        self.username = name
        self.tokens = tokens
    
    def set_name(self, name):
        self.username = name
    
    def set_tokens(self, tokens):
        self.tokens = tokens

class TesterMime(object):
    def __init__(self, musiccat):
        self.musiccat = musiccat
        self.cat = self.musiccat.current_category
        self.user = PBRUser("Abyll", 99)
        play_menu = [
            Choice(1, "Play Song ID", handler=t(nullfunc), subMenu=DataMenu("DISABLED", "Enter song id: ")),
            Choice(2, "Play Next", handler=t(self.playnext)),
            Choice(3, "Play Random", handler=t(self.playrandom)),
            Choice(4, "Play Next Category", handler=t(self.playnextcat)),
            Choice(5, "Set Category", handler=self.set_category, subMenu=DataMenu("Category", "Enter category: ", valid=lambda cat: cat if cat in MusicCat._categories else None)),
            Choice(0, "Cancel", handler=lambda : False)
            ]

        config_menu = [
            Choice(1, "Song Cooldown", handler=t(musiccat.set_cooldown), subMenu=DataMenu("Time Before Song Replay", "Enter # of minutes: ", valid=int)),
            Choice(2, "Volume", handler=t(musiccat.set_base_volume), subMenu=DataMenu("Volume", "Set new volume(0-255): ", valid=int)),
            Choice(3, "Change username", handler=self.user.set_name, subMenu=DataMenu("Username", "Enter new name: ")),
            Choice(4, "Reset tokens", handler=self.user.set_tokens, subMenu=DataMenu("Tokens", "Enter tokens: ", valid=int)),
            Choice(0, "Cancel", handler=lambda : False)
            ]
        
        main_menu = [
            Choice(1, "Check Song", handler=t(musiccat.find_song_info), subMenu=DataMenu("Check Song", "Enter song id: ")),
            Choice(2, "Play Song", subMenu=Menu("Play Menu", play_menu)),
            Choice(3, "Rate Song", handler=t(self.do_rate), subMenu=DataMenu("Rate Song", "Enter song id and rating: ")),
            Choice(4, "Bid Song", handler=t(self.do_bid), subMenu=DataMenu("Bid Song", "Enter song id and bid: ")),
            Choice(5, "Config", subMenu=Menu("Config", config_menu)),
            Choice(6, "Import pack", handler=t(musiccat.import_metadata), subMenu=DataMenu("Import", "Enter metadata file path: ", validate_path)),
            Choice(7, "Debug", handler=t(self.debug_output), subMenu=DataMenu("Debug", "Enter statement: ")),
            Choice(0, "Exit", handler=lambda : False)
            ]

        self.mainmenu = Menu("MusicCat Test", main_menu)
        self.mainmenu.waitForInput()
    
    def set_category(self, cat):
        self.cat = cat
    
    def do_rate(self, args):
        self.musiccat.rate_command(self.user, args)
    
    def do_bid(self, args):
        self.musiccat.bid_command(self.user, args)
    
    def playnextcat(self):
        val = self.musiccat.play_next_song()
        self.category = self.musiccat.current_category
        return val
    
    def playnext(self):
        return self.musiccat.play_next_song(self.cat, use_bid=True)
    
    def playrandom(self):
        return self.musiccat.play_next_song(self.cat, use_bid=False)
    
    def debug_output(self, *args):
        return [eval(arg) for arg in args]

if __name__ == "__main__":
    import sys, datetime
    root_path = "D:\Projects\TPPRB Music"
    winamp_path = "C:/Program Files (x86)/Winamp/winamp.exe"
    mongo_uri = "mongodb://abylls-server:27017"
    time_before_replay = datetime.timedelta(minutes=3)
    minimum_match_ratio = 0.75
    minimum_autocorrect_ratio = 0.92
    base_volume = 150
    default_selectorcat_class = selectorcats.defaultCat
    library = MusicCat(root_path, time_before_replay, minimum_match_ratio, minimum_autocorrect_ratio, mongo_uri, winamp_path,base_volume, default_selectorcat_class)

    TesterMime(library)