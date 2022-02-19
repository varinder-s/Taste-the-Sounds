import os

from cs50 import SQL
import os
import requests
import urllib.parse
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
from statistics import pstdev, mean

import spoonacular as spoon
api = spoon.API(os.environ.get("SPOONACULAR_API_KEY"))

# Constants. Determined by actual daily averages for each amount
DVCAL = 2250
DVFAT = 69
DVSODIUM = 3400


def getTrack(song):
    
    # Look up song from Spotify
    sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    results = sp.search(song, limit=1, type='track')
    return results
    
def getFeatures(songID):
    
    # Get song's audio features
    sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    return sp.audio_features(songID)
    

def getMinMax(genres):
    
    # Get min and max values of certain audio features of a song
    db = SQL("sqlite:///project.db")
    artist_genres = {"danceability": [], "energy": [], "valence": []}
    clustered = {"danceability": [], "energy": [], "valence": []}
    MinMax = {"danceability": [], "energy": [], "valence": []}
    raw_data = db.execute("SELECT * FROM genres")
    
    # See if the artist has genres associated with them
    if not genres or genres == None:
        
        # Get averages of all genres
        for data in raw_data:
            clustered["danceability"].append(data["danceability"])
            clustered["energy"].append(data["energy"])
            clustered["valence"].append(data["valence"])
            
        # Get the min and max values from the genre averages
        MinMax["danceability"].append(min(clustered["danceability"]))
        MinMax["energy"].append(min(clustered["energy"]))
        MinMax["valence"].append(min(clustered["valence"]))
        MinMax["danceability"].append(max(clustered["danceability"]))
        MinMax["energy"].append(max(clustered["energy"]))
        MinMax["valence"].append(max(clustered["valence"]))
        return MinMax
    else:
        
        # Get averages of the genres associated with the artist
        for data in raw_data:
            if data["name"] in genres:
                artist_genres["danceability"].append(data["danceability"])
                artist_genres["energy"].append(data["energy"])
                artist_genres["valence"].append(data["valence"])
                
            # Get averages of all genres
            clustered["danceability"].append(data["danceability"])
            clustered["energy"].append(data["energy"])
            clustered["valence"].append(data["valence"])
            
        # Add the average of all genres to the list of artist genre averages
        artist_genres["danceability"].append(mean(clustered["danceability"]))
        artist_genres["energy"].append(mean(clustered["energy"]))
        artist_genres["valence"].append(mean(clustered["valence"]))
        
        # Get the min and max values from the genre averages
        MinMax["danceability"].append(min(artist_genres["danceability"]))
        MinMax["energy"].append(min(artist_genres["energy"]))
        MinMax["valence"].append(min(artist_genres["valence"]))
        MinMax["danceability"].append(max(artist_genres["danceability"]))
        MinMax["energy"].append(max(artist_genres["energy"]))
        MinMax["valence"].append(max(artist_genres["valence"]))
        return MinMax
    
def getFood(track):
    sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    artist = sp.artist(track["artists"][0]["id"])
    genres = artist["genres"]
    
    # Get audio features of the song
    features = getFeatures(track["id"])
    
    # Get min and max values of certain audio features of a song
    MinMax = getMinMax(genres)
    
    # Open up range between min and max to account for the fact that some songs will be outside of initial range
    minDance = min(MinMax["danceability"]) * .75
    maxDance = max(MinMax["danceability"]) * 1.25
    minValence = min(MinMax["valence"]) * .75
    maxValence = max(MinMax["valence"]) * 1.25
    minEnergy = min(MinMax["energy"]) * .75
    maxEnergy = max(MinMax["energy"]) * 1.25
    
    # Normalize range and use to calculate percentage for each feature
    perDance = (features[0]["danceability"] - minDance) * (100 / (maxDance - minDance))
    perValence = (features[0]["valence"] - minValence) * (100 / (maxValence - minValence))
    perEnergy = (features[0]["energy"] - minEnergy) * (100 / (maxEnergy - minEnergy))
    
    # Ensure percentages are not ridiculous
    if perDance > 150:
        perDance = 150
    if perDance < 1:
        perDance = 1
    if perEnergy > 150:
        perEnergy = 150
    if perEnergy < -1:
        perEnergy = 1
    if perValence > 150:
        perValence = 150
    if perValence < 1:
        perValence = 1
    
    # Calculate a song score by combining percentages of all features
    songScore = abs((perDance + perEnergy + perValence) / 300)
    
    # Finding nutrient info relative to each song
    # 3 determined by most people eating 3 meals per day
    songCal = (songScore * DVCAL) / 3
    songSodium = (songScore * DVSODIUM) / 3
    songFat = (songScore * DVFAT) / 3
    response = api.nutrient_search(songCal * 1.1, songCal * 0.9, songSodium * 25, songSodium * 0.05, songFat * 25, songFat * 0.05)
    data = response.json()
    return data
    

