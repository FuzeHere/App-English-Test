# PRD — CEST Practice Simulator

**Document status:** Draft v1.0 — implementation-ready baseline  
**Date:** 2026-09-30  
**Product name:** CEST Practice Simulator  
**Product type:** Private, desktop-only web application  
**Primary purpose:** Personal preparation before taking the Cambridge English Skills Test (CEST) General  
**Target user:** Single private user (owner of the application)  
**Scope of skills:** Reading, Listening, Writing  
**Speaking:** Out of scope for MVP  
**Deployment:** Docker on the user's PC  
**AI providers:** OpenAI API, Gemini API, LM Studio (local)  
**Authentication:** None for normal use  

> **Important product/legal positioning**
>
> This project is a **practice simulator inspired by the published structure, task types, timing and assessment constructs of Cambridge English Skills Test General**. It is **not an official Cambridge product**, does not reproduce Cambridge's proprietary item bank, does not use official test questions, and must not claim that its scores are official Cambridge scores or Cambridge English Scale scores.
>
> All question texts, audio scripts, graphics and writing prompts generated for this application must be original content. The UI may reproduce functional patterns needed for an exam-like experience, but must not copy Cambridge branding, logos, proprietary visual assets, or copyrighted sample-test content.

---

## 1. Executive Summary

CEST Practice Simulator is a private web application designed to let one user repeatedly practise the three CEST General skills that matter to this project:

1. Reading
2. Listening
3. Writing

The application has two primary modes:

- **Practice Mode** — relaxed learning-oriented mode. The user can practise a skill independently, receive explanations after answers, inspect listening transcripts after attempting a task, and receive automated AI feedback for Writing.
- **Full Test Simulation** — exam-oriented mode. The application simulates the timing and interaction style of the real test as closely as reasonably possible using publicly documented information. Reading and Listening use an adaptive engine; Writing uses two timed tasks.

The adaptive modules use a **Rasch / 1-parameter Item Response Theory (1PL IRT)** model with an EAP ability estimator. The engine selects the next item based on estimated ability and item information while also enforcing content-balance and exposure rules. This is a **simulation design choice**, not a claim that it reproduces Cambridge's proprietary adaptive algorithm.

Writing is evaluated automatically by a configurable AI provider using a rubric inspired by the officially published Cambridge Writing assessment dimensions: **Communicative Achievement, Organisation, and Language**. The simulator additionally provides diagnostic information about grammar, vocabulary, coherence, task completion and common errors, but these diagnostics are separate from the core rubric score.

The application stores practice/test history locally in its PostgreSQL database and does not require user accounts. LM Studio can run locally on the user's PC so that AI generation/evaluation can be performed locally. OpenAI and Gemini are optional cloud providers.

---

# 2. Verified Reference Model

The following product decisions are based on publicly available Cambridge English information available at the time of this PRD.

## 2.1 CEST General positioning

Cambridge describes CEST General as an online, on-demand, modular test of general everyday English for adult learners. The published CEFR reporting range is **A1 to C1**. Reading, Listening, Writing and Speaking are separate modules; this simulator intentionally implements only Reading, Listening and Writing.

The official CEST General page states approximately:

| Module | Published duration | Simulator requirement |
|---|---:|---|
| Reading | 30–40 min approx.; maximum 59 min | 59 min hard maximum; adaptive stopping before the maximum when precision is sufficient |
| Listening | 30–40 min approx.; maximum 59 min | 59 min hard maximum; adaptive stopping before the maximum when precision is sufficient |
| Writing | 45 min | 45 min hard maximum |
| Speaking | 16 min | Out of scope |

Cambridge also states that Reading and Listening are adaptive and finish when the algorithm has enough confidence to determine the test-taker's ability level. [1]

## 2.2 Modular behaviour

CEST is modular; candidates do not necessarily need to take all modules in one sitting. The simulator therefore supports individual practice as well as a custom three-skill **Full Test Simulation** consisting of Reading + Listening + Writing.

The Full Test Simulation should be understood as a **simulated session**, not an assertion that Cambridge requires these three modules to be completed in this exact order or in one sitting.

## 2.3 Reading construct

The official CEST General Reading design document describes these task types:

1. Open Cloze
2. Multiple-choice Cloze
3. Cross Text Matching
4. Discrete Cloze
5. Discrete with a graphic
6. Gapped Text — Sentences
7. Gapped Text — Paragraphs
8. Comprehension task with 5 items
9. Comprehension task with 2 items

The same document describes reading activities such as global/local, careful/expeditious reading and cognitive processes such as lexical access, syntactic parsing, inferencing, text-level representation and mental-model construction. [2]

The simulator must therefore map the user's initial concept as follows:

| User's requested material | Simulator implementation |
|---|---|
| Notice | Discrete with a graphic |
| Message / text message / email | Discrete with a graphic |
| Article | Mainly 5-item / 2-item comprehension, gapped-text tasks, or cross-text tasks depending on target level |
| Opinion | Comprehension tasks and Cross Text Matching |
| Grammar | Open Cloze, Discrete Cloze, selected Multiple-choice Cloze |
| Vocabulary | Multiple-choice Cloze, Discrete Cloze, selected comprehension tasks |

## 2.4 Listening construct

The official CEST General Listening design document describes 1-item, 2-item and 5-item comprehension tasks using audio featuring one, two or three speakers. The focus includes extracting information from monologues and dialogues and, depending on level, detail, inference, meaning construction, feeling, attitude and global meaning. [3]

The simulator therefore uses:

- **Monologue** scenarios
- **Dialogue / conversation** scenarios
- **Discussion / multi-speaker** scenarios
- 1-item, 2-item and 5-item comprehension task structures

An official CEST General candidate-advice document confirms that the listening recording automatically plays **two times** and that the candidate can move forward to the next question when ready. [4]

Therefore, in **Full Test Simulation**, each listening recording:

- automatically plays exactly two times;
- cannot be manually replayed beyond those two plays;
- cannot be seeked/scrubbed;
- cannot be paused by the candidate;
- presents the next-task control only after the permitted playback cycle is complete;
- keeps the transcript hidden.

## 2.5 Writing construct

The official CEST General Writing design document states that the Writing component has two tasks:

- **Part 1 — Email:** read a short prompt and write an email using the information and three bullet points; minimum 50 words.
- **Part 2 — Writing to a wider audience:** respond to a scenario and three bullet points; minimum 180 words; possible text types include a review, article or web post.

The official candidate-advice material recommends about 15 minutes for Part 1 and about 30 minutes for Part 2, giving a total of 45 minutes. [5]

## 2.6 Writing assessment model

Cambridge's published Writing assessment criteria organise performance around:

- Communicative Achievement
- Organisation
- Language

with CEFR descriptors from A1 through C1. The simulator will paraphrase and operationalise these criteria rather than copy the full copyrighted descriptor text. [6]

## 2.7 Adaptive testing principle

Cambridge publicly describes adaptive testing as a process where future questions become harder or easier based on prior answers and the test ends when the algorithm has sufficient confidence about the candidate's ability. [1]

The simulator will implement the same **principle** using its own transparent 1PL IRT model and its own stopping rules.

---

# 3. Product Goals

## 3.1 Primary goals

### G1 — Realistic preparation

Give the user an exam-like experience that is functionally similar to CEST General in structure, timing, task behaviour and adaptive nature.

### G2 — Useful diagnostics

After practice or simulation, show enough detail to identify:

- estimated level per skill;
- strengths;
- weak areas;
- task-type performance;
- common grammar/vocabulary problems;
- writing feedback;
- task completion issues;
- explanations for objective items.

### G3 — Adaptive assessment

Make Reading and Listening adaptive so that the user does not simply receive a fixed beginner/intermediate/advanced test.

### G4 — Automated Writing evaluation

Evaluate writing with an AI model and return structured, repeatable feedback.

### G5 — Private local-first operation

Run the main system in Docker on the user's own PC. The application should work without a public cloud server when LM Studio and local assets are used.

### G6 — Extensible AI architecture

Allow OpenAI, Gemini and LM Studio to be swapped without rewriting the application logic.

### G7 — Original content generation

Generate a reusable original question bank using AI, validate it, and persist approved items before they are shown to the user.

---

# 4. Non-Goals / Explicitly Out of Scope

The MVP must NOT attempt to:

- implement Speaking;
- reproduce Cambridge's proprietary question bank;
- reproduce official Cambridge sample questions verbatim;
- reproduce official Cambridge branding or logos;
- claim an official Cambridge result;
- claim that the simulator reproduces Cambridge's proprietary scoring or adaptive algorithm;
- produce an official Cambridge English Scale score;
- provide mobile-first UI;
- support multiple user accounts;
- require a public VPS;
- include payments/subscriptions;
- implement remote invigilation or anti-cheating surveillance;
- build a public social community;
- build a full English-learning course.

---

# 5. Target User

## 5.1 Primary user

A single private user preparing personally for the Cambridge English Skills Test General.

## 5.2 User characteristics

- Uses a desktop PC.
- Wants a serious test simulation rather than a gamified quiz.
- Wants detailed post-test feedback.
- Wants to practise repeatedly.
- Does not want an account/login workflow.
- Is comfortable running Docker and LM Studio locally.
- Wants AI provider choice.

## 5.3 Typical user journeys

