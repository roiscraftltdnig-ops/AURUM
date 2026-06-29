import re
from typing import Any

from app.services.sales_intelligence import (
    extract_investment_amount,
    parse_amount_label,
    plan_for_amount,
    plan_range,
    normalize_money,
)


V4_STAGES = [
    "Curious Visitor",
    "Learning",
    "Interested",
    "Evaluating",
    "Decision",
    "Activation",
    "Partner Recruitment",
    "Investor + Partner Hybrid",
    "Existing Customer",
]

INTENT_RULES = {
    "Investment Interest": ["invest", "investment", "deposit", "plan", "start with", "budget", "minimum"],
    "Partner Interest": ["partner", "referral", "refer", "team", "network", "invite people", "invite friends"],
    "Profit Question": ["profit", "return", "earn", "earning", "roi", "monthly"],
    "Compensation Question": ["commission", "compensation", "bonus", "matching", "rank reward", "percentage"],
    "Product Question": ["ex-ai", "ex ai", "exai", "neobank", "neo bank", "zeus", "bot", "wallet", "card"],
    "Withdrawal": ["withdraw", "withdrawal", "cash out"],
    "Deposit": ["deposit", "fund", "payment", "pay", "buy credit"],
    "Registration": ["register", "sign up", "join", "open account", "create account"],
    "Comparison": ["compare", "versus", "vs", "better", "which plan", "which option", "best plan"],
    "Objection": ["not sure", "afraid", "worried", "expensive", "too much", "later", "think about"],
    "Trust": ["scam", "real", "legit", "trust", "proof", "verify", "who owns"],
    "Risk": ["risk", "lose", "loss", "guarantee", "guaranteed", "safe"],
    "Activation": ["activate", "activation", "start now", "proceed", "ready", "make payment"],
    "Support": ["support", "help", "issue", "problem", "not working"],
    "Referral": ["referral", "refer", "invite", "contacts", "friends", "prospects"],
    "Webinar": ["webinar", "presentation", "training", "zoom", "meeting"],
    "Admin Request": ["admin", "representative", "human", "call me", "speak with", "connect me"],
    "Greeting": ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "/start"],
    "Casual Conversation": ["thanks", "thank you", "ok", "okay", "alright"],
}

OBJECTION_RULES = {
    "Money": ["expensive", "too much", "not enough", "no money", "no capital", "can't afford", "cannot afford"],
    "Trust": ["scam", "real", "legit", "trust", "proof", "verify"],
    "Time": ["later", "not now", "think about", "give me time", "come back"],
    "Experience": ["new", "beginner", "no experience", "never done"],
    "Fear": ["afraid", "worried", "fear", "concerned"],
    "Risk": ["risk", "lose", "loss", "guarantee", "guaranteed"],
    "Partner concerns": ["no audience", "no followers", "don't know anyone", "small network"],
    "Withdrawal": ["withdraw", "withdrawal", "cash out"],
    "Returns": ["profit", "return", "earn", "roi"],
    "Company legitimacy": ["who owns", "founder", "license", "licensed", "registered"],
    "Activation": ["activate", "payment", "buy credit", "deposit"],
}

PLAYBOOKS = {
    "Investment Playbook": {
        "goal": "Move the user from curiosity into a plan recommendation and activation readiness.",
        "flow": "Confirm budget, match plan, explain risk/withdrawal basics, ask for activation readiness.",
        "cta": "Ask whether to walk through activation or compare the next plan up.",
    },
    "Partner Playbook": {
        "goal": "Qualify referral potential and move the user toward partner onboarding or webinar invitation.",
        "flow": "Confirm network, explain education-led referrals, introduce team growth, ask for first action.",
        "cta": "Ask how many people they can invite or whether they want partner onboarding.",
    },
    "Hybrid Playbook": {
        "goal": "Progress investor plan selection and partner qualification together.",
        "flow": "Match budget, qualify referral network, recommend a combined next step.",
        "cta": "Ask whether they want activation first or partner onboarding first.",
    },
    "Objection Playbook": {
        "goal": "Lower resistance without pressure and move the user back into a clear decision path.",
        "flow": "Acknowledge concern, answer with official facts, recommend a low-risk next step.",
        "cta": "Ask which concern should be clarified before they decide.",
    },
    "Profit Explanation Playbook": {
        "goal": "Explain earning structure accurately without promising guaranteed returns.",
        "flow": "Use amount if known, show plan, official return/withdrawal structure, ask for next step.",
        "cta": "Ask whether to calculate the user's specific starting range or route to activation.",
    },
    "Compensation Playbook": {
        "goal": "Explain partner earning layers without inventing fixed percentages.",
        "flow": "Explain referral, team, rank, leadership, matching-bonus conditions.",
        "cta": "Ask whether the user wants direct referrals, team building, or both.",
    },
    "Activation Playbook": {
        "goal": "Move ready users to guided activation and human follow-up.",
        "flow": "Confirm readiness, collect WhatsApp, amount, country, and preferred route.",
        "cta": "Ask for WhatsApp number and amount range.",
    },
    "Webinar Invitation Playbook": {
        "goal": "Convert interest into webinar attendance or partner prospecting action.",
        "flow": "Position webinar as education, confirm interest, ask for preferred reminder/follow-up.",
        "cta": "Ask whether they want to attend or invite prospects.",
    },
    "Referral Playbook": {
        "goal": "Turn referral curiosity into a practical first contact list and invitation plan.",
        "flow": "Estimate referral count, encourage realistic momentum, ask for first channel.",
        "cta": "Ask which channel they will use first.",
    },
    "Admin Handoff Playbook": {
        "goal": "Collect details and notify admin for high-intent support.",
        "flow": "Affirm request, collect contact details, summarize intent for admin.",
        "cta": "Ask for WhatsApp, country, and amount or partner goal.",
    },
}


