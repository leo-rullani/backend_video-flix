````md
# Videoflix Backend (Django + DRF + JWT Cookies + Postgres + Redis/RQ + HLS)

Videoflix is a Netflix-like demo / school project (Developer Akademie).
This repository contains the **Django backend** with a REST API, **JWT authentication using HttpOnly cookies**, **email flows** (registration activation + password reset), **Redis + Django RQ** (background jobs), and **HLS streaming** (FFmpeg).

The frontend (HTML/CSS/JS) connects to this backend via `/api/...`.

---

## Table of Contents

1. [Tech Stack](#tech-stack)
2. [Features](#features)
3. [Requirements](#requirements)
4. [Quickstart with Docker](#quickstart-with-docker)
5. [Environment Variables](#environment-variables)
6. [Common Docker Commands](#common-docker-commands)
7. [Auth Flow: Register → Activate → Login](#auth-flow-register--activate--login)
8. [Email Setup (Console vs Real SMTP)](#email-setup-console-vs-real-smtp)
9. [Background Jobs (Redis + RQ)](#background-jobs-redis--rq)
10. [HLS (FFmpeg) and Streaming Endpoints](#hls-ffmpeg-and-streaming-endpoints)
11. [API Overview](#api-overview)
12. [Tests](#tests)
13. [Keep requirements.txt up to date](#keep-requirementstxt-up-to-date)
14. [Troubleshooting](#troubleshooting)
15. [Legal](#legal)

---

## Tech Stack

- Python (runs inside Docker)
- Django + Django REST Framework (DRF)
- JWT via `djangorestframework-simplejwt`
- Authentication via **HttpOnly cookies** (`access_token`, `refresh_token`)
- PostgreSQL (Docker container)
- Redis + Django RQ (queue + worker for background tasks)
- FFmpeg for HLS (`.m3u8` playlists + `.ts` segments)
- Whitenoise for static files inside Docker
- gunicorn as WSGI server in Docker

---

## Features

### Authentication & Accounts
- Register with email + password + password confirmation
- Account is **inactive until activated**
- Activation email is sent after registration
- Login sets HttpOnly cookie tokens
- Logout blacklists refresh token
- Password reset via email link

### Videos & Streaming
- Video list endpoint for the frontend dashboard
- HLS streaming for multiple qualities (e.g. 480p / 720p / 1080p)
- Endpoints serve `index.m3u8` and `.ts` segments

### Background Jobs
- Email sending is executed via **Django RQ** (Redis queue)
- HLS generation can be run via a management command

---

## Requirements

You need:
- Docker Desktop / Docker Engine (with Compose)
- Git

This project is designed to run **fully containerized** (recommended for grading / review).

---

## Quickstart with Docker

> Important (Developer Akademie Docker setup):
> - Do **not** modify `backend.Dockerfile`, `docker-compose.yml`, or `backend.entrypoint.sh`.
> - You may change values in `.env` but do **not rename** existing variables.
> - Keep `requirements.txt` updated if you install new Python packages.

### 1) Clone the repository

```bash
git clone https://github.com/leo-rullani/backend_video-flix.git
cd backend_video-flix
````

### 2) Create your `.env`

**Mac / Linux / Git Bash (Windows):**

```bash
cp .env.template .env
```

**Windows PowerShell alternative:**

```powershell
copy .env.template .env
```

### 3) Fill in `.env`

Open `.env` and set the values you need (see [Environment Variables](#environment-variables)).

### 4) Build and start containers

If your system supports `docker-compose`:

```bash
docker-compose up -d --build
```

If your system uses the new plugin syntax:

```bash
docker compose up -d --build
```

### 5) Apply migrations

```bash
docker-compose exec web python manage.py migrate
```

### 6) (Optional) Create a Django admin user

```bash
docker-compose exec web python manage.py createsuperuser
```

### 7) Open the backend

* Backend root: `http://127.0.0.1:8000/`
* Django admin: `http://127.0.0.1:8000/admin/`
* API base: `http://127.0.0.1:8000/api/`

---

## Environment Variables

The backend reads its configuration from `.env`.

### Required (minimum for Docker setup)

```env
# Django
SECRET_KEY=please_change_me
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:5500,http://localhost:5500,http://127.0.0.1:8000,http://localhost:8000

# PostgreSQL
DB_NAME=videoflix_db
DB_USER=videoflix_user
DB_PASSWORD=supersecretpassword
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_LOCATION=redis://redis:6379/1
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Frontend URLs used to build activation/reset links
FRONTEND_BASE_URL=http://127.0.0.1:5500
FRONTEND_ACTIVATION_PATH=/pages/auth/activate.html
FRONTEND_PASSWORD_RESET_PATH=/pages/auth/reset_password.html
```

### Email (Console mode or real SMTP)

```env
# Email backend (console is default for local dev)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# For real SMTP email sending (example)
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@example.com
EMAIL_HOST_PASSWORD=your_email_password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=your_email@example.com
```

---

## Common Docker Commands

### Show running containers

```bash
docker-compose ps
```

### View backend logs

```bash
docker-compose logs -f web
```

### Stop containers

```bash
docker-compose down
```

### Rebuild everything (after dependency changes)

```bash
docker-compose up -d --build
```

---

## Auth Flow: Register → Activate → Login

This is the most important flow for reviewers.

### 1) Register

Use the frontend registration form (or call the API).
After a successful registration:

* The user is created
* The user is set to **inactive**
* An activation email is sent (in console mode: printed in logs)

### 2) Get the activation link

If your email backend is the console backend, the activation email will be printed in the **Docker logs**:

```bash
docker-compose logs -f web
```

You should see a clean link that you can copy/paste (example):

```text
[ACTIVATION LINK] http://127.0.0.1:5500/pages/auth/activate.html?uid=...&token=...
```

Open that link in the browser.
The frontend activation page will then call the backend activation endpoint.

### 3) Login

After activation, login works and sets:

* `access_token` (HttpOnly cookie)
* `refresh_token` (HttpOnly cookie)

---

## Email Setup (Console vs Real SMTP)

### Console email (recommended for local development / grading)

This is the simplest and most stable setup:

* Emails are not sent to the internet
* The email content (including activation/reset link) appears in Docker logs
* Reviewers can test the flow without SMTP credentials

Check the current backend:

```bash
docker-compose exec web python manage.py shell -c "from django.conf import settings; print(settings.EMAIL_BACKEND)"
```

Expected output for console mode:

```text
django.core.mail.backends.console.EmailBackend
```

### Real email (SMTP)

If you want real emails:

1. Set `EMAIL_BACKEND` to SMTP backend (or remove it to use your default settings)
2. Provide `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, etc. in `.env`
3. Rebuild containers:

```bash
docker-compose up -d --build
```

Note:

* Some providers require an “app password” (e.g. Gmail).
* SMTP can fail due to firewall, missing credentials, or provider restrictions.

---

## Background Jobs (Redis + RQ)

Activation and reset emails are queued as background jobs.

### Check if worker is running

In backend logs you should see something like:

```text
*** Listening on default...
```

### Manually run a worker (if needed)

```bash
docker-compose exec web python manage.py rqworker default
```

---

## HLS (FFmpeg) and Streaming Endpoints

### Generate HLS renditions

The backend provides a management command:

```bash
docker-compose exec web python manage.py generate_hls
```

Options:

* Only one video:

```bash
docker-compose exec web python manage.py generate_hls --video-id 1
```

* Overwrite existing output:

```bash
docker-compose exec web python manage.py generate_hls --overwrite
```

Output structure (default):

* `media/hls/<video_id>/480p/index.m3u8`
* `media/hls/<video_id>/480p/000.ts`, `001.ts`, ...

### HLS endpoints

* Master playlist:

  * `GET /api/video/<movie_id>/<resolution>/index.m3u8`
* Segment file:

  * `GET /api/video/<movie_id>/<resolution>/<segment>/`

---

## API Overview

### Authentication

* `POST /api/register/`
* `GET /api/activate/<uidb64>/<token>/`
* `POST /api/login/`
* `POST /api/logout/`
* `POST /api/token/refresh/`
* `POST /api/password_reset/`
* `POST /api/password_confirm/<uidb64>/<token>/`

### Videos / Streaming

* `GET /api/video/`
* `GET /api/video/<movie_id>/<resolution>/index.m3u8`
* `GET /api/video/<movie_id>/<resolution>/<segment>/`

---

## Tests

Run Django tests inside Docker:

```bash
docker-compose exec web python manage.py test
```

If your project also uses pytest:

```bash
docker-compose exec web pytest
```

---

## Keep requirements.txt up to date

If you install new Python packages, update `requirements.txt`:

```bash
docker-compose exec web pip freeze > requirements.txt
```

Commit the updated file.

---

## Troubleshooting

### 1) Docker is not running

If you see errors like “unable to get image” or connection errors:

* Start Docker Desktop
* Retry:

```bash
docker-compose up -d --build
```

### 2) `backend.entrypoint.sh: no such file or directory`

This often happens when the file uses **CRLF** line endings.
Fix: set file line endings to **LF** and commit.

### 3) CORS blocked in the browser

If the browser shows CORS errors:

* Make sure your frontend origin is in `CORS_ALLOWED_ORIGINS`
* Make sure `CORS_ALLOW_CREDENTIALS=True`
* Make sure frontend fetch uses:

  * `credentials: "include"`

Also avoid mixing `localhost` and `127.0.0.1` (cookies can behave differently).

### 4) Token expired / always 401

If you get “token is expired”:

* Clear cookies for `127.0.0.1`
* Or call logout endpoint
* Then login again

### 5) Migration problems after model changes

If migrations fail and Docker cannot start cleanly:

```bash
docker run --rm web python manage.py makemigrations
docker run --rm web python manage.py migrate
```

---

## Legal

Operator (demo project):

Leugzim Rullani
Untere Farnbühlstrasse 3
5610 Wohlen
Email: [leugzimrullani@outlook.com](mailto:leugzimrullani@outlook.com)

Legal pages are in the frontend:

* `/pages/legal/imprint/index.html`
* `/pages/legal/privacy/index.html`

---

## Reference (Developer Akademie Docker setup)

Docker setup source repository (for the provided docker files):

```text
https://github.com/Developer-Akademie-Backendkurs/material.videoflix-docker-files
```

```
::contentReference[oaicite:0]{index=0}
```