### Journey A — Quick practice

`Dashboard → Practice → Reading → Adaptive practice → Answer → Explanation → Continue → Results`

### Journey B — Listening practice

`Dashboard → Practice → Listening → Task → Audio twice → Answer → Transcript + explanation → Next`

### Journey C — Writing practice

`Dashboard → Practice → Writing → Part 1 + Part 2 → Submit → AI evaluation → Detailed feedback`

### Journey D — Full simulation

`Dashboard → Full Test Simulation → Instructions → Reading → Listening → Writing → Final result`

### Journey E — Content bank maintenance

`Dashboard → Content Studio → Select skill/task types → Generate → Validate → Approve → Question Bank`

---

# 6. Product Modes

## 6.1 Practice Mode

Purpose: learning and familiarity.

Rules:

- Timer is optional or relaxed.
- Reading remains adaptive, but stop rules may be relaxed.
- Listening allows pause and replay.
- Listening transcript may be revealed after answering.
- Explanations are shown immediately after the item is submitted.
- Correct answer may be shown immediately.
- Writing receives AI evaluation after submission.
- User can abandon a session and return later only if a resume feature is intentionally enabled; MVP may simply mark it incomplete.

Recommended Practice Mode UI label:

> **Practice Mode — Learn while you test**

## 6.2 Full Test Simulation

Purpose: realistic exam preparation.

Rules:

- Strict countdown timers.
- Reading and Listening adaptive.
- No answer explanations during a module.
- No objective-item answer reveal during a module.
- Listening recordings auto-play twice.
- Listening has no pause, replay or seek.
- Answers are committed when moving forward.
- Adaptive Reading/Listening items cannot be revisited after submission.
- Writing Part 1 and Part 2 share the fixed 45-minute total.
- Part 1 target duration: about 15 minutes.
- Part 2 target duration: about 30 minutes.
- At timeout, the module is automatically submitted.

Recommended Full Test label:

> **Full Test Simulation — Exam conditions**

---

# 7. Information Architecture

```text
/
├── Dashboard
├── Practice
│   ├── Reading
│   ├── Listening
│   └── Writing
├── Full Test Simulation
├── Results
│   ├── Latest Result
│   └── Result Details
├── History
├── Content Studio
│   ├── Generate Bank
│   ├── Review Queue
│   └── Question Bank
├── Settings
│   ├── AI Provider
│   ├── TTS
│   ├── Test Defaults
│   └── Storage
└── About / Disclaimer
```

No login screen is required.

---

# 8. Dashboard Requirements

## 8.1 Dashboard purpose

The dashboard is the starting point and should answer:

> “What is my current estimated level, what did I recently practise, and how do I start the next test?”

## 8.2 Dashboard layout

```text
┌──────────────────────────────────────────────────────────────┐
│ CEST Practice Simulator                            Settings  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  CURRENT ESTIMATED LEVELS                                    │
│                                                              │
│  Reading          Listening          Writing                 │
│  B2               B1                 B2                     │
│                                                              │
│  [Start Full Test Simulation]                               │
│                                                              │
│  [Practice Reading] [Practice Listening] [Practice Writing] │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ Recent Results                                               │
│                                                              │
│ Date       Mode        Reading  Listening  Writing          │
│ ...                                                        │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ Focus Areas                                                  │
│ • Grammar in cloze tasks                                     │
│ • Listening for implied meaning                              │
│ • Email register                                             │
└──────────────────────────────────────────────────────────────┘
```

## 8.3 Dashboard must show

- latest Reading estimated CEFR;
- latest Listening estimated CEFR;
- latest Writing estimated CEFR;
- latest full-test estimated overall level, if available;
- recent sessions table;
- weak areas based on accumulated history;
- quick-start buttons;
- current AI provider status;
- content-bank health warning if too few approved items are available.

## 8.4 Dashboard must not use

- progress charts/graphs, because the user explicitly chose not to use them;
- leaderboard;
- gamified streaks as a core experience.

---

# 9. Test Selection and Setup

## 9.1 Practice setup

User chooses:

```text
Skill
[ Reading ] [ Listening ] [ Writing ]

Difficulty
[ Adaptive ]

Mode options
[ Relaxed ]
[ Timed practice ] (optional)

[ Start Practice ]
```

For Reading/Listening, adaptive should be the default.

For Writing:

```text
Writing
[ Part 1 ]
[ Part 2 ]
[ Full Writing Practice ]
```

## 9.2 Full Test setup

```text
FULL TEST SIMULATION

Included skills:
☑ Reading
☑ Listening
☑ Writing

Estimated total time:
~ 105–130 minutes depending on adaptive modules and writing timing

Conditions:
• Strict timer
• No explanations during test
• Listening audio plays twice
• No replay/pause during test
• Reading and Listening are adaptive

[ Begin Simulation ]
```

The total is an estimate because Reading and Listening are adaptive.

---

# 10. Reading Module

## 10.1 Objective

Measure practical English reading ability across A1–C1 using task types and cognitive demands aligned with the published CEST General Reading construct.

## 10.2 Supported task types

### RT-01 — Open Cloze

- 5 gaps.
- User types one grammatical word per gap.
- Suggested content range: 60–150 words depending on level.
- Main focus: grammar and syntactic processing.

### RT-02 — Multiple-choice Cloze

- 5 gaps.
- 3 options for A1–B1-style items.
- 4 options for B2–C1-style items.
- Suggested content range: 60–150 words.
- Main focus: lexical and lexico-grammatical knowledge.

### RT-03 — Cross Text Matching

- Four texts on the same topic.
- User matches prompts/questions to relevant text(s).
- Suggested combined length: 500–600 words.
- Target: B2–C1.
- Main focus: compare, contrast and synthesise information/views.

### RT-04 — Discrete Cloze

- One sentence with one gap.
- 3 or 4 answer options according to item level.
- Tests lexical and lexico-grammatical knowledge.

### RT-05 — Discrete with a Graphic

- Short notice/message/email/label or, for very low level, an image-supported item.
- One multiple-choice question.
- 3 options.
- Target: A1–B2.

### RT-06 — Gapped Text: Sentences

- Long text with 5 sentence gaps.
- 8 sentence options.
- 5 keys + 3 distractors.
- Target: B1–C1.

### RT-07 — Gapped Text: Paragraphs

- Text with 5 missing sections.
- 6 paragraph options.
- 5 keys + 1 distractor.
- Suggested combined content length: 600–700 words.
- Target: B2–C1.

### RT-08 — Comprehension: 5 Items

- Reading passage.
- 5 multiple-choice questions.
- 3 options at lower levels.
- 4 options at B2+.
- Suggested text length: 200–600 words according to level.
- Focus can include gist, specific information, opinion, purpose, main idea and implication.

### RT-09 — Comprehension: 2 Items

- Shorter reading passage.
- 2 multiple-choice questions.
- 4 options.
- Suggested text length: 200–250 words.
- Target: B2–C1.

## 10.3 Reading task metadata

Every item must store:

```json
{
  "skill": "reading",
  "task_type": "RT-08",
  "cefr_target": "B2",
  "difficulty_theta": 0.72,
  "topic": "technology",
  "scenario": "university life",
  "cognitive_focus": [
    "gist",
    "specific_information",
    "inference"
  ],
  "question_format": "mcq",
  "answer_key": "C",
  "explanation": "...",
  "status": "approved"
}
```

## 10.4 Reading interface

The test view should resemble a modern computer-delivered exam:

```text
┌──────────────────────────────────────────────────────────────┐
│ Reading                         Time remaining 38:22          │
├───────────────────────┬──────────────────────────────────────┤
│                       │                                      │
│ Text / Passage        │ Question                             │
│                       │                                      │
│ paragraph...          │ 1. What does the writer imply?       │
│ paragraph...          │                                      │
│                       │ ○ A ...                              │
│                       │ ○ B ...                              │
│                       │ ○ C ...                              │
│                       │ ○ D ...                              │
│                       │                                      │
│                       │                 [ Next → ]           │
└───────────────────────┴──────────────────────────────────────┘
```

For multi-text tasks, use a scrollable text workspace with clearly labelled sources.

## 10.5 Navigation

Full Test Simulation:

- no Previous button after an item is submitted;
- Next submits the current answer and immediately selects the next adaptive item;
- an unanswered item may not be submitted unless the user explicitly chooses an allowed “leave blank” action;
- once submitted, the response is immutable.

The no-back rule is a simulator design requirement driven by adaptive test integrity; it must not be presented as a literal reproduction of undocumented Cambridge implementation details.

Practice Mode may allow more flexible navigation only in non-adaptive drill workflows. The default adaptive practice flow should remain one-way to preserve the usefulness of the ability estimate.

---

# 11. Listening Module

## 11.1 Objective

Measure comprehension of spoken English in realistic everyday settings through monologues, conversations and multi-speaker discussions.

## 11.2 Supported task types

### LT-01 — 1-item comprehension

- One multiple-choice question.
- One or two speakers.
- 3 written options or 3 image options where appropriate.
- Audio approximately 70–150 words depending on difficulty.
- Can test detail, inference, attitude, meaning and other suitable listening constructs.

### LT-02 — 2-item comprehension

- Two multiple-choice questions.
- One or two speakers.
- 3 options each.
- Audio approximately 160–260 words depending on difficulty.
- Mainly upper-level items.