def _contains(text: str, phrases: list[str]) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in phrases)


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def detect_intents(text: str) -> list[str]:
    lowered = text.lower().strip()
    intents = []
    if lowered in INTENT_RULES["Greeting"]:
        intents.append("Greeting")
    for intent, phrases in INTENT_RULES.items():
        if intent == "Greeting":
            continue
        if _contains(lowered, phrases):
            intents.append(intent)
    if not intents:
        intents.append("Casual Conversation" if len(lowered.split()) <= 3 else "Product Question")
    if "Compensation Question" in intents and "Partner Interest" not in intents:
        intents.append("Partner Interest")
    if "Profit Question" in intents and "Investment Interest" not in intents:
        intents.append("Investment Interest")
    return intents


def detect_objection_categories(text: str) -> list[str]:
    lowered = text.lower()
    return [label for label, phrases in OBJECTION_RULES.items() if _contains(lowered, phrases)]


def extract_referral_count(text: str) -> int | None:
    lowered = text.lower()
    for match in re.finditer(r"(\d{1,5})\s+(?:people|persons|friends|contacts|prospects|members|referrals)", lowered):
        value = int(match.group(1))
        if 0 < value <= 10000:
            return value
    return None


def extract_memory_signals(text: str) -> dict[str, Any]:
    lowered = text.lower()
    updates: dict[str, Any] = {}
    amount = extract_investment_amount(text)
    if amount:
        updates["budget"] = normalize_money(amount)
        updates["investment_amount"] = amount
    referral_count = extract_referral_count(text)
    if referral_count is not None:
        updates["referral_count"] = referral_count
    occupation_match = re.search(r"(?:i work as|i am a|i'm a|my occupation is)\s+([A-Za-z][A-Za-z '\-]{2,50})", text, re.IGNORECASE)
    if occupation_match:
        occupation = occupation_match.group(1).strip()
        if occupation.lower() not in {"beginner", "partner", "member", "investor"}:
            updates["occupation"] = occupation.title()
    income_goal_match = re.search(r"(?:income goal|make|earn|target)\s+(?:is\s+)?(\$?\s*\d[\d,]*(?:\.\d+)?\s*(?:usdt|usd|dollars?)?)\s*(?:per month|monthly|a month)?", text, re.IGNORECASE)
    if income_goal_match and any(term in lowered for term in ["goal", "monthly", "per month", "target"]):
        updates["income_goal"] = " ".join(income_goal_match.group(1).upper().replace("$", "USD ").split())
    if any(term in lowered for term in ["low risk", "careful", "conservative", "small amount"]):
        updates["risk_tolerance"] = "Conservative"
    elif any(term in lowered for term in ["high risk", "aggressive", "big amount", "scale fast"]):
        updates["risk_tolerance"] = "Aggressive"
    elif any(term in lowered for term in ["moderate risk", "balanced"]):
        updates["risk_tolerance"] = "Balanced"
    if any(term in lowered for term in ["attend webinar", "join webinar", "webinar reminder", "webinar link"]):
        updates["interest_in_webinars"] = True
    if any(term in lowered for term in ["already activated", "account activated", "i have activated"]):
        updates["activation_status"] = "Activated"
    elif any(term in lowered for term in ["ready to activate", "activation", "buy credit", "make payment"]):
        updates["activation_status"] = "Activation requested"
    if any(term in lowered for term in ["already a partner", "registered partner"]):
        updates["partner_status"] = "Registered partner"
    elif any(term in lowered for term in ["become a partner", "partner registration", "join the partner program"]):
        updates["partner_status"] = "Partner prospect"
    return updates


