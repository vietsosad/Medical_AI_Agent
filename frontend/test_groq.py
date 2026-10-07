import os

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


class TestSchema(BaseModel):
    answer: str = Field(description="the answer")


groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise RuntimeError("Set GROQ_API_KEY before running this smoke test.")

for model_name in [
    "llama3-8b-8192",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
    "mixtral-8x7b-32768",
]:
    try:
        llm = ChatOpenAI(
            model=model_name,
            api_key=groq_api_key,
            base_url="https://api.groq.com/openai/v1",
            temperature=0,
        )
        structured_llm = llm.with_structured_output(TestSchema)
        response = structured_llm.invoke("Hi")
        print(f"SUCCESS {model_name}:", response)
    except Exception as exc:
        print(f"FAILED {model_name}: {exc}")
