"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

from recommender import load_songs, recommend_songs

def main() -> None:
    # 1. Load the data
    songs = load_songs("data/songs.csv") 
    print(f"Loaded songs: {len(songs)}\n")

    # 2. Define multiple target user profiles, including adversarial cases
    test_profiles = {
        "High-Energy Pop": {"genre": "pop", "mood": "happy", "energy": 0.9},
        "Chill Lofi": {"genre": "lofi", "mood": "chill", "energy": 0.35},
        "Deep Intense Rock": {"genre": "rock", "mood": "intense", "energy": 0.85},
        "Adversarial (Conflicting)": {"genre": "ambient", "mood": "intense", "energy": 0.95},
        "Adversarial (Unknown Genre)": {"genre": "country", "mood": "happy", "energy": 0.6}
    }

    # 3 & 4. Loop through each profile, rank recommendations, and print results
    for profile_name, prefs in test_profiles.items():
        print(f"{'='*50}")
        print(f"Evaluating Profile: {profile_name}")
        print(f"Target: genre={prefs['genre']}, mood={prefs['mood']}, energy={prefs['energy']}")
        print(f"{'='*50}\n")

        recommendations = recommend_songs(prefs, songs, k=5)

        for i, rec in enumerate(recommendations, 1):
            # Unpack the tuple returned by recommend_songs
            song, score, explanation = rec
            
            # Clean, readable terminal formatting
            print(f"{i}. {song['title']} - Score: {score:.2f}")
            print(f"   Because: {explanation}\n")
            
        print("\n")

if __name__ == "__main__":
    main()