# 🎵 Music Recommender Simulation

## Project Summary

In this project you will build and explain a small music recommender system.

Your goal is to:

- Represent songs and a user "taste profile" as data
- Design a scoring rule that turns that data into recommendations
- Evaluate what your system gets right and wrong
- Reflect on how this mirrors real world AI recommenders

Replace this paragraph with your own summary of what your version does.

---

## How The System Works

The recommendation pipeline processes user preferences and song metadata to calculate mathematical matching scores, yielding a ranked list of top recommendations.

- Song Features: Each Song in the catalog is represented by categorical features (genre, mood) and numerical audio features (energy, tempo_bpm, valence, danceability, acousticness).

- User Profile: The UserProfile stores the user's target preferences, specifically their favorite_genre, favorite_mood, a continuous target_energy preference (0.0 to 1.0), and a boolean for likes_acoustic.

Computing the Score: The Recommender evaluates each song against the user's profile and assigns a total score (out of a maximum 4.0 points):

-  +2.0 points for a direct genre match.

-  +1.0 point for a direct mood match.

-  Up to +1.0 point for energy proximity (calculated as 1.0 - abs(target_energy - song_energy)).

Choosing Recommendations: The system iterates through the entire catalog, scores each song, sorts the list in descending order by total score, and returns the top K (e.g., top 5) highest-scoring tracks.


---

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python -m src.main
```

### Running Tests

Run the starter tests with:

```bash
pytest
```

You can add more tests in `tests/test_recommender.py`.

---

## Sample Recommendation Output

Paste a sample of your recommender's output here as a text block so a reader can see what it produces:

```
# e.g.:
# User profile: genre=indie, mood=chill, energy=low
# Recommendations:
#   1. ...
#   2. ...
#   3. ...
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or demo video link here -->

---

## Experiments You Tried

Use this section to document the experiments you ran. For example:

- What happened when you changed the weight on genre from 2.0 to 0.5
- What happened when you added tempo or valence to the score
- How did your system behave for different types of users

---

## Limitations and Risks

Summarize some limitations of your recommender.

Examples:

- It only works on a tiny catalog
- It does not understand lyrics or language
- It might over favor one genre or mood

You will go deeper on this in your model card.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Write 1 to 2 paragraphs here about what you learned:

- about how recommenders turn data into predictions
- about where bias or unfairness could show up in systems like this