def detect_stage(text: str, memory: dict[str, Any], intents: list[str], opportunity_scores: dict[str, int]) -> str:
    if memory.get("experience_level") == "Existing Aurum member" or memory.get("activation_status") == "Activated":
        return "Existing Customer"
    if "Investor + Partner Hybrid" in str(memory.get("sales_stage_v4")):
        if any(intent in intents for intent in ["Investment Interest", "Partner Interest", "Referral"]):
            return "Investor + Partner Hybrid"
    if "Investment Interest" in intents and any(intent in intents for intent in ["Partner Interest", "Referral", "Compensation Question"]):
        return "Investor + Partner Hybrid"
    if any(intent in intents for intent in ["Activation", "Registration"]) or opportunity_scores.get("activation_probability", 0) >= 75:
        return "Activation"
    if "Admin Request" in intents:
        return "Decision"
    if any(intent in intents for intent in ["Partner Interest", "Referral", "Compensation Question", "Webinar"]):
        return "Partner Recruitment"
    if any(intent in intents for intent in ["Comparison", "Trust", "Risk", "Objection"]):
        return "Evaluating"
    if any(intent in intents for intent in ["Investment Interest", "Profit Question", "Withdrawal", "Deposit"]):
        return "Decision" if opportunity_scores.get("buying_intent", 0) >= 65 else "Interested"
    if any(intent in intents for intent in ["Product Question"]):
        return "Interested"
    if "Greeting" in intents:
        return "Curious Visitor"
    return "Learning"


def calculate_scores(text: str, memory: dict[str, Any], intents: list[str], objections: list[str]) -> dict[str, int]:
    previous = memory.get("opportunity_scores") or {}
    scores = {
        "investor_score": int(previous.get("investor_score") or 0),
        "partner_score": int(previous.get("partner_score") or 0),
        "buying_intent": int(previous.get("buying_intent") or 0),
        "urgency": int(previous.get("urgency") or 0),
        "trust_level": int(previous.get("trust_level") or 50),
        "referral_potential": int(previous.get("referral_potential") or 0),
        "webinar_potential": int(previous.get("webinar_potential") or 0),
        "activation_probability": int(previous.get("activation_probability") or 0),
    }
    amount = extract_investment_amount(text) or parse_amount_label(memory.get("preferred_investment_range"))
    referral_count = extract_referral_count(text) or int(memory.get("referral_count") or 0)

    if any(intent in intents for intent in ["Investment Interest", "Profit Question", "Deposit", "Withdrawal"]):
        scores["investor_score"] += 12
        scores["buying_intent"] += 8
    if amount:
        scores["investor_score"] += 18
        scores["buying_intent"] += 15
        scores["activation_probability"] += 10
    if any(intent in intents for intent in ["Partner Interest", "Referral", "Compensation Question"]):
        scores["partner_score"] += 14
        scores["referral_potential"] += 10
    if referral_count:
        scores["partner_score"] += 15
        scores["referral_potential"] += min(35, referral_count * 2)
    if "Webinar" in intents:
        scores["webinar_potential"] += 25
        scores["partner_score"] += 5
    if any(intent in intents for intent in ["Registration", "Activation", "Admin Request"]):
        scores["buying_intent"] += 25
        scores["urgency"] += 25
        scores["activation_probability"] += 25
    if any(label in objections for label in ["Trust", "Risk", "Company legitimacy"]):
        scores["trust_level"] -= 10
    elif any(intent in intents for intent in ["Product Question", "Investment Interest", "Partner Interest"]):
        scores["trust_level"] += 5
    if any(label in objections for label in ["Time", "Fear"]):
        scores["urgency"] -= 5
    return {key: _clamp(value) for key, value in scores.items()}


def select_playbook(intents: list[str], stage: str, memory: dict[str, Any], objections: list[str]) -> str:
    if "Admin Request" in intents:
        return "Admin Handoff Playbook"
    if stage == "Activation" or any(intent in intents for intent in ["Activation", "Registration"]):
        return "Activation Playbook"
    if stage == "Investor + Partner Hybrid":
        return "Hybrid Playbook"
    if "Webinar" in intents:
        return "Webinar Invitation Playbook"
    if "Referral" in intents:
        return "Referral Playbook"
    if objections:
        return "Objection Playbook"
    if "Compensation Question" in intents:
        return "Compensation Playbook"
    if "Profit Question" in intents:
        return "Profit Explanation Playbook"
    if "Partner Interest" in intents:
        return "Partner Playbook"
    return "Investment Playbook" if any(intent in intents for intent in ["Investment Interest", "Deposit", "Withdrawal"]) else "Investment Playbook"


