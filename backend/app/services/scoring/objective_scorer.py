from typing import Dict, Any, List, Optional
from app.core.config import settings


def normalize_text(val: str) -> str:
    return " ".join(str(val or "").strip().lower().split())


def get_question_sub_item_count(task_type: str, content_json: Dict[str, Any]) -> int:
    """
    Returns the number of scored item response units within a task (PRD Section 15.10).
    """
    qtype = content_json.get("type", "")
    if qtype == "open_cloze" or task_type == "RT-01":
        return max(1, len(content_json.get("gaps", [])))
    if qtype == "mcq_cloze" or task_type == "RT-02":
        return max(1, len(content_json.get("gaps", [])))
    if qtype == "cross_text_matching" or task_type == "RT-03":
        return max(1, len(content_json.get("questions", [])))
    if qtype in ("gapped_text_sentences", "gapped_text_paragraphs") or task_type in ("RT-06", "RT-07"):
        return max(1, len(content_json.get("gaps", [])))
    if qtype == "multi_mcq" or task_type in ("RT-08", "RT-09", "LT-02", "LT-03"):
        return max(1, len(content_json.get("questions", [])))
    return 1


def score_question_response(
    task_type: str,
    content_json: Dict[str, Any],
    user_answer: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Deterministically scores any of the 9 Reading or 3 Listening task types (PRD Section 26).
    Returns:
    {
      "sub_item_count": int,
      "correct_sub_items": int,
      "is_correct": bool,
      "details": list of per-subquestion results,
      "correct_answer_summary": dict/str
    }
    """
    qtype = content_json.get("type", "mcq")
    answers_map = user_answer.get("answers", {})
    selected_option = user_answer.get("selected_option_id")

    # 1. Single MCQ: RT-04 (Discrete Cloze), RT-05 (Discrete with Graphic), LT-01 (1-item Listening)
    if qtype in ("mcq", "discrete_cloze", "discrete_graphic") or task_type in ("RT-04", "RT-05", "LT-01"):
        if "questions" in content_json and len(content_json["questions"]) > 0 and "correct_option_id" not in content_json:
            # Handled as 1-item multi_mcq
            q0 = content_json["questions"][0]
            qid = q0.get("id", "q1")
            correct_id = str(q0.get("correct_option_id", "")).strip()
            given = str(answers_map.get(qid, selected_option or "")).strip()
            is_corr = given.upper() == correct_id.upper() and correct_id != ""
            return {
                "sub_item_count": 1,
                "correct_sub_items": 1 if is_corr else 0,
                "is_correct": is_corr,
                "details": [{"id": qid, "given": given, "correct": correct_id, "is_correct": is_corr}],
                "correct_answer_summary": {qid: correct_id},
            }

        correct_id = str(content_json.get("correct_option_id", "")).strip()
        given = str(selected_option or answers_map.get("main", "")).strip()
        is_corr = given.upper() == correct_id.upper() and correct_id != ""
        return {
            "sub_item_count": 1,
            "correct_sub_items": 1 if is_corr else 0,
            "is_correct": is_corr,
            "details": [{"id": "main", "given": given, "correct": correct_id, "is_correct": is_corr}],
            "correct_answer_summary": {"main": correct_id},
        }

    # 2. Open Cloze: RT-01
    if qtype == "open_cloze" or task_type == "RT-01":
        gaps = content_json.get("gaps", [])
        details = []
        correct_summary = {}
        correct_count = 0
        for g in gaps:
            gid = g.get("id")
            accepted = [normalize_text(a) for a in g.get("accepted_answers", [])]
            primary = g.get("primary_answer", accepted[0] if accepted else "")
            given_raw = str(answers_map.get(gid, "")).strip()
            given_norm = normalize_text(given_raw)
            is_corr = given_norm in accepted and given_norm != ""
            if is_corr:
                correct_count += 1
            correct_summary[gid] = primary
            details.append({
                "id": gid,
                "given": given_raw,
                "correct": primary,
                "accepted_answers": g.get("accepted_answers", []),
                "is_correct": is_corr,
            })
        total = max(1, len(gaps))
        return {
            "sub_item_count": total,
            "correct_sub_items": correct_count,
            "is_correct": correct_count == total,
            "details": details,
            "correct_answer_summary": correct_summary,
        }

    # 3. Multiple-choice Cloze: RT-02
    if qtype == "mcq_cloze" or task_type == "RT-02":
        gaps = content_json.get("gaps", [])
        details = []
        correct_summary = {}
        correct_count = 0
        for g in gaps:
            gid = g.get("id")
            correct_id = str(g.get("correct_option_id", "")).strip()
            given = str(answers_map.get(gid, "")).strip()
            is_corr = given.upper() == correct_id.upper() and correct_id != ""
            if is_corr:
                correct_count += 1
            correct_summary[gid] = correct_id
            details.append({"id": gid, "given": given, "correct": correct_id, "is_correct": is_corr})
        total = max(1, len(gaps))
        return {
            "sub_item_count": total,
            "correct_sub_items": correct_count,
            "is_correct": correct_count == total,
            "details": details,
            "correct_answer_summary": correct_summary,
        }

    # 4. Gapped Text (Sentences RT-06 / Paragraphs RT-07)
    if qtype in ("gapped_text_sentences", "gapped_text_paragraphs") or task_type in ("RT-06", "RT-07"):
        gaps = content_json.get("gaps", [])
        correct_map = content_json.get("correct", {})
        details = []
        correct_summary = {}
        correct_count = 0
        for gid in gaps:
            gap_key = gid if isinstance(gid, str) else gid.get("id")
            correct_id = str(correct_map.get(gap_key, "")).strip()
            given = str(answers_map.get(gap_key, "")).strip()
            is_corr = given.upper() == correct_id.upper() and correct_id != ""
            if is_corr:
                correct_count += 1
            correct_summary[gap_key] = correct_id
            details.append({"id": gap_key, "given": given, "correct": correct_id, "is_correct": is_corr})
        total = max(1, len(gaps))
        return {
            "sub_item_count": total,
            "correct_sub_items": correct_count,
            "is_correct": correct_count == total,
            "details": details,
            "correct_answer_summary": correct_summary,
        }

    # 5. Cross Text Matching (RT-03) and Multi-MCQ Comprehension (RT-08, RT-09, LT-02, LT-03)
    questions = content_json.get("questions", [])
    details = []
    correct_summary = {}
    correct_count = 0
    for q in questions:
        qid = q.get("id")
        correct_id = str(q.get("correct_option_id", "")).strip()
        given = str(answers_map.get(qid, "")).strip()
        is_corr = given.upper() == correct_id.upper() and correct_id != ""
        if is_corr:
            correct_count += 1
        correct_summary[qid] = correct_id
        details.append({
            "id": qid,
            "given": given,
            "correct": correct_id,
            "is_correct": is_corr,
            "explanation": q.get("explanation", ""),
        })
    total = max(1, len(questions))
    return {
        "sub_item_count": total,
        "correct_sub_items": correct_count,
        "is_correct": correct_count == total,
        "details": details,
        "correct_answer_summary": correct_summary,
    }


def sanitize_question_for_client(content_json: Dict[str, Any], include_transcript: bool = False) -> Dict[str, Any]:
    """
    Exam Integrity Rule (PRD Section 31.2):
    Never send the correct answer, explanation, or hidden transcript to the browser before submission.
    """
    import copy
    clean = copy.deepcopy(content_json)
    clean.pop("correct_option_id", None)
    clean.pop("correct", None)
    clean.pop("explanation", None)
    if not include_transcript:
        clean.pop("transcript", None)

    if "gaps" in clean and isinstance(clean["gaps"], list):
        sanitized_gaps = []
        for g in clean["gaps"]:
            if isinstance(g, dict):
                g_copy = dict(g)
                g_copy.pop("accepted_answers", None)
                g_copy.pop("primary_answer", None)
                g_copy.pop("correct_option_id", None)
                g_copy.pop("explanation", None)
                sanitized_gaps.append(g_copy)
            else:
                sanitized_gaps.append(g)
        clean["gaps"] = sanitized_gaps

    if "questions" in clean and isinstance(clean["questions"], list):
        for q in clean["questions"]:
            if isinstance(q, dict):
                q.pop("correct_option_id", None)
                q.pop("explanation", None)

    return clean


def map_theta_to_cefr(theta: float, thresholds: Optional[Dict[str, float]] = None) -> str:
    """
    Maps latent ability theta to CEFR A1-C1 (PRD Section 15.5).
    """
    t = thresholds or settings.CEFR_THETA_THRESHOLDS
    if theta < t["A1_MAX"]:
        return "A1"
    if theta < t["A2_MAX"]:
        return "A2"
    if theta < t["B1_MAX"]:
        return "B1"
    if theta < t["B2_MAX"]:
        return "B2"
    return "C1"


def map_cefr_to_default_theta(cefr: str) -> float:
    mapping = {
        "A1": -1.50,
        "A2": -0.80,
        "B1": 0.00,
        "B2": 0.80,
        "C1": 1.50,
    }
    return mapping.get(cefr.upper(), 0.0)


def map_se_to_confidence(se: float, time_limited: bool = False) -> str:
    """
    Maps standard error to plain-language confidence label (PRD Section 17.2).
    """
    if time_limited:
        return "Limited confidence (time-limited)"
    if se <= 0.32:
        return "High confidence"
    if se <= 0.48:
        return "Moderate confidence"
    return "Limited confidence"


def calculate_overall_cefr(
    reading_cefr: Optional[str],
    listening_cefr: Optional[str],
    writing_cefr: Optional[str],
) -> Optional[str]:
    """
    Transparent 3-skill ordinal average (PRD Section 14.2):
    A1 = 1, A2 = 2, B1 = 3, B2 = 4, C1 = 5
    """
    ordinal_map = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5}
    reverse_map = {1: "A1", 2: "A2", 3: "B1", 4: "B2", 5: "C1"}

    levels = [reading_cefr, listening_cefr, writing_cefr]
    numeric_vals = [ordinal_map[lvl] for lvl in levels if lvl in ordinal_map]
    if not numeric_vals:
        return None
    avg_val = sum(numeric_vals) / len(numeric_vals)
    rounded = int(round(avg_val))
    rounded = max(1, min(5, rounded))
    return reverse_map[rounded]


def get_can_do_statements(skill: str, cefr: str) -> List[str]:
    """
    Original paraphrased Can-Do statements inspired by CEFR concepts (PRD Section 17.4).
    """
    statements = {
        "reading": {
            "A1": [
                "Understand very short, everyday notices, labels, and simple messages.",
                "Locate basic factual details such as times, places, and prices in familiar texts.",
            ],
            "A2": [
                "Understand routine personal emails, short notices, and straightforward factual descriptions.",
                "Identify specific predictable information in everyday reading materials.",
            ],
            "B1": [
                "Follow the main points of clear articles and workplace or study messages on familiar topics.",
                "Connect ideas across paragraphs and recognize writer intentions in straightforward texts.",
            ],
            "B2": [
                "Follow main ideas and supporting arguments in moderately complex articles and reports.",
                "Identify and compare viewpoints, attitudes, and implied meaning across multiple related texts.",
            ],
            "C1": [
                "Understand lengthy, complex texts and recognize subtle distinctions of style and implicit attitude.",
                "Synthesize detailed arguments and abstract concepts across dense multi-section passages.",
            ],
        },
        "listening": {
            "A1": [
                "Recognize familiar words and basic phrases concerning immediate everyday situations when spoken slowly.",
                "Catch key details such as numbers, days, and simple instructions in short recordings.",
            ],
            "A2": [
                "Understand common expressions and key points in short announcements, appointments, and everyday dialogues.",
                "Follow simple exchanges about travel, shopping, and personal routines.",
            ],
            "B1": [
                "Understand the main points of clear standard speech on work, study, and leisure topics.",
                "Follow everyday conversations and identify speaker plans, preferences, and general attitudes.",
            ],
            "B2": [
                "Understand extended discussions and monologues and infer implied meaning and speaker attitude.",
                "Follow multi-speaker interactions even when viewpoints contrast or shift naturally.",
            ],
            "C1": [
                "Follow complex spoken discussions and lectures with ease, recognizing subtle nuances and implicit stance.",
                "Synthesize detailed arguments across multi-speaker debates at natural native-like pace.",
            ],
        },
        "writing": {
            "A1": [
                "Write very short, simple messages and emails covering basic factual points.",
                "Use basic vocabulary and simple sentence forms for immediate communicative needs.",
            ],
            "A2": [
                "Write short, connected emails and notes using common linking words like 'and', 'but', and 'because'.",
                "Address straightforward prompts about everyday plans, invitations, and experiences.",
            ],
            "B1": [
                "Produce connected, intelligible emails and short articles covering all required prompt points.",
                "Organize ideas into clear paragraphs with generally accurate everyday grammar and vocabulary.",
            ],
            "B2": [
                "Produce clear, well-structured emails, reviews, and articles appropriate for the target audience.",
                "Use a varied range of vocabulary, cohesive devices, and complex sentence structures effectively.",
            ],
            "C1": [
                "Write well-developed, persuasive texts with natural register control and sophisticated lexical precision.",
                "Organize complex ideas seamlessly using varied cohesive mechanisms and high grammatical accuracy.",
            ],
        },
    }
    skill_map = statements.get(skill.lower(), statements["reading"])
    return skill_map.get(cefr.upper(), skill_map["B1"])