### LT-03 — 5-item comprehension

- Five multiple-choice questions.
- One, two or three speakers.
- 3 or 4 options per question according to level.
- Audio approximately 120–650 words depending on difficulty.
- Can test detail, inference, meaning, feeling, attitude and global understanding.

## 11.3 Scenario categories

The generator must intentionally distribute content across:

- everyday conversations;
- appointments;
- study situations;
- travel;
- work and workplace-lite contexts;
- shopping/services;
- hobbies/free time;
- technology;
- education;
- health/lifestyle topics suitable for general English;
- community events;
- personal plans;
- news-like informational monologues;
- short discussions.

Avoid making every listening item sound like a scripted textbook conversation.

## 11.4 Listening speaker design

Each generated audio item must specify:

```json
{
  "speaker_count": 2,
  "speaker_roles": [
    "student",
    "friend"
  ],
  "accent_profile": "international_English",
  "speech_speed": "B1",
  "register": "informal"
}
```

The default accent profile should be understandable international English. Do not intentionally create extreme accents that test accent recognition instead of listening comprehension.

## 11.5 Full Test Simulation playback rules

```text
Audio state:
LOADING
  ↓
PLAY 1
  ↓
SHORT TRANSITION
  ↓
PLAY 2
  ↓
ANSWER ENABLED / CONTINUE
```

The candidate-advice source confirms two automatic plays. [4]

Full-test controls:

- Volume: allowed.
- Pause: disabled.
- Replay: disabled.
- Seek/scrub: disabled.
- Speed control: disabled.
- Transcript: hidden.
- Next: enabled only according to task flow.

Practice Mode:

- Pause: allowed.
- Replay: allowed.
- Seek: allowed.
- Transcript: reveal after answer.
- Explanation: immediate.

## 11.6 Listening pre-read time

Where a task requires reading the question/options before audio starts, the content model should include a configurable `prelistening_seconds` value.

The default for a simple one-question item can be 10 seconds based on the publicly available candidate-advice example, but this value must be stored per task rather than hard-coded for every listening task. [4]

---

# 12. Writing Module

## 12.1 Structure

```text
WRITING — 45 MINUTES

Part 1 — Email
Recommended time: ~15 min
Minimum: 50 words

Part 2 — Wider-audience writing
Recommended time: ~30 min
Minimum: 180 words
```

These are based on Cambridge's published CEST General candidate-advice materials. [5]

## 12.2 Part 1 — Email

The generated task must contain:

- a realistic sender/context;
- recipient/audience information;
- a short prompt or incoming email/message;
- 3 clear bullet-point requirements;
- an explicit word-count instruction: “Write at least 50 words.”

Typical contexts:

- friend/college acquaintance;
- event planning;
- travel arrangements;
- study/life arrangements;
- invitations;
- requests for information;
- informal or semi-formal everyday communication.

The generator must choose register based on audience.

## 12.3 Part 2 — Wider-audience writing

The generated task must contain:

- a realistic scenario;
- a specified wider audience;
- 3 required content points;
- optional freedom for additional relevant points;
- a requested text type such as article, review, web post, comments or opinion-oriented text;
- instruction to write at least 180 words.

The generator must vary topic and text type while retaining the same underlying construct.

## 12.4 Writing editor UI

```text
┌──────────────────────────────────────────────────────────────┐
│ Writing Part 1                                  14:37        │
├──────────────────────────────────────────────────────────────┤
│ Prompt                                                       │
│ ...                                                          │
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ Dear ...                                                 │ │
│ │                                                          │ │
│ │ ...                                                      │ │
│ │                                                          │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ Words: 96                                  Minimum: 50       │
│                                                              │
│ [Continue to Part 2]                                        │
└──────────────────────────────────────────────────────────────┘
```

## 12.5 Word counter

The editor must show:

- current word count;
- minimum required word count;
- optional warning below the minimum;
- no hard block solely because the response is below the minimum.

Rationale: the simulator should evaluate the actual response rather than hiding a low-performing submission.

## 12.6 Writing timer behaviour

Full Test Simulation:

- total Writing module timer = 45 minutes;
- Part 1 starts first;
- user can move to Part 2 before the recommended 15 minutes if desired;
- remaining time carries into Part 2;
- once the global 45-minute timer expires, Writing automatically submits;
- no extra time is added because the user spent too long on Part 1.

Practice Mode:

- optional timer;
- recommended timing displayed but not enforced unless “Timed Practice” is selected.

---

# 13. Writing AI Evaluation

## 13.1 Evaluation objectives

The AI evaluator must return:

- estimated CEFR level for Part 1;
- estimated CEFR level for Part 2;
- combined Writing estimated CEFR;
- rubric scores;
- task completion analysis;
- grammar diagnostics;
- vocabulary diagnostics;
- organisation/coherence analysis;
- register analysis;
- specific mistakes with corrections;
- concrete improvement advice;
- examples of improved sentences where useful.

## 13.2 Core rubric

The core rubric is based on the officially published CEST Writing dimensions:

1. **Communicative Achievement** — whether the response accomplishes the task appropriately for the target reader and context.
2. **Organisation** — whether ideas are connected, structured and easy to follow.
3. **Language** — range, appropriacy and control of vocabulary and grammar.

See official criteria source [6].

## 13.3 Simulator scoring scale

Do not expose the internal AI raw rubric number as an official Cambridge score.

Use an internal 0–5 band per criterion:

```text
0 = insufficient / non-functional evidence
1 = very limited
2 = emerging
3 = generally adequate
4 = strong
5 = highly effective
```

The evaluator then estimates a CEFR level using calibration rules stored in configuration.

Example internal record:

```json
{
  "communicative_achievement": 4,
  "organisation": 3,
  "language": 4,
  "estimated_cefr": "B2",
  "confidence": 0.78
}
```

The exact mapping from rubric results to CEFR is a **simulator-defined calibration**, not an official Cambridge scoring conversion.

## 13.4 Secondary diagnostics

The AI may separately return:

```text
Grammar
- verb agreement
- article use
- tense consistency
- prepositions
- sentence complexity

Vocabulary
- range
- repetition
- collocation
- word choice

Coherence
- paragraphing
- linking
- progression

Task
- missing bullet point
- weak development
- register mismatch
```

These diagnostics do not replace the three core rubric dimensions.

## 13.5 Correction examples

The UI should show concise evidence-based corrections.

Example:

```text
Original
it can gives them experience

Suggested
it can give them experience

Why
After the modal verb “can”, use the base form of the verb.
```

The evaluator must not rewrite the entire essay unnecessarily. The purpose is learning and preparation.

## 13.6 AI output constraints

The AI evaluator must:

- return strict structured JSON;
- avoid inventing task requirements;
- quote the user's own text accurately when citing evidence;
- distinguish errors from stylistic alternatives;
- not penalise an alternative that is grammatically valid merely because it is different from a preferred wording;
- evaluate against the prompt actually shown to the user;
- not use hidden answer keys from unrelated tasks;
- provide a confidence value;
- report when the response is too short to evaluate reliably.

---

# 14. Overall Estimated Level

## 14.1 Skill levels

Each module produces a separate simulator estimate:

```text
Reading     A1–C1
Listening   A1–C1
Writing     A1–C1
```

## 14.2 Overall level

The simulator's overall estimate is **not an official CEST result**.

For MVP, use a transparent three-skill aggregation:

1. Convert the three skill-level estimates into ordinal numeric levels:

```text
A1 = 1
A2 = 2
B1 = 3
B2 = 4
C1 = 5
```

2. Average the three values.
3. Map the result to the nearest named CEFR level using configured rounding rules.
4. Display both the three skill results and the overall estimate so that a user cannot mistake the overall label for an official Cambridge score.

Future versions may replace this rule with an empirically calibrated latent-score model.

## 14.3 Example result

```text
ESTIMATED RESULT

Reading       B2
Listening     B1
Writing       B2

Estimated Overall Level: B2

IMPORTANT:
This is a simulator estimate, not an official Cambridge result.
```

---

# 15. IRT Adaptive Engine

## 15.1 Why 1PL/Rasch

The user requested an academically stronger adaptive mechanism. A 1PL IRT model is appropriate for the first production version because the item bank initially does not contain enough empirical data to estimate separate item discrimination and guessing parameters reliably.

Therefore:

- all items use discrimination `a = 1.0` initially;
- each item has an estimated difficulty `b`;
- the item difficulty is derived initially from the assigned CEFR target and later calibrated from response data.

## 15.2 Model

Use the Rasch probability model:

```text
P(X = 1 | theta, b) = 1 / (1 + exp(-(theta - b)))
```

where:

- `theta` = user's latent ability estimate;
- `b` = item's latent difficulty;
- `X = 1` = correct answer.

## 15.3 Ability estimation

Use **Expected A Posteriori (EAP)** estimation for stability with relatively small numbers of responses.

Initial prior:

```text
theta ~ Normal(0, 1)
```

The prior must be configurable.

## 15.4 Initial ability

Default initial ability:

```text
theta = 0.0
```

This should be interpreted as a neutral simulator starting point, approximately around the middle of the configured initial bank.

Do not describe theta=0 as an official Cambridge B1 score.

## 15.5 Initial CEFR ↔ theta calibration

