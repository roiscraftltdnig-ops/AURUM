from collections import Counter, defaultdict
from datetime import datetime, timezone
from textwrap import wrap
from typing import Any

from app.core.config import get_settings
from app.db.supabase import supabase
from app.services.telegram import telegram


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _top_lines(counter: Counter, empty: str) -> str:
    if not counter:
        return empty
    return "\n".join(f"{index}. {label} ({count})" for index, (label, count) in enumerate(counter.most_common(8), start=1))


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_pdf(title: str, lines: list[str]) -> bytes:
    printable_lines: list[str] = []
    for raw_line in [title, "", *lines]:
        line = _text(raw_line)
        if not line:
            printable_lines.append("")
            continue
        for part in wrap(line, width=92) or [""]:
            printable_lines.append(part)

    pages = [printable_lines[index:index + 52] for index in range(0, len(printable_lines), 52)] or [[]]
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",  # Filled after page object ids are known.
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    page_ids: list[int] = []
    for page_lines in pages:
        content_lines = ["BT", "/F1 10 Tf", "50 790 Td", "14 TL"]
        for line in page_lines:
            if line:
                content_lines.append(f"({_pdf_escape(line)}) Tj")
            content_lines.append("T*")
        content_lines.append("ET")
        stream = "\n".join(content_lines).encode("latin-1", "replace")
        page_id = len(objects) + 1
        content_id = len(objects) + 2
        page_ids.append(page_id)
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>".encode()
        )
        objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode()

    pdf = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode())
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_at = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(f"trailer << /Root 1 0 R /Size {len(objects) + 1} >>\nstartxref\n{xref_at}\n%%EOF\n".encode())
    return bytes(pdf)


