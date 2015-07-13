# MusicCat Test suite "TesterMime" v0.1

import sys
from menusystem.MenuSystem import *
import MusicCat

class TesterMime(object):
    def __init__(self, musiccat):
        self.musiccat = musiccat
        
        play_menu = [
            Choice(1, "Play Song ID", None),
            Choice(2, "Play Next", None),
            Choice(3, "Play Random", None),
            Choice(4, "Play Weighted Random", None)
            Choice(0, "Cancel", handler=lambda x:return False)
            ]

        main_menu = [
            Choice(1, "Check Song", subMenu=play_menu),
            Choice(2, "Play Song", None),
            Choice(3, "Rate Song", None),
            Choice(6, "Bid Song"),
            Choice(4, "Volume", None),
            Choice(5, "Import pack", None)
            ]

        self.mainmenu = Menu("MusicCat Test", main_menu)
        self.mainmenu.waitForInput()

if __name__ == "__main__":
    import sys
    root_path = "D:\Projects\TPPRB Music"
    winamp_path = "C:/Program Files (x86)/Winamp/winamp.exe"
    mongo_uri = "mongodb://abylls-server:27017"
    time_before_replay = datetime.timedelta(hours=6)
    minimum_match_ratio = 0.75
    minimum_autocorrect_ratio = 0.92
    library = MusicCat(root_path, time_before_replay, minimum_match_ratio, minimum_autocorrect_ratio, mongo_uri, winamp_path)

    TesterMime(library)