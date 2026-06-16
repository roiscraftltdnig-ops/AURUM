import re
from typing import Any


PLAN_LEVELS = [
    {"name": "Basic", "min": 100, "max": 249},
    {"name": "Standard", "min": 250, "max": 999},
    {"name": "Comfort", "min": 1000, "max": 2499},
    {"name": "Optimal", "min": 2500, "max": 4999},
    {"name": "Business", "min": 5000, "max": 9999},
    {"name": "VIP", "min": 10000, "max": 24999},
    {"name": "Luxury", "min": 25000, "max": 49999},
    {"name": "Ultimate", "min": 50000, "max": 99999},
]

STAGE_ORDER = {
    "NEW_VISITOR": 1,
    "CURIOUS_EXPLORER": 2,
    "PRODUCT_INTEREST": 3,
    "INVESTMENT_CONSIDERATION": 4,
    "HIGH_INTENT": 5,
    "REGISTRATION_HANDOFF": 6,
}

INTENT_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "VERY_HIGH": 4}

PRODUCT_ALIASES = {
    "EX-AI Bot": ["ex-ai", "ex ai", "exai", "trading bot", "ai bot"],
    "EX-AI Pro": ["ex-ai pro", "ex ai pro", "exai pro"],
    "NeoBank": ["neobank", "neo bank", "wallet", "card", "bank"],
    "Zeus AI Bot": ["zeus"],
    "Aurum Plans": ["plan", "plans", "minimum", "deposit", "withdraw", "earn", "return", "profit"],
}

MONEY_CONTEXT = {
    "$",
    "usd",
    "usdt",
    "dollar",
    "dollars",
    "start",
    "deposit",
    "invest",
    "investment",
    "budget",
    "capital",
    "with",
    "range",
}

HIGH_INTENT_TERMS = [
    "minimum",
    "start with",
    "deposit",
    "how much",
    "earn",
    "earning",
    "return",
    "profit",
    "withdraw",
    "which plan",
    "best plan",
]

VERY_HIGH_INTENT_TERMS = [
    "register",
    "ready",
    "join",
    "start now",
    "i want to start",
    "i want to proceed",
    "connect me",
    "admin",
    "representative",
    "make payment",
    "pay",
    "buy credit",
]

LOW_INTENT_TERMS = ["what is", "tell me about", "explain", "how does", "how it works", "about aurum"]

OBJECTION_PATTERNS = {
    "MONEY_CONCERN": ["not enough", "expensive", "too much", "can't afford", "cannot afford", "no money", "small money"],
    "TRUST_CONCERN": ["scam", "real", "legit", "trust", "proof", "verify", "safe", "who owns"],
    "TIME_CONCERN": ["think", "later", "not now", "give me time", "come back"],
    "RISK_CONCERN": ["risk", "lose", "loss", "guarantee", "guaranteed", "sure profit"],
}


def normalize_money(amount: float | int) -> str:
    value = int(amount) if float(amount).is_integer() else amount
    return f"{value:,} USDT"


def parse_amount_label(label: str | None) -> float | None:
    if not label:
        return None
    match = re.search(r"(\d[\d,]*(?:\.\d+)?)", str(label))
    if not match:
        return None
    return float(match.group(1).replace(",", ""))


def extract_investment_amount(text: str) -> float | None:
    lowered = text.lower()
    if not any(term in lowered for term in MONEY_CONTEXT):
        return None
    matches = re.finditer(r"(?:\$|usd\s*|usdt\s*)?\s*(\d[\d,]*(?:\.\d+)?)\s*(?:usdt|usd|dollars?)?", lowered)
    for match in matches:
        raw = match.group(0)
        value = float(match.group(1).replace(",", ""))
        if value < 20 or value > 1_000_000:
            continue
        window = lowered[max(0, match.start() - 24): match.end() + 24]
        if any(term in window for term in MONEY_CONTEXT) or "$" in raw or "usd" in raw or "usdt" in raw:
            return value
    return None


def plan_for_amount(amount: float | int | None) -> dict[str, Any] | None:
    if amount is None:
        return None
    for plan in PLAN_LEVELS:
        if plan["min"] <= amount <= plan["max"]:
            return plan
    return None


def plan_range(plan: dict[str, Any]) -> str:
    return f"{plan['min']:,}-{plan['max']:,} USDT"


def detect_products(text: str) -> list[str]:
    lowered = text.lower()
    products: list[str] = []
    for product, aliases in PRODUCT_ALIASES.items():
        if any(alias in lowered for alias in aliases):
            products.append(product)
    return products


def detect_objections(text: str) -> list[str]:
    lowered = text.lower()
    objections: list[str] = []
    for objection, patterns in OBJECTION_PATTERNS.items():
        if any(pattern in lowered for pattern in patterns):
            objections.append(objection)
    return objections


def merge_unique(existing: list[Any] | None, additions: list[Any], limit: int = 20) -> list[Any]:
    values = list(existing or [])
    for item in additions:
        if item and item not in values:
            values.append(item)
    return values[-limit:]


