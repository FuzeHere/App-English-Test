import math
import random
from dataclasses import dataclass
from typing import List, Set, Optional, Tuple
from app.core.config import settings


@dataclass
class CandidateItem:
    id: str
    task_type: str
    primary_topic: str
    difficulty_theta: float
    sub_item_count: int = 1
    usage_count: int = 0


@dataclass
class ObservedResponse:
    difficulty_b: float
    is_correct: bool
    sub_items: int = 1
    correct_sub_items: int = 1


def rasch_probability(theta: float, b: float) -> float:
    """
    1PL Rasch probability model (PRD Section 15.2):
    P(X = 1 | theta, b) = 1 / (1 + exp(-(theta - b)))
    """
    diff = max(-20.0, min(20.0, theta - b))
    return 1.0 / (1.0 + math.exp(-diff))


def fisher_information(theta: float, b: float, sub_items: int = 1) -> float:
    """
    1PL Fisher Information (PRD Section 15.6 & 15.10):
    I(theta) = P(theta) * (1 - P(theta)) * sub_items
    """
    p = rasch_probability(theta, b)
    return p * (1.0 - p) * max(1, sub_items)


def estimate_eap(
    responses: List[ObservedResponse],
    prior_mean: Optional[float] = None,
    prior_sd: Optional[float] = None,
    grid_min: float = -4.0,
    grid_max: float = 4.0,
    grid_points: int = 161,
) -> Tuple[float, float]:
    """
    Expected A Posteriori (EAP) ability estimator with Gaussian prior (PRD Section 15.3).
    Returns (theta_estimate, standard_error).
    Handles both single-item and multi-subquestion polytomous/binomial task units (Section 15.10).
    """
    mu = settings.IRT_PRIOR_MEAN if prior_mean is None else prior_mean
    sd = settings.IRT_PRIOR_SD if prior_sd is None else prior_sd

    step = (grid_max - grid_min) / (grid_points - 1)
    thetas = [grid_min + i * step for i in range(grid_points)]

    log_posteriors = []
    for t in thetas:
        # Normal log prior
        log_prior = -0.5 * (((t - mu) / sd) ** 2)
        log_lik = 0.0
        for r in responses:
            p = rasch_probability(t, r.difficulty_b)
            p = max(1e-9, min(1.0 - 1e-9, p))
            n = max(1, r.sub_items)
            k = max(0, min(n, r.correct_sub_items if r.sub_items > 1 else (1 if r.is_correct else 0)))
            log_lik += k * math.log(p) + (n - k) * math.log(1.0 - p)
        log_posteriors.append(log_prior + log_lik)

    max_lp = max(log_posteriors)
    weights = [math.exp(lp - max_lp) for lp in log_posteriors]
    total_weight = sum(weights)

    if total_weight <= 0:
        return mu, sd

    norm_weights = [w / total_weight for w in weights]
    eap_theta = sum(t * w for t, w in zip(thetas, norm_weights))
    variance = sum(w * ((t - eap_theta) ** 2) for t, w in zip(thetas, norm_weights))
    standard_error = math.sqrt(max(1e-6, variance))

    return round(eap_theta, 4), round(standard_error, 4)


def select_next_item(
    current_theta: float,
    candidates: List[CandidateItem],
    used_item_ids: Set[str],
    recent_task_types: List[str],
    recent_topics: List[str],
    top_k: Optional[int] = None,
    rng_seed: Optional[int] = None,
) -> Optional[CandidateItem]:
    """
    Selects the next adaptive item based on Fisher information, content-balancing rules,
    and exposure control (PRD Section 15.6 - 15.8).
    """
    k = settings.IRT_TOP_K_EXPOSURE if top_k is None else top_k
    available = [c for c in candidates if c.id not in used_item_ids]
    if not available:
        return None

    # Content-balancing constraints (Section 15.7):
    # 1. No same task_type more than 2 times consecutively
    filtered = available
    if len(recent_task_types) >= 2 and recent_task_types[-1] == recent_task_types[-2]:
        blocked_task = recent_task_types[-1]
        non_repeating_task = [c for c in filtered if c.task_type != blocked_task]
        if non_repeating_task:
            filtered = non_repeating_task

    # 2. No same topic more than 2 times consecutively
    if len(recent_topics) >= 2 and recent_topics[-1] == recent_topics[-2]:
        blocked_topic = recent_topics[-1]
        non_repeating_topic = [c for c in filtered if c.primary_topic != blocked_topic]
        if non_repeating_topic:
            filtered = non_repeating_topic

    # 3. Encourage task diversity if < 3 distinct task types seen so far
    distinct_seen = set(recent_task_types)
    if 0 < len(distinct_seen) < 3 and len(recent_task_types) >= 2:
        unseen_type_items = [c for c in filtered if c.task_type not in distinct_seen]
        if unseen_type_items:
            filtered = unseen_type_items

    # Score each candidate by Fisher Information at current_theta with slight exposure penalty
    scored = []
    for item in filtered:
        # Per-unit information so 5-item tasks don't always dominate 1-item tasks purely by count
        unit_info = fisher_information(current_theta, item.difficulty_theta, sub_items=1)
        exposure_factor = 1.0 / (1.0 + 0.03 * max(0, item.usage_count))
        score = unit_info * exposure_factor
        scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_candidates = [item for _, item in scored[: max(1, k)]]

    if rng_seed is not None:
        rng = random.Random(rng_seed)
        return rng.choice(top_candidates)
    return random.choice(top_candidates)


def check_stopping_condition(
    completed_item_units: int,
    standard_error: float,
    elapsed_seconds: int,
    max_time_seconds: Optional[int],
    distinct_task_types: int,
    min_item_units: Optional[int] = None,
    max_item_units: Optional[int] = None,
    target_se: Optional[float] = None,
) -> Tuple[bool, str]:
    """
    Evaluates whether the adaptive module should terminate (PRD Section 15.9 & 16).
    Returns (should_stop, reason).
    """
    min_units = settings.IRT_MIN_ITEM_UNITS_SIMULATION if min_item_units is None else min_item_units
    max_units = settings.IRT_MAX_ITEM_UNITS_SIMULATION if max_item_units is None else max_item_units
    se_threshold = settings.IRT_TARGET_SE if target_se is None else target_se

    if max_time_seconds is not None and elapsed_seconds >= max_time_seconds:
        return True, "time_limit_reached"

    if max_units is not None and completed_item_units >= max_units:
        return True, "target_items_completed"

    if completed_item_units >= min_units and standard_error <= se_threshold and distinct_task_types >= min(3, completed_item_units):
        return True, "precision_reached"

    return False, "continue"
