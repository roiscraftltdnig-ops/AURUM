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
    "VISITOR": 1,
    "CURIOUS_EXPLORER": 2,
    "INTERESTED": 2,
    "PRODUCT_INTEREST": 3,
    "INVESTMENT_CONSIDERATION": 3,
    "INVESTOR_PROSPECT": 3,
    "PARTNER_PROSPECT": 3,
    "HYBRID_PROSPECT": 4,
    "HIGH_INTENT": 5,
    "READY_FOR_REGISTRATION": 6,
    "REGISTRATION_HANDOFF": 7,
    "HUMAN_HANDOFF": 8,
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

INVESTOR_SIGNALS = [
    "invest", "investment", "deposit", "plan", "profit", "return", "withdraw",
    "ex-ai", "ex ai", "exai", "trading bot", "starting amount", "minimum",
]

PARTNER_SIGNALS = [
    "partner", "referral", "refer", "commission", "compensation", "team building",
    "build a team", "network", "community", "audience", "invite people", "webinar",
    "earn without investing", "earn without investment", "promote", "matching bonus",
    "leadership bonus", "partner level", "partner rank",
]

NO_CAPITAL_SIGNALS = [
    "don't have money", "dont have money", "do not have money", "no money", "no capital",
    "don't have capital", "dont have capital", "cannot afford", "can't afford",
    "cant afford", "without investing", "without investment", "cannot afford a plan",
]

PARTNER_READY_SIGNALS = [
    "i want to become a partner", "ready to become a partner", "ready to build a team",
    "i have people interested", "people are interested", "start my partner journey",
    "partner registration", "register as a partner", "join the partner program",
]

HUMAN_HANDOFF_SIGNALS = [
    "connect me", "connect me to someone", "speak with admin", "talk to admin",
    "speak with the team", "talk to the team", "representative", "call me",
]

LOW_INTENT_TERMS = ["what is", "tell me about", "explain", "how does", "how it works", "about aurum"]

GREETING_TERMS = {"hi", "hello", "hey", "/start", "start", "good morning", "good afternoon", "good evening"}

INTENT_KEYWORDS = {
    "partner_information": [
        "partner", "partner program", "referral", "refer", "commission", "compensation",
        "team building", "matching bonus", "rank", "leadership", "webinar", "prospect",
        "invite friends", "invite people", "no capital", "don't have capital", "dont have capital",
    ],
    "investment_information": [
        "invest", "investment", "deposit", "plan", "minimum", "profit", "return",
        "withdraw", "earning", "earn", "start with", "ex-ai pro",
    ],
    "registration": [
        "register", "join", "start now", "proceed", "buy credit", "make payment",
        "activate", "open account", "sign up",
    ],
    "human_support": HUMAN_HANDOFF_SIGNALS + ["support", "agent", "person", "human"],
    "compensation": [
        "commission", "compensation", "bonus", "matching", "reward", "get paid",
        "percentage", "percent", "earning opportunity",
    ],
    "webinar": ["webinar", "presentation", "training session", "zoom", "meeting"],
    "product_explanation": [
        "ex-ai", "ex ai", "exai", "neo bank", "neobank", "zeus", "bot", "product",
        "service", "wallet", "card",
    ],
    "company_overview": ["aurum", "foundation", "what is", "about", "overview", "tell me"],
}

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


def contains_any(text: str, phrases: list[str]) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in phrases)


def detect_partner_topics(text: str) -> list[str]:
    lowered = text.lower()
    topics: list[str] = []
    topic_terms = {
        "Partner overview": ["partner program", "become a partner", "partner journey"],
        "Direct referrals": ["referral", "refer", "invite someone", "introduce people"],
        "Team building": ["team", "network", "community", "organization"],
        "Compensation": ["commission", "compensation", "reward", "earn", "get paid"],
        "Ranks and leadership": ["rank", "level", "leader", "leadership"],
        "Matching bonuses": ["matching bonus", "matching system"],
        "Qualification": ["qualify", "qualification", "requirement", "business volume"],
        "Webinar prospecting": ["webinar", "prospect", "invitation", "follow up"],
        "Partner training": ["first 30 days", "daily routine", "training", "beginner roadmap"],
    }
    for topic, terms in topic_terms.items():
        if any(term in lowered for term in terms):
            topics.append(topic)
    return topics


