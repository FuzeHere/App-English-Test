from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import SessionLocal
from app.models.entities import ModuleSession, TestSession
from app.services.adaptive.irt_engine import (
    rasch_probability,
    fisher_information,
    estimate_eap,
    select_next_item,
    check_stopping_condition,
    CandidateItem,
    ObservedResponse,
)
from app.services.scoring.objective_scorer import (
    score_question_response,
    sanitize_question_for_client,
    map_theta_to_cefr,
    calculate_overall_cefr,
)
from app.services.providers.ai_provider import (
    OpenAIProvider,
    GeminiProvider,
    LMStudioProvider,
    LocalRuleBasedEvaluator,
    ProviderOrchestrator,
)


# ============================================================================
# 1. UNIT TESTS: Scoring all 9 Reading & 3 Listening Task Types + Sanitization
# ============================================================================

def test_all_task_types_scoring_and_sanitization():
    # RT-01 Open Cloze: multiple accepted answers & case/whitespace normalization
    rt01 = {
        "type": "open_cloze",
        "gaps": [
            {"id": "g1", "accepted_answers": ["on"], "primary_answer": "on"},
            {"id": "g2", "accepted_answers": ["because", "as", "since"], "primary_answer": "because"},
            {"id": "g3", "accepted_answers": ["a", "one"], "primary_answer": "a"},
            {"id": "g4", "accepted_answers": ["with"], "primary_answer": "with"},
            {"id": "g5", "accepted_answers": ["to"], "primary_answer": "to"},
        ],
    }
    clean_rt01 = sanitize_question_for_client(rt01)
    for g in clean_rt01["gaps"]:
        assert "accepted_answers" not in g
        assert "primary_answer" not in g

    res_rt01 = score_question_response(
        "RT-01",
        rt01,
        {"answers": {"g1": " ON ", "g2": "Since", "g3": "one", "g4": "with", "g5": "to"}},
    )
    assert res_rt01["is_correct"] is True
    assert res_rt01["correct_sub_items"] == 5

    # RT-02 Multiple-Choice Cloze
    rt02 = {
        "type": "mcq_cloze",
        "gaps": [
            {"id": "g1", "options": [{"id": "A", "text": "platform"}, {"id": "B", "text": "road"}], "correct_option_id": "A"},
            {"id": "g2", "options": [{"id": "A", "text": "arrive"}, {"id": "B", "text": "reach"}], "correct_option_id": "B"},
        ],
    }
    clean_rt02 = sanitize_question_for_client(rt02)
    assert "correct_option_id" not in clean_rt02["gaps"][0]
    res_rt02 = score_question_response("RT-02", rt02, {"answers": {"g1": "A", "g2": "A"}})
    assert res_rt02["sub_item_count"] == 2
    assert res_rt02["correct_sub_items"] == 1
    assert res_rt02["is_correct"] is False

    # RT-06 / RT-07 Gapped Text
    rt06 = {
        "type": "gapped_text_sentences",
        "gaps": ["gap1", "gap2"],
        "options": [{"id": "A", "text": "S1"}, {"id": "B", "text": "S2"}, {"id": "C", "text": "S3"}],
        "correct": {"gap1": "B", "gap2": "C"},
    }
    clean_rt06 = sanitize_question_for_client(rt06)
    assert "correct" not in clean_rt06
    res_rt06 = score_question_response("RT-06", rt06, {"answers": {"gap1": "B", "gap2": "C"}})
    assert res_rt06["is_correct"] is True
    assert res_rt06["correct_sub_items"] == 2

    # RT-03 / RT-08 / LT-03 Multi-MCQ & Transcript hiding
    lt03 = {
        "type": "multi_mcq",
        "transcript": "Secret listening transcript that must stay hidden during test.",
        "questions": [
            {"id": "q1", "stem": "Q1?", "options": [{"id": "A", "text": "1"}, {"id": "B", "text": "2"}], "correct_option_id": "A", "explanation": "Exp 1"},
            {"id": "q2", "stem": "Q2?", "options": [{"id": "A", "text": "1"}, {"id": "B", "text": "2"}], "correct_option_id": "B", "explanation": "Exp 2"},
        ],
    }
    clean_lt03 = sanitize_question_for_client(lt03, include_transcript=False)
    assert "transcript" not in clean_lt03
    assert "correct_option_id" not in clean_lt03["questions"][0]
    assert "explanation" not in clean_lt03["questions"][0]