The initial item-bank calibration is configuration, not official Cambridge scoring.

Recommended initial target bands:

| CEFR | Initial theta band |
|---|---:|
| A1 | < -1.20 |
| A2 | -1.20 to -0.40 |
| B1 | -0.40 to +0.40 |
| B2 | +0.40 to +1.20 |
| C1 | > +1.20 |

These thresholds must be stored in a configuration table/file and changed later after real pilot data is available.

## 15.6 Item selection

At each step:

1. estimate current ability `theta`;
2. calculate Fisher information of candidate items at `theta`;
3. filter items by required task distribution and content constraints;
4. exclude already-used items;
5. exclude items too similar to immediately previous items;
6. apply exposure control;
7. randomly select one item from the top information candidates.

For the 1PL model:

```text
I(theta) = P(theta) * (1 - P(theta))
```

## 15.7 Content-balancing constraints

The selection engine must avoid creating an adaptive test made entirely of one task type.

Example constraints:

```text
No same task_type more than 2 times consecutively.
No same topic more than 2 times in a row.
At least 3 distinct task types before stopping.
For B2/C1 tests, include higher-order comprehension/inference tasks when available.
```

The exact test blueprint must be configurable.

## 15.8 Exposure control

Because this is initially a one-user private application, item exposure is less critical than in a multi-user exam platform. Nevertheless, implement basic controls:

- track item usage count;
- randomly choose among top-K candidates with similar information;
- do not reuse an item within the same session;
- optionally exclude recently seen items for practice sessions.

## 15.9 Minimum and maximum stopping rules

Because the official CEST public description says the adaptive module ends when the algorithm has enough confidence, while its exact proprietary stopping algorithm is not public, the simulator needs its own explicit rule.

Recommended MVP rule:

```text
Minimum scored item units: 12
Maximum elapsed time: 59 minutes
Preferred stopping condition:
  - minimum 12 item units completed
  - EAP standard error <= 0.30
  - at least one item in each of the relevant difficulty neighbourhoods
  - no severe content-balance violation
```

If standard error does not reach the threshold before 59 minutes:

- stop at 59:00;
- compute final estimate using the latest EAP theta;
- mark confidence as “time-limited”.

These stopping parameters are simulator-defined and must not be presented as Cambridge's exact CAT algorithm.

## 15.10 Item unit accounting

Some Reading/Listening task types contain multiple subquestions. Internally, the system may treat each subquestion as an item response for IRT purposes while preserving the task as a grouped UI unit.

Example:

```text
Task LT-03
Audio = 1 task
Questions = 5 item responses
IRT evidence = 5 responses
UI navigation = one grouped task
```

This gives the adaptive engine enough evidence without making the interface unnecessarily fragmented.

---

# 16. Practice Adaptivity

Practice mode should retain the same core IRT engine but allow the user to prioritise learning.

Recommended behaviour:

```text
Adaptive Practice
      ↓
Select next informative item
      ↓
Answer
      ↓
Show correctness
      ↓
Show explanation
      ↓
Update theta
      ↓
Next item
```

Practice Mode may allow the user to set:

- `5 items`
- `10 items`
- `20 items`
- `Until confidence threshold`

For a private study tool, this provides flexibility without changing the underlying item-selection logic.

---

# 17. CEFR Reporting

## 17.1 Reporting range

The report must use A1–C1 as the primary displayed range.

## 17.2 Confidence

Show confidence in plain language:

```text
High confidence
Moderate confidence
Limited confidence
```

Do not expose a raw statistical interval unless the user opens an “Assessment details” section.

## 17.3 Ability details

Advanced diagnostic view may show:

```text
Estimated ability theta: +0.74
Standard error: 0.28
Confidence: High
```

The raw theta is a simulator diagnostic only.

## 17.4 Can-Do statements

The result page should include practical Can-Do style statements.

Example:

```text
At this estimated level, the simulator indicates that you can generally:

• follow the main ideas in moderately complex texts;
• identify relevant information across related texts;
• understand common spoken interactions and infer some implied meaning;
• produce connected written responses for familiar audiences.
```

These statements must be original paraphrases inspired by CEFR concepts and must not be presented as an official Cambridge certificate descriptor.

---

# 18. Result Page

## 18.1 Overall layout

```text
┌──────────────────────────────────────────────────────────────┐
│ TEST RESULT                                                  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ Estimated Overall Level: B2                                  │
│ Confidence: Moderate                                         │
│                                                              │
│ Reading       B2                                             │
│ Listening     B1                                             │
│ Writing       B2                                             │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ READING DETAILS                                              │
│                                                              │
│ Estimated level: B2                                         │
│ Accuracy: 74%                                                │
│ Confidence: High                                             │
│                                                              │
│ Task performance:                                            │
│ Open Cloze                    Strong                          │
│ Comprehension                 Good                            │
│ Cross Text Matching           Developing                      │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ LISTENING DETAILS                                            │
│ ...                                                          │
├──────────────────────────────────────────────────────────────┤
│ WRITING DETAILS                                              │
│                                                              │
│ Estimated level: B2                                         │
│ Communicative Achievement     4/5                            │
│ Organisation                  3/5                            │
│ Language                      4/5                            │
│                                                              │
│ Grammar diagnostics          ...                             │
│ Vocabulary diagnostics       ...                             │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ CAN-DO STYLE SUMMARY                                         │
│ ...                                                          │
└──────────────────────────────────────────────────────────────┘
```

## 18.2 Objective item review

After Full Test Simulation completion, allow:

- user's answer;
- correct answer;
- explanation;
- task type;
- CEFR target level;
- whether response was correct.

For Listening, optionally show transcript after the entire module is finished.

## 18.3 Writing review

Show:

- prompt;
- user's response;
- word count;
- criterion scores;
- feedback;
- evidence examples;
- corrections;
- suggested next focus.

---

# 19. History

## 19.1 Purpose

Because the user wants progress tracking but no graph, history should be a detailed table and expandable result cards.

## 19.2 History record

```text
Date | Mode | Reading | Listening | Writing | Overall | Status
```

## 19.3 Session details

Every session should retain enough data to reproduce the result:

- session ID;
- start/end timestamps;
- mode;
- module order;
- item IDs;
- item responses;
- theta estimates per step for adaptive modules;
- final theta;
- standard error;
- Writing AI provider/model;
- Writing raw response;
- Writing evaluation JSON;
- final displayed levels;
- timer metadata;
- content version.

## 19.4 Delete history

Settings must include:

```text
[ Delete selected session ]
[ Delete all history ]
```

Deletion must cascade through associated records but must not remove shared question-bank items unless explicitly requested from Content Studio.

---

# 20. Question Bank Strategy

## 20.1 Principle

Questions are generated **ahead of testing** and stored in a validated question bank. The application must not depend on live AI generation to create a question while a timed Full Test is in progress.

## 20.2 Why pre-generation

Pre-generation provides:

- deterministic answer keys;
- lower latency;
- fewer test interruptions;
- stable audio;
- stable difficulty metadata;
- reproducible sessions;
- better validation;
- easier debugging.

## 20.3 Suggested initial bank

The generator should support a configurable target bank such as:

### Reading

| Level | Starting target |
|---|---:|
| A1 | 20 item units |
| A2 | 20 |
| B1 | 30 |
| B2 | 30 |
| C1 | 20 |

### Listening

| Level | Starting target |
|---|---:|
| A1 | 20 item units |
| A2 | 20 |
| B1 | 30 |
| B2 | 30 |
| C1 | 20 |

### Writing

At least:

- 20 Part 1 prompts across A2–C1;
- 20 Part 2 prompts across A2–C1;
- target-level metadata;
- topic diversity.

These numbers are engineering defaults, not official Cambridge item counts.

## 20.4 Generation pipeline

```text
Select generation target
        ↓
Build task-type-specific prompt
        ↓
AI generates structured item
        ↓
JSON schema validation
        ↓
Deterministic rule validation
        ↓
Answer-key validation
        ↓
Distractor validation
        ↓
CEFR/task constraint validation
        ↓
Duplicate/similarity check
        ↓
Audio generation if Listening
        ↓
Audio/transcript alignment check
        ↓
Quality status = REVIEW
        ↓
Human/private owner approval
        ↓
Status = APPROVED
        ↓
Available to adaptive engine
```

## 20.5 AI-generated item validation

The system must automatically check:

### Structural

- required fields exist;
- JSON is valid;
- correct number of options;
- correct number of gaps;
- correct answer exists among options where applicable;
- no duplicate options;
- no accidental answer leakage.

### Linguistic

- grammar is valid for the intended level;
- wording is natural;
- vocabulary matches target level;
- prompt is unambiguous;
- distractors are plausible but incorrect;
- answer has a defensible rationale.

### Assessment

- task actually measures the intended construct;
- difficulty is plausible for target CEFR;
- cognitive focus matches task type;
- no unnecessary specialist knowledge is required.

### Content

- no copyrighted text copied from known sources;
- no Cambridge sample content reproduced;
- no answer copied from reference materials;
- no inappropriate or unsafe material;
- topic appropriate for general English.

---

# 21. Content Studio

Even though the application has one user, a lightweight content-management view is required so the question bank can be generated and maintained without editing database records manually.

## 21.1 Content Studio pages

