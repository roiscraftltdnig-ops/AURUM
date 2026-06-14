# Example Admin Workflows

## Configure Community Links

1. Open dashboard.
2. Use the community group API or Supabase table to update `community_groups`.
3. Set `min_stage` for gated access.
4. Keep `is_active` false until the link is approved.

## Review Hot Leads

1. Open the action queue.
2. Review AI-generated lead summary.
3. Check Telegram username and contact details.
4. Assign an admin.
5. Move status to `in_progress`.
6. Complete after follow-up.

## Upload Knowledge

1. Select portfolio.
2. Upload PDF, DOCX, TXT, or Markdown.
3. Confirm chunk count.
4. Ask the Telegram bot a question from that document.
5. Check that the answer cites the trusted knowledge implicitly and routes to a next step.

## Broadcast Campaign

1. Draft message in the broadcast composer.
2. Save as scheduled.
3. Use n8n or a worker to send to matching users from the `broadcasts.segment` object.
4. Record sends in `engagement_events`.

## Daily Report

Use the `dashboard_metrics()` RPC plus:

- top repeated `messages.content`
- open `admin_tasks`
- new HOT users
- portfolio interest counts from `users.ecosystem_interests`
- group joins from `engagement_events`

