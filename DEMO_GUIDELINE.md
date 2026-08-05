# Demo Video Guideline (1–2 minutes)

This guide walks you through recording your assignment demo video using the deployed app.

## The essentials (assignment requirement)

The video must show:
1. The app running
2. **At least 3 questions** answered from the supplied PDFs
3. The answers **and their citations** (document name + page number + retrieved text)
4. **1 question** whose answer is NOT in the PDFs — the app must say the info is unavailable

Video should be 1–2 minutes. No narration needed, but a short explanation helps.

---

## Step 0 — Before you record (5 minutes of prep)

- [ ] Open the app in Chrome: **https://pdf-rag-assistant-pxpa.onrender.com**
- [ ] **Warm it up first**: ask any question (e.g. "What is the right to privacy?") and wait for the full answer.
      The free Render tier sleeps after ~15 min idle — the first request takes 30–60s. You don't want that
      happening during the recording.
- [ ] Close all other tabs and any notification popups. Make the window fullscreen.
- [ ] Have your screen recorder ready:
      - Linux Mint: press **Super + Shift + R** (built-in GNOME recorder), or
      - OBS Studio (free) if you want to pause/resume and trim.
- [ ] Test the recorder for 10 seconds before starting the real take.

> Tip: each answer takes 15–45 seconds (free-tier LLM). That's longer than it looks.
> Pause the recording while waiting, or trim the silent parts afterward. Total video must stay under 2 minutes.

---

## Step 1 — Intro (10 seconds)

- Open the app URL.
- Show the top bar: it displays **"28 documents · 5,503 chunks"** and **"Qdrant connected"**.
- Optional one-liner (no need for fancy explanation): *"This is a RAG app that answers questions from
  28 Supreme Court judgments, with citations. Built with FastAPI, Qdrant and OpenRouter free models."*

## Step 2 — Question 1: Privacy (Puttaswamy) (~30 sec)

Type (or paste): **"Is the right to privacy a fundamental right under the Indian Constitution?"**

- Let the answer stream in (this shows the token-by-token streaming).
- After the answer, **scroll down to the SOURCES cards**.
- Point at / hover over the citation number **[1]** in the answer — it jumps to the source card showing:
  - Document name: `23_Justice_K_S_Puttaswamy_Retd_and_Anr...`
  - Page number: e.g. **Page 7**
  - Retrieved text snippet

## Step 3 — Question 2: FIR registration (Lalita Kumari) (~30 sec)

Type: **"Is it mandatory for the police to register an FIR when a cognizable offence is reported?"**

- Expected: "Yes… the police officer **shall** register an FIR…"
- Show the source card with **Page 19** — its retrieved text explicitly says *"the use of the word 'shall' in
  Section 154(1)… mandatory to register an FIR"*. This is your strongest citation — make sure it's visible on screen.

## Step 4 — Question 3: Reservation limit (Indra Sawhney) (~30 sec)

Type: **"What is the permissible limit of reservation under the Constitution?"**

- Expected: a nuanced answer — no fixed ceiling, generally **not exceeding 50%**, with the 80% exception.
- Show the source cards (all from `18_Indra_Sawhney_...`).

## Step 5 — Out-of-scope question (~15 sec)

Type: **"What is the best recipe for chocolate cake?"**

- The app must answer: **"The information is not available in the provided documents."**
- Show that **no source cards** appear (proves it doesn't fabricate).
- If you have time, add: *"This is what happens when a question isn't in the PDFs."*

## Step 6 — Closing (5 seconds)

- Optional: *"Code and README are on GitHub: github.com/pramit-webdev/ConversAIlabsV1"* and/or show
  the repo page briefly.
- Stop recording.

---

## Timings cheat sheet

| Segment | What to show | Target time |
|---|---|---|
| Intro | URL + status bar (28 docs) | ~10s |
| Q1 | Privacy answer + citation card | ~30s |
| Q2 | FIR answer + Page 19 citation | ~30s |
| Q3 | Reservation answer + citations | ~30s |
| Q4 | "Not available" refusal, no sources | ~15s |
| Outro | GitHub link (optional) | ~5s |
| **Total** | | **~1:45** |

---

## If something goes wrong during recording

- **Answer says "not available" for a real question** — wait and re-ask (transient retrieval miss), or use
  one of the backup questions below.
- **429 / slow response** — free-tier rate limit; wait 30–60 seconds and re-ask. Don't record during the wait.
- **App is sleeping** — first request takes 30–60s; just wait it out (or trim it later).
- **Streaming looks stuck** — the free model can pause mid-stream; give it up to 10 seconds before re-asking.

### Backup questions (same documents, equally strong citations)

- "What did the Supreme Court hold in Maneka Gandhi about the procedure established by law under Article 21?" → Puttaswamy digest, ~page 128-130
- "Can the state impose a complete ban on the use of loudspeakers in a religious place?" → Common Cause
- "Is the right to life and personal liberty protected by Article 21?" → multiple judgments

---

## After recording — final submission checklist

- [ ] Video is 1–2 minutes and shows all 4 required elements
- [ ] Citations are visible (document name + page number + text) for every answer
- [ ] GitHub repo is public with the final code: https://github.com/pramit-webdev/ConversAIlabsV1
- [ ] README is the 1-page version (already done)
- [ ] Bonus: title the video file something clear, e.g. `demo.mp4`, and keep it under 50 MB

Good luck!