def detect_intent(text: str, memory: dict[str, Any]) -> str:
    lowered = text.lower().strip()
    if lowered in GREETING_TERMS:
        return "greeting"
    for intent in ["human_support", "registration", "compensation", "partner_information", "investment_information", "webinar", "product_explanation", "company_overview"]:
        if contains_any(lowered, INTENT_KEYWORDS[intent]):
            return intent
    if lowered in {"more", "tell me more", "continue", "go on", "explain more"}:
        return str(memory.get("detected_intent") or "education")
    return "unknown"


def detect_user_type(text: str, memory: dict[str, Any]) -> str:
    lowered = text.lower()
    no_capital = contains_any(lowered, NO_CAPITAL_SIGNALS)
    amount = extract_investment_amount(text)
    investor_signal = bool(amount) or contains_any(lowered, INVESTOR_SIGNALS)
    partner_signal = no_capital or contains_any(lowered, PARTNER_SIGNALS) or contains_any(lowered, PARTNER_READY_SIGNALS)
    previous = str(memory.get("user_type") or "").lower()

    if no_capital and not amount:
        return "partner"
    if previous == "hybrid" and (investor_signal or partner_signal):
        return "hybrid"
    if investor_signal and partner_signal:
        return "hybrid"
    if partner_signal and previous == "investor":
        return "hybrid"
    if investor_signal and previous == "partner":
        return "hybrid"
    if partner_signal:
        return "partner"
    if investor_signal:
        return "investor"
    return previous if previous in {"investor", "partner", "hybrid"} else "undetermined"


def merge_unique(existing: list[Any] | None, additions: list[Any], limit: int = 20) -> list[Any]:
    values = list(existing or [])
    for item in additions:
        if item and item not in values:
            values.append(item)
    return values[-limit:]


def infer_stage(text: str, memory: dict[str, Any], lead_score: int, user_type: str) -> tuple[str, str]:
    lowered = text.lower().strip()
    amount = extract_investment_amount(text) or parse_amount_label(memory.get("preferred_investment_range"))

    if contains_any(lowered, HUMAN_HANDOFF_SIGNALS):
        return "HUMAN_HANDOFF", "VERY_HIGH"
    if contains_any(lowered, PARTNER_READY_SIGNALS) or any(term in lowered for term in VERY_HIGH_INTENT_TERMS):
        return "READY_FOR_REGISTRATION", "VERY_HIGH"
    if lead_score >= 71:
        return "HIGH_INTENT", "HIGH"
    if user_type == "hybrid":
        return "HYBRID_PROSPECT", "HIGH"
    if user_type == "partner":
        return "PARTNER_PROSPECT", "MEDIUM"
    if amount or any(term in lowered for term in HIGH_INTENT_TERMS):
        return "INVESTOR_PROSPECT", "HIGH"
    if user_type == "investor":
        return "INVESTOR_PROSPECT", "MEDIUM"
    if detect_products(text):
        return "INTERESTED", "MEDIUM"
    if lowered in GREETING_TERMS:
        return "VISITOR", "LOW"
    if any(term in lowered for term in LOW_INTENT_TERMS):
        return "INTERESTED", "LOW"
    return memory.get("conversation_stage") or "INTERESTED", memory.get("intent_level") or "LOW"


def display_stage_for(stage: str, user_type: str, intent_level: str, intent: str) -> str:
    if stage == "HUMAN_HANDOFF" or intent == "human_support":
        return "Human Handoff"
    if stage in {"READY_FOR_REGISTRATION", "REGISTRATION_HANDOFF"} or intent == "registration":
        return "Registration"
    if stage == "HIGH_INTENT":
        return "High Intent"
    if user_type == "partner" or intent in {"partner_information", "compensation", "webinar"}:
        return "Partner Interest"
    if user_type == "investor" or intent == "investment_information":
        return "Investor Interest"
    if user_type == "hybrid":
        return "Consideration"
    if intent == "greeting":
        return "Greeting"
    if intent in {"product_explanation", "company_overview"}:
        return "Education"
    if intent_level == "HIGH":
        return "Consideration"
    if intent_level == "VERY_HIGH":
        return "Decision"
    if stage == "INTERESTED":
        return "Interest"
    return "Discovery"


