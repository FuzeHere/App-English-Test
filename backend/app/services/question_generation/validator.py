import hashlib
import json
from typing import Dict, Any, List
from app.services.scoring.objective_scorer import get_question_sub_item_count


READING_TASK_TYPES = {
    "RT-01": "Open Cloze (5 gaps)",
    "RT-02": "Multiple-choice Cloze (5 gaps)",
    "RT-03": "Cross Text Matching (4 texts)",
    "RT-04": "Discrete Cloze (1 gap)",
    "RT-05": "Discrete with a Graphic",
    "RT-06": "Gapped Text — Sentences (5 gaps, 8 options)",
    "RT-07": "Gapped Text — Paragraphs (5 gaps, 6 options)",
    "RT-08": "Comprehension — 5 Items",
    "RT-09": "Comprehension — 2 Items",
}

LISTENING_TASK_TYPES = {
    "LT-01": "1-Item Listening Comprehension",
    "LT-02": "2-Item Listening Comprehension",
    "LT-03": "5-Item Listening Comprehension",
}


def compute_content_hash(content_json: Dict[str, Any]) -> str:
    serialized = json.dumps(content_json, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def validate_question_item(
    skill: str,
    task_type: str,
    cefr_target: str,
    difficulty_theta: float,
    content_json: Dict[str, Any],
    explanation: str,
) -> Dict[str, Any]:
    """
    Deterministic structural, answer-key, distractor, and CEFR constraint validator (PRD Section 20.5).
    """
    errors: List[str] = []
    warnings: List[str] = []

    if skill not in ("reading", "listening"):
        errors.append(f"Invalid skill: {skill}")

    if cefr_target not in ("A1", "A2", "B1", "B2", "C1"):
        errors.append(f"Invalid CEFR target: {cefr_target}")

    if not (-3.5 <= difficulty_theta <= 3.5):
        errors.append(f"Difficulty theta {difficulty_theta} outside plausible range [-3.5, +3.5]")

    if not explanation or len(explanation.strip()) < 10:
        warnings.append("Explanation is brief; recommended >= 10 characters.")

    qtype = content_json.get("type", "")
    if not qtype:
        errors.append("Missing 'type' field in content_json")

    # Task-specific checks
    if task_type == "RT-01" or qtype == "open_cloze":
        gaps = content_json.get("gaps", [])
        if len(gaps) != 5:
            errors.append(f"RT-01 Open Cloze must have 5 gaps, found {len(gaps)}")
        for g in gaps:
            if not g.get("accepted_answers"):
                errors.append(f"Gap {g.get('id')} missing accepted_answers")

    elif task_type == "RT-02" or qtype == "mcq_cloze":
        gaps = content_json.get("gaps", [])
        if len(gaps) != 5:
            errors.append(f"RT-02 Multiple-choice Cloze must have 5 gaps, found {len(gaps)}")
        for g in gaps:
            opts = g.get("options", [])
            if len(opts) < 3:
                errors.append(f"Gap {g.get('id')} has fewer than 3 options")
            texts = [o.get("text", "").strip().lower() for o in opts]
            if len(texts) != len(set(texts)):
                errors.append(f"Gap {g.get('id')} contains duplicate option texts")
            opt_ids = {o.get("id") for o in opts}
            if g.get("correct_option_id") not in opt_ids:
                errors.append(f"Gap {g.get('id')} correct_option_id not in options")

    elif task_type in ("RT-04", "RT-05", "LT-01") and qtype in ("mcq", "discrete_cloze", "discrete_graphic"):
        opts = content_json.get("options", [])
        if len(opts) < 3:
            errors.append("MCQ item must have at least 3 options")
        texts = [o.get("text", "").strip().lower() for o in opts]
        if len(texts) != len(set(texts)):
            errors.append("Duplicate options detected")
        opt_ids = {o.get("id") for o in opts}
        if content_json.get("correct_option_id") not in opt_ids:
            errors.append("correct_option_id does not match any option ID")

    elif task_type in ("RT-06", "RT-07") or qtype in ("gapped_text_sentences", "gapped_text_paragraphs"):
        gaps = content_json.get("gaps", [])
        opts = content_json.get("options", [])
        correct_map = content_json.get("correct", {})
        if len(gaps) != 5:
            errors.append(f"{task_type} requires 5 gaps, found {len(gaps)}")
        expected_min_opts = 8 if task_type == "RT-06" else 6
        if len(opts) < expected_min_opts:
            warnings.append(f"{task_type} recommends {expected_min_opts} options, found {len(opts)}")
        opt_ids = {o.get("id") for o in opts}
        for g in gaps:
            gid = g if isinstance(g, str) else g.get("id")
            if correct_map.get(gid) not in opt_ids:
                errors.append(f"Gap {gid} answer key missing from options")

    elif task_type in ("RT-03", "RT-08", "RT-09", "LT-02", "LT-03") or qtype in ("cross_text_matching", "multi_mcq"):
        questions = content_json.get("questions", [])
        if not questions:
            errors.append(f"{task_type} must contain a non-empty 'questions' array")
        for q in questions:
            opts = q.get("options", [])
            if len(opts) < 3:
                errors.append(f"Subquestion {q.get('id')} has fewer than 3 options")
            opt_ids = {o.get("id") for o in opts}
            if q.get("correct_option_id") not in opt_ids:
                errors.append(f"Subquestion {q.get('id')} correct_option_id not in options")

    if skill == "listening":
        if not content_json.get("transcript"):
            errors.append("Listening item must include a transcript in content_json")
        if "prelistening_seconds" not in content_json:
            warnings.append("Listening item missing explicit prelistening_seconds; defaulting to 10s.")

    sub_units = get_question_sub_item_count(task_type, content_json)

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "sub_item_units": sub_units,
    }
