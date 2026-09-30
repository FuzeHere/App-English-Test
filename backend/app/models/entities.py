import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


def gen_uuid():
    return str(uuid.uuid4())


class QuestionItem(Base):
    __tablename__ = "question_items"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    skill = Column(String(20), nullable=False, index=True)  # 'reading' | 'listening'
    task_type = Column(String(20), nullable=False, index=True)  # RT-01..RT-09, LT-01..LT-03
    cefr_target = Column(String(5), nullable=False, index=True)  # A1, A2, B1, B2, C1
    difficulty_theta = Column(Float, nullable=False, default=0.0)
    status = Column(String(20), nullable=False, default="REVIEW", index=True)  # DRAFT, REVIEW, APPROVED, REJECTED, ARCHIVED
    version = Column(Integer, nullable=False, default=1)
    content_hash = Column(String(64), nullable=False, index=True)
    primary_topic = Column(String(80), nullable=False, default="general")
    scenario = Column(String(120), nullable=False, default="everyday life")
    cognitive_focus = Column(JSON, nullable=False, default=list)
    content_json = Column(JSON, nullable=False, default=dict)
    explanation = Column(Text, nullable=False, default="")
    usage_count = Column(Integer, nullable=False, default=0)
    validation_report = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    options = relationship("QuestionOption", back_populates="question", cascade="all, delete-orphan")
    audio_assets = relationship("AudioAsset", back_populates="question", cascade="all, delete-orphan")


class QuestionOption(Base):
    __tablename__ = "question_options"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    question_id = Column(String(36), ForeignKey("question_items.id", ondelete="CASCADE"), nullable=False, index=True)
    label = Column(String(10), nullable=False)
    text = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False, default=False)
    position = Column(Integer, nullable=False, default=0)

    question = relationship("QuestionItem", back_populates="options")