async def generate_daily_report() -> dict[str, Any]:
    today = datetime.now(timezone.utc).date().isoformat()
    metrics = await supabase.rpc("dashboard_metrics", {})
    users = await supabase.select("users", "order=last_seen_at.desc", limit=5000)
    memories = await supabase.select("user_memory", "order=updated_at.desc", limit=5000)
    tasks = await supabase.select("admin_tasks", "status=eq.open&order=created_at.desc", limit=50)
    messages = await supabase.select("messages", "order=created_at.desc", limit=1000)
    user_messages = [message for message in messages if message.get("role") == "user"]
    memory_by_user = {row.get("user_id"): row.get("memory") or {} for row in memories}

    product_interest: Counter[str] = Counter()
    objections: Counter[str] = Counter()
    terms: Counter[str] = Counter()
    ready_count = 0
    conversations_by_user: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for message in reversed(messages):
        if message.get("user_id"):
            conversations_by_user[message["user_id"]].append(message)

    for message in user_messages:
        content = _text(message.get("content")).lower()
        if any(term in content for term in ["ready", "register", "proceed", "connect me", "speak with", "buy credit", "deposit"]):
            ready_count += 1
        for label, terms_list in {
            "EX-AI Bot": ["ex-ai", "ex ai", "exai"],
            "EX-AI Pro": ["ex-ai pro", "ex ai pro"],
            "NeoBank": ["neobank", "neo bank", "wallet", "card"],
            "Zeus AI Bot": ["zeus"],
            "Deposit Plans": ["plan", "minimum", "deposit", "start with", "100 usdt"],
            "Withdrawals": ["withdraw", "withdrawal"],
        }.items():
            if any(term in content for term in terms_list):
                product_interest[label] += 1
        for label, terms_list in {
            "Risk concern": ["risk", "lose", "safe", "guarantee", "afraid"],
            "Trust concern": ["scam", "real", "legit", "trust"],
            "Profit expectation": ["profit", "return", "earn", "roi"],
            "Withdrawal concern": ["withdraw", "cash out"],
        }.items():
            if any(term in content for term in terms_list):
                objections[label] += 1
        for word in content.split():
            cleaned = "".join(char for char in word if char.isalnum())
            if len(cleaned) > 5:
                terms[cleaned] += 1

    cold_count = sum(1 for user in users if user.get("lead_temperature") == "COLD")
    warm_count = sum(1 for user in users if user.get("lead_temperature") == "WARM")
    hot_count = sum(1 for user in users if user.get("lead_temperature") == "HOT")
    hot_users = [user for user in users if user.get("lead_temperature") == "HOT" or int(user.get("engagement_score") or 0) >= 80]
    user_type_counts: Counter[str] = Counter(
        str(memory_by_user.get(user.get("id"), {}).get("user_type") or "undetermined")
        for user in users
    )
    stage_counts: Counter[str] = Counter(
        str(memory_by_user.get(user.get("id"), {}).get("display_conversation_stage") or user.get("qualification_stage") or "Unknown")
        for user in users
    )
    high_partner_count = sum(
        1 for user in users
        if memory_by_user.get(user.get("id"), {}).get("user_type") == "partner"
        and (user.get("lead_temperature") == "HOT" or int(user.get("engagement_score") or 0) >= 50)
    )
    high_investor_count = sum(
        1 for user in users
        if memory_by_user.get(user.get("id"), {}).get("user_type") == "investor"
        and (user.get("lead_temperature") == "HOT" or int(user.get("engagement_score") or 0) >= 50)
    )
    high_hybrid_count = sum(
        1 for user in users
        if memory_by_user.get(user.get("id"), {}).get("user_type") == "hybrid"
        and (user.get("lead_temperature") == "HOT" or int(user.get("engagement_score") or 0) >= 50)
    )

    interests = _top_lines(product_interest, "No clear product interest yet.")
    objection_lines = _top_lines(objections, "No common objections yet.")
    stage_lines = _top_lines(stage_counts, "No conversation stages recorded yet.")
    top_questions = ", ".join(word for word, _count in terms.most_common(8)) or "No dominant question themes yet."
    hot_lines = "\n".join(
        f"- @{user.get('telegram_username') or user.get('telegram_id')}: score {user.get('engagement_score', 0)}, type {memory_by_user.get(user.get('id'), {}).get('user_type') or 'undetermined'}, stage {memory_by_user.get(user.get('id'), {}).get('display_conversation_stage') or user.get('qualification_stage')}"
        for user in hot_users[:12]
    ) or "- No high-intent leads today."
    task_lines = "\n".join(f"- {task['title']}: {task['recommended_action']}" for task in tasks[:12]) or "- No open admin tasks."

    telegram_text = (
        f"*Daily Aurum AI Report*\n"
        f"Date: {today}\n\n"
        f"Total users: {metrics.get('total_users', len(users)) if isinstance(metrics, dict) else len(users)}\n"
        f"Active users: {metrics.get('active_users', 0) if isinstance(metrics, dict) else 0}\n"
        f"New/high-intent follow-up items: {ready_count + len(tasks)}\n\n"
        f"Cold leads: {cold_count}\n"
        f"Warm leads: {warm_count}\n"
        f"Hot leads: {hot_count}\n\n"
        f"Investor leads: {user_type_counts.get('investor', 0)} total / {high_investor_count} warm-hot\n"
        f"Partner leads: {user_type_counts.get('partner', 0)} total / {high_partner_count} warm-hot\n"
        f"Hybrid leads: {user_type_counts.get('hybrid', 0)} total / {high_hybrid_count} warm-hot\n\n"
        f"*Top interests*\n{interests}\n\n"
        f"*Conversation stages*\n{stage_lines}\n\n"
        f"*Common objections*\n{objection_lines}\n\n"
        f"*Action queue*\n{task_lines}\n\n"
        f"*High-intent leads*\n{hot_lines}\n\n"
        f"*Question themes*\n{top_questions}"
    )

    pdf_lines = [
        f"Date: {today}",
        f"Total users: {len(users)}",
        f"User messages reviewed: {len(user_messages)}",
        f"Cold/Warm/Hot: {cold_count}/{warm_count}/{hot_count}",
        f"Investor/Partner/Hybrid leads: {user_type_counts.get('investor', 0)}/{user_type_counts.get('partner', 0)}/{user_type_counts.get('hybrid', 0)}",
        f"Warm-hot investor/partner/hybrid: {high_investor_count}/{high_partner_count}/{high_hybrid_count}",
        "",
        "Top interests:",
        interests,
        "",
        "Conversation stages:",
        stage_lines,
        "",
        "Common objections:",
        objection_lines,
        "",
        "Open action queue:",
        task_lines,
        "",
        "Conversation detail:",
    ]
    for user in users[:200]:
        user_memory = memory_by_user.get(user.get("id"), {})
        identity = f"@{user.get('telegram_username')}" if user.get("telegram_username") else user.get("telegram_id")
        pdf_lines.extend([
            "",
            f"User: {identity}",
            f"Name: {_text((user.get('first_name') or '') + ' ' + (user.get('last_name') or '')).strip() or 'Not collected'}",
            f"Phone/WhatsApp: {user.get('phone_number') or 'Not collected'}",
            f"Country: {user.get('country') or 'Not collected'}",
            f"Lead score: {user.get('engagement_score', 0)}",
            f"Interest type: {user_memory.get('user_type') or 'undetermined'}",
            f"Detected intent: {user_memory.get('detected_intent') or 'Not collected'}",
            f"Stage: {user_memory.get('display_conversation_stage') or user.get('qualification_stage')} / {user.get('lead_temperature')}",
            f"Recommended action: {user_memory.get('recommended_next_action') or 'Review and continue guided onboarding'}",
            f"Follow-up required: {user.get('followup_required')}",
            "Recent conversation:",
        ])
        for message in conversations_by_user.get(user["id"], [])[-10:]:
            pdf_lines.append(f"{message.get('role')}: {_text(message.get('content'))[:500]}")
        pdf_lines.append("Recommended action: Follow up directly if score is 80+, HOT, or follow-up is required.")

    filename = f"aurum-daily-report-{today}.pdf"
    return {
        "metrics": {
            **(metrics if isinstance(metrics, dict) else {}),
            "cold_leads": cold_count,
            "warm_leads": warm_count,
            "hot_leads": hot_count,
            "ready_for_followup": ready_count + len(tasks),
            "investor_leads": user_type_counts.get("investor", 0),
            "partner_leads": user_type_counts.get("partner", 0),
            "hybrid_leads": user_type_counts.get("hybrid", 0),
            "conversation_stages": dict(stage_counts.most_common(12)),
            "top_interests": dict(product_interest.most_common(8)),
            "common_objections": dict(objections.most_common(8)),
        },
        "telegram_text": telegram_text,
        "pdf_filename": filename,
        "pdf_bytes": _build_pdf("Daily Aurum AI Conversation Intelligence Report", pdf_lines),
    }


async def send_daily_report_to_admins() -> dict[str, Any]:
    settings = get_settings()
    report = await generate_daily_report()
    targets = [target for target in [settings.admin_chat_id, settings.admin_notification_group] if target]
    for target in targets:
        try:
            await telegram.send_message(target, report["telegram_text"])
            await telegram.send_document_bytes(
                target,
                report["pdf_filename"],
                report["pdf_bytes"],
                caption="Detailed Aurum AI conversation report",
            )
        except Exception:
            continue
    return {key: value for key, value in report.items() if key != "pdf_bytes"}
