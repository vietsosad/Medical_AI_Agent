"""Multi-provider LLM Factory & Auto-Fallback Service (Gemini + OpenAI + Mock Simulation).

Tuân thủ nghiêm ngặt chuẩn backend-rules.md:
- Đảm bảo độ ổn định cao nhất cho hệ thống: Ưu tiên dùng Gemini Generative AI.
- Nếu gặp lỗi Timeout/Quota hoặc chưa cài đặt API key trong dev, tự động kích hoạt
  chế độ Mock Simulated Clinical AI để bảo đảm Frontend luôn vận hành mượt mà khi demo.
"""

from functools import lru_cache
from typing import Any

from langchain_core.messages import BaseMessage

from src.config import get_settings


class MockClinicalAI:
    """Non-clinical dev fallback; it must never fabricate ESI or citations."""
    
    async def ainvoke(self, prompt_or_messages: str | list[BaseMessage] | dict[str, Any]) -> Any:
        response_text = (
            "Môi trường hiện tại chưa có mô hình lâm sàng khả dụng. Hệ thống sẽ không tạo "
            "dự đoán ESI và cần chuyển sang nhân viên y tế khi cần đánh giá."
        )

        # Trả về đối tượng giả định có phương thức content tương tự AIMessage
        return type("MockAIMessage", (), {"content": response_text, "response_metadata": {"model": "mock-clinical-simulator-v1"}})


@lru_cache(maxsize=2)
def get_resilient_llm(tier: str = "large") -> Any:
    """Trả về mô hình LLM chính hoặc bộ Fallback Simulator an toàn cho Dev.
    
    Args:
        tier (str): "small" cho Slot-filling/Router (Flash/Mini), "large" cho Evaluation (Pro/4o).
    """
    settings = get_settings()
    
    # Ưu tiên 1: Thử nạp OpenAI (Theo API key của user)
    if settings.openai_api_key and settings.openai_api_key.strip() != "":
        try:
            from langchain_openai import ChatOpenAI
            # Dùng gpt-4o-mini cho task nhỏ (nhanh, rẻ), và gpt-4o cho task phức tạp (thông minh)
            model_name = settings.model_name.strip() or "gpt-4o-mini"
            return ChatOpenAI(
                model=model_name,
                api_key=settings.openai_api_key,
                temperature=settings.llm_temperature,
                timeout=settings.llm_request_timeout_seconds,
                max_retries=settings.llm_max_retries,
            )
        except Exception as e:
            print(f"⚠️ [LLM Provider] Không thể kết nối OpenAI API ({e}). Đang fallback...")

    # Ưu tiên 2: Sử dụng Gemini Generative AI
    if settings.google_api_key and settings.google_api_key.strip() != "":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            # Both retired models 404 against a current key, so the documented
            # fallback chain silently ended at the mock simulator.
            model_name = "gemini-2.5-flash"
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=settings.google_api_key,
                temperature=settings.llm_temperature,
            )
        except Exception as e:
            print(f"⚠️ [LLM Provider] Không thể kết nối Gemini API ({e}). Đang fallback...")

    # Ưu tiên 3: Sử dụng Groq (nhanh, tương thích OpenAI)
    if settings.groq_api_key and settings.groq_api_key.strip() != "":
        try:
            from langchain_openai import ChatOpenAI
            model_name = "openai/gpt-oss-120b"
            return ChatOpenAI(
                model=model_name,
                api_key=settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
                temperature=settings.llm_temperature,
                timeout=settings.llm_request_timeout_seconds,
                max_retries=settings.llm_max_retries,
            )
        except Exception as e:
            print(f"⚠️ [LLM Provider] Không thể kết nối Groq API ({e}). Đang fallback...")

    # Nếu không cấu hình API keys hoặc ở dev, dùng Mock Clinical Simulator
    print(f"ℹ️ [LLM Provider] Không tìm thấy API Key khả dụng. Kích hoạt 'Mock Clinical AI Simulator' ({tier}) phục vụ Dev/Demo!")
    return MockClinicalAI()


@lru_cache(maxsize=1)
def get_deepagent_llm() -> Any:
    """Return an explicit tool-calling model for the DeepAgent supervisor."""
    settings = get_settings()
    model_name = settings.deepagent_model_name.strip() or settings.model_name

    if settings.openai_api_key.strip():
        try:
            from langchain_openai import ChatOpenAI

            gpt_model = model_name if settings.deepagent_model_name else "gpt-4o"
            return ChatOpenAI(
                model=gpt_model,
                api_key=settings.openai_api_key,
                temperature=0.0,
                timeout=settings.deepagent_request_timeout_seconds,
                max_retries=settings.llm_max_retries,
            )
        except Exception as exc:
            print(f"[DeepAgent LLM] OpenAI unavailable: {exc}")

    if settings.google_api_key.strip():
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            gemini_model = model_name if settings.deepagent_model_name else "gemini-2.5-flash"
            return ChatGoogleGenerativeAI(
                model=gemini_model,
                google_api_key=settings.google_api_key,
                temperature=0.0,
            )
        except Exception as exc:
            print(f"[DeepAgent LLM] Gemini unavailable: {exc}")

    if settings.groq_api_key.strip():
        try:
            from langchain_openai import ChatOpenAI

            groq_model = model_name if settings.deepagent_model_name else "openai/gpt-oss-120b"
            return ChatOpenAI(
                model=groq_model,
                api_key=settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
                temperature=0.0,
                timeout=settings.deepagent_request_timeout_seconds,
                max_retries=settings.llm_max_retries,
            )
        except Exception as exc:
            print(f"[DeepAgent LLM] Groq unavailable: {exc}")


    return MockClinicalAI()