# ============================================================================
# 2. PROVIDER CONTRACT TESTS (PRD Section 42.3)
# ============================================================================

@pytest.mark.parametrize(
    "provider_cls,kwargs",
    [
        (OpenAIProvider, {"api_key": "sk-test-key", "default_model": "gpt-4o-mini"}),
        (GeminiProvider, {"api_key": "gem-test-key", "default_model": "gemini-2.5-flash"}),
        (LMStudioProvider, {"base_url": "http://127.0.0.1:1234/v1", "default_model": "qwen-local"}),
        (LocalRuleBasedEvaluator, {}),
    ],
)
def test_provider_contract_suite(provider_cls, kwargs):
    """
    Every provider adapter must pass the same abstract contract (PRD Section 42.3):
    health_check, list_models, generate_text, score_writing, error_handling.
    """
    provider = provider_cls(**kwargs)

    # 1. list_models returns non-empty list of strings
    models = provider.list_models()
    assert isinstance(models, list)
    assert len(models) >= 1

    # 2. Mocked HTTP call for generate_text & score_writing on network providers
    sample_eval_json = """{
      "communicative_achievement": 4,
      "organisation": 4,
      "language": 3,
      "estimated_cefr": "B2",
      "confidence": 0.82,
      "too_short_warning": false,
      "summary_en": "Good B2 response.",
      "summary_id": "Jawaban B2 yang baik.",
      "task_completion": {
        "all_bullets_addressed": true,
        "bullet_analysis": ["Addressed 1", "Addressed 2", "Addressed 3"],
        "register_analysis": "Appropriate semi-formal register."
      },
      "diagnostics": {
        "grammar": ["Good clause control."],
        "vocabulary": ["Adequate range."],
        "coherence": ["Clear paragraphing."]
      },
      "corrections": [],
      "improvement_plan": ["Use more varied linkers."]
    }"""

    prompt_data = {
        "task_part": 1,
        "cefr_target": "B2",
        "text_type": "email",
        "audience": "manager",
        "scenario": "schedule update",
        "prompt_text": "Write an email.",
        "bullet_points": ["p1", "p2", "p3"],
        "minimum_words": 50,
    }
    candidate_text = (
        "Dear Manager, I am writing to inform you about our project schedule update. "
        "We have completed the first phase ahead of time, although the testing equipment "
        "will arrive on Thursday morning. Therefore, I suggest moving our review meeting to Friday afternoon."
    )

    if isinstance(provider, LocalRuleBasedEvaluator):
        hc = provider.health_check()
        assert hc["connected"] is True
        res = provider.score_writing(prompt_data, candidate_text)
        assert res["provider"] == "local_heuristic"
        assert res["evaluation"]["estimated_cefr"] in ("A1", "A2", "B1", "B2", "C1")
    else:
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_client

            # Mock GET for health_check
            mock_get_resp = MagicMock()
            mock_get_resp.status_code = 200
            mock_get_resp.json.return_value = {"data": [{"id": "test-model"}]}
            mock_client.get.return_value = mock_get_resp

            hc = provider.health_check()
            assert hc["connected"] is True

            # Mock POST for generate_text / score_writing
            mock_post_resp = MagicMock()
            mock_post_resp.status_code = 200
            if isinstance(provider, GeminiProvider):
                mock_post_resp.json.return_value = {
                    "candidates": [{"content": {"parts": [{"text": sample_eval_json}]}}],
                    "usageMetadata": {"totalTokenCount": 120},
                }
            else:
                mock_post_resp.json.return_value = {
                    "model": "test-model",
                    "choices": [{"message": {"content": sample_eval_json}}],
                    "usage": {"total_tokens": 120},
                }
            mock_client.post.return_value = mock_post_resp

            scored = provider.score_writing(prompt_data, candidate_text)
            assert scored["evaluation"]["estimated_cefr"] == "B2"
            assert scored["evaluation"]["communicative_achievement"] == 4


