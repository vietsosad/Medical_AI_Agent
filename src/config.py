from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# A deployment may reduce the refinement budget, but cannot turn one patient
# turn into an open-ended retrieval loop.  This hard ceiling is intentionally
# code-owned rather than environment-owned.
RAG_REFINEMENT_ATTEMPTS_HARD_MAX = 3


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "AI20K Agent"
    app_env: Literal["development", "production", "test"] = "development"
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_host: str = "0.0.0.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: str = "http://localhost:3000"

    # LLM
    openai_api_key: str = ""
    groq_api_key: str = ""
    model_name: str = "gpt-4o-mini"
    google_api_key: str = ""
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    # A bounded structured router for utterances the deterministic pass could
    # not place. It runs *after* every safety decision, is capped by
    # ``llm_request_timeout_seconds``, and returns nothing on error or low
    # confidence -- so it can only turn "I did not understand you" into a
    # usable route, never delay or override the safety path.
    intent_llm_fallback_enabled: bool = True
    llm_request_timeout_seconds: float = Field(default=8.0, ge=1.0, le=60.0)
    # How many times a transient provider fault (429, 5xx, socket timeout) is
    # retried before the call is treated as an outage. Zero meant a single slow
    # response degraded the whole clinical turn to the deterministic fallback;
    # the live audit saw that happen on rate-limited and slow calls alike.
    llm_max_retries: int = Field(default=2, ge=0, le=5)
    deepagent_runtime_enabled: bool = True
    # Parallel pilot runtime (src/agents/simple_agent_runtime/), reachable only
    # via the additive src/api/routes_simple_triage.py routes. Off by default so
    # enabling it is an explicit local/opt-in choice, never a silent switch of
    # the live /triage/* traffic already served by deepagent_runtime above.
    simple_agent_enabled: bool = False
    # The orchestration model runs unbounded by any outer asyncio timeout and
    # sends the accumulated tool transcript each step, so it legitimately takes
    # longer than a single clinical node call. Kept separate so raising it
    # cannot lengthen how long a patient waits for a safety decision.
    deepagent_request_timeout_seconds: float = Field(default=45.0, ge=5.0, le=180.0)
    deepagent_model_name: str = ""
    # Groq rotates its catalogue and retires model ids; keep these in settings so a
    # decommissioned name is an env change, not a code change.
    deepagent_max_tool_calls_per_turn: int = Field(default=12, ge=5, le=40)
    deepagent_require_tool_gates: bool = True
    semantic_emergency_confidence_threshold: float = Field(
        default=0.80,
        ge=0.50,
        le=1.0,
    )

    # Offline protocol-corpus builder. These settings are intentionally
    # separate from the patient-facing LLM so a data build cannot silently
    # change runtime clinical behavior.
    protocol_openai_extraction_model: str = "gpt-4o-mini"
    protocol_openai_verification_model: str = "gpt-5-mini"
    protocol_openai_pages_per_request: int = Field(default=3, ge=1, le=10)
    protocol_openai_extraction_max_output_tokens: int = Field(
        default=16_000,
        ge=1_000,
        le=16_384,
    )
    protocol_openai_verification_max_output_tokens: int = Field(
        default=8_000,
        ge=1_000,
        le=32_000,
    )
    protocol_openai_request_timeout_seconds: float = Field(
        default=60.0,
        ge=5.0,
        le=300.0,
    )
    protocol_openai_max_retries: int = Field(default=2, ge=0, le=5)

    # LLM-as-Judge evaluation. This is intentionally separate from the
    # patient-facing runtime model so benchmark settings cannot silently alter
    # clinical behaviour.
    llm_judge_provider: Literal["openai"] = "openai"
    llm_judge_model: str = "gpt-5-mini"
    llm_judge_temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    llm_judge_max_retries: int = Field(default=2, ge=0, le=5)
    llm_judge_max_output_tokens: int = Field(default=2000, ge=256, le=8000)

    # Database & Storage
    database_url: str = "sqlite+aiosqlite:///./data/app.db"
    sync_database_url: str = ""

    # Security & Auth (UI Group 1: Identity & Auth)
    jwt_secret_key: str = "super-secret-default-jwt-key-change-in-prod"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=1440, ge=1)   # 1 day default
    refresh_token_expire_minutes: int = Field(default=10080, ge=1) # 7 days default

    # OAuth 2.0 Providers (Google & GitHub)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:3000/auth/callback/google"
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:3000/auth/callback/github"

    # Email & SMTP Service (OTP Verification & Password Recovery)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply-aitriage@hospital.vn"
    smtp_from_name: str = "Hệ thống AI Triage Cấp cứu"

    # ---- Adaptive conversation ----
    # The agent decides when it has enough; these only bound the loop so a
    # planning bug cannot turn one triage into an interrogation.
    adaptive_questioning_enabled: bool = True
    adaptive_max_consecutive_questions: int = Field(default=8, ge=1, le=20)
    # How many questions may be put in one message. One is the norm; a small
    # group is allowed when the answers are naturally given together.
    adaptive_max_questions_per_turn: int = Field(default=1, ge=1, le=3)
    # How many extra facts the evidence-grounded reasoner may ask for *after*
    # the patient has confirmed the intake summary. Without a budget it walked
    # its whole 32-target menu one question at a time and never concluded: the
    # live audit saw severity, associated symptoms, vitals, chest pain, blood
    # pressure, dyspnoea, temperature, SpO2 and nausea asked in sequence, all
    # after the agent had already judged the case sufficiently characterised.
    # SUFFICIENT is not COMPLETE.
    evidence_question_budget: int = Field(default=3, ge=0, le=8)

    # ---- Retrieval strategy ----
    # Each is independently switchable so a benchmark can attribute a change to
    # the layer that caused it rather than to "the new retrieval".
    retrieval_english_normalization_enabled: bool = True
    retrieval_multi_query_enabled: bool = True
    retrieval_hybrid_enabled: bool = True
    retrieval_rerank_enabled: bool = True
    retrieval_candidate_pool_size: int = Field(default=30, ge=5, le=200)
    # Reciprocal-rank-fusion damping. 60 is the value the RRF paper uses.
    retrieval_rrf_k: int = Field(default=60, ge=1, le=1000)
    # Below this reranked relevance, a similar case is withheld rather than
    # shown. Calibrated against eval/retrieval_ledger.json: the sweep in
    # eval/results/retrieval_metrics.json shows 0.30 is the knee -- it drops
    # clearly-unrelated candidates while keeping 100% of the judged-relevant
    # ones, and every higher floor costs relevant cases without reducing the
    # irrelevant share. The score is a good ranker and a weak classifier, so
    # `case_support_max_shown` does most of the work of keeping the list clean.
    case_support_min_relevance: float = Field(default=0.30, ge=0.0, le=1.0)
    case_support_max_shown: int = Field(default=3, ge=0, le=10)

    # ---- Vector Store ----
    rag_retrieval_top_k: int = Field(default=5, ge=1, le=50)
    rag_max_refinement_attempts: int = Field(
        default=2,
        ge=0,
        le=RAG_REFINEMENT_ATTEMPTS_HARD_MAX,
    )
    rag_protocol_retrieval_enabled: bool = True

    # ---- Cơ sở y tế gần người bệnh (Nearby facilities) ----
    # Tính năng phụ trợ cho người bệnh sau khi có mức ESI khẩn (1/2/3): bật
    # định vị -> danh sách cơ sở y tế gần nhất -> deep link Google Maps chỉ
    # đường. Lớp này KHÔNG sinh ra bất kỳ kết luận lâm sàng nào và không đọc
    # ghi state của agent; nó chỉ tra cứu dữ liệu hành chính bên thứ ba.
    #
    # Khoá Google nằm ở backend, không bao giờ là biến NEXT_PUBLIC_*: mọi biến
    # NEXT_PUBLIC_* đều bị nhúng thẳng vào bundle trình duyệt.
    google_maps_api_key: str = ""
    # "auto" = dùng Google khi có khoá, tự rơi về dữ liệu nội bộ khi thiếu khoá
    # hoặc khi Google lỗi/timeout. "local" ép dùng dữ liệu nội bộ (chạy offline,
    # không phát sinh chi phí). "google" ép dùng Google nhưng VẪN rơi về dữ liệu
    # nội bộ khi gọi hỏng -- không có chế độ nào để tính năng này trả về rỗng
    # trong khi vẫn còn dữ liệu dùng được.
    facility_provider: Literal["auto", "google", "local"] = "auto"
    # Trần 50km là giới hạn cứng của Google Places Nearby Search.
    facility_search_radius_meters: int = Field(default=10_000, ge=500, le=50_000)
    facility_max_results: int = Field(default=8, ge=1, le=20)
    # Cache ngắn hạn trong tiến trình, chặn việc bấm lại liên tục đốt quota.
    # Giữ ở mức phút, không phải ngày: điều khoản Google Maps Platform không cho
    # lưu nội dung Places quá 30 ngày, và dữ liệu này cũng không được ghi xuống
    # CSDL của hệ thống.
    facility_cache_ttl_seconds: int = Field(default=300, ge=0, le=1800)
    facility_provider_timeout_seconds: float = Field(default=5.0, ge=1.0, le=20.0)
    # Chặn lạm dụng quota theo từng tài khoản. Trần đủ rộng để một người bệnh
    # đang hoảng có bấm lại nhiều lần vẫn không bị khoá.
    facility_lookups_per_user: int = Field(default=20, ge=1, le=200)
    facility_rate_limit_window_seconds: int = Field(default=300, ge=10, le=3600)


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_rag_refinement_attempt_limit() -> int:
    """Return the configured budget, defensively clamped to the code hard cap."""
    configured = int(get_settings().rag_max_refinement_attempts)
    return max(0, min(configured, RAG_REFINEMENT_ATTEMPTS_HARD_MAX))
