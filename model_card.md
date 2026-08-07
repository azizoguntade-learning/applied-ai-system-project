# 🎧 Model Card: Music Recommender

## 1. Model Name

CloudStreamerr.set

---

## 2. Intended Use and Non-Intended Use

This system suggests songs based on a free-text description of what you want to
hear — genre, mood, energy level, and whether you want something acoustic. It is
built as a classroom tool for learning how recommendation algorithms work and
how an AI system can check its own output.

It is **not** built for a real music app. Do not use it for diverse music
discovery. It knows 17 songs, understands only English keywords, and cannot
handle complex or mixed tastes.

---

## 3. Algorithm Summary

Every song is scored against the parsed request, and the highest scores win:

- **+2.0** if the genre matches exactly
- **+1.0** if the mood matches exactly
- **up to +1.0** for energy proximity: `1.0 - |requested − song|`
- **−1.0 to +1.0** for acoustic fit — *only* when the user asked for acoustic:
  `(acousticness − 0.5) × 2`

The acoustic term is centred rather than a bonus so that asking for acoustic can
*demote* a non-acoustic track, not merely fail to promote it. Maximum score is
4.0 for a request with no acoustic preference, and 5.0 for one with it.

A **critic** then re-reads the top result against the request and can trigger one
retry with the genre constraint dropped. See [README §3](README.md).

---

## 4. Data Used

The catalog is very small: 17 made-up songs, spanning pop, lofi, rock, ambient,
jazz, synthwave, indie pop, classical, country, EDM, R&B, heavy metal, reggae,
and blues, with moods from happy to aggressive. The dataset has strict limits and
misses huge categories including hip-hop, Afrobeats, K-pop, and most non-Western
music.

---

## 5. Strengths

The system works well when a request maps cleanly onto the catalog's attributes:
"chill lofi" and "high-energy pop" both return exactly what you would expect. The
arithmetic separates slow, quiet songs from loud, fast ones reliably, and every
recommendation comes with the exact reasons and point values behind it — there is
no unexplainable output anywhere in the system.

The critic adds a second strength: when the scoring rule and the request
disagree, the system notices and says so instead of returning a confident wrong
answer.

---

## 6. Limitations and Biases

**The genre weight creates a filter bubble.** A genre match is worth 2.0 points —
half the base score. This means the system will almost never surface a song from
a different genre, and will ignore a great track whose mood and energy are
perfect simply because the genre tag is wrong. That weight was not an objective
truth; it was a subjective design choice I made as the programmer, and it
fundamentally shapes every result.

**The critic mitigates this bias but does not remove it.** It only fires when the
top pick visibly contradicts the request, and its only repair is dropping the
genre filter entirely. A request that is *mildly* over-narrowed still passes.

**The catalog is tiny and skewed.** 17 songs cannot represent musical taste. The
genres present are overwhelmingly Western, so any request outside that range
falls back to energy matching and returns something arbitrary. `high energy
polka` returns a high-energy song that is not polka, because no polka exists.

**Routing is keyword-based and English-only.** The router matches literal
substrings against catalog vocabulary. "Upbeat" and "energetic" work because they
are in a hardcoded list; a synonym outside that list is silently ignored. Non-
English requests get no taste signal at all. There is no understanding of lyrics,
language, culture, or context.

**Guardrails are regex-based and are not a complete defense.** They stop the
obvious cases — "ignore previous instructions", fake `<system>` tags, developer-
mode requests — but a determined attacker can rephrase around a pattern list.
They are a cheap first filter, not a security boundary.

**The off-topic filter is brittle in a specific, documented way.** The word
"code" is on the off-topic list, so "lofi to code to" is a legitimate request
that comes within one word of being blocked. It survives only because "lofi" is
also matched as catalog vocabulary. A user asking for "music to code to" — with
no genre named — *would* be wrongly rejected.

**Everything is deterministic, which is a limitation as well as a strength.** The
same input always produces the same output. There is no personalisation, no
learning from feedback, and no notion of novelty or serendipity — arguably the
most valuable things a real recommender provides.

---

## 7. Could This Be Misused, and How Would You Prevent That?

**Repurposing it as a general-purpose chatbot.** The most likely misuse is
prompt injection to make the system answer questions it was never meant to
answer. *Prevention:* `validate_input()` runs before any other component and
blocks injection patterns and off-topic requests outright — verified at 8/8 on
the adversarial golden cases. *Residual risk:* the pattern list is finite and a
novel phrasing will get through. The deeper mitigation is architectural rather
than pattern-based: there is no language model in the request path, so even a
successful injection has nothing to hijack. The system can only ever return
songs from a fixed CSV.

**Manipulating the catalog to promote content.** Anyone who can edit
`data/songs.csv` can inflate a song's attributes so it wins every ranking — the
recommender equivalent of payola. *Prevention:* the critic checks results against
the request rather than trusting the score, so a song with implausible attributes
gets flagged when it fails to match; and the golden set pins expected results for
23 requests, so a manipulated catalog fails the evaluation. *Residual risk:*
neither defense covers a subtle change to a song not referenced by a golden case.
A production system would need signed data and provenance tracking.

**Cost and denial-of-service abuse.** An agentic system with an unbounded repair
loop can be made to spin indefinitely. *Prevention:* `MAX_INPUT_LENGTH = 500`
caps input size, `MAX_CRITIC_RETRIES = 1` bounds the repair loop by construction,
and there is no external API to run up a bill against.

