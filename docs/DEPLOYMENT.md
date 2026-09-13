# EventScout Production Deployment Guide

This document explains the production deployment architecture for the **EventScout** platform, covering the decoupled FastAPI backend, asynchronous background worker, Next.js frontend, and MongoDB Atlas database.

---

## 1. System Architecture & Process Separation

In production, EventScout separates compute workloads across three independent processes:

1. **FastAPI Web Service (`api/main.py`)**:
   - High-throughput asynchronous REST API.
   - Stateless request handling (Search, Filters, Personalization, Auth, Source Management).
   - Horizontally scalable across multiple container replicas.

2. **Background Scheduler Worker (`eventscout/scheduler.py`)**:
   - Autonomous daemon running outside web request cycles.
   - Executes multi-source dynamic collection at configured intervals (`SCRAPE_INTERVAL_HOURS=6`).
   - Runs daily email digest dispatches at scheduled hours (`DAILY_DIGEST_HOUR=8`).
   - Strict failure isolation: a broken collector never halts the worker process.

3. **Next.js Frontend (`frontend/`)**:
   - Modern React 19 / Next.js 15 App Router interface.
   - Client-side filtering, state persistence, dark mode, responsive card grids.

4. **MongoDB Atlas Database**:
   - Hosted managed cluster storing `events`, `users`, `sources`, and `notifications`.
   - Compound indexes: `(source, source_event_id)` unique, `(date_time)` ascending.

---

## 2. Environment Variables Checklist

Ensure these variables are defined in your deployment platform (e.g. Render, Railway, AWS ECS, Fly.io):

| Variable | Description | Example |
|---|---|---|
| `MONGODB_URI` | MongoDB Atlas connection string | `mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority` |
| `MONGODB_DATABASE` | Database name | `eventscout` |
| `JWT_SECRET_KEY` | Cryptographic secret for signing tokens | `min_32_chars_random_string` |
| `JWT_ALGORITHM` | Signature algorithm | `HS256` |
| `JWT_EXPIRE_DAYS` | Token lifespan | `7` |
| `GEMINI_API_KEY` | Google Gemini API key for Source Discovery Agent | `AIzaSy...` |
| `SMTP_HOST` | Outbound mail server (optional for email digests) | `smtp.resend.com` |
| `SMTP_PORT` | Outbound mail port | `587` |
| `SMTP_USERNAME` | Outbound mail user | `resend` |
| `SMTP_PASSWORD` | Outbound mail password/key | `re_...` |
| `EMAIL_FROM` | Sender address | `EventScout <notifications@eventscout.dev>` |
| `NEXT_PUBLIC_API_URL` | Public URL of the FastAPI backend | `https://api.eventscout.dev` |

---

## 3. Deployment with Docker Compose

To spin up the entire production stack locally or on a single VPS (DigitalOcean Droplet, AWS EC2):

```bash
# 1. Clone repository
git clone https://github.com/your-org/eventscout.git
cd eventscout

# 2. Configure environment
cp .env.example .env
# Edit .env with your MongoDB Atlas URI and Gemini key

# 3. Build and launch all services
docker compose up -d --build

# 4. View running container logs
docker compose logs -f
```

---

## 4. Platform-as-a-Service (PaaS) Deployment

### Deploying on Render / Railway

1. **FastAPI Backend (Web Service)**:
   - Build Command: `pip install -r requirements.txt && playwright install chromium`
   - Start Command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
   - Health Check Path: `/health`

2. **Scheduler Worker (Background Worker Service)**:
   - Build Command: `pip install -r requirements.txt && playwright install chromium`
   - Start Command: `python -m eventscout.scheduler`

3. **Frontend (Static / Node Web Service)**:
   - Root Directory: `frontend`
   - Build Command: `npm install && npm run build`
   - Start Command: `npm run start`
   - Environment Variable: `NEXT_PUBLIC_API_URL=https://your-api-domain.com`

---

## 5. Chrome Extension Deployment

To publish the EventScout extension or load for testing:

1. Open Chrome at `chrome://extensions/`.
2. Enable **Developer mode**.
3. Click **Load unpacked** and select the `extension/` directory.
4. Update `API_BASE_URL` in `extension/background.js` to point to your production API if deploying publicly.