```text
Content Studio
├── Bank Health
├── Generate
├── Review Queue
└── Approved Bank
```

## 21.2 Generate page

```text
Skill
[ Reading ▼ ]

Task type
[ Comprehension — 5 items ▼ ]

Target levels
☑ A1
☑ A2
☑ B1
☑ B2
☑ C1

Quantity
[ 20 ]

AI Provider
[ LM Studio ▼ ]

[ Generate ]
```

## 21.3 Review queue

Every generated item starts with:

```text
status = REVIEW
```

The user can:

- Preview
- Approve
- Reject
- Regenerate
- Edit metadata
- Edit answer explanation

Editing a question after approval must create a new `content_version` and invalidate previous validation results.

## 21.4 Bank health

Show:

```text
Reading
A1  18 / 20  ⚠
A2  24 / 20  ✓
B1  31 / 30  ✓
B2  14 / 30  ⚠
C1  21 / 20  ✓

Listening
...
```

The adaptive engine must refuse to run a task blueprint that requires unavailable approved items. Instead it should show a clear Content Bank warning.

---

# 22. AI Provider Abstraction

## 22.1 Required providers

```text
AIProvider
├── OpenAIProvider
├── GeminiProvider
└── LMStudioProvider
```

Each provider implements the same logical interface:

```text
generate_text()
score_writing()
validate_item()
health_check()
list_models()
```

## 22.2 Provider selection

The user's settings should allow:

```text
Default AI Provider
[ LM Studio ▼ ]

Generation Model
[ model-id ▼ ]

Writing Evaluation Model
[ model-id ▼ ]
```

API keys are not editable through normal user-facing test pages.

## 22.3 Environment variables

Recommended variables:

```env
OPENAI_API_KEY=
OPENAI_MODEL=

GEMINI_API_KEY=
GEMINI_MODEL=

LM_STUDIO_BASE_URL=http://host.docker.internal:1234/v1
LM_STUDIO_MODEL=
LM_STUDIO_API_KEY=

AI_DEFAULT_PROVIDER=lm_studio
WRITING_DEFAULT_PROVIDER=lm_studio
```

The actual model IDs must remain configurable. Do not hard-code a model whose availability may change.

## 22.4 OpenAI integration

Use the current official OpenAI SDK/API pattern appropriate to the selected SDK version. OpenAI's current developer documentation uses the Responses API for text generation and supports structured output via JSON Schema for supported models. [7]

The implementation should use structured outputs whenever the selected provider/model supports them.

## 22.5 Gemini integration

Use Google's current Gemini API/SDK and request structured output where supported. The provider adapter must isolate Gemini-specific request/response handling from the rest of the application. [8]

## 22.6 LM Studio integration

LM Studio exposes local REST APIs and OpenAI-compatible endpoints. Its documentation currently supports OpenAI-compatible `/v1/responses` and `/v1/chat/completions` endpoints. [9]

For Docker Desktop on Windows, the backend should use a configurable host base URL such as:

```text
http://host.docker.internal:1234/v1
```

The URL must be configurable rather than hard-coded because the deployment may later move to Linux or another environment.

LM Studio may operate fully offline after the model files are available locally. [10]

## 22.7 Automatic fallback

Fallback is required, but Writing evaluation must maintain provider consistency within a session.

Policy:

```text
Start session
  ↓
Preferred provider health check
  ↓
Provider unavailable?
  ├─ No → lock provider for session
  └─ Yes → try next configured provider
                    ↓
                 lock successful provider
```

Once a provider successfully evaluates the Writing module, do not automatically switch to another provider for subsequent scoring calls in the same session unless the current provider fails entirely and a retry policy is exhausted.

Generation tasks may use a different provider from Writing evaluation.

## 22.8 Retry policy

Recommended:

```text
Attempt 1
↓
backoff 1s
↓
Attempt 2
↓
backoff 3s
↓
Attempt 3
↓
fallback provider if allowed
```

All retries must be logged.

---

# 23. TTS / Audio Generation

## 23.1 Requirement

Listening questions require stable audio assets generated before a test.

## 23.2 TTS architecture

```text
TTSEngine
├── LocalTTSAdapter
└── CloudTTSAdapter (optional)
```

The default architecture should favour local TTS so the private simulator can operate locally.

A practical implementation is a local Piper-style TTS adapter or another locally hosted open-source TTS engine. The exact model/voice must be configurable.

## 23.3 Audio generation pipeline

```text
Listening script
      ↓
Voice assignment
      ↓
TTS generation
      ↓
Normalize volume
      ↓
Encode audio
      ↓
Save local audio asset
      ↓
Store asset metadata
```

## 23.4 Audio metadata

```json
{
  "audio_id": "aud_01J...",
  "format": "mp3",
  "sample_rate": 44100,
  "duration_seconds": 42.8,
  "speaker_count": 2,
  "script_hash": "...",
  "tts_provider": "local",
  "voice": "en_voice_01"
}
```

## 23.5 Quality checks

Before approval:

- file exists;
- decodes correctly;
- duration is plausible;
- no silent/near-silent output;
- no severe clipping;
- transcript exactly matches the generated script;
- question is answerable from the audio.

---

# 24. Local Storage Architecture

## 24.1 Database

Use PostgreSQL.

Reasoning:

- reliable relational model;
- good support for structured historical data;
- easy Docker deployment;
- suitable for question bank, sessions and evaluations;
- future extensibility.

## 24.2 File storage

Store audio assets in a Docker-mounted local volume:

```text
./data/audio/
```

Do not put large binary audio blobs directly into PostgreSQL unless there is a concrete reason to do so.

## 24.3 User history

Store history in PostgreSQL.

Optional browser caching may use IndexedDB for resilience, but PostgreSQL is the source of truth.

---

# 25. Database Schema

The following is the recommended logical schema.

## 25.1 `question_items`

```text
id UUID PK
skill ENUM(reading, listening)
task_type VARCHAR
cefr_target ENUM(A1, A2, B1, B2, C1)
difficulty_theta NUMERIC
status ENUM(DRAFT, REVIEW, APPROVED, REJECTED, ARCHIVED)
version INTEGER
content_hash VARCHAR
primary_topic VARCHAR
scenario VARCHAR
cognitive_focus JSONB
content_json JSONB
explanation TEXT
created_at TIMESTAMP
updated_at TIMESTAMP
```

## 25.2 `question_options`

```text
id UUID PK
question_id UUID FK
label VARCHAR
text TEXT
is_correct BOOLEAN
position INTEGER
```

This table is useful for conventional MCQ tasks. Complex tasks can store additional structure in `content_json`.

## 25.3 `audio_assets`

```text
id UUID PK
question_id UUID FK
file_path TEXT
duration_seconds NUMERIC
format VARCHAR
voice VARCHAR
tts_provider VARCHAR
script_hash VARCHAR
status VARCHAR
created_at TIMESTAMP
```

## 25.4 `writing_prompts`

```text
id UUID PK
task_part INTEGER
cefr_target ENUM(A1, A2, B1, B2, C1)
text_type VARCHAR
audience VARCHAR
scenario TEXT
prompt_text TEXT
bullet_points JSONB
minimum_words INTEGER
recommended_minutes INTEGER
status VARCHAR
version INTEGER
created_at TIMESTAMP
updated_at TIMESTAMP
```

## 25.5 `test_sessions`

```text
id UUID PK
mode ENUM(PRACTICE, FULL_SIMULATION)
status ENUM(IN_PROGRESS, COMPLETED, ABANDONED, TIMEOUT)
started_at TIMESTAMP
ended_at TIMESTAMP
current_module VARCHAR
reading_result_id UUID NULL
listening_result_id UUID NULL
writing_result_id UUID NULL
overall_level VARCHAR NULL
created_at TIMESTAMP
```

## 25.6 `module_sessions`

```text
id UUID PK
test_session_id UUID FK
skill ENUM(reading, listening, writing)
started_at TIMESTAMP
ended_at TIMESTAMP
time_limit_seconds INTEGER
elapsed_seconds INTEGER
final_theta NUMERIC NULL
standard_error NUMERIC NULL
confidence_label VARCHAR NULL
estimated_cefr VARCHAR NULL
raw_accuracy NUMERIC NULL
```

## 25.7 `responses`

```text
id UUID PK
module_session_id UUID FK
question_id UUID NULL
writing_prompt_id UUID NULL
item_position INTEGER
answer_json JSONB
is_correct BOOLEAN NULL
response_time_seconds INTEGER
pre_theta NUMERIC NULL
post_theta NUMERIC NULL
created_at TIMESTAMP
```

## 25.8 `writing_submissions`

```text
id UUID PK
module_session_id UUID FK
writing_prompt_id UUID FK
part_number INTEGER
response_text TEXT
word_count INTEGER
submitted_at TIMESTAMP
```

## 25.9 `writing_evaluations`

```text
id UUID PK
submission_id UUID FK
provider VARCHAR
model VARCHAR
evaluation_version VARCHAR
communicative_achievement NUMERIC
organisation NUMERIC
language NUMERIC
estimated_cefr VARCHAR
confidence NUMERIC
feedback_json JSONB
raw_provider_response JSONB NULL
created_at TIMESTAMP
```

## 25.10 `ai_provider_logs`

