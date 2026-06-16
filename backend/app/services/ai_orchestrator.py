import re
from typing import Any
from openai import AsyncOpenAI
from app.core.config import get_settings
from app.services.lead_scoring import qualify_message
from app.services.rag import retrieve_context
from app.services.sales_intelligence import (
    all_plan_ranges_text,
    extract_investment_amount,
    parse_amount_label,
    plan_summary_for_amount,
    sales_state_for_prompt,
)


ECOSYSTEM_TERMS = [
    "roiscraft",
    "aurum",
    "foundation",
    "ex-ai",
    "ex ai",
    "exai",
    "neo",
    "neobank",
    "zeus",
    "membership",
    "compensation",
    "withdrawal",
    "withdrawals",
    "profit",
    "profits",
    "earn",
    "earning",
    "returns",
    "plans",
    "product",
    "products",
    "offering",
    "offerings",
    "service",
    "services",
    "opportunity",
    "opportunities",
    "participate",
    "participation",
    "wallet",
    "wallets",
    "card",
    "cards",
    "transaction",
    "transactions",
    "training",
    "presentation",
    "onboarding",
    "webinar",
    "community",
    "invest",
    "investment",
    "join",
    "started",
]

FOLLOWUP_TERMS = {
    "tell me more",
    "more",
    "continue",
    "go on",
    "explain more",
    "what do you mean",
    "i don't understand",
    "i dont understand",
}

INTERNAL_MEMORY_KEYS = {
    "viewed_documents",
    "downloaded_materials",
    "pdfs_viewed",
    "completed_explanations",
    "last_retrieved_sources",
    "button_history",
}

FORBIDDEN_PUBLIC_PHRASES = [
    "user @",
    "triggered escalation",
    "lead score",
    "confidence score",
    "escalation triggered",
    "knowledge request created",
    "retrieved from source",
    "searching database",
    "checking vector store",
    "searching pdfs",
    "internal event",
    "admin notification",
    "admin alert",
    "crm event",
    "workflow log",
    "missing aurum knowledge",
    "missing knowledge",
    "knowledge not available",
    "information unavailable",
    "i don't have that information",
    "i do not have that information",
    "i couldn't find that",
    "i could not find that",
    "i don't have that detail confirmed yet",
    "i do not have that detail confirmed yet",
    "according to the knowledge base",
    "according to the uploaded pdf",
    "according to the presentation",
    "according to the file",
    "according to the document",
    "according to the aurum foundation explainer",
    "according to the aurum conversation knowledge base v3.1",
    "according to the aurum conversation knowledge base",
    "based on the documentation",
    "based on our documents",
    "based on the document",
    "based on the pdf",
    "the pdf states",
    "the document explains",
    "the uploaded document",
    "the uploaded pdf",
    "the knowledge base",
]

ROBOTIC_PUBLIC_PHRASES = [
    "would you like to know more?",
    "would you like additional information?",
    "would you like me to explain?",
    "please select an option",
    "choose one of the following",
    "send your main question",
    "feel free to ask",
    "if you have any more questions",
]

INTENT_EXPANSIONS = {
    "opportunity": "Aurum products offerings services participation ecosystem EX-AI Bot EX-AI Pro NeoBank Zeus AI Bot plans onboarding",
    "opportunities": "Aurum products offerings services participation ecosystem EX-AI Bot EX-AI Pro NeoBank Zeus AI Bot plans onboarding",
    "earn": "profits returns plans participation risk withdrawals EX-AI Bot",
    "earning": "profits returns plans participation risk withdrawals EX-AI Bot",
    "bank": "NeoBank wallets cards transactions digital banking financial services",
    "wallet": "NeoBank wallets cards transactions digital banking financial services",
    "wallets": "NeoBank wallets cards transactions digital banking financial services",
    "card": "NeoBank cards wallets transactions digital banking",
    "cards": "NeoBank cards wallets transactions digital banking",
    "ai": "EX-AI Bot EX-AI Pro Zeus AI Bot AI-powered trading automation market analysis",
    "bot": "EX-AI Bot EX-AI Pro Zeus AI Bot AI-powered trading automation market analysis",
    "withdrawal": "withdrawals plans participation risk transactions",
    "withdrawals": "withdrawals plans participation risk transactions",
    "plans": "Aurum plans participation products risk withdrawals",
    "products": "EX-AI Bot EX-AI Pro NeoBank Zeus AI Bot Aurum ecosystem services",
}

