import re


INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions?", re.I),
    re.compile(r"(reveal|show|print|repeat)\s+(the\s+)?system\s+prompt", re.I),
    re.compile(r"(developer|admin|debug)\s+mode", re.I),
    re.compile(r"(bypass|override)\s+(safety|security|instructions?)", re.I),
    re.compile(r"(show|reveal|list)\s+(all|every)\s+users?", re.I),
    re.compile(r"(api[_ -]?key|GROQ_API_KEY|access[_ -]?token)", re.I),
    re.compile(r"(SWdub3JlIGFsb|49676e6f7265)", re.I),
)


def contains_prompt_injection(messages):
    return any(
        pattern.search(str(message))
        for message in messages
        for pattern in INJECTION_PATTERNS
    )


def safe_unknown_context(status="ok"):
    return {
        "intent": "unknown",
        "category": None,
        "start_date": None,
        "end_date": None,
        "resolved_query": None,
        "ai_status": status,
    }


def grounded_answer(amount, currency, language="English"):
    from src.agents.personalization import format_money

    display = format_money(amount, currency)
    language = (language or "English").casefold()
    if language == "marathi":
        return f"तुमच्या नोंदीनुसार, रक्कम {display} आहे."
    if language == "hindi":
        return f"आपके रिकॉर्ड के अनुसार, राशि {display} है।"
    return f"Based on your records, the amount is {display}."
