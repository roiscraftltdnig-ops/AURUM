# Deployment Guide

## Docker Compose

```bash
docker compose up --build
```

Use this for local integration and VPS deployments.

## Railway

1. Create a Railway project.
2. Add Supabase and OpenAI environment variables.
3. Deploy the backend using `railway.json`.
4. Deploy the frontend as a separate service from `frontend/Dockerfile`.
5. Set `APP_BASE_URL` to the Railway backend URL.
6. Activate the Telegram webhook.

## Render

1. Connect the repository to Render.
2. Use `render.yaml`.
3. Add secrets in the Render dashboard.
4. Replace `NEXT_PUBLIC_API_BASE_URL` with the deployed backend URL.

## VPS

1. Install Docker and Docker Compose.
2. Create `.env`.
3. Run `docker compose up -d --build`.
4. Put Caddy, Nginx, or Traefik in front of the backend and frontend.
5. Use HTTPS for Telegram webhooks.

Example Nginx routes:

```nginx
location /api/ {
  proxy_pass http://127.0.0.1:8000/;
}

location / {
  proxy_pass http://127.0.0.1:3000;
}
```

