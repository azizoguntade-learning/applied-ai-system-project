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

    # 2. Define the target user profile
    user_prefs = {"genre": "pop", "mood": "happy", "energy": 0.8}
    print("# User profile: genre=pop, mood=happy, energy=0.8")
    print("# Recommendations:\n")

    # 3. Get the ranked recommendations
    recommendations = recommend_songs(user_prefs, songs, k=5)

    # 4. Print the results in a clean, readable format
    for i, rec in enumerate(recommendations, 1):
        # Unpack the tuple returned by recommend_songs
        song, score, explanation = rec
        
        # Clean, readable terminal formatting
        print(f"{i}. {song['title']} - Score: {score:.2f}")
        print(f"   Because: {explanation}")
        print()

if __name__ == "__main__":
    main()