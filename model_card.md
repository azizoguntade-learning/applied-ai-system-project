# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

-  CloudStreamerr.set  

---

## 2. Intended Use  

This recommender is designed to generate music track suggestions based on a user's explicit structural audio    preferences. It assumes the user knows exactly what genre, mood, and energy level they are looking for. It is primarily built for classroom exploration and simulation rather than a commercial production environment.

---

## 3. How the Model Works  

The system uses a mathematical content-based filtering approach. It takes a user's target preferences (genre, mood, and energy) and compares them against the metadata of each song in our catalog. It awards +2.0 points for an exact genre match, +1.0 point for an exact mood match, and up to +1.0 point based on how close the song's energy level is to the user's target energy. The songs with the highest total scores are ranked and recommended.

---

## 4. Data  

The model uses a tiny, custom dataset of roughly 10 to 17 fictional songs. The catalog features core genres like pop, lofi, rock, and ambient, with moods ranging from happy to chill to intense. Because the dataset is so small, vast sections of musical taste (like hip-hop, classical, or global music) are underrepresented or entirely missing, limiting the system's ability to serve a diverse global user base.

---

## 5. Strengths  

The system works exceptionally well for users whose tastes perfectly align with the core clusters in the dataset, such as "Chill Lofi" or "High-Energy Pop." The mathematical scoring reliably captures these distinct archetypes, accurately pushing upbeat pop to the top of one list and slow, acoustic loops to the top of another.


---

## 6. Limitations and Bias 

The current scoring logic heavily over-prioritizes the categorical genre match by assigning it 50% of the maximum possible score (+2.0 out of 4.0). This creates a strict "filter bubble" where the system will almost never recommend a track outside of the user's requested genre, even if an out-of-genre song perfectly matches their desired mood and energy level. Furthermore, because the dataset is extremely small and skews towards pop and lofi, users requesting niche or missing genres (like country or classical) will receive disjointed recommendations simply because the system lacks the inventory to serve them properly.

---

## 7. Evaluation  

I tested the recommender using a variety of profiles, including "High-Energy Pop", "Chill Lofi", "Deep Intense Rock", and an adversarial profile with conflicting traits ("Ambient", "Intense", "0.95 energy").

The most surprising result came from the conflicting adversarial profile: the system still highly prioritized standard, low-energy ambient tracks simply because the +2.0 genre weight mathematically overpowered the extreme energy and mood mismatches.

Profile Comparisons:

- High-Energy Pop vs. Chill Lofi: The pop profile heavily prioritizes upbeat tracks like "Sunrise City", while the lofi profile reliably filters down to slow, acoustic tracks like "Library Rain". This makes perfect sense because both the genre (+2.0) and energy proximity (+1.0) naturally align with these two opposite poles in our dataset.

- Why "Gym Hero" shows up for "Happy Pop": "Gym Hero" is an intense pop song, not a happy one. However, it still shows up near the top of the list for users wanting "Happy Pop" simply because it shares the "pop" genre (+2.0 points) and has a very high energy score that stays close to the user's target. The system essentially decides that being a high-energy pop song is "close enough," completely ignoring the emotional mismatch in the mood.



---

## 8. Future Work  

Future improvements would include dynamically adjusting the category weights based on the user's flexibility, rather than strictly enforcing a +2.0 genre bonus. We could also introduce collaborative filtering elements to break the filter bubble, allowing the system to recommend songs outside of the user's explicitly stated metadata if similar users enjoyed them.

---

## 9. Personal Reflection  

Building this simulation demonstrated how recommenders must reduce abstract human preferences (like a "chill vibe") into measurable, mathematical distances. It also highlighted where bias easily enters algorithmic systems: the decision to weight a genre match at +2.0 points wasn't an objective truth, but rather a subjective design choice by the programmer that fundamentally altered the output and created an artificial filter bubble.