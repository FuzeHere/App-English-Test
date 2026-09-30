from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
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
    AIProviderLog,
)
from app.services.providers.ai_provider import ProviderOrchestrator
from app.services.question_generation.studio_service import (
    get_bank_health_summary,
    generate_studio_items,
)
from app.services.question_generation.validator import (
    READING_TASK_TYPES,
    LISTENING_TASK_TYPES,
    validate_question_item,
    compute_content_hash,
)
from app.services.session_orchestrator import (
    get_app_settings_dict,
    start_practice_session,
    start_full_simulation_session,
    get_current_session_state,
    submit_objective_answer,
    submit_writing_module,
    build_session_result_report,
    get_active_module_session,
    _finalize_module_session,
)
from app.services.tts.tts_engine import tts_engine

router = APIRouter(prefix="/api")


# ---------------- Request Schemas ----------------

class PracticeStartRequest(BaseModel):
    skill: str
    timed: bool = False
    target_units: int = 10
    writing_part_mode: str = "full"
    task_type_filter: Optional[str] = None


class SimulationStartRequest(BaseModel):
    included_skills: List[str] = ["reading", "listening", "writing"]


class AnswerSubmitRequest(BaseModel):
    question_id: Optional[str] = None
    answer: Dict[str, Any] = {}
    response_time_seconds: int = 15
    part1_text: Optional[str] = None
    part2_text: Optional[str] = None
    preferred_provider: Optional[str] = None


class ContentGenerateRequest(BaseModel):
    skill: str
    task_type: str
    target_levels: List[str] = ["B1", "B2"]
    quantity: int = 2
    provider: str = "lm_studio"


class ContentUpdateRequest(BaseModel):
    cefr_target: Optional[str] = None
    difficulty_theta: Optional[float] = None
    primary_topic: Optional[str] = None
    scenario: Optional[str] = None
    explanation: Optional[str] = None
    content_json: Optional[Dict[str, Any]] = None


class SettingsUpdateRequest(BaseModel):
    ai_default_provider: Optional[str] = None
    writing_default_provider: Optional[str] = None
    generation_model: Optional[str] = None
    writing_evaluation_model: Optional[str] = None
    lm_studio_base_url: Optional[str] = None
    tts_provider: Optional[str] = None
    tts_voice: Optional[str] = None
    practice_explanations: Optional[bool] = None
    cefr_theta_thresholds: Optional[Dict[str, float]] = None


# ---------------- 27.1 Health ----------------

@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "product": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }


