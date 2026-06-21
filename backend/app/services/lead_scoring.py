from dataclasses import dataclass
import re


ESCALATION_TERMS = {
    "speak with someone", "speak to someone", "talk to someone", "speak with the team",
    "talk to the team", "contact me", "call me", "phone call", "human support",
    "admin", "administrator", "account assistance", "direct contact", "requesting contact",
}
CONTACT_TERMS = {"my phone", "my number", "email me", "call me", "whatsapp me", "contact me"}
JOIN_TERMS = {"how to join", "how can i join", "join", "get started", "onboard", "sign up", "how do i start", "how do i join"}
READY_TERMS = {"ready to start", "i am ready", "i'm ready", "ready now", "i want to proceed", "proceed", "let me start", "i want to start", "i want to deposit", "buy credit"}
REGISTRATION_TERMS = {"register me", "registration", "i want to register", "connect me", "admin assistance", "representative", "agent", "open account"}
MINIMUM_DEPOSIT_TERMS = {"minimum deposit", "minimum amount", "least amount", "how much do i need", "how much to start", "start with", "start small"}
PLAN_TERMS = {"plan", "plans", "withdrawal", "withdrawals", "earn", "profit", "return", "returns", "deposit", "how much can i earn", "how do i deposit"}
PRODUCT_TERMS = {"product", "products", "opportunity", "opportunities", "service", "services", "offering", "offerings"}
PARTNER_TERMS = {
    "partner", "partner program", "referral", "refer", "commission", "compensation",
    "team building", "build a team", "network", "community", "matching bonus",
    "leadership bonus", "partner rank", "partner level", "webinar",
}
NO_CAPITAL_TERMS = {
    "don't have money", "dont have money", "do not have money", "no money", "no capital",
    "cannot afford", "can't afford", "cant afford", "without investing", "without investment",
}
PARTNER_READY_TERMS = {
    "i want to become a partner", "ready to become a partner", "ready to build a team",
    "i have people interested", "people are interested", "partner registration",
    "register as a partner", "join the partner program", "start my partner journey",
}
HYBRID_TERMS = {
    "invest and refer", "invest and invite", "invest and build a team",
    "investor and partner", "both investor and partner", "invest and become a partner",
}
ADVANCED_TERMS = {"tokenomics", "liquidity", "ecosystem", "governance", "institutional", "strategy"}
BEGINNER_TERMS = {"what is", "explain", "beginner", "new to", "basics", "learn", "crypto", "tell me about"}
GREETING_TERMS = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening", "/start", "start"}


@dataclass
class Qualification:
    stage: str
    lead_temperature: str
    delta: int
    escalation_required: bool
    reasons: list[str]


def qualify_message(text: str, current_score: int = 0) -> Qualification:
    lowered = text.lower().strip()
    reasons: list[str] = []
    delta = 0

    if lowered in GREETING_TERMS or lowered in {"how are you", "how far", "good day"}:
        score = min(100, current_score)
        return Qualification(stage_for_score(score), temperature_for_score(score), 0, False, [])

    def move_to(target_score: int) -> None:
        nonlocal delta
        delta = max(delta, max(0, target_score - current_score))

    if any(term in lowered for term in BEGINNER_TERMS):
        move_to(10)
        reasons.append("Education-stage question")
    if any(term in lowered for term in PRODUCT_TERMS):
        move_to(20)
        reasons.append("Product interest")
    if any(term in lowered for term in PARTNER_TERMS):
        move_to(45)
        reasons.append("Partner-program interest")
    if any(term in lowered for term in NO_CAPITAL_TERMS):
        move_to(45)
        reasons.append("No-capital partner-path signal")
    if any(term in lowered for term in HYBRID_TERMS):
        move_to(85)
        reasons.append("Hybrid investor-and-partner intent")
    if any(term in lowered for term in PARTNER_READY_TERMS):
        move_to(100)
        reasons.append("Ready-to-start partner signal")
    if any(term in lowered for term in ["ex-ai", "ex ai", "exai", "neobank", "neo bank", "zeus"]):
        move_to(30)
        reasons.append("Specific Aurum product interest")
    if any(term in lowered for term in PLAN_TERMS):
        move_to(40)
        reasons.append("Plans or transaction question")
    amount_match = re.search(r"(?:\$|usd\s*|usdt\s*)?\s*(\d[\d,]*(?:\.\d+)?)\s*(?:usdt|usd|dollars?)?", lowered)
    if amount_match and any(term in lowered for term in ["$", "usd", "usdt", "start", "deposit", "invest", "investment", "budget", "capital", "with"]):
        move_to(75)
        reasons.append("Specific investment amount shared")
    if any(term in lowered for term in MINIMUM_DEPOSIT_TERMS):
        move_to(60)
        reasons.append("Minimum deposit question")
    if any(term in lowered for term in JOIN_TERMS):
        move_to(80)
        reasons.append("Join/onboarding question")
    if any(term in lowered for term in READY_TERMS):
        move_to(100)
        reasons.append("Ready-to-start signal")
    if any(term in lowered for term in REGISTRATION_TERMS):
        move_to(100)
        reasons.append("Registration or admin assistance requested")
    if any(term in lowered for term in ADVANCED_TERMS):
        move_to(30)
        reasons.append("Advanced ecosystem vocabulary")
    if any(term in lowered for term in ESCALATION_TERMS):
        move_to(100)
        reasons.append("Human support requested")
    if any(term in lowered for term in CONTACT_TERMS):
        move_to(100)
        reasons.append("Contact follow-up requested")

    score = min(100, current_score + delta)
    escalation = any(term in lowered for term in ESCALATION_TERMS | CONTACT_TERMS | READY_TERMS | REGISTRATION_TERMS | PARTNER_READY_TERMS)
    return Qualification(stage_for_score(score), temperature_for_score(score), delta, escalation, reasons)


def stage_for_score(score: int) -> str:
    if score >= 71:
        return "HIGH_INTENT"
    if score >= 50:
        return "ADVANCED"
    if score >= 31:
        return "INTERMEDIATE"
    return "BEGINNER"


def temperature_for_score(score: int) -> str:
    if score >= 71:
        return "HOT"
    if score >= 31:
        return "WARM"
    return "COLD"