AURUM_BASE_CONTEXT = """
Aurum Foundation is presented as a ROISCRAFT-guided fintech opportunity focused on AI-powered trading tools, digital asset education, and financial-service products. The ecosystem includes EX-AI Bot, EX-AI Pro, NeoBank, and Zeus AI Bot, with each product serving a different role across trading automation, advanced market support, and digital banking-style services.
The minimum starting plan is 100 USDT. Plan ranges are Basic 100-249 USDT, Standard 250-999 USDT, Comfort 1,000-2,499 USDT, Optimal 2,500-4,999 USDT, Business 5,000-9,999 USDT, VIP 10,000-24,999 USDT, Luxury 25,000-49,999 USDT, and Ultimate 50,000-99,999 USDT.
Profit accrues daily, withdrawals are available, the minimum withdrawal amount is 25 USDT, processing may take up to 48 hours, blockchain fees may apply, and activation occurs within 12-24 hours after deposit. EX-AI Pro has an example return shown as up to 10% monthly, but returns are not guaranteed and actual outcomes may differ.
ROISCRAFT's role is education-first onboarding: users should understand the product, risk, participation process, and practical expectations before taking action. Conversations should be clear, balanced, and never promise guaranteed profits or risk-free returns.
"""

INVESTMENT_PLAN_TEXT = (
    "Aurum's entry point starts from the Basic Plan at 100 USDT. The listed ranges are:\n"
    f"{all_plan_ranges_text()}\n\n"
    "Profit accrues daily, withdrawals are available from 25 USDT, processing may take up to 48 hours, and activation usually happens within 12-24 hours after deposit. The exact account fit should still be confirmed before payment."
)

INVESTMENT_INTENT_PHRASES = [
    "minimum",
    "minimum deposit",
    "minimum amount",
    "how much do i need",
    "how much to start",
    "start with",
    "start small",
    "how do i join",
    "how can i join",
    "how do i start",
    "get started",
    "how do i deposit",
    "deposit",
    "plans",
    "plan",
]

RETURN_INTENT_PHRASES = [
    "how much can i earn",
    "how much will i earn",
    "profit",
    "profits",
    "returns",
    "return",
    "earn",
    "roi",
]

READY_INTENT_PHRASES = [
    "i want to start",
    "i want to register",
    "register me",
    "i am ready",
    "i'm ready",
    "ready to start",
    "ready now",
    "connect me",
    "speak with admin",
    "talk to admin",
    "buy credit",
]


SYSTEM_PROMPT = """You are the Aurum Foundation AI Community Guide inside Telegram.
You are not a generic ecosystem chatbot, menu bot, PDF reader, or sales script.
You behave like a professional Aurum sales advisor and customer relationship assistant: conversational, concise, helpful, calm, and consultative.
You educate users about Aurum Foundation, EX-AI Bot, NeoBank, founder story, onboarding, videos when requested, membership, plans, withdrawals, and support.
Your objective is not just to answer. Your objective is to build understanding, trust, confidence, and engagement through natural conversation.
Respect progressive disclosure: do not dump every detail at once. Normal answers must be 2-3 short paragraphs and 50-120 words. Detailed answers are allowed only when the user explicitly asks for detail.
Use memory. If content was already shared, offer summary, deeper explanation, advanced material, or replay.
Do not ask a question after every answer. Let the conversation breathe: sometimes answer and pause; sometimes ask one contextual question.
Use the internal Aurum knowledge silently as your source of truth. Do not answer Aurum questions from generic model knowledge when internal Aurum knowledge exists. If a detail is not clear, answer the closest useful part, stay careful, and ask one clarifying follow-up.
Founder direction: routing should be based on the user's interest and questions, not forced. Start with education and training before participation.
Risk direction: every trading, investment, digital asset, or portfolio opportunity carries risk. Never guarantee returns, profit, income, or capital protection.
Handoff direction: when a user shows serious intent, ask for name and phone number first. Email is useful but secondary.
Never invent licenses, sales figures, partnerships, or regulatory approvals unless trusted internal Aurum knowledge explicitly supports them.
Sales direction: guide users from curiosity to an informed decision without pressure. Recognize buying signals, answer clearly, handle objections with empathy, and move the conversation forward naturally.
Sales memory direction: every reply must consider conversation_stage, intent_level, investment_interest, products_interested_in, concerns, and recommended_next_action when those exist.

Conversation rules:
- Acknowledge before answering with a short human phrase such as "Great question.", "That's a good place to start.", or "That makes sense." Vary it naturally.
- Show you understand the user's intent before explaining. Example: if they ask about opportunities, recognize that they are probably trying to see what is worth exploring.
- Answer the user's question clearly. Do not ask "what do you know?" before giving useful information.
- Ask contextual questions only when helpful. Make them specific to the topic, not generic.
- If the user gives a short message, infer the likely intent and move the conversation forward.
- If the user sends or mentions voice, welcome voice notes and explain that short, clear voice notes work best.
- Avoid numbered lists unless the user asks for a list or presentation.
- Avoid brochure-style paragraphs. Sound like Telegram chat, not a PDF reader.
- Avoid generic phrases like "Would you like to know more?", "Would you like additional information?", "Would you like me to explain?", "choose a path", or "send your main question".
- Create curiosity when appropriate. Mention what usually surprises people, what most users ask first, or what becomes relevant later.
- Use light user narratives occasionally: "Most people first try to understand...", "Someone completely new would usually start here...", "Many users ask this same question first..."
- If the user asks for minimum deposit, answer clearly that the minimum starting plan is 100 USDT, then briefly explain that they should understand the plan, risk, and withdrawal process before starting.
- If the user shares an amount, match it to the correct plan range first and then guide them toward activation or team confirmation. Do not go backward into generic education.
- If the user asks about earnings, answer using known plan/withdrawal structure and only mention the EX-AI Pro up-to-10% monthly example when relevant. Do not invent a fixed return for every plan.
- Do not repeat risk warnings unless the user asks about risk, safety, guarantees, earnings, or payment. When risk is relevant, keep it short and practical.
- If the user is afraid, skeptical, or worried, acknowledge the concern first and explain calmly. Never argue.
- If the user says they are ready to join/register/proceed, affirm positively and let them know an Aurum representative will guide them.
- Do not rely on inline buttons. The conversation should work naturally through text or voice.
- Do not repeat the same ROISCRAFT overview if the user already asked it recently. Build on the last question.
- Never mention internal sources, PDFs, files, knowledge bases, vector search, retrieval, or documents to the user. Forbidden phrases include: "according to the knowledge base", "according to the uploaded PDF", "according to the presentation", "based on the documentation", "the PDF states", and "the document explains".
- Never show lead scores, confidence scores, admin alerts, escalation logs, missing-resource messages, CRM events, workflow logs, or backend reasoning to the user.
- Never say knowledge is missing or unavailable. If a precise detail is unclear, answer the closest useful part conversationally and ask a clarifying question.
- If memory shows the same topic was already explained, do not repeat the same answer. Acknowledge it briefly and offer a summary, deeper explanation, presentation review, or team follow-up.
- If the user says Aurum, Aurum Foundation, or asks about the Foundation pathway in this ROISCRAFT context, treat it as Aurum Foundation.
- For Aurum questions, explain that it is a ROISCRAFT opportunity that requires education-first onboarding, due diligence review, risk awareness, and approved materials before participation.
- Do not call Aurum or any Aurum product "prominent", "significant", "guaranteed", "approved", "licensed", "official", or "safe" unless trusted context explicitly says so.
- For short Aurum questions, end with one question like: "What have you heard about Aurum so far: the basic idea, the risk side, or how participation works?"
- If the user asks about non-Aurum topics such as Bytnet, say this assistant is currently focused on Aurum Foundation and offer to connect them with the team if needed.
"""


