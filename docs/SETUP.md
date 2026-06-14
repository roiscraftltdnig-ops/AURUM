# Setup Guide

## 1. Supabase

1. Create a Supabase project.
2. Enable the `vector` extension if it is not already available.
3. Run `supabase/migrations/001_initial_schema.sql` in the SQL editor.
4. Copy the project URL, anon key, and service role key into `.env`.

The backend uses the service role key server-side only. Do not expose it in the frontend.

## 2. Telegram

1. Create a bot with BotFather.
2. Add the token to `TELEGRAM_BOT_TOKEN`.
3. Generate a long random `TELEGRAM_WEBHOOK_SECRET`.
4. Set `APP_BASE_URL` to your backend HTTPS URL.
5. Start the backend and call `POST /admin/telegram/webhook` from the dashboard.

## 3. AI

1. Add `OPENAI_API_KEY`.
2. Default chat model: `gpt-4o`.
3. Default embedding model: `text-embedding-3-small`.

The backend has a deterministic local embedding fallback so local smoke tests still run without an API key, but production RAG should use OpenAI embeddings.

## 4. Admin Dashboard

1. Start the frontend.
2. Sign in with seeded credentials.
3. Replace the seeded password.
4. Configure community group links.
5. Upload ROISCRAFT, Aurum Foundation, and Bytnet knowledge materials.

## 5. n8n Compatibility

Use the database tables as automation triggers:

- `broadcasts` for scheduled campaigns.
- `admin_tasks` for human follow-up queues.
- `engagement_events` for behavioral triggers.
- `users.followup_required` for CRM escalation.

