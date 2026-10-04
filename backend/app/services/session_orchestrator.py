import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import func
from fastapi import HTTPException

from app.core.config import settings
from app.models.entities import (
    QuestionItem,
    AudioAsset,
    WritingPrompt,
    TestSession,
    ModuleSession,
    ItemResponse,
    WritingSubmission,
    WritingEvaluation,
    AppSetting,
)
from app.services.adaptive.irt_engine import (
    CandidateItem,
    ObservedResponse,
    estimate_eap,
    select_next_item,
    check_stopping_condition,
)
from app.services.scoring.objective_scorer import (
    get_question_sub_item_count,
    score_question_response,
    sanitize_question_for_client,
    map_theta_to_cefr,
    map_se_to_confidence,
    calculate_overall_cefr,
    get_can_do_statements,
)
from app.services.providers.ai_provider import ProviderOrchestrator
from app.services.question_generation.validator import READING_TASK_TYPES, LISTENING_TASK_TYPES


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ensure_aware(dt: Optional[datetime]) -> datetime:
    if dt is None:
        return utcnow()
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def compute_elapsed_and_remaining(mod: ModuleSession) -> tuple[int, Optional[int], bool]:
    """
    Server-authoritative timer calculation (PRD Section 30).
    Returns (elapsed_seconds, remaining_seconds, is_timed_out).
    """
    if mod.status in ("COMPLETED", "TIMEOUT") and mod.ended_at:
        elapsed = mod.elapsed_seconds
    else:
        started = ensure_aware(mod.started_at)
        elapsed = max(0, int((utcnow() - started).total_seconds()))

    if mod.time_limit_seconds is None:
        return elapsed, None, False

    remaining = max(0, mod.time_limit_seconds - elapsed)
    timed_out = remaining <= 0 and mod.status == "IN_PROGRESS"
    return elapsed, remaining, timed_out


def get_app_settings_dict(db: Session) -> Dict[str, Any]:
    row = db.query(AppSetting).filter(AppSetting.key == "global_config").first()
    defaults = {
        "ai_default_provider": settings.AI_DEFAULT_PROVIDER,
        "writing_default_provider": settings.WRITING_DEFAULT_PROVIDER,
        "generation_model": settings.LM_STUDIO_MODEL,
        "writing_evaluation_model": settings.LM_STUDIO_MODEL,
        "openai_model": settings.OPENAI_MODEL,
        "gemini_model": settings.GEMINI_MODEL,
        "lm_studio_base_url": settings.LM_STUDIO_BASE_URL,
        "tts_provider": "local",
        "tts_voice": "en_voice_01",
        "reading_max_minutes": 59,
        "listening_max_minutes": 59,
        "writing_max_minutes": 45,
        "practice_explanations": True,
        "cefr_theta_thresholds": settings.CEFR_THETA_THRESHOLDS,
    }
    if row and isinstance(row.value_json, dict):
        defaults.update(row.value_json)
    return defaults


def _select_next_adaptive_question_for_module(db: Session, mod: ModuleSession) -> Optional[QuestionItem]:
    """
    Runs the 1PL IRT adaptive selector for Reading or Listening module sessions.
    """
    query = db.query(QuestionItem).filter(QuestionItem.skill == mod.skill, QuestionItem.status == "APPROVED")
    task_filter = (mod.state_json or {}).get("task_type_filter")
    if task_filter:
        filtered_pool = query.filter(QuestionItem.task_type == task_filter).all()
        approved_pool = filtered_pool if filtered_pool else query.all()
    else:
        approved_pool = query.all()

    if not approved_pool:
        return None

    prev_responses = (
        db.query(ItemResponse)
        .filter(ItemResponse.module_session_id == mod.id)
        .order_by(ItemResponse.item_position.asc())
        .all()
    )
    used_ids = {r.question_id for r in prev_responses if r.question_id}

    q_by_id = {q.id: q for q in approved_pool}
    recent_task_types = [q_by_id[r.question_id].task_type for r in prev_responses if r.question_id in q_by_id]
    recent_topics = [q_by_id[r.question_id].primary_topic for r in prev_responses if r.question_id in q_by_id]

    current_theta = mod.final_theta if mod.final_theta is not None else settings.IRT_PRIOR_MEAN

    candidates = [
        CandidateItem(
            id=q.id,
            task_type=q.task_type,
            primary_topic=q.primary_topic,
            difficulty_theta=q.difficulty_theta,
            sub_item_count=get_question_sub_item_count(q.task_type, q.content_json or {}),
            usage_count=q.usage_count or 0,
        )
        for q in approved_pool
    ]

    chosen = select_next_item(
        current_theta=current_theta,
        candidates=candidates,
        used_item_ids=used_ids,
        recent_task_types=recent_task_types,
        recent_topics=recent_topics,
    )
    if not chosen:
        return None

    return q_by_id.get(chosen.id)


