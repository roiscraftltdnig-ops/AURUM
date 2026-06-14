insert into education_journeys (key, portfolio, stage, title, steps, is_active)
values
  (
    'beginner_roiscraft',
    'ROISCRAFT',
    'BEGINNER',
    'ROISCRAFT Beginner Education',
    '[
      {"step": 1, "label": "Understand ROISCRAFT", "resource_key": "roiscraft_overview"},
      {"step": 2, "label": "Choose interest path", "options": ["Aurum Foundation", "Bytnet", "Speak with team"]},
      {"step": 3, "label": "Review first material", "format_options": ["quick explanation", "video", "PDF"]},
      {"step": 4, "label": "Collect contact if serious", "fields": ["name", "phone_number", "email"]}
    ]',
    true
  ),
  (
    'aurum_interest',
    'Aurum Foundation',
    'INTERMEDIATE',
    'Aurum Foundation Interest Path',
    '[
      {"step": 1, "label": "Assess prior knowledge"},
      {"step": 2, "label": "Share Aurum overview", "resource_key": "aurum_foundation_overview"},
      {"step": 3, "label": "Explain risk and due diligence"},
      {"step": 4, "label": "Offer team follow-up"}
    ]',
    true
  ),
  (
    'bytnet_interest',
    'Bytnet',
    'INTERMEDIATE',
    'Bytnet Interest Path',
    '[
      {"step": 1, "label": "Assess user interest"},
      {"step": 2, "label": "Share Bytnet overview", "resource_key": "bytnet_overview"},
      {"step": 3, "label": "Answer only from uploaded source materials"},
      {"step": 4, "label": "Offer team follow-up"}
    ]',
    true
  ),
  (
    'vip_handoff',
    'ROISCRAFT',
    'HIGH_INTENT',
    'VIP And Human Follow-up',
    '[
      {"step": 1, "label": "Acknowledge intent"},
      {"step": 2, "label": "Collect name and phone number"},
      {"step": 3, "label": "Create admin task"},
      {"step": 4, "label": "Notify Telegram admin"}
    ]',
    true
  )
on conflict (key) do update set
  portfolio = excluded.portfolio,
  stage = excluded.stage,
  title = excluded.title,
  steps = excluded.steps,
  is_active = excluded.is_active;
