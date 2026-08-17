import os
from dataclasses import dataclass

from dotenv import load_dotenv
from langchain_groq import ChatGroq


load_dotenv()


@dataclass(frozen=True)
class LLMSettings:
    model: str
    timeout_seconds: float
    max_retries: int
    max_tokens: int


def _number(name, default, cast, minimum, maximum):
    value = os.getenv(name)
    try:
        parsed = cast(value) if value is not None else default
    except (TypeError, ValueError) as error:
        raise RuntimeError(f"{name} must be a number.") from error
    if parsed < minimum or parsed > maximum:
        raise RuntimeError(f"{name} must be between {minimum} and {maximum}.")
    return parsed


def get_llm_settings():
    model = os.getenv("FINANCE_LLM_MODEL", "llama-3.3-70b-versatile").strip()
    if not model or len(model) > 100:
        raise RuntimeError("FINANCE_LLM_MODEL must contain 1 to 100 characters.")
    return LLMSettings(
        model=model,
        timeout_seconds=_number("FINANCE_LLM_TIMEOUT_SECONDS", 20.0, float, 1, 120),
        max_retries=_number("FINANCE_LLM_MAX_RETRIES", 2, int, 0, 5),
        max_tokens=_number("FINANCE_LLM_MAX_TOKENS", 300, int, 50, 2000),
    )


def get_llm():
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is not configured."
        )

    settings = get_llm_settings()
    return ChatGroq(
        api_key=api_key,
        model=settings.model,
        temperature=0,
        timeout=settings.timeout_seconds,
        max_retries=settings.max_retries,
        max_tokens=settings.max_tokens,
    )