def _format_question_payload_for_client(
    db: Session,
    q: QuestionItem,
    mod: ModuleSession,
    session_mode: str,
) -> Dict[str, Any]:
    """
    Formats an active question for the client while enforcing Exam Integrity Rules (PRD Section 31):
    - Never sends answer keys or explanations before submission.
    - Never sends CEFR target or difficulty_theta in Full Simulation.
    """
    audio_asset = None
    if q.skill == "listening":
        asset = db.query(AudioAsset).filter(AudioAsset.question_id == q.id).first()
        if asset:
            audio_asset = {
                "id": asset.id,
                "url": asset.file_path,
                "duration_seconds": asset.duration_seconds,
                "format": asset.format,
                "voice": asset.voice,
            }

    sanitized_content = sanitize_question_for_client(q.content_json or {}, include_transcript=False)

    task_labels = {**READING_TASK_TYPES, **LISTENING_TASK_TYPES}
    payload = {
        "question_id": q.id,
        "skill": q.skill,
        "task_type": q.task_type,
        "task_type_label": task_labels.get(q.task_type, q.task_type),
        "primary_topic": q.primary_topic,
        "scenario": q.scenario,
        "content_version": q.version,
        "sub_item_count": get_question_sub_item_count(q.task_type, q.content_json or {}),
        "content": sanitized_content,
        "audio": audio_asset,
        "playback_rules": {
            "auto_play_count": 2 if session_mode == "FULL_SIMULATION" else 1,
            "allow_pause": session_mode != "FULL_SIMULATION",
            "allow_replay": session_mode != "FULL_SIMULATION",
            "allow_seek": session_mode != "FULL_SIMULATION",
            "prelistening_seconds": (q.content_json or {}).get("prelistening_seconds", 10),
        } if q.skill == "listening" else None,
    }
    return payload


def start_practice_session(
    db: Session,
    skill: str,
    timed: bool = False,
    target_units: Optional[int] = 10,
    writing_part_mode: str = "full",  # 'part1' | 'part2' | 'full'
    task_type_filter: Optional[str] = None,
) -> Dict[str, Any]:
    skill = skill.lower()
    if skill not in ("reading", "listening", "writing"):
        raise HTTPException(status_code=400, detail="Invalid skill. Choose reading, listening, or writing.")

    # Verify bank availability
    if skill in ("reading", "listening"):
        count = db.query(QuestionItem).filter(QuestionItem.skill == skill, QuestionItem.status == "APPROVED").count()
        if count == 0:
            raise HTTPException(status_code=400, detail=f"No approved {skill} items in Question Bank. Generate and approve items in Content Studio first.")
    else:
        wp_count = db.query(WritingPrompt).filter(WritingPrompt.status == "APPROVED").count()
        if wp_count == 0:
            raise HTTPException(status_code=400, detail="No approved writing prompts available.")

    time_limit = None
    if timed:
        if skill == "reading":
            time_limit = settings.READING_MAX_TIME_SECONDS
        elif skill == "listening":
            time_limit = settings.LISTENING_MAX_TIME_SECONDS
        else:
            time_limit = settings.WRITING_MAX_TIME_SECONDS

    session = TestSession(
        mode="PRACTICE",
        status="IN_PROGRESS",
        current_module=skill,
        module_order=[skill],
        settings_json={
            "timed": timed,
            "target_units": target_units,
            "writing_part_mode": writing_part_mode,
            "task_type_filter": task_type_filter,
        },
    )
    db.add(session)
    db.flush()

    mod_state: Dict[str, Any] = {
        "completed_units": 0,
        "target_units": target_units or 12,
        "task_type_filter": task_type_filter,
    }

    if skill == "writing":
        p1 = db.query(WritingPrompt).filter(WritingPrompt.status == "APPROVED", WritingPrompt.task_part == 1).order_by(func.random()).first()
        p2 = db.query(WritingPrompt).filter(WritingPrompt.status == "APPROVED", WritingPrompt.task_part == 2).order_by(func.random()).first()
        mod_state["writing_part_mode"] = writing_part_mode
        mod_state["part1_prompt_id"] = p1.id if p1 else None
        mod_state["part2_prompt_id"] = p2.id if p2 else None
        mod_state["active_part"] = 2 if writing_part_mode == "part2" else 1

    mod = ModuleSession(
        test_session_id=session.id,
        skill=skill,
        status="IN_PROGRESS",
        time_limit_seconds=time_limit,
        final_theta=0.0 if skill in ("reading", "listening") else None,
        standard_error=1.0 if skill in ("reading", "listening") else None,
        state_json=mod_state,
    )
    db.add(mod)
    db.flush()

    if skill in ("reading", "listening"):
        first_q = _select_next_adaptive_question_for_module(db, mod)
        if first_q:
            mod.current_question_id = first_q.id

    db.commit()
    return get_current_session_state(db, session.id)


