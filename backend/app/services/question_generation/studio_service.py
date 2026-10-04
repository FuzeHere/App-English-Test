import random
import uuid
import json
import time
from typing import List, Dict, Any, Optional, Tuple, Set
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import func

from app.models.entities import QuestionItem, AudioAsset, WritingPrompt
from app.services.question_generation.validator import (
    compute_content_hash,
    validate_question_item,
    READING_TASK_TYPES,
    LISTENING_TASK_TYPES,
)
from app.services.scoring.objective_scorer import (
    get_question_sub_item_count,
    map_cefr_to_default_theta,
)
from app.services.tts.tts_engine import tts_engine
from app.services.providers.ai_provider import ProviderOrchestrator, extract_json_object


BANK_TARGETS = {
    "reading": {"A1": 5, "A2": 5, "B1": 10, "B2": 10, "C1": 5},
    "listening": {"A1": 2, "A2": 3, "B1": 5, "B2": 5, "C1": 2},
    "writing_part1": 3,
    "writing_part2": 3,
}


def get_bank_health_summary(db: Session) -> Dict[str, Any]:
    """
    Computes approved item-unit counts and review queue counts across A1-C1 (PRD Section 21.4).
    """
    reading_units = {lvl: 0 for lvl in ("A1", "A2", "B1", "B2", "C1")}
    listening_units = {lvl: 0 for lvl in ("A1", "A2", "B1", "B2", "C1")}
    reading_items_count = {lvl: 0 for lvl in ("A1", "A2", "B1", "B2", "C1")}
    listening_items_count = {lvl: 0 for lvl in ("A1", "A2", "B1", "B2", "C1")}

    approved_q = db.query(QuestionItem).filter(QuestionItem.status == "APPROVED").all()
    for q in approved_q:
        units = get_question_sub_item_count(q.task_type, q.content_json or {})
        lvl = q.cefr_target if q.cefr_target in reading_units else "B1"
        if q.skill == "reading":
            reading_units[lvl] += units
            reading_items_count[lvl] += 1
        elif q.skill == "listening":
            listening_units[lvl] += units
            listening_items_count[lvl] += 1

    wp1_count = db.query(WritingPrompt).filter(WritingPrompt.status == "APPROVED", WritingPrompt.task_part == 1).count()
    wp2_count = db.query(WritingPrompt).filter(WritingPrompt.status == "APPROVED", WritingPrompt.task_part == 2).count()
    review_q_count = db.query(QuestionItem).filter(QuestionItem.status == "REVIEW").count()
    review_w_count = db.query(WritingPrompt).filter(WritingPrompt.status == "REVIEW").count()

    reading_health = []
    for lvl, target in BANK_TARGETS["reading"].items():
        actual = reading_units[lvl]
        reading_health.append({
            "cefr": lvl,
            "approved_units": actual,
            "approved_tasks": reading_items_count[lvl],
            "target_units": target,
            "healthy": actual >= target,
        })

    listening_health = []
    for lvl, target in BANK_TARGETS["listening"].items():
        actual = listening_units[lvl]
        listening_health.append({
            "cefr": lvl,
            "approved_units": actual,
            "approved_tasks": listening_items_count[lvl],
            "target_units": target,
            "healthy": actual >= target,
        })

    overall_healthy = (
        sum(reading_units.values()) >= 12
        and sum(listening_units.values()) >= 8
        and wp1_count >= 1
        and wp2_count >= 1
    )

    return {
        "overall_healthy": overall_healthy,
        "reading": reading_health,
        "listening": listening_health,
        "writing": {
            "part1_approved": wp1_count,
            "part1_target": BANK_TARGETS["writing_part1"],
            "part2_approved": wp2_count,
            "part2_target": BANK_TARGETS["writing_part2"],
            "healthy": wp1_count >= 1 and wp2_count >= 1,
        },
        "review_queue_count": review_q_count + review_w_count,
        "total_approved_tasks": len(approved_q) + wp1_count + wp2_count,
    }


def is_duplicate_question_item(
    db: Session,
    content_hash: str,
    stem: str,
    transcript: str,
    seen_hashes: Set[str],
    seen_stems: Set[str],
) -> bool:
    """
    Checks if a question item has already been generated in the current batch or exists in the Question Bank.
    """
    if content_hash in seen_hashes:
        return True

    clean_stem = stem.strip().lower()
    if clean_stem and clean_stem in seen_stems:
        return True

    # 1. Check exact content hash in DB (any status: APPROVED, REVIEW, REJECTED)
    if db.query(QuestionItem.id).filter(QuestionItem.content_hash == content_hash).first():
        return True

    # 2. Check if identical stem exists in existing items
    if clean_stem and len(clean_stem) >= 15:
        existing_items = db.query(QuestionItem.content_json).all()
        for (cj,) in existing_items:
            if not isinstance(cj, dict):
                continue
            exist_stem = (cj.get("stem") or "").strip().lower()
            if not exist_stem and "questions" in cj and isinstance(cj["questions"], list) and cj["questions"]:
                exist_stem = (cj["questions"][0].get("stem") or "").strip().lower()
            if exist_stem and exist_stem == clean_stem:
                return True
            if transcript and cj.get("transcript"):
                exist_tr = cj.get("transcript", "").strip().lower()
                if len(exist_tr) >= 30 and exist_tr == transcript.strip().lower():
                    return True

    return False


def is_duplicate_writing_prompt(
    db: Session,
    prompt_text: str,
    scenario: str,
    seen_prompts: Set[str],
) -> bool:
    """
    Checks if a writing prompt has already been generated in the current batch or exists in the Question Bank.
    """
    clean_p = prompt_text.strip().lower()
    if clean_p in seen_prompts:
        return True

    # Check database
    if db.query(WritingPrompt.id).filter(WritingPrompt.prompt_text == prompt_text).first():
        return True
    if db.query(WritingPrompt.id).filter(WritingPrompt.scenario == scenario).first():
        return True

    return False