```text
id UUID PK
provider VARCHAR
model VARCHAR
operation VARCHAR
status VARCHAR
latency_ms INTEGER
retry_count INTEGER
error_code VARCHAR NULL
usage_json JSONB NULL
created_at TIMESTAMP
```

Do not store API keys in this table.

---

# 26. Question JSON Contracts

## 26.1 MCQ example

```json
{
  "type": "mcq",
  "stem": "What is the main reason...?",
  "options": [
    {"id": "A", "text": "..."},
    {"id": "B", "text": "..."},
    {"id": "C", "text": "..."},
    {"id": "D", "text": "..."}
  ],
  "correct_option_id": "B",
  "explanation": "..."
}
```

## 26.2 Open Cloze example

```json
{
  "type": "open_cloze",
  "text_segments": [
    {"text": "Many students find that"},
    {"gap_id": "g1"},
    {"text": "time management is important."}
  ],
  "gaps": [
    {
      "id": "g1",
      "accepted_answers": ["good"],
      "primary_answer": "good",
      "answer_type": "single_word"
    }
  ]
}
```

Accepted answers must be explicitly defined. Do not rely on AI semantic matching for objective Reading scoring in the MVP.

## 26.3 Gapped-text example

```json
{
  "type": "gapped_text_sentences",
  "base_text": "...",
  "gaps": ["gap1", "gap2", "gap3", "gap4", "gap5"],
  "options": [
    {"id": "A", "text": "..."},
    {"id": "B", "text": "..."}
  ],
  "correct": {
    "gap1": "C",
    "gap2": "F"
  }
}
```

---

# 27. API Design

Use REST for the MVP.

## 27.1 Health

```http
GET /api/health
GET /api/health/ai
GET /api/health/database
```

## 27.2 Dashboard

```http
GET /api/dashboard/summary
GET /api/dashboard/recent-sessions
GET /api/dashboard/focus-areas
```

## 27.3 Practice

```http
POST /api/practice/start
POST /api/practice/{session_id}/answer
GET  /api/practice/{session_id}/next
POST /api/practice/{session_id}/finish
```

## 27.4 Full simulation

```http
POST /api/simulations/start
GET  /api/simulations/{session_id}/current
POST /api/simulations/{session_id}/answer
POST /api/simulations/{session_id}/module/finish
POST /api/simulations/{session_id}/finish
```

## 27.5 Results

```http
GET /api/results/{session_id}
GET /api/results/{session_id}/details
```

## 27.6 History

```http
GET    /api/history
GET    /api/history/{session_id}
DELETE /api/history/{session_id}
DELETE /api/history
```

## 27.7 Content Studio

```http
POST /api/content/generate
GET  /api/content/review-queue
POST /api/content/{id}/approve
POST /api/content/{id}/reject
POST /api/content/{id}/regenerate
GET  /api/content/bank-health
```

## 27.8 AI settings

```http
GET /api/settings/ai
PUT /api/settings/ai
POST /api/settings/ai/health-check
GET /api/settings/ai/{provider}/models
```

---

# 28. Backend Architecture

Recommended stack:

```text
Python
FastAPI
SQLAlchemy
Alembic
PostgreSQL
Pydantic
```

## 28.1 Backend modules

```text
backend/app/
├── api/
├── core/
├── models/
├── schemas/
├── services/
│   ├── adaptive/
│   ├── scoring/
│   ├── question_generation/
│   ├── writing_evaluation/
│   ├── tts/
│   └── providers/
├── repositories/
├── prompts/
├── workers/
└── main.py
```

## 28.2 Service boundaries

The backend must not mix:

- IRT math;
- question generation;
- UI concerns;
- provider-specific API calls.

Example:

```text
WritingEvaluationService
        ↓
AIProvider interface
        ↓
OpenAI / Gemini / LM Studio
```

This makes provider replacement straightforward.

---

# 29. Frontend Architecture

Recommended stack:

```text
Next.js
React
TypeScript
Tailwind CSS
```

A component library may be added if it improves consistency, but the exam UI must remain clean and restrained.

## 29.1 Frontend state

Use server state for persistent session data and local state for transient UI state.

Suggested tools:

- React Query/TanStack Query for API state;
- React context or Zustand for session UI state if required.

## 29.2 Exam state machine

The frontend must not rely on ad-hoc booleans such as `isLoading`, `isFinished`, `isAudioPlaying`, etc. for critical exam logic.

Use explicit states:

```text
READING:
  INTRO
  ACTIVE
  SUBMITTING
  COMPLETED

LISTENING:
  PREVIEW
  PLAYBACK_1
  PLAYBACK_2
  ANSWER
  SUBMITTING

WRITING:
  PART_1
  PART_2
  SUBMITTING
  COMPLETED
```

The backend remains authoritative for session status.

---

# 30. Timer Architecture

## 30.1 Principle

The backend must treat server time as authoritative.

Do not trust a client-side timer for test validity.

## 30.2 Countdown

Frontend:

```text
remaining = server_deadline - current_client_time
```

Synchronise with backend periodically.

## 30.3 Timeout

When timeout occurs:

1. frontend immediately disables input;
2. backend receives or detects timeout;
3. backend finalises the module;
4. unanswered fields are recorded as blank;
5. result calculation proceeds.

## 30.4 Browser refresh

In Full Test Simulation:

- refresh should attempt to recover the active session;
- the user must not gain extra time;
- the server deadline remains unchanged.

If recovery fails, mark the session as an error/incomplete rather than silently creating a new attempt.

---

# 31. Exam Integrity Rules

## 31.1 Full simulation

The UI must not reveal:

- CEFR target of the current item;
- item difficulty theta;
- adaptive direction;
- whether a user answer was correct;
- explanation before submission;
- correct answer before module completion.

## 31.2 API integrity

The API must never send the correct answer to the browser before the user submits the corresponding response.

Do not merely hide the answer with CSS or UI state. Keep it out of the response payload.

## 31.3 Adaptive integrity

The backend chooses the next item. The frontend must not request an arbitrary next item by ID in Full Test Simulation.

Bad:

```http
GET /api/items/{id}
```

Good:

```http
GET /api/simulations/{session_id}/current
```

where the backend determines the item.

---

# 32. Privacy and Data Handling

## 32.1 Default local-first mode

By default:

- PostgreSQL is local;
- audio is local;
- history is local;
- question bank is local;
- LM Studio inference is local.

## 32.2 Cloud AI mode

If the user selects OpenAI or Gemini:

- writing responses may be sent to the selected provider;
- question-generation prompts may be sent to the selected provider;
- the app must clearly show which provider is active;
- secrets remain in environment variables;
- cloud provider raw responses should not be retained indefinitely unless explicitly enabled.

For OpenAI integration, the implementation must review the current data-control/storage behaviour for the selected endpoint and set storage-related request options appropriately. Current OpenAI documentation notes that Responses API data has application-state retention behaviour unless the relevant controls disable storage. [11]

## 32.3 Privacy notice

Before the user first selects a cloud provider, show:

> “Cloud AI mode sends your writing or generation prompts to the selected provider. Use LM Studio for local-only AI processing.”

---

# 33. Security

Even though this is a private single-user application:

## 33.1 Secrets

Never commit:

- OpenAI API key;
- Gemini API key;
- LM Studio API token if configured.

Use `.env` and `.env.example`.

## 33.2 Local bind

Default Docker port exposure should bind to localhost where practical.

Example:

```yaml
ports:
  - "127.0.0.1:3000:3000"
  - "127.0.0.1:8000:8000"
```

Do not automatically expose the application to the internet.

## 33.3 LM Studio network exposure

If LM Studio is exposed beyond localhost, authentication should be considered/enabled. LM Studio itself warns that binding beyond localhost exposes the server to other devices. [12]

---

# 34. Docker Architecture

## 34.1 Core services

```text
┌──────────────────────────────────────────────┐
│ Windows PC                                  │
│                                              │
│  Browser                                     │
│     ↓                                        │
│  Next.js Container                           │
│     ↓                                        │
│  FastAPI Container                           │
│     ↓               ↓                        │
│ PostgreSQL      Local audio volume           │
│                                              │
│  FastAPI ───────────────→ LM Studio Host     │
│                    http://host.docker...     │
└──────────────────────────────────────────────┘
```

## 34.2 `docker-compose.yml` concept

```yaml
services:
  frontend:
    build: ./frontend
    depends_on:
      - backend

  backend:
    build: ./backend
    depends_on:
      - db
    env_file:
      - .env
    volumes:
      - ./data:/app/data

  db:
    image: postgres:latest
    environment:
      POSTGRES_DB: cest
      POSTGRES_USER: cest
      POSTGRES_PASSWORD: change_me
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

Pin actual production versions in the implementation repository rather than using `latest`.

## 34.3 LM Studio

LM Studio runs outside Docker on the Windows host.

The backend reaches it using the configurable `LM_STUDIO_BASE_URL`.

---

# 35. Settings

## 35.1 AI Provider settings

```text
AI Provider

Default:
[ LM Studio ▼ ]

Generation model:
[ ... ]

Writing evaluation model:
[ ... ]

OpenAI: Connected / Not configured
Gemini: Connected / Not configured
LM Studio: Connected / Not connected

[ Test connections ]
```

## 35.2 TTS settings

```text
TTS Provider
[ Local ▼ ]

Voice
[ English voice 1 ▼ ]