def build_recommendation(memory: dict[str, Any], amount: float | None, stage: str) -> str:
    referral_count = int(memory.get("referral_count") or 0)
    plan = plan_for_amount(amount)
    if stage == "Investor + Partner Hybrid":
        if plan and referral_count:
            return f"Recommend the {plan['name']} Plan while building a partner list from the {referral_count} contacts already mentioned."
        if plan:
            return f"Recommend the {plan['name']} Plan and qualify referral potential before activation."
        return "Recommend clarifying budget and referral network so the user can choose investor, partner, or both."
    if stage == "Partner Recruitment":
        if referral_count:
            return f"Recommend starting with webinar invitations because {referral_count} possible contacts gives the user a practical partner starting point."
        return "Recommend the Partner Program path and ask how many people the user can introduce."
    if plan:
        if plan["name"] in {"Basic", "Standard"}:
            return f"Recommend the {plan['name']} Plan as a learning-first starting point before any upgrade conversation."
        return f"Recommend the {plan['name']} Plan with team confirmation before payment because the amount is more serious."
    return "Recommend learning the product and choosing a comfortable starting range before activation."


def financial_summary(memory: dict[str, Any], amount: float | None) -> str | None:
    if not amount:
        return None
    plan = plan_for_amount(amount)
    plan_text = f"{plan['name']} Plan ({plan_range(plan)})" if plan else "Team-confirmed custom route"
    return (
        f"Investment Summary\n"
        f"Amount: {normalize_money(amount)}\n"
        f"Applicable plan: {plan_text}\n"
        f"Current return structure: daily profit accrual; EX-AI Pro has an example shown as up to 10% monthly when applicable\n"
        f"Withdrawal threshold: 25 USDT minimum\n"
        f"Activation timeline: usually 12-24 hours after deposit\n"
        f"Recommended next step: confirm activation guidance with the Aurum team"
    )


def comparison_summary(amounts: list[float]) -> str | None:
    if len(amounts) < 2:
        return None
    lines = ["Plan Comparison"]
    for amount in amounts[:4]:
        plan = plan_for_amount(amount)
        plan_text = f"{plan['name']} ({plan_range(plan)})" if plan else "team confirmation needed"
        lines.append(f"{normalize_money(amount)}: {plan_text}")
    return "\n".join(lines)


def extract_comparison_amounts(text: str) -> list[float]:
    lowered = text.lower()
    if not _contains(lowered, INTENT_RULES["Comparison"]):
        return []
    amounts: list[float] = []
    for match in re.finditer(r"(?:\$|usd\s*|usdt\s*)?\s*(\d[\d,]*(?:\.\d+)?)\s*(?:usdt|usd|dollars?)?", lowered):
        value = float(match.group(1).replace(",", ""))
        if 20 <= value <= 1_000_000 and value not in amounts:
            amounts.append(value)
    return amounts


def micro_close_for(playbook_name: str, memory: dict[str, Any]) -> str:
    amount = parse_amount_label(memory.get("preferred_investment_range")) or memory.get("investment_amount")
    referral_count = memory.get("referral_count")
    if playbook_name == "Activation Playbook":
        return "Should I guide you into the activation step from here?"
    if playbook_name == "Hybrid Playbook":
        return "Would you rather activate your plan first, or start by building the partner side?"
    if playbook_name == "Partner Playbook":
        return "How many people could you realistically invite to an educational webinar first?"
    if playbook_name == "Referral Playbook":
        return "Which channel would you use first: WhatsApp, social media, or direct calls?"
    if playbook_name == "Webinar Invitation Playbook":
        return "Should we position the webinar for you personally, or for people you want to invite?"
    if playbook_name == "Objection Playbook":
        return "What would you want clarified before you feel comfortable moving forward?"
    if playbook_name == "Profit Explanation Playbook":
        return "Do you want me to connect this to your exact starting amount?"
    if playbook_name == "Investment Playbook" and amount:
        return "Which option feels most suitable for your current budget?"
    if amount and referral_count:
        return "Does that combined investor and partner route fit what you are trying to build?"
    if amount:
        return "Can you see yourself starting from that range?"
    return "Which option feels most suitable for your goal right now?"


