# Demo Video — Recording Guide

A simple step-by-step script to record the required 1–2 minute demo video for the AI Python Engineering Assignment.

## Before you record (2 minutes of prep)

1. **Warm up the app** — start the local server and ask one dummy question first. This primes the free APIs so answers in the video stream fast instead of stalling:

   ```bash
   cd ~/Desktop/Projects/ConversAIlabsV1
   .venv/bin/uvicorn app.main:app --port 8123
   ```

2. Open http://localhost:8123, ask any question, and wait for it to finish.
3. Keep the project folder visible in a terminal (you will show the server command at the start of the video).
4. Have your screen recorder ready (OBS / SimpleScreenRecorder / Kazam).

## Video script (1–2 minutes, in this order)

### Step 1 — Show it running locally (5–10 sec)
- Terminal on screen showing the uvicorn server running (`Uvicorn running on http://0.0.0.0:8123`).
- Optional one-line narration: *"FastAPI server running locally; documents are embedded and stored in Qdrant Cloud, answers come from a free OpenRouter model."*

### Step 2 — Show the indexed corpus (5 sec)
- Browser → http://localhost:8123
- Point at the top badge: **"28 documents · 5503 chunks"** — proves all supplied PDFs were parsed and indexed.

### Step 3 — Question 1 with citations (20–30 sec)
- Ask: **"Is the right to privacy a fundamental right under the Indian Constitution?"**
- Wait for the streaming answer, then **click the `[1]` marker** in the answer so it jumps to the source card.
- Point at the source card: document `23_Justice_K_S_Puttaswamy…`, Page 7, retrieved text — this demonstrates "citation = document name + page number + snippet".

### Step 4 — Question 2 (20–30 sec)
- Ask: **"Is it mandatory for the police to register an FIR when a cognizable offence is reported?"**
- Show the citation: `29_Lalita_Kumari…`, **Page 19** — the snippet literally says *"shall… mandatory to register an FIR"*, a perfect example of the cited text supporting the answer.

### Step 5 — Question 3 (20–30 sec)
- Ask: **"What is the permissible limit of reservation under the Constitution?"**
- Show the `18_Indra_Sawhney…` citations.

### Step 6 — Out-of-scope question (10 sec)
- Ask: **"What is the best recipe for chocolate cake?"**
- Show the amber refusal: *"The information is not available in the provided documents."* — no fabricated answer.

### Step 7 — Done
- Stop recording. Total ≈ 1.5–2 min.

## Pro tips

- **Slow first answer (30–60s)?** That is normal for free-tier APIs. Either trim the wait while editing, or pre-ask each question once during warm-up, then re-ask fresh for the video.
- **Citations on screen are mandatory** — always click the `[n]` marker so the source card (doc name + page + text) is visible. This is the 30% "Citation Accuracy" evaluation criterion.
- **No narration needed.** If you narrate, keep it to the 1–2 lines above.
- **Show the local machine, not the Render URL** — the assignment says *"running from your local machine"*. You may mention the live deployment at the end if you want.

## Checklist before submitting

- [ ] GitHub repo pushed with complete source code (done)
- [ ] README is 1 page: architecture, libraries, embedding model, assumptions, how to run (done)
- [ ] Demo video: 3 questions + citations + 1 out-of-scope refusal