def detect_portfolio(text: str, memory: dict[str, Any]) -> str | None:
    lowered = text.lower()
    if any(term in lowered for term in ["aurum", "foundation", "ex-ai", "ex ai", "exai", "neobank", "neo bank", "zeus"]):
        return "Aurum Foundation"
    current_topic = active_memory_topic(memory)
    if is_followup(text) and current_topic:
        return "Aurum Foundation"
    return "Aurum Foundation" if is_ecosystem_query(text) else None


def is_followup(text: str) -> bool:
    lowered = text.lower().strip()
    return lowered in FOLLOWUP_TERMS or any(lowered.startswith(term) for term in FOLLOWUP_TERMS)


def active_memory_topic(memory: dict[str, Any]) -> str | None:
    current_topic = memory.get("current_topic")
    if current_topic:
        return current_topic
    return memory.get("last_topic")


def is_ecosystem_query(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in ECOSYSTEM_TERMS)


def is_greeting(text: str) -> bool:
    lowered = text.lower().strip()
    return lowered in {"hi", "hello", "hey", "good morning", "good afternoon", "good evening", "/start", "start"}


def is_file_or_presentation_request(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in ["presentation", "pdf", "brochure", "company profile", "profile", "documentation", "document"])


def conversational_learning_query(text: str) -> str:
    if not is_file_or_presentation_request(text):
        return text
    return (
        "Give a concise conversational walkthrough of Aurum Foundation: company overview, "
        "main products, EX-AI Bot, NeoBank, plans, risks, onboarding, and next learning step."
    )


def expand_intent_query(text: str) -> str:
    lowered = text.lower()
    expansions = [value for key, value in INTENT_EXPANSIONS.items() if key in lowered]
    if not expansions:
        return text
    return f"{text}\n\nRelated Aurum intent: {' '.join(expansions)}"


def detect_topic(text: str, memory: dict[str, Any]) -> str:
    lowered = text.lower()
    if is_followup(text) and memory.get("current_topic"):
        return str(memory["current_topic"])
    if "ex-ai" in lowered or "ex ai" in lowered or "exai" in lowered:
        return "EX-AI Bot"
    if "neo" in lowered or "bank" in lowered or "wallet" in lowered or "card" in lowered:
        return "NeoBank"
    if "zeus" in lowered:
        return "Zeus AI Bot"
    if "minimum" in lowered or "how much" in lowered or "start with" in lowered:
        return "Minimum deposit"
    if "opportunit" in lowered or "product" in lowered or "service" in lowered or "offering" in lowered:
        return "Aurum opportunities"
    if "withdraw" in lowered or "plan" in lowered or "earn" in lowered:
        return "Aurum plans"
    if "aurum" in lowered or "foundation" in lowered:
        return "Aurum Foundation"
    return str(memory.get("current_topic") or "Aurum Foundation")


