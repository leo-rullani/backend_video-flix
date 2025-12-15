# Videoflix Backend (Django + DRF + JWT Cookies + Postgres + Redis/RQ + HLS)

Videoflix is a Netflix-like demo / school project (Developer Akademie).
This repository contains the **Django backend** with:

* REST API (`/api/...`)
* JWT authentication using **HttpOnly cookies**
* Registration + account activation email flow (**SMTP required for review**)
* Password reset email flow (**SMTP required for review**)
* Redis + Django RQ (background jobs)
* HLS streaming (FFmpeg)

The frontend (HTML/CSS/JS) connects to this backend via `/api/...`.

---

## Table of Contents

1. Tech Stack
2. Features
3. Requirements
4. Quickstart with Docker (recommended)
5. Environment Variables (.env)
6. What Docker does automatically
7. Common Docker Commands
8. Auth Flow: Register → Activate → Login
9. Email Setup (SMTP / Mailtrap Sandbox)
10. Background Jobs (Redis + RQ)
11. HLS (FFmpeg) + Streaming Endpoints
12. API Overview
13. Tests
14. Keep requirements.txt up to date
15. Troubleshooting
16. Reference (Developer Akademie Docker Files)

---

## 1) Tech Stack

* Django + Django REST Framework (DRF)
* JWT via `djangorestframework-simplejwt`
* Auth via HttpOnly cookies: `access_token`, `refresh_token`
* PostgreSQL (Docker)
* Redis + Django RQ
* FFmpeg for HLS (`.m3u8` + `.ts`)
* gunicorn + Whitenoise (inside Docker)

---

## 2) Features

### Accounts & Authentication

* Register with email + password + confirmation
* User is **inactive until activated**
* Activation email is sent after registration
* Login sets HttpOnly cookies
* Logout blacklists refresh token
* Password reset via email link

### Videos & Streaming

* Video list endpoint for dashboard
* HLS endpoints serve playlists and `.ts` segments

### Background Jobs

* Emails and HLS generation are processed via Django RQ (worker in the same container)

---

## 3) Requirements

You need:

* Docker Desktop / Docker Engine (with Docker Compose)
* Git

This project is designed to run **fully containerized** (recommended for grading/review).

---

## 4) Quickstart with Docker (recommended)

> Important (Developer Akademie Docker setup):
>
> * Do **not** modify `backend.Dockerfile`, `docker-compose.yml`, or `backend.entrypoint.sh`.
> * You may change values in `.env` but do **not rename** existing variables.
> * Keep `requirements.txt` updated if you install new packages.
> * Do **not** commit generated migration files (`*/migrations/00*.py`).

### Step 1 — Clone the repository

```bash
git clone https://github.com/leo-rullani/backend_video-flix.git
cd backend_video-flix
```

### Step 2 — Create your `.env`

Mac / Linux / Git Bash (Windows):

```bash
cp .env.template .env
```

Windows PowerShell:

```powershell
copy .env.template .env
```

> Note:
>
> * `.env.template` is included in the repo (safe defaults + placeholders).
> * `.env` is **NOT** tracked and must contain your local credentials (DB/SMTP etc.).
> * Never commit `.env`.

### Step 3 — Fill in `.env`

Open `.env` and **replace placeholders** (especially SMTP credentials).
See section “Environment Variables”.

### Step 4 — Build and start containers

If your system supports `docker-compose`:

```bash
docker-compose up -d --build
```

If your system uses the new plugin syntax:

```bash
docker compose up -d --build
```

### Step 5 — Open the backend

* Admin: `http://127.0.0.1:8000/admin/`
* API base: `http://127.0.0.1:8000/api/`

> Note: `http://127.0.0.1:8000/` may return 404 by design. Use `/api/` or `/admin/`.

---

## 5) Environment Variables (.env)

The backend reads config from `.env`.

### Minimum required (works with Docker defaults)

```env
# --------------------------------------------------
# DJANGO SUPERUSER (created automatically by entrypoint)
# --------------------------------------------------
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_PASSWORD=adminpassword
DJANGO_SUPERUSER_EMAIL=admin@example.com

# --------------------------------------------------
# DJANGO CORE
# --------------------------------------------------
SECRET_KEY=please-change-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Needed for cookies + CSRF in local dev
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:5500,http://localhost:5500,http://127.0.0.1:8000,http://localhost:8000

# --------------------------------------------------
# DATABASE (PostgreSQL via Docker)
# IMPORTANT: If you change DB_* after first start, remove volumes (see Troubleshooting)
# --------------------------------------------------
DB_NAME=videoflix_db
DB_USER=videoflix_user
DB_PASSWORD=supersecretpassword
DB_HOST=db
DB_PORT=5432

# --------------------------------------------------
# REDIS (RQ + Cache)
# --------------------------------------------------
REDIS_LOCATION=redis://redis:6379/1
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# --------------------------------------------------
# FRONTEND LINKS (Activation / Reset)
# IMPORTANT: Use ONE host consistently (either 127.0.0.1 OR localhost)
# --------------------------------------------------
FRONTEND_BASE_URL=http://127.0.0.1:5500
FRONTEND_ACTIVATION_PATH=/pages/auth/activate.html
FRONTEND_PASSWORD_RESET_PATH=/pages/auth/reset_password.html
```

---