def start_full_simulation_session(
    db: Session,
    included_skills: Optional[List[str]] = None,
) -> Dict[str, Any]:
    skills = [s.lower() for s in (included_skills or ["reading", "listening", "writing"]) if s.lower() in ("reading", "listening", "writing")]
    if not skills:
        skills = ["reading", "listening", "writing"]

    # Check bank health before starting Full Simulation (PRD Section 21.4)
    for sk in skills:
        if sk in ("reading", "listening"):
            cnt = db.query(QuestionItem).filter(QuestionItem.skill == sk, QuestionItem.status == "APPROVED").count()
            if cnt < 3:
                raise HTTPException(
                    status_code=400,
                    detail=f"Content Bank warning: Insufficient approved items for {sk} ({cnt} available). Please approve more items in Content Studio.",
                )
        elif sk == "writing":
            p1_cnt = db.query(WritingPrompt).filter(WritingPrompt.status == "APPROVED", WritingPrompt.task_part == 1).count()
            p2_cnt = db.query(WritingPrompt).filter(WritingPrompt.status == "APPROVED", WritingPrompt.task_part == 2).count()
            if p1_cnt < 1 or p2_cnt < 1:
                raise HTTPException(
                    status_code=400,
                    detail="Content Bank warning: Writing requires at least 1 approved Part 1 prompt and 1 approved Part 2 prompt.",
                )

    first_skill = skills[0]
    session = TestSession(
        mode="FULL_SIMULATION",
        status="IN_PROGRESS",
        current_module=first_skill,
        module_order=skills,
        settings_json={"strict_exam_conditions": True},
    )
    db.add(session)
    db.flush()

    _create_module_session_for_skill(db, session, first_skill)
    db.commit()
    return get_current_session_state(db, session.id)


def _create_module_session_for_skill(db: Session, session: TestSession, skill: str) -> ModuleSession:
    if skill == "reading":
        limit = settings.READING_MAX_TIME_SECONDS
    elif skill == "listening":
        limit = settings.LISTENING_MAX_TIME_SECONDS
    else:
        limit = settings.WRITING_MAX_TIME_SECONDS

    mod_state: Dict[str, Any] = {
        "completed_units": 0,
        "target_units": settings.IRT_MIN_ITEM_UNITS_SIMULATION,
    }

    if skill == "writing":
        p1 = db.query(WritingPrompt).filter(WritingPrompt.status == "APPROVED", WritingPrompt.task_part == 1).order_by(func.random()).first()
        p2 = db.query(WritingPrompt).filter(WritingPrompt.status == "APPROVED", WritingPrompt.task_part == 2).order_by(func.random()).first()
        mod_state["writing_part_mode"] = "full"
        mod_state["part1_prompt_id"] = p1.id if p1 else None
        mod_state["part2_prompt_id"] = p2.id if p2 else None
        mod_state["active_part"] = 1

    mod = ModuleSession(
        test_session_id=session.id,
        skill=skill,
        status="IN_PROGRESS",
        time_limit_seconds=limit,
        final_theta=0.0 if skill in ("reading", "listening") else None,
        standard_error=1.0 if skill in ("reading", "listening") else None,
        state_json=mod_state,
    )
    db.add(mod)
    db.flush()

    if skill in ("reading", "listening"):
        first_q = _select_next_adaptive_question_for_module(db, mod)
        if first_q:
            mod.current_question_id = first_q.id

    return mod


def get_active_module_session(db: Session, session: TestSession) -> Optional[ModuleSession]:
    if not session.current_module:
        return None
    return (
        db.query(ModuleSession)
        .filter(
            ModuleSession.test_session_id == session.id,
            ModuleSession.skill == session.current_module,
        )
        .order_by(ModuleSession.started_at.desc())
        .first()
    )