Preview
[ Play ]
```

## 35.3 Exam settings

Only non-proprietary simulator settings are exposed:

```text
Reading max time: 59 min
Listening max time: 59 min
Writing time: 45 min

Practice explanations: ON
```

Do not allow the user to casually change core Full Test timing if the goal is realistic simulation. Advanced developer configuration may be available through environment/config files.

---

# 36. Content Generation Prompts — High-Level Contract

The implementation should maintain prompt templates in version-controlled files.

## 36.1 Reading generation prompt must specify

- target task type;
- target CEFR;
- topic;
- scenario;
- word-count range;
- required option count;
- distractor rules;
- exact answer;
- explanation;
- cognitive focus;
- originality requirement;
- no Cambridge proprietary content.

## 36.2 Listening generation prompt must specify

- task type;
- speaker count;
- scenario;
- target CEFR;
- approximate word count;
- natural conversational characteristics;
- exact factual answerability;
- transcript;
- question(s);
- distractor logic;
- explanation.

## 36.3 Writing generation prompt must specify

- Part 1 or Part 2;
- target CEFR;
- audience;
- scenario;
- three bullet points;
- minimum word count;
- register;
- text type;
- originality.

---

# 37. AI Evaluation Prompt — High-Level Contract

The evaluator should be given:

```text
SYSTEM
You are an English-language assessment evaluator for a private practice simulator.
Evaluate the candidate response against the exact task prompt provided.
Do not claim to produce an official Cambridge score.
Return only the requested structured JSON.

INPUT
- CEFR target context
- task type
- audience
- prompt
- required bullet points
- candidate response

OUTPUT
- rubric scores
- estimated CEFR
- evidence
- diagnostics
- corrections
- improvement plan
- confidence
```

The implementation should use provider-specific structured-output capabilities where supported.

---

# 38. Error Handling

## 38.1 AI error

User message:

> “The selected AI provider is currently unavailable. The simulator will retry automatically.”

Do not show raw stack traces to the user.

## 38.2 Writing evaluator unavailable

If all providers fail:

- save the Writing response;
- mark evaluation status `PENDING_RETRY`;
- do not fabricate a score;
- show:

> “Your writing has been saved, but automated evaluation is temporarily unavailable.”

The result must not silently become a guessed CEFR level.

## 38.3 Audio error

If audio fails to load during a Full Test Simulation:

- retry automatically;
- verify local file availability;
- if still unavailable, pause progression without advancing adaptive state;
- log the incident;
- offer a controlled recovery action.

Never score a listening item as answered merely because audio failed.

## 38.4 Database error

The backend must fail safely and must not reset the active session.

---

# 39. Accessibility

Desktop-only does not mean inaccessible.

Required:

- keyboard navigation;
- visible focus states;
- semantic buttons/controls;
- sufficient text contrast;
- no meaning conveyed by colour alone;
- readable font sizes;
- screen-reader friendly labels where technically appropriate.

For Full Test Simulation, accessibility behaviour should not unintentionally introduce extra controls that change the intended test conditions unless a dedicated accessibility mode is later implemented.

---

# 40. Performance Requirements

## 40.1 Normal test operation

- Next objective item request: target < 300 ms locally, excluding heavy generation.
- Database query for next adaptive item: target < 100 ms.
- Audio playback must start without visible buffering after the asset is loaded.
- Full simulation must never synchronously call an LLM to generate the current Reading/Listening question.

## 40.2 AI generation

Question generation can be asynchronous/background.

Example:

```text
Generate 20 items
      ↓
Job queued
      ↓
Progress: 1/20 ... 20/20
      ↓
Review queue
```

## 40.3 Writing evaluation

Because AI generation may take several seconds, show a result state:

```text
Evaluating your writing...

[ progress / spinner ]

Do not close this page.
```

A background job approach is preferred so browser refresh does not lose the evaluation.

---

# 41. Logging and Observability

Log:

- session start/end;
- adaptive selections;
- final theta/SE;
- item validation failures;
- AI provider latency;
- provider failures;
- fallback events;
- TTS failures;
- audio failures;
- unexpected session-state transitions.

Never log:

- API keys;
- raw user writing in normal application logs;
- unnecessary personal data.

For development, structured JSON logs are recommended.

---

# 42. Testing Strategy

## 42.1 Unit tests

### Adaptive engine

Test:

- probability calculation;
- Fisher information;
- EAP estimation;
- standard error;
- stopping logic;
- item exclusion;
- content balancing;
- no item duplication.

### Scoring

Test:

- objective answer matching;
- Open Cloze accepted answers;
- gapped-text mapping;
- CEFR mapping configuration;
- overall-level calculation.

### Timer

Test:

- countdown;
- timeout;
- refresh recovery;
- clock drift handling;
- session deadline enforcement.

## 42.2 Integration tests

Test complete flows:

```text
Start → answer → adaptive next → finish → result
```

for Reading and Listening.

Test:

```text
Start Writing → Part 1 → Part 2 → AI evaluation → result
```

with every AI provider mocked.

## 42.3 Provider contract tests

Every provider adapter must pass the same abstract test suite:

```text
health_check
text_generation
structured_generation
writing_evaluation
error_handling
```

## 42.4 End-to-end tests

At minimum:

1. Start Reading practice.
2. Answer 12 item units.
3. Verify adaptive selection changes after answers.
4. Finish with a stable CEFR estimate.
5. Start Listening simulation.
6. Verify audio plays exactly twice.
7. Verify pause/replay controls are absent.
8. Start Writing simulation.
9. Verify 45-minute deadline.
10. Verify AI result schema.
11. Verify history record.
12. Verify dashboard updates.

---

# 43. Acceptance Criteria — MVP

## 43.1 General

- [ ] App starts entirely from Docker.
- [ ] No normal user login is required.
- [ ] Desktop layout works at 1280×720 and above.
- [ ] Application is clearly labelled as a practice simulator.
- [ ] No official Cambridge result/score claim appears anywhere.

## 43.2 Dashboard

- [ ] Dashboard shows latest Reading, Listening and Writing estimates.
- [ ] Dashboard shows recent sessions.
- [ ] Dashboard shows focus areas.
- [ ] Dashboard has Practice and Full Test actions.

## 43.3 Reading

- [ ] All 9 published CEST General Reading task types are represented in the bank generator.
- [ ] Reading uses adaptive item selection.
- [ ] Reading has a 59-minute hard maximum in Full Test Simulation.
- [ ] Correct answer is not sent to the frontend before submission.
- [ ] The system stores pre/post theta per response.
- [ ] The system reports CEFR estimate + confidence.

## 43.4 Listening

- [ ] 1-item, 2-item and 5-item comprehension structures are implemented.
- [ ] Monologue/dialogue/discussion scenarios are supported.
- [ ] Full Test audio auto-plays twice.
- [ ] Full Test pause is disabled.
- [ ] Full Test replay is disabled.
- [ ] Full Test seeking is disabled.
- [ ] Full Test transcript is hidden.
- [ ] Listening has a 59-minute hard maximum.

## 43.5 Writing

- [ ] Part 1 email is implemented.
- [ ] Part 1 minimum is 50 words.
- [ ] Part 1 recommended time is 15 minutes.
- [ ] Part 2 wider-audience writing is implemented.
- [ ] Part 2 minimum is 180 words.
- [ ] Part 2 recommended time is 30 minutes.
- [ ] Global Writing timer is 45 minutes.
- [ ] Word counter is visible.
- [ ] Automated evaluation returns Communicative Achievement, Organisation and Language scores.
- [ ] AI feedback includes actionable corrections.
- [ ] Provider and model are recorded.

## 43.6 AI providers

- [ ] OpenAI adapter works.
- [ ] Gemini adapter works.
- [ ] LM Studio adapter works.
- [ ] Provider can be selected without changing core scoring logic.
- [ ] Fallback exists for provider failure.
- [ ] Writing provider is locked to one successful provider for a session unless complete failure forces a controlled fallback.

## 43.7 Question generation

- [ ] Content Studio can generate Reading items.
- [ ] Content Studio can generate Listening items.
- [ ] Content Studio can generate Writing prompts.
- [ ] Generated content enters REVIEW status.
- [ ] Only APPROVED content is used by Full Test Simulation.
- [ ] Validation failures are visible.

## 43.8 Storage

- [ ] PostgreSQL is persistent across container restarts.
- [ ] Audio assets persist in a mounted volume.
- [ ] Test history persists.
- [ ] Deleting history does not delete the approved bank.

---

# 44. Recommended Development Phases

## Phase 1 — Foundation

Implement:

- Docker Compose;
- Next.js;
- FastAPI;
- PostgreSQL;
- migrations;
- dashboard skeleton;
- settings;
- basic session model.

## Phase 2 — Reading MVP

Implement:

- MCQ;
- Open Cloze;
- Multiple-choice Cloze;
- Discrete Cloze;
- Discrete with graphic;
- remaining advanced task layouts;
- objective scoring;
- IRT engine;
- Reading result page.

## Phase 3 — Listening MVP

Implement:

- 1/2/5-item tasks;
- local audio assets;
- strict double-play behaviour;
- transcript storage;
- Listening adaptive engine;
- result page.

## Phase 4 — Writing MVP

Implement:

- Part 1;
- Part 2;
- 45-minute timer;
- word counter;
- Writing AI evaluator;
- provider abstraction;
- detailed feedback.

## Phase 5 — Full Test Simulation

Implement:

- session orchestration;
- module sequencing;
- strict timers;
- final result;
- history.

## Phase 6 — Content Studio

Implement:

- generation jobs;
- validation;
- review queue;
- approval;
- bank health.

## Phase 7 — Refinement

Improve:

- UX fidelity;
- question quality;
- CEFR calibration;
- AI evaluation quality;
- local TTS quality;
- performance;
- accessibility.

---

# 45. Future Calibration Plan

The most important long-term limitation is not the frontend. It is **item calibration and writing-score validity**.

The simulator should therefore save anonymised item response statistics locally so that future versions can improve calibration.

## 45.1 Reading/Listening item calibration

For each item, eventually estimate:

- difficulty;
- empirical facility;
- exposure;
- point-biserial or related diagnostic;
- task type performance;
- estimated CEFR alignment.

Initially, `difficulty_theta` is a generated/configured value. After enough responses, it can be recalibrated.

## 45.2 Writing calibration

Future versions may collect a personally labelled reference set and compare AI ratings to human ratings.

Metrics to monitor:

- correlation with human rubric scores;
- level classification agreement;
- false positive / false negative level classification;
- inter-rater consistency;
- provider-to-provider variation.

This should be treated as an assessment research problem, not just an LLM prompt-engineering problem.

---

# 46. Important Product Decisions Already Locked

```text
Product name:
CEST Practice Simulator

