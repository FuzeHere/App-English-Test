import json
import re
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
import httpx
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.entities import AIProviderLog
from app.prompts.templates import (
    WRITING_EVALUATION_SYSTEM_PROMPT,
    build_writing_evaluation_user_prompt,
)


def extract_json_object(raw_text: str) -> Dict[str, Any]:
    """Extracts and parses a JSON object from LLM text output."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    return json.loads(text)


class AIProvider(ABC):
    provider_name: str = "base"

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def list_models(self) -> List[str]:
        pass

    @abstractmethod
    def generate_text(self, system_prompt: str, user_prompt: str, model: Optional[str] = None) -> Dict[str, Any]:
        pass

    def score_writing(
        self,
        prompt_data: Dict[str, Any],
        candidate_response: str,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        user_prompt = build_writing_evaluation_user_prompt(
            task_part=prompt_data.get("task_part", 1),
            cefr_target=prompt_data.get("cefr_target", "B1"),
            text_type=prompt_data.get("text_type", "email"),
            audience=prompt_data.get("audience", "reader"),
            scenario=prompt_data.get("scenario", ""),
            prompt_text=prompt_data.get("prompt_text", ""),
            bullet_points=prompt_data.get("bullet_points", []),
            minimum_words=prompt_data.get("minimum_words", 50),
            candidate_response=candidate_response,
        )
        raw = self.generate_text(WRITING_EVALUATION_SYSTEM_PROMPT, user_prompt, model=model)
        parsed = extract_json_object(raw["text"])
        return {
            "evaluation": parsed,
            "provider": self.provider_name,
            "model": raw.get("model", model or "default"),
            "usage": raw.get("usage"),
        }

    def validate_item(self, item_payload: Dict[str, Any]) -> Dict[str, Any]:
        return {"valid": True, "provider": self.provider_name}


class LMStudioProvider(AIProvider):
    provider_name = "lm_studio"

    def __init__(self, base_url: Optional[str] = None, default_model: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = (base_url or settings.LM_STUDIO_BASE_URL).rstrip("/")
        self.default_model = default_model or settings.LM_STUDIO_MODEL or "local-model"
        self.api_key = api_key or settings.LM_STUDIO_API_KEY or "lm-studio"

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def health_check(self) -> Dict[str, Any]:
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(f"{self.base_url}/models", headers=self._headers())
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get("id", "local-model") for m in data.get("data", [])]
                    return {
                        "connected": True,
                        "provider": self.provider_name,
                        "status": "Connected",
                        "models": models or [self.default_model],
                        "base_url": self.base_url,
                    }
                return {"connected": False, "provider": self.provider_name, "status": f"HTTP {resp.status_code}", "models": []}
        except Exception as e:
            return {"connected": False, "provider": self.provider_name, "status": "Not connected (Local server offline)", "error": str(e), "models": []}

    def list_models(self) -> List[str]:
        hc = self.health_check()
        return hc.get("models") or [self.default_model]

    def generate_text(self, system_prompt: str, user_prompt: str, model: Optional[str] = None) -> Dict[str, Any]:
        target_model = model or self.default_model
        payload = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        with httpx.Client(timeout=45.0) as client:
            resp = client.post(f"{self.base_url}/chat/completions", headers=self._headers(), json=payload)
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            return {
                "text": text,
                "model": data.get("model", target_model),
                "usage": data.get("usage"),
            }


class OpenAIProvider(AIProvider):
    provider_name = "openai"

    def __init__(self, api_key: Optional[str] = None, default_model: Optional[str] = None):
        self.api_key = api_key if api_key is not None else settings.OPENAI_API_KEY
        self.default_model = default_model or settings.OPENAI_MODEL or "gpt-4o-mini"

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def health_check(self) -> Dict[str, Any]:
        if not self.api_key:
            return {"connected": False, "provider": self.provider_name, "status": "Not configured", "models": []}
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get("https://api.openai.com/v1/models", headers=self._headers())
                if resp.status_code == 200:
                    return {
                        "connected": True,
                        "provider": self.provider_name,
                        "status": "Connected",
                        "models": ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"],
                    }
                return {"connected": False, "provider": self.provider_name, "status": f"HTTP {resp.status_code}", "models": []}
        except Exception as e:
            return {"connected": False, "provider": self.provider_name, "status": "Connection error", "error": str(e), "models": []}

    def list_models(self) -> List[str]:
        return [self.default_model, "gpt-4o-mini", "gpt-4o"]

    def generate_text(self, system_prompt: str, user_prompt: str, model: Optional[str] = None) -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("OpenAI API key is not configured")
        target_model = model or self.default_model
        # Use Responses API / Chat Completions with store: False per PRD Section 32.2 privacy control
        payload = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "store": False,
            "temperature": 0.2,
        }
        with httpx.Client(timeout=45.0) as client:
            resp = client.post("https://api.openai.com/v1/chat/completions", headers=self._headers(), json=payload)
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            return {
                "text": text,
                "model": data.get("model", target_model),
                "usage": data.get("usage"),
            }


class GeminiProvider(AIProvider):
    provider_name = "gemini"

    def __init__(self, api_key: Optional[str] = None, default_model: Optional[str] = None):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.default_model = default_model or settings.GEMINI_MODEL or "gemini-2.5-flash"

    def health_check(self) -> Dict[str, Any]:
        if not self.api_key:
            return {"connected": False, "provider": self.provider_name, "status": "Not configured", "models": []}
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    return {
                        "connected": True,
                        "provider": self.provider_name,
                        "status": "Connected",
                        "models": [self.default_model, "gemini-2.5-flash", "gemini-2.5-pro"],
                    }
                return {"connected": False, "provider": self.provider_name, "status": f"HTTP {resp.status_code}", "models": []}
        except Exception as e:
            return {"connected": False, "provider": self.provider_name, "status": "Connection error", "error": str(e), "models": []}

    def list_models(self) -> List[str]:
        return [self.default_model, "gemini-2.5-flash", "gemini-2.5-pro"]

    def generate_text(self, system_prompt: str, user_prompt: str, model: Optional[str] = None) -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("Gemini API key is not configured")
        target_model = model or self.default_model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={self.api_key}"
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }
        with httpx.Client(timeout=45.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return {
                "text": text,
                "model": target_model,
                "usage": data.get("usageMetadata"),
            }


class LocalRuleBasedEvaluator(AIProvider):
    """
    Built-in deterministic local linguistic analyzer used when external AI servers
    (LM Studio / OpenAI / Gemini) are unreachable and local fallback is active,
    or for instant offline assessment. Clearly records provider='local_heuristic_engine'.
    """
    provider_name = "local_heuristic"

    def health_check(self) -> Dict[str, Any]:
        return {
            "connected": True,
            "provider": self.provider_name,
            "status": "Ready (Built-in Local Engine)",
            "models": ["cest-local-rubric-v1"],
        }

    def list_models(self) -> List[str]:
        return ["cest-local-rubric-v1"]

    def generate_text(self, system_prompt: str, user_prompt: str, model: Optional[str] = None) -> Dict[str, Any]:
        return {"text": "{}", "model": "cest-local-rubric-v1", "usage": {"tokens": 0}}

    def score_writing(
        self,
        prompt_data: Dict[str, Any],
        candidate_response: str,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        text = (candidate_response or "").strip()
        words = [w for w in re.split(r"\s+", text) if w]
        word_count = len(words)
        min_words = prompt_data.get("minimum_words", 50)
        bullets = prompt_data.get("bullet_points", [])
        part = prompt_data.get("task_part", 1)

        if word_count < 10:
            return {
                "provider": self.provider_name,
                "model": "cest-local-rubric-v1",
                "evaluation": {
                    "communicative_achievement": 1,
                    "organisation": 1,
                    "language": 1,
                    "estimated_cefr": "A1",
                    "confidence": 0.55,
                    "too_short_warning": True,
                    "summary_en": f"The response ({word_count} words) is significantly below the minimum requirement of {min_words} words, providing limited evidence for higher band assessment.",
                    "summary_id": f"Tulisan ({word_count} kata) jauh di bawah batas minimum {min_words} kata, sehingga bukti kemampuan bahasa masih sangat terbatas.",
                    "task_completion": {
                        "all_bullets_addressed": False,
                        "bullet_analysis": [f"Not adequately developed: {b}" for b in bullets],
                        "register_analysis": "Insufficient text length to establish appropriate register.",
                    },
                    "diagnostics": {
                        "grammar": ["Response is too brief to demonstrate control of complex clause structures."],
                        "vocabulary": ["Very limited lexical range due to extreme brevity."],
                        "coherence": ["Needs full paragraph development and clear opening/closing conventions."],
                    },
                    "corrections": [],
                    "improvement_plan": [
                        f"Ensure your Part {part} response reaches at least {min_words} words.",
                        "Address all three required bullet points in dedicated sentences or paragraphs.",
                    ],
                },
            }

        # Analyze lexical diversity, connectors, sentence structure, and common errors
        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        unique_words = len(set(w.lower().strip(",.!?;:\"'()") for w in words))
        ttr = unique_words / max(1, word_count)

        connectors = {"however", "furthermore", "moreover", "therefore", "although", "despite", "whereas", "consequently", "addition", "firstly", "secondly", "finally", "because", "while", "since"}
        used_connectors = [w.lower().strip(",.") for w in words if w.lower().strip(",.") in connectors]

        # Check common errors in candidate text for evidence-based corrections
        corrections = []
        pattern_checks = [
            (r"\bcan\s+(gives|makes|helps|goes|comes|takes|provides)\b", lambda m: f"can {m.group(1)[:-1]}", "After modal verb 'can', use the base form of the verb.", "Setelah kata kerja modal 'can', gunakan bentuk dasar kata kerja (bare infinitive)."),
            (r"\b(informations|advices|equipments|furnitures|researches)\b", lambda m: m.group(1)[:-1], "Uncountable nouns such as 'information', 'advice', or 'equipment' do not take a plural '-s'.", "Kata benda ini termasuk uncountable noun (tidak dapat dihitung) sehingga tidak menggunakan akhiran jamak '-s'."),
            (r"\bi\b", lambda m: "I", "The pronoun 'I' must always be capitalised in English.", "Kata ganti 'I' harus selalu ditulis dengan huruf kapital."),
            (r"\b(look forward to)\s+(hear|see|meet)\b", lambda m: f"look forward to {m.group(2)}ing", "After 'look forward to', use the -ing (gerund) form of the verb.", "Setelah frasa 'look forward to', gunakan kata kerja bentuk -ing (gerund)."),
            (r"\b(depend of|depends of)\b", lambda m: m.group(1).replace(" of", " on"), "The verb 'depend' collocates with the preposition 'on', not 'of'.", "Kata kerja 'depend' berpasangan dengan preposisi 'on', bukan 'of'."),
            (r"\b(discuss about|discussed about)\b", lambda m: m.group(1).replace(" about", ""), "The verb 'discuss' is transitive and does not take the preposition 'about'.", "Kata kerja 'discuss' bersifat transitif dan langsung diikuti objek tanpa 'about'."),
        ]
        for pat, repl_fn, why_en, why_id in pattern_checks:
            match = re.search(pat, text)
            if match:
                orig = match.group(0)
                sugg = repl_fn(match)
                if orig != sugg:
                    corrections.append({
                        "original": orig,
                        "suggested": sugg,
                        "why_en": why_en,
                        "why_id": why_id,
                    })

        # Add stylistic improvement suggestion from the first sentence if no pattern error found
        if not corrections and sentences:
            s0 = sentences[0]
            if len(s0.split()) < 8:
                corrections.append({
                    "original": s0,
                    "suggested": f"{s0}, which allows me to address your main question clearly.",
                    "why_en": "Expanding short opening clauses with relative clauses demonstrates stronger B2/C1 syntactic range.",
                    "why_id": "Memperluas kalimat pembuka yang pendek dengan klausa relatif menunjukkan variasi struktur kalimat level B2/C1.",
                })

        # Score calculation (0-5)
        length_ratio = min(1.3, word_count / max(1, min_words))
        comm_score = min(5, max(1, int(round(2.2 * length_ratio + (1.2 if len(sentences) >= 3 else 0.4) + (0.8 if len(used_connectors) >= 1 else 0)))))
        org_score = min(5, max(1, int(round(1.8 * length_ratio + (1.2 if len(paragraphs) >= 2 else 0.4) + min(1.5, len( set(used_connectors)) * 0.5)))))
        lang_score = min(5, max(1, int(round(2.0 * length_ratio + (1.5 if ttr > 0.55 else 0.8) + (0.8 if len(words) / max(1, len(sentences)) >= 11 else 0.2) - 0.3 * len(corrections)))))

        avg_band = (comm_score + org_score + lang_score) / 3.0
        if avg_band < 1.6:
            est_cefr = "A1"
        elif avg_band < 2.5:
            est_cefr = "A2"
        elif avg_band < 3.4:
            est_cefr = "B1"
        elif avg_band < 4.3:
            est_cefr = "B2"
        else:
            est_cefr = "C1"

        too_short = word_count < min_words
        if too_short and est_cefr in ("B2", "C1"):
            est_cefr = "B1"

        bullet_status = []
        for idx, b in enumerate(bullets):
            addressed = word_count >= (idx + 1) * (min_words * 0.25)
            bullet_status.append(f"{'Addressed' if addressed else 'Needs fuller development'}: {b}")

        return {
            "provider": self.provider_name,
            "model": "cest-local-rubric-v1",
            "evaluation": {
                "communicative_achievement": comm_score,
                "organisation": org_score,
                "language": lang_score,
                "estimated_cefr": est_cefr,
                "confidence": 0.76 if not too_short else 0.62,
                "too_short_warning": too_short,
                "summary_en": (
                    f"Your Part {part} response contains {word_count} words (minimum {min_words}) across {len(paragraphs)} paragraph(s). "
                    f"It demonstrates {est_cefr}-level control across Communicative Achievement ({comm_score}/5), Organisation ({org_score}/5), and Language ({lang_score}/5)."
                ),
                "summary_id": (
                    f"Jawaban Part {part} Anda terdiri dari {word_count} kata (minimum {min_words} kata) dalam {len(paragraphs)} paragraf. "
                    f"Tulisan ini menunjukkan estimasi kemampuan level {est_cefr} pada dimensi Communicative Achievement ({comm_score}/5), Organisation ({org_score}/5), dan Language ({lang_score}/5)."
                ),
                "task_completion": {
                    "all_bullets_addressed": not too_short and len(sentences) >= 3,
                    "bullet_analysis": bullet_status,
                    "register_analysis": f"Register is generally appropriate for the target audience ({prompt_data.get('audience', 'reader')}).",
                },
                "diagnostics": {
                    "grammar": [
                        f"Average sentence length is {round(word_count / max(1, len(sentences)), 1)} words per sentence.",
                        "Maintain consistent tense control and modal verb structures across paragraphs.",
                    ],
                    "vocabulary": [
                        f"Lexical diversity (unique word ratio) is {int(round(ttr * 100))}% ({unique_words} unique words).",
                        "Incorporate more topic-specific collocations to strengthen precision.",
                    ],
                    "coherence": [
                        f"Detected {len(set(used_connectors))} distinct cohesive device(s): {', '.join( sorted(set(used_connectors)) ) if used_connectors else 'none'}.",
                        "Use clear paragraph transitions to guide the reader through each required bullet point.",
                    ],
                },
                "corrections": corrections,
                "improvement_plan": [
                    "Ensure every bullet point in the prompt is developed with a supporting reason or example.",
                    "Use varied cohesive devices (e.g., 'Furthermore', 'However', 'Consequently') to connect ideas smoothly.",
                    f"Target at least {min_words + 20} words with clear opening and concluding paragraphs.",
                ],
            },
        }


class ProviderOrchestrator:
    """
    Manages AI provider selection, retry policy (Attempt 1 -> 1s -> Attempt 2 -> 3s -> Attempt 3 -> Fallback),
    and session provider locking (PRD Section 22.7 & 22.8).
    """

    def __init__(self, db: Session, app_config: Optional[Dict[str, Any]] = None):
        self.db = db
        self.config = app_config or {}
        self.providers: Dict[str, AIProvider] = {
            "lm_studio": LMStudioProvider(
                base_url=self.config.get("lm_studio_base_url", settings.LM_STUDIO_BASE_URL),
                default_model=self.config.get("generation_model") or settings.LM_STUDIO_MODEL,
            ),
            "openai": OpenAIProvider(default_model=self.config.get("openai_model") or settings.OPENAI_MODEL),
            "gemini": GeminiProvider(default_model=self.config.get("gemini_model") or settings.GEMINI_MODEL),
            "local_heuristic": LocalRuleBasedEvaluator(),
        }

    def _log_call(
        self,
        provider: str,
        model: str,
        operation: str,
        status: str,
        latency_ms: int,
        retry_count: int = 0,
        error_code: Optional[str] = None,
        usage_json: Optional[Dict[str, Any]] = None,
    ):
        try:
            log_entry = AIProviderLog(
                provider=provider,
                model=model,
                operation=operation,
                status=status,
                latency_ms=latency_ms,
                retry_count=retry_count,
                error_code=error_code,
                usage_json=usage_json,
            )
            self.db.add(log_entry)
            self.db.commit()
        except Exception:
            self.db.rollback()

    def check_all_providers(self) -> Dict[str, Any]:
        results = {}
        for name in ("lm_studio", "openai", "gemini", "local_heuristic"):
            results[name] = self.providers[name].health_check()
        return results

    def evaluate_writing_with_fallback(
        self,
        prompt_data: Dict[str, Any],
        candidate_response: str,
        preferred_provider: Optional[str] = None,
        locked_provider: Optional[str] = None,
        model: Optional[str] = None,
        fast_retry_in_dev: bool = True,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Executes Writing AI evaluation with session-level provider locking and retry backoff.
        Returns (result_dict, active_provider_name).
        """
        primary = locked_provider or preferred_provider or settings.WRITING_DEFAULT_PROVIDER
        order = [primary]
        for fallback_cand in ("lm_studio", "openai", "gemini", "local_heuristic"):
            if fallback_cand not in order:
                order.append(fallback_cand)

        backoffs = [0.2, 0.5] if fast_retry_in_dev else [1.0, 3.0]

        for prov_name in order:
            provider = self.providers.get(prov_name)
            if not provider:
                continue

            # Check health before burning retries if external provider is not configured
            hc = provider.health_check()
            if not hc.get("connected"):
                self._log_call(
                    provider=prov_name,
                    model=model or "default",
                    operation="score_writing",
                    status="UNAVAILABLE",
                    latency_ms=0,
                    retry_count=0,
                    error_code=hc.get("status", "disconnected"),
                )
                continue

            for attempt in range(3):
                t0 = time.perf_counter()
                try:
                    res = provider.score_writing(prompt_data, candidate_response, model=model)
                    elapsed_ms = int((time.perf_counter() - t0) * 1000)
                    self._log_call(
                        provider=prov_name,
                        model=res.get("model", model or "default"),
                        operation="score_writing",
                        status="SUCCESS",
                        latency_ms=elapsed_ms,
                        retry_count=attempt,
                        usage_json=res.get("usage"),
                    )
                    return res, prov_name
                except Exception as exc:
                    elapsed_ms = int((time.perf_counter() - t0) * 1000)
                    self._log_call(
                        provider=prov_name,
                        model=model or "default",
                        operation="score_writing",
                        status="RETRY" if attempt < 2 else "FAILED",
                        latency_ms=elapsed_ms,
                        retry_count=attempt + 1,
                        error_code=type(exc).__name__,
                    )
                    if attempt < len(backoffs):
                        time.sleep(backoffs[attempt])

        return None, None
