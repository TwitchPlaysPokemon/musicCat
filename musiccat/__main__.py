
import os, sys
from . import MusicCat, NoMatchError

def rtfm():
    print("""Usage:
    musiccat count [category]     prints the total amount of songs found. filtered by a category if supplied
    musiccat play <song_id>       plays the song identified by the given song id
    musiccat pause                pauses the current song (resumes if already paused)
    musiccat unpause              resumes the current song (restarts the song if already running)
    musiccat volume <volume>      sets the volume, float between 0.0 and 1.0
    musiccat search <keyword>...  searches for a song by keywords and returns the best match""")

def main():
    # assumed windows-only for now
    winamp_path = os.path.expandvars("%PROGRAMFILES(X86)%/Winamp/winamp.exe")
    musiccat = MusicCat(".", winamp_path, disable_nobrstm_exception=True)

    # command-line interface
    if len(sys.argv) < 2:
        rtfm()
        return
    
    command = sys.argv[1]
    args = sys.argv[2:]
    if command == "count":
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
        songs = musiccat.search(args)
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
