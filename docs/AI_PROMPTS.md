# Example AI Prompts

## System Prompt

The production system prompt is implemented in `backend/app/services/ai_orchestrator.py`.

Core principles:

- Act as ROISCRAFT Intelligence, not a chatbot.
- Educate, qualify, route, nurture, and escalate.
- Use Telegram-native brevity and inline destinations.
- Respect progressive disclosure.
- Use memory before sending content.
- Prioritize trusted uploaded knowledge.

## Lead Summary Prompt Pattern

```text
Summarize this Telegram user for an admin.
Include:
- ecosystem interest
- onboarding progress
- engagement signals
- high-intent phrases
- recommended next action
Keep it under 90 words.
```

## RAG Answer Pattern

```text
Answer from trusted context first.
If the context does not confirm a claim, avoid inventing.
End with a destination:
- continue education
- join community
- watch resource
- schedule follow-up
- request VIP/admin handoff
```

## Admin Report Pattern

```text
Create today's ROISCRAFT intelligence report.
Sections:
1. Conversation volume
2. High-intent leads
3. Follow-up queue
4. Most asked questions
5. Portfolio interest trends
6. Recommended admin actions
```