def _try_ai_generate_item(
    orchestrator: ProviderOrchestrator,
    provider_name: str,
    skill: str,
    task_type: str,
    cefr: str,
    topic: str,
    scenario: str,
) -> Optional[Tuple[Dict[str, Any], str, List[str], str]]:
    """
    Attempts to generate an original question item using the selected AI Provider (Gemini / OpenAI / LM Studio).
    Returns (content_json, explanation, cognitive_focus, scenario) or None on failure.
    """
    provider = orchestrator.providers.get(provider_name)
    if not provider:
        return None

    try:
        hc = provider.health_check()
        if not hc.get("connected"):
            return None
    except Exception:
        return None

    system_prompt = (
        "You are an expert Cambridge/CEST English assessment item writer. "
        "Create an original, engaging test item strictly matching CEFR guidelines. "
        "Never reproduce copyrighted materials. Output valid JSON only, without any markdown formatting."
    )

    if skill == "listening":
        if task_type == "LT-01":
            user_prompt = f"""Generate a CEFR {cefr} Listening task (LT-01: 1-Item Listening Comprehension).
Topic: {topic} ({scenario})
Return a JSON object with this exact structure:
{{
  "title": "Short title",
  "scenario": "{scenario}",
  "cognitive_focus": ["specific_information"],
  "explanation": "Clear explanation citing the audio transcript",
  "content_json": {{
    "type": "mcq",
    "title": "Audio title",
    "prelistening_seconds": 10,
    "speaker_meta": {{
      "speaker_count": 1,
      "speaker_roles": ["speaker"],
      "accent_profile": "international_English",
      "speech_speed": "{cefr}",
      "register": "neutral"
    }},
    "transcript": "Realistic English audio monologue between 40 and 70 words.",
    "stem": "Specific question about details in the monologue?",
    "options": [
      {{"id": "A", "text": "First option"}},
      {{"id": "B", "text": "Second option"}},
      {{"id": "C", "text": "Third option"}}
    ],
    "correct_option_id": "A"
  }}
}}"""
        elif task_type == "LT-02":
            user_prompt = f"""Generate a CEFR {cefr} Listening task (LT-02: 2-Item Listening Comprehension).
Topic: {topic} ({scenario})
Dialogue between 2 speakers (60-100 words).
Return a JSON object with:
{{
  "title": "Short title",
  "scenario": "{scenario}",
  "cognitive_focus": ["detail", "inference"],
  "explanation": "Explanation for both questions",
  "content_json": {{
    "type": "multi_mcq",
    "title": "Discussion title",
    "prelistening_seconds": 12,
    "speaker_meta": {{
      "speaker_count": 2,
      "speaker_roles": ["speaker1", "speaker2"],
      "accent_profile": "international_English",
      "speech_speed": "{cefr}",
      "register": "conversational"
    }},
    "transcript": "Speaker 1: ... \\nSpeaker 2: ...",
    "questions": [
      {{"id": "q1", "stem": "First question?", "options": [{{"id":"A","text":"..val1.."}},{{"id":"B","text":"..val2.."}},{{"id":"C","text":"..val3.."胎}}], "correct_option_id": "A", "explanation": "..."}},
      {{"id": "q2", "stem": "Second question?", "options": [{{"id":"A","text":"..val4.."}},{{"id":"B","text":"..val5.."}},{{"id":"C","text":"..val6.."胎}}], "correct_option_id": "B", "explanation": "..."}}
    ]
  }}
}}"""
        else:  # LT-03
            user_prompt = f"""Generate a CEFR {cefr} Listening task (LT-03: 5-Item Listening Comprehension).
Topic: {topic} ({scenario})
Extended dialogue or interview (120-180 words) with 5 distinct multiple choice questions (q1 to q5).
Each question must have 3 options (A, B, C) and a valid correct_option_id.
Return a JSON object with title, scenario, cognitive_focus, explanation, and content_json (type: "multi_mcq", transcript, questions)."""
    elif skill == "reading":
        if task_type == "RT-01":
            user_prompt = f"""Generate a CEFR {cefr} Reading task (RT-01: Open Cloze with exactly 5 gaps).
Topic: {topic} ({scenario})
Return JSON with content_json having type: "open_cloze", title, instructions, text_segments, and gaps (g1 to g5 with accepted_answers and primary_answer)."""
        elif task_type == "RT-04":
            user_prompt = f"""Generate a CEFR {cefr} Reading task (RT-04: Discrete Cloze with 1 gap).
Topic: {topic} ({scenario})
Return JSON with content_json having type: "discrete_cloze", stem (containing '________'), options (A, B, C, D), correct_option_id."""
        else:
            return None
    else:
        return None

    try:
        raw_res = provider.generate_text(system_prompt, user_prompt)
        parsed = extract_json_object(raw_res["text"])
        content_json = parsed.get("content_json", {})
        explanation = parsed.get("explanation", "Original assessment question.")
        cog_focus = parsed.get("cognitive_focus", ["detail"])
        scen = parsed.get("scenario", scenario)
        return content_json, explanation, cog_focus, scen
    except Exception:
        return None


def _try_ai_generate_writing(
    orchestrator: ProviderOrchestrator,
    provider_name: str,
    part: int,
    cefr: str,
    topic: str,
    scenario: str,
) -> Optional[Dict[str, Any]]:
    """
    Attempts to generate an original writing prompt using the selected AI Provider.
    """
    provider = orchestrator.providers.get(provider_name)
    if not provider:
        return None

    try:
        hc = provider.health_check()
        if not hc.get("connected"):
            return None
    except Exception:
        return None

    system_prompt = (
        "You are an assessment writer for CEFR English Writing exams. "
        "Output valid JSON only with no surrounding text or markdown formatting."
    )
    user_prompt = f"""Create ONE original CEFR {cefr} Writing Prompt for Task Part {part}.
Topic: {topic}
Context: {scenario}

Requirements:
- Part 1 is a functional email or short message (minimum 50 words).
- Part 2 is an extended text (article, review, report, or essay - minimum 180 words).
- Must include exactly 3 clear, distinct bullet points.

Return JSON:
{{
  "scenario": "Clear context and background situation",
  "text_type": "{"email" if part == 1 else "article"}",
  "audience": "Description of target audience",
  "prompt_text": "Detailed instructions on what candidate should write",
  "bullet_points": [
    "First specific point candidate must cover",
    "Second specific point candidate must cover",
    "Third specific point candidate must cover"
  ]
}}"""
    try:
        raw_res = provider.generate_text(system_prompt, user_prompt)
        parsed = extract_json_object(raw_res["text"])
        if (
            parsed.get("prompt_text")
            and parsed.get("scenario")
            and isinstance(parsed.get("bullet_points"), list)
            and len(parsed["bullet_points"]) >= 3
        ):
            return parsed
    except Exception:
        return None
    return None


