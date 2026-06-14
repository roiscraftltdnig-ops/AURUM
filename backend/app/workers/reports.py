from collections import Counter
from app.db.supabase import supabase


async def generate_daily_report() -> dict[str, str | dict]:
    metrics = await supabase.rpc("dashboard_metrics", {})
    users = await supabase.select("users", "order=last_seen_at.desc", limit=5000)
    hot_users = [user for user in users if user.get("lead_temperature") == "HOT"][:10]
    tasks = await supabase.select("admin_tasks", "status=eq.open&order=created_at.desc", limit=10)
    messages = await supabase.select("messages", "role=eq.user&order=created_at.desc", limit=200)
    terms = Counter()
    product_interest = Counter()
    objections = Counter()
    ready_count = 0
    for message in messages:
        content = message.get("content", "").lower()
        if any(term in content for term in ["ready", "register", "proceed", "connect me", "speak with"]):
            ready_count += 1
        for label, terms_list in {
            "EX-AI Bot": ["ex-ai", "ex ai", "exai"],
            "EX-AI Pro": ["ex-ai pro", "ex ai pro"],
            "NeoBank": ["neobank", "neo bank", "wallet", "card"],
            "Zeus AI Bot": ["zeus"],
            "Deposit Plans": ["plan", "minimum", "deposit", "start with"],
            "Withdrawals": ["withdraw", "withdrawal"],
        }.items():
            if any(term in content for term in terms_list):
                product_interest[label] += 1
        for label, terms_list in {
            "Risk concern": ["risk", "lose", "safe", "guarantee", "afraid"],
            "Trust concern": ["scam", "real", "legit", "trust"],
            "Profit expectation": ["profit", "return", "earn"],
            "Withdrawal concern": ["withdraw", "cash out"],
        }.items():
            if any(term in content for term in terms_list):
                objections[label] += 1
        for word in content.split():
            cleaned = "".join(char for char in word if char.isalnum())
            if len(cleaned) > 5:
                terms[cleaned] += 1
    top_questions = ", ".join(word for word, _count in terms.most_common(8)) or "No dominant question themes yet."
    hot_lines = "\n".join(f"- @{user.get('telegram_username') or user.get('telegram_id')}: score {user.get('engagement_score', 0)}" for user in hot_users) or "- No hot leads today."
    task_lines = "\n".join(f"- {task['title']}: {task['recommended_action']}" for task in tasks) or "- No open admin tasks."
    cold_count = sum(1 for user in users if user.get("lead_temperature") == "COLD")
    warm_count = sum(1 for user in users if user.get("lead_temperature") == "WARM")
    hot_count = sum(1 for user in users if user.get("lead_temperature") == "HOT")
    interests = "\n".join(f"{index}. {label} ({count})" for index, (label, count) in enumerate(product_interest.most_common(5), start=1)) or "No clear product interest yet."
    objection_lines = "\n".join(f"- {label}: {count}" for label, count in objections.most_common(5)) or "- No common objections yet."
    telegram_text = (
        f"*Daily Aurum AI Report*\n\n"
        f"Total conversations/users: {metrics.get('total_users', len(users))}\n"
        f"Active users: {metrics.get('active_users', 0)}\n\n"
        f"Cold leads: {cold_count}\n"
        f"Warm leads: {warm_count}\n"
        f"Hot leads: {hot_count}\n"
        f"Ready for human follow-up: {ready_count + len(tasks)}\n\n"
        f"*Top interests*\n{interests}\n\n"
        f"*Common objections*\n{objection_lines}\n\n"
        f"*Action queue*\n{task_lines}\n\n"
        f"*High-intent leads*\n{hot_lines}\n\n"
        f"*Question themes*\n{top_questions}"
    )
    return {
        "metrics": {
            **(metrics if isinstance(metrics, dict) else {}),
            "cold_leads": cold_count,
            "warm_leads": warm_count,
            "hot_leads": hot_count,
            "ready_for_followup": ready_count + len(tasks),
            "top_interests": dict(product_interest.most_common(8)),
            "common_objections": dict(objections.most_common(8)),
        },
        "telegram_text": telegram_text,
    }
