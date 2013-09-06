import urllib2
import shutil
import json
import copy
import eyed3
import os
import sys

BASE_URL = "http://api.musixmatch.com/ws/1.1/"
API_KEY = "YOUR API KEY HERE"
base_params = {"apikey": API_KEY}
WORD_FILTER = {"fuck",
               "shit",
               "damn",
               "hell",
               "bitch",
               "crap",
               " ass",
               "sex",
               "dick",
               "pussy",
               "piss"}
DEFAULT_DIRECTORY = "./"
DESTINATION_DIRECTORY = "../filtered_songs/"


def _make_request(target, in_params):
    params = copy.deepcopy(in_params)
    params.update(base_params)
    final_url = "".join((BASE_URL, target, _encode_get(params)))
    response = urllib2.urlopen(final_url)
    try:
        response_dict = json.loads(response.read())
    except ValueError:
        # no response from goofballs
        return None
    return response_dict


def _encode_get(dict_obj):
    ret_string = ""
    first = True
    for key, value in dict_obj.items():
        if first:
            ret_string += '?'
        else:
            ret_string += '&'
        ret_string += "%s=%s" % (key, value)
        first = False
    return ret_string


def get_artist_id(artist_name):
    params = {"q_artist": "\"%s\"" % artist_name}
    TARGET = "artist.search"
    response_dict = _make_request(TARGET, params)
    if not response_dict:
        return -1
    artist_list = response_dict["message"]["body"]["artist_list"]
    for artist_dict in artist_list:
        if artist_name.lower() == artist_dict["artist"]["artist_name"].lower():
            return artist_dict["artist"]["artist_id"]
    return -1


def get_possible_tracks(artist_id, track_name):
    TARGET = "track.search"
    params = {"f_artist_id": "%s" % artist_id,
              "q_track": "\"%s\"" % track_name}
    response_dict = _make_request(TARGET, params)
    if not response_dict:
        return []
    track_list = response_dict["message"]["body"]["track_list"]
    track_ids = []
    for track in track_list:
        if track["track"]["track_name"].lower() == track_name.lower():
            return [track["track"]["track_id"]]
        track_ids.append(track["track"]["track_id"])
    return track_ids


def get_lyrics(track_ids):
    TARGET = "track.lyrics.get"
    all_lyrics = ""
    for track_id in track_ids:
        params = {"track_id": "%s" % track_id}
        response_dict = _make_request(TARGET, params)
        if not response_dict:
            continue
        try:
            all_lyrics += response_dict["message"]["body"]["lyrics"]["lyrics_body"]
        except TypeError:
            print response_dict.__str__()
    return all_lyrics


def filter_song(lyrics, title):
    if len(lyrics) == 0:  # assume it's dirty if we can't get the lyrics
        return False, ''
    for curse_word in WORD_FILTER:
        if curse_word in lyrics.lower() or curse_word in title.lower():
            return False, curse_word
    return True, ''


def get_track_info(filename):
    if not filename.endswith(".mp3"):
        return None, None
    audio_file = eyed3.load(filename)
    tag = audio_file.tag
    if tag is None:
        return None, None
    return tag.artist, tag.title


def process_file(filename):
    artist, title = get_track_info(filename)
    if artist and title:
        for curse_word in WORD_FILTER:
            if curse_word in title.lower():
                return False, ''
        artist_id = get_artist_id(artist)
        possible_track_ids = get_possible_tracks(artist_id, title)
        lyrics = get_lyrics(possible_track_ids)
        return filter_song(lyrics, filename)
    return False, ''


def traverse_target_directory():
    clean_songs = 0
    total_songs = 0
    for root, dirs, files in os.walk(DEFAULT_DIRECTORY):
        current_directory = root.replace(DEFAULT_DIRECTORY, "")
        for name in files:
            full_path = "/".join((root, name))
            clean, word = process_file(full_path)
            if name.endswith(".mp3"):
                total_songs += 1
            if clean:
                clean_songs += 1
                target_directory = "/".join((DESTINATION_DIRECTORY, current_directory))
                if not os.path.exists(target_directory):
                    os.makedirs(target_directory)
                destination_path = "/".join((target_directory, name))
                shutil.copy2(full_path, destination_path)
                print "CLEAN: %s" % name
            else:
                if len(word) > 0:
                    print "DIRTY: %s because of the word %s" % (name, word.upper())
                else:
                    print "DIRTY: %s because of wrong file type or no lyrics data" % name
    print "%s percent of your songs have been determined to be non-explicit and have been transferred" % (100.0 * float(clean_songs) / total_songs)


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        DEFAULT_DIRECTORY = sys.argv[1]
    if len(sys.argv) >= 3:
        DESTINATION_DIRECTORY = sys.argv[2]
    traverse_target_directory()