**Over-trusting the output.** The most realistic harm is someone presenting a
17-song classroom toy as a real recommendation engine. *Prevention:* this model
card, the "not built for a real music app" statement in §2, and the fact that
every recommendation shows its own arithmetic — a user can see that "Matched
genre (+2.0)" is the whole reason for a pick and judge it accordingly.

---

## 8. Evaluation Process

I tested several profiles and then built a repeatable harness rather than relying
on spot checks. `eval/run_eval.py` runs 23 labelled cases across six categories —
taste matching, critic repairs, low-confidence requests, and three guardrail
classes — and prints a pass/fail report with reliability metrics. It exits
non-zero on failure, so a regression fails the build rather than being noticed by
eye.

Straightforward requests behaved as expected: "High-Energy Pop" and "Chill Lofi"
both returned exactly the right tracks. The interesting cases were the failures.
An "Intense Ambient" request returned slow ambient songs anyway, because the 2
points for the ambient genre were too strong to overcome — this is now the
motivating example for the critic, and it is fixed. I also noticed "Gym Hero"
appearing for a "Happy Pop" user: it wins on genre and energy while completely
ignoring that its mood is wrong.

Current results: 23/23 cases pass, 8/8 adversarial inputs blocked, the critic
flags 3 cases and repairs 2 of them, mean routing confidence 0.79. A human still
reads the report and the traces to judge whether a flagged case was *genuinely*
wrong — the harness measures agreement with my labels, not correctness.

---

## 9. What Surprised Me While Testing Reliability

**A feature can be fully "implemented" and completely inert.** `likes_acoustic`
existed on two dataclasses, was parsed by the router, and was documented in the
README — but nothing ever read it. Every individual piece looked right. Only a
test that asserted on *results* rather than on the field's existence caught it.

**My first fix for that bug also did nothing, and passed a test.** I added
acousticness as a bonus and wrote a test asserting acoustic songs score higher.
The test passed. The rankings did not move at all, because adding a non-negative
number to every candidate shifts all scores and reorders nothing. A bonus can
never demote. I only found this by printing the actual top 3 before and after.

**Two of my own test expectations were wrong, not the system.** I asserted that
`happy classical` would decline a repair. It repairs — correctly, because the
only classical track is melancholic, so widening genuinely helps. I had encoded
an assumption as a test and briefly believed the code was broken.

**The evaluation harness immediately found a bug in the code it was written to
grade.** `PipelineResult` kept only the critic's *final* verdict, so a successful
repair erased the fact that the critic had ever objected. The summary printed a
self-contradictory "flagged 0 cases, repaired 2 cases".

**A test-isolation bug that would have failed silently.** `configure_logging()`
sets `propagate = False` so the app never double-prints. Had any test triggered
it, every later `caplog` assertion would have captured nothing and passed
vacuously — tests that appear green while checking nothing at all.

The through-line: every one of these was invisible to code review and visible
only by measuring output.

---

## 10. Collaboration With AI

I used an AI assistant throughout, mostly for refactoring, test design, and
reviewing my own reasoning. Two examples, one of each kind.

### A suggestion that was genuinely helpful

Early on, the recommender was one module doing everything. The AI proposed
splitting it into single-responsibility agents with a thin orchestrator —
`models` / `scoring` / `guardrails` / `agents` / `orchestrator` — with scoring as
pure functions taking no I/O. I took it mostly on faith at the time.

It paid off later in a way I could not have predicted. When I added the critic —
the project's core feature — it dropped in as one new class and one new branch in
the orchestrator, touching nothing else. Because scoring was already pure, I could
call it twice with two different intents to implement the replan. If the logic had
still been one function, the critic would have been a rewrite rather than an
addition.

### A suggestion that was flawed

The same assistant added a `likes_acoustic` field to `Intent` and `UserProfile`,
wrote router logic to detect words like "acoustic" and "unplugged", and
documented the feature in the README — but **never wired it into `score_song`**.
The result was worse than an obvious bug: the feature looked complete in four
separate places, so nothing prompted me to check it. "Something acoustic and
relaxed" cheerfully returned a track with 0.40 acousticness above one with 0.95.
It shipped silently broken and stayed that way across multiple commits.

A smaller instance of the same failure: `requirements.txt` listed `pandas` and
`streamlit`, neither of which is imported anywhere — `data_loader.py` uses the
standard-library `csv` module. Anyone following the setup instructions would have
installed two large packages for nothing, and the phantom dependencies implied
capabilities the project did not have.

**What I changed as a result.** I stopped accepting "the code exists" as evidence
that a feature works. Every behavioural claim in this project is now backed by a
test that asserts on *output* — which is exactly how I found that my own first
fix for the acoustic bug was inert, and how the evaluation harness found a
reporting bug in the pipeline. AI assistance made me faster at producing code and
no faster at knowing whether it was right; verification is the part that does not
delegate.

---

## 11. Ideas for Improvement

If I kept developing this, I would let the user decide how much genre matters
instead of forcing the 2-point rule, and add collaborative filtering — suggesting
songs based on what similar users like — to break the filter bubble properly
rather than only repairing it after the fact. I would also give the critic more
than one relaxation to choose from, and grow the catalog enough that the
evaluation metrics mean something statistically.