class AudioAsset(Base):
    __tablename__ = "audio_assets"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    question_id = Column(String(36), ForeignKey("question_items.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(Text, nullable=False)
    duration_seconds = Column(Float, nullable=False, default=30.0)
    format = Column(String(10), nullable=False, default="wav")
    voice = Column(String(50), nullable=False, default="en_voice_01")
    tts_provider = Column(String(30), nullable=False, default="local")
    script_hash = Column(String(64), nullable=False, default="")
    status = Column(String(20), nullable=False, default="READY")
    created_at = Column(DateTime(timezone=True), default=utcnow)

    question = relationship("QuestionItem", back_populates="audio_assets")


class WritingPrompt(Base):
    __tablename__ = "writing_prompts"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    task_part = Column(Integer, nullable=False, index=True)  # 1 or 2
    cefr_target = Column(String(5), nullable=False, index=True)  # A1..C1
    text_type = Column(String(50), nullable=False, default="email")  # email, article, review, web_post
    audience = Column(String(120), nullable=False, default="friend")
    scenario = Column(Text, nullable=False)
    prompt_text = Column(Text, nullable=False)
    bullet_points = Column(JSON, nullable=False, default=list)
    minimum_words = Column(Integer, nullable=False, default=50)
    recommended_minutes = Column(Integer, nullable=False, default=15)
    status = Column(String(20), nullable=False, default="APPROVED", index=True)  # REVIEW, APPROVED, REJECTED
    version = Column(Integer, nullable=False, default=1)
    validation_report = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class TestSession(Base):
    __tablename__ = "test_sessions"
    __test__ = False

    id = Column(String(36), primary_key=True, default=gen_uuid)
    mode = Column(String(25), nullable=False, index=True)  # PRACTICE | FULL_SIMULATION
    status = Column(String(25), nullable=False, default="IN_PROGRESS", index=True)  # IN_PROGRESS, COMPLETED, ABANDONED, TIMEOUT
    started_at = Column(DateTime(timezone=True), default=utcnow)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    current_module = Column(String(20), nullable=True)  # reading | listening | writing
    module_order = Column(JSON, nullable=False, default=list)  # e.g. ["reading", "listening", "writing"]
    reading_result_id = Column(String(36), nullable=True)
    listening_result_id = Column(String(36), nullable=True)
    writing_result_id = Column(String(36), nullable=True)
    overall_level = Column(String(10), nullable=True)
    locked_ai_provider = Column(String(30), nullable=True)
    settings_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    modules = relationship("ModuleSession", back_populates="test_session", cascade="all, delete-orphan")


class ModuleSession(Base):
    __tablename__ = "module_sessions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    test_session_id = Column(String(36), ForeignKey("test_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    skill = Column(String(20), nullable=False, index=True)  # reading | listening | writing
    status = Column(String(25), nullable=False, default="IN_PROGRESS")  # IN_PROGRESS | COMPLETED | TIMEOUT
    started_at = Column(DateTime(timezone=True), default=utcnow)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    time_limit_seconds = Column(Integer, nullable=True)  # None if relaxed practice
    elapsed_seconds = Column(Integer, nullable=False, default=0)
    final_theta = Column(Float, nullable=True)
    standard_error = Column(Float, nullable=True)
    confidence_label = Column(String(30), nullable=True)
    estimated_cefr = Column(String(10), nullable=True)
    raw_accuracy = Column(Float, nullable=True)
    current_question_id = Column(String(36), nullable=True)
    state_json = Column(JSON, nullable=False, default=dict)

    test_session = relationship("TestSession", back_populates="modules")
    responses = relationship("ItemResponse", back_populates="module_session", cascade="all, delete-orphan")
    writing_submissions = relationship("WritingSubmission", back_populates="module_session", cascade="all, delete-orphan")


class ItemResponse(Base):
    __tablename__ = "responses"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    module_session_id = Column(String(36), ForeignKey("module_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(String(36), ForeignKey("question_items.id", ondelete="SET NULL"), nullable=True)
    writing_prompt_id = Column(String(36), ForeignKey("writing_prompts.id", ondelete="SET NULL"), nullable=True)
    item_position = Column(Integer, nullable=False, default=1)
    sub_item_count = Column(Integer, nullable=False, default=1)
    correct_sub_items = Column(Integer, nullable=False, default=0)
    answer_json = Column(JSON, nullable=False, default=dict)
    is_correct = Column(Boolean, nullable=True)
    response_time_seconds = Column(Integer, nullable=False, default=0)
    pre_theta = Column(Float, nullable=True)
    post_theta = Column(Float, nullable=True)
    post_se = Column(Float, nullable=True)
    content_version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    module_session = relationship("ModuleSession", back_populates="responses")


class WritingSubmission(Base):
    __tablename__ = "writing_submissions"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    module_session_id = Column(String(36), ForeignKey("module_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    writing_prompt_id = Column(String(36), ForeignKey("writing_prompts.id", ondelete="SET NULL"), nullable=True)
    part_number = Column(Integer, nullable=False)  # 1 or 2
    response_text = Column(Text, nullable=False, default="")
    word_count = Column(Integer, nullable=False, default=0)
    submitted_at = Column(DateTime(timezone=True), default=utcnow)

    module_session = relationship("ModuleSession", back_populates="writing_submissions")
    evaluations = relationship("WritingEvaluation", back_populates="submission", cascade="all, delete-orphan")


class WritingEvaluation(Base):
    __tablename__ = "writing_evaluations"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    submission_id = Column(String(36), ForeignKey("writing_submissions.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(30), nullable=False)
    model = Column(String(80), nullable=False)
    evaluation_version = Column(String(20), nullable=False, default="1.0")
    status = Column(String(25), nullable=False, default="COMPLETED")  # COMPLETED | PENDING_RETRY
    communicative_achievement = Column(Float, nullable=True)
    organisation = Column(Float, nullable=True)
    language = Column(Float, nullable=True)
    estimated_cefr = Column(String(10), nullable=True)
    confidence = Column(Float, nullable=True)
    feedback_json = Column(JSON, nullable=False, default=dict)
    raw_provider_response = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    submission = relationship("WritingSubmission", back_populates="evaluations")


class AIProviderLog(Base):
    __tablename__ = "ai_provider_logs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    provider = Column(String(30), nullable=False, index=True)
    model = Column(String(80), nullable=False)
    operation = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)  # SUCCESS | FAILED | RETRY | FALLBACK
    latency_ms = Column(Integer, nullable=False, default=0)
    retry_count = Column(Integer, nullable=False, default=0)
    error_code = Column(String(80), nullable=True)
    usage_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key = Column(String(64), primary_key=True)
    value_json = Column(JSON, nullable=False, default=dict)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
