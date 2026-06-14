create table if not exists admin_users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  password_hash text not null,
  role text not null default 'admin',
  created_at timestamptz not null default now()
);

create table if not exists users (
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

create table if not exists conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  channel text not null default 'telegram',
  summary text,
  status text not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists messages (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  conversation_id uuid references conversations(id) on delete set null,
  role text not null check (role in ('user', 'assistant', 'admin', 'system')),
  content text not null,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create table if not exists lead_scores (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  score integer not null,
  temperature lead_temperature not null,
  stage qualification_stage not null,
  reasons text[] not null default '{}',
  created_at timestamptz not null default now()
);

create table if not exists user_tags (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  tag text not null,
  created_by uuid references admin_users(id),
  created_at timestamptz not null default now(),
  unique(user_id, tag)
);

create table if not exists user_memory (
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

create table if not exists onboarding_progress (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  journey_key text not null,
  stage text not null,
  completed boolean not null default false,
  completed_at timestamptz,
  metadata jsonb not null default '{}',
  unique(user_id, journey_key, stage)
);

create table if not exists viewed_content (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  content_key text not null,
  content_type text not null,
  portfolio text not null default 'ROISCRAFT',
  viewed_at timestamptz not null default now(),
  metadata jsonb not null default '{}',
  unique(user_id, content_key)
);

create table if not exists engagement_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  event_type text not null,
  event_value text,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create table if not exists knowledge_documents (
  id uuid primary key default gen_random_uuid(),
  filename text not null,
  portfolio text not null default 'ROISCRAFT',
  status text not null default 'uploaded',
  uploaded_by uuid references admin_users(id),
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create table if not exists document_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references knowledge_documents(id) on delete cascade,
  chunk_index integer not null,
  content text not null,
  embedding vector(1536) not null,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  unique(document_id, chunk_index)
);

create table if not exists education_journeys (
  id uuid primary key default gen_random_uuid(),
  key text unique not null,
  portfolio text not null default 'ROISCRAFT',
  stage qualification_stage not null,
  title text not null,
  steps jsonb not null default '[]',
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create table if not exists broadcasts (
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

create table if not exists admin_logs (
  id uuid primary key default gen_random_uuid(),
  admin_id uuid references admin_users(id),
  action text not null,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create table if not exists admin_tasks (
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

create table if not exists community_groups (
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

create table if not exists analytics_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete set null,
  name text not null,
  value numeric,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);
