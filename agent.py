import json
import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI


class GeminiQuotaError(RuntimeError):
    """Gemini API quota or rate limit was reached."""


class GeminiUnavailableError(RuntimeError):
    """Gemini service is temporarily unavailable."""


PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a careful sales analytics and business insights assistant.
Answer using ONLY the supplied sales summary. Never invent numbers, categories, products, causes, or trends.
If the summary does not contain enough evidence to answer a question, say what additional data is needed.
Distinguish observed facts from hypotheses. Provide concise, practical recommendations.
When useful, use headings and bullet points. Currency values are in the dataset's assumed currency; do not assume a currency symbol.
Do not claim correlation proves causation. The data is aggregated and may not include marketing spend, returns, seasonality drivers, or customer details.
SALES SUMMARY (JSON):
{summary}
"""),
    ("human", "{question}")
])


def _classify_error(exc: Exception, model_name: str) -> RuntimeError:
    raw = str(exc)
    message = raw.lower()
    if any(token in message for token in ["resource_exhausted", "quota", "429", "rate limit", "too many requests"]):
        return GeminiQuotaError(
            f"Google Gemini rejected the request because a quota or rate limit was reached for '{model_name}'. "
            "Check project usage and limits at https://ai.dev/rate-limit and billing/plan details. "
            "Wait for the stated reset window before retrying; automatic retries cannot restore exhausted quota."
        )
    if any(token in message for token in ["503", "unavailable", "high demand", "service unavailable", "deadline exceeded"]):
        return GeminiUnavailableError(
            f"Gemini model '{model_name}' appears temporarily unavailable. Wait briefly and retry once. "
            "If this continues, check https://ai.google.dev/gemini-api/docs/troubleshooting."
        )
    if any(token in message for token in ["api key", "permission_denied", "401", "403", "unauthenticated", "invalid_argument"]):
        return RuntimeError(
            "Gemini authentication/model configuration failed. Verify GOOGLE_API_KEY, API access, and GEMINI_MODEL. "
            "Do not paste your API key into chat or source control. Technical detail: " + raw
        )
    return RuntimeError(f"Gemini request failed for model '{model_name}': {raw}")


def ask_sales_analyst(question: str, summary: dict, model_name: str | None = None, api_key: str | None = None) -> str:
    model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    api_key = api_key or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is missing. Add it to your .env file.")
    try:
        # Keep retries low: retrying exhausted quota is not useful and can add failed requests.
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0.2,
            max_retries=1,
            timeout=60,
        )
        chain = PROMPT | llm
        response = chain.invoke({
            "question": question,
            "summary": json.dumps(summary, ensure_ascii=False, default=str)
        })
        content = getattr(response, "content", "")
        if isinstance(content, list):
            content = "\n".join(str(item.get("text", item)) if isinstance(item, dict) else str(item) for item in content)
        content = str(content).strip()
        if not content:
            raise RuntimeError("Gemini returned an empty response.")
        return content
    except (GeminiQuotaError, GeminiUnavailableError):
        raise
    except Exception as exc:
        raise _classify_error(exc, model_name) from exc
