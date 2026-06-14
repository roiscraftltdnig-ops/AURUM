# Production Next Steps

## Completed

- Official brand spelling confirmed: ROISCRAFT.
- Founder call converted into extracted answers.
- Draft knowledge base generated.
- Telegram bot token validated.
- Personal admin Telegram ID validated.
- Admin/report group validated.
- Local dashboard and backend tested.

## Ready To Configure

Use these generated knowledge files:

- `knowledge_base/roiscraft/overview.md`
- `knowledge_base/roiscraft/faqs.md`
- `knowledge_base/aurum_foundation/overview.md`
- `knowledge_base/bytnet/overview.md`
- `knowledge_base/onboarding/journeys.md`
- `knowledge_base/onboarding/telegram_routing.md`
- `knowledge_base/compliance/disclaimers.md`
- `knowledge_base/compliance/ai_boundaries.md`

## Fabrication Boundary

The draft knowledge base fills gaps with conservative education-first content. It does not fabricate:

- Telegram invite links.
- Legal approvals.
- Regulatory licenses.
- Sales performance.
- ROI or profit claims.
- Real document/video URLs.
- Deployment credentials.

Those must be supplied or verified before final public launch.

## Still Required For Real Production

Supabase migration access:

```env
SUPABASE_DB_PASSWORD=
```

or:

```env
SUPABASE_ACCESS_TOKEN=
SUPABASE_PROJECT_ID=ojnbxoollsvlodvpgezl
```

AI:

```env
OPENAI_API_KEY=
```

Public webhook deployment:

```env
APP_BASE_URL=https://your-backend-domain.com
```

Telegram destination links:

```text
Beginner group link:
Advanced group link:
VIP group link:
Announcement channel link:
Webinar link:
Support/admin contact:
```

## Production Sequence

1. Apply `001_initial_schema.sql`.
2. Apply `002_roiscraft_seed_content.sql`.
3. Add real Telegram destination links in dashboard Resource Center.
4. Run local knowledge ingestion:

```powershell
tools\python-3.12.8\python.exe scripts\ingest_local_knowledge.py
```

5. Deploy backend to public HTTPS.
6. Set `APP_BASE_URL`.
7. Activate Telegram webhook.
8. Test:
   - Beginner onboarding.
   - Aurum routing.
   - Bytnet routing.
   - High-intent escalation.
   - Admin alert.
   - Daily report.
