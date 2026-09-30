from typing import Dict, Any, List


WRITING_EVALUATION_SYSTEM_PROMPT = """You are an English-language assessment evaluator for a private practice simulator (CEST Practice Simulator).
Evaluate the candidate response against the exact task prompt provided.
Do not claim to produce an official Cambridge score.
Use the simulator's 0-5 band per criterion:
0 = insufficient / non-functional evidence
1 = very limited
2 = emerging
3 = generally adequate
4 = strong
5 = highly effective

Criteria:
1. communicative_achievement: whether the response accomplishes the task appropriately for the target reader and context.
2. organisation: whether ideas are connected, structured and easy to follow.
3. language: range, appropriacy and control of vocabulary and grammar.

Rules:
- Avoid inventing task requirements.
- Quote the user's own text accurately when citing evidence.
- Distinguish errors from stylistic alternatives.
- Do not penalise an alternative that is grammatically valid merely because it is different from a preferred wording.
- Return ONLY valid JSON matching the requested schema.
"""


def build_writing_evaluation_user_prompt(
    task_part: int,
    cefr_target: str,
    text_type: str,
    audience: str,
    scenario: str,
    prompt_text: str,
    bullet_points: List[str],
    minimum_words: int,
    candidate_response: str,
) -> str:
    bullets_str = "\n".join(f"- {b}" for b in bullet_points)
    return f"""Evaluate the following candidate writing submission:

TASK METADATA:
- Part: Part {task_part}
- Target CEFR context: {cefr_target}
- Text type: {text_type}
- Target audience: {audience}
- Minimum required words: {minimum_words}
- Scenario: {scenario}
- Prompt: {prompt_text}
- Required bullet points:
{bullets_str}

CANDIDATE RESPONSE:
\"\"\"
{candidate_response}
\"\"\"

Return strict JSON with this exact structure:
{{
  "communicative_achievement": <int 0-5>,
  "organisation": <int 0-5>,
  "language": <int 0-5>,
  "estimated_cefr": "<A1|A2|B1|B2|C1>",
  "confidence": <float 0.0-1.0>,
  "too_short_warning": <bool>,
  "summary_en": "<concise assessment summary in English>",
  "summary_id": "<ringkasan evaluasi dalam Bahasa Indonesia>",
  "task_completion": {{
    "all_bullets_addressed": <bool>,
    "bullet_analysis": ["<point 1 status>", "<point 2 status>", "<point 3 status>"],
    "register_analysis": "<analysis of tone/register for target audience>"
  }},
  "diagnostics": {{
    "grammar": ["<specific observation>"],
    "vocabulary": ["<specific observation>"],
    "coherence": ["<specific observation>"]
  }},
  "corrections": [
    {{
      "original": "<exact quote from candidate text>",
      "suggested": "<improved version>",
      "why_en": "<explanation in English>",
      "why_id": "<penjelasan dalam Bahasa Indonesia>"
    }}
  ],
  "improvement_plan": [
    "<actionable next step 1>",
    "<actionable next step 2>"
  ]
}}"""


def build_question_generation_prompt(
    skill: str,
    task_type: str,
    cefr_target: str,
    topic: str,
    scenario: str,
) -> str:
    return f"""You are an assessment item writer for a private English practice simulator.
Create ONE original {skill.upper()} question item for task type {task_type} targeting CEFR {cefr_target}.
Topic: {topic}
Scenario: {scenario}

Rules:
- Original content only. Never reproduce copyrighted Cambridge sample questions.
- Ensure unambiguous answer key and plausible distractors.
- Return ONLY valid JSON with fields:
  "primary_topic", "scenario", "cognitive_focus", "explanation", "content_json"
"""