Target:
Private personal preparation

CEST version:
General

Skills:
Reading + Listening + Writing

Speaking:
No

Level range:
A1–C1

Reading:
Adaptive

Listening:
Adaptive

Adaptive model:
Rasch / 1PL IRT + EAP

Practice mode:
Yes

Full simulation:
Yes

Writing:
AI evaluated

Writing structure:
Part 1 email + Part 2 wider-audience writing

Writing timing:
15 min recommendation + 30 min recommendation = 45 min total

Listening playback in simulation:
Exactly twice

Listening playback in practice:
Pause/replay allowed

Login:
No

Dashboard:
Yes

History:
Yes

Progress graphs:
No

Question source:
AI-generated original content bank

Question generation:
Pre-generate + validate + approve

AI providers:
OpenAI + Gemini + LM Studio

Fallback:
Yes

LM Studio:
Run on local PC host, reached by Docker backend

Deployment:
Docker on PC

Public VPS:
No

Primary UI language:
Indonesian

Test content language:
English

Writing feedback:
English + Indonesian explanatory support may be offered in UI

Device target:
Desktop only
```

---

# 47. UX Copy Guidelines

The interface should use Indonesian for navigation while retaining English for test content.

Examples:

| UI | Copy |
|---|---|
| Dashboard | Dashboard |
| Start full test | Mulai Simulasi Penuh |
| Practice | Latihan |
| Result | Hasil |
| History | Riwayat |
| Time remaining | Waktu tersisa |
| Next | Berikutnya |
| Submit | Kirim jawaban |
| Explanation | Penjelasan |
| Correct answer | Jawaban benar |
| Estimated level | Perkiraan level |
| Confidence | Tingkat keyakinan |
| Focus area | Area yang perlu dilatih |
| Writing evaluation | Evaluasi tulisan |
| Word count | Jumlah kata |

Test prompts themselves remain in English.

---

# 48. Design Direction

## 48.1 Visual goal

The visual direction should feel like a serious computer-delivered English assessment rather than a language-learning game.

Characteristics:

- clean white/neutral canvas;
- strong hierarchy;
- restrained accent colour;
- large readable exam content;
- fixed timer region;
- unobtrusive controls;
- minimal animations during a timed test.

## 48.2 Exam screen principles

- Content gets most of the screen.
- Timer is always visible during timed modules.
- Next/continue control is obvious.
- Avoid unnecessary side panels in simple tasks.
- For long reading texts, preserve comfortable reading width.
- Do not use decorative widgets that consume attention.

---

# 49. Definition of Done

The project is considered MVP-complete when the user can:

1. Open the application in a desktop browser.
2. See a dashboard without logging in.
3. Start Reading Practice.
4. Complete an adaptive Reading session.
5. Receive an estimated A1–C1 Reading level and detailed review.
6. Start Listening Practice.
7. Complete Listening tasks with relaxed controls and transcript/explanation review.
8. Start Writing Practice.
9. Complete an email and/or wider-audience task.
10. Receive structured AI feedback.
11. Start a Full Test Simulation.
12. Complete Reading + Listening + Writing under the simulator's exam conditions.
13. Receive one detailed result covering the three modules.
14. View the test in History later.
15. Generate new question-bank content through Content Studio.
16. Switch between LM Studio, OpenAI and Gemini without changing the exam engine.
17. Run the application locally using Docker with persistent data.

---

# 50. Source References

These references are included so the implementation team/AI agent can distinguish **verified Cambridge facts** from **simulator design choices**.

[1] Cambridge English — Cambridge English Skills Test General. Published test description, modules, durations, adaptive testing and reporting.  
https://www.cambridgeenglish.org/exams-and-tests/cambridge-english-skills-test/general/

[2] Cambridge English — *Cambridge English Skills Test General: Reading* (document 735975). Official task-type and Reading construct description.  
https://www.cambridgeenglish.org/Images/735975-cest-general-reading.pdf

[3] Cambridge English — *Cambridge English Skills Test General: Listening* (document 735974). Official Listening task-type and construct description.  
https://www.cambridgeenglish.org/Images/735974-cest-general-listening.pdf

[4] Cambridge English — *Cambridge English Skills Test General Listening Candidate Advice* (document 731666). Public candidate instructions showing automatic two-play listening behaviour.  
https://www.cambridgeenglish.org/gr/Images/731666-cest-adults-listening-candidate-advice.pdf

[5] Cambridge English — *Cambridge English Skills Test General Writing Candidate Advice* (document 731664). Public candidate instructions for Part 1/Part 2, timing and word minimums.  
https://www.cambridgeenglish.org/vn/Images/731664-cest-adults-writing-candidate-advice.pdf

[6] Cambridge English — *Cambridge English Skills Test Writing Assessment Criteria* (document 731660). Official Writing criteria organised by CEFR, Communicative Achievement, Organisation and Language.  
https://www.cambridgeenglish.org/Images/731660-cambridge-english-skills-test-writing-assessment-criteria.pdf

[7] OpenAI — Developer Quickstart / Responses API. Current official API documentation used as a reference for provider integration.  
https://platform.openai.com/docs/quickstart/make-your-first-api-request

[8] Google AI for Developers — Gemini API, Generate Content. Current official Gemini API documentation.  
https://ai.google.dev/api/generate-content

[9] LM Studio — OpenAI-compatible endpoints and local server documentation.  
https://lmstudio.ai/docs/developer/openai-compat

[10] LM Studio — Offline operation documentation.  
https://lmstudio.ai/docs/app/offline

[11] OpenAI — API data controls / application state documentation.  
https://platform.openai.com/docs/models/default-usage-policies-by-endpoint

[12] LM Studio — Serve on Local Network / local server exposure guidance.  
https://lmstudio.ai/docs/developer/core/server/serve-on-network

---

# 51. Implementation Notes for the AI Coding Agent

The coding agent should follow these rules while implementing the application:

1. **Do not invent official CEST details.** When the PRD says “official” or “published”, use the cited source.
2. **Do not claim proprietary replication.** The simulator mimics the public construct and timing, not internal Cambridge algorithms.
3. **Keep exam logic server-authoritative.** The browser must not decide adaptive item selection, scoring or remaining official test time by itself.
4. **Keep AI providers behind interfaces.** No OpenAI/Gemini/LM Studio-specific code in core evaluation logic.
5. **Never generate live exam questions during an active Full Test unless the system is explicitly configured for a future experimental mode.** Use approved pre-generated items.
6. **Treat Writing AI as probabilistic.** Save provider/model/version and never fabricate a score when evaluation fails.
7. **Make calibration configurable.** CEFR/theta thresholds must live in configuration and be easy to recalibrate.
8. **Use migrations for all schema changes.** Do not modify the PostgreSQL schema manually.
9. **Add tests before implementing complex adaptive logic.** In particular, test EAP estimation, stopping rules and item selection.
10. **Prefer transparent failure over silent incorrect scoring.** If the system cannot reliably score a response, mark the result unavailable/pending rather than guessing.
11. **Keep the interface desktop-first.** Do not spend MVP effort on mobile layouts.
12. **Keep the exam interface quiet.** No distracting animations, gamification or unnecessary controls during Full Test Simulation.
13. **Maintain the disclaimer visibly in About/Settings and preferably in the initial Full Test instructions.**
14. **Use original generated content only.** Never copy official Cambridge sample questions into the database.
15. **Record content version on every response.** A result must remain reproducible even after question-bank updates.

---

# 52. Final Product Principle

The most important design principle is:

> **Make the experience feel like a serious CEST-style preparation environment, while being completely honest that the adaptive engine, scoring, AI writing assessment and question bank are the simulator's own implementation.**

The application should optimise for **realistic practice, useful diagnostics, reproducibility and local control**, not for pretending to be an official Cambridge test.