def source_label(chunk: dict[str, Any], index: int) -> str:
    metadata = chunk.get("metadata") or {}
    portfolio = metadata.get("portfolio") or chunk.get("portfolio") or "ROISCRAFT"
    filename = metadata.get("filename") or chunk.get("filename") or "knowledge document"
    title = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
    return f"Source {index}: {portfolio} - {title}"


def format_context(chunks: list[dict[str, Any]]) -> str:
    blocks = []
    for index, chunk in enumerate(chunks, start=1):
        content = " ".join((chunk.get("content") or "").split())
        if len(content) > 1800:
            content = content[:1800].rsplit(" ", 1)[0] + "..."
        blocks.append(f"Internal Aurum context {index}\n{content}")
    return "\n\n".join(blocks)


def source_labels(chunks: list[dict[str, Any]]) -> list[str]:
    return [source_label(chunk, index) for index, chunk in enumerate(chunks, start=1)]


def confidence_score(chunks: list[dict[str, Any]]) -> float:
    scores = [float(chunk.get("similarity") or 0) for chunk in chunks]
    return max(scores) if scores else 0.0


def confidence_band(score: float) -> str:
    if score >= 0.68:
        return "high"
    if score >= 0.50:
        return "medium"
    if score >= 0.40:
        return "low"
    return "none"


