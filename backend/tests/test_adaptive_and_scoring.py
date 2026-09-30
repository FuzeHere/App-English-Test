import math
import pytest
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
    map_theta_to_cefr,
    map_se_to_confidence,
    calculate_overall_cefr,
)


def test_rasch_probability():
    # At theta == b, probability must be 0.5
    assert math.isclose(rasch_probability(0.0, 0.0), 0.5, rel_tol=1e-6)
    assert math.isclose(rasch_probability(1.2, 1.2), 0.5, rel_tol=1e-6)
    # Higher theta than difficulty -> P > 0.5
    assert rasch_probability(1.0, 0.0) > 0.5
    # Lower theta than difficulty -> P < 0.5
    assert rasch_probability(-1.0, 0.0) < 0.5


def test_fisher_information():
    # Max information for 1PL occurs at theta == b: 0.5 * 0.5 = 0.25 per sub-item
    assert math.isclose(fisher_information(0.0, 0.0, sub_items=1), 0.25, rel_tol=1e-6)
    assert math.isclose(fisher_information(0.0, 0.0, sub_items=5), 1.25, rel_tol=1e-6)
    # Away from b, information decreases
    assert fisher_information(2.0, 0.0, sub_items=1) < 0.25


def test_eap_estimation_and_standard_error():
    # Prior only (no responses): theta = 0.0, SE = 1.0
    theta0, se0 = estimate_eap([])
    assert math.isclose(theta0, 0.0, abs_tol=1e-3)
    assert math.isclose(se0, 1.0, abs_tol=1e-2)

    # Answering correct items increases theta and reduces SE
    responses = [
        ObservedResponse(difficulty_b=0.0, is_correct=True, sub_items=1, correct_sub_items=1),
        ObservedResponse(difficulty_b=0.5, is_correct=True, sub_items=1, correct_sub_items=1),
        ObservedResponse(difficulty_b=1.0, is_correct=True, sub_items=1, correct_sub_items=1),
    ]
    theta_pos, se_pos = estimate_eap(responses)
    assert theta_pos > 0.5
    assert se_pos < se0

    # Answering incorrect items decreases theta
    neg_responses = [
        ObservedResponse(difficulty_b=0.0, is_correct=False, sub_items=1, correct_sub_items=0),
        ObservedResponse(difficulty_b=-0.5, is_correct=False, sub_items=1, correct_sub_items=0),
    ]
    theta_neg, _ = estimate_eap(neg_responses)
    assert theta_neg < -0.3


def test_item_selection_and_content_balancing():
    pool = [
        CandidateItem(id="q1", task_type="RT-01", primary_topic="tech", difficulty_theta=0.0, sub_item_count=5, usage_count=0),
        CandidateItem(id="q2", task_type="RT-01", primary_topic="travel", difficulty_theta=0.02, sub_item_count=5, usage_count=0),
        CandidateItem(id="q3", task_type="RT-02", primary_topic="work", difficulty_theta=0.05, sub_item_count=5, usage_count=0),
        CandidateItem(id="q4", task_type="RT-08", primary_topic="education", difficulty_theta=0.10, sub_item_count=5, usage_count=0),
    ]

    # Exclude already-used items and enforce max 2 consecutive task_type
    selected = select_next_item(
        current_theta=0.0,
        candidates=pool,
        used_item_ids={"q1"},
        recent_task_types=["RT-01", "RT-01"],
        recent_topics=["tech", "travel"],
        top_k=1,
    )
    assert selected is not None
    assert selected.id != "q1"
    # Because RT-01 appeared twice consecutively, q2 (also RT-01) must be filtered out
    assert selected.task_type != "RT-01"


def test_stopping_rules():
    # Less than minimum 12 item units -> should not stop
    stop, reason = check_stopping_condition(
        completed_item_units=8,
        standard_error=0.25,
        elapsed_seconds=600,
        max_time_seconds=3540,
        distinct_task_types=3,
        min_item_units=12,
        target_se=0.30,
    )
    assert not stop

    # >= 12 item units, SE <= 0.30, >= 3 distinct task types -> stop with precision
    stop2, reason2 = check_stopping_condition(
        completed_item_units=14,
        standard_error=0.28,
        elapsed_seconds=1200,
        max_time_seconds=3540,
        distinct_task_types=3,
        min_item_units=12,
        target_se=0.30,
    )
    assert stop2
    assert reason2 == "precision_reached"

    # Timeout reached -> stop regardless of SE
    stop3, reason3 = check_stopping_condition(
        completed_item_units=6,
        standard_error=0.55,
        elapsed_seconds=3540,
        max_time_seconds=3540,
        distinct_task_types=2,
        min_item_units=12,
        target_se=0.30,
    )
    assert stop3
    assert reason3 == "time_limit_reached"


def test_objective_scoring_and_cefr_mapping():
    # Open Cloze scoring
    open_cloze_content = {
        "type": "open_cloze",
        "gaps": [
            {"id": "g1", "accepted_answers": ["in", "within"], "primary_answer": "in"},
            {"id": "g2", "accepted_answers": ["which", "that"], "primary_answer": "which"},
        ],
    }
    res = score_question_response("RT-01", open_cloze_content, {"answers": {"g1": " IN ", "g2": "who"}})
    assert res["sub_item_count"] == 2
    assert res["correct_sub_items"] == 1
    assert res["is_correct"] is False

    # CEFR mapping
    assert map_theta_to_cefr(-1.5) == "A1"
    assert map_theta_to_cefr(-0.8) == "A2"
    assert map_theta_to_cefr(0.0) == "B1"
    assert map_theta_to_cefr(0.8) == "B2"
    assert map_theta_to_cefr(1.5) == "C1"

    # Overall CEFR calculation
    assert calculate_overall_cefr("B2", "B1", "B2") == "B2"
    assert calculate_overall_cefr("A2", "B1", "B1") == "B1"
    assert map_se_to_confidence(0.26) == "High confidence"
    assert map_se_to_confidence(0.38) == "Moderate confidence"
    assert map_se_to_confidence(0.55) == "Limited confidence"