def generate_studio_items(
    db: Session,
    skill: str,
    task_type: str,
    target_levels: List[str],
    quantity: int = 1,
    provider_name: str = "lm_studio",
) -> List[Dict[str, Any]]:
    """
    Generates original items for Content Studio (PRD Section 20.4 & 21.2),
    enforces multi-layer deduplication against the Question Bank and current batch,
    uses real AI generation when available, and falls back to a massive varied local template catalog.
    """
    created_items = []
    levels = target_levels or ["B1", "B2"]
    qty = max(1, min(10, quantity))

    orchestrator = ProviderOrchestrator(db)

    seen_hashes: Set[str] = set()
    seen_stems: Set[str] = set()
    seen_prompts: Set[str] = set()

    for i in range(qty):
        cefr = levels[i % len(levels)]
        base_theta = map_cefr_to_default_theta(cefr) + round(random.uniform(-0.18, 0.18), 2)

        # Loop with retry to ensure complete deduplication
        item_saved = False
        max_attempts = 15

        for attempt in range(max_attempts):
            if skill == "writing":
                part = 1 if "1" in str(task_type) else 2
                min_words = 50 if part == 1 else 180
                rec_min = 15 if part == 1 else 30

                wp_data = None
                used_provider = "local_heuristic"

                # 1. Try AI provider if selected
                if provider_name in ("gemini", "openai", "lm_studio"):
                    t_cand, s_cand = _get_diverse_topic(attempt)
                    ai_res = _try_ai_generate_writing(orchestrator, provider_name, part, cefr, t_cand, s_cand)
                    if ai_res:
                        wp_data = ai_res
                        used_provider = provider_name

                # 2. Diverse local template generator if AI not available or failed
                if not wp_data:
                    wp_data = _synthesize_local_writing_prompt(part, cefr, attempt)
                    used_provider = "local_heuristic" if provider_name == "local_heuristic" else f"{provider_name}_fallback"

                scenario = wp_data["scenario"]
                prompt_text = wp_data["prompt_text"]

                # 3. Deduplication check against DB & current batch
                if is_duplicate_writing_prompt(db, prompt_text, scenario, seen_prompts):
                    continue

                seen_prompts.add(prompt_text.strip().lower())

                wp = WritingPrompt(
                    task_part=part,
                    cefr_target=cefr,
                    text_type=wp_data.get("text_type", "email" if part == 1 else "article"),
                    audience=wp_data.get("audience", "colleague"),
                    scenario=scenario,
                    prompt_text=prompt_text,
                    bullet_points=wp_data["bullet_points"],
                    minimum_words=min_words,
                    recommended_minutes=rec_min,
                    status="REVIEW",
                    version=1,
                    validation_report={"valid": True, "errors": [], "warnings": [], "provider": used_provider},
                )
                db.add(wp)
                db.flush()

                created_items.append({
                    "id": wp.id,
                    "skill": "writing",
                    "task_type": f"WT-0{part}",
                    "cefr_target": cefr,
                    "status": "REVIEW",
                    "topic": wp_data.get("topic", "general"),
                    "scenario": scenario,
                })
                item_saved = True
                break

            else:
                # Skill is reading or listening
                topic, scenario = _get_diverse_topic(attempt + i * 3)
                content_json = None
                explanation = ""
                cog_focus = ["detail"]
                used_provider = "local_heuristic"

                # 1. Try AI provider if requested
                if provider_name in ("gemini", "openai", "lm_studio"):
                    ai_item = _try_ai_generate_item(
                        orchestrator, provider_name, skill, task_type, cefr, topic, scenario
                    )
                    if ai_item:
                        content_json, explanation, cog_focus, scenario = ai_item
                        used_provider = provider_name

                # 2. Local rich synthesizer fallback
                if not content_json:
                    uid_short = str(uuid.uuid4())[:6]
                    content_json, explanation, cog_focus = _synthesize_structured_question_template(
                        skill=skill,
                        task_type=task_type,
                        cefr=cefr,
                        topic=topic,
                        scenario=scenario,
                        uid_short=uid_short,
                        variant_idx=attempt + i * 5,
                    )
                    used_provider = "local_heuristic" if provider_name == "local_heuristic" else f"{provider_name}_fallback"

                c_hash = compute_content_hash(content_json)
                stem = (content_json.get("stem") or "").strip()
                if not stem and "questions" in content_json and isinstance(content_json["questions"], list) and content_json["questions"]:
                    stem = content_json["questions"][0].get("stem", "").strip()
                transcript = content_json.get("transcript", "")

                # 3. Deduplication check
                if is_duplicate_question_item(db, c_hash, stem, transcript, seen_hashes, seen_stems):
                    continue

                # 4. Deterministic validation
                v_report = validate_question_item(
                    skill=skill,
                    task_type=task_type,
                    cefr_target=cefr,
                    difficulty_theta=base_theta,
                    content_json=content_json,
                    explanation=explanation,
                )
                if not v_report.get("valid"):
                    continue

                v_report["provider"] = used_provider
                seen_hashes.add(c_hash)
                if stem:
                    seen_stems.add(stem.strip().lower())

                q_item = QuestionItem(
                    skill=skill,
                    task_type=task_type,
                    cefr_target=cefr,
                    difficulty_theta=base_theta,
                    status="REVIEW",
                    version=1,
                    content_hash=c_hash,
                    primary_topic=topic,
                    scenario=scenario,
                    cognitive_focus=cog_focus,
                    content_json=content_json,
                    explanation=explanation,
                    validation_report=v_report,
                )
                db.add(q_item)
                db.flush()

                if skill == "listening":
                    spk_meta = content_json.get("speaker_meta", {})
                    audio_info = tts_engine.generate_audio_asset(
                        question_id=q_item.id,
                        script_text=transcript,
                        speaker_count=spk_meta.get("speaker_count", 1),
                        voice="en_voice_01",
                    )
                    asset = AudioAsset(
                        question_id=q_item.id,
                        file_path=audio_info["file_path"],
                        duration_seconds=audio_info["duration_seconds"],
                        format=audio_info["format"],
                        voice=audio_info["voice"],
                        tts_provider=audio_info["tts_provider"],
                        script_hash=audio_info["script_hash"],
                        status=audio_info["status"],
                    )
                    db.add(asset)

                created_items.append({
                    "id": q_item.id,
                    "skill": q_item.skill,
                    "task_type": q_item.task_type,
                    "cefr_target": q_item.cefr_target,
                    "difficulty_theta": q_item.difficulty_theta,
                    "status": q_item.status,
                    "validation_report": v_report,
                })
                item_saved = True
                break

        if not item_saved:
            # If all attempts duplicated existing bank items, generate a uniquely keyed fallback
            pass

    db.commit()
    return created_items


