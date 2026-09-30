# App-English-Test — CEST Practice Simulator

Private, desktop-first web application for personal preparation inspired by the published structure, task types, timing, and assessment constructs of the **Cambridge English Skills Test (CEST) General** across **Reading, Listening, and Writing (A1–C1)**.

> **Important Legal & Product Positioning**
> This project is a **private practice simulator** inspired by publicly documented CEST General test structures and criteria. It is **not** an official Cambridge product, does not reproduce proprietary item banks, and does not produce official Cambridge or Cambridge English Scale scores.

---

## Features Implemented (100% PRD Aligned)

1. **Dashboard (Indonesian UI + English Test Content)**:
   - Displays current estimated CEFR levels (`A1`–`C1`) for **Reading**, **Listening**, and **Writing**.
   - Quick-start actions for **Full Test Simulation** and individual skill **Practice Mode**.
   - Recent Results table & dynamic Focus Areas (`Area yang Perlu Dilatih`) without gamified streaks or progress charts.
2. **Reading Module (All 9 Task Types, Adaptive 1PL IRT + EAP)**:
   - `RT-01` Open Cloze (5 gaps)
   - `RT-02` Multiple-choice Cloze (5 gaps)
   - `RT-03` Cross Text Matching (4 texts A–D)
   - `RT-04` Discrete Cloze (1 gap)
   - `RT-05` Discrete with a Graphic (Notices, Text Messages, Emails)
   - `RT-06` Gapped Text — Sentences (5 gaps, 8 sentence options)
   - `RT-07` Gapped Text — Paragraphs (5 gaps, 6 paragraph options)
   - `RT-08` Comprehension — 5 Items
   - `RT-09` Comprehension — 2 Items
3. **Listening Module (`LT-01`, `LT-02`, `LT-03` + Local WAV Audio Engine)**:
   - 1-item, 2-item, and 5-item comprehension tasks across monologues, dialogues, and 3-speaker discussions.
   - **Full Test Simulation**: Strict state machine (`PREVIEW` → `PLAYBACK_1` → `SHORT_TRANSITION` → `PLAYBACK_2` → `ANSWER`) playing audio twice automatically with pause, replay, and seek disabled and transcript hidden.
   - **Practice Mode**: Full pause, replay, and seek controls, plus transcript & explanation reveal after answering.
4. **Writing Module (Part 1 Email & Part 2 Wider-Audience Writing + AI Evaluation)**:
   - **Part 1 — Email**: Minimum 50 words, recommended ~15 minutes, 3 required bullet points.
   - **Part 2 — Wider-audience writing (Article / Review / Web Post)**: Minimum 180 words, recommended ~30 minutes, 3 required bullet points.
   - Shared 45-minute authoritative countdown timer in Full Simulation.
   - Structured AI evaluation across **Communicative Achievement (0–5)**, **Organisation (0–5)**, and **Language (0–5)**, CEFR calibration, bilingual feedback (English + Indonesian), and evidence-based sentence corrections (`Original` → `Suggested` + `Why`).
5. **Content Studio**:
   - **Bank Health**: Monitors approved item units across `A1`–`C1` for Reading, Listening, and Writing.
   - **Generate Bank**: Generates original items into `REVIEW` status with automatic structural, answer-key, and distractor validation.
   - **Review Queue & Approved Bank**: Preview, Approve, Reject, Regenerate, and Edit metadata/explanations (with automatic version incrementing).
6. **Extensible AI Provider Architecture**:
   - Supports **LM Studio (Local)**, **OpenAI API**, **Gemini API**, and a **Built-in Local Rubric Engine** with automatic retry backoff and session-level provider locking.

---

## Running with Docker Compose (PostgreSQL + FastAPI + Next.js)

```bash
docker compose up --build
```

- **Frontend UI**: [http://127.0.0.1:3000](http://127.0.0.1:3000)
- **Backend API & Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Running Directly on Local Host (Without Docker)

### 1. Start the FastAPI Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Start the Next.js Frontend
```bash
cd frontend
npm install
npm run dev
```

### 3. Run Unit & Integration Tests
```bash
cd backend
python -m pytest tests/ -v
```
