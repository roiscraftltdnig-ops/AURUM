import re
from typing import Any
from io import BytesIO
from fastapi import HTTPException, Request
from openai import AsyncOpenAI
from app.core.config import get_settings
from app.db.supabase import supabase
from app.services.ai_orchestrator import generate_reply
from app.services.admin_alerts import notify_admins
from app.services.crm import apply_qualification, create_admin_task, get_or_create_user, load_memory, log_message, save_memory, update_user_profile
from app.services.rate_limit import allow_event
from app.services.sales_intelligence import analyze_sales_state, apply_sales_state
from app.services.telegram import telegram


def sanitize_text(text: str) -> str:
    return "".join(char for char in text if char.isprintable() or char in "\n\t").strip()[:4000]


def clean_name(value: str) -> str | None:
    cleaned = re.sub(r"[^A-Za-z '\-]", "", value).strip()
    words = [word for word in cleaned.split() if word.lower() not in {"i", "am", "my", "name", "is"}]
    if not words or words[0].lower() in {"ready", "interested", "new", "beginner"}:
        return None
    return " ".join(words[:2]).title()


def extract_profile_updates(text: str, memory: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    lowered = text.lower().strip()
    updates: dict[str, Any] = {}
    memory_updates: dict[str, Any] = {}

    pending = memory.get("pending_profile_field")
    if pending == "first_name":
        name = clean_name(text)
        if name:
            updates["first_name"] = name
            memory_updates["pending_profile_field"] = None
    if pending == "phone_number":
        phone_match = re.search(r"(?:\+?\d[\d\s().-]{7,}\d)", text)
        if phone_match:
            updates["phone_number"] = re.sub(r"[^\d+]", "", phone_match.group(0))
            memory_updates["pending_profile_field"] = None
    if pending == "country":
        country = re.sub(r"[^A-Za-z '\-]", "", text).strip()
        if 2 <= len(country) <= 40:
            updates["country"] = country.title()
            memory_updates["pending_profile_field"] = None

    explicit_name = re.search(r"(?:my name is|i am|i'm|call me)\s+([A-Za-z][A-Za-z '\-]{1,40})", text, re.IGNORECASE)
    if explicit_name and "first_name" not in updates:
        name = clean_name(explicit_name.group(1))
        if name:
            updates["first_name"] = name

    phone_match = re.search(r"(?:whatsapp|phone|number)?\s*(\+?\d[\d\s().-]{7,}\d)", text, re.IGNORECASE)
    if phone_match:
        updates["phone_number"] = re.sub(r"[^\d+]", "", phone_match.group(1))

    amount_match = re.search(r"(\$?\s*\d[\d,]*(?:\.\d+)?\s*(?:usdt|usd|dollars?)?)", text, re.IGNORECASE)
    if amount_match and any(term in lowered for term in ["range", "budget", "start", "deposit", "invest", "considering", "with"]):
        amount = " ".join(amount_match.group(1).upper().replace("$", "USD ").split())
        memory_updates["preferred_investment_range"] = amount
        updates["investment_intent"] = amount

    country_match = re.search(r"(?:i am from|i'm from|from|in)\s+([A-Za-z][A-Za-z '\-]{1,40})", text, re.IGNORECASE)
    if country_match:
        country = country_match.group(1).strip()
        if country.lower() not in {"aurum", "this", "here"}:
            updates["country"] = country.title()

    if any(term in lowered for term in ["beginner", "new to aurum", "new here", "new investor"]):
        memory_updates["experience_level"] = "Beginner"
    elif any(term in lowered for term in ["experienced investor", "i invest", "investor", "trading experience"]):
        memory_updates["experience_level"] = "Experienced investor"
    elif any(term in lowered for term in ["existing member", "already a member", "aurum member", "i have an account"]):
        memory_updates["experience_level"] = "Existing Aurum member"

    return updates, memory_updates


def sync_profile_memory(memory: dict[str, Any], user: dict[str, Any]) -> None:
    profile = memory.setdefault("profile", {})
    for key in ["first_name", "phone_number", "country"]:
        if user.get(key) and not profile.get(key):
            profile[key] = user[key]


def profile_followup(memory: dict[str, Any], user: dict[str, Any]) -> str | None:
    previous_questions = memory.get("previous_questions") or []
    turn_count = len(previous_questions)
    prompted = memory.setdefault("profile_prompted", {})
    profile = memory.setdefault("profile", {})

    first_name = profile.get("first_name") or user.get("first_name")
    phone_number = profile.get("phone_number") or user.get("phone_number")
    country = profile.get("country") or user.get("country")
    experience = memory.get("experience_level")

    if turn_count >= 2 and not first_name and not prompted.get("first_name"):
        prompted["first_name"] = True
        memory["pending_profile_field"] = "first_name"
        return "By the way, I would love to know your name so I can assist you more personally."
    if turn_count >= 3 and first_name and not phone_number and not prompted.get("phone_number"):
        prompted["phone_number"] = True
        memory["pending_profile_field"] = "phone_number"
        return f"Also, {first_name}, could you share your WhatsApp number? It helps the Aurum team reach you if you need guided assistance or important updates."
    if turn_count >= 4 and phone_number and not country and not prompted.get("country"):
        prompted["country"] = True
        memory["pending_profile_field"] = "country"
        return "Which country are you chatting from? That helps the team understand your location context."
    if turn_count >= 4 and first_name and not experience and not prompted.get("experience_level"):
        prompted["experience_level"] = True
        return "Just so I guide you properly, are you completely new to Aurum, an experienced investor, or already an Aurum member?"
    return None


def remember_retrieval(memory: dict[str, Any], ai: dict[str, Any], message_date: Any) -> None:
    topic = ai.get("topic") or ai.get("portfolio") or "Aurum Foundation"
    memory["last_topic"] = memory.get("current_topic")
    memory["current_topic"] = topic
    memory["current_topic_updated_at"] = message_date
    discussed = memory.setdefault("discussed_products", [])
    if topic not in discussed and topic in {"EX-AI Bot", "NeoBank", "Zeus AI Bot", "Aurum opportunities", "Aurum plans"}:
        discussed.append(topic)

    chunks = ai.get("context") or []
    if not chunks or ai.get("missing_knowledge") or ai.get("missing_video") or ai.get("confidence") == "low":
        return

    viewed_documents = memory.setdefault("viewed_documents", [])
    completed = memory.setdefault("completed_explanations", [])
    seen_document_keys = {
        f"{item.get('portfolio')}::{item.get('filename')}::{item.get('document_id')}"
        for item in viewed_documents
        if isinstance(item, dict)
    }

    for chunk in chunks:
        metadata = chunk.get("metadata") or {}
        entry = {
            "portfolio": metadata.get("portfolio") or ai.get("portfolio"),
            "filename": metadata.get("filename"),
            "document_id": chunk.get("document_id"),
            "last_viewed_at": message_date,
        }
        key = f"{entry.get('portfolio')}::{entry.get('filename')}::{entry.get('document_id')}"
        if key not in seen_document_keys:
            viewed_documents.append(entry)
            seen_document_keys.add(key)

    completed.append({
        "topic": topic,
        "completed_at": message_date,
    })


def remember_sent_resource(memory: dict[str, Any], ai: dict[str, Any], message_date: Any) -> None:
    resource = ai.get("resource_sent")
    if not resource:
        return
    key = resource.get("key")
    resource_type = resource.get("type")
    if resource_type == "video":
        bucket = memory.setdefault("videos_sent", [])
    elif resource_type == "pdf":
        bucket = memory.setdefault("pdfs_viewed", [])
    else:
        bucket = memory.setdefault("resources_sent", [])
    if not any(isinstance(item, dict) and item.get("key") == key for item in bucket):
        bucket.append({"key": key, "url": resource.get("url"), "sent_at": message_date})
    memory["last_topic"] = ai.get("portfolio") or "Aurum Foundation"
    memory["learning_stage"] = memory.get("learning_stage") or "BEGINNER"


def decision_stage_for_score(score: int) -> str:
    if score >= 75:
        return "Decision"
    if score >= 50:
        return "Evaluation"
    if score >= 25:
        return "Confidence"
    if score >= 10:
        return "Understanding"
    return "Awareness"


def handoff_confirmation(user: dict[str, Any], memory: dict[str, Any]) -> str:
    name = (memory.get("profile") or {}).get("first_name") or user.get("first_name")
    prefix = f"Excellent, {name}." if name else "Excellent."
    phone = (memory.get("profile") or {}).get("phone_number") or user.get("phone_number")
    if not phone:
        memory["pending_profile_field"] = "phone_number"
        return (
            f"{prefix} I'll connect you with the Aurum support team so they can guide you through the next steps.\n\n"
            "Please share your WhatsApp number and, if you already know it, the investment range you are considering. That helps the team guide you properly."
        )
    return (
        f"{prefix} I'll connect you with the Aurum support team so they can guide you through the next steps.\n\n"
        "A representative will contact you shortly. While you wait, keep any question you have in mind so the team can address it clearly."
    )


async def build_lead_summary(user: dict[str, Any], memory: dict[str, Any], score: int, latest_text: str) -> str:
    profile = memory.get("profile") or {}
    messages = await supabase.select("messages", f"user_id=eq.{user['id']}&order=created_at.asc", limit=80)
    conversation_lines = []
    for message in messages[-30:]:
        role = message.get("role")
        content = " ".join((message.get("content") or "").split())
        if content:
            conversation_lines.append(f"{role}: {content[:500]}")

    return (
        f"Name: {profile.get('first_name') or user.get('first_name') or 'Not collected'}\n"
        f"Telegram: @{user.get('telegram_username') or user.get('telegram_id')}\n"
        f"WhatsApp: {profile.get('phone_number') or user.get('phone_number') or 'Not collected'}\n"
        f"Country: {profile.get('country') or user.get('country') or 'Not collected'}\n"
        f"Preferred investment range: {memory.get('preferred_investment_range') or user.get('investment_intent') or 'Not collected'}\n"
        f"Conversation stage: {memory.get('conversation_stage') or memory.get('customer_journey_stage') or memory.get('decision_stage') or 'Awareness'}\n"
        f"Intent level: {memory.get('intent_level') or 'Not collected'}\n"
        f"Matched plan: {memory.get('matched_plan') or 'Not collected'} {memory.get('matched_plan_range') or ''}\n"
        f"Concerns/objections: {', '.join(memory.get('concerns') or []) or 'None detected'}\n"
        f"Recommended next action: {memory.get('recommended_next_action') or 'Review and continue guided onboarding'}\n"
        f"Lead score: {score}\n"
        f"Lead temperature: {user.get('lead_temperature') or memory.get('lead_temperature') or 'COLD'}\n"
        f"Products discussed: {', '.join(memory.get('discussed_products') or []) or 'None yet'}\n"
        f"Experience level: {memory.get('experience_level') or 'Not collected'}\n"
        f"Latest user message: {latest_text}\n\n"
        f"Recent conversation history:\n" + "\n".join(conversation_lines)
    )


CALLBACK_PROMPTS = {
    "format:quick": "Give me a quick explanation of ROISCRAFT in a conversational way.",
    "format:video": "I want the short video version. If the video link is not connected yet, explain the short version naturally.",
    "format:presentation": "Walk me through the ROISCRAFT presentation in a conversational way, without dumping everything at once.",
    "route:aurum": "Tell me about Aurum Foundation. I clicked Aurum because I want to understand it.",
    "route:bytnet": "Tell me about Bytnet. I clicked Bytnet because I want to understand it.",
    "explain:how_it_works": "Explain how ROISCRAFT works and what happens after someone shows interest.",
    "aurum:first_time": "I am hearing about Aurum for the first time. Explain it to me clearly.",
    "aurum:seen": "I have already seen something about Aurum. Help me understand the next important thing.",
    "bytnet:overview": "Give me a clear overview of Bytnet and how ROISCRAFT handles it.",
    "explain:risk": "Explain the risk side of ROISCRAFT opportunities in a practical way.",
}


async def configured_resources() -> dict[str, Any]:
    rows = await supabase.select("community_groups", "is_active=eq.true")
    return {row["key"]: row["invite_url"] for row in rows}


async def create_content_task(user: dict[str, Any], title: str, summary: str, recommended_action: str) -> None:
    await supabase.insert("admin_tasks", {
        "user_id": user["id"],
        "title": title,
        "summary": summary,
        "priority": "medium",
        "recommended_action": recommended_action,
        "status": "open",
    })


async def handle_update(request: Request) -> dict[str, Any]:
    settings = get_settings()
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if settings.telegram_webhook_secret and secret != settings.telegram_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid Telegram webhook secret")
    update = await request.json()
    if "callback_query" in update:
        return await handle_callback(update["callback_query"])
    if "message" not in update:
        return {"ok": True, "ignored": True}
    message = update["message"]
    if "text" in message:
        return await handle_message(message)
    if "voice" in message:
        return await handle_voice_message(message)
    if "audio" in message:
        return await handle_audio_message(message)
    return {"ok": True, "ignored": True}


async def handle_callback(callback: dict[str, Any]) -> dict[str, Any]:
    data = callback.get("data", "")
    message = callback.get("message") or {}
    chat_id = message.get("chat", {}).get("id")
    if chat_id is None:
        return {"ok": True, "ignored": True}

    user = await get_or_create_user(callback.get("from", {}), int(chat_id))
    memory = await load_memory(user["id"])
    memory.setdefault("button_history", []).append(data)
    await save_memory(user["id"], memory)
    await telegram.answer_callback(callback.get("id", ""), "Got it")

    if data.startswith("handoff") or data == "route:vip":
        summary = f"User requested {data}. Current stage: {user.get('qualification_stage')}. Engagement score: {user.get('engagement_score', 0)}."
        await create_admin_task(user, summary, "high", "Assign admin for direct Telegram follow-up.")
        await notify_admins("ROISCRAFT action required", summary, exclude_chat_id=chat_id)
        text = (
            "I have flagged this for the ROISCRAFT team.\n\n"
            "To help them follow up properly, please send your name and phone number. "
            "You can also add your email, country, and the opportunity you are interested in."
        )
        await log_message(user["id"], "assistant", text, {"callback_data": data})
        await telegram.send_message(chat_id, text)
        return {"ok": True}

    prompt = CALLBACK_PROMPTS.get(data, "Continue this ROISCRAFT conversation naturally based on what I clicked.")
    callback_message = {"chat": {"id": chat_id}, "from": callback.get("from", {}), "date": message.get("date")}
    return await process_user_text(callback_message, prompt, source="callback", metadata={"callback_data": data})


async def handle_message(message: dict[str, Any]) -> dict[str, Any]:
    return await process_user_text(message, message["text"], source="text")


async def handle_voice_message(message: dict[str, Any]) -> dict[str, Any]:
    voice = message.get("voice") or {}
    return await transcribe_and_process(message, voice.get("file_id"), "voice")


async def handle_audio_message(message: dict[str, Any]) -> dict[str, Any]:
    audio = message.get("audio") or {}
    return await transcribe_and_process(message, audio.get("file_id"), "audio")


async def transcribe_and_process(message: dict[str, Any], file_id: str | None, source: str) -> dict[str, Any]:
    chat_id = message["chat"]["id"]
    if not file_id:
        await telegram.send_message(chat_id, "I can work with voice notes too. This one did not include a usable audio file, so please resend it or type the question.")
        return {"ok": True, "ignored": True}

    settings = get_settings()
    if not settings.openai_api_key:
        await telegram.send_message(chat_id, "I can accept voice notes, but transcription needs the OpenAI key to be active. Please type this one for now.")
        return {"ok": True, "ignored": True}

    try:
        audio_bytes = await telegram.download_file_bytes(file_id)
        if not audio_bytes:
            raise ValueError("Telegram file download returned no bytes")
        file_obj = BytesIO(audio_bytes)
        file_obj.name = "telegram_voice.ogg"
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        transcript = await client.audio.transcriptions.create(model=settings.openai_transcription_model, file=file_obj)
        text = sanitize_text(getattr(transcript, "text", ""))
    except Exception:
        await telegram.send_message(chat_id, "I can listen to voice notes, but this one did not transcribe clearly. Please resend it a little slower, or type the key question.")
        return {"ok": True, "transcription_failed": True}

    if not text:
        await telegram.send_message(chat_id, "I listened, but I could not pick out clear words from that note. Send it again or type the question and I will continue from there.")
        return {"ok": True, "transcription_empty": True}

    return await process_user_text(message, text, source=source, metadata={"transcribed": True})


async def process_user_text(message: dict[str, Any], raw_text: str, source: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    chat_id = message["chat"]["id"]
    telegram_id = str(message.get("from", {}).get("id", chat_id))
    if not await allow_event(f"telegram:user:{telegram_id}", limit=18, window_seconds=60):
        await telegram.send_message(chat_id, "You are moving quickly. I am pausing for a moment so the ROISCRAFT team can keep this channel high-signal.")
        return {"ok": True, "rate_limited": True}
    user = await get_or_create_user(message.get("from", {}), chat_id)
    text = sanitize_text(raw_text)
    if not text:
        return {"ok": True, "ignored": True}
    memory = await load_memory(user["id"])
    sync_profile_memory(memory, user)
    memory.setdefault("previous_questions", []).append(text)
    memory["previous_questions"] = memory["previous_questions"][-20:]
    memory["last_message_at"] = message.get("date")
    profile_updates, memory_updates = extract_profile_updates(text, memory)
    if profile_updates:
        updated_user = await update_user_profile(user["id"], profile_updates)
        user = {**user, **updated_user}
        sync_profile_memory(memory, user)
    for key, value in memory_updates.items():
        if value is None:
            memory.pop(key, None)
        else:
            memory[key] = value
    sync_profile_memory(memory, user)
    sales_analysis = analyze_sales_state(text, memory, int(user.get("engagement_score") or 0))
    apply_sales_state(memory, sales_analysis, text, int(user.get("engagement_score") or 0))
    if source in {"voice", "audio"}:
        memory["voice_interaction_enabled"] = True
        text_for_ai = f"The user sent a Telegram {source} note. Transcription: {text}"
    else:
        text_for_ai = text
    resources = await configured_resources()
    await log_message(user["id"], "user", text, {"source": source, **(metadata or {})})
    ai = await generate_reply(text_for_ai, memory, resources, int(user.get("engagement_score") or 0))
    remember_retrieval(memory, ai, message.get("date"))
    remember_sent_resource(memory, ai, message.get("date"))
    new_score = await apply_qualification(user["id"], int(user.get("engagement_score") or 0), ai["qualification"])
    memory["lead_score"] = new_score
    if new_score >= 71:
        memory["customer_journey_stage"] = "High-intent investor"
    elif new_score >= 50:
        memory["customer_journey_stage"] = "Interested prospect"
    elif new_score >= 31:
        memory["customer_journey_stage"] = "Learning and exploring"
    elif memory.get("experience_level") == "Existing Aurum member":
        memory["customer_journey_stage"] = "Existing member"
    else:
        memory["customer_journey_stage"] = "Curious visitor"
    memory["decision_stage"] = decision_stage_for_score(new_score)
    high_intent_alert_needed = new_score >= 80 and not memory.get("high_intent_alert_sent")
    if ai["qualification"].escalation_required:
        ai["text"] = handoff_confirmation(user, memory)
    else:
        followup = profile_followup(memory, user)
        if followup and not ai["text"].strip().endswith("?"):
            ai["text"] = f"{ai['text']}\n\n{followup}"
    memory["last_assistant_asked_question"] = ai["text"].strip().endswith("?")
    memory["last_assistant_message_preview"] = ai["text"][:240]
    await log_message(user["id"], "assistant", ai["text"], {
        "retrieved_chunks": ai["context"],
        "retrieved_sources": ai.get("source_labels", []),
        "confidence": ai.get("confidence"),
        "confidence_score": ai.get("confidence_score"),
        "missing_knowledge": ai.get("missing_knowledge", False),
        "missing_video": ai.get("missing_video", False),
        "missing_resource": ai.get("missing_resource"),
        "lead_score": new_score,
    })
    await save_memory(user["id"], memory)
    await telegram.send_message(chat_id, ai["text"])
    if ai.get("missing_knowledge"):
        missing_resource = ai.get("missing_resource")
        title = f"Content review: {missing_resource}" if missing_resource else "Content review request"
        summary = f"{title} requested by @{user.get('telegram_username') or user.get('telegram_id')}: {text}"
        await create_content_task(user, title, summary, "Upload or configure the relevant Aurum PDF, presentation, FAQ, transcript, or onboarding document, then retest the bot answer.")
        await notify_admins("Aurum content review", summary, exclude_chat_id=chat_id)
    if ai.get("missing_video"):
        missing_resource = ai.get("missing_resource") or "intro_video"
        summary = f"Media review '{missing_resource}' requested by @{user.get('telegram_username') or user.get('telegram_id')}: {text}"
        await create_content_task(user, f"Media review: {missing_resource}", summary, "Add the requested media URL in the admin resource center and retest the request.")
        await notify_admins("Aurum media review", summary, exclude_chat_id=chat_id)
    if ai["qualification"].escalation_required or high_intent_alert_needed:
        summary = await build_lead_summary(user, memory, new_score, text)
        await create_admin_task(user, summary, "high", "Review conversation, collect contact details, and route into VIP/investor onboarding.")
        await notify_admins("High-intent investor signal", summary, exclude_chat_id=chat_id)
        memory["high_intent_alert_sent"] = True
        await save_memory(user["id"], memory)
    return {"ok": True}