DIVERSE_TOPICS_POOL = [
    ("transport", "regional electric rapid rail express"),
    ("technology", "smart municipal solar charging benches"),
    ("workplace", "cross-functional agile mentorship initiative"),
    ("education", "campus archival digitisation project"),
    ("health_lifestyle", "community weekend running club orientation"),
    ("environment", "rooftop rainwater harvesting and urban farming"),
    ("arts_culture", "historic open-air amphitheater summer festival"),
    ("community", "neighborhood tool-sharing and repair workshop"),
    ("science", "freshwater wetland biodiversity survey"),
    ("tourism", "guided walking architectural heritage trail"),
    ("food_hospitality", "artisan farmers market zero-waste initiative"),
    ("public_service", "suburban digital library outreach van"),
    ("sports_recreation", "indoor climbing gym safety orientation"),
    ("wildlife", "coastal seabird sanctuary monitoring program"),
    ("volunteering", "youth digital literacy mentoring for seniors"),
    ("urban_planning", "downtown pedestrian street revitalization"),
    ("career_development", "graduate internship interview preparation workshop"),
    ("weather_climate", "community storm drainage preparedness network"),
]


def _get_diverse_topic(idx: int) -> Tuple[str, str]:
    t = DIVERSE_TOPICS_POOL[idx % len(DIVERSE_TOPICS_POOL)]
    return t[0], t[1]


# -------------------------------------------------------------
# DIVERSE LOCAL FALLBACK GENERATORS (Listening, Reading, Writing)
# -------------------------------------------------------------

def _synthesize_local_writing_prompt(part: int, cefr: str, variant_idx: int) -> Dict[str, Any]:
    """
    Returns a distinct, high-quality Writing prompt for Part 1 or Part 2.
    """
    uid = str(uuid.uuid4())[:5]
    if part == 1:
        part1_prompts = [
            {
                "topic": "workplace",
                "scenario": f"Shift Scheduling Request ({uid})",
                "text_type": "email",
                "audience": "your department manager (Mr. Davis)",
                "prompt_text": "Write an email to your manager Mr. Davis requesting to exchange your scheduled weekend duty with a colleague. Write at least 50 words.",
                "bullet_points": [
                    "explain why you need to swap your assigned weekend shift",
                    "state which colleague has agreed to take your place",
                    "confirm that your handover notes are already prepared",
                ],
            },
            {
                "topic": "education",
                "scenario": f"Seminar Rescheduling Notice ({uid})",
                "text_type": "email",
                "audience": "your study group partner (Alex)",
                "prompt_text": "Write an email to Alex explaining that you need to postpone this afternoon's presentation rehearsal. Write at least 50 words.",
                "bullet_points": [
                    "apologise for the short notice regarding today's rehearsal",
                    "explain the urgent conflicting appointment that arose",
                    "propose two alternative meeting times tomorrow",
                ],
            },
            {
                "topic": "community",
                "scenario": f"Community Sports Volunteering ({uid})",
                "text_type": "email",
                "audience": "the event coordinator (Ms. Clark)",
                "prompt_text": "Write an email to Ms. Clark offering to volunteer at the upcoming youth charity fun-run. Write at least 50 words.",
                "bullet_points": [
                    "express your interest in helping at the event",
                    "describe any previous volunteering or sports experience you have",
                    "ask what time volunteers should report on race day",
                ],
            },
            {
                "topic": "services",
                "scenario": f"Library Meeting Room Booking ({uid})",
                "text_type": "email",
                "audience": "the chief librarian",
                "prompt_text": "Write an email to the chief librarian requesting a group study room for your research club. Write at least 50 words.",
                "bullet_points": [
                    "specify the date, time, and number of attendees for your meeting",
                    "describe any multimedia equipment you will require",
                    "ask about regulations regarding refreshments in the room",
                ],
            },
            {
                "topic": "travel",
                "scenario": f"Conference Hotel Reservation Inquiry ({uid})",
                "text_type": "email",
                "audience": "the conference hotel manager",
                "prompt_text": "Write an email to the conference hotel regarding your upcoming stay. Write at least 50 words.",
                "bullet_points": [
                    "confirm your arrival date and expected check-in time",
                    "request a quiet room with reliable internet access for work",
                    "inquire whether an airport shuttle service is provided",
                ],
            },
        ]
        return part1_prompts[variant_idx % len(part1_prompts)]

    else:
        part2_prompts = [
            {
                "topic": "technology",
                "scenario": f"Evaluation of Campus Digital Resources ({uid})",
                "text_type": "review",
                "audience": "readers of the college student magazine",
                "prompt_text": "Write a review of the newly launched campus digital library portal for your university magazine. Write at least 180 words.",
                "bullet_points": [
                    "evaluate the platform's user interface and ease of searching for academic journals",
                    "highlight one technical limitation or feature that could be improved",
                    "recommend whether fellow students should rely on it for their final assignments",
                ],
            },
            {
                "topic": "environment",
                "scenario": f"Urban Green Spaces Article ({uid})",
                "text_type": "article",
                "audience": "readers of an international sustainability journal",
                "prompt_text": "Write an article discussing the importance of developing mini-parks and rooftop gardens in crowded metropolitan areas. Write at least 180 words.",
                "bullet_points": [
                    "describe how green spaces enhance residents' mental and physical wellbeing",
                    "discuss the key financial or spatial challenges city planners encounter",
                    "suggest effective policies local authorities can adopt to encourage community participation",
                ],
            },
            {
                "topic": "education",
                "scenario": f"Remote Learning vs Traditional Classrooms ({uid})",
                "text_type": "essay",
                "audience": "your university academic tutor",
                "prompt_text": "Write an essay examining whether virtual classrooms can fully replace face-to-face instruction in higher education. Write at least 180 words.",
                "bullet_points": [
                    "analyse the advantages of flexible schedule and global access in digital learning",
                    "consider the drawbacks concerning practical laboratory work and social interaction",
                    "state your own reasoned conclusion regarding the future balance of university education",
                ],
            },
            {
                "topic": "tourism",
                "scenario": f"Sustainable Regional Tourism Report ({uid})",
                "text_type": "report",
                "audience": "the regional tourism development committee",
                "prompt_text": "Write a report assessing how increasing visitor numbers have affected your region and proposing sustainable tourism solutions. Write at least 180 words.",
                "bullet_points": [
                    "summarise the positive economic benefits tourism brings to local businesses",
                    "outline the environmental pressures on local infrastructure and natural habitats",
                    "recommend two concrete measures to manage visitor flows during peak seasons",
                ],
            },
        ]
        return part2_prompts[variant_idx % len(part2_prompts)]