def keep_forward_stage(previous: str | None, current: str) -> str:
    if not previous:
        return current
    if previous == "HUMAN_HANDOFF":
        return previous
    if previous in {"READY_FOR_REGISTRATION", "REGISTRATION_HANDOFF"} and current != "HUMAN_HANDOFF":
        return previous
    if current in {"INVESTOR_PROSPECT", "PARTNER_PROSPECT", "HYBRID_PROSPECT"}:
        return current
    return previous if STAGE_ORDER.get(previous, 0) > STAGE_ORDER.get(current, 0) else current


def recommended_next_action(stage: str, user_type: str, amount: float | None, products: list[str], objections: list[str]) -> str:
    if "TRUST_CONCERN" in objections:
        return "Build confidence with product, team, verification, and due-diligence context."
    if "MONEY_CONCERN" in objections and user_type == "partner":
        return "Explain the Partner Program and ask about the user's network, audience, or community."
    if stage in {"READY_FOR_REGISTRATION", "REGISTRATION_HANDOFF", "HUMAN_HANDOFF"}:
        return "Collect WhatsApp/contact details and connect the user to an Aurum representative."
    if user_type == "hybrid":
        return "Match the investment range and qualify the user's partner network before combined onboarding."
    if user_type == "partner":
        return "Explain partner rewards and ask whether the user wants direct referrals or team building."
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
    partner_topics = detect_partner_topics(user_text)
    objections = detect_objections(user_text)
    detected_intent = detect_intent(user_text, memory)
    user_type = detect_user_type(user_text, memory)
    stage, intent_level = infer_stage(user_text, memory, lead_score, user_type)
    stage = keep_forward_stage(memory.get("conversation_stage"), stage)
    previous_intent = memory.get("intent_level")
    if previous_intent and INTENT_ORDER.get(previous_intent, 0) > INTENT_ORDER.get(intent_level, 0):
        intent_level = previous_intent

    return {
        "conversation_stage": stage,
        "display_conversation_stage": display_stage_for(stage, user_type, intent_level, detected_intent),
        "detected_intent": detected_intent,
        "user_type": user_type,
        "intent_level": intent_level,
        "investment_amount": amount,
        "investment_interest": normalize_money(amount) if amount else memory.get("investment_interest"),
        "matched_plan": plan["name"] if plan else None,
        "matched_plan_range": plan_range(plan) if plan else None,
        "products_interested_in": products,
        "partner_topics": partner_topics,
        "concerns": objections,
        "recommended_next_action": recommended_next_action(stage, user_type, amount, products, objections),
    }


def apply_sales_state(memory: dict[str, Any], analysis: dict[str, Any], user_text: str, lead_score: int = 0) -> None:
    memory["conversation_stage"] = analysis["conversation_stage"]
    memory["display_conversation_stage"] = analysis.get("display_conversation_stage")
    memory["detected_intent"] = analysis.get("detected_intent")
    memory["user_type"] = analysis["user_type"]
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
    memory["partner_topics"] = merge_unique(memory.get("partner_topics"), analysis.get("partner_topics") or [])
    memory["concerns"] = merge_unique(memory.get("concerns"), analysis.get("concerns") or [])
    memory["questions_asked"] = merge_unique(memory.get("questions_asked"), [user_text.strip()], limit=30)


def sales_state_for_prompt(memory: dict[str, Any]) -> str:
    keys = [
        "conversation_stage",
        "display_conversation_stage",
        "detected_intent",
        "user_type",
        "intent_level",
        "investment_interest",
        "matched_plan",
        "matched_plan_range",
        "products_interested_in",
        "partner_topics",
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