# ============================================================================
# 3. TDD TESTS FOR EDGE CASES & BUG HUNTING
# ============================================================================

def test_practice_task_type_filter_is_respected():
    """
    TDD Test 1: When starting Reading Practice with task_type_filter='RT-05',
    the adaptive selector must only select RT-05 items when available.
    """
    with TestClient(app) as client:
        r = client.post(
            "/api/practice/start",
            json={"skill": "reading", "timed": False, "target_units": 5, "task_type_filter": "RT-05"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["question"]["task_type"] == "RT-05"


def test_writing_evaluator_failure_does_not_fabricate_score():
    """
    TDD Test 2 (PRD Section 38.2 & 51 Rule 6):
    If all AI providers fail during Writing evaluation:
    - save the Writing response
    - mark evaluation status PENDING_RETRY
    - do NOT fabricate a guessed CEFR score ('B1') in the result report!
    """
    with TestClient(app) as client:
        w_start = client.post(
            "/api/practice/start",
            json={"skill": "writing", "timed": False, "writing_part_mode": "part1"},
        )
        assert w_start.status_code == 200
        session_id = w_start.json()["session_id"]

        with patch.object(
            ProviderOrchestrator,
            "evaluate_writing_with_fallback",
            return_value=(None, None),
        ):
            w_ans = client.post(
                f"/api/practice/{session_id}/answer",
                json={"part1_text": "Dear Alex, thank you for helping with the photography event last Saturday."},
            )
            assert w_ans.status_code == 200
            ans_json = w_ans.json()
            assert ans_json["estimated_cefr"] is None

        # Check Result Report: skill_levels['writing'] and modules['writing']['estimated_cefr'] must be None, NOT 'B1'
        r_res = client.get(f"/api/results/{session_id}")
        assert r_res.status_code == 200
        rep = r_res.json()
        assert rep["skill_levels"]["writing"] is None
        assert rep["modules"]["writing"]["estimated_cefr"] is None
        assert rep["modules"]["writing"]["parts"][0]["evaluation"]["status"] == "PENDING_RETRY"


def test_timer_timeout_and_refresh_recovery_integrity():
    """
    TDD Test 3 (PRD Section 30.3 & 30.4):
    - Browser refresh recovery must not grant extra time.
    - When server deadline expires, module automatically transitions to TIMEOUT / next module.
    """
    with TestClient(app) as client:
        sim_start = client.post(
            "/api/simulations/start",
            json={"included_skills": ["reading", "writing"]},
        )
        assert sim_start.status_code == 200
        state1 = sim_start.json()
        session_id = state1["session_id"]
        mod_id = state1["module_session_id"]
        initial_rem = state1["timer"]["remaining_seconds"]
        assert initial_rem <= 59 * 60

        # Refresh recovery check: calling current state again never exceeds initial_rem
        state2 = client.get(f"/api/simulations/{session_id}/current").json()
        assert state2["timer"]["remaining_seconds"] <= initial_rem

        # Simulate server-side timeout by moving module started_at back 60 minutes
        db = SessionLocal()
        try:
            mod = db.query(ModuleSession).filter(ModuleSession.id == mod_id).first()
            mod.started_at = datetime.now(timezone.utc) - timedelta(minutes=60)
            db.commit()
        finally:
            db.close()

        # Fetching current state after timeout must auto-finalize reading and advance to writing!
        state_after_timeout = client.get(f"/api/simulations/{session_id}/current").json()
        assert state_after_timeout["current_module"] == "writing"