def get_current_session_state(db: Session, session_id: str) -> Dict[str, Any]:
    session = db.query(TestSession).filter(TestSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    mod = get_active_module_session(db, session)
    if not mod or session.status in ("COMPLETED", "TIMEOUT", "ABANDONED"):
        return {
            "session_id": session.id,
            "mode": session.mode,
            "status": session.status,
            "current_module": session.current_module,
            "module_order": session.module_order,
            "overall_level": session.overall_level,
            "is_finished": True,
        }

    elapsed, remaining, timed_out = compute_elapsed_and_remaining(mod)
    mod.elapsed_seconds = elapsed
    if timed_out:
        _finalize_module_session(db, session, mod, time_limited=True)
        db.commit()
        return get_current_session_state(db, session.id)

    responses_count = db.query(ItemResponse).filter(ItemResponse.module_session_id == mod.id).count()
    state_json = mod.state_json or {}

    if mod.skill in ("reading", "listening"):
        q = None
        if mod.current_question_id:
            q = db.query(QuestionItem).filter(QuestionItem.id == mod.current_question_id).first()
        if not q:
            q = _select_next_adaptive_question_for_module(db, mod)
            if q:
                mod.current_question_id = q.id
                db.commit()

        if not q:
            # No more unused items in bank -> finalize module cleanly
            _finalize_module_session(db, session, mod, time_limited=False)
            db.commit()
            return get_current_session_state(db, session.id)

        question_payload = _format_question_payload_for_client(db, q, mod, session.mode)
        return {
            "session_id": session.id,
            "mode": session.mode,
            "status": session.status,
            "current_module": mod.skill,
            "module_session_id": mod.id,
            "module_order": session.module_order,
            "is_finished": False,
            "timer": {
                "time_limit_seconds": mod.time_limit_seconds,
                "elapsed_seconds": elapsed,
                "remaining_seconds": remaining,
                "server_timestamp": utcnow().isoformat(),
            },
            "progress": {
                "tasks_completed": responses_count,
                "completed_item_units": state_json.get("completed_units", 0),
                "target_min_units": state_json.get("target_units", settings.IRT_MIN_ITEM_UNITS_SIMULATION),
            },
            "question": question_payload,
        }

    # Writing module state
    p1_id = state_json.get("part1_prompt_id")
    p2_id = state_json.get("part2_prompt_id")
    p1 = db.query(WritingPrompt).filter(WritingPrompt.id == p1_id).first() if p1_id else None
    p2 = db.query(WritingPrompt).filter(WritingPrompt.id == p2_id).first() if p2_id else None

    existing_subs = db.query(WritingSubmission).filter(WritingSubmission.module_session_id == mod.id).all()
    drafts = {s.part_number: s.response_text for s in existing_subs}

    prompts_payload = []
    for p in (p1, p2):
        if p:
            prompts_payload.append({
                "prompt_id": p.id,
                "task_part": p.task_part,
                "text_type": p.text_type,
                "audience": p.audience,
                "scenario": p.scenario,
                "prompt_text": p.prompt_text,
                "bullet_points": p.bullet_points,
                "minimum_words": p.minimum_words,
                "recommended_minutes": p.recommended_minutes,
                "saved_text": drafts.get(p.task_part, ""),
            })

    return {
        "session_id": session.id,
        "mode": session.mode,
        "status": session.status,
        "current_module": "writing",
        "module_session_id": mod.id,
        "module_order": session.module_order,
        "is_finished": False,
        "timer": {
            "time_limit_seconds": mod.time_limit_seconds,
            "elapsed_seconds": elapsed,
            "remaining_seconds": remaining,
            "server_timestamp": utcnow().isoformat(),
        },
        "writing": {
            "writing_part_mode": state_json.get("writing_part_mode", "full"),
            "active_part": state_json.get("active_part", 1),
            "prompts": prompts_payload,
        },
    }


def submit_objective_answer(
    db: Session,
    session_id: str,
    question_id: str,
    user_answer: Dict[str, Any],
    response_time_seconds: int = 15,
) -> Dict[str, Any]:
    """
    Processes a Reading or Listening response, updates the 1PL IRT EAP estimate,
    records pre/post theta, and determines whether to continue or stop (PRD Section 15 & 16).
    """
    session = db.query(TestSession).filter(TestSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    mod = get_active_module_session(db, session)
    if not mod or mod.skill not in ("reading", "listening"):
        raise HTTPException(status_code=400, detail="No active Reading or Listening module in this session")

    elapsed, remaining, timed_out = compute_elapsed_and_remaining(mod)
    mod.elapsed_seconds = elapsed
    if timed_out:
        _finalize_module_session(db, session, mod, time_limited=True)
        db.commit()
        return {
            "module_finished": True,
            "session_finished": session.status == "COMPLETED",
            "reason": "time_limit_reached",
        }

    q = db.query(QuestionItem).filter(QuestionItem.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    # Score response deterministically
    score_res = score_question_response(q.task_type, q.content_json or {}, user_answer)
    pre_theta = mod.final_theta if mod.final_theta is not None else settings.IRT_PRIOR_MEAN

    prev_responses = (
        db.query(ItemResponse)
        .filter(ItemResponse.module_session_id == mod.id)
        .order_by(ItemResponse.item_position.asc())
        .all()
    )

    q_ids = [r.question_id for r in prev_responses if r.question_id] + [q.id]
    q_lookup = {
        item.id: item
        for item in db.query(QuestionItem).filter(QuestionItem.id.in_(q_ids)).all()
    }

    observed: List[ObservedResponse] = []
    for r in prev_responses:
        q_past = q_lookup.get(r.question_id)
        if q_past:
            observed.append(
                ObservedResponse(
                    difficulty_b=q_past.difficulty_theta,
                    is_correct=bool(r.is_correct),
                    sub_items=r.sub_item_count,
                    correct_sub_items=r.correct_sub_items,
                )
            )
    observed.append(
        ObservedResponse(
            difficulty_b=q.difficulty_theta,
            is_correct=score_res["is_correct"],
            sub_items=score_res["sub_item_count"],
            correct_sub_items=score_res["correct_sub_items"],
        )
    )

    post_theta, post_se = estimate_eap(observed)

    new_resp = ItemResponse(
        module_session_id=mod.id,
        question_id=q.id,
        item_position=len(prev_responses) + 1,
        sub_item_count=score_res["sub_item_count"],
        correct_sub_items=score_res["correct_sub_items"],
        answer_json=user_answer,
        is_correct=score_res["is_correct"],
        response_time_seconds=max(1, response_time_seconds),
        pre_theta=pre_theta,
        post_theta=post_theta,
        post_se=post_se,
        content_version=q.version,
    )
    db.add(new_resp)

    # Update item exposure usage count
    q.usage_count = (q.usage_count or 0) + 1

    # Update module adaptive state
    mod.final_theta = post_theta
    mod.standard_error = post_se
    total_units = sum(o.sub_items for o in observed)
    distinct_types = len({q_lookup[qid].task_type for qid in q_ids if qid in q_lookup})

    state_json = dict(mod.state_json or {})
    state_json["completed_units"] = total_units
    mod.state_json = state_json

    target_units = state_json.get("target_units", settings.IRT_MIN_ITEM_UNITS_SIMULATION)
    max_units = target_units if session.mode == "PRACTICE" else settings.IRT_MAX_ITEM_UNITS_SIMULATION
    min_units = min(target_units, settings.IRT_MIN_ITEM_UNITS_SIMULATION)

    should_stop, stop_reason = check_stopping_condition(
        completed_item_units=total_units,
        standard_error=post_se,
        elapsed_seconds=elapsed,
        max_time_seconds=mod.time_limit_seconds,
        distinct_task_types=distinct_types,
        min_item_units=min_units,
        max_item_units=max_units,
        target_se=settings.IRT_TARGET_SE,
    )

    next_q = None
    if not should_stop:
        db.flush()
        next_q = _select_next_adaptive_question_for_module(db, mod)
        if next_q:
            mod.current_question_id = next_q.id
        else:
            should_stop = True
            stop_reason = "bank_exhausted"

    if should_stop:
        _finalize_module_session(db, session, mod, time_limited=(stop_reason == "time_limit_reached"))

    db.commit()

    # In Practice Mode, return immediate feedback, explanation, and transcript (PRD Section 6.1 & 16)
    practice_feedback = None
    if session.mode == "PRACTICE":
        practice_feedback = {
            "is_correct": score_res["is_correct"],
            "sub_item_count": score_res["sub_item_count"],
            "correct_sub_items": score_res["correct_sub_items"],
            "details": score_res["details"],
            "correct_answer_summary": score_res["correct_answer_summary"],
            "explanation": q.explanation,
            "cefr_target": q.cefr_target,
            "transcript": (q.content_json or {}).get("transcript") if q.skill == "listening" else None,
            "updated_theta": post_theta,
            "updated_cefr_estimate": map_theta_to_cefr(post_theta),
        }

    return {
        "submitted_question_id": q.id,
        "module_finished": should_stop,
        "stop_reason": stop_reason if should_stop else None,
        "session_finished": session.status == "COMPLETED",
        "current_module": session.current_module,
        "practice_feedback": practice_feedback,
    }


def submit_writing_module(
    db: Session,
    session_id: str,
    part1_text: Optional[str] = None,
    part2_text: Optional[str] = None,
    preferred_provider: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Saves Part 1 and Part 2 writing responses, runs AI evaluation via ProviderOrchestrator,
    and finalizes the Writing module (PRD Section 12 & 13).
    """
    session = db.query(TestSession).filter(TestSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    mod = get_active_module_session(db, session)
    if not mod or mod.skill != "writing":
        raise HTTPException(status_code=400, detail="Writing module is not currently active")

    elapsed, _, _ = compute_elapsed_and_remaining(mod)
    mod.elapsed_seconds = elapsed

    state_json = mod.state_json or {}
    part_mode = state_json.get("writing_part_mode", "full")
    p1_id = state_json.get("part1_prompt_id")
    p2_id = state_json.get("part2_prompt_id")

    app_cfg = get_app_settings_dict(db)
    orchestrator = ProviderOrchestrator(db, app_config=app_cfg)
    locked_provider = session.locked_ai_provider
    chosen_provider = preferred_provider or app_cfg.get("writing_default_provider", settings.WRITING_DEFAULT_PROVIDER)

    parts_to_process = []
    if part_mode in ("part1", "full") and p1_id:
        parts_to_process.append((1, p1_id, part1_text or ""))
    if part_mode in ("part2", "full") and p2_id:
        parts_to_process.append((2, p2_id, part2_text or ""))

    part_cefrs: List[str] = []
    part_confidences: List[float] = []

    for part_num, prompt_id, resp_text in parts_to_process:
        prompt_obj = db.query(WritingPrompt).filter(WritingPrompt.id == prompt_id).first()
        if not prompt_obj:
            continue

        words = [w for w in re.split(r"\s+", (resp_text or "").strip()) if w]
        sub = WritingSubmission(
            module_session_id=mod.id,
            writing_prompt_id=prompt_obj.id,
            part_number=part_num,
            response_text=resp_text or "",
            word_count=len(words),
        )
        db.add(sub)
        db.flush()

        prompt_dict = {
            "task_part": prompt_obj.task_part,
            "cefr_target": prompt_obj.cefr_target,
            "text_type": prompt_obj.text_type,
            "audience": prompt_obj.audience,
            "scenario": prompt_obj.scenario,
            "prompt_text": prompt_obj.prompt_text,
            "bullet_points": prompt_obj.bullet_points,
            "minimum_words": prompt_obj.minimum_words,
        }

        eval_res, used_prov = orchestrator.evaluate_writing_with_fallback(
            prompt_data=prompt_dict,
            candidate_response=resp_text or "",
            preferred_provider=chosen_provider,
            locked_provider=locked_provider,
            model=app_cfg.get("writing_evaluation_model"),
        )

        if eval_res and used_prov:
            locked_provider = used_prov
            session.locked_ai_provider = used_prov
            ev_data = eval_res["evaluation"]
            est_cefr = ev_data.get("estimated_cefr", "B1")
            conf = float(ev_data.get("confidence", 0.75))
            part_cefrs.append(est_cefr)
            part_confidences.append(conf)

            w_eval = WritingEvaluation(
                submission_id=sub.id,
                provider=used_prov,
                model=eval_res.get("model", "default"),
                evaluation_version="1.0",
                status="COMPLETED",
                communicative_achievement=float(ev_data.get("communicative_achievement", 3)),
                organisation=float(ev_data.get("organisation", 3)),
                language=float(ev_data.get("language", 3)),
                estimated_cefr=est_cefr,
                confidence=conf,
                feedback_json=ev_data,
            )
            db.add(w_eval)
        else:
            # PRD Section 38.2: Never fabricate a score if all providers fail
            w_eval = WritingEvaluation(
                submission_id=sub.id,
                provider=chosen_provider,
                model="unavailable",
                evaluation_version="1.0",
                status="PENDING_RETRY",
                feedback_json={
                    "message": "Your writing has been saved, but automated evaluation is temporarily unavailable."
                },
            )
            db.add(w_eval)

    # Combine Part 1 and Part 2 CEFR estimates
    if part_cefrs:
        ordinal = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5}
        rev = {1: "A1", 2: "A2", 3: "B1", 4: "B2", 5: "C1"}
        # Weight Part 2 slightly higher (60% Part 2, 40% Part 1) when both exist
        if len(part_cefrs) == 2:
            combined_num = round(0.4 * ordinal.get(part_cefrs[0], 3) + 0.6 * ordinal.get(part_cefrs[1], 3))
        else:
            combined_num = ordinal.get(part_cefrs[0], 3)
        mod.estimated_cefr = rev.get(max(1, min(5, int(combined_num))), "B1")
        avg_conf = sum(part_confidences) / len(part_confidences)
        mod.confidence_label = "High confidence" if avg_conf >= 0.75 else ("Moderate confidence" if avg_conf >= 0.55 else "Limited confidence")
    else:
        mod.estimated_cefr = None
        mod.confidence_label = "Pending evaluation"

    _finalize_module_session(db, session, mod, time_limited=False)
    db.commit()
    return {
        "session_id": session.id,
        "module_finished": True,
        "session_finished": session.status == "COMPLETED",
        "estimated_cefr": mod.estimated_cefr,
    }


def _finalize_module_session(
    db: Session,
    session: TestSession,
    mod: ModuleSession,
    time_limited: bool = False,
) -> None:
    mod.status = "TIMEOUT" if time_limited else "COMPLETED"
    mod.ended_at = utcnow()
    mod.current_question_id = None

    if mod.skill in ("reading", "listening"):
        resps = db.query(ItemResponse).filter(ItemResponse.module_session_id == mod.id).all()
        total_sub = sum(r.sub_item_count for r in resps)
        corr_sub = sum(r.correct_sub_items for r in resps)
        mod.raw_accuracy = round((corr_sub / total_sub) * 100.0, 1) if total_sub > 0 else 0.0

        theta = mod.final_theta if mod.final_theta is not None else 0.0
        se = mod.standard_error if mod.standard_error is not None else 1.0
        app_cfg = get_app_settings_dict(db)
        thresholds = app_cfg.get("cefr_theta_thresholds", settings.CEFR_THETA_THRESHOLDS)
        mod.estimated_cefr = map_theta_to_cefr(theta, thresholds)
        mod.confidence_label = map_se_to_confidence(se, time_limited=time_limited)

    if mod.skill == "reading":
        session.reading_result_id = mod.id
    elif mod.skill == "listening":
        session.listening_result_id = mod.id
    elif mod.skill == "writing":
        session.writing_result_id = mod.id

    # Advance to next module in module_order or complete the session
    order = session.module_order or [mod.skill]
    try:
        idx = order.index(mod.skill)
    except ValueError:
        idx = len(order) - 1

    if idx + 1 < len(order):
        next_skill = order[idx + 1]
        session.current_module = next_skill
        _create_module_session_for_skill(db, session, next_skill)
    else:
        session.current_module = None
        session.status = "COMPLETED"
        session.ended_at = utcnow()

        # Calculate overall CEFR level across completed modules
        all_mods = db.query(ModuleSession).filter(ModuleSession.test_session_id == session.id).all()
        by_skill = {m.skill: m.estimated_cefr for m in all_mods if m.estimated_cefr}
        session.overall_level = calculate_overall_cefr(
            by_skill.get("reading"),
            by_skill.get("listening"),
            by_skill.get("writing"),
        )


def build_session_result_report(db: Session, session_id: str) -> Dict[str, Any]:
    """
    Constructs the comprehensive Result & Diagnostics payload (PRD Section 17 & 18).
    """
    session = db.query(TestSession).filter(TestSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    modules = (
        db.query(ModuleSession)
        .filter(ModuleSession.test_session_id == session.id)
        .order_by(ModuleSession.started_at.asc())
        .all()
    )

    task_labels = {**READING_TASK_TYPES, **LISTENING_TASK_TYPES}
    module_reports: Dict[str, Any] = {}
    can_do_combined: List[str] = []

    for mod in modules:
        if mod.skill in ("reading", "listening"):
            resps = (
                db.query(ItemResponse)
                .filter(ItemResponse.module_session_id == mod.id)
                .order_by(ItemResponse.item_position.asc())
                .all()
            )
            q_ids = [r.question_id for r in resps if r.question_id]
            q_map = {
                q.id: q
                for q in db.query(QuestionItem).filter(QuestionItem.id.in_(q_ids)).all()
            } if q_ids else {}

            task_stats: Dict[str, Dict[str, int]] = {}
            review_items = []
            theta_trajectory = []

            for r in resps:
                q = q_map.get(r.question_id)
                t_type = q.task_type if q else "Unknown"
                if t_type not in task_stats:
                    task_stats[t_type] = {"total": 0, "correct": 0}
                task_stats[t_type]["total"] += r.sub_item_count
                task_stats[t_type]["correct"] += r.correct_sub_items

                score_detail = score_question_response(t_type, q.content_json if q else {}, r.answer_json or {}) if q else {}
                theta_trajectory.append({
                    "step": r.item_position,
                    "pre_theta": r.pre_theta,
                    "post_theta": r.post_theta,
                    "post_se": r.post_se,
                    "task_type": t_type,
                })
                review_items.append({
                    "position": r.item_position,
                    "question_id": r.question_id,
                    "task_type": t_type,
                    "task_type_label": task_labels.get(t_type, t_type),
                    "cefr_target": q.cefr_target if q else "B1",
                    "difficulty_theta": q.difficulty_theta if q else 0.0,
                    "title": (q.content_json or {}).get("title") or (q.content_json or {}).get("stem", "Task Item"),
                    "is_correct": r.is_correct,
                    "sub_item_count": r.sub_item_count,
                    "correct_sub_items": r.correct_sub_items,
                    "user_answer": r.answer_json,
                    "correct_answer_summary": score_detail.get("correct_answer_summary", {}),
                    "sub_details": score_detail.get("details", []),
                    "explanation": q.explanation if q else "",
                    "transcript": (q.content_json or {}).get("transcript") if (q and q.skill == "listening") else None,
                    "pre_theta": r.pre_theta,
                    "post_theta": r.post_theta,
                })

            task_performance = []
            for t_code, st in task_stats.items():
                ratio = st["correct"] / max(1, st["total"])
                rating = "Strong" if ratio >= 0.75 else ("Good" if ratio >= 0.50 else "Developing")
                task_performance.append({
                    "task_type": t_code,
                    "label": task_labels.get(t_code, t_code),
                    "correct_units": st["correct"],
                    "total_units": st["total"],
                    "accuracy_percent": round(ratio * 100, 1),
                    "rating": rating,
                })

            est_lvl = mod.estimated_cefr or "B1"
            can_do_combined.extend(get_can_do_statements(mod.skill, est_lvl))

            module_reports[mod.skill] = {
                "module_session_id": mod.id,
                "skill": mod.skill,
                "status": mod.status,
                "estimated_cefr": est_lvl,
                "accuracy_percent": mod.raw_accuracy if mod.raw_accuracy is not None else 0.0,
                "confidence_label": mod.confidence_label or "Moderate confidence",
                "final_theta": mod.final_theta,
                "standard_error": mod.standard_error,
                "elapsed_seconds": mod.elapsed_seconds,
                "task_performance": task_performance,
                "theta_trajectory": theta_trajectory,
                "item_review": review_items,
            }

        elif mod.skill == "writing":
            subs = (
                db.query(WritingSubmission)
                .filter(WritingSubmission.module_session_id == mod.id)
                .order_by(WritingSubmission.part_number.asc())
                .all()
            )
            parts_review = []
            comm_scores = []
            org_scores = []
            lang_scores = []

            for sub in subs:
                prompt_obj = db.query(WritingPrompt).filter(WritingPrompt.id == sub.writing_prompt_id).first()
                ev = (
                    db.query(WritingEvaluation)
                    .filter(WritingEvaluation.submission_id == sub.id)
                    .order_by(WritingEvaluation.created_at.desc())
                    .first()
                )
                if ev and ev.status == "COMPLETED":
                    if ev.communicative_achievement is not None:
                        comm_scores.append(ev.communicative_achievement)
                    if ev.organisation is not None:
                        org_scores.append(ev.organisation)
                    if ev.language is not None:
                        lang_scores.append(ev.language)

                parts_review.append({
                    "submission_id": sub.id,
                    "part_number": sub.part_number,
                    "word_count": sub.word_count,
                    "minimum_words": prompt_obj.minimum_words if prompt_obj else (50 if sub.part_number == 1 else 180),
                    "prompt": {
                        "text_type": prompt_obj.text_type if prompt_obj else "email",
                        "audience": prompt_obj.audience if prompt_obj else "",
                        "scenario": prompt_obj.scenario if prompt_obj else "",
                        "prompt_text": prompt_obj.prompt_text if prompt_obj else "",
                        "bullet_points": prompt_obj.bullet_points if prompt_obj else [],
                    },
                    "response_text": sub.response_text,
                    "evaluation": {
                        "status": ev.status if ev else "PENDING_RETRY",
                        "provider": ev.provider if ev else "none",
                        "model": ev.model if ev else "none",
                        "communicative_achievement": ev.communicative_achievement if ev else None,
                        "organisation": ev.organisation if ev else None,
                        "language": ev.language if ev else None,
                        "estimated_cefr": ev.estimated_cefr if ev else None,
                        "confidence": ev.confidence if ev else None,
                        "feedback": ev.feedback_json if ev else {},
                    },
                })

            if mod.estimated_cefr:
                can_do_combined.extend(get_can_do_statements("writing", mod.estimated_cefr))

            module_reports["writing"] = {
                "module_session_id": mod.id,
                "skill": "writing",
                "status": mod.status,
                "estimated_cefr": mod.estimated_cefr,
                "confidence_label": mod.confidence_label or "Moderate confidence",
                "elapsed_seconds": mod.elapsed_seconds,
                "rubric_averages": {
                    "communicative_achievement": round(sum(comm_scores) / len(comm_scores), 1) if comm_scores else None,
                    "organisation": round(sum(org_scores) / len(org_scores), 1) if org_scores else None,
                    "language": round(sum(lang_scores) / len(lang_scores), 1) if lang_scores else None,
                },
                "parts": parts_review,
            }

    return {
        "session_id": session.id,
        "mode": session.mode,
        "status": session.status,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "overall_level": session.overall_level,
        "skill_levels": {
            "reading": module_reports.get("reading", {}).get("estimated_cefr"),
            "listening": module_reports.get("listening", {}).get("estimated_cefr"),
            "writing": module_reports.get("writing", {}).get("estimated_cefr"),
        },
        "modules": module_reports,
        "can_do_statements": can_do_combined[:6],
        "disclaimer": "IMPORTANT: This is a simulator estimate based on original practice tasks and the simulator's own 1PL IRT / AI assessment model. It is not an official Cambridge result or Cambridge English Scale score.",
    }