## 9) Email Setup (SMTP / Mailtrap Sandbox)

### Why this matters (review requirement)

For the Developer Akademie review, **SMTP must be enabled**, so activation + password reset emails can be sent.

⚠️ `smtp.example.com` is just a placeholder.
If you leave placeholder values, sending an email will fail (DNS/auth errors).

### Option A (recommended for review): Mailtrap Sandbox SMTP

Create a Mailtrap account → “Email Testing” → Inbox → SMTP Settings.

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=sandbox.smtp.mailtrap.io
EMAIL_PORT=2525
EMAIL_HOST_USER=YOUR_MAILTRAP_USERNAME
EMAIL_HOST_PASSWORD=YOUR_MAILTRAP_PASSWORD
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
DEFAULT_FROM_EMAIL=videoflix@mailtrap.io
```

After changing `.env`, rebuild:

```bash
docker-compose down
docker-compose up -d --build
```

Verify settings inside the container:

```bash
docker-compose exec web python manage.py shell -c "from django.conf import settings; print(settings.EMAIL_BACKEND, settings.EMAIL_HOST, settings.EMAIL_PORT, settings.EMAIL_USE_TLS, settings.EMAIL_USE_SSL)"
```

Send a test email (it will appear in the Mailtrap Inbox):

```bash
docker-compose exec web python manage.py shell -c "from django.core.mail import send_mail; print(send_mail('SMTP Test','Hello from Videoflix',None,['test@example.com']))"
```

Expected output:

```text
1
```

### Option B: Real SMTP Provider (Gmail/Outlook/etc.)

Use your provider’s SMTP host and an app password if required.

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.your-provider.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@example.com
EMAIL_HOST_PASSWORD=your_app_password_or_smtp_password
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
DEFAULT_FROM_EMAIL=your_email@example.com
```

Rebuild afterwards:

```bash
docker-compose down
docker-compose up -d --build
```

---

## 6) What Docker does automatically

When you start Docker, `backend.entrypoint.sh` automatically:

1. waits for PostgreSQL
2. collects static files
3. runs `makemigrations` and `migrate`
4. creates the Django admin user (from `DJANGO_SUPERUSER_*`)
5. starts gunicorn + the RQ worker

So you usually **do NOT need** to run `migrate` manually.

---

## 7) Common Docker Commands

Show containers:

```bash
docker-compose ps
```

Backend logs:

```bash
docker-compose logs -f web
```

Stop containers:

```bash
docker-compose down
```

Rebuild:

```bash
docker-compose up -d --build
```

Open a Django shell:

```bash
docker-compose exec web python manage.py shell
```

---

## 8) Auth Flow: Register → Activate → Login

### Register

* User is created and set to inactive
* Activation email is sent (SMTP required)

### Activate

* User clicks activation link from the email
* Frontend activation page calls backend activation endpoint

### Login

* Login sets HttpOnly cookies:

  * `access_token`
  * `refresh_token`

---

## 10) Background Jobs (Redis + RQ)

Emails and HLS generation are processed by Django RQ.

In logs you should see something like:

```text
*** Listening on default...
```

To follow logs:

```bash
docker-compose logs -f web
```

---

## 11) HLS (FFmpeg) + Streaming Endpoints

HLS output includes:

* `index.m3u8`
* many `.ts` segments

Example endpoints:

* Playlist:

  * `GET /api/video/<movie_id>/<resolution>/index.m3u8`
* Segment:

  * `GET /api/video/<movie_id>/<resolution>/<segment>/`

If you need to (re)generate HLS manually:

```bash
docker-compose exec web python manage.py generate_hls --overwrite
```

---

## 12) API Overview

Auth:

* `POST /api/register/`
* `GET /api/activate/<uidb64>/<token>/`
* `POST /api/login/`
* `POST /api/logout/`
* `POST /api/token/refresh/`
* `POST /api/password_reset/`
* `POST /api/password_confirm/<uidb64>/<token>/`

Video:

* `GET /api/video/`
* `GET /api/video/<movie_id>/<resolution>/index.m3u8`
* `GET /api/video/<movie_id>/<resolution>/<segment>/`

---

## 13) Tests

```bash
docker-compose exec web python manage.py test
```

---

## 14) Keep requirements.txt up to date

If you install new packages:

```bash
docker-compose exec web pip freeze > requirements.txt
```

Commit the updated file.

---

## 15) Troubleshooting

### A) PostgreSQL “password authentication failed”

This usually happens if:

* you changed `DB_NAME/DB_USER/DB_PASSWORD` after the database volume was already created.

Fix (reset volumes):

```bash
docker-compose down -v
docker-compose up -d --build
```

### B) SMTP “Name does not resolve” / “Connection unexpectedly closed”

* `smtp.example.com` is a placeholder → replace with real SMTP host
* Replace placeholder `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD`
* Then rebuild:

```bash
docker-compose down
docker-compose up -d --build
```

### C) CORS / cookies not working

Do not mix `localhost` and `127.0.0.1`. Use one consistently (frontend + backend + env URLs).

### D) backend.entrypoint.sh “no such file or directory”

Often CRLF line endings on Windows.
Fix file line endings to **LF** and commit.

---

## 16) Reference (Developer Akademie Docker Files)

Docker setup source:

```text
https://github.com/Developer-Akademie-Backendkurs/material.videoflix-docker-files
```