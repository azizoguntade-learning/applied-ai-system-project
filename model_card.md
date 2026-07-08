# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

-  CloudStreamerr.set  

---

## 2. Intended Use and Non-Intended Use 

This system suggests songs based on your exact music taste. You tell it the genre, mood, and energy you want. It is built as a classroom tool to learn how recommendation algorithms work.

It is not built for a real music app. Do not use it for diverse music discovery. It only knows a few songs and cannot handle complex, mixed tastes.


---

## 3. Algorithm Summary  

The system uses a simple math formula to score songs. It looks at the song's data and your preferences.

- It adds 2 points if the genre matches exactly.

- It adds 1 point if the mood matches exactly.

- It looks at the song's energy. It adds up to 1 point if the energy is very close to what you asked for.
Finally, it adds up the points. The highest-scoring songs get recommended to you.

---

## 4. Data Used

The catalog is very small. It has about 17 made-up songs. It includes genres like pop, lofi, rock, and ambient. The moods go from happy to intense. The dataset has strict limits. It misses huge categories like hip-hop, classical, and global music.

---

## 5. Strengths  

The system works well if your taste perfectly matches the data. For example, it gives great results for "Chill Lofi" or "High-Energy Pop." The math easily separates slow, quiet songs from loud, fast songs.


---

## 6. Observed Behavior and Biases 

The system has a major bias: the genre score is too high. Genre makes up half of the total points. This creates a strict "filter bubble." The system will almost never suggest a song from a different genre. It will ignore a great song just because it has the wrong genre tag, even if the mood and energy are perfect.

---

## 7. Evaluation Process  

I tested several user profiles to see what the system would do. I tried "High-Energy Pop" and "Chill Lofi." The results made sense. The math easily pushed upbeat songs to the top for pop, and slow acoustic tracks to the top for lofi.

I also tested a tricky profile: a user wanting an "Intense Ambient" track with high energy. The system failed here. It gave them slow ambient songs anyway. The 2 points for the ambient genre were just too strong to overcome. I also noticed the intense song "Gym Hero" showed up for a "Happy Pop" user. It won points for being pop and high energy, completely ignoring the fact that the mood was wrong.

---

## 8. Ideas for Improvement 

If I kept developing this, I would change two main things. First, I would let the user decide how important genre is, instead of forcing the 2-point rule. Second, I would add collaborative filtering. This means suggesting songs based on what similar users like. It would help break the filter bubble.
---

## 9. Personal Reflection  

My biggest learning moment was seeing how recommenders turn human feelings into math. I had to change a "chill vibe" into a measurable distance score. I was surprised that such simple addition and subtraction could actually feel like real recommendations.

Using AI tools helped me write the code faster, but I had to double-check its math logic to make sure the final scores were actually sorting correctly.

This project also showed me how easily bias enters algorithmic systems. The decision to make a genre match worth 2 points wasn't an objective truth. It was just a subjective design choice I made as the programmer. That single choice fundamentally altered the output and created an artificial filter bubble. Next time, I would try adding more features like danceability to make the suggestions feel much more natural.