def infer_stage(text: str, memory: dict[str, Any], lead_score: int) -> tuple[str, str]:
    lowered = text.lower().strip()
    amount = extract_investment_amount(text) or parse_amount_label(memory.get("preferred_investment_range"))

    if any(term in lowered for term in VERY_HIGH_INTENT_TERMS):
        return "REGISTRATION_HANDOFF", "VERY_HIGH"
    if amount or any(term in lowered for term in HIGH_INTENT_TERMS):
        return ("HIGH_INTENT" if lead_score >= 70 else "INVESTMENT_CONSIDERATION"), "HIGH"
    if detect_products(text):
        return "PRODUCT_INTEREST", "MEDIUM"
    if lowered in {"hi", "hello", "hey", "/start", "start", "good morning", "good afternoon", "good evening"}:
        return "NEW_VISITOR", "LOW"
    if any(term in lowered for term in LOW_INTENT_TERMS):
        return "CURIOUS_EXPLORER", "LOW"
    return memory.get("conversation_stage") or "CURIOUS_EXPLORER", memory.get("intent_level") or "LOW"


def keep_forward_stage(previous: str | None, current: str) -> str:
    if not previous:
        return current
    return previous if STAGE_ORDER.get(previous, 0) > STAGE_ORDER.get(current, 0) else current


def recommended_next_action(stage: str, amount: float | None, products: list[str], objections: list[str]) -> str:
    if "TRUST_CONCERN" in objections:
        return "Build confidence with product, team, verification, and due-diligence context."
    if "MONEY_CONCERN" in objections:
        return "Explain entry-level starting options and help the user choose a comfortable range."
    if stage == "REGISTRATION_HANDOFF":
        return "Collect WhatsApp/contact details and connect the user to an Aurum representative."
    if amount:
        plan = plan_for_amount(amount)
        if plan:
            return f"Explain the {plan['name']} range and ask whether to walk through activation."
        return "Clarify the user's intended range and connect them for plan confirmation."
    if stage == "INVESTMENT_CONSIDERATION":
        return "Ask for the amount range and explain matching plan levels."
    if products:
        return "Connect the product explanation to the user's goal and ask about their intended starting range."
    return "Educate briefly, then guide the user toward product interest or starting range."


def analyze_sales_state(user_text: str, memory: dict[str, Any], lead_score: int = 0) -> dict[str, Any]:
    amount = extract_investment_amount(user_text) or parse_amount_label(memory.get("preferred_investment_range"))
    plan = plan_for_amount(amount)
    products = detect_products(user_text)
    objections = detect_objections(user_text)
    stage, intent_level = infer_stage(user_text, memory, lead_score)
    stage = keep_forward_stage(memory.get("conversation_stage"), stage)
    previous_intent = memory.get("intent_level")
    if previous_intent and INTENT_ORDER.get(previous_intent, 0) > INTENT_ORDER.get(intent_level, 0):
        intent_level = previous_intent

    return {
        "conversation_stage": stage,
        "intent_level": intent_level,
        "investment_amount": amount,
        "investment_interest": normalize_money(amount) if amount else memory.get("investment_interest"),
        "matched_plan": plan["name"] if plan else None,
        "matched_plan_range": plan_range(plan) if plan else None,
        "products_interested_in": products,
        "concerns": objections,
        "recommended_next_action": recommended_next_action(stage, amount, products, objections),
    }


def apply_sales_state(memory: dict[str, Any], analysis: dict[str, Any], user_text: str, lead_score: int = 0) -> None:
    memory["conversation_stage"] = analysis["conversation_stage"]
    memory["intent_level"] = analysis["intent_level"]
    memory["recommended_next_action"] = analysis["recommended_next_action"]
    memory["lead_score"] = lead_score

    if analysis.get("investment_amount"):
        memory["investment_amount"] = analysis["investment_amount"]
        memory["investment_interest"] = analysis["investment_interest"]
        memory["preferred_investment_range"] = analysis["investment_interest"]
    if analysis.get("matched_plan"):
        memory["matched_plan"] = analysis["matched_plan"]
        memory["matched_plan_range"] = analysis["matched_plan_range"]

    memory["products_interested_in"] = merge_unique(memory.get("products_interested_in"), analysis.get("products_interested_in") or [])
    memory["concerns"] = merge_unique(memory.get("concerns"), analysis.get("concerns") or [])
    memory["questions_asked"] = merge_unique(memory.get("questions_asked"), [user_text.strip()], limit=30)


def sales_state_for_prompt(memory: dict[str, Any]) -> str:
    keys = [
        "conversation_stage",
        "intent_level",
        "investment_interest",
        "matched_plan",
        "matched_plan_range",
        "products_interested_in",
        "concerns",
        "recommended_next_action",
    ]
    return "\n".join(f"- {key}: {memory.get(key)}" for key in keys if memory.get(key) not in (None, "", [], {}))


def plan_summary_for_amount(amount: float | None) -> str | None:
    plan = plan_for_amount(amount)
    if not plan:
        if amount is not None and amount < 100:
            return "That is below Aurum's listed starting point of 100 USDT."
        if amount is not None and amount > 99_999:
            return "That is above the listed Ultimate range, so a team member should confirm the suitable route."
        return None
    return f"{normalize_money(amount)} sits in the {plan['name']} Plan range ({plan_range(plan)})."


def all_plan_ranges_text() -> str:
    return "\n".join(f"- {plan['name']}: {plan_range(plan)}" for plan in PLAN_LEVELS)
