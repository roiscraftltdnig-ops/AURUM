# ROISCRAFT AI Community & Investor Intelligence System

Telegram-first AI ecosystem infrastructure for ROISCRAFT, Aurum Foundation, Bytnet, and future portfolios.

This repository contains:

- FastAPI backend for Telegram webhooks, AI orchestration, RAG, CRM, admin APIs, and escalation logic.
- Next.js 15 admin dashboard with premium dark SaaS UX.
- Supabase PostgreSQL schema with pgvector retrieval.
- Docker, Railway, Render, and VPS-ready deployment assets.
- Setup guides, API notes, onboarding flows, AI prompts, and admin workflows.

## Architecture

```text
Telegram Users
  -> Telegram Bot Webhook
  -> FastAPI Orchestration Layer
  -> Memory + Lead Scoring + RAG
  -> Supabase CRM / pgvector
  -> Telegram Replies + Admin Alerts
  -> Next.js Admin Dashboard
```

The platform is intentionally Telegram-native. Onboarding, qualification, routing, broadcasts, escalation, and CRM activity are designed to happen through Telegram while admins manage the intelligence layer through the dashboard.

## Local Setup

1. Copy `.env.example` to `.env` and fill the values.
2. Create a Supabase project and run `supabase/migrations/001_initial_schema.sql`.
3. Start the stack:

```bash
docker compose up --build
```

On Windows, you can prepare the environment with:

```powershell
.\scripts\bootstrap-windows.ps1
```

To attempt runtime installation through winget:

```powershell
.\scripts\bootstrap-windows.ps1 -InstallTools
```

4. Visit `http://localhost:3000`.
5. Sign in with `admin@roiscraft.ai` and `ChangeMeNow!2026`, then rotate the password in Supabase immediately.
6. Configure Telegram links in the dashboard or directly in `community_groups`.
7. Click `Activate webhook` from the dashboard after `APP_BASE_URL` points to a public HTTPS URL.

## Backend Development

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Frontend Development

```bash
cd frontend
npm install
npm run dev
```

## Key Behavior

- The bot validates Telegram webhook secrets.
- Every message is stored in the CRM.
- Lead stage and temperature are updated continuously.
- High-intent language creates admin tasks and Telegram admin alerts.
- RAG retrieval prioritizes uploaded ROISCRAFT, Aurum Foundation, and Bytnet documents.
- Memory prevents repetitive onboarding content and supports progressive disclosure.

## Production Notes

- Replace the seeded admin password.
- Restrict CORS origins in `backend/app/main.py`.
- Configure Supabase Row Level Security policies for direct client access if you later expose Supabase to browsers.
- Use a public HTTPS URL for Telegram webhooks.
- Set `JWT_SECRET` to a long random value.
