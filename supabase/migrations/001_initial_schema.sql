create extension if not exists vector;
create extension if not exists pgcrypto;

create type lead_temperature as enum ('COLD', 'WARM', 'HOT');
create type qualification_stage as enum ('BEGINNER', 'INTERMEDIATE', 'ADVANCED', 'HIGH_INTENT');
create type task_status as enum ('open', 'in_progress', 'completed', 'dismissed');

create table admin_users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  password_hash text not null,
  role text not null default 'admin',
  created_at timestamptz not null default now()
);

create table users (
  id uuid primary key default gen_random_uuid(),
  telegram_id text unique not null,
  telegram_chat_id text not null,
  telegram_username text,
  first_name text,
  last_name text,
  phone_number text,
  email text,
  country text,
  ecosystem_interests text[] not null default '{}',
  investment_intent text,
  partnership_intent text,
  qualification_stage qualification_stage not null default 'BEGINNER',
  lead_temperature lead_temperature not null default 'COLD',
  engagement_score integer not null default 0 check (engagement_score between 0 and 100),
  admin_review_status text not null default 'none',
  followup_required boolean not null default false,
  created_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now()
);

create table conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  channel text not null default 'telegram',
  summary text,
  status text not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table messages (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  conversation_id uuid references conversations(id) on delete set null,
  role text not null check (role in ('user', 'assistant', 'admin', 'system')),
  content text not null,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create table lead_scores (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  score integer not null,
  temperature lead_temperature not null,
  stage qualification_stage not null,
  reasons text[] not null default '{}',
  created_at timestamptz not null default now()
);

create table user_tags (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  tag text not null,
  created_by uuid references admin_users(id),
  created_at timestamptz not null default now(),
  unique(user_id, tag)
);

create table user_memory (
  user_id uuid primary key references users(id) on delete cascade,
  memory jsonb not null default '{
    "intro_video_sent": false,
    "intro_video_clicked": false,
    "intro_video_watched": false,
    "aurum_intro_completed": false,
    "bytnet_intro_completed": false,
    "onboarding_completed": false,
    "beginner_stage_completed": false,
    "intermediate_stage_completed": false,
    "advanced_stage_completed": false,
    "joined_groups": [],
    "joined_channels": [],
    "attended_webinars": [],
    "viewed_documents": [],
    "downloaded_materials": [],
    "previous_questions": [],
    "engagement_score": 0,
    "lead_temperature": "COLD",
    "admin_review_status": "none",
    "followup_required": false
  }',
  updated_at timestamptz not null default now()
);

create table onboarding_progress (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  journey_key text not null,
  stage text not null,
  completed boolean not null default false,
  completed_at timestamptz,
  metadata jsonb not null default '{}',
  unique(user_id, journey_key, stage)
);

create table viewed_content (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  content_key text not null,
  content_type text not null,
  portfolio text not null default 'ROISCRAFT',
  viewed_at timestamptz not null default now(),
  metadata jsonb not null default '{}',
  unique(user_id, content_key)
);

create table engagement_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  event_type text not null,
  event_value text,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create table knowledge_documents (
  id uuid primary key default gen_random_uuid(),
  filename text not null,
  portfolio text not null default 'ROISCRAFT',
  status text not null default 'uploaded',
  uploaded_by uuid references admin_users(id),
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create table document_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references knowledge_documents(id) on delete cascade,
  chunk_index integer not null,
  content text not null,
  embedding vector(1536) not null,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  unique(document_id, chunk_index)
);

create index document_chunks_embedding_idx on document_chunks using ivfflat (embedding vector_cosine_ops) with (lists = 100);

create table education_journeys (
  id uuid primary key default gen_random_uuid(),
  key text unique not null,
  portfolio text not null default 'ROISCRAFT',
  stage qualification_stage not null,
  title text not null,
  steps jsonb not null default '[]',
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create table broadcasts (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  body text not null,
  segment jsonb not null default '{}',
  status text not null default 'draft',
  scheduled_for timestamptz,
  sent_at timestamptz,
  created_by uuid references admin_users(id),
  created_at timestamptz not null default now()
);

create table admin_logs (
  id uuid primary key default gen_random_uuid(),
  admin_id uuid references admin_users(id),
  action text not null,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create table admin_tasks (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  title text not null,
  summary text not null,
  priority text not null default 'medium',
  recommended_action text not null,
  status task_status not null default 'open',
  assigned_to uuid references admin_users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table community_groups (
  id uuid primary key default gen_random_uuid(),
  key text unique not null,
  portfolio text not null default 'ROISCRAFT',
  label text not null,
  invite_url text not null,
  min_stage qualification_stage not null default 'BEGINNER',
  is_vip boolean not null default false,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create table analytics_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete set null,
  name text not null,
  value numeric,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create or replace function match_document_chunks(
  query_embedding vector(1536),
  match_count int default 5,
  portfolio_filter text default null
)
returns table (
  id uuid,
  document_id uuid,
  content text,
  metadata jsonb,
  similarity float
)
language sql stable
as $$
  select
    dc.id,
    dc.document_id,
    dc.content,
    dc.metadata,
    1 - (dc.embedding <=> query_embedding) as similarity
  from document_chunks dc
  join knowledge_documents kd on kd.id = dc.document_id
  where portfolio_filter is null or kd.portfolio = portfolio_filter or kd.portfolio = 'ROISCRAFT'
  order by dc.embedding <=> query_embedding
  limit match_count;
$$;

create or replace function dashboard_metrics()
returns jsonb
language sql stable
as $$
  select jsonb_build_object(
    'total_users', (select count(*) from users),
    'active_users', (select count(*) from users where last_seen_at > now() - interval '7 days'),
    'hot_leads', (select count(*) from users where lead_temperature = 'HOT'),
    'open_tasks', (select count(*) from admin_tasks where status = 'open'),
    'vip_requests', (select count(*) from admin_tasks where lower(title) like '%vip%' or lower(summary) like '%vip%'),
    'documents', (select count(*) from knowledge_documents),
    'broadcasts', (select count(*) from broadcasts)
  );
$$;

insert into admin_users (email, password_hash, role)
values ('admin@roiscraft.ai', crypt('ChangeMeNow!2026', gen_salt('bf')), 'owner')
on conflict (email) do nothing;