@router.get("/health/database")
def health_database(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        q_count = db.query(QuestionItem).count()
        w_count = db.query(WritingPrompt).count()
        return {"status": "connected", "question_items": q_count, "writing_prompts": w_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.get("/health/ai")
def health_ai(db: Session = Depends(get_db)):
    cfg = get_app_settings_dict(db)
    orchestrator = ProviderOrchestrator(db, app_config=cfg)
    return {
        "active_default_provider": cfg.get("ai_default_provider", settings.AI_DEFAULT_PROVIDER),
        "writing_default_provider": cfg.get("writing_default_provider", settings.WRITING_DEFAULT_PROVIDER),
        "providers": orchestrator.check_all_providers(),
    }


# ---------------- 27.2 Dashboard ----------------

@router.get("/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    completed_modules = (
        db.query(ModuleSession)
        .filter(ModuleSession.status.in_(["COMPLETED", "TIMEOUT"]), ModuleSession.estimated_cefr.isnot(None))
        .order_by(ModuleSession.ended_at.desc())
        .all()
    )

    latest_by_skill: Dict[str, Optional[str]] = {"reading": None, "listening": None, "writing": None}
    latest_confidence: Dict[str, Optional[str]] = {"reading": None, "listening": None, "writing": None}
    for m in completed_modules:
        if m.skill in latest_by_skill and latest_by_skill[m.skill] is None:
            latest_by_skill[m.skill] = m.estimated_cefr
            latest_confidence[m.skill] = m.confidence_label

    latest_full_sim = (
        db.query(TestSession)
        .filter(TestSession.mode == "FULL_SIMULATION", TestSession.status == "COMPLETED")
        .order_by(TestSession.ended_at.desc())
        .first()
    )

    bank_health = get_bank_health_summary(db)
    cfg = get_app_settings_dict(db)

    return {
        "estimated_levels": latest_by_skill,
        "confidence_labels": latest_confidence,
        "latest_overall_simulation_level": latest_full_sim.overall_level if latest_full_sim else None,
        "total_completed_sessions": db.query(TestSession).filter(TestSession.status == "COMPLETED").count(),
        "ai_provider_status": {
            "default_provider": cfg.get("ai_default_provider", settings.AI_DEFAULT_PROVIDER),
            "writing_provider": cfg.get("writing_default_provider", settings.WRITING_DEFAULT_PROVIDER),
            "generation_model": cfg.get("generation_model", settings.LM_STUDIO_MODEL),
        },
        "bank_health": bank_health,
    }


@router.get("/dashboard/recent-sessions")
def dashboard_recent_sessions(db: Session = Depends(get_db)):
    sessions = (
        db.query(TestSession)
        .order_by(TestSession.started_at.desc())
        .limit(8)
        .all()
    )
    return {"sessions": [_serialize_session_summary(db, s) for s in sessions]}


@router.get("/dashboard/focus-areas")
def dashboard_focus_areas(db: Session = Depends(get_db)):
    """
    Computes weak areas based on accumulated response history (PRD Section 8.3).
    """
    focus_items: List[Dict[str, str]] = []

    resps = db.query(ItemResponse).order_by(ItemResponse.created_at.desc()).limit(60).all()
    if resps:
        q_ids = [r.question_id for r in resps if r.question_id]
        q_map = {q.id: q for q in db.query(QuestionItem).filter(QuestionItem.id.in_(q_ids)).all()} if q_ids else {}
        stats: Dict[str, List[float]] = {}
        for r in resps:
            q = q_map.get(r.question_id)
            if q:
                ratio = r.correct_sub_items / max(1, r.sub_item_count)
                stats.setdefault(q.task_type, []).append(ratio)

        task_labels = {**READING_TASK_TYPES, **LISTENING_TASK_TYPES}
        for t_code, vals in stats.items():
            avg_acc = sum(vals) / len(vals)
            if avg_acc < 0.70:
                focus_items.append({
                    "area": task_labels.get(t_code, t_code),
                    "skill": "Reading" if t_code.startswith("RT") else "Listening",
                    "recommendation": f"Accuracy is {int(round(avg_acc * 100))}%. Practice careful lexical/contextual verification on {t_code} tasks.",
                })

    # Always provide actionable study areas if history is still fresh
    defaults = [
        {
            "area": "Grammar & structural control in Open Cloze (RT-01)",
            "skill": "Reading",
            "recommendation": "Pay close attention to prepositions, relative pronouns, and auxiliary verbs in gapped passages.",
        },
        {
            "area": "Listening for implied meaning & speaker attitude (LT-02 / LT-03)",
            "skill": "Listening",
            "recommendation": "Use the pre-listening seconds to highlight contrast words in the stems before Play 1 begins.",
        },
        {
            "area": "Audience register & paragraph cohesion in Part 1 & Part 2",
            "skill": "Writing",
            "recommendation": "Ensure all three bullet points are developed in distinct logical steps with clear linking devices.",
        },
    ]
    for d in defaults:
        if len(focus_items) < 4:
            focus_items.append(d)

    return {"focus_areas": focus_items[:4]}


# ---------------- 27.3 Practice ----------------

@router.post("/practice/start")
def api_practice_start(req: PracticeStartRequest, db: Session = Depends(get_db)):
    return start_practice_session(
        db=db,
        skill=req.skill,
        timed=req.timed,
        target_units=req.target_units,
        writing_part_mode=req.writing_part_mode,
        task_type_filter=req.task_type_filter,
    )


@router.get("/practice/{session_id}/next")
def api_practice_next(session_id: str, db: Session = Depends(get_db)):
    return get_current_session_state(db, session_id)


@router.post("/practice/{session_id}/answer")
def api_practice_answer(session_id: str, req: AnswerSubmitRequest, db: Session = Depends(get_db)):
    session = db.query(TestSession).filter(TestSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.current_module == "writing":
        return submit_writing_module(
            db=db,
            session_id=session_id,
            part1_text=req.part1_text,
            part2_text=req.part2_text,
            preferred_provider=req.preferred_provider,
        )
    if not req.question_id:
        raise HTTPException(status_code=400, detail="question_id is required for Reading/Listening")
    return submit_objective_answer(
        db=db,
        session_id=session_id,
        question_id=req.question_id,
        user_answer=req.answer,
        response_time_seconds=req.response_time_seconds,
    )


@router.post("/practice/{session_id}/finish")
def api_practice_finish(session_id: str, db: Session = Depends(get_db)):
    session = db.query(TestSession).filter(TestSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    mod = get_active_module_session(db, session)
    if mod and mod.status == "IN_PROGRESS":
        _finalize_module_session(db, session, mod, time_limited=False)
        db.commit()
    return {"session_id": session.id, "status": session.status}


# ---------------- 27.4 Full Simulation ----------------

@router.post("/simulations/start")
def api_simulation_start(req: SimulationStartRequest, db: Session = Depends(get_db)):
    return start_full_simulation_session(db=db, included_skills=req.included_skills)


@router.get("/simulations/{session_id}/current")
def api_simulation_current(session_id: str, db: Session = Depends(get_db)):
    return get_current_session_state(db, session_id)


@router.post("/simulations/{session_id}/answer")
def api_simulation_answer(session_id: str, req: AnswerSubmitRequest, db: Session = Depends(get_db)):
    session = db.query(TestSession).filter(TestSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.current_module == "writing":
        return submit_writing_module(
            db=db,
            session_id=session_id,
            part1_text=req.part1_text,
            part2_text=req.part2_text,
            preferred_provider=req.preferred_provider,
        )
    if not req.question_id:
        raise HTTPException(status_code=400, detail="question_id is required")
    return submit_objective_answer(
        db=db,
        session_id=session_id,
        question_id=req.question_id,
        user_answer=req.answer,
        response_time_seconds=req.response_time_seconds,
    )


@router.post("/simulations/{session_id}/module/finish")
def api_simulation_module_finish(session_id: str, db: Session = Depends(get_db)):
    session = db.query(TestSession).filter(TestSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    mod = get_active_module_session(db, session)
    if mod and mod.status == "IN_PROGRESS":
        _finalize_module_session(db, session, mod, time_limited=False)
        db.commit()
    return get_current_session_state(db, session_id)


@router.post("/simulations/{session_id}/finish")
def api_simulation_finish(session_id: str, db: Session = Depends(get_db)):
    session = db.query(TestSession).filter(TestSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    mod = get_active_module_session(db, session)
    if mod and mod.status == "IN_PROGRESS":
        _finalize_module_session(db, session, mod, time_limited=False)
    session.status = "COMPLETED"
    session.current_module = None
    db.commit()
    return {"session_id": session.id, "status": session.status}


# ---------------- 27.5 Results ----------------

@router.get("/results/{session_id}")
def api_get_results(session_id: str, db: Session = Depends(get_db)):
    return build_session_result_report(db, session_id)


@router.get("/results/{session_id}/details")
def api_get_results_details(session_id: str, db: Session = Depends(get_db)):
    return build_session_result_report(db, session_id)


# ---------------- 27.6 History ----------------

def _serialize_session_summary(db: Session, s: TestSession) -> Dict[str, Any]:
    mods = db.query(ModuleSession).filter(ModuleSession.test_session_id == s.id).all()
    by_skill = {m.skill: m.estimated_cefr for m in mods}
    return {
        "session_id": s.id,
        "mode": s.mode,
        "status": s.status,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "ended_at": s.ended_at.isoformat() if s.ended_at else None,
        "reading": by_skill.get("reading"),
        "listening": by_skill.get("listening"),
        "writing": by_skill.get("writing"),
        "overall": s.overall_level,
        "module_order": s.module_order,
    }


@router.get("/history")
def api_get_history(db: Session = Depends(get_db)):
    sessions = db.query(TestSession).order_by(TestSession.started_at.desc()).all()
    return {"history": [_serialize_session_summary(db, s) for s in sessions]}


@router.get("/history/{session_id}")
def api_get_history_detail(session_id: str, db: Session = Depends(get_db)):
    return build_session_result_report(db, session_id)


@router.delete("/history/{session_id}")
def api_delete_history_item(session_id: str, db: Session = Depends(get_db)):
    session = db.query(TestSession).filter(TestSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return {"deleted": True, "session_id": session_id}


@router.delete("/history")
def api_delete_all_history(db: Session = Depends(get_db)):
    """
    Deletes all session history while preserving the shared Question Bank (PRD Section 19.4 & 43.8).
    """
    db.query(WritingEvaluation).delete()
    db.query(WritingSubmission).delete()
    db.query(ItemResponse).delete()
    db.query(ModuleSession).delete()
    count = db.query(TestSession).delete()
    db.commit()
    return {"deleted_all": True, "deleted_sessions": count}


# ---------------- 27.7 Content Studio ----------------

@router.get("/content/bank-health")
def api_content_bank_health(db: Session = Depends(get_db)):
    return get_bank_health_summary(db)


@router.post("/content/generate")
def api_content_generate(req: ContentGenerateRequest, db: Session = Depends(get_db)):
    items = generate_studio_items(
        db=db,
        skill=req.skill.lower(),
        task_type=req.task_type,
        target_levels=req.target_levels,
        quantity=req.quantity,
        provider_name=req.provider,
    )
    return {"generated_count": len(items), "items": items}


@router.get("/content/review-queue")
def api_content_review_queue(db: Session = Depends(get_db)):
    q_items = (
        db.query(QuestionItem)
        .filter(QuestionItem.status == "REVIEW")
        .order_by(QuestionItem.created_at.desc())
        .all()
    )
    w_items = (
        db.query(WritingPrompt)
        .filter(WritingPrompt.status == "REVIEW")
        .order_by(WritingPrompt.created_at.desc())
        .all()
    )
    return {
        "questions": [_serialize_studio_question(db, q) for q in q_items],
        "writing_prompts": [_serialize_studio_writing(w) for w in w_items],
    }


@router.get("/content/approved")
def api_content_approved(skill: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(QuestionItem).filter(QuestionItem.status == "APPROVED")
    if skill and skill in ("reading", "listening"):
        query = query.filter(QuestionItem.skill == skill)
    q_items = query.order_by(QuestionItem.skill.asc(), QuestionItem.task_type.asc(), QuestionItem.difficulty_theta.asc()).all()
    w_items = db.query(WritingPrompt).filter(WritingPrompt.status == "APPROVED").order_by(WritingPrompt.task_part.asc()).all()
    return {
        "questions": [_serialize_studio_question(db, q) for q in q_items],
        "writing_prompts": [_serialize_studio_writing(w) for w in w_items],
    }


def _serialize_studio_question(db: Session, q: QuestionItem) -> Dict[str, Any]:
    task_labels = {**READING_TASK_TYPES, **LISTENING_TASK_TYPES}
    audio = db.query(AudioAsset).filter(AudioAsset.question_id == q.id).first() if q.skill == "listening" else None
    return {
        "id": q.id,
        "skill": q.skill,
        "task_type": q.task_type,
        "task_type_label": task_labels.get(q.task_type, q.task_type),
        "cefr_target": q.cefr_target,
        "difficulty_theta": q.difficulty_theta,
        "status": q.status,
        "version": q.version,
        "primary_topic": q.primary_topic,
        "scenario": q.scenario,
        "cognitive_focus": q.cognitive_focus,
        "content_json": q.content_json,
        "explanation": q.explanation,
        "usage_count": q.usage_count,
        "validation_report": q.validation_report,
        "audio": {
            "url": audio.file_path,
            "duration_seconds": audio.duration_seconds,
            "voice": audio.voice,
            "status": audio.status,
        } if audio else None,
        "updated_at": q.updated_at.isoformat() if q.updated_at else None,
    }


def _serialize_studio_writing(w: WritingPrompt) -> Dict[str, Any]:
    return {
        "id": w.id,
        "skill": "writing",
        "task_part": w.task_part,
        "task_type": f"WT-0{w.task_part}",
        "cefr_target": w.cefr_target,
        "text_type": w.text_type,
        "audience": w.audience,
        "scenario": w.scenario,
        "prompt_text": w.prompt_text,
        "bullet_points": w.bullet_points,
        "minimum_words": w.minimum_words,
        "recommended_minutes": w.recommended_minutes,
        "status": w.status,
        "version": w.version,
        "validation_report": w.validation_report,
    }


@router.post("/content/{item_id}/approve")
def api_content_approve(item_id: str, db: Session = Depends(get_db)):
    q = db.query(QuestionItem).filter(QuestionItem.id == item_id).first()
    if q:
        v_rep = validate_question_item(
            skill=q.skill,
            task_type=q.task_type,
            cefr_target=q.cefr_target,
            difficulty_theta=q.difficulty_theta,
            content_json=q.content_json or {},
            explanation=q.explanation,
        )
        q.validation_report = v_rep
        if not v_rep["valid"]:
            raise HTTPException(status_code=400, detail=f"Cannot approve invalid item: {v_rep['errors']}")
        q.status = "APPROVED"
        db.commit()
        return {"id": q.id, "status": q.status, "version": q.version}

    w = db.query(WritingPrompt).filter(WritingPrompt.id == item_id).first()
    if w:
        w.status = "APPROVED"
        db.commit()
        return {"id": w.id, "status": w.status, "version": w.version}

    raise HTTPException(status_code=404, detail="Content item not found")


@router.post("/content/{item_id}/reject")
def api_content_reject(item_id: str, db: Session = Depends(get_db)):
    q = db.query(QuestionItem).filter(QuestionItem.id == item_id).first()
    if q:
        q.status = "REJECTED"
        db.commit()
        return {"id": q.id, "status": q.status}

    w = db.query(WritingPrompt).filter(WritingPrompt.id == item_id).first()
    if w:
        w.status = "REJECTED"
        db.commit()
        return {"id": w.id, "status": w.status}

    raise HTTPException(status_code=404, detail="Content item not found")


@router.post("/content/{item_id}/regenerate")
def api_content_regenerate(item_id: str, db: Session = Depends(get_db)):
    q = db.query(QuestionItem).filter(QuestionItem.id == item_id).first()
    if q:
        new_items = generate_studio_items(
            db=db,
            skill=q.skill,
            task_type=q.task_type,
            target_levels=[q.cefr_target],
            quantity=1,
        )
        q.status = "REJECTED"
        db.commit()
        return {"regenerated": True, "new_item": new_items[0] if new_items else None}

    w = db.query(WritingPrompt).filter(WritingPrompt.id == item_id).first()
    if w:
        new_items = generate_studio_items(
            db=db,
            skill="writing",
            task_type=f"WT-0{w.task_part}",
            target_levels=[w.cefr_target],
            quantity=1,
        )
        w.status = "REJECTED"
        db.commit()
        return {"regenerated": True, "new_item": new_items[0] if new_items else None}

    raise HTTPException(status_code=404, detail="Content item not found")


@router.put("/content/{item_id}")
def api_content_update(item_id: str, req: ContentUpdateRequest, db: Session = Depends(get_db)):
    """
    PRD Section 21.3: Editing a question after approval creates a new content_version
    and re-runs validation.
    """
    q = db.query(QuestionItem).filter(QuestionItem.id == item_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question item not found")

    if req.cefr_target is not None:
        q.cefr_target = req.cefr_target
    if req.difficulty_theta is not None:
        q.difficulty_theta = req.difficulty_theta
    if req.primary_topic is not None:
        q.primary_topic = req.primary_topic
    if req.scenario is not None:
        q.scenario = req.scenario
    if req.explanation is not None:
        q.explanation = req.explanation
    if req.content_json is not None:
        q.content_json = req.content_json
        q.content_hash = compute_content_hash(req.content_json)

    q.version = (q.version or 1) + 1
    q.status = "REVIEW"
    q.validation_report = validate_question_item(
        skill=q.skill,
        task_type=q.task_type,
        cefr_target=q.cefr_target,
        difficulty_theta=q.difficulty_theta,
        content_json=q.content_json or {},
        explanation=q.explanation,
    )
    db.commit()
    return _serialize_studio_question(db, q)


# ---------------- 27.8 AI & TTS Settings ----------------

@router.get("/settings/ai")
def api_get_settings_ai(db: Session = Depends(get_db)):
    cfg = get_app_settings_dict(db)
    orchestrator = ProviderOrchestrator(db, app_config=cfg)
    logs = db.query(AIProviderLog).order_by(AIProviderLog.created_at.desc()).limit(10).all()
    return {
        "settings": cfg,
        "providers_status": orchestrator.check_all_providers(),
        "available_voices": tts_engine.AVAILABLE_VOICES,
        "recent_logs": [
            {
                "id": lg.id,
                "provider": lg.provider,
                "model": lg.model,
                "operation": lg.operation,
                "status": lg.status,
                "latency_ms": lg.latency_ms,
                "retry_count": lg.retry_count,
                "created_at": lg.created_at.isoformat() if lg.created_at else None,
            }
            for lg in logs
        ],
    }


@router.put("/settings/ai")
def api_update_settings_ai(req: SettingsUpdateRequest, db: Session = Depends(get_db)):
    row = db.query(AppSetting).filter(AppSetting.key == "global_config").first()
    current = get_app_settings_dict(db)
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    current.update(updates)
    if not row:
        row = AppSetting(key="global_config", value_json=current)
        db.add(row)
    else:
        row.value_json = current
    db.commit()
    return {"updated": True, "settings": current}


@router.post("/settings/ai/health-check")
def api_test_ai_connections(db: Session = Depends(get_db)):
    cfg = get_app_settings_dict(db)
    orchestrator = ProviderOrchestrator(db, app_config=cfg)
    return {"providers_status": orchestrator.check_all_providers()}


@router.get("/settings/ai/{provider}/models")
def api_get_provider_models(provider: str, db: Session = Depends(get_db)):
    cfg = get_app_settings_dict(db)
    orchestrator = ProviderOrchestrator(db, app_config=cfg)
    prov = orchestrator.providers.get(provider)
    if not prov:
        raise HTTPException(status_code=404, detail="Unknown provider")
    return {"provider": provider, "models": prov.list_models()}


@router.post("/tts/preview")
def api_tts_preview(voice: str = "en_voice_01"):
    info = tts_engine.generate_audio_asset(
        question_id=f"preview_{voice}",
        script_text="This is a sample listening voice check for the CEST Practice Simulator.",
        speaker_count=1,
        voice=voice,
    )
    return info


@router.get("/audio/{filename}")
def api_serve_audio(filename: str):
    safe_name = Path(filename).name
    file_path = Path(settings.AUDIO_STORAGE_DIR) / safe_name
    if not file_path.exists():
        # Auto-regenerate fallback audio if missing
        tts_engine.generate_audio_asset(
            question_id="recovered",
            script_text="Audio stream recovered for listening comprehension task.",
            speaker_count=1,
        )
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio asset not found")
    return FileResponse(path=str(file_path), media_type="audio/wav", filename=safe_name)
