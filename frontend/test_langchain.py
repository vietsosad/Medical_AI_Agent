import os

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field


class TestSchema(BaseModel):
    answer: str = Field(description="the answer")


google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    raise RuntimeError("Set GOOGLE_API_KEY before running this smoke test.")

for model_name in ["gemini-2.5-flash", "gemini-flash-latest"]:
    try:
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=google_api_key,
        )
        structured_llm = llm.with_structured_output(TestSchema)
        response = structured_llm.invoke("Hi")
        print(f"SUCCESS {model_name}:", response)
    except Exception as exc:
        print(f"FAILED {model_name}:", exc)
