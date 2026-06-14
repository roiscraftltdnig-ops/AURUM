from datetime import datetime, timezone
from typing import Any
from app.db.supabase import supabase


REQUIRED_DOCUMENTS = [
    {
        "key": "aurum_conversation_kb_v31",
        "label": "Aurum Conversation Knowledge Base V3.1",
        "portfolio": "Aurum Foundation",
        "filename_terms": ["conversation", "v3"],
    },
    {
        "key": "aurum_overview_pdf",
        "label": "Aurum Overview PDF",
        "portfolio": "Aurum Foundation",
        "filename_terms": ["overview", "aurum"],
    },
    {
        "key": "aurum_presentation_pdf",
        "label": "Aurum Presentation PDF",
        "portfolio": "Aurum Foundation",
        "filename_terms": ["presentation", "aurum"],
    },
    {
        "key": "founder_presentation_pdf",
        "label": "Founder Presentation PDF",
        "portfolio": "Aurum Foundation",
        "filename_terms": ["founder", "presentation"],
    },
    {
        "key": "ex_ai_bot_pdf",
        "label": "EX-AI Bot PDF",
        "portfolio": "Aurum Foundation",
        "filename_terms": ["ex", "ai"],
    },
    {
        "key": "neobank_pdf",
        "label": "NeoBank PDF",
        "portfolio": "Aurum Foundation",
        "filename_terms": ["neo", "bank"],
    },
]

REQUIRED_RESOURCES = [
    {"key": "aurum_intro_video", "label": "Aurum Introduction Video"},
    {"key": "ex_ai_bot_video", "label": "EX-AI Bot Video"},
    {"key": "neobank_video", "label": "NeoBank Video"},
    {"key": "founder_presentation_video", "label": "Founder Presentation Video"},
    {"key": "webinar_video", "label": "Webinar Video"},
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def document_matches(document: dict[str, Any], requirement: dict[str, Any]) -> bool:
    filename = str(document.get("filename") or "").lower()
    metadata = document.get("metadata") or {}
    resource_key = str(metadata.get("resource_key") or "").lower()
    portfolio = str(document.get("portfolio") or "")
    terms = requirement["filename_terms"]
    return (
        portfolio == requirement["portfolio"]
        and (
            requirement["key"] in resource_key
            or (filename.endswith(".pdf") and all(term in filename for term in terms))
        )
    )


async def audit_required_resources() -> dict[str, Any]:
    documents = await supabase.select("knowledge_documents", "order=created_at.desc", limit=1000)
    resources = await supabase.select("community_groups", "is_active=eq.true", limit=1000)
    resource_keys = {row.get("key") for row in resources if row.get("invite_url")}

    missing = []
    for requirement in REQUIRED_DOCUMENTS:
        if not any(document_matches(document, requirement) for document in documents):
            missing.append({**requirement, "type": "document"})

    for requirement in REQUIRED_RESOURCES:
        if requirement["key"] not in resource_keys:
            missing.append({**requirement, "type": "video"})

    return {
        "ok": not missing,
        "checked_at": now_iso(),
        "missing": missing,
        "documents_checked": len(documents),
        "resources_checked": len(resources),
    }


async def create_missing_resource_tasks() -> dict[str, Any]:
    audit = await audit_required_resources()
    if not audit["missing"]:
        return audit

    open_tasks = await supabase.select("admin_tasks", "status=eq.open", limit=500)
    existing_titles = {task.get("title") for task in open_tasks}

    for item in audit["missing"]:
        title = f"Missing resource: {item['label']}"
        if title in existing_titles:
            continue
        await supabase.insert("admin_tasks", {
            "title": title,
            "summary": f"{item['label']} is required for production onboarding but is not currently configured.",
            "priority": "medium",
            "recommended_action": "Upload the approved file or add the correct video URL in the resource center.",
            "status": "open",
        })

    return audit