def updateDB(track):
    db = SQL("sqlite:///project.db")
    sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    artist = sp.artist(track["artists"][0]["id"])
    artistGenres = artist["genres"]
    
    # Ensure artist's genres exist
    if not artistGenres or artistGenres == None:
        return 0
    # Ensure track exists
    if not track["name"] or track["name"] == None:
        return 0
    # Get audio features
    features = getFeatures(track["id"])
    features = features[0]
    
    # Ensure features exist
    if not features or features == None:
        return 0
    
    # Delete any keys which are not going to be stored
    del features["type"]
    del features["id"]
    del features["uri"]
    del features["track_href"]
    del features["analysis_url"]
    for genre in artistGenres:
        
        # Get genre database
        dbGenres = db.execute("SELECT * FROM genres WHERE name = ?", genre)
        
        # If there is no genre currently, create a new row and add info
        if not dbGenres:
            db.execute("INSERT INTO genres (name, acousticness, danceability, duration_ms, energy, instrumentalness, key, liveness, loudness, mode, speechiness, tempo, time_signature, valence, count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                genre, features["acousticness"], features["danceability"], features["duration_ms"], features["energy"], features["instrumentalness"], features["key"], features["liveness"], features["loudness"], features["mode"], features["speechiness"],
                features["tempo"], features["time_signature"], features["valence"], 1)
        else:
            data = db.execute("SELECT * FROM genres WHERE name = ?", genre)
            new_data = {}
            
            # Adjust average of each feature in the genre
            for feature in features:
                new_data[feature] = ((data[0][feature] * data[0]["count"]) + features[feature]) / (data[0]["count"] + 1)
            new_data["count"] = data[0]["count"] + 1
            
            # Update database
            db.execute("UPDATE genres SET acousticness = ?, danceability = ?, duration_ms = ?, energy = ?, instrumentalness = ?, key = ?, liveness = ?, loudness = ?, mode = ?, speechiness = ?, tempo = ?, time_signature = ?, valence = ?, count = ? WHERE name = ?",
                new_data["acousticness"], new_data["danceability"], new_data["duration_ms"], new_data["energy"], new_data["instrumentalness"], new_data["key"], new_data["liveness"], new_data["loudness"], new_data["mode"], new_data["speechiness"],
                new_data["tempo"], new_data["time_signature"], new_data["valence"], new_data["count"], genre)
    return 1

