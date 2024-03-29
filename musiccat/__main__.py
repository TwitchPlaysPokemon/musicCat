
import os, sys
import logging
import json
from . import MusicCat, NoMatchError

def rtfm():
    print("""Usage:
    musiccat [options] count [category]     prints the total amount of songs found. filtered by a category if supplied
    musiccat [options] verify               verifies the integrity and correctness of the music library. prints errors.
    musiccat [options] play <song_id>       plays the song identified by the given song id
    musiccat [options] pause                pauses the current song (resumes if already paused)
    musiccat [options] unpause              resumes the current song (restarts the song if already running)
    musiccat [options] volume <volume>      sets the volume, float between 0.0 and 1.0
    musiccat [options] search <keyword>...  searches for a song by keywords and returns the best match
    musiccat [options] listing <file>       generates a full json listing to file
Options:
    --nologging                   disables logging output
    --metapath=<path>             path to the metadata directory. default is current path
    --filepath=<path>             path to the songfiles. default is current path
    --showunused                  for verifying. Show unused songfiles""")

def main():
    # command-line interface
    if len(sys.argv) < 2:
        rtfm()
        return
    
    args = sys.argv[1:]
    options = {}
    while args:
        arg = args[0]
        for option in ("--nologging", "--metapath", "--filepath", "--showunused"):
            if arg.startswith(option):
                if "=" not in arg:
                    options[option] = None
                else:
                    options[option] = arg.split("=", maxsplit=1)[1]
                args.pop(0)
                break
        else:
            break
    
    command = ""
    if args:
        command = args.pop(0)
    
    if "--nologging" in options:
        logging.disable(logging.CRITICAL)
    
    if command == "listing" and args:
        print("Processing music library...")
        musiccat = MusicCat(options.get("--metapath", "."), disable_brstm_check=True)
        filepath = os.path.abspath(args[0])
        print("Generating listing...")
        listing = {}
        # Song = namedtuple("Song", ("id", "title", "path", "types", "game", "fullpath", "ends", "tags"))
        # Game = namedtuple("Game", ("id", "title", "platform", "year", "series","is_fanwork"))
        for song in musiccat.songs.values():
            if not listing.get(song.game.id, None):
                listing[song.game.id] = {
                    "id":song.game.id, 
                    "title": song.game.title,
                    "platform": song.game.platform,
                    "year": song.game.year,
                    "series": song.game.series,
                    "is_fanwork": song.game.is_fanwork,
                    "songs": []
                }
            listing[song.game.id]["songs"].append({
                "id": song.id,
                "title": song.title,
                "types": song.types,
                "ends": song.ends,
                "tags": song.tags                 
            })
        print("Writing listing to {}...".format(filepath))
        f = open(filepath, "w")
        f.write(json.dumps(listing, separators=(',', ':')))
        f.close()
        print("Finished.")
        return

    # assumed windows-only for now
    winamp_path = os.path.expandvars("%PROGRAMFILES(X86)%/Winamp/winamp.exe")
    musiccat = MusicCat(
        options.get("--metapath", "."),
        winamp_path,
        disable_nobrstm_exception=True,
        songfile_path=options.get("--filepath"),
    )
    
    if command == "count":
        if args:
            category = args[0]
            count = sum(1 for song in musiccat.songs.values() if category in song.types)
            print("Number of songs in category %s: %d" % (category, count))
        else:
            print("Number of songs: %d" % len(musiccat.songs))
    elif command == "verify":
        present_files = set()
        for root, _, files in os.walk(musiccat.songfile_path):
            for file in files:
                if not file.endswith(".yaml"):
                    present_files.add(os.path.join(root, file))
        metadata_files = set(s.fullpath for s in musiccat.songs.values())
        if "--showunused" in options:
            for unused in sorted(present_files - metadata_files):
                print("Unused songfile {}".format(unused))
        for missing in sorted(metadata_files - present_files):
            print("Missing songfile {}".format(missing))
        # look for duplicated metadata entries (2 entries with same songfile)
        existing = set()
        for entry in musiccat.songs.values():
            path = entry.fullpath
            if path in existing:
                print("Duplicated use of songfile {}".format(path))
            else:
                existing.add(path)
            # check for null values
            for key, value in entry._asdict().items():
                if value is None and key not in ("ends","tags",):
                    print("Empty field {} for songfile {}".format(key, path))
            for key, value in entry.game._asdict().items():
                if value is None and key not in ("series",):
                    print("Empty field game.{} for songfile {}".format(key, path))


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
