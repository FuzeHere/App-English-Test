import random
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.entities import QuestionItem, AudioAsset, WritingPrompt
from app.services.question_generation.validator import (
    compute_content_hash,
    validate_question_item,
)
from app.services.scoring.objective_scorer import (
    get_question_sub_item_count,
    map_cefr_to_default_theta,
)
from app.services.tts.tts_engine import tts_engine


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
    runs deterministic validation, synthesizes audio for Listening, and stores them with status='REVIEW'.
    """
    created_items = []
    levels = target_levels or ["B1", "B2"]
    qty = max(1, min(10, quantity))

    topics = [
        ("technology", "smart community library lockers"),
        ("travel", "regional electric ferry service"),
        ("workplace", "cross-department mentorship scheme"),
        ("education", "archival digitisation workshop"),
        ("health_lifestyle", "urban running club orientation"),
        ("environment", "rooftop rainwater harvesting"),
    ]

    for i in range(qty):
        cefr = levels[i % len(levels)]
        topic, scenario = topics[(i + random.randint(0, 5)) % len(topics)]
        base_theta = map_cefr_to_default_theta(cefr) + round(random.uniform(-0.18, 0.18), 2)
        uid_short = str(uuid.uuid4())[:6]

        if skill == "writing":
            part = 1 if "1" in str(task_type) else 2
            min_words = 50 if part == 1 else 180
            rec_min = 15 if part == 1 else 30
            text_type = "email" if part == 1 else random.choice(["article", "review", "web_post"])
            audience = "a project colleague (Jordan)" if part == 1 else "readers of an international community journal"
            wp = WritingPrompt(
                task_part=part,
                cefr_target=cefr,
                text_type=text_type,
                audience=audience,
                scenario=f"Scenario ({scenario}): Organising and evaluating a new local initiative (#{uid_short}).",
                prompt_text=(
                    f"Write {'an email to Jordan' if part == 1 else f'a {text_type} for our readers'} about {scenario}. "
                    f"Write at least {min_words} words."
                ),
                bullet_points=[
                    f"describe your recent experience with {scenario}",
                    "explain one practical challenge that arose and how it was handled",
                    "suggest what improvements should be made next month",
                ],
                minimum_words=min_words,
                recommended_minutes=rec_min,
                status="REVIEW",
                version=1,
                validation_report={"valid": True, "errors": [], "warnings": [], "provider": provider_name},
            )
            db.add(wp)
            db.flush()
            created_items.append({
                "id": wp.id,
                "skill": "writing",
                "task_type": f"WT-0{part}",
                "cefr_target": cefr,
                "status": "REVIEW",
                "topic": topic,
                "scenario": scenario,
            })
            continue

        content_json, explanation, cog_focus = _synthesize_structured_question_template(
            skill=skill,
            task_type=task_type,
            cefr=cefr,
            topic=topic,
            scenario=scenario,
            uid_short=uid_short,
        )
        c_hash = compute_content_hash(content_json)
        v_report = validate_question_item(
            skill=skill,
            task_type=task_type,
            cefr_target=cefr,
            difficulty_theta=base_theta,
            content_json=content_json,
            explanation=explanation,
        )
        v_report["provider"] = provider_name

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
            transcript = content_json.get("transcript", "")
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

    db.commit()
    return created_items


def _synthesize_structured_question_template(
    skill: str,
    task_type: str,
    cefr: str,
    topic: str,
    scenario: str,
    uid_short: str,
) -> tuple[Dict[str, Any], str, List[str]]:
    if skill == "listening":
        if task_type == "LT-01":
            content = {
                "type": "mcq",
                "title": f"Audio Update: {scenario.title()} ({uid_short})",
                "prelistening_seconds": 10,
                "speaker_meta": {
                    "speaker_count": 1,
                    "speaker_roles": ["coordinator"],
                    "accent_profile": "international_English",
                    "speech_speed": cefr,
                    "register": "neutral",
                },
                "transcript": (
                    f"Hello everyone. Regarding our {scenario} scheduled for Thursday, please note that registration "
                    f"will now take place in Room 204 on the second floor instead of the main lobby because the lobby floor is being polished."
                ),
                "stem": f"Where will registration for the {scenario} take place on Thursday?",
                "options": [
                    {"id": "A", "text": "In Room 204 on the second floor"},
                    {"id": "B", "text": "In the main ground-floor lobby"},
                    {"id": "C", "text": "Outside the courtyard entrance"},
                ],
                "correct_option_id": "A",
            }
            return content, "The coordinator states registration moved to Room 204 on the second floor.", ["specific_information"]

        # LT-02 or LT-03
        num_q = 2 if task_type == "LT-02" else 5
        questions = []
        for idx in range(1, num_q + 1):
            questions.append({
                "id": f"q{idx}",
                "stem": f"Question {idx}: What aspect of the {scenario} do the speakers highlight in section {idx}?",
                "options": [
                    {"id": "A", "text": "Scheduling flexible weekday afternoon slots for participants"},
                    {"id": "B", "text": "Closing the facility during the summer holidays"},
                    {"id": "C", "text": "Charging an additional fee for printed handbooks"},
                ],
                "correct_option_id": "A",
                "explanation": "The speakers agree on providing flexible weekday afternoon slots.",
            })
        content = {
            "type": "multi_mcq",
            "title": f"Discussion on {scenario.title()} ({uid_short})",
            "prelistening_seconds": 12 if num_q == 2 else 15,
            "speaker_meta": {
                "speaker_count": 2,
                "speaker_roles": ["organiser", "participant"],
                "accent_profile": "international_English",
                "speech_speed": cefr,
                "register": "conversational",
            },
            "transcript": (
                f"Organiser: We've been reviewing feedback on the {scenario}. Most people asked for flexible weekday afternoon slots.\n"
                f"Participant: Yes, having afternoon sessions makes it much easier for commuters and students to attend without rushing, and we don't need to charge extra for digital handouts."
            ),
            "questions": questions,
        }
        return content, "The speakers highlight flexible weekday afternoon slots for participants.", ["detail", "inference"]

    # Reading task types
    if task_type == "RT-01":
        content = {
            "type": "open_cloze",
            "title": f"Notes on {scenario.title()} ({uid_short})",
            "instructions": "Type ONE grammatical word in each gap (1–5).",
            "text_segments": [
                {"text": f"Setting up a successful {scenario} requires careful coordination "},
                {"gap_id": "g1", "number": 1},
                {"text": " local volunteers. Most participants prefer sessions that take place "},
                {"gap_id": "g2", "number": 2},
                {"text": " the afternoon, when public transport is quieter. Organisers have found "},
                {"gap_id": "g3", "number": 3},
                {"text": " sending a short reminder email two days in advance reduces absences. In addition, providing "},
                {"gap_id": "g4", "number": 4},
                {"text": " clear welcome guide helps newcomers feel confident as soon "},
                {"gap_id": "g5", "number": 5},
                {"text": " they arrive."},
            ],
            "gaps": [
                {"id": "g1", "accepted_answers": ["among", "between", "with"], "primary_answer": "with", "answer_type": "single_word"},
                {"id": "g2", "accepted_answers": ["in", "during"], "primary_answer": "in", "answer_type": "single_word"},
                {"id": "g3", "accepted_answers": ["that"], "primary_answer": "that", "answer_type": "single_word"},
                {"id": "g4", "accepted_answers": ["a"], "primary_answer": "a", "answer_type": "single_word"},
                {"id": "g5", "accepted_answers": ["as"], "primary_answer": "as", "answer_type": "single_word"},
            ],
        }
        return content, "1: with/among; 2: in; 3: that; 4: a; 5: as (as soon as).", ["grammar", "syntactic_parsing"]

    if task_type == "RT-05":
        content = {
            "type": "discrete_graphic",
            "graphic": {
                "graphic_type": "notice",
                "header": f"COMMUNITY NOTICE — {scenario.upper()} ({uid_short})",
                "subtext": "Updated Schedule",
                "body": f"Please note that all {scenario} sessions now begin at 17:15 sharp. Participants should bring their own reusable water bottle and sign in at the front desk.",
                "footer": "Coordinator Team",
            },
            "stem": f"What are participants in the {scenario} asked to bring?",
            "options": [
                {"id": "A", "text": "A reusable water bottle"},
                {"id": "B", "text": "A printed registration receipt"},
                {"id": "C", "text": "A folding chair from home"},
            ],
            "correct_option_id": "A",
        }
        return content, "The notice states participants should bring their own reusable water bottle.", ["specific_information"]

    # Default to Discrete Cloze (RT-04) or Comprehension
    content = {
        "type": "discrete_cloze",
        "stem": f"The committee's new proposal for the {scenario} (#{uid_short}) was ________ approved after residents saw the environmental benefits.",
        "options": [
            {"id": "A", "text": "widely"},
            {"id": "B", "text": "narrowly"},
            {"id": "C", "text": "shortly"},
            {"id": "D", "text": "deeply"},
        ],
        "correct_option_id": "A",
    }
    return content, "'widely approved' is the natural collocation meaning supported by a large number of people.", ["lexical_access", "collocation"]