# Function used to create initial database of genres
def fillDB():
    db = SQL("sqlite:///project.db")
    sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
    artistList = ["Taylor Swift", "Drake", "Bad Bunny", "BTS", "Ed Sheeran", "Justin Bieber", "Dua Lipa", "Ariana Grande", "Nicki Minaj", "Eminem", "Juice WRLD", "Olivia Rodrigo", "The Weeknd",
    "Doja Cat", "Lil Nas X", "Billie Eilish", "J Balvin", "Post Malone", "Adele", "Kanye West", "Jay Z", "Beyonce", "Harry Styles", "Kendrick Lamar", "Pop Smoke", "Kuldeep Manak", "Jazzy B",
    "Surjit Bindrakhia", "Sidhu Moose Wala", "Karan Aujla", "Diljit", "Amrinder Gill", "AP Dhillon", "Babbu Mann", "Imran Khan", "Beethoven", "John Legend", "Mariah Carey", "John Lennon",
    "Ozzy Osborne", "Metallica", "Queen", "Led Zeppelin", "Garth Brooks", "Michael Jackson", "Billy Joel", "Shakira", "Elton John", "Aerosmith", "Madonna", "Tupac", "Backstreet Boys",
    "Blake Shelton", "Johnny Cash", "Keith Urban", "Arjit Singh", "Elvis Presley", "Coldplay", "Imagine Dragons", "Sia", "Shawn Mendes", "Khalid", "Selena Gomez", "Miley Cyrus", "Huey Lewis", 
    "Katy Perry", "Daft Punk", "Avicii", "Twenty One Pilots", "The Chainsmokers", "Jassi Gill", "Guru Randhawa", "Bruno Mars", "Harry Styles", "Alicia Keys", "SZA", "Cardi B",
    "Tyga", "Maluma", "Anuel AA", "Alan Walker", "Swedish House Mafia", "Grimes", "Skrillex", "System of a Down", "The Beatles", "Pitbull", "Janet Jackson", "Stevie Wonder", "One Direction"]
    seenIDs = db.execute("SELECT id FROM artists")
    seen = set()
    for seenID in seenIDs:
        seen.add(seenID["id"])
    for artistName in artistList:
        artists = sp.search(artistName, type='artist')
        artists = artists["artists"]["items"]
        for artist in artists:
            if not artist["id"] or artist["id"] == None:
                continue
            if artist["id"] not in seen:
                db.execute("INSERT INTO artists (id, name) VALUES (?, ?)", artist["id"], artist["name"])
                seen.add(artist["id"])
                artistID = artist["id"]
                artistGenres = artist["genres"]
                if not artistGenres or artistGenres == None:
                    continue
                albums = sp.artist_albums(artistID, limit=50)
                if not albums or albums == None:
                    continue
                albums = albums["items"]
                unique = set()
                for album in albums:
                    if not album["name"] or album["name"]  == None:
                        continue
                    if album["name"].lower not in unique:
                        unique.add(album["name"].lower)
                        albumID = album["id"]
                        albumTracks = sp.album_tracks(albumID)
                        if not albumTracks or albumTracks == None:
                            continue
                        albumTracks = albumTracks["items"]
                        duplicate = set()
                        for track in albumTracks:
                            if not track["name"] or track["name"] == None:
                                continue
                            if track["name"].lower not in duplicate:
                                duplicate.add(track["name"].lower)
                                features = getFeatures(track["id"])
                                if not features[0] or features[0] == None:
                                    continue
                                features = features[0]
                                del features["type"]
                                del features["id"]
                                del features["uri"]
                                del features["track_href"]
                                del features["analysis_url"]
                                for genre in artistGenres:
                                    dbGenres = db.execute("SELECT * FROM genres WHERE name = ?", genre)
                                    if not dbGenres:
                                        db.execute("INSERT INTO genres (name, acousticness, danceability, duration_ms, energy, instrumentalness, key, liveness, loudness, mode, speechiness, tempo, time_signature, valence, count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                            genre, features["acousticness"], features["danceability"], features["duration_ms"], features["energy"], features["instrumentalness"], features["key"], features["liveness"], features["loudness"], features["mode"], features["speechiness"],
                                            features["tempo"], features["time_signature"], features["valence"], 1)
                                    else:
                                        data = db.execute("SELECT * FROM genres WHERE name = ?", genre)
                                        new_data = {}
                                        for feature in features:
                                            new_data[feature] = ((data[0][feature] * data[0]["count"]) + features[feature]) / (data[0]["count"] + 1)
                                        new_data["count"] = data[0]["count"] + 1
                                        db.execute("UPDATE genres SET acousticness = ?, danceability = ?, duration_ms = ?, energy = ?, instrumentalness = ?, key = ?, liveness = ?, loudness = ?, mode = ?, speechiness = ?, tempo = ?, time_signature = ?, valence = ?, count = ? WHERE name = ?",
                                            new_data["acousticness"], new_data["danceability"], new_data["duration_ms"], new_data["energy"], new_data["instrumentalness"], new_data["key"], new_data["liveness"], new_data["loudness"], new_data["mode"], new_data["speechiness"],
                                            new_data["tempo"], new_data["time_signature"], new_data["valence"], new_data["count"], genre)
    return 1
                                    
                                    
                        
    
# Genre linked to arist
# Get artists
# Get artists genres
# Get songs from artist
# Get audio features of each song
# Aggregate audio features and link them to each genre (put info into database)
# Repeat for multiple artsts
# Give each genre some food/cuisine/meal

# For a given song (input)
# Find closest match of audio features in the artists genres
# Output food based on genre (base)
# Output food based on genre and some other features (better)
# Output food based on genre, some other features, and user feedback (best)

# Databases
# Genres
#   id, name, acousticness, danceability, duration_ms, energy, instrumentalness, key(mode), liveness, loudness, mode(mode), speechiness, tempo, time_signature(mode), valence, count


# CREATE TABLE genres (id INTEGER NOT NULL, name TEXT NOT NULL, acousticness INTEGER NOT NULL, danceability INTEGER NOT NULL, duration_ms INTEGER NOT NULL, energy INTEGER NOT NULL, instrumentalness INTEGER NOT NULL, key INTEGER NOT NULL, liveness INTEGER NOT NULL, loudness INTEGER NOT NULL, mode INTEGER NOT NULL, speechiness INTEGER NOT NULL, tempo INTEGER NOT NULL, time_signature INTEGER NOT NULL, valence INTEGER NOT NULL, count INTEGER NOT NULL, PRIMARY KEY(id));

# CREATE TABLE artists (id INTEGER NOT NULL, name TEXT NOT NULL, PRIMARY KEY(id));
