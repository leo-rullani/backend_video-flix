# Videoflix – Backend (Django, DRF, HLS, JWT)

Videoflix ist ein Netflix-ähnliches Demo-Projekt aus dem Kurs 2024.  
Dieses Repository enthält das **Django-Backend** mit REST-API, JWT-Authentifizierung
(HTTP-only Cookies), HLS-Streaming und E-Mail-Flows für Registrierung & Passwort-Reset.

Das Frontend (HTML/CSS/JS) greift über `/api/...` auf dieses Backend zu.

---

## Inhalt

1. [Technologie-Stack](#technologie-stack)  
2. [Features / User Stories](#features--user-stories)  
3. [Voraussetzungen](#voraussetzungen)  
4. [Quickstart mit Docker](#quickstart-mit-docker)  
5. [Umgebungsvariablen](#umgebungsvariablen)  
6. [Datenbank & Migrations](#datenbank--migrations)  
7. [HLS-Generierung](#hls-generierung)  
8. [Background-Tasks & Redis](#background-tasks--redis)  
9. [API-Übersicht](#api-übersicht)  
10. [Tests](#tests)  
11. [requirements.txt aktuell halten](#requirementstxt-aktuell-halten)  
12. [Rechtliches](#rechtliches)

---

## Technologie-Stack

- **Python** 3.11+  
- **Django** als Web-Framework  
- **Django REST Framework (DRF)** für die API  
- **JWT** via `djangorestframework-simplejwt` (Tokens in HttpOnly-Cookies)  
- **PostgreSQL** als Datenbank (im Docker-Setup)  
- **Redis** als Cache & Queue-Backend  
- **django-rq** für Background-Tasks (z. B. Mails, HLS)  
- **FFmpeg** für HLS-Transcoding  
- **Whitenoise** zur Auslieferung statischer Dateien im Docker-Setup  
- **gunicorn** als WSGI-Server im Docker-Setup  

---

## Features / User Stories

Die Implementierung orientiert sich an der offiziellen Videoflix-Checkliste (2024):

### Benutzeraccount & Registrierung

- Registrierung mit E-Mail, Passwort & Passwortbestätigung  
- Aktivierungs-E-Mail und Freischaltung des Accounts vor erstem Login  
- Login mit JWT in HttpOnly-Cookies (`access_token`, `refresh_token`)  
- Logout mit Blacklisting des Refresh-Tokens  
- Passwort-Reset via E-Mail-Link (Request + Confirm)  

### Video-Dashboard & Wiedergabe

- Video-Dashboard mit Teaser (Hero) und Listen nach Kategorien  
- Videos werden mit Thumbnail, Titel, Beschreibung und Kategorie angezeigt  
- HLS-Streaming mit mehreren Auflösungen: 480p, 720p, 1080p  
- Player mit automatischer Qualität und manueller Auswahl  
- Toast-Nachrichten beim Qualitätswechsel  
- Standard-Controls (Play/Pause, Seek, Vollbild)

### Rechtliche Informationen

- Seiten für **Impressum** und **Datenschutz**  
- Inhalte sind personalisiert auf: *Leugzim Rullani, Untere Farnbühlstrasse 3, 5610 Wohlen*  
- Links im Footer des Frontends sind jederzeit erreichbar

---

## Voraussetzungen

Zum Start über Docker benötigst du:  

- [Docker](https://www.docker.com/) inkl. `docker-compose`  
- Git (zum Klonen des Repositories)

FFmpeg und weitere Python-Abhängigkeiten sind im Docker-Image bereits berücksichtigt.
Für lokale Entwicklung ohne Docker muss FFmpeg ggf. separat installiert werden.

---

## Quickstart mit Docker

> **Ziel:** Aus einem frischen Clone mit wenigen Befehlen ein lauffähiges Backend starten.  
> Einige Schritte sind aus der offiziellen Docker-Dokumentation übernommen. :contentReference[oaicite:21]{index=21}  

1. **Repository klonen**

```bash
git clone <DEIN-GITHUB-URL-ZU-DIESEM-REPO>.git
cd videoflix-backend
.env aus Template erstellen
Im Projekt-Root liegt .env.template. Erzeuge daraus deine lokale .env:
bash
Code kopieren
cp .env.template .env
.env ausfüllen
Siehe Abschnitt Umgebungsvariablen.
Docker-Container bauen & starten
bash
Code kopieren
docker-compose up --build
Der Django-Container heißt typischerweise web.
Postgres & Redis werden im Compose-File automatisch gestartet.
Migrations im Container ausführen
In einem neuen Terminal:
bash
Code kopieren
docker-compose exec web python manage.py migrate
(Optional) Superuser erstellen
bash
Code kopieren
docker-compose exec web python manage.py createsuperuser
Danach sollte das Backend unter http://localhost:8000/ erreichbar sein.
Die API liegt unter http://localhost:8000/api/....
Umgebungsvariablen
Die wichtigsten Variablen (werden über .env gesetzt und von settings.py gelesen): 
Videoflix_Docker_Readme

env
Code kopieren
# Django
SECRET_KEY=please_change_me
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1

# Postgres
DB_NAME=videoflix
DB_USER=videoflix
DB_PASSWORD=videoflix
DB_HOST=db
DB_PORT=5432

# Redis (Beispiel)
REDIS_URL=redis://redis:6379/0

# E-Mail (für Registrierung & Passwort-Reset)
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@example.com
EMAIL_HOST_PASSWORD=your_email_password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=Videoflix <your_email@example.com>
Passe diese Werte an deine Umgebung an (lokal, Prüfungsrechner, etc.).
Datenbank & Migrations
Die Datenbank ist im Docker-Setup auf Postgres konfiguriert. 
Videoflix_Docker_Readme

 Typische Befehle:
bash
Code kopieren
# Migrations erstellen (nur bei Model-Änderungen nötig)
docker-compose exec web python manage.py makemigrations

# Migrations anwenden
docker-compose exec web python manage.py migrate
HLS-Generierung
Für die HLS-Streams (480p, 720p, 1080p) gibt es einen Management-Command:
bash
Code kopieren
docker-compose exec web python manage.py generate_hls
Optionen:
--video-id <id> – nur für ein bestimmtes Video HLS generieren
--overwrite – bestehende HLS-Dateien überschreiben
Die Ausgabe landet in dem konfigurierten HLS_ROOT (z. B. MEDIA_ROOT/hls/...).
Background-Tasks & Redis
Für aufwendige Tasks (z. B. E-Mail-Versand, HLS-Generierung) ist django-rq
als Background-Task-Runner vorgesehen, Redis als Queue-Backend. 
Videoflix_Docker_Readme

 Ein typischer Setup umfasst:
Konfiguration von CACHES und RQ_QUEUES in settings.py
Start eines RQ-Workers im Container, z. B.:
bash
Code kopieren
docker-compose exec web python manage.py rqworker default
Konkrete Jobs (z. B. „Registrierungs-Mail verschicken“) werden dann im Code
in eine Queue gelegt und im Hintergrund ausgeführt.
API-Übersicht
Die vollständige API ist in einer separaten Dokumentation beschrieben
(Videoflix API Endpoint Dokumentation). 
Videoflix_API_Endpoint_Dokument…

 Kurzüberblick:
Authentication
POST /api/register/ – Benutzer registrieren (E-Mail + Passwort)
GET /api/activate/<uidb64>/<token>/ – Account aktivieren
POST /api/login/ – Login, setzt access_token + refresh_token Cookies
POST /api/logout/ – Logout, Blacklisting des Refresh-Tokens
POST /api/token/refresh/ – neuen Access-Token via Cookie holen
POST /api/password_reset/ – Passwort-Reset-E-Mail anstoßen
POST /api/password_confirm/<uidb64>/<token>/ – neues Passwort setzen
Videos & Streaming
GET /api/video/ – Liste aller Videos (Titel, Beschreibung, Thumbnail, Kategorie, created_at, …)
GET /api/video/<movie_id>/<resolution>/index.m3u8 – HLS-Playlist für eine Auflösung
GET /api/video/<movie_id>/<resolution>/<segment>/ – einzelnes HLS-Segment
Tests
Je nach Setup:
bash
Code kopieren
docker-compose exec web python manage.py test
Falls zusätzlich pytest verwendet wird:
bash
Code kopieren
docker-compose exec web pytest
requirements.txt aktuell halten
Damit die Prüfer:innen das Projekt problemlos installieren können, sollte
requirements.txt immer zum aktuellen Stand passen. Empfohlener Workflow:
Im laufenden web-Container alle benötigten Pakete installiert haben
Dann aus dem Projekt-Root:
bash
Code kopieren
docker-compose exec web pip freeze > requirements.txt
requirements.txt committen
So ist sichergestellt, dass alle Abhängigkeiten (Django, DRF, SimpleJWT, django-rq,
django-redis, psycopg2-binary, gunicorn, whitenoise, etc.) exakt dem Stand im Container entsprechen. 
Videoflix_Docker_Readme

Rechtliches
Betreiber (Demoprojekt): Leugzim Rullani
Untere Farnbühlstrasse 3
5610 Wohlen
E-Mail: leugzimrullani@outlook.com Detaillierte rechtliche Informationen finden sich im Frontend unter:
/pages/legal/imprint/index.html (Impressum)
/pages/legal/privacy/index.html (Datenschutz)