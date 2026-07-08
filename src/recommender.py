from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import csv

@dataclass
class Song:
    """Represents a song and its attributes."""
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """Represents a user's taste preferences."""
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

class Recommender:
    """OOP implementation of the recommendation logic."""
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Returns the top k recommended Song objects based on user preferences."""
        # Using the same logic as our functional approach below
        user_dict = {
            "genre": user.favorite_genre,
            "mood": user.favorite_mood,
            "energy": user.target_energy
        }
        
        scored_songs = []
        for song in self.songs:
            # Convert dataclass to dict for the score_song function
            song_dict = song.__dict__
            score, _ = score_song(user_dict, song_dict)
            scored_songs.append((song, score))
            
        ranked_songs = sorted(scored_songs, key=lambda x: x[1], reverse=True)
        return [song for song, score in ranked_songs][:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Returns a string explanation of why a song was recommended."""
        user_dict = {"genre": user.favorite_genre, "mood": user.favorite_mood, "energy": user.target_energy}
        _, reasons = score_song(user_dict, song.__dict__)
        return ", ".join(reasons)

def load_songs(csv_path: str) -> List[Dict]:
    """Loads songs from a CSV file into a list of dictionaries."""
    print(f"Loading songs from {csv_path}...")
    songs = []
    with open(csv_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Convert string numbers to floats/ints for scoring math
            row['id'] = int(row['id'])
            row['energy'] = float(row['energy'])
            row['tempo_bpm'] = float(row['tempo_bpm'])
            row['valence'] = float(row['valence'])
            row['danceability'] = float(row['danceability'])
            row['acousticness'] = float(row['acousticness'])
            songs.append(row)
            
    return songs

def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """Scores a single song against user preferences and returns the score and reasons."""
    score = 0.0
    reasons = []

    # 1. Genre Match (+2.0 points)
    if song.get("genre") == user_prefs.get("genre"):
        score += 2.0
        reasons.append("Matched genre (+2.0)")

    # 2. Mood Match (+1.0 point)
    if song.get("mood") == user_prefs.get("mood"):
        score += 1.0
        reasons.append("Matched mood (+1.0)")

    # 3. Energy Proximity (Up to +1.0 point)
    target_energy = user_prefs.get("energy", 0.5)
    song_energy = song.get("energy", 0.5)
    energy_proximity = 1.0 - abs(target_energy - song_energy)
    
    score += energy_proximity
    reasons.append(f"Energy proximity {song_energy} vs {target_energy} (+{energy_proximity:.2f})")

    return float(score), reasons

def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """Calculates scores for all songs and returns the top k ranked results."""
    scored_items = []
    
    # The Loop: Judge every individual song
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        # Join the list of reasons into a single readable string
        explanation = ", ".join(reasons)
        scored_items.append((song, score, explanation))
        
    # The Output: Rank using sorted() and a lambda function to target the score (index 1)
    ranked_songs = sorted(scored_items, key=lambda item: item[1], reverse=True)
    
    # Return exactly k results using list slicing
    return ranked_songs[:k]