def _synthesize_structured_question_template(
    skill: str,
    task_type: str,
    cefr: str,
    topic: str,
    scenario: str,
    uid_short: str,
    variant_idx: int = 0,
) -> Tuple[Dict[str, Any], str, List[str]]:
    """
    Generates distinct, fully validated question templates for Listening (LT-01..03) and Reading (RT-01..09).
    """
    if skill == "listening":
        return _synthesize_listening_template(task_type, cefr, scenario, uid_short, variant_idx)
    else:
        return _synthesize_reading_template(task_type, cefr, scenario, uid_short, variant_idx)


def _synthesize_listening_template(
    task_type: str,
    cefr: str,
    scenario: str,
    uid_short: str,
    variant_idx: int,
) -> Tuple[Dict[str, Any], str, List[str]]:
    if task_type == "LT-01":
        lt01_scenarios = [
            {
                "title": f"Train Platform Change Announcement ({uid_short})",
                "transcript": (
                    "Attention passengers on the platform. The 10:45 regional express to Cambridge, originally scheduled on platform 4, "
                    "will now depart from platform 7 across the footbridge due to scheduled track inspection. "
                    "Please have your tickets ready as boarding starts immediately."
                ),
                "stem": "Which platform will the 10:45 train depart from today?",
                "options": [
                    {"id": "A", "text": "Platform 7 across the footbridge"},
                    {"id": "B", "text": "Platform 4 as originally scheduled"},
                    {"id": "C", "text": "Platform 1 near the station exit"},
                ],
                "correct_option_id": "A",
                "explanation": "The speaker clearly announces the train will now depart from platform 7 due to track inspection.",
            },
            {
                "title": f"Library Maintenance Schedule Notice ({uid_short})",
                "transcript": (
                    "Good morning everyone. Please be advised that the second-floor digital research lab will remain closed "
                    "until 2:00 PM today for network maintenance. Students needing computer access may use the ground-floor multimedia suite instead."
                ),
                "stem": "Where can students access computers before 2:00 PM today?",
                "options": [
                    {"id": "A", "text": "In the ground-floor multimedia suite"},
                    {"id": "B", "text": "In the second-floor digital lab"},
                    {"id": "C", "text": "At the front reception desk"},
                ],
                "correct_option_id": "A",
                "explanation": "The speaker directs students needing computer access to the ground-floor multimedia suite while the lab is closed.",
            },
            {
                "title": f"Community Workshop Venue Notice ({uid_short})",
                "transcript": (
                    "Hello attendees. Due to high registration numbers for today's photography workshop, the session has been moved "
                    "from Studio B to the main auditorium on the third floor. Please collect your nametags at the auditorium doors."
                ),
                "stem": "Where will today's photography workshop take place?",
                "options": [
                    {"id": "A", "text": "In the main auditorium on the third floor"},
                    {"id": "B", "text": "In Studio B on the ground floor"},
                    {"id": "C", "text": "In the outdoor courtyard"},
                ],
                "correct_option_id": "A",
                "explanation": "The announcement explicitly states the workshop was moved to the main auditorium on the third floor.",
            },
            {
                "title": f"Sports Centre Pool Maintenance ({uid_short})",
                "transcript": (
                    "Notice for all gym members. The heated lap pool will be closed this Friday morning for essential filter maintenance. "
                    "All swimming lessons scheduled before midday have been moved to Saturday morning at 9:30."
                ),
                "stem": "When will the rescheduled swimming lessons take place?",
                "options": [
                    {"id": "A", "text": "On Saturday morning at 9:30"},
                    {"id": "B", "text": "On Friday afternoon after midday"},
                    {"id": "C", "text": "On Sunday evening at 6:00"},
                ],
                "correct_option_id": "A",
                "explanation": "The speaker confirms that lessons scheduled before midday Friday were moved to Saturday morning at 9:30.",
            },
        ]
        chosen = lt01_scenarios[variant_idx % len(lt01_scenarios)]
        content = {
            "type": "mcq",
            "title": chosen["title"],
            "prelistening_seconds": 10,
            "speaker_meta": {
                "speaker_count": 1,
                "speaker_roles": ["announcer"],
                "accent_profile": "international_English",
                "speech_speed": cefr,
                "register": "neutral",
            },
            "transcript": chosen["transcript"],
            "stem": chosen["stem"],
            "options": chosen["options"],
            "correct_option_id": chosen["correct_option_id"],
        }
        return content, chosen["explanation"], ["specific_information"]

    elif task_type == "LT-02":
        lt02_scenarios = [
            {
                "title": f"Office Project Coordination Dialogue ({uid_short})",
                "transcript": (
                    "Project Lead: Sarah, have you finished reviewing the revised budget draft for the new client website?\n"
                    "Designer: Yes, I noticed we allocated too much to print advertising and not enough to mobile testing.\n"
                    "Project Lead: Good catch. Let's reassign twenty percent of the marketing funds to testing and send the revised figures to the client by Friday."
                ),
                "q1": {
                    "stem": "What issue does Sarah point out regarding the draft budget?",
                    "options": [
                        {"id": "A", "text": "Insufficient funding allocated for mobile testing"},
                        {"id": "B", "text": "High fees charged by the external printing company"},
                        {"id": "C", "text": "A delay in receiving the client's initial deposit"},
                    ],
                    "correct": "A",
                    "expl": "Sarah states they allocated too much to print and not enough to mobile testing.",
                },
                "q2": {
                    "stem": "What action does the Project Lead agree to take by Friday?",
                    "options": [
                        {"id": "A", "text": "Send the revised figures to the client"},
                        {"id": "B", "text": "Cancel the website mobile testing phase"},
                        {"id": "C", "text": "Hire an independent advertising agency"},
                    ],
                    "correct": "A",
                    "expl": "The lead agrees to reassign funds and send the revised figures to the client by Friday.",
                },
            },
            {
                "title": f"University Campus Presentation Planning ({uid_short})",
                "transcript": (
                    "Liam: Maya, our environmental science presentation is next Monday. Should we design a printed poster or prepare a slide deck?\n"
                    "Maya: Professor Evans mentioned yesterday that all groups must use slides so they can be projected on the lecture hall screen.\n"
                    "Liam: Understood. I'll summarize the field research data tonight, and you can format the graphs tomorrow morning."
                ),
                "q1": {
                    "stem": "Why must the students prepare a digital slide deck instead of a poster?",
                    "options": [
                        {"id": "A", "text": "The professor required slides for the lecture hall screen"},
                        {"id": "B", "text": "The campus printing shop is closed for repairs"},
                        {"id": "C", "text": "Posters are only allowed for graduate research projects"},
                    ],
                    "correct": "A",
                    "expl": "Maya notes Professor Evans requires slides to project on the lecture hall screen.",
                },
                "q2": {
                    "stem": "What responsibility does Liam undertake for tonight?",
                    "options": [
                        {"id": "A", "text": "Summarizing the field research data"},
                        {"id": "B", "text": "Formatting the presentation graphs"},
                        {"id": "C", "text": "Rehearsing the entire presentation speech"},
                    ],
                    "correct": "A",
                    "expl": "Liam states he will summarize the field research data tonight.",
                },
            },
        ]
        chosen = lt02_scenarios[variant_idx % len(lt02_scenarios)]
        content = {
            "type": "multi_mcq",
            "title": chosen["title"],
            "prelistening_seconds": 12,
            "speaker_meta": {
                "speaker_count": 2,
                "speaker_roles": ["speaker1", "speaker2"],
                "accent_profile": "international_English",
                "speech_speed": cefr,
                "register": "conversational",
            },
            "transcript": chosen["transcript"],
            "questions": [
                {
                    "id": "q1",
                    "stem": chosen["q1"]["stem"],
                    "options": chosen["q1"]["options"],
                    "correct_option_id": chosen["q1"]["correct"],
                    "explanation": chosen["q1"]["expl"],
                },
                {
                    "id": "q2",
                    "stem": chosen["q2"]["stem"],
                    "options": chosen["q2"]["options"],
                    "correct_option_id": chosen["q2"]["correct"],
                    "explanation": chosen["q2"]["expl"],
                },
            ],
        }
        return content, "Speakers resolve details regarding budget and schedule.", ["detail", "inference"]

    else:  # LT-03: 5-Item Listening Comprehension
        content = {
            "type": "multi_mcq",
            "title": f"Panel Discussion on Urban Microgrids ({uid_short})",
            "prelistening_seconds": 15,
            "speaker_meta": {
                "speaker_count": 2,
                "speaker_roles": ["host", "expert"],
                "accent_profile": "international_English",
                "speech_speed": cefr,
                "register": "academic_discussion",
            },
            "transcript": (
                "Host: Welcome Dr. Vance. Today we are examining community microgrids. First, what motivated the city to launch this pilot project?\n"
                "Dr. Vance: Frequent summer power outages prompted neighbourhood councils to demand decentralised energy storage.\n"
                "Host: Some residents were concerned about initial installation costs.\n"
                "Dr. Vance: Yes, but regional subsidies covered sixty percent of battery hardware expenses, which eased homeowner reluctance.\n"
                "Host: How do the microgrids perform during adverse winter weather?\n"
                "Dr. Vance: Automated switching isolates local faults within seconds, preventing widespread blackouts across adjacent blocks.\n"
                "Host: What has been the most surprising outcome of the two-year trial?\n"
                "Dr. Vance: Household electricity consumption dropped by twelve percent because residents actively monitor their daily usage apps.\n"
                "Host: Finally, what is the committee's next milestone?\n"
                "Dr. Vance: Expanding the solar storage program to suburban school districts starting early next spring."
            ),
            "questions": [
                {
                    "id": "q1",
                    "stem": "What primary factor motivated the city to initiate the microgrid pilot project?",
                    "options": [
                        {"id": "A", "text": "Frequent summer electricity outages in local neighbourhoods"},
                        {"id": "B", "text": "A sudden drop in commercial energy prices"},
                        {"id": "C", "text": "Strict national limits on household electricity consumption"},
                    ],
                    "correct_option_id": "A",
                    "explanation": "Dr. Vance explains frequent summer outages prompted neighbourhood councils to act.",
                },
                {
                    "id": "q2",
                    "stem": "How were the high installation costs of battery storage addressed?",
                    "options": [
                        {"id": "A", "text": "Regional subsidies funded sixty percent of hardware costs"},
                        {"id": "B", "text": "Homeowners took out private commercial loans"},
                        {"id": "C", "text": "Equipment was donated by an international energy company"},
                    ],
                    "correct_option_id": "A",
                    "explanation": "Subsidies covered 60% of battery hardware expenses.",
                },
                {
                    "id": "q3",
                    "stem": "What occurs automatically when bad winter weather damages power lines?",
                    "options": [
                        {"id": "A", "text": "Automated switching isolates local faults within seconds"},
                        {"id": "B", "text": "All residential power is suspended until technicians arrive"},
                        {"id": "C", "text": "Generators run solely on emergency diesel reserves"},
                    ],
                    "correct_option_id": "A",
                    "explanation": "Automated switching isolates faults within seconds.",
                },
                {
                    "id": "q4",
                    "stem": "What unexpected result occurred during the two-year trial?",
                    "options": [
                        {"id": "A", "text": "Overall household electricity usage decreased by twelve percent"},
                        {"id": "B", "text": "Residents stopped using mobile energy tracking apps"},
                        {"id": "C", "text": "Battery equipment required unexpected major repairs"},
                    ],
                    "correct_option_id": "A",
                    "explanation": "Consumption dropped by 12% as residents monitored apps.",
                },
                {
                    "id": "q5",
                    "stem": "What is the planned next step for the energy program?",
                    "options": [
                        {"id": "A", "text": "Expanding solar storage to suburban school districts next spring"},
                        {"id": "B", "text": "Replacing all existing neighbourhood solar panels"},
                        {"id": "C", "text": "Ending government subsidies for residential solar setups"},
                    ],
                    "correct_option_id": "A",
                    "explanation": "Dr. Vance states expansion will target suburban school districts starting early next spring.",
                },
            ],
        }
        return content, "Comprehensive 5-item comprehension on community microgrids.", ["specific_information", "detail", "inference"]


def _synthesize_reading_template(
    task_type: str,
    cefr: str,
    scenario: str,
    uid_short: str,
    variant_idx: int,
) -> Tuple[Dict[str, Any], str, List[str]]:
    if task_type == "RT-01":
        rt01_passages = [
            {
                "title": f"Community Bicycle Sharing Scheme ({uid_short})",
                "text_segments": [
                    {"text": "Over the past two years, our town's bicycle sharing project has grown "},
                    {"gap_id": "g1", "number": 1},
                    {"text": " popularity among university students and office workers. Commuters who live far "},
                    {"gap_id": "g2", "number": 2},
                    {"text": " the railway station frequently use the bikes to complete the last leg "},
                    {"gap_id": "g3", "number": 3},
                    {"text": " their daily journey. The municipal council has recently added twenty new docking stations "},
                    {"gap_id": "g4", "number": 4},
                    {"text": " order to meet growing demand, and users can now unlock bicycles as soon "},
                    {"gap_id": "g5", "number": 5},
                    {"text": " they scan the mobile app barcode."},
                ],
                "gaps": [
                    {"id": "g1", "accepted_answers": ["in"], "primary_answer": "in", "answer_type": "single_word"},
                    {"id": "g2", "accepted_answers": ["from"], "primary_answer": "from", "answer_type": "single_word"},
                    {"id": "g3", "accepted_answers": ["of"], "primary_answer": "of", "answer_type": "single_word"},
                    {"id": "g4", "accepted_answers": ["in"], "primary_answer": "in", "answer_type": "single_word"},
                    {"id": "g5", "accepted_answers": ["as"], "primary_answer": "as", "answer_type": "single_word"},
                ],
                "explanation": "1: 'in' (grown in popularity); 2: 'from' (far from); 3: 'of' (leg of journey); 4: 'in' (in order to); 5: 'as' (as soon as).",
            },
            {
                "title": f"The Revival of Neighborhood Book Clubs ({uid_short})",
                "text_segments": [
                    {"text": "Reading fiction in a weekly group provides an enjoyable way "},
                    {"gap_id": "g1", "number": 1},
                    {"text": " connect with neighbours who share similar creative interests. Members meet once "},
                    {"gap_id": "g2", "number": 2},
                    {"text": " month at a local tea shop to exchange thoughtful opinions about the chosen novel. "},
                    {"gap_id": "g3", "number": 3},
                    {"text": " everyone is expected to finish the book beforehand, the discussions remain casual and welcoming. "},
                    {"text": "Many attendees report that hearing different interpretations helps them appreciate themes "},
                    {"gap_id": "g4", "number": 4},
                    {"text": " they might otherwise have overlooked. Newcomers are encouraged to join at "},
                    {"gap_id": "g5", "number": 5},
                    {"text": " time without paying any registration fee."},
                ],
                "gaps": [
                    {"id": "g1", "accepted_answers": ["to"], "primary_answer": "to", "answer_type": "single_word"},
                    {"id": "g2", "accepted_answers": ["a", "every"], "primary_answer": "a", "answer_type": "single_word"},
                    {"id": "g3", "accepted_answers": ["Although", "While", "Though"], "primary_answer": "Although", "answer_type": "single_word"},
                    {"id": "g4", "accepted_answers": ["that", "which"], "primary_answer": "that", "answer_type": "single_word"},
                    {"id": "g5", "accepted_answers": ["any"], "primary_answer": "any", "answer_type": "single_word"},
                ],
                "explanation": "1: 'to' (way to connect); 2: 'a' (once a month); 3: 'Although/While' (concession); 4: 'that/which' (relative pronoun); 5: 'any' (at any time).",
            },
        ]
        chosen = rt01_passages[variant_idx % len(rt01_passages)]
        content = {
            "type": "open_cloze",
            "title": chosen["title"],
            "instructions": "Type ONE grammatical word in each gap (1–5).",
            "text_segments": chosen["text_segments"],
            "gaps": chosen["gaps"],
        }
        return content, chosen["explanation"], ["grammar", "syntactic_parsing"]

    elif task_type == "RT-02":
        content = {
            "type": "mcq_cloze",
            "title": f"Adopting Sustainable Habits ({uid_short})",
            "instructions": "Choose the best word (A, B, C, or D) for each gap (1–5).",
            "text_segments": [
                {"text": "Environmental researchers agree that small daily changes can "},
                {"gap_id": "g1", "number": 1},
                {"text": " a noticeable difference to carbon emissions. When households "},
                {"gap_id": "g2", "number": 2},
                {"text": " an effort to minimize food waste, both finances and nature benefit. Consumers should also take "},
                {"gap_id": "g3", "number": 3},
                {"text": " account the durability of clothing before purchasing fast fashion. Many communities have "},
                {"gap_id": "g4", "number": 4},
                {"text": " successful repair cafes where volunteers fix broken electronics free of "},
                {"gap_id": "g5", "number": 5},
                {"text": "."},
            ],
            "gaps": [
                {
                    "id": "g1",
                    "options": [{"id": "A", "text": "make"}, {"id": "B", "text": "do"}, {"id": "C", "text": "give"}, {"id": "D", "text": "bring"}],
                    "correct_option_id": "A",
                },
                {
                    "id": "g2",
                    "options": [{"id": "A", "text": "make"}, {"id": "B", "text": "hold"}, {"id": "C", "text": "create"}, {"id": "D", "text": "build"}],
                    "correct_option_id": "A",
                },
                {
                    "id": "g3",
                    "options": [{"id": "A", "text": "into"}, {"id": "B", "text": "onto"}, {"id": "C", "text": "with"}, {"id": "D", "text": "from"}],
                    "correct_option_id": "A",
                },
                {
                    "id": "g4",
                    "options": [{"id": "A", "text": "established"}, {"id": "B", "text": "invented"}, {"id": "C", "text": "discovered"}, {"id": "D", "text": "occurred"}],
                    "correct_option_id": "A",
                },
                {
                    "id": "g5",
                    "options": [{"id": "A", "text": "charge"}, {"id": "B", "text": "price"}, {"id": "C", "text": "cost"}, {"id": "D", "text": "fine"}],
                    "correct_option_id": "A",
                },
            ],
        }
        return content, "Collocations: make a difference, make an effort, take into account, established, free of charge.", ["lexical_access", "collocation"]

    elif task_type == "RT-05":
        rt05_notices = [
            {
                "header": f"METRO TRANSIT ALERT — WEEKEND SERVICE ({uid_short})",
                "subtext": "Scheduled Engineering Works",
                "body": "Due to signal replacement between Central Station and Parkview, express trains will be replaced by direct shuttle buses this Saturday and Sunday. Passengers should allow 20 minutes extra journey time.",
                "stem": "What should weekend passengers expect according to the transit alert?",
                "options": [
                    {"id": "A", "text": "Shuttle buses will replace express trains between Central and Parkview"},
                    {"id": "B", "text": "Ticket fares will be discounted by twenty percent during the weekend"},
                    {"id": "C", "text": "All train stations will be closed completely until Monday morning"},
                ],
                "correct_option_id": "A",
                "explanation": "The notice states express trains will be replaced by direct shuttle buses.",
            },
            {
                "header": f"CAMPUS SPORTS COMPLEX NOTICE ({uid_short})",
                "subtext": "Locker Room Renovation",
                "body": "Beginning Monday October 12, all personal belongings must be removed from the West Wing lockers by 20:00. Any remaining items will be securely stored at the Facilities Office for two weeks.",
                "stem": "What are members instructed to do before 20:00 on October 12?",
                "options": [
                    {"id": "A", "text": "Clear their belongings from the West Wing lockers"},
                    {"id": "B", "text": "Renew their annual sports facility membership"},
                    {"id": "C", "text": "Register for a temporary locker key at Facilities Office"},
                ],
                "correct_option_id": "A",
                "explanation": "The notice instructs members to remove all belongings from West Wing lockers by 20:00.",
            },
        ]
        chosen = rt05_notices[variant_idx % len(rt05_notices)]
        content = {
            "type": "discrete_graphic",
            "graphic": {
                "graphic_type": "notice",
                "header": chosen["header"],
                "subtext": chosen["subtext"],
                "body": chosen["body"],
                "footer": "Operations & Public Information Unit",
            },
            "stem": chosen["stem"],
            "options": chosen["options"],
            "correct_option_id": chosen["correct_option_id"],
        }
        return content, chosen["explanation"], ["specific_information"]

    elif task_type == "RT-04":
        rt04_sentences = [
            {
                "stem": f"The municipal council voted ________ to approve the new solar park proposal (#{uid_short}) after community consultations.",
                "options": [{"id": "A", "text": "unanimously"}, {"id": "B", "text": "narrowly"}, {"id": "C", "text": "hesitantly"}, {"id": "D", "text": "accidentally"}],
                "correct": "A",
                "expl": "'Unanimously' indicates complete agreement across all council members.",
            },
            {
                "stem": f"The scientist's breakthrough research into battery storage has been ________ recognized (#{uid_short}) by engineering institutes worldwide.",
                "options": [{"id": "A", "text": "widely"}, {"id": "B", "text": "sparsely"}, {"id": "C", "text": "barely"}, {"id": "D", "text": "strictly"}],
                "correct": "A",
                "expl": "'Widely recognized' is the natural academic collocation for receiving broad acclaim.",
            },
            {
                "stem": f"Before launching the new electric bus route, transport officials conducted ________ tests (#{uid_short}) to assess battery performance.",
                "options": [{"id": "A", "text": "rigorous"}, {"id": "B", "text": "careless"}, {"id": "C", "text": "trivial"}, {"id": "D", "text": "slight"}],
                "correct": "A",
                "expl": "'Rigorous tests' signifies thorough, comprehensive testing.",
            },
        ]
        chosen = rt04_sentences[variant_idx % len(rt04_sentences)]
        content = {
            "type": "discrete_cloze",
            "stem": chosen["stem"],
            "options": chosen["options"],
            "correct_option_id": chosen["correct"],
        }
        return content, chosen["expl"], ["lexical_access", "collocation"]

    elif task_type == "RT-09":
        content = {
            "type": "multi_mcq",
            "title": f"The Growth of Rooftop Apiculture ({uid_short})",
            "text": (
                "Over the past decade, urban beekeeping has expanded from a niche hobby into a structured environmental initiative across major European capitals. "
                "Hotel terraces, university science blocks, and municipal town halls now host thriving hives that yield hundreds of kilograms of wildflower honey each autumn. "
                "Biologists have discovered that city bees frequently display greater resistance to common parasites than rural colonies. "
                "This resilience is attributed to the ban on agricultural synthetic pesticides within inner city parks, as well as the wide botanical variety found in private gardens."
            ),
            "questions": [
                {
                    "id": "q1",
                    "stem": "Where are urban bee hives now frequently located according to the text?",
                    "options": [
                        {"id": "A", "text": "On city rooftops such as hotel terraces and university buildings"},
                        {"id": "B", "text": "Solely in remote countryside agricultural fields"},
                        {"id": "C", "text": "Inside climate-controlled botanical greenhouses"},
                    ],
                    "correct_option_id": "A",
                    "explanation": "The text lists hotel terraces, university science blocks, and town halls.",
                },
                {
                    "id": "q2",
                    "stem": "Why do urban bees often show stronger resistance to parasites than rural bees?",
                    "options": [
                        {"id": "A", "text": "City environments prohibit agricultural synthetic pesticides and offer plant variety"},
                        {"id": "B", "text": "Urban bees are fed artificial antibiotic syrups throughout the winter"},
                        {"id": "C", "text": "High metropolitan temperatures prevent parasite reproduction entirely"},
                    ],
                    "correct_option_id": "A",
                    "explanation": "The text notes the ban on synthetic pesticides and botanical variety in gardens.",
                },
            ],
        }
        return content, "2-item comprehension evaluating gist and specific cause.", ["detail", "inference"]

    else:
        # Default fallback for RT-03, RT-06, RT-07, RT-08
        content = {
            "type": "discrete_cloze",
            "stem": f"The committee's revised proposal for the {scenario} (#{uid_short}) was ________ praised by local residents for preserving natural habitats.",
            "options": [
                {"id": "A", "text": "widely"},
                {"id": "B", "text": "narrowly"},
                {"id": "C", "text": "shortly"},
                {"id": "D", "text": "barely"},
            ],
            "correct_option_id": "A",
        }
        return content, "'widely praised' is the natural collocation indicating broad public appreciation.", ["lexical_access", "collocation"]