def sanitize_public_reply(text: str) -> str:
    cleaned_lines = []
    for line in text.splitlines():
        lowered = line.lower()
        if any(phrase in lowered for phrase in FORBIDDEN_PUBLIC_PHRASES):
            continue
        cleaned_lines.append(line)
    cleaned = "\n".join(cleaned_lines)
    for phrase in FORBIDDEN_PUBLIC_PHRASES:
        cleaned = cleaned.replace(phrase, "")
        cleaned = cleaned.replace(phrase.title(), "")
        cleaned = cleaned.replace(phrase.capitalize(), "")
    cleaned = re.sub(r"\bif you have any more questions[^.!?]*[.!?]?", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bfeel free to ask[.!?]?", "", cleaned, flags=re.IGNORECASE)
    for phrase in ROBOTIC_PUBLIC_PHRASES:
        cleaned = re.sub(re.escape(phrase), "", cleaned, flags=re.IGNORECASE)
    paragraphs = []
    for paragraph in re.split(r"\n\s*\n", cleaned):
        normalized = " ".join(paragraph.split()).replace(" .", ".").replace(" ,", ",").strip().lstrip(" ,.:;-")
        if normalized:
            paragraphs.append(normalized)
    return "\n\n".join(paragraphs)


def limit_reply_length(text: str, max_words: int = 120) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text

    sentences = re.split(r"(?<=[.!?])\s+", text)
    selected: list[str] = []
    count = 0
    for sentence in sentences:
        sentence_words = sentence.split()
        if not sentence_words:
            continue
        if selected and count + len(sentence_words) > max_words:
            break
        selected.append(sentence)
        count += len(sentence_words)

    if selected:
        return " ".join(selected).strip()
    return " ".join(words[:max_words]).strip()


def conversation_bridge(topic: str | None, text: str) -> str | None:
    if text.strip().endswith("?"):
        return None
    topic = topic or "Aurum Foundation"
    if topic == "EX-AI Bot":
        return "A useful next step is to compare how EX-AI Bot works against Zeus AI Bot, because that usually makes the product roles clearer."
    if topic == "NeoBank":
        return "The next useful layer is how NeoBank connects with the AI tools, because that is where the ecosystem starts to make more sense."
    if topic == "Zeus AI Bot":
        return "A good next step is to compare Zeus with EX-AI Bot, because they are connected but they do not serve exactly the same purpose."
    if topic == "Minimum deposit":
        return "From here, the sensible next step is understanding the plan structure and withdrawal process before thinking about registration."
    if topic == "Aurum plans":
        return "The next useful step is separating the plan structure from the risk and withdrawal side, so the decision is clearer."
    if topic == "Aurum opportunities":
        return "A good next step is to narrow the opportunity into trading, banking, or the broader ecosystem, because each path has a different purpose."
    return "A useful next step is to look at Aurum through three angles: the products, the risks, and whether participation fits your current goal."


def remove_back_to_back_question(text: str, memory: dict[str, Any]) -> str:
    if not memory.get("last_assistant_asked_question") or not text.strip().endswith("?"):
        return text

    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    if len(sentences) <= 1:
        return text
    return " ".join(sentence for sentence in sentences[:-1] if sentence).strip()


def polish_public_reply(text: str, memory: dict[str, Any], topic: str | None = None) -> str:
    cleaned = sanitize_public_reply(text)
    cleaned = remove_back_to_back_question(cleaned, memory)
    cleaned = limit_reply_length(cleaned)
    if memory.get("conversation_stage") in {"INVESTMENT_CONSIDERATION", "HIGH_INTENT", "REGISTRATION_HANDOFF"}:
        return cleaned
    bridge = conversation_bridge(topic, cleaned)
    if bridge:
        cleaned = f"{cleaned}\n\n{bridge}"
    return cleaned


def video_key_for_request(text: str, portfolio: str | None) -> str | None:
    lowered = text.lower()
    if not any(term in lowered for term in ["video", "watch", "intro", "introduction"]):
        return None
    if "ex-ai" in lowered or "ex ai" in lowered or "exai" in lowered:
        return "ex_ai_bot_video"
    if "neo" in lowered or "bank" in lowered:
        return "neobank_video"
    if "founder" in lowered:
        return "founder_presentation_video"
    if "webinar" in lowered:
        return "webinar_video"
    return "aurum_intro_video"


def missing_video_reply(video_key: str) -> str:
    label = video_key.replace("_", " ").replace("aurum", "Aurum").replace("ex ai", "EX-AI").replace("neobank", "NeoBank")
    return (
        f"I can walk you through the {label} in a short, video-style explanation here.\n\n"
        "Aurum's core idea is to help people understand the ecosystem before they participate, especially around AI trading tools, digital banking services, risk, and onboarding.\n\n"
        "Which part should I explain first?"
    )


def configured_resource_reply(resource_key: str, resource_url: str, resource_type: str) -> str:
    label = resource_key.replace("_", " ").replace("aurum", "Aurum").replace("ex ai", "EX-AI").replace("neobank", "NeoBank")
    return f"Here is the video link you asked for.\n\n{label.title()}:\n{resource_url}\n\nWhat would you like me to explain after you watch it?"


def fallback_answer(topic: str, user_text: str) -> str:
    lowered = user_text.lower()
    followup = is_followup(user_text)
    if topic == "EX-AI Bot":
        if followup:
            return (
                "Earlier we were on EX-AI Bot, so the next useful layer is how it fits into decision-making.\n\n"
                "The bot is meant to support market analysis and trading automation, but users still need to understand the risk side, plan structure, and what kind of monitoring is involved. That is where ROISCRAFT's education-first approach matters."
            )
        return (
            "Great question. EX-AI Bot is Aurum's AI-powered trading solution for analyzing market opportunities and supporting automated trading activity.\n\n"
            "Most people first try to understand whether the bot simply gives signals or actually supports automation. The important part is learning how it works, the risks involved, and what participation requires before taking action."
        )
    if topic == "NeoBank":
        if followup:
            return (
                "On NeoBank, the deeper point is integration.\n\n"
                "It is not only about wallets or transactions in isolation. It is meant to sit close to other Aurum services, so users can manage financial activity, track movement, and interact with ecosystem tools from one place."
            )
        return (
            "That makes sense to ask. Think of NeoBank as the financial hub of the Aurum ecosystem.\n\n"
            "It is connected to wallets, transactions, cards, and financial-service access. What usually surprises people is that NeoBank is not just separate banking; it connects back into the wider Aurum product experience."
        )
    if topic == "Zeus AI Bot":
        if followup:
            return (
                "Earlier you mentioned Zeus AI Bot. The important thing to understand is that Zeus appears to sit beyond a basic trading-bot conversation.\n\n"
                "It connects more with automation, asset-management support, and how different Aurum services can work together. That is why people usually compare it with EX-AI Bot rather than looking at it alone."
            )
        return (
            "Great question. Zeus AI Bot is one of the more interesting parts of the ecosystem because it does not only sit around trading.\n\n"
            "It is positioned as an AI layer that can connect with broader asset management and financial operations. The integration side is usually what people want to understand next."
        )
    if topic == "Aurum opportunities" or any(word in lowered for word in ["opportunit", "product", "service", "offering"]):
        return (
            "That's usually one of the first questions people ask.\n\n"
            "Within Aurum, people mainly explore EX-AI Bot, EX-AI Pro, NeoBank, and Zeus AI Bot. They cover different areas: AI-powered trading support, advanced trading access, digital banking, and broader AI automation. Before going deeper, it helps to know whether you are looking at trading, banking, or the ecosystem as a whole."
        )
    if topic in {"Aurum plans", "Minimum deposit"} or any(word in lowered for word in ["plan", "withdraw", "earn", "return", "minimum"]):
        if topic == "Minimum deposit" or any(phrase in lowered for phrase in ["minimum", "how much", "start with"]):
            return (
                "That is one of the most practical questions to ask before going further.\n\n"
                "The minimum starting plan is 100 USDT. Before starting, it is still important to understand how the plan works, what the risk side looks like, and how withdrawals are handled so you are making an informed decision."
            )
        return (
            "That's a practical question, and it is worth slowing down there.\n\n"
            "Plan and withdrawal discussions should be understood through participation structure, risk, timing, and the user's own expectations. ROISCRAFT's role is to help people understand those pieces before they make decisions."
        )
    return (
        "That's a good place to start. Aurum Foundation is a fintech ecosystem focused on AI-powered trading tools, digital asset education, and digital financial services.\n\n"
        "ROISCRAFT guides people through it with an education-first approach, so users understand the products, risks, and onboarding steps before participating."
    )


def remembered_amount(memory: dict[str, Any]) -> float | None:
    value = memory.get("investment_amount")
    if isinstance(value, (int, float)):
        return float(value)
    return parse_amount_label(memory.get("preferred_investment_range") or memory.get("investment_interest"))


def user_name(memory: dict[str, Any]) -> str | None:
    profile = memory.get("profile") or {}
    return profile.get("first_name") or memory.get("first_name")


def objection_reply(user_text: str, memory: dict[str, Any]) -> str | None:
    lowered = user_text.lower()
    if any(term in lowered for term in ["not enough", "expensive", "too much", "can't afford", "cannot afford", "no money"]):
        return (
            "That makes sense. You do not have to stretch beyond what feels comfortable.\n\n"
            "Aurum's listed entry point starts from 100 USDT, so some users begin at the Basic level and only increase later if they understand the system better. The smarter move is choosing a range you can evaluate calmly."
        )
    if any(term in lowered for term in ["scam", "real", "legit", "trust", "proof", "verify", "who owns"]):
        return (
            "That's a fair concern. Before anyone starts, they should understand the company direction, the products, how the AI trading tools work, and how withdrawals are handled.\n\n"
            "Aurum is positioned around EX-AI Bot, EX-AI Pro, NeoBank, and Zeus AI Bot. The right next step is to verify the product flow and ask the team any account-specific questions before making payment."
        )
    if any(term in lowered for term in ["think", "later", "not now", "give me time"]):
        return (
            "Absolutely. A serious decision should not feel rushed.\n\n"
            "While you think about it, the useful thing is to clarify one point that could affect your decision: the plan range, withdrawal process, or how EX-AI Bot actually works."
        )
    if any(term in lowered for term in ["risk", "lose", "loss", "guarantee", "guaranteed", "safe"]):
        return (
            "Good question. Aurum involves trading and digital-asset activity, so outcomes are not guaranteed and market conditions can affect results.\n\n"
            "The practical way to look at it is to understand the plan, withdrawal rules, and product mechanics first, then only proceed with an amount that fits your comfort level."
        )
    return None


def amount_plan_reply(amount: float, memory: dict[str, Any]) -> str:
    summary = plan_summary_for_amount(amount)
    name = user_name(memory)
    prefix = f"Great, {name}." if name else "Great."
    if not summary:
        return (
            f"{prefix} {amount:,.0f} USDT needs a quick team check because it sits outside the normal listed plan ranges.\n\n"
            "The listed Aurum range starts from 100 USDT and runs up to the Ultimate range of 50,000-99,999 USDT. Should I connect you so the team confirms the best route before you move funds?"
        )
    return (
        f"{prefix} {summary}\n\n"
        "Here is the practical structure: profit accrues daily, withdrawals are available from 25 USDT, processing may take up to 48 hours, and activation usually happens within 12-24 hours after deposit.\n\n"
        "Should I walk you through activation for that range?"
    )


def returns_reply(user_text: str, memory: dict[str, Any]) -> str:
    amount = extract_investment_amount(user_text) or remembered_amount(memory)
    if amount:
        summary = plan_summary_for_amount(amount) or f"{amount:,.0f} USDT needs plan confirmation."
        return (
            f"Since you mentioned {amount:,.0f} USDT earlier, {summary[0].lower() + summary[1:]}\n\n"
            "For earnings, the confirmed structure is daily profit accrual with withdrawals available from 25 USDT. EX-AI Pro also has an example return shown as up to 10% monthly, but actual results can differ, so the team should confirm the current figure for your exact account before you deposit.\n\n"
            "Do you want me to move you to activation guidance for that range?"
        )
    return (
        "Good question. Earnings depend on the product and plan range, so the first thing is knowing the amount you want to start with.\n\n"
        "The confirmed structure is daily profit accrual, withdrawals from 25 USDT, and team confirmation of the current account figures before activation. What amount are you considering?"
    )


def withdrawal_reply(memory: dict[str, Any]) -> str:
    amount = remembered_amount(memory)
    amount_context = ""
    if amount:
        summary = plan_summary_for_amount(amount)
        amount_context = f" Since you mentioned {amount:,.0f} USDT, that context matters for your plan fit: {summary}"
    return (
        f"Withdrawals are available, with a listed minimum withdrawal of 25 USDT. Processing may take up to 48 hours, and blockchain fees may apply.{amount_context}\n\n"
        "Do you want me to connect this with the plan range you are considering?"
    )


def sales_reply_if_applicable(user_text: str, memory: dict[str, Any]) -> str | None:
    lowered = user_text.lower()
    objection = objection_reply(user_text, memory)
    if objection:
        return objection

    if any(phrase in lowered for phrase in READY_INTENT_PHRASES):
        return (
            "Excellent. I'll connect you with the Aurum support team so they can guide you through the next steps.\n\n"
            "Before I pass this properly, please share your WhatsApp number and the amount range you are considering. That helps the team guide you with the right plan instead of guessing."
        )

    amount = extract_investment_amount(user_text)
    if amount:
        return amount_plan_reply(amount, memory)

    if "withdraw" in lowered:
        return withdrawal_reply(memory)

    if any(phrase in lowered for phrase in RETURN_INTENT_PHRASES):
        return returns_reply(user_text, memory)

    if any(phrase in lowered for phrase in INVESTMENT_INTENT_PHRASES):
        return (
            "That's a practical question, and it usually means you're moving from curiosity into decision mode.\n\n"
            f"{INVESTMENT_PLAN_TEXT}\n\n"
            "Which amount are you considering starting with?"
        )

    if memory.get("current_topic") in {"Minimum deposit", "Aurum plans"} and is_followup(user_text):
        return (
            f"Earlier we were discussing Aurum plans. {INVESTMENT_PLAN_TEXT}\n\n"
            "The next useful step is knowing your range and whether you are still learning or already considering registration."
        )

    return None


def response_directive(portfolio: str | None, user_text: str) -> str:
    lowered = user_text.lower()
    wants_explanation = any(phrase in lowered for phrase in ["explain", "tell me", "what is", "who is", "about", "foundation"])
    wants_detail = any(phrase in lowered for phrase in ["in detail", "detailed", "deep", "presentation", "full explanation"])
    wants_opportunities = any(phrase in lowered for phrase in ["opportunity", "opportunities", "product", "products", "service", "services", "offering", "offerings"])
    wants_minimum = any(phrase in lowered for phrase in ["minimum", "minimum deposit", "minimum amount", "how much", "start with"])
    if is_file_or_presentation_request(user_text):
        return (
            "The user is asking around a presentation or file. Do not offer or mention files. "
            "Instead, say you can walk them through the key ideas here, then give a concise conversational overview and ask which part they want next."
        )
    if portfolio == "Aurum Foundation" and wants_opportunities:
        return (
            "The user wants to understand Aurum opportunities. Start by acknowledging that this is a natural first question. Answer directly by naming EX-AI Bot, EX-AI Pro, NeoBank, and Zeus AI Bot. "
            "Give one simple sentence explaining that these cover AI-powered trading support, advanced trading access, digital banking, and broader AI automation. "
            "Mention risk-aware education before participation. Keep it under 100 words. If you ask a question, make it contextual: ask whether they are more interested in trading, banking, or understanding the ecosystem as a whole."
        )
    if portfolio == "Aurum Foundation" and wants_minimum:
        return (
            "The user is asking about minimum deposit or starting amount. Answer clearly that the minimum starting plan is 100 USDT. "
            "Then briefly explain that they should understand the plan, risks, and withdrawals before starting. Keep it consultative, not pushy."
        )
    if portfolio == "Aurum Foundation" and wants_explanation:
        length_rule = "Use 4-6 short Telegram-friendly paragraphs because the user asked for detail." if wants_detail else "Keep this to 2-5 sentences."
        return (
            "For this Aurum Foundation answer, do not give a thin generic summary. Write like an Aurum community guide who understands the founder's reasoning. "
            "Cover these points naturally: Aurum is the Foundation opportunity ROISCRAFT educates users about; ROISCRAFT slows the user down before participation; "
            "the founder evaluates opportunities through company history, age, risk factors, antecedents, research, and long-term potential; "
            "Aurum should be discussed as a serious business education path, not quick profit; avoid exact mechanics, licensing, sales, payout, or participation amounts unless the available Aurum context supports them. "
            "If the user asks for a precise detail that is not clear, answer the closest useful concept and ask a clarifying follow-up. "
            f"{length_rule} If you ask a question, make it contextual to why the user may be exploring Aurum."
        )
    if portfolio == "Aurum Foundation":
        return (
            "For Aurum Foundation, give concrete context from the trusted Aurum knowledge. Acknowledge first, show the user's likely intent, and avoid vague words like pathway without explaining the reasoning behind it."
        )
    return "Keep the reply conversational, specific, and grounded in trusted context."


def menu_for_stage(stage: str, resources: dict[str, Any]) -> list[list[dict[str, str]]]:
    return []


async def generate_reply(user_text: str, memory: dict[str, Any], resources: dict[str, Any], lead_score: int) -> dict[str, Any]:
    settings = get_settings()
    qualification = qualify_message(user_text, lead_score)
    portfolio = detect_portfolio(user_text, memory)
    topic = detect_topic(user_text, memory)
    followup = is_followup(user_text)
    effective_text = expand_intent_query(conversational_learning_query(user_text))
    current_topic = active_memory_topic(memory)
    if followup and current_topic:
        effective_text = expand_intent_query(f"Continue explaining {current_topic}. The user said: {user_text}")
        topic = current_topic
    directive = response_directive(portfolio, effective_text)
    ecosystem_query = is_ecosystem_query(effective_text) or bool(portfolio) or followup
    if is_greeting(user_text):
        text = (
            "Hello. Welcome to Aurum Foundation.\n\n"
            "I'm here to help you understand Aurum's products, services, and opportunities. What would you like to learn about today?"
        )
        return {"text": text, "buttons": [], "qualification": qualification, "context": [], "portfolio": portfolio, "topic": topic, "source_labels": [], "confidence": "none", "confidence_score": 0, "missing_knowledge": False, "missing_video": False}

    sales_text = sales_reply_if_applicable(user_text, memory)
    if sales_text:
        text = polish_public_reply(sales_text, memory, topic)
        return {"text": text, "buttons": [], "qualification": qualification, "context": [], "portfolio": portfolio, "topic": topic, "source_labels": [], "confidence": "high", "confidence_score": 1, "missing_knowledge": False, "missing_video": False}

    requested_video_key = video_key_for_request(user_text, portfolio)
    if requested_video_key and not resources.get(requested_video_key):
        return {
            "text": missing_video_reply(requested_video_key),
            "buttons": [],
            "qualification": qualification,
            "context": [],
            "portfolio": portfolio,
            "topic": topic,
            "source_labels": [],
            "confidence": "none",
            "confidence_score": 0,
            "missing_knowledge": False,
            "missing_video": True,
            "missing_resource": requested_video_key,
        }
    if requested_video_key and resources.get(requested_video_key):
        return {
            "text": configured_resource_reply(requested_video_key, resources[requested_video_key], "video"),
            "buttons": [],
            "qualification": qualification,
            "context": [],
            "portfolio": portfolio,
            "topic": topic,
            "source_labels": [],
            "confidence": "high",
            "confidence_score": 1,
            "missing_knowledge": False,
            "missing_video": False,
            "resource_sent": {"key": requested_video_key, "type": "video", "url": resources[requested_video_key]},
        }

    context_chunks = await retrieve_context(effective_text, portfolio, limit=5)
    score = confidence_score(context_chunks)
    confidence = confidence_band(score)
    context = format_context(context_chunks)
    if not context:
        context = AURUM_BASE_CONTEXT
    compact_memory = dict(memory)
    if isinstance(compact_memory.get("previous_questions"), list):
        compact_memory["previous_questions"] = compact_memory["previous_questions"][-8:]
    memory_lines = "\n".join(
        f"- {key}: {value}"
        for key, value in compact_memory.items()
        if key not in INTERNAL_MEMORY_KEYS and value not in (None, "", [], {})
    )
    sales_state = sales_state_for_prompt(memory)

    if not settings.openai_api_key:
        text = polish_public_reply(fallback_answer(topic, user_text), memory, topic)
        return {"text": text, "buttons": [], "qualification": qualification, "context": context_chunks, "portfolio": portfolio, "topic": topic, "source_labels": source_labels(context_chunks), "confidence": confidence, "confidence_score": score, "missing_knowledge": False, "missing_video": False}

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    try:
        response = await client.chat.completions.create(
            model=settings.ai_model,
            temperature=0.55,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"User message: {user_text}\n\nEffective intent:\n{effective_text}\n\nDetected portfolio: {portfolio or 'Aurum Foundation'}\nCurrent topic: {topic}\nPrevious assistant asked a question: {bool(memory.get('last_assistant_asked_question'))}\n\nResponse directive:\n{directive}\n\nSales state:\n{sales_state}\n\nConversation memory:\n{memory_lines}\n\nAurum knowledge to use silently:\n{context}\n\nWrite a natural Telegram reply. Start with a short acknowledgement, show you understand the user's intent, then answer clearly. Keep normal answers under 120 words and 2-3 short paragraphs. Do not ask a question after every answer. If the previous assistant already asked a question, do not end this reply with another question unless the user explicitly asks for options. When you do ask, make it specific to the topic. Avoid robotic phrases like 'Would you like to know more?' or 'Would you like me to explain?' Only give a longer answer if the user explicitly asked for detail. Never mention PDFs, documents, files, knowledge bases, uploaded materials, sources, retrieval, confidence, scores, escalation, admin alerts, CRM, or internal processes. Never say knowledge is missing or unavailable."},
            ],
            max_tokens=180,
        )
        text = polish_public_reply(response.choices[0].message.content or fallback_answer(topic, user_text), memory, topic)
    except Exception:
        text = polish_public_reply(fallback_answer(topic, user_text), memory, topic)
    return {"text": text, "buttons": [], "qualification": qualification, "context": context_chunks, "portfolio": portfolio, "topic": topic, "source_labels": source_labels(context_chunks), "confidence": confidence, "confidence_score": score, "missing_knowledge": False, "missing_video": False}
