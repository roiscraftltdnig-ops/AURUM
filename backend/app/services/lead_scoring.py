from dataclasses import dataclass


ESCALATION_TERMS = {
    "speak with someone", "speak to someone", "talk to someone", "speak with the team",
    "talk to the team", "contact me", "call me", "phone call", "human support",
    "admin", "administrator", "account assistance", "direct contact", "requesting contact",
}
CONTACT_TERMS = {"my phone", "my number", "email me", "call me", "whatsapp me", "contact me"}
JOIN_TERMS = {"how to join", "how can i join", "join", "get started", "onboard", "sign up", "how do i start"}
READY_TERMS = {"ready to start", "i am ready", "i'm ready", "ready now", "i want to proceed", "proceed", "let me start"}
REGISTRATION_TERMS = {"register me", "registration", "i want to register", "connect me", "admin assistance", "representative", "agent"}
MINIMUM_DEPOSIT_TERMS = {"minimum deposit", "minimum amount", "least amount", "how much do i need", "how much to start", "start with"}
PLAN_TERMS = {"plan", "plans", "withdrawal", "withdrawals", "earn", "profit", "return", "returns"}
PRODUCT_TERMS = {"product", "products", "opportunity", "opportunities", "service", "services", "offering", "offerings"}
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

    if any(term in lowered for term in BEGINNER_TERMS):
        delta = max(delta, 5)
        reasons.append("Education-stage question")
    if any(term in lowered for term in PRODUCT_TERMS):
        delta = max(delta, 10)
        reasons.append("Product interest")
    if any(term in lowered for term in ["ex-ai", "ex ai", "exai", "neobank", "neo bank", "zeus"]):
        delta = max(delta, 15)
        reasons.append("Specific Aurum product interest")
    if any(term in lowered for term in PLAN_TERMS):
        delta = max(delta, 20)
        reasons.append("Plans or transaction question")
    if any(term in lowered for term in MINIMUM_DEPOSIT_TERMS):
        delta = max(delta, 30)
        reasons.append("Minimum deposit question")
    if any(term in lowered for term in JOIN_TERMS):
        delta = max(delta, 40)
        reasons.append("Join/onboarding question")
    if any(term in lowered for term in READY_TERMS):
        delta = max(delta, 50)
        reasons.append("Ready-to-start signal")
    if any(term in lowered for term in REGISTRATION_TERMS):
        delta = max(delta, 70)
        reasons.append("Registration or admin assistance requested")
    if any(term in lowered for term in ADVANCED_TERMS):
        delta = max(delta, 15)
        reasons.append("Advanced ecosystem vocabulary")
    if any(term in lowered for term in ESCALATION_TERMS):
        delta = max(delta, 70)
        reasons.append("Human support requested")
    if any(term in lowered for term in CONTACT_TERMS):
        delta = max(delta, 70)
        reasons.append("Contact follow-up requested")

    score = min(100, current_score + delta)
    escalation = any(term in lowered for term in ESCALATION_TERMS | CONTACT_TERMS | READY_TERMS | REGISTRATION_TERMS)
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