def analyze_sales_pipeline(text: str, memory: dict[str, Any]) -> dict[str, Any]:
    intents = detect_intents(text)
    objections = detect_objection_categories(text)
    memory_updates = extract_memory_signals(text)
    working_memory = {**memory, **memory_updates}
    scores = calculate_scores(text, working_memory, intents, objections)
    stage = detect_stage(text, working_memory, intents, scores)
    playbook_name = select_playbook(intents, stage, working_memory, objections)
    amount = extract_investment_amount(text) or parse_amount_label(working_memory.get("preferred_investment_range"))
    comparison = comparison_summary(extract_comparison_amounts(text))
    finance = financial_summary(working_memory, amount) if any(intent in intents for intent in ["Profit Question", "Deposit", "Investment Interest", "Comparison"]) else None
    recommendation = build_recommendation(working_memory, amount, stage)
    if comparison:
        recommendation = "Between those options, start with the range you can evaluate calmly and only upgrade after you understand the product, withdrawal process, and risk."
    return {
        "sales_stage_v4": stage,
        "detected_intents_v4": intents,
        "objection_categories": objections,
        "sales_memory_updates": memory_updates,
        "opportunity_scores": scores,
        "selected_playbook": playbook_name,
        "playbook": PLAYBOOKS[playbook_name],
        "recommendation": recommendation,
        "financial_summary": finance,
        "comparison_summary": comparison,
        "micro_close": micro_close_for(playbook_name, working_memory),
    }


def apply_sales_pipeline(memory: dict[str, Any], pipeline: dict[str, Any]) -> None:
    memory["sales_stage_v4"] = pipeline["sales_stage_v4"]
    memory["detected_intents_v4"] = pipeline["detected_intents_v4"]
    memory["objection_categories"] = pipeline["objection_categories"]
    memory["opportunity_scores"] = pipeline["opportunity_scores"]
    memory["selected_playbook"] = pipeline["selected_playbook"]
    memory["playbook_goal"] = pipeline["playbook"]["goal"]
    memory["recommendation"] = pipeline["recommendation"]
    memory["financial_summary"] = pipeline.get("financial_summary")
    memory["comparison_summary"] = pipeline.get("comparison_summary")
    memory["micro_close"] = pipeline["micro_close"]
    for key, value in (pipeline.get("sales_memory_updates") or {}).items():
        memory[key] = value


def sales_pipeline_for_prompt(memory: dict[str, Any]) -> str:
    keys = [
        "sales_stage_v4",
        "detected_intents_v4",
        "objection_categories",
        "opportunity_scores",
        "selected_playbook",
        "playbook_goal",
        "recommendation",
        "micro_close",
        "budget",
        "risk_tolerance",
        "occupation",
        "income_goal",
        "referral_count",
        "interest_in_webinars",
        "activation_status",
        "partner_status",
    ]
    return "\n".join(f"- {key}: {memory.get(key)}" for key in keys if memory.get(key) not in (None, "", [], {}))


def deterministic_playbook_reply(memory: dict[str, Any]) -> str | None:
    financial = memory.get("financial_summary")
    comparison = memory.get("comparison_summary")
    recommendation = memory.get("recommendation")
    close = memory.get("micro_close")
    playbook = memory.get("selected_playbook")
    referral_count = int(memory.get("referral_count") or 0)
    if comparison:
        return f"{comparison}\n\n{recommendation}\n\n{close}"
    if financial and memory.get("selected_playbook") in {"Profit Explanation Playbook", "Investment Playbook"}:
        return f"{financial}\n\n{recommendation}\n\n{close}"
    if playbook == "Referral Playbook":
        count_text = f"{referral_count} possible contacts" if referral_count else "a few interested contacts"
        return (
            f"That is a useful starting point. With {count_text}, your strongest move is not to pressure people, but to invite them into a simple education-first conversation or webinar.\n\n"
            "Even if only a portion become active, you are already building the foundation of a partner pipeline. Start with the people most likely to understand technology, finance, or community-based opportunities.\n\n"
            f"{close}"
        )
    if playbook == "Partner Playbook":
        return (
            "The Partner Program is the business-building side of Aurum. The practical work is learning the ecosystem, introducing interested people, inviting them to education sessions, and supporting follow-up with the team.\n\n"
            f"{recommendation}\n\n{close}"
        )
    if playbook == "Webinar Invitation Playbook":
        return (
            "A webinar is useful when someone needs the full picture without being rushed. It lets them understand the products, opportunity, risks, and partner route in a guided setting.\n\n"
            f"{recommendation}\n\n{close}"
        )
    